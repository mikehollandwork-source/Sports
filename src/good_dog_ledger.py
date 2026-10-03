"""
The good-dog tag as a PLAIN LEDGER: every qualifying dog on every board we have,
graded at the board's own price, in date order, with the running balance.

WHY THIS EXISTS ALONGSIDE good_dogs.py
`good_dogs.py` scans cuts and corrects them with a max-statistic permutation. That
answers "could this be noise". It does NOT answer "what would we actually have".
This does: one row per dog, $1 a bet, running units, worst drawdown. No grid, no
cells, no chosen cut - the tag's own shipped definition (`good_dog.tag` at
FAV_RATE) applied to each board as it stood.

POINT-IN-TIME BY CONSTRUCTION
`good_dog.favourite_rates(date)` reads boards dated STRICTLY BEFORE `date`, so a
team is never labelled "usually the favourite" using the games being graded. The
price is the board's own recorded moneyline for that team, not a reconstruction.

THE CONTROL IS THE POINT
Every OTHER underdog on the same boards is graded too. "Good dogs lost money" and
"good dogs beat the alternative" can both be true, and the difference is the only
number that says whether the tag earns anything. Backing underdogs is a losing
activity on its own.

Writes output/good_dog_ledger.md.
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import good_dog, grade, mlb_api
from .record_audit import GOOD_DOG_SHIPPED

log = logging.getLogger("good_dog_ledger")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
RECENT = 25            # dogs listed individually at the end
TRIALS = 10000


def collect() -> tuple[list[dict], list[dict], list[str]]:
    """(good dogs, other underdogs, dates skipped for want of results)."""
    dogs: list[dict] = []
    ctrl: list[dict] = []
    skipped: list[str] = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            board = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        try:
            res = mlb_api.results_for(date)
        except Exception as exc:
            log.warning("results unavailable for %s (%s)", date, exc)
            skipped.append(date)
            continue
        if not res:
            skipped.append(date)
            continue
        rates = good_dog.favourite_rates(date)      # prior boards only
        graded_any = False
        for g in board.get("games", []):
            pc = g.get("pick_criteria") or {}
            m = g.get("matchup") or ""
            adv = pc.get("advantage_team")
            a, o = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if " @ " not in m or not adv or not isinstance(a, int) \
                    or not isinstance(o, int):
                continue
            away, home = m.split(" @ ")
            if adv not in (away, home):
                continue
            r = res.get(g.get("game_pk")) or {}
            winner = r.get("winner")
            if not r.get("final") or not winner:
                continue
            graded_any = True
            opp = home if adv == away else away
            price = {adv: a, opp: o}
            tag = good_dog.tag(g, rates)
            for team, odds in price.items():
                if odds <= 0:
                    continue                        # underdogs only
                won = team == winner
                row = {"date": date, "team": team, "odds": odds, "won": won,
                       "profit": grade.american_profit(odds) if won else -1.0,
                       "matchup": m, "play": pc.get("play"),
                       "bet_team": pc.get("bet_team")}
                if tag and tag["team"] == team:
                    row["rate"] = tag["rate"]
                    dogs.append(row)
                else:
                    ctrl.append(row)
        if not graded_any:
            skipped.append(date)
    dogs.sort(key=lambda r: r["date"])
    ctrl.sort(key=lambda r: r["date"])
    return dogs, ctrl, skipped


def _tally(rs: list[dict]) -> tuple[int, int, float, float]:
    w = sum(1 for r in rs if r["won"])
    u = sum(r["profit"] for r in rs)
    return w, len(rs) - w, u, (u / len(rs) if rs else 0.0)


def _fmt(rs: list[dict]) -> str:
    w, l, u, roi = _tally(rs)
    return f"{w}-{l} · {u:+.2f}u · **{roi:+.1%}** (n={len(rs)})" if rs else "— (0)"


def _curve(rs: list[dict]) -> tuple[float, float, str, float]:
    """(final units, worst drawdown, date of the trough, peak before it)."""
    run = peak = 0.0
    worst, worst_at, worst_peak = 0.0, "", 0.0
    for r in rs:
        run += r["profit"]
        peak = max(peak, run)
        if peak - run > worst:
            worst, worst_at, worst_peak = peak - run, r["date"], peak
    return run, worst, worst_at, worst_peak


def build() -> str:
    dogs, ctrl, skipped = collect()
    md = ["# Good dogs — the plain ledger", "",
          "_Every qualifying dog on every board, graded at the board's own price, "
          "$1 a bet. No cuts scanned, no cells: the tag's shipped definition "
          f"(favoured ≥ {good_dog.FAV_RATE:.0%} of PRIOR games, priced as a dog) "
          "applied to each board as it stood._", ""]
    if not dogs:
        return "\n".join(md + ["No graded good dogs found.", ""])

    md += [f"- graded good dogs: **{len(dogs)}**  ·  "
           f"first {dogs[0]['date']}, last {dogs[-1]['date']}",
           f"- board dates with no usable results: {len(skipped)}"
           + (f" ({', '.join(skipped[:8])}{'…' if len(skipped) > 8 else ''})"
              if skipped else ""), ""]

    units, dd, dd_at, dd_peak = _curve(dogs)
    w, l, u, roi = _tally(dogs)
    md += ["## Where we would be", "",
           "| | |", "|---|---|",
           f"| good dogs, backed flat | **{_fmt(dogs)}** |",
           f"| every OTHER underdog, same boards | {_fmt(ctrl)} |",
           f"| difference | **{(roi - _tally(ctrl)[3]) * 100:+.1f} points** |", "",
           f"- running balance ends at **{units:+.2f}u**",
           f"- worst drawdown **−{dd:.2f}u**, bottoming {dd_at} "
           f"(from a {dd_peak:+.2f}u peak)", ""]

    # is +/-roi distinguishable from break-even? one number, not a scan
    if len(dogs) >= 30:
        by_day = defaultdict(list)
        for r in dogs:
            by_day[r["date"]].append(r["profit"])
        allday = sorted(by_day)
        rng = random.Random(7)
        sims = []
        for _ in range(TRIALS):
            pool = []
            for _ in allday:
                pool += by_day[allday[rng.randrange(len(allday))]]
            if pool:
                sims.append(st.mean(pool) * 100)
        sims.sort()
        md += [f"- 95% interval on that ROI, resampling whole days: "
               f"**{sims[int(.025*len(sims))]:+.1f}% to "
               f"{sims[int(.975*len(sims))]:+.1f}%**"
               + ("  — spans zero, so flat is inside the range"
                  if sims[int(.025*len(sims))] < 0 < sims[int(.975*len(sims))]
                  else ""), ""]

    md += ["## Month by month", "", "| month | record | units | ROI | running |",
           "|---|---|---|---|---|"]
    bym = defaultdict(list)
    for r in dogs:
        bym[r["date"][:7]].append(r)
    run = 0.0
    for mth in sorted(bym):
        mw, ml, mu, mroi = _tally(bym[mth])
        run += mu
        md.append(f"| {mth} | {mw}-{ml} | {mu:+.2f}u | {mroi:+.1%} | {run:+.2f}u |")
    md.append("")

    pre = [r for r in dogs if r["date"] < GOOD_DOG_SHIPPED]
    post = [r for r in dogs if r["date"] >= GOOD_DOG_SHIPPED]
    md += ["## Before and after the tag shipped", "",
           f"_{GOOD_DOG_SHIPPED} is when the tag went on the board. Everything "
           "before it is the data the idea was found on; everything after is the "
           "only genuinely forward evidence there is._", "",
           f"- before: {_fmt(pre)}", f"- **after: {_fmt(post)}**", ""]

    md += [f"## The last {RECENT}, one row each", "",
           "| date | dog | price | fav rate | result | units |", "|---|---|---|---|---|---|"]
    run = 0.0
    for r in dogs[-RECENT:]:
        run += r["profit"]
        md.append(f"| {r['date']} | {r['team']} | {r['odds']:+d} | "
                  f"{r.get('rate', 0):.0%} | {'WON' if r['won'] else 'lost'} | "
                  f"{r['profit']:+.2f} |")
    md.append("")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    argparse.ArgumentParser().parse_args()
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "good_dog_ledger.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
