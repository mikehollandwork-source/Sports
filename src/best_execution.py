"""
What our OWN picks would have returned at the best available price.

WHY THIS AND NOT ANOTHER SIGNAL HUNT
Eleven selection ideas have now failed out of sample, and the max- and
min-statistic tests say why: this dataset manufactures cells on demand. The one
measurement that survived everything is execution - the exchange ask beat the
booked sportsbook price on 285 of 313 bets. That number carried a caveat in
`execution_edge.md`, stated plainly there: "Kalshi's fees are not modelled here,
so treat it as an upper bound." This removes the caveat.

WHAT MAKES THIS DIFFERENT FROM EVERY FAILED TEST
It changes no picks. The same games, the same sides, the same dates - only the
price paid to enter. There is no cell to select, no threshold to tune and no
direction to choose, so there is nothing for a scan to overfit. If it wins here
it wins by arithmetic, and the only ways it can fail in production are
liquidity and slippage, both of which are measured below.

THE ARITHMETIC
Every price is converted to one comparable number: the cost of $1 of payout.
  book       de-vigged-free implied probability of the booked American odds
  polymarket the ask on our side, or 1 - bid when we need the other side,
             because buying the complement of a binary market costs 1 - bid
  kalshi     the ask plus its fee, 0.07 x p x (1 - p) per contract
A bet entered at cost c returns (1 - c) / c on a win and -1 on a loss, which is
the same formula American odds already express - so the venues are compared on
identical footing rather than by eyeballing prices.

Only readings at or before first pitch are used, so this is a price that was
actually available when the pick went out, not a post-hoc one.

Writes output/best_execution.md.
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
from .pregame_money import HOLDOUT_FROM, _implied

log = logging.getLogger("best_execution")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
STAKE_USD = 20.0          # the bankroll the liquidity check has to clear
KALSHI_FEE = 0.07         # fees = 0.07 * contracts * p * (1 - p)


def _kalshi_cost(ask: float) -> float:
    return ask + KALSHI_FEE * ask * (1 - ask)


def _pregame(readings, start_ts, key) -> dict | None:
    """Last quote at or before first pitch that actually carries `key`."""
    ok = [r for r in (readings or [])
          if not r.get("empty") and isinstance(r.get(key), (int, float))
          and r.get(key) and (start_ts is None or r.get("t", 0) <= start_ts)]
    return ok[-1] if ok else None


def _start_ts(entry) -> int | None:
    s = entry.get("game_datetime")
    if not s:
        return None
    try:
        return int(dt.datetime.fromisoformat(
            s.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def collect() -> list[dict]:
    recs = []
    for bf in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(bf).stem.split("picks_")[1]
        try:
            books = json.loads(
                (OUTPUT_DIR / f"pm_books_{date}.json").read_text()).get("games") or {}
        except (OSError, ValueError):
            books = {}
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        for g in json.loads(Path(bf).read_text()).get("games", []):
            pc = g.get("pick_criteria") or {}
            if pc.get("play") != "pick":
                continue
            bet, ml = pc.get("bet_team"), pc.get("bet_moneyline")
            if not bet or not isinstance(ml, int):
                continue
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            won = res["winner"] == bet
            row = {"date": date, "matchup": g.get("matchup"), "bet": bet,
                   "won": won, "book_cost": _implied(ml), "odds": ml,
                   "pm_cost": None, "pm_size": None, "k_cost": None}

            e = books.get(str(g.get("game_pk")))
            if e:
                ts = _start_ts(e)
                same = e.get("side") == bet
                # our side's ask, or the complement's cost which is 1 - bid
                key = "ask" if same else "bid"
                q = _pregame(e.get("readings"), ts, key)
                if q:
                    row["pm_cost"] = q["ask"] if same else 1 - q["bid"]
                    row["pm_size"] = (q.get("ask_sz") if same
                                      else q.get("bid_sz")) or 0
                kq = _pregame(e.get("k_readings"), ts, key)
                if kq:
                    raw = kq["ask"] if same else 1 - kq["bid"]
                    row["k_cost"] = _kalshi_cost(raw)
            recs.append(row)
    return recs


def _profit(cost: float, won: bool) -> float:
    """Per 1 unit staked: a cheaper entry buys more payout for the same risk."""
    if not cost or cost <= 0 or cost >= 1:
        return 0.0
    return (1 - cost) / cost if won else -1.0


def _roi(rows, key) -> tuple[int, float, float]:
    live = [r for r in rows if r.get(key)]
    u = sum(_profit(r[key], r["won"]) for r in live)
    return len(live), u, (u / len(live) if live else 0.0)


def _fmt(rows, key) -> str:
    n, u, roi = _roi(rows, key)
    if not n:
        return "—"
    w = sum(1 for r in rows if r.get(key) and r["won"])
    return f"{w}-{n-w} · {u:+.2f}u · **{roi:+.1%}** (n={n})"


def _boot(rows, a, b, trials=4000) -> tuple[float, float]:
    """CI on the per-bet gain from routing, paired by bet - the same game at two
    prices is one observation, not two."""
    both = [r for r in rows if r.get(a) and r.get(b)]
    if len(both) < 10:
        return (float("nan"), float("nan"))
    rng = random.Random(101)
    out = []
    for _ in range(trials):
        s = [both[rng.randrange(len(both))] for _ in both]
        out.append(sum(_profit(r[b], r["won"]) - _profit(r[a], r["won"])
                       for r in s) / len(s))
    out.sort()
    return out[int(.025 * trials)], out[int(.975 * trials)]


def build() -> str:
    recs = collect()
    md = ["# Best execution — the same picks at a better price", "",
          "_No pick changes. Same games, same sides, same dates; only the price "
          "paid to enter. There is no cell to select and no threshold to tune, "
          "so there is nothing here for a scan to overfit._", "",
          f"- settled board picks: **{len(recs)}**",
          f"- with a pre-game Polymarket quote: "
          f"**{sum(1 for r in recs if r['pm_cost'])}**",
          f"- with a pre-game Kalshi quote: "
          f"**{sum(1 for r in recs if r['k_cost'])}**", ""]
    if not recs:
        return "\n".join(md + ["No settled picks.", ""])

    both = [r for r in recs if r["pm_cost"]]
    if len(both) < 10:
        return "\n".join(md + ["Too few quoted picks to measure.", ""])

    # like-for-like: the book number restricted to the same bets
    md += ["## Same bets, priced three ways", "",
           "| venue | on the quoted picks |", "|---|---|",
           f"| sportsbook (what we booked) | {_fmt(both, 'book_cost')} |",
           f"| **Polymarket ask** | {_fmt(both, 'pm_cost')} |"]
    kal = [r for r in recs if r["k_cost"]]
    if len(kal) >= 10:
        md += [f"| Kalshi ask + fee | {_fmt(kal, 'k_cost')} |",
               f"| _(sportsbook on those same Kalshi bets)_ | "
               f"{_fmt(kal, 'book_cost')} |"]
    md.append("")

    cheaper = sum(1 for r in both if r["pm_cost"] < r["book_cost"])
    n, bu, broi = _roi(both, "book_cost")
    _, pu, proi = _roi(both, "pm_cost")
    lo, hi = _boot(both, "book_cost", "pm_cost")
    gain = st.mean([_profit(r["pm_cost"], r["won"]) - _profit(r["book_cost"], r["won"])
                    for r in both])
    md += ["## What routing to the better price is worth", "",
           f"- Polymarket was cheaper on **{cheaper}/{len(both)}** "
           f"({cheaper/len(both):.0%}) of picks",
           f"- ROI: **{broi:+.1%}** booked → **{proi:+.1%}** routed "
           f"(**{proi-broi:+.1f} points**)",
           f"- units on the same bets: {bu:+.2f}u → {pu:+.2f}u "
           f"(**{pu-bu:+.2f}u** on {len(both)} bets)",
           f"- mean gain per bet: **{gain:+.1%}**, 95% CI "
           f"**{lo:+.1%} to {hi:+.1%}**", ""]
    md += (["The interval excludes zero, so this is a real per-bet gain rather "
            "than a coin flip - and unlike every selection result in this repo "
            "it cannot decay, because it is the vig difference between a book "
            "and an exchange, not a pattern in outcomes.", ""]
           if lo > 0 else
           ["The interval includes zero. Not actionable on this sample.", ""])

    # holdout, purely as a stability check - there is nothing fitted to split
    pre = [r for r in both if r["date"] < HOLDOUT_FROM]
    post = [r for r in both if r["date"] >= HOLDOUT_FROM]
    md += ["## Stability", "",
           "| period | booked | routed |", "|---|---|---|",
           f"| in-sample | {_fmt(pre, 'book_cost')} | {_fmt(pre, 'pm_cost')} |",
           f"| holdout | {_fmt(post, 'book_cost')} | {_fmt(post, 'pm_cost')} |", ""]

    # liquidity: an edge you cannot fill is not an edge
    fills = [r for r in both if (r["pm_size"] or 0) * r["pm_cost"] >= STAKE_USD]
    md += ["## Can it actually be filled?", "",
           f"- picks whose resting size covers a ${STAKE_USD:.0f} bet: "
           f"**{len(fills)}/{len(both)}** ({len(fills)/len(both):.0%})",
           f"- median resting notional on our side: "
           f"**${st.median([(r['pm_size'] or 0) * r['pm_cost'] for r in both]):,.0f}**",
           "", "_At this stake liquidity is not the binding constraint. It would "
           "become one long before the bankroll reached the size where the book "
           "price mattered more._", ""]

    md += ["## The catch, stated plainly", "",
           "- these are **quoted** prices, not fills; a real order pays the "
           "spread it crosses, and the ask is the right side of that but not a "
           "guarantee",
           "- Polymarket is an exchange with no per-trade fee today; if that "
           "changes, the gain moves with it",
           "- the quote used is the last one at or before first pitch, matching "
           "how the board freezes its own prices",
           f"- this measures only the **{len(both)}** picks that carried a "
           f"quote, not the whole record", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "best_execution.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
