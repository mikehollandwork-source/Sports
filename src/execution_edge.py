"""
Three ways to make more money without finding a new edge.

WHY THIS ANGLE
Six separate edge hunts died out of sample. Rather than hunt a seventh, this
looks at execution - the money that is won or lost after the pick is already
decided. Nothing here needs a new signal to be true.

1. CLOSING LINE VALUE — the diagnostic this repo has been missing
   CLV asks whether the market moved TOWARD our side after we bet. It is the
   single most reliable predictor of long-run profit in betting, and crucially it
   barely depends on who won: a pick can lose and still have been a good bet at a
   good price. That makes CLV measurable on ~200 picks where ROI is hopeless -
   our ROI confidence intervals have been +/-20 points all session, while CLV
   converges far faster because it strips out the coin-flip.

   Read it like this: consistently POSITIVE CLV means the edge is real and
   variance is hiding it - keep going, bet bigger. Consistently NEGATIVE CLV
   means we are systematically buying prices the market disagrees with, and no
   amount of extra sample will rescue that.

   Kalshi's last pre-game candle is the closing price. Both sides are de-vigged
   against each other before comparing, since a sportsbook moneyline carries
   vig and a two-sided prediction market barely does - comparing them raw would
   manufacture fake CLV on every single bet.

2. CLV AS A FILTER — actionable if #1 holds
   If picks that beat the close win more than picks that do not, that is a rule
   requiring no new signal at all: skip the ones the market has moved against.

3. PRICE SHOPPING — free units, no prediction required
   We book the sportsbook price. If Kalshi's ask was cheaper on the same side,
   the difference is money left on the table for nothing. This is the only item
   here that is pure arithmetic with no inference in it.

Writes output/execution_edge.md.
"""

from __future__ import annotations

import glob
import json
import logging
import statistics as st
import time
from pathlib import Path

from . import grade, kalshi, mlb_api
from .analysis import _canon_abbr
from .pregame_money import (HOLDOUT_FROM, LOOKBACK, MIN_N, PACE, _candles,
                            _implied, _start_ts, settled_index)

log = logging.getLogger("execution_edge")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _close_prices(cs: list) -> tuple[float | None, float | None]:
    """(last mid/close price, last ask) from a candle series, or (None, None)."""
    price = ask = None
    for c in reversed(cs):
        if price is None:
            v = kalshi._num((c.get("price") or {}).get("close_dollars"))
            if v and 0 < v < 1:
                price = v
        if ask is None:
            v = kalshi._num((c.get("yes_ask") or {}).get("close_dollars"))
            if v and 0 < v < 1:
                ask = v
        if price is not None and ask is not None:
            break
    return price, ask


def collect() -> list:
    kmap = settled_index()
    recs = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        day = json.loads(Path(f).read_text())
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
            if chk.get("money") != "with public" or not maj:
                continue
            away, home = matchup.split(" @ ")
            adv = pc.get("advantage_team")
            if maj not in (away, home) or not adv:
                continue
            book_odds = (pc.get("advantage_moneyline") if maj == adv
                         else pc.get("opponent_moneyline"))
            other_odds = (pc.get("opponent_moneyline") if maj == adv
                          else pc.get("advantage_moneyline"))
            if not isinstance(book_odds, int) or not isinstance(other_odds, int):
                continue

            aa = _canon_abbr(g.get("away_abbr") or "")
            ha = _canon_abbr(g.get("home_abbr") or "")
            teams = kmap.get((date, frozenset({aa, ha}))) if aa and ha else None
            start = _start_ts(g.get("game_datetime"))
            if not teams or not start or len(teams) != 2:
                continue
            bet_ab = ha if maj == home else aa
            opp_ab = aa if bet_ab == ha else ha

            px = {}
            for ab in (bet_ab, opp_ab):
                cs = _candles(teams[ab]["ticker"], start - LOOKBACK, start)
                if not cs:
                    break
                p, a = _close_prices(cs)
                if p is None:
                    break
                px[ab] = {"close": p, "ask": a}
                time.sleep(PACE)
            if len(px) != 2:
                continue

            # de-vig BOTH sides before comparing - a book price carries vig, a
            # two-sided prediction market barely does
            b_imp, o_imp = _implied(book_odds), _implied(other_odds)
            tot_b = b_imp + o_imp
            k_tot = px[bet_ab]["close"] + px[opp_ab]["close"]
            if tot_b <= 0 or k_tot <= 0:
                continue
            our_fair = b_imp / tot_b
            close_fair = px[bet_ab]["close"] / k_tot

            recs.append({
                "date": date, "matchup": matchup, "bet": maj,
                "won": res["winner"] == maj,
                "book_odds": book_odds,
                "our_fair": our_fair, "close_fair": close_fair,
                "clv": close_fair - our_fair,
                "k_ask": px[bet_ab]["ask"],
                "was_pick": pc.get("play") == "pick",
            })
    return recs


def _fmt(rows) -> str:
    if not rows:
        return "—"
    w = sum(1 for x in rows if x["won"])
    u = sum(grade.american_profit(x["book_odds"]) if x["won"] else -1 for x in rows)
    tag = "" if len(rows) >= MIN_N else " _(thin)_"
    return (f"{w}-{len(rows)-w} · {u:+.1f}u · **{u/len(rows):+.1%}** "
            f"(n={len(rows)}){tag}")


def _clv_line(rows, label: str) -> str:
    if not rows:
        return f"| {label} | — | — | — |"
    cl = [r["clv"] for r in rows]
    pos = sum(1 for c in cl if c > 0)
    return (f"| {label} | **{st.mean(cl)*100:+.2f} pts** | "
            f"{pos}/{len(cl)} ({pos/len(cl):.0%}) | {_fmt(rows)} |")


def build() -> str:
    recs = collect()
    md = ["# Execution — making more without a new edge", "",
          "_Six edge hunts died out of sample. This looks instead at what "
          "happens after the pick is chosen: whether we are getting good prices, "
          "and whether the market agrees with us._", "",
          f"## Coverage", "",
          f"- games clearing the consensus gate with a Kalshi close: **{len(recs)}**",
          f"- of those, actual board picks: **{sum(1 for r in recs if r['was_pick'])}**", ""]
    if len(recs) < MIN_N:
        return "\n".join(md + ["Too few games to read.", ""])

    pre = [r for r in recs if r["date"] < HOLDOUT_FROM]
    post = [r for r in recs if r["date"] >= HOLDOUT_FROM]
    picks = [r for r in recs if r["was_pick"]]

    md += ["## 1. Closing line value", "",
           "_CLV = the de-vigged closing probability of our side minus the "
           "de-vigged price we booked. Positive means the market moved toward "
           "us. This is the low-variance read: it barely depends on who won._",
           "", "| population | mean CLV | % beating the close | actual ROI |",
           "|---|---|---|---|",
           _clv_line(recs, "all consensus-gate games"),
           _clv_line(pre, "in-sample (< 07-23)"),
           _clv_line(post, "holdout (>= 07-23)"),
           _clv_line(picks, "actual board picks"), ""]

    mean_all = st.mean(r["clv"] for r in recs) * 100
    if mean_all > 0.5:
        verdict = ("**Positive CLV.** The market moves toward our side after we "
                   "bet, which is the signature of a real edge being masked by "
                   "variance. This argues for staying the course and sizing up, "
                   "not for hunting another signal.")
    elif mean_all < -0.5:
        verdict = ("**Negative CLV.** We are systematically buying prices the "
                   "market then moves away from. No amount of extra sample fixes "
                   "this - it means the selection itself is behind the market, "
                   "and the fix has to be entering earlier or selecting "
                   "differently.")
    else:
        verdict = ("**CLV is roughly flat.** We are neither beating nor losing to "
                   "the close, which is what a breakeven-before-vig selection "
                   "looks like. The edge, if any, is small enough that price "
                   "execution matters as much as selection.")
    md += [verdict, ""]

    md += ["## 2. Does CLV predict the winner?", "",
           "_If picks that beat the close win more often, skipping the rest is a "
           "rule that needs no new signal._", "",
           "| bucket | result |", "|---|---|",
           f"| CLV positive (market moved to us) | {_fmt([r for r in recs if r['clv'] > 0])} |",
           f"| CLV negative (market moved away) | {_fmt([r for r in recs if r['clv'] <= 0])} |", ""]
    strong = [r for r in recs if r["clv"] > 0.02]
    weak = [r for r in recs if r["clv"] < -0.02]
    md += ["_Only decisive moves (2+ points of probability):_", "",
           "| bucket | result |", "|---|---|",
           f"| CLV > +2 pts | {_fmt(strong)} |",
           f"| CLV < -2 pts | {_fmt(weak)} |", "",
           "_Holdout on the same split:_", "",
           "| bucket | in-sample | holdout |", "|---|---|---|",
           f"| CLV positive | {_fmt([r for r in pre if r['clv'] > 0])} | "
           f"{_fmt([r for r in post if r['clv'] > 0])} |",
           f"| CLV negative | {_fmt([r for r in pre if r['clv'] <= 0])} | "
           f"{_fmt([r for r in post if r['clv'] <= 0])} |", ""]

    # ---- 3. price shopping: is the Kalshi ask cheaper than the book? ----
    shop = [r for r in recs if r.get("k_ask")]
    gained = 0.0
    better = 0
    for r in shop:
        book_profit = grade.american_profit(r["book_odds"])
        k_profit = (1 - r["k_ask"]) / r["k_ask"]
        if k_profit > book_profit:
            better += 1
        best = max(book_profit, k_profit)
        gained += (best - book_profit) if r["won"] else 0.0
    md += ["## 3. Price shopping — units left on the table", "",
           "_Pure arithmetic, no prediction: for each bet, was Kalshi's ask "
           "cheaper than the sportsbook price we booked?_", ""]
    if shop:
        md += [f"- bets with a Kalshi ask to compare: **{len(shop)}**",
               f"- Kalshi paid better: **{better}** ({better/len(shop):.0%})",
               f"- extra units from always taking the better price: "
               f"**{gained:+.2f}u** over {len(shop)} bets "
               f"(**{gained/len(shop):+.2%}** per bet)", "",
               "_This is additive to whatever the selection edge is - it costs "
               "nothing and risks nothing, since it is the same bet at a better "
               "price. Execution slippage and Kalshi's fees are not modelled "
               "here, so treat it as an upper bound._", ""]
    else:
        md += ["_No Kalshi ask data available._", ""]

    md.append("_CLV is the number to watch here. It is the one measurement in "
              "this repo that gives a usable read at this sample size._")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "execution_edge.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
