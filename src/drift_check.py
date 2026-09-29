"""
Is "back Polymarket drift = +10.5%" real, or is it reading the game?

WHAT HAPPENED
`signal_sweep` returned the first result of this season to clear everything:
backing Polymarket drift at +10.5% over 962 games, corrected p = 0.006 across
32 cells, split-half +8.6% against +12.2%. Fading it at -16.2%, p = 0.003,
split-half -16.3% / -16.1%. Nothing else has come close.

WHY IT IS PROBABLY WRONG
`consensus.book_metrics` computes drift as the last reading minus the first
across the WHOLE day file, with no time cut. Its docstring calls it "the
day's pre-game order-book log", and live that is true - when the board builds
at 4pm the file only holds readings up to 4pm. But a BACKTEST reads the
completed file, which `venue_signal` already measured as 37% at-or-after
first pitch.

So the backtest's "drift" includes the price moving DURING the game. A team
that is winning drifts toward 1.00. That predicts the winner almost
perfectly and means nothing.

THE TEST
Recompute drift two ways on the same games and compare:

    as the backtest does   first to last reading, whole file
    pre-game only          readings strictly before first pitch - 15 min,
                           the moment the board freezes a pick

If the effect survives the cut it is real and it is the find of the season.
If it collapses, the +10.5% was circular, and the same contamination may sit
inside every other backtest that calls `book_metrics` on completed days -
which is most of them, including the ones that validated the live rule.

The live RECORD is unaffected either way: those were real bets placed before
first pitch, from a file that held only pre-game readings at the time.

Writes output/drift_check.md.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
import random
import statistics as st
from pathlib import Path

from . import consensus as C, grade, mlb_api
from .pregame_money import _implied

log = logging.getLogger("drift_check")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
LOCK_LEAD = dt.timedelta(minutes=15)
TRIALS = 3000


def _mid(r):
    b, a = r.get("bid"), r.get("ask")
    if not (isinstance(b, (int, float)) and isinstance(a, (int, float))):
        return None
    if a <= b or (a - b) > C.MAX_SPREAD:
        return None
    return (a + b) / 2


def collect() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "pm_books_2026-*.json"))):
        date = Path(f).stem.split("pm_books_")[1]
        try:
            day = json.loads(Path(f).read_text())
            board = json.loads((OUTPUT_DIR / f"picks_{date}.json").read_text())
            results = mlb_api.results_for(date)
        except Exception:
            continue
        bg = {g.get("game_pk"): g for g in board.get("games", [])}
        for pk_s, g in (day.get("games") or {}).items():
            try:
                pk = int(pk_s)
            except (TypeError, ValueError):
                continue
            bgame, res = bg.get(pk), results.get(pk)
            if not bgame or not res or not res.get("final") or not res.get("winner"):
                continue
            pc = bgame.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            m = bgame.get("matchup") or ""
            start = bgame.get("game_datetime")
            if (" @ " not in m or not adv or not isinstance(a_ml, int)
                    or not isinstance(o_ml, int) or not start):
                continue
            away, home = m.split(" @ ")
            if adv not in (away, home):
                continue
            opp = home if adv == away else away
            try:
                cutoff = (dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
                          - LOCK_LEAD).timestamp()
            except ValueError:
                continue

            reads = [r for r in (g.get("readings") or [])
                     if not r.get("empty") and _mid(r) is not None]
            reads.sort(key=lambda r: r.get("t", 0))
            pre = [r for r in reads
                   if isinstance(r.get("t"), (int, float)) and r["t"] <= cutoff]
            if len(reads) < C.MIN_READINGS:
                continue
            full_drift = _mid(reads[-1]) - _mid(reads[0])
            pre_drift = (_mid(pre[-1]) - _mid(pre[0])
                         if len(pre) >= C.MIN_READINGS else None)
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0:
                continue
            side = g.get("side")
            flip = 1 if side == adv else -1
            rows.append({
                "date": date, "adv": adv, "opp": opp,
                "adv_odds": a_ml, "opp_odds": o_ml,
                "adv_won": res["winner"] == adv,
                "p_adv": _implied(a_ml) / tot,
                "full": full_drift * flip,
                "pre": (pre_drift * flip) if pre_drift is not None else None,
                "n_all": len(reads), "n_pre": len(pre),
            })
    return rows


def _bets(rs, key):
    """Back whichever side the drift points at."""
    out = []
    for r in rs:
        d = r.get(key)
        if d is None or d == 0:
            continue
        back_adv = d > 0
        out.append(((r["adv_odds"] if back_adv else r["opp_odds"]),
                    (r["adv_won"] if back_adv else not r["adv_won"]),
                    (r["p_adv"] if back_adv else 1 - r["p_adv"])))
    return out


def _roi(b) -> float:
    if not b:
        return 0.0
    return sum(grade.american_profit(o) if w else -1 for o, w, _ in b) / len(b)


def _fmt(b) -> str:
    if not b:
        return "—"
    w = sum(1 for _, won, _ in b if won)
    return f"{w}-{len(b)-w} · **{_roi(b):+.1%}** (n={len(b)})"


def build() -> str:
    rows = collect()
    md = ["# Is the Polymarket drift signal real, or is it reading the game?",
          "", "_`signal_sweep` returned backing Polymarket drift at +10.5%, "
          "corrected p = 0.006, split-half +8.6% / +12.2% — the first result "
          "this season to clear everything. `book_metrics` computes drift "
          "across the WHOLE day file with no time cut, and 37% of readings "
          "fall at or after first pitch, so that number may simply be the "
          "price moving during the game._", "",
          f"- games: **{len(rows)}**", ""]
    if len(rows) < 300:
        return "\n".join(md + ["Not enough games.", ""])

    n_all = st.mean([r["n_all"] for r in rows])
    n_pre = st.mean([r["n_pre"] for r in rows])
    md += [f"- readings per game: **{n_all:.1f}** in the whole file, "
           f"**{n_pre:.1f}** before the freeze "
           f"(**{1 - n_pre/n_all:.0%}** discarded)", ""]

    full = _bets(rows, "full")
    pre = _bets(rows, "pre")
    md += ["## The same signal, computed two ways", "",
           "| drift measured | backing the side it points at |", "|---|---|",
           f"| whole day file (what the backtest did) | {_fmt(full)} |",
           f"| **pre-game only** (before first pitch − 15 min) | {_fmt(pre)} |",
           ""]

    # same games both ways, so the comparison is not a sample artefact
    both = [r for r in rows if r.get("pre") is not None and r["pre"] != 0
            and r["full"] != 0]
    fb = _bets(both, "full")
    pb = _bets(both, "pre")
    md += ["_On the identical subset of games, so the difference is the "
           "measurement and not the sample:_", "",
           "| drift measured | same games |", "|---|---|",
           f"| whole day file | {_fmt(fb)} |",
           f"| pre-game only | {_fmt(pb)} |", ""]

    agree = sum(1 for r in both if (r["full"] > 0) == (r["pre"] > 0))
    md += [f"- the two measures point at the SAME side in "
           f"**{agree}/{len(both)}** ({agree/max(len(both),1):.0%}) of games",
           ""]

    if pb:
        rng = random.Random(11)
        null = []
        for _ in range(TRIALS):
            null.append(sum(grade.american_profit(o) if rng.random() < p else -1
                            for o, _, p in pb) / len(pb) * 100)
        obs = _roi(pb) * 100
        pv = (sum(1 for x in null if x >= obs) + 1) / (TRIALS + 1)
        md += ["## Does the pre-game version stand on its own?", "",
               f"- pre-game drift: **{obs:+.1f}%** (n={len(pb)})",
               f"- market-calibrated null: median {st.median(null):+.1f}%, "
               f"95th {sorted(null)[int(.95*TRIALS)]:+.1f}%",
               f"- **p = {pv:.3f}** (single test, no grid to correct — this "
               "was specified before looking)", ""]
        rh = random.Random(6)
        tag = [rh.random() < 0.5 for _ in pb]
        a = [x for x, t in zip(pb, tag) if t]
        b = [x for x, t in zip(pb, tag) if not t]
        if min(len(a), len(b)) >= 40:
            md += [f"- split-half: {_fmt(a)} against {_fmt(b)}", ""]

    md += ["## What follows either way", "",
           "- **if the pre-game version holds**, it is the find of the "
           "season and a candidate signal in its own right",
           "- **if it collapses**, the +10.5% was circular, and the same "
           "contamination sits in every backtest that calls `book_metrics` "
           "on a completed day — including the ones used to validate the "
           "live rule's gates. Those would all need re-reading.",
           "- the live RECORD is unaffected either way: those were real bets "
           "placed before first pitch, from a file that held only pre-game "
           "readings at the time.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "drift_check.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
