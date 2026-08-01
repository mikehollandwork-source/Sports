"""
The dog-money signal, on the widest sample available.

THE FINDING THIS CHASES
pregame_money found that backing the side with more pre-game Kalshi volume
returns ~0% when that side is the favourite (140 games) but +40.2% when it is
the DOG (29 games). 29 games is far too thin to act on - it is the same shape as
the reversal rule that shipped at +25% in-sample and went -41% live.

HOW THE SAMPLE GETS BIGGER
pregame_money could only use games that appear in our own picks_*.json files
with sportsbook moneylines on both sides: 343 of the 852 complete two-sided
games Kalshi has settled. Everything needed is actually inside Kalshi:

  * the ticker encodes both teams AND the start time in ET
    'KXMLBGAME-26JUL312210BOSLAD-LAD' -> Jul 31, 22:10 ET, BOS at LAD, LAD's market
  * `result` on each team's settled market says who won
  * candles give pre-game volume and the pre-game price

So this needs no picks file, no MLB API and no sportsbook line, and covers every
game Kalshi has. Grading at Kalshi's own price is also the more honest test for
a Polymarket/Kalshi bot, since that is the price it would actually pay.

EXECUTION REALISM
The close price is a mid, not a fill. Results are reported both at the close and
with a one-cent haircut, because an edge that only exists at the mid is not an
edge you can trade.

Prices are converted to American odds so pregame_money's controls - the
favourite control, market-calibrated null, holdout split and day-block
bootstrap - apply unchanged. Writes output/dog_money.md.
"""

from __future__ import annotations

import datetime as dt
import logging
import re
import time
import zoneinfo
from pathlib import Path

from . import kalshi
from .pregame_money import (LOOKBACK, MIN_N, PACE, STATUS, _candles, _controls,
                            _vol)

log = logging.getLogger("dog_money")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
HAIRCUT = 0.01           # one cent of slippage against us on entry

# 'KXMLBGAME-26JUL312210BOSLAD-LAD' -> 26 JUL 31, 22:10 ET
_TICKER = re.compile(r"-(\d{2})([A-Z]{3})(\d{2})(\d{2})(\d{2})")
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}


def ticker_start(ticker: str):
    """(date_iso, unix_ts) of first pitch from the ticker, or (None, None)."""
    m = _TICKER.search(ticker or "")
    if not m:
        return None, None
    yy, mon, dd, hh, mi = m.groups()
    mo = _MONTHS.get(mon)
    if not mo:
        return None, None
    try:
        d = dt.datetime(2000 + int(yy), mo, int(dd), int(hh), int(mi), tzinfo=EASTERN)
    except ValueError:
        return None, None
    return d.date().isoformat(), int(d.timestamp())


def _american(p: float) -> int:
    """Decimal probability -> American odds, so the shared controls apply."""
    p = min(max(p, 0.01), 0.99)
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def collect() -> tuple[list, dict]:
    """One rec per game, from Kalshi alone."""
    by_event: dict = {}
    for m in kalshi.settled_markets():
        tk, ev = m.get("ticker"), m.get("event_ticker")
        team = kalshi._abbr(tk) if tk else None
        if not (tk and ev and team):
            continue
        by_event.setdefault(ev, {})[team] = {
            "ticker": tk, "result": (m.get("result") or "").lower()}

    recs, diag = [], {"events": len(by_event), "no_start": 0, "no_result": 0,
                      "no_candles": 0, "tied": 0}

    for teams in by_event.values():
        if len(teams) != 2:
            continue
        abbrs = list(teams)
        # winner straight off the settled markets
        winners = [ab for ab in abbrs if teams[ab]["result"] == "yes"]
        losers = [ab for ab in abbrs if teams[ab]["result"] == "no"]
        if len(winners) != 1 or len(losers) != 1:
            diag["no_result"] += 1
            continue
        date, start = ticker_start(teams[abbrs[0]]["ticker"])
        if not start:
            diag["no_start"] += 1
            continue

        pre = {}
        for ab in abbrs:
            cs = _candles(teams[ab]["ticker"], start - LOOKBACK, start)
            if not cs:
                continue
            price = None
            for c in reversed(cs):          # last candle with a real close
                v = kalshi._num((c.get("price") or {}).get("close_dollars"))
                if v and 0 < v < 1:
                    price = v
                    break
            if price is None:
                continue
            pre[ab] = {"vol": sum(_vol(c) for c in cs), "price": price}
            time.sleep(PACE)
        if len(pre) != 2:
            diag["no_candles"] += 1
            continue
        if pre[abbrs[0]]["vol"] == pre[abbrs[1]]["vol"]:
            diag["tied"] += 1
            continue

        # de-vig the two YES prices against each other
        tot = pre[abbrs[0]]["price"] + pre[abbrs[1]]["price"]
        if tot <= 0:
            continue
        recs.append({
            "date": date, "winner": winners[0],
            "adv": abbrs[0], "opp": abbrs[1],
            "name": {ab: ab for ab in abbrs},
            "price": {ab: _american(pre[ab]["price"] / tot) for ab in abbrs},
            "raw_price": {ab: pre[ab]["price"] for ab in abbrs},
            "pre": {ab: {"vol": pre[ab]["vol"]} for ab in abbrs},
        })
    return recs, diag


def _dog_rows(recs, thresh: float, haircut: float) -> list:
    """Games where the MORE-money side is the dog, at a lopsidedness threshold."""
    from .pregame_money import _devig, _sides

    out = []
    for r in recs:
        more, _less, share = _sides(r, "vol")
        if not more or share is None or share < thresh:
            continue
        if _devig(r, more) > 0.5:          # money is on the favourite - not this set
            continue
        p = min(r["raw_price"][more] + haircut, 0.99)
        out.append({"won": r["winner"] == more, "profit": (1 - p) / p})
    return out


def _fmt_dec(rows) -> str:
    if not rows:
        return "—"
    w = sum(1 for x in rows if x["won"])
    u = sum(x["profit"] if x["won"] else -1 for x in rows)
    tag = "" if len(rows) >= MIN_N else " _(thin)_"
    return (f"{w}-{len(rows)-w} ({w/len(rows):.0%}) · {u:+.1f}u · "
            f"**{u/len(rows):+.1%}** (n={len(rows)}){tag}")


def build() -> str:
    recs, diag = collect()
    md = ["# Dog money — widest available sample", "",
          "_Every complete two-sided game Kalshi has settled, using Kalshi alone: "
          "the ticker gives the teams and first pitch, `result` gives the winner, "
          "candles give pre-game volume and price. No picks file, no sportsbook "
          "line - so this is not limited to days we ran a board._", "",
          "## Coverage", "",
          f"- two-sided settled events: **{diag['events']}**",
          f"- usable games: **{len(recs)}**",
          f"- dropped (no candles {diag['no_candles']}, no result "
          f"{diag['no_result']}, no start {diag['no_start']}, tied volume "
          f"{diag['tied']})", "",
          "_Candle fetch outcomes: " +
          (", ".join(f"`{k}` {v}" for k, v in STATUS.most_common()) or "none") +
          "._", ""]

    if len(recs) < MIN_N:
        return "\n".join(md + ["## Verdict", "", "Too few games to read.", ""])

    md += ["## The dog subset, by lopsidedness threshold", "",
           "_Backing the side with more pre-game volume, only when that side is "
           "the price underdog. Graded at the Kalshi close, and again with a "
           "one-cent entry haircut - an edge that only exists at the mid is not "
           "tradeable._", "",
           "| min share | at close | with 1c haircut |", "|---|---|---|"]
    for t in (0.55, 0.60, 0.65, 0.70, 0.75, 0.80):
        md.append(f"| {t:.0%} | {_fmt_dec(_dog_rows(recs, t, 0.0))} | "
                  f"{_fmt_dec(_dog_rows(recs, t, HAIRCUT))} |")
    md.append("")

    md += _controls(recs, "vol")
    md.append("_A flat profile across thresholds is the encouraging shape; a "
              "spike at one threshold that vanishes either side of it is the "
              "signature of fitting noise._")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "dog_money.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
