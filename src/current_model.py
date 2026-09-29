"""
What the system running RIGHT NOW would have done over the whole record.

WHY THIS IS NOT JUST TWO NUMBERS ADDED UP
The live system is two rules that interact. The consensus rule picks; the fade
rule backs the other side of anything the consensus rule WITHDRAWS. Tightening
the gates cuts picks, which cuts withdrawals, which cuts fades. The 67-pick
backtest and the 143-fade backtest were measured under different settings and
cannot simply be summed.

So this replays the season properly: for every committed board version, the
gates are re-evaluated under the CURRENT settings, using only the order-book
readings that existed at that moment. A game that qualifies in some version and
not the last one is a withdrawal, and therefore a fade.

WHAT IT IS AND IS NOT
It is the best available estimate of the current system's record. It is not the
record - those picks were never made, and a backtest of settings chosen partly
by looking at this data will flatter itself. The confirm change was tested on
its own at p = 0.028 with a +10.2 point holdout gain, so expect the live number
to land nearer that than the headline here.

Writes output/current_model.md.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
import subprocess
from collections import defaultdict
from pathlib import Path

from . import consensus as C, grade, mlb_api
from .pregame_money import _implied

log = logging.getLogger("current_model")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPO = Path(__file__).resolve().parent.parent


def _shas(rel):
    try:
        o = subprocess.run(["git", "log", "--format=%H", "--all", "--reverse",
                            "--", rel], cwd=REPO, capture_output=True,
                           text=True, timeout=120)
        return [x for x in o.stdout.split() if x]
    except Exception:
        return []


def _at(sha, rel):
    try:
        o = subprocess.run(["git", "show", f"{sha}:{rel}"], cwd=REPO,
                           capture_output=True, text=True, timeout=60)
        return json.loads(o.stdout) if o.returncode == 0 else None
    except Exception:
        return None


def _metrics_as_of(books: dict, cutoff_ts: int | None) -> dict:
    """book_metrics using only readings that existed at `cutoff_ts`.

    Without the cutoff every version would be scored on the full day's book,
    which is hindsight - the 9am board cannot see the 6pm order flow."""
    out = {}
    for pk_s, g in (books.get("games") or {}).items():
        reads = [r for r in (g.get("readings") or [])
                 if not r.get("empty")
                 and isinstance(r.get("bid"), (int, float))
                 and isinstance(r.get("ask"), (int, float))
                 and r["ask"] > r["bid"] and (r["ask"] - r["bid"]) <= C.MAX_SPREAD
                 and (cutoff_ts is None or (r.get("t") or 0) <= cutoff_ts)]
        if len(reads) < C.MIN_READINGS:
            continue
        reads.sort(key=lambda r: r.get("t", 0))
        f, l = reads[0], reads[-1]
        drift = (l["bid"] + l["ask"]) / 2 - (f["bid"] + f["ask"]) / 2
        bs, as_ = l.get("bid_sz") or 0, l.get("ask_sz") or 0
        imb = (bs - as_) / (bs + as_) if (bs + as_) > 0 else 0.0
        try:
            out[int(pk_s)] = {"drift": drift, "imbalance": imb}
        except (TypeError, ValueError):
            continue
    return out


def _qualifies(g: dict, metrics: dict):
    """Current live gates. Returns (bet_team, odds) or None."""
    pc = g.get("pick_criteria") or {}
    chk = g.get("public_check") or {}
    maj = (g.get("public_majority") or {}).get("team")
    adv = pc.get("advantage_team")
    m = g.get("matchup") or ""
    if chk.get("money") != "with public" or not maj or not adv or " @ " not in m:
        return None
    odds = pc.get("advantage_moneyline") if maj == adv else pc.get("opponent_moneyline")
    if not isinstance(odds, int):
        return None
    mm = metrics.get(g.get("game_pk"))
    if not mm or not C._confirms(mm, maj == adv):
        return None
    if C.line_tag(g, maj) != "against":
        return None
    return maj, odds


def simulate() -> list[dict]:
    out = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        rel = f"output/picks_{date}.json"
        shas = _shas(rel)
        if not shas:
            continue
        try:
            books = json.loads((OUTPUT_DIR / f"pm_books_{date}.json").read_text())
            results = mlb_api.results_for(date)
        except Exception:
            continue
        seen: dict = defaultdict(dict)
        final_state: dict = {}
        last_game: dict = {}
        for sha in shas:
            day = _at(sha, rel)
            if not day:
                continue
            ts = None
            if day.get("generated_at"):
                try:
                    ts = int(dt.datetime.fromisoformat(
                        day["generated_at"].replace("Z", "+00:00")).timestamp())
                except ValueError:
                    ts = None
            metrics = _metrics_as_of(books, ts)
            for g in day.get("games", []):
                pk = g.get("game_pk")
                q = _qualifies(g, metrics)
                last_game[pk] = g
                final_state[pk] = q
                if q and pk not in seen:
                    seen[pk] = {"bet": q[0], "odds": q[1]}
        for pk, first in seen.items():
            res = results.get(pk)
            g = last_game.get(pk)
            if not res or not res.get("final") or not res.get("winner") or not g:
                continue
            survived = final_state.get(pk) is not None
            if survived:
                bet, odds = final_state[pk]
                out.append({"date": date, "kind": "pick", "matchup": g.get("matchup"),
                            "bet": bet, "odds": odds, "won": res["winner"] == bet})
            else:
                m = g.get("matchup") or ""
                if " @ " not in m:
                    continue
                away, home = m.split(" @ ")
                fade = home if first["bet"] == away else away
                pc = g.get("pick_criteria") or {}
                adv = pc.get("advantage_team")
                odds = (pc.get("advantage_moneyline") if fade == adv
                        else pc.get("opponent_moneyline"))
                if not isinstance(odds, int):
                    continue
                out.append({"date": date, "kind": "fade", "matchup": m,
                            "bet": fade, "odds": odds, "won": res["winner"] == fade})
    return out


def _tally(rs):
    if not rs:
        return 0, 0, 0.0, 0.0
    w = sum(1 for r in rs if r["won"])
    u = sum(grade.american_profit(r["odds"]) if r["won"] else -1 for r in rs)
    return w, len(rs) - w, u, u / len(rs)


def _line(lbl, rs):
    w, l, u, roi = _tally(rs)
    if not rs:
        return f"| {lbl} | — | — | — | — |"
    return (f"| {lbl} | **{w}-{l}** | {w/(w+l):.1%} | {u:+.2f}u | **{roi:+.1%}** |")


def build() -> str:
    rows = simulate()
    md = ["# What the current live system would have returned", "",
          "_Every committed board version replayed under today's gates, scored "
          "only on the order-book readings that existed at that moment. A game "
          "that qualified in some version and not the last is a withdrawal, and "
          "therefore a fade._", "",
          f"- rule: confirm **BOTH** signals · line move **≥"
          f"{C.LINE_MOVE_MIN:.1%}** · imbalance **>{C.IMBALANCE_MIN}** · fade "
          f"rule **on**", ""]
    if not rows:
        return "\n".join(md + ["No games reconstructed.", ""])
    picks = [r for r in rows if r["kind"] == "pick"]
    fades = [r for r in rows if r["kind"] == "fade"]
    dates = sorted({r["date"] for r in rows})
    md += [f"- period: **{dates[0]} → {dates[-1]}** ({len(dates)} slates)", "",
           "| | record | win rate | units | ROI |", "|---|---|---|---|---|",
           _line("consensus picks", picks),
           _line("fades", fades),
           _line("**EVERYTHING**", rows), ""]

    # what the ledger actually holds, for comparison
    try:
        led = json.load(open(OUTPUT_DIR / "ledger.json"))["plays"]["entries"]
        real = [e for e in led if e.get("date") and e["date"] >= dates[0]]
        w = sum(1 for e in real if e.get("result") == "W")
        u = sum(e.get("profit", 0) for e in real)
        md += ["## Against what actually happened over the same period", "",
               "| | record | units | ROI |", "|---|---|---|---|",
               f"| actual ledger | {w}-{len(real)-w} | {u:+.2f}u | "
               f"**{u/len(real):+.1%}** |" if real else "| actual ledger | — | — | — |",
               f"| current model | {_tally(rows)[0]}-{_tally(rows)[1]} | "
               f"{_tally(rows)[2]:+.2f}u | **{_tally(rows)[3]:+.1%}** |", ""]
    except Exception:
        pass

    mid = dates[len(dates) // 2]
    md += ["## Split in half, as a stability check", "",
           "| | record | win rate | units | ROI |", "|---|---|---|---|---|",
           _line("first half", [r for r in rows if r["date"] < mid]),
           _line("second half", [r for r in rows if r["date"] >= mid]), "",
           "_These picks were never made. Settings chosen partly by looking at "
           "this data will flatter themselves here; the confirm change tested "
           "alone gave a **+10.2 point** holdout gain, which is the number to "
           "plan around._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "current_model.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
