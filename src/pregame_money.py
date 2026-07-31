"""
PRE-GAME money per side on Kalshi - the version that isn't contaminated by the
game itself.

WHY THIS EXISTS
venue_volume.py compared each team's TOTAL settled volume and found nothing
(back-more-money -3.4%, back-less -5.5% over 343 games). But a settled market's
total volume includes every in-game trade, and in-game trading is driven by the
score. A team that goes down 5-0 and rallies generates huge volume BECAUSE of
what happened - so "which side had more money" on a settled market is largely a
readout of the game, not of pre-game conviction. That is not the signal we want.

Candlesticks fix it: they are a per-period time series, so volume can be cut off
at first pitch. What is left is money that arrived while the outcome was still
unknown - which is the thing actually worth testing.

CUMULATIVE-OR-PER-PERIOD
The candle `volume_fp` field could be either. Rather than guess, this checks a
sample of markets both ways against the market's known total volume and uses
whichever reconciles, reporting the finding.

Writes output/pregame_money.md. Reporting only - nothing here feeds the board.
"""

from __future__ import annotations

import glob
import json
import logging
import time
from collections import Counter
from pathlib import Path

import requests

from . import grade, kalshi, mlb_api
from .analysis import _canon_abbr
from .venue_volume import _ticker_date

log = logging.getLogger("pregame_money")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TIMEOUT = 20
MIN_N = 30
# 24h exactly: the probe confirmed this window returns 24 candles on markets of
# every age, from June through July. A 3-day window returned nothing, and the
# last 24h before first pitch is the pre-game money we actually want.
LOOKBACK = 86400
PERIOD = 60                   # minutes per candle
MAX_GAMES = 400               # hard cap on API work
PACE = 0.25                   # seconds between candle calls

STATUS = Counter()            # what the endpoint actually returned, for diagnosis


def _candles(ticker: str, start_ts: int, end_ts: int) -> list:
    """Hourly candles for a market, or [] on any failure. Retries on 429 - a
    burst of several hundred calls is exactly what a rate limiter exists for,
    and a silent [] there would look identical to 'no data'."""
    url = f"{kalshi.BASE}/series/{kalshi.SERIES}/markets/{ticker}/candlesticks"
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=TIMEOUT,
                             params={"start_ts": start_ts, "end_ts": end_ts,
                                     "period_interval": PERIOD},
                             headers={"User-Agent": "mlb-edge-finder (research)"})
            STATUS[r.status_code] += 1
            if r.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            if not r.ok:
                if attempt == 0:
                    log.warning("candles %s -> %s: %s", ticker,
                                r.status_code, r.text[:160])
                return []
            cs = (r.json() or {}).get("candlesticks") or []
            if not cs:
                STATUS["ok_but_empty"] += 1
            return cs
        except Exception as exc:
            STATUS["exception"] += 1
            log.warning("candles failed (%s): %s", ticker, exc)
            return []
    return []


def _vol(c: dict) -> float:
    v = kalshi._num(c.get("volume_fp"))
    return v if v is not None else 0.0


def settled_index() -> dict:
    """{(date, frozenset{abbr,abbr}): {abbr: {ticker, total_volume}}}"""
    by_event: dict = {}
    for m in kalshi.settled_markets():
        tk, ev = m.get("ticker"), m.get("event_ticker")
        team = kalshi._abbr(tk) if tk else None
        if not (tk and ev and team):
            continue
        by_event.setdefault(ev, {"date": _ticker_date(tk), "teams": {}})
        by_event[ev]["teams"][team] = {
            "ticker": tk, "total_volume": kalshi.market_money(m).get("volume"),
        }
    out = {}
    for d in by_event.values():
        if len(d["teams"]) == 2 and d["date"]:
            out[(d["date"], frozenset(d["teams"]))] = d["teams"]
    return out


def _start_ts(iso) -> int | None:
    import datetime as dt
    try:
        return int(dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


def collect() -> tuple[list, dict]:
    kmap = settled_index()
    recs, diag = [], {"matched": 0, "no_candles": 0, "no_start": 0,
                      "cum_hits": 0, "sum_hits": 0, "checked": 0}

    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        day = json.loads(Path(f).read_text())
        for g in day.get("games", []):
            if len(recs) >= MAX_GAMES:
                break
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            if " @ " not in (g.get("matchup") or ""):
                continue
            aa, ha = _canon_abbr(g.get("away_abbr") or ""), _canon_abbr(g.get("home_abbr") or "")
            teams = kmap.get((date, frozenset({aa, ha}))) if aa and ha else None
            if not teams:
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            start = _start_ts(g.get("game_datetime"))
            if not start:
                diag["no_start"] += 1
                continue
            diag["matched"] += 1

            pre = {}
            for ab, info in teams.items():
                cs = _candles(info["ticker"], start - LOOKBACK, start)
                if not cs:
                    continue
                vols = [_vol(c) for c in cs]
                # reconcile against the market total to learn the field's meaning
                total = info.get("total_volume")
                if total and diag["checked"] < 40:
                    diag["checked"] += 1
                    if abs(vols[-1] - total) < abs(sum(vols) - total):
                        diag["cum_hits"] += 1
                    else:
                        diag["sum_hits"] += 1
                pre[ab] = {"last": vols[-1], "sum": sum(vols)}
                time.sleep(PACE)

            if len(pre) != 2:
                diag["no_candles"] += 1
                continue
            away, home = g["matchup"].split(" @ ")
            opp = home if adv == away else away
            recs.append({
                "date": date, "winner": res["winner"], "adv": adv, "opp": opp,
                "price": {adv: a_ml, opp: o_ml},
                "name": {aa: away, ha: home}, "pre": pre,
            })
    return recs, diag


def _sides(r: dict, mode: str):
    """(more_money_team, less_money_team, share) using the chosen volume mode."""
    v = {ab: d[mode] for ab, d in r["pre"].items()}
    hi, lo = max(v, key=v.get), min(v, key=v.get)
    tot = v[hi] + v[lo]
    if v[hi] == v[lo] or tot <= 0:
        return None, None, None
    return r["name"].get(hi), r["name"].get(lo), v[hi] / tot


def _fmt(rows) -> str:
    if not rows:
        return "—"
    w = sum(1 for x in rows if x["won"])
    if len(rows) < MIN_N:
        return f"{w}-{len(rows)-w} · _n={len(rows)}, too few_"
    u = sum(grade.american_profit(x["odds"]) if x["won"] else -1 for x in rows)
    return f"{w}-{len(rows)-w} ({w/len(rows):.0%}) · {u:+.1f}u · **{u/len(rows):+.1%}** (n={len(rows)})"


def _rows(recs, mode, pick, gate=None) -> list:
    out = []
    for r in recs:
        more, less, share = _sides(r, mode)
        if not more or (gate and not gate(share)):
            continue
        t = more if pick == "more" else less
        if t in r["price"]:
            out.append({"won": r["winner"] == t, "odds": r["price"][t]})
    return out


def build() -> str:
    recs, diag = collect()
    mode = "last" if diag["cum_hits"] >= diag["sum_hits"] else "sum"
    md = ["# Pre-game money per side (Kalshi candlesticks)", "",
          "_Volume truncated at first pitch, so in-game trading - which is driven "
          "by the score rather than by conviction - is excluded. This is the "
          "correction to `venue_volume.md`, whose totals included the whole game._",
          "",
          "## Coverage", "",
          f"- games matched with a start time: **{diag['matched']}**",
          f"- usable (candles on both sides): **{len(recs)}**",
          f"- dropped, no candles: **{diag['no_candles']}**", "",
          "_Candle fetch outcomes: " +
          (", ".join(f"`{k}` {v}" for k, v in STATUS.most_common()) or "none") +
          "._", ""]

    md += ["## Is candle `volume_fp` cumulative or per-period?", "",
           f"Reconciled against each market's known total on {diag['checked']} "
           f"markets: last-candle matched **{diag['cum_hits']}**, "
           f"sum-of-candles matched **{diag['sum_hits']}** — "
           f"treating it as **{'cumulative' if mode == 'last' else 'per-period'}**.", ""]

    if len(recs) < MIN_N:
        md += ["## Verdict", "",
               f"Only **{len(recs)}** usable games, below the **{MIN_N}** needed "
               "for a read. Counts only.", ""]
        return "\n".join(md)

    md += ["## Does the pre-game money side win?", "",
           "| strategy | result |", "|---|---|",
           f"| back the MORE pre-game money side | {_fmt(_rows(recs, mode, 'more'))} |",
           f"| back the LESS pre-game money side | {_fmt(_rows(recs, mode, 'less'))} |", ""]

    for lo, hi, label in ((0.60, 1.01, "60%+"), (0.70, 1.01, "70%+")):
        gate = lambda s, lo=lo, hi=hi: s is not None and lo <= s < hi
        md += [f"_Lopsided — one side holds {label} of pre-game volume:_", "",
               "| strategy | result |", "|---|---|",
               f"| back the MORE side | {_fmt(_rows(recs, mode, 'more', gate))} |",
               f"| back the LESS side | {_fmt(_rows(recs, mode, 'less', gate))} |", ""]

    md.append("_Volume counts both sides of every trade, so this is a proxy for "
              "interest in a side, not a ledger of money backing it. Holdout "
              "discipline still applies before any of this touches the board._")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "pregame_money.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
