"""
Aggressive money flow per side, from Kalshi trade history.

WHY THIS IS DIFFERENT FROM VOLUME
Volume counts both sides of every trade - a buyer and a seller - so a team's
market volume measures interest in the matchup, not money backing that team.
That is why `pregame_money.md` carries a caveat it cannot resolve.

The trade feed exposes `taker_side`: who crossed the spread. The taker is the
one with conviction; the maker was sitting there. So aggressive notional is a
direct read of money PUSHING a side, which is the thing "which side is the
money on" actually means.

COMBINING THE TWO MARKETS
Each game has two markets, one per team, and they are economically redundant -
buying NO on the away team is buying the home team. Both are used:

    money_on(A) = yes-taker notional in A's market + no-taker notional in B's
    money_on(B) = yes-taker notional in B's market + no-taker notional in A's

Notional is count x the price the taker paid, so a big trade at 0.90 counts for
more than the same contract count at 0.10.

Trades are truncated at first pitch, so nothing in here is contaminated by the
game itself. Reuses pregame_money's controls verbatim - the favourite control,
the market-calibrated null, the holdout split and the day-block bootstrap - so
this result is held to the same bar that disqualified the volume version.

Writes output/taker_flow.md. Reporting only - nothing here feeds the board.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
import time
from collections import Counter
from pathlib import Path

import requests

from . import kalshi, mlb_api
from .analysis import _canon_abbr
from .pregame_money import (MIN_N, _controls, _fmt, _rows, _start_ts,
                            settled_index)

log = logging.getLogger("taker_flow")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TIMEOUT = 20
LOOKBACK = 86400          # 24h before first pitch, matching the candle window
PAGES = 8                 # max trade pages per market
PAGE_LIMIT = 1000
PACE = 0.2
MIN_NOTIONAL = 100.0      # skip games with almost no pre-game aggressive flow

STATUS = Counter()


def _num(v) -> float:
    n = kalshi._num(v)
    return n if n is not None else 0.0


def trades(ticker: str, min_ts: int, max_ts: int) -> list:
    """Pre-game trades for one market, paginated. [] on failure."""
    out, cursor = [], None
    for _ in range(PAGES):
        params = {"ticker": ticker, "limit": PAGE_LIMIT,
                  "min_ts": min_ts, "max_ts": max_ts}
        if cursor:
            params["cursor"] = cursor
        got = None
        for attempt in range(4):
            try:
                r = requests.get(f"{kalshi.BASE}/markets/trades", params=params,
                                 timeout=TIMEOUT,
                                 headers={"User-Agent": "mlb-edge-finder (research)"})
                STATUS[r.status_code] += 1
                if r.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                if not r.ok:
                    if attempt == 0:
                        log.warning("trades %s -> %s: %s", ticker,
                                    r.status_code, r.text[:160])
                    return out
                got = r.json() or {}
                break
            except Exception as exc:
                STATUS["exception"] += 1
                log.warning("trades failed (%s): %s", ticker, exc)
                return out
        if got is None:
            return out
        batch = got.get("trades") or []
        out.extend(batch)
        cursor = got.get("cursor")
        if not cursor or not batch:
            break
        time.sleep(PACE)
    return out


def _ts(iso) -> int | None:
    try:
        return int(dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


def _flow(tr: list, min_ts: int, max_ts: int) -> tuple[float, float]:
    """(yes-taker notional, no-taker notional) for one market's trades.

    Re-filters on created_time rather than trusting min_ts/max_ts to have been
    honoured - if the endpoint ignored them we would silently be counting
    in-game trades, which is exactly the contamination this module exists to
    avoid."""
    yes = no = 0.0
    for t in tr:
        ts = _ts(t.get("created_time"))
        if ts is None or ts < min_ts or ts >= max_ts:
            continue
        n = _num(t.get("count_fp"))
        if n <= 0:
            continue
        if (t.get("taker_side") or "").lower() == "yes":
            yes += n * _num(t.get("yes_price_dollars"))
        else:
            no += n * _num(t.get("no_price_dollars"))
    return yes, no


def collect() -> tuple[list, dict]:
    kmap = settled_index()
    recs, diag = [], {"matched": 0, "thin": 0, "no_trades": 0}

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
            if " @ " not in (g.get("matchup") or ""):
                continue
            aa = _canon_abbr(g.get("away_abbr") or "")
            ha = _canon_abbr(g.get("home_abbr") or "")
            teams = kmap.get((date, frozenset({aa, ha}))) if aa and ha else None
            if not teams or len(teams) != 2:
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            start = _start_ts(g.get("game_datetime"))
            if not start:
                continue
            diag["matched"] += 1

            # yes/no aggressive notional in each team's own market
            side_flow = {}
            for ab, info in teams.items():
                tr = trades(info["ticker"], start - LOOKBACK, start)
                if not tr:
                    continue
                side_flow[ab] = _flow(tr, start - LOOKBACK, start)
                time.sleep(PACE)
            if len(side_flow) != 2:
                diag["no_trades"] += 1
                continue

            x, y = list(side_flow)
            # money on X = takers buying X's YES + takers buying Y's NO
            money = {x: side_flow[x][0] + side_flow[y][1],
                     y: side_flow[y][0] + side_flow[x][1]}
            if sum(money.values()) < MIN_NOTIONAL:
                diag["thin"] += 1
                continue

            away, home = g["matchup"].split(" @ ")
            opp = home if adv == away else away
            recs.append({
                "date": date, "winner": res["winner"], "adv": adv, "opp": opp,
                "price": {adv: a_ml, opp: o_ml},
                "name": {aa: away, ha: home},
                # shaped like pregame_money's recs so _sides/_controls work as-is
                "pre": {ab: {"taker": v} for ab, v in money.items()},
            })
    return recs, diag


def build() -> str:
    recs, diag = collect()
    mode = "taker"
    md = ["# Aggressive money per side (Kalshi taker flow)", "",
          "_Who crossed the spread, pre-game. Unlike volume - which counts both "
          "the buyer and the seller of every trade - taker notional is a direct "
          "read of money pushing a side. Both of a game's markets are combined: "
          "money on a team = YES takers in its own market + NO takers in its "
          "opponent's._", "",
          "## Coverage", "",
          f"- games matched: **{diag['matched']}**",
          f"- usable: **{len(recs)}**",
          f"- dropped, no trades: **{diag['no_trades']}**",
          f"- dropped, under ${MIN_NOTIONAL:.0f} pre-game flow: **{diag['thin']}**", "",
          "_Trade fetch outcomes: " +
          (", ".join(f"`{k}` {v}" for k, v in STATUS.most_common()) or "none") +
          "._", ""]

    if len(recs) < MIN_N:
        return "\n".join(md + ["## Verdict", "",
                               f"Only **{len(recs)}** usable games, below "
                               f"**{MIN_N}**. Counts only.", ""])

    md += ["## Does the aggressive-money side win?", "",
           "| strategy | result |", "|---|---|",
           f"| back the MORE aggressive-money side | {_fmt(_rows(recs, mode, 'more'))} |",
           f"| back the LESS aggressive-money side | {_fmt(_rows(recs, mode, 'less'))} |", ""]

    for lo, label in ((0.60, "60%+"), (0.70, "70%+")):
        gate = lambda s, lo=lo: s is not None and s >= lo
        md += [f"_Lopsided — one side holds {label} of aggressive flow:_", "",
               "| strategy | result |", "|---|---|",
               f"| back the MORE side | {_fmt(_rows(recs, mode, 'more', gate))} |",
               f"| back the LESS side | {_fmt(_rows(recs, mode, 'less', gate))} |", ""]

    md += _controls(recs, mode)
    md.append("_Same bar as the volume version: the favourite control decides "
              "whether this is an edge or a repriced favourite, and the "
              "favourite/dog split shows how many games actually carry it._")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "taker_flow.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
