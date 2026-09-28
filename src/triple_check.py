"""
Line movement, public money, and the two venues — together, against outcomes.

THE QUESTION
Each family has been looked at alone and come back null. This asks whether
they mean something in COMBINATION: when two or three of them point the same
way, does that side win more often than when they disagree? And does any one
of them correlate with the result at all across the full sample?

WHY THIS USES ~978 GAMES AND NOT OUR 103 PLAYS
`venue_signal` compared our own winners against our own losers, which is two
groups of roughly seventy — too small for a five-point difference to mean
anything, and restricted in range because the gates already selected on the
very things being measured. Every consensus-qualifying game is used here
instead, whether we bet it or not, and the outcome measured is whether the
ADVANTAGE side won. Nine times the sample and no selection on the features.

THE ONE LEAD THIS IS CHASING
`venue_signal` found the order-book size lean running BACKWARDS among our
plays: losers averaged +0.363 toward the side we backed, winners +0.219, with
the same inversion on Kalshi. That bears on a live gate — gate 5 treats
`imbalance > 0.20` as confirmation. If more lean really goes with more losing,
that gate is pointed the wrong way, and it would be the first real
improvement found this season. On 103 post-hoc games it is a hypothesis; this
tests it on the full sample.

EVERY READING IS STILL CUT AT THE FREEZE
Both venues log through the game and past settlement, and 37% of all readings
fall at or after first pitch minus 15 minutes. That cut is reused from
`venue_signal` rather than reimplemented.

HOW THE SCAN IS PAID FOR
Eight features, three families, and an agreement count is a lot of places to
find something. Each feature gets a correlation and an ROI split; the best is
then corrected by a max-statistic permutation with outcomes redrawn from
de-vigged prices, and anything surviving that must still repeat across random
halves. That pairing is what killed every other candidate this season.

Writes output/triple_check.md.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
import random
import statistics as st
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import _implied
from .venue_signal import LOCK_LEAD, _pregame, _venue

log = logging.getLogger("triple_check")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 3000
MIN_CELL = 40


def collect() -> list[dict]:
    """One row per consensus-qualifying game, every feature signed toward the
    ADVANTAGE side, outcome = did that side win."""
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
            m = bgame.get("matchup") or ""
            pc = bgame.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if " @ " not in m or not adv or not isinstance(a_ml, int) \
                    or not isinstance(o_ml, int):
                continue
            away, home = m.split(" @ ")
            if adv not in (away, home):
                continue
            adv_home = adv == home
            start = bgame.get("game_datetime")
            if not start:
                continue
            try:
                cutoff = (dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
                          - LOCK_LEAD).timestamp()
            except ValueError:
                continue

            pv = _venue(_pregame(g.get("readings"), cutoff))
            kv = _venue(_pregame(g.get("k_readings"), cutoff))
            # venue readings are logged on g["side"]; flip when that is not adv
            vflip = 1 if g.get("side") == adv else -1

            chk = bgame.get("public_check") or {}
            ms, maj = chk.get("money_side"), chk.get("majority_side")
            pct = chk.get("money_pct")
            handle = None
            if ms in ("home", "away") and isinstance(pct, (int, float)):
                on_adv = (ms == "home") == adv_home
                handle = (pct - 50) * (1 if on_adv else -1)
            tickets = None
            if maj in ("home", "away"):
                tickets = 1.0 if ((maj == "home") == adv_home) else -1.0

            tot = _implied(a_ml) + _implied(o_ml)
            rows.append({
                "date": date, "adv_odds": a_ml, "opp_odds": o_ml,
                "adv_won": res["winner"] == adv,
                "p_adv": (_implied(a_ml) / tot) if tot > 0 else 0.5,
                "line": (pc.get("line_check") or {}).get("implied_shift"),
                "handle": handle, "tickets": tickets,
                "pm_drift": (pv["drift"] * vflip) if pv else None,
                "pm_imb": (pv["imbalance"] * vflip) if pv else None,
                "k_drift": (kv["drift"] * vflip) if kv else None,
                "k_imb": (kv["imbalance"] * vflip) if kv else None,
                "gap": ((pv["close"] - kv["close"]) * vflip) if (pv and kv) else None,
            })
    return rows


FEATURES = [
    ("line movement", "line", "line"),
    ("handle share", "handle", "public"),
    ("ticket majority", "tickets", "public"),
    ("Polymarket drift", "pm_drift", "venue"),
    ("Polymarket size lean", "pm_imb", "venue"),
    ("Kalshi drift", "k_drift", "venue"),
    ("Kalshi size lean", "k_imb", "venue"),
    ("venue price gap", "gap", "venue"),
]


def _bets(rows, back_adv=True):
    return [((r["adv_odds"] if back_adv else r["opp_odds"]),
             (r["adv_won"] if back_adv else not r["adv_won"])) for r in rows]


def _roi(bets) -> float:
    if not bets:
        return 0.0
    return sum(grade.american_profit(o) if w else -1 for o, w in bets) / len(bets)


def _fmt(rows, back_adv=True) -> str:
    b = _bets(rows, back_adv)
    if not b:
        return "—"
    w = sum(1 for _, won in b if won)
    return f"{w}-{len(b)-w} · **{_roi(b):+.1%}** (n={len(b)})"


def build() -> str:
    rows = collect()
    md = ["# Line movement, public money and the two venues, together", "",
          "_Every consensus-qualifying game, not only the ones we bet. All "
          "features signed toward the ADVANTAGE side; the outcome is whether "
          "that side won. Order-book readings cut at first pitch minus 15 "
          "minutes._", "",
          f"- games: **{len(rows)}**", ""]
    if len(rows) < 200:
        return "\n".join(md + ["Not enough joined games.", ""])

    # --- each feature alone -----------------------------------------------
    md += ["## Each signal against the result", "",
           "_`r` is the correlation with the advantage side winning. The two "
           "ROI columns back that side when the signal is positive, and when "
           "it is negative._", "",
           "| signal | n | r with winning | signal > 0 | signal < 0 |",
           "|---|---|---|---|---|"]
    cells = []
    for label, key, fam in FEATURES:
        sub = [r for r in rows if isinstance(r.get(key), (int, float))]
        if len(sub) < MIN_CELL:
            md.append(f"| {label} | {len(sub)} | — | — | — |")
            continue
        xs = [r[key] for r in sub]
        ys = [1.0 if r["adv_won"] else 0.0 for r in sub]
        r_ = (st.correlation(xs, ys)
              if len(set(xs)) > 1 and len(set(ys)) > 1 else 0.0)
        pos = [r for r in sub if r[key] > 0]
        neg = [r for r in sub if r[key] < 0]
        cells += [(f"{label} >0", pos), (f"{label} <0", neg)]
        md.append(f"| {label} | {len(sub)} | **{r_:+.3f}** | {_fmt(pos)} "
                  f"| {_fmt(neg)} |")
    md.append("")

    # --- the lead: is the size lean inverted? -----------------------------
    md += ["## The lead: is the order-book size lean pointed the wrong way?", "",
           "_`venue_signal` found losers averaging a STRONGER lean toward our "
           "side than winners (+0.363 against +0.219), on 103 post-hoc games. "
           "Gate 5 treats `imbalance > 0.20` as confirmation, so if that "
           "inversion is real the gate is backwards._", "",
           "| Polymarket size lean toward the advantage side | that side |",
           "|---|---|"]
    bands = [("strong lean > +0.40", lambda v: v > 0.40),
             ("lean +0.20 to +0.40  (what gate 5 accepts)",
              lambda v: 0.20 < v <= 0.40),
             ("flat -0.20 to +0.20", lambda v: -0.20 <= v <= 0.20),
             ("lean against -0.40 to -0.20", lambda v: -0.40 <= v < -0.20),
             ("strong lean against < -0.40", lambda v: v < -0.40)]
    for label, test in bands:
        sub = [r for r in rows if isinstance(r.get("pm_imb"), (int, float))
               and test(r["pm_imb"])]
        md.append(f"| {label} | {_fmt(sub)} |")
    md += ["", "_If the top rows are worse than the bottom rows, more lean "
           "goes with more losing and gate 5's condition is inverted._", ""]

    # --- agreement across the three families ------------------------------
    md += ["## When the three families agree", "",
           "_One vote each: line movement toward the advantage side, the "
           "public (handle and tickets), and the venues (Polymarket and "
           "Kalshi drift). Counting how many point the same way._", "",
           "| families pointing at the advantage side | that side |",
           "|---|---|"]

    def _votes(r) -> int | None:
        v = []
        if isinstance(r.get("line"), (int, float)):
            v.append(1 if r["line"] > 0 else -1)
        pub = [x for x in (r.get("handle"), r.get("tickets"))
               if isinstance(x, (int, float))]
        if pub:
            v.append(1 if sum(1 if p > 0 else -1 for p in pub) > 0 else -1)
        ven = [x for x in (r.get("pm_drift"), r.get("k_drift"))
               if isinstance(x, (int, float))]
        if ven:
            v.append(1 if sum(1 if d > 0 else -1 for d in ven) > 0 else -1)
        return None if len(v) < 3 else sum(1 for x in v if x > 0)

    agree_cells = []
    for n_ in (3, 2, 1, 0):
        sub = [r for r in rows if _votes(r) == n_]
        agree_cells.append((f"{n_} of 3", sub))
        md.append(f"| {n_} of 3 | {_fmt(sub)} |")
    md.append("")

    # --- pay for the scan --------------------------------------------------
    pool = [(l, s) for l, s in (cells + agree_cells) if len(s) >= MIN_CELL]
    if pool:
        bl, bs = max(pool, key=lambda c: _roi(_bets(c[1])))
        obs = _roi(_bets(bs)) * 100
        plan = [[(grade.american_profit(r["adv_odds"]), r["p_adv"]) for r in s]
                for _, s in pool]
        rng = random.Random(21)
        null = [max(sum(w if rng.random() < p else -1 for w, p in pl) / len(pl)
                    for pl in plan) * 100 for _ in range(TRIALS)]
        pv = (sum(1 for x in null if x >= obs) + 1) / (len(null) + 1)
        md += ["## Does the best of all of them beat the search?", "",
               f"- cells at n≥{MIN_CELL}: **{len(pool)}**",
               f"- best: **{bl}** at {obs:+.1f}%",
               f"- biggest a price-redraw manufactures: median "
               f"**{st.median(null):+.1f}%**, 95th pct "
               f"**{sorted(null)[int(.95*len(null))]:+.1f}%**",
               f"- **corrected p = {pv:.3f}**", "",
               ("**Clears the scan** — now it needs split-half below."
                if pv < 0.05 else
                "**Does not clear.** A scan this wide manufactures a cell "
                "this good often enough that the number is the width of the "
                "search."), ""]

        # split-half on the best cell, whatever the permutation said
        rh = random.Random(404)
        half = [rh.random() < 0.5 for _ in bs]
        a = [r for r, h in zip(bs, half) if h]
        b = [r for r, h in zip(bs, half) if not h]
        if min(len(a), len(b)) >= 15:
            md += [f"- split-half of **{bl}**: {_fmt(a)} against {_fmt(b)}", "",
                   "_Two halves of the same cell landing far apart means the "
                   "cell is noise, whatever its pooled number._", ""]

    md += ["## How to read this", "",
           "- a cell must clear the permutation AND repeat across halves; "
           "nothing this season has done both",
           "- the size-lean table is the only part bearing on a LIVE gate, so "
           "it matters even if every other row is flat",
           "- nothing here changes the board on its own.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "triple_check.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
