"""
Which venue should confirm the consensus pick - and how many plays does each
one cost us?

THE PROBLEM
The live rule requires Polymarket's pre-game order book to confirm the consensus
side. That gate is the binding constraint on board size: PM readings exist for
roughly 44% of games, Kalshi money for ~89%. Whole slates come back empty not
because no game qualified but because the confirming data was missing - which is
a data-coverage failure being reported to the user as "no plays today".

WHAT IS TESTED
The live rule replayed on history, changing only the confirmation source:

    pm      - Polymarket order book (what runs now)
    kalshi  - the consensus side holds more pre-game Kalshi volume
    either  - either venue confirms  (max coverage)
    both    - both must confirm      (max strictness)
    none    - no confirmation at all (isolates what confirmation is worth)

Each is run with and without the line-against price filter, since that filter
also cuts volume hard. Reported per cell: record, ROI, n, plays per slate day,
and the holdout split - because a variant that earns slightly less per bet while
finding twice as many bets can still be the better rule, and only the per-day
column makes that visible.

Writes output/confirm_source.md. Reporting only - it changes nothing by itself.
"""

from __future__ import annotations

import glob
import json
import logging
import statistics as st
import time
from pathlib import Path

from . import grade, mlb_api
from .analysis import _canon_abbr
from .consensus import IMBALANCE_MIN, book_metrics, line_tag
from .pregame_money import (HOLDOUT_FROM, LOOKBACK, MIN_N, PACE, _candles,
                            _start_ts, _vol, settled_index)

log = logging.getLogger("confirm_source")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
VARIANTS = ["pm", "kalshi", "either", "both", "none"]


def collect() -> tuple[list, int]:
    """One rec per game that clears the consensus gate, with each venue's read."""
    kmap = settled_index()
    recs, days = [], set()

    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        metrics = book_metrics(date)
        day = json.loads(Path(f).read_text())
        days.add(date)
        for g in day.get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            matchup = g.get("matchup") or ""
            if " @ " not in matchup:
                continue
            pc = g.get("pick_criteria") or {}
            chk = g.get("public_check") or {}
            maj = (g.get("public_majority") or {}).get("team")
            # --- the consensus gate itself, unchanged from the live rule ---
            if chk.get("money") != "with public" or not maj:
                continue
            away, home = matchup.split(" @ ")
            adv = pc.get("advantage_team")
            if maj not in (away, home) or not adv:
                continue
            odds = (pc.get("advantage_moneyline") if maj == adv
                    else pc.get("opponent_moneyline"))
            if not isinstance(odds, int):
                continue

            # --- venue reads, each may be None (no data) ---
            pm_ok = None
            m = metrics.get(g.get("game_pk"))
            if m:
                toward_adv = m["drift"] > 0 or m["imbalance"] > IMBALANCE_MIN
                pm_ok = toward_adv if maj == adv else (not toward_adv)

            kal_ok = None
            aa = _canon_abbr(g.get("away_abbr") or "")
            ha = _canon_abbr(g.get("home_abbr") or "")
            teams = kmap.get((date, frozenset({aa, ha}))) if aa and ha else None
            start = _start_ts(g.get("game_datetime"))
            if teams and start and len(teams) == 2:
                vols = {}
                for ab, info in teams.items():
                    cs = _candles(info["ticker"], start - LOOKBACK, start)
                    if cs:
                        vols[ab] = sum(_vol(c) for c in cs)
                    time.sleep(PACE)
                if len(vols) == 2 and vols[aa] != vols[ha]:
                    money_side = away if vols[aa] > vols[ha] else home
                    kal_ok = (money_side == maj)

            recs.append({
                "date": date, "won": res["winner"] == maj, "odds": odds,
                "pm": pm_ok, "kalshi": kal_ok,
                "line": line_tag(g, maj),
            })
    return recs, len(days)


def _passes(r: dict, variant: str) -> bool:
    pm, k = r["pm"], r["kalshi"]
    if variant == "pm":
        return pm is True
    if variant == "kalshi":
        return k is True
    if variant == "either":
        return pm is True or k is True
    if variant == "both":
        return pm is True and k is True
    return True                                    # "none"


def _fmt(rows, days: int) -> str:
    if not rows:
        return "—"
    w = sum(1 for x in rows if x["won"])
    u = sum(grade.american_profit(x["odds"]) if x["won"] else -1 for x in rows)
    per = len(rows) / days if days else 0
    tag = "" if len(rows) >= MIN_N else " _(thin)_"
    return (f"{w}-{len(rows)-w} · {u:+.1f}u · **{u/len(rows):+.1%}** "
            f"(n={len(rows)}, {per:.1f}/day){tag}")


def build() -> str:
    recs, days = collect()
    md = ["# Which venue should confirm the pick?", "",
          "_The live rule replayed on history, changing only the confirmation "
          "source. The order-book gate is the binding constraint on board size, "
          "so the plays-per-day column matters as much as ROI: a variant that "
          "earns a little less per bet while finding twice as many can still be "
          "the better rule._", "",
          f"## Coverage", "",
          f"- slate days: **{days}**",
          f"- games clearing the consensus gate: **{len(recs)}**",
          f"- of those, Polymarket has a read on **{sum(1 for r in recs if r['pm'] is not None)}**",
          f"- of those, Kalshi has a read on **{sum(1 for r in recs if r['kalshi'] is not None)}**", ""]

    if len(recs) < MIN_N:
        return "\n".join(md + ["## Verdict", "", "Too few games to read.", ""])

    for require_line in (True, False):
        label = ("line-against required (the live setting)" if require_line
                 else "no line filter")
        md += [f"## {label}", "",
               "| confirmation | all-time | in-sample | holdout |",
               "|---|---|---|---|"]
        for v in VARIANTS:
            sub = [r for r in recs if _passes(r, v)
                   and (not require_line or r["line"] == "against")]
            pre = [r for r in sub if r["date"] < HOLDOUT_FROM]
            post = [r for r in sub if r["date"] >= HOLDOUT_FROM]
            md.append(f"| `{v}` | {_fmt(sub, days)} | {_fmt(pre, days)} | "
                      f"{_fmt(post, days)} |")
        md.append("")

    # how often do the two venues actually disagree?
    both = [r for r in recs if r["pm"] is not None and r["kalshi"] is not None]
    same = sum(1 for r in both if r["pm"] == r["kalshi"])
    md += ["## Do the two venues say the same thing?", "",
           f"- games where both have a read: **{len(both)}**",
           f"- they agree: **{same}**"
           + (f" ({same/len(both):.0%})" if both else ""), ""]
    if both:
        dis = [r for r in both if r["pm"] != r["kalshi"]]
        md += ["_When they disagree:_", "",
               "| follow | result |", "|---|---|",
               f"| Polymarket's read | {_fmt([r for r in dis if r['pm']], days)} |",
               f"| Kalshi's read | {_fmt([r for r in dis if r['kalshi']], days)} |", ""]

    md.append("_A variant only replaces the live rule if it beats it on the "
              "holdout as well as all-time. Higher volume alone is not a reason "
              "to switch - it is only a reason to look._")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "confirm_source.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
