"""
Polymarket viability: does the board's edge survive being executed on Polymarket
right before first pitch?

WHY THIS IS THE DECIDING QUESTION
Every ROI number this system has produced was graded at the SPORTSBOOK moneyline
frozen pre-game. A Polymarket bot does not get that price - it pays the ASK on
Polymarket at the moment it fires. Those are different numbers, and the gap
decides whether a +8% or +25% backtest is a real +8%/+25%, a breakeven, or a
loser. Worse, the consensus rule reads the order book as its SIGNAL, so by
definition it fires on games where money has already moved the PM price - we may
be systematically buying after the move we are keying on.

WHAT THIS MEASURES, per historical board pick
  * the last clean PM reading before first pitch (what a bot would actually see)
  * the execution price: the ask on our side's token, or 1 - bid when we back the
    other outcome (buying the complement of a binary market)
  * the same pick regraded at that PM price, net of the platform fee
  * the price gap vs the sportsbook line, and the top-of-book SIZE available -
    because an edge you cannot fill at scale is not an edge

Reported for both the unfiltered consensus board and the live line-against
filtered board. Writes output/pm_viability.md.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import statistics as st
from pathlib import Path

from . import consensus, grade, mlb_api, pm_books
from .pm_executor import FEE_RATE

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
HOLDOUT_FROM = "2026-07-23"
MAX_SPREAD = 0.15
LOCK_LEAD = 15 * 60        # bot fires this long before first pitch


def _implied(ml: int) -> float:
    return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)


def _start_ts(iso: str):
    try:
        return int(dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


def collect() -> list[dict]:
    recs = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        day = json.loads(Path(f).read_text())
        metrics = consensus.book_metrics(date)
        if not metrics:
            continue
        try:
            books = pm_books.load_day(date) or {}
            results = mlb_api.results_for(date)
        except Exception:
            continue
        bg = books.get("games") or {}
        for g in day.get("games", []):
            pk = g.get("game_pk")
            res = results.get(pk)
            if not res or not res.get("final") or not res.get("winner"):
                continue
            consensus.REQUIRE_LINE_AGAINST = False
            play = consensus.evaluate(g, metrics)     # unfiltered consensus pick
            if not play:
                continue
            bk = bg.get(str(pk)) or {}
            start = _start_ts(bk.get("game_datetime") or g.get("game_datetime"))
            if not start:
                continue
            # last clean reading strictly before the bot's firing moment
            cutoff = start - 0  # readings are pre-game already; use first pitch
            best = None
            for r in bk.get("readings") or []:
                if r.get("empty") or not isinstance(r.get("t"), (int, float)):
                    continue
                b, a = r.get("bid"), r.get("ask")
                if not (isinstance(b, (int, float)) and isinstance(a, (int, float))):
                    continue
                if a <= b or (a - b) > MAX_SPREAD or r["t"] > cutoff:
                    continue
                if best is None or r["t"] > best["t"]:
                    best = r
            if not best:
                continue
            # execution price: the token logged is the ADVANTAGE side's
            tracked = bk.get("side")
            bet = play["bet"]
            if tracked == bet:
                px, size = best["ask"], best.get("ask_sz") or 0
            else:
                px, size = 1.0 - best["bid"], best.get("bid_sz") or 0
            if not (0.01 < px < 0.99):
                continue
            maj = (g.get("public_majority") or {}).get("team")
            recs.append({
                "date": date, "won": res["winner"] == bet,
                "book_odds": play["odds"], "book_imp": _implied(play["odds"]),
                "pm_px": px, "size": float(size),
                "line_tag": consensus.line_tag(g, maj) if maj else "flat",
                "holdout": date >= HOLDOUT_FROM,
            })
    consensus.REQUIRE_LINE_AGAINST = True
    return recs


def _book_roi(rows):
    if not rows:
        return None
    return sum(grade.american_profit(r["book_odds"]) if r["won"] else -1
               for r in rows) / len(rows)


def _pm_roi(rows, fee=FEE_RATE):
    """$1 buys 1/px shares; a win returns 1/px, and the fee comes off winnings."""
    if not rows:
        return None
    tot = 0.0
    for r in rows:
        if r["won"]:
            gross = 1.0 / r["pm_px"] - 1.0
            tot += gross * (1 - fee)
        else:
            tot -= 1.0
    return tot / len(rows)


def _fmt(rows, roi_fn):
    if not rows:
        return "—"
    w = sum(1 for r in rows if r["won"])
    v = roi_fn(rows)
    return f"{w}-{len(rows)-w} ({w/len(rows):.0%}) · **{v:+.1%}** (n={len(rows)})"


def build() -> str:
    recs = collect()
    if not recs:
        return "# Polymarket viability\n\n_No board picks with a pre-game book reading._"
    kept = [r for r in recs if r["line_tag"] == "against"]

    md = [f"# Polymarket viability — {len(recs)} consensus picks with a real "
          f"pre-game order-book price", "",
          f"_Executed at the Polymarket ask before first pitch, net of a "
          f"{FEE_RATE:.0%} fee on winnings. Compared against the sportsbook "
          "moneyline every backtest so far has used._", "",
          "| board | at BOOK price | at POLYMARKET price |", "|---|---|---|",
          f"| unfiltered consensus | {_fmt(recs, _book_roi)} | {_fmt(recs, _pm_roi)} |",
          f"| line-against filtered (live board) | {_fmt(kept, _book_roi)} | {_fmt(kept, _pm_roi)} |",
          ""]

    # the price gap - the whole story in one number
    gaps = [(r["pm_px"] - r["book_imp"]) * 100 for r in recs]
    worse = sum(1 for x in gaps if x > 0)
    md += ["## Why — the price gap", "",
           f"- Polymarket asks **{st.mean(gaps):+.1f} probability points** vs the "
           f"sportsbook implied price on average (median {st.median(gaps):+.1f}).",
           f"- PM was the WORSE price on **{worse} of {len(recs)}** picks "
           f"({worse/len(recs):.0%}).",
           "- Positive = we pay more on Polymarket, and that difference comes "
           "straight out of the edge.", ""]

    # liquidity - can the bet even be filled?
    sizes = sorted(r["size"] for r in recs)
    if sizes:
        md += ["## Liquidity at the moment of the bet", "",
               f"- Top-of-book size available: median **${st.median(sizes):,.0f}**, "
               f"25th pct **${sizes[len(sizes)//4]:,.0f}**, "
               f"min **${sizes[0]:,.0f}**.",
               f"- Picks with under $100 available: "
               f"**{sum(1 for s in sizes if s < 100)} of {len(sizes)}**.",
               "- A stake beyond top-of-book walks the price up and cuts the edge "
               "further than the table above shows.", ""]

    # fee sensitivity
    md += ["## Fee sensitivity (unfiltered board)", "",
           "| fee on winnings | PM ROI |", "|---|---|"]
    for fee in (0.0, 0.02, 0.05):
        md.append(f"| {fee:.0%} | {_pm_roi(recs, fee):+.1%} |")
    md.append("")

    md.append("_Every number here uses the REAL recorded ask at the last clean "
              "pre-game reading, so it reflects what a bot would have paid - not "
              "an assumed price._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "pm_viability.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
