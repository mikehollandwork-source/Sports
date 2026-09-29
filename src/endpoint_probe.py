"""
Endpoint probe - exploratory only.

The settled-markets endpoint returns volume/open_interest as null, which killed
the historical money-per-side backtest. Before giving up on it, this checks the
remaining routes, and also confirms one thing the live logger currently assumes:

  1. do OPEN markets carry volume / open_interest at all? (if not, the forward
     money log is capturing depth but never "total money")
  2. /markets/{ticker} single fetch - richer than the list endpoint?
  3. candlesticks - historical price AND volume time series per market
  4. /markets/trades - raw trade history, from which per-side volume could be
     rebuilt directly
  5. Polymarket gamma - which volume fields exist on a closed market

Prints what it finds and asserts nothing. Nothing here feeds the board.
"""

from __future__ import annotations

import json
import logging
import time

import requests

from . import kalshi, pm_books

log = logging.getLogger("endpoint_probe")
TIMEOUT = 20
PROBE_PERIOD = 60


def _show(label: str, obj, limit: int = 400) -> None:
    txt = json.dumps(obj, indent=1)[:limit] if obj is not None else "None"
    print(f"\n--- {label} ---\n{txt}")


def probe() -> None:
    # ---------- 1. an OPEN market: does it carry cumulative money? ----------
    idx = kalshi.game_markets()
    print(f"open paired games: {len(idx)//2}")
    open_ticker = None
    for pair in idx.values():
        for t in pair.values():
            open_ticker = t
            break
        if open_ticker:
            break
    if not open_ticker:
        print("no open ticker to probe")
        return
    print(f"probe ticker: {open_ticker}")

    row = kalshi.market_row(open_ticker) or {}
    keys = sorted(k for k, v in row.items() if v not in (None, ""))
    print(f"\nOPEN market populated fields ({len(keys)}):\n  {keys}")
    _show("money() on an OPEN market", kalshi.money(open_ticker))

    # ---------- 2. SETTLED markets: do they carry cumulative money? ----------
    # This is the question that decides the historical backtest. The list
    # endpoint's rows are what venue_volume actually consumes, so check those
    # directly rather than only the single-market fetch.
    settled = kalshi.settled_markets(limit_pages=1)
    if settled:
        s = settled[0]
        keys = sorted(k for k, v in s.items() if v not in (None, ""))
        print(f"\nSETTLED list-row populated fields ({len(keys)}):\n  {keys}")
        _show("market_money() on a SETTLED list row", kalshi.market_money(s))
        have = sum(1 for m in settled if kalshi.market_money(m).get("volume"))
        print(f"settled rows with a usable volume: {have}/{len(settled)}")
        st = s.get("ticker")
        data = kalshi._get(f"/markets/{st}")
        m = (data or {}).get("market") or {}
        _show(f"single fetch of SETTLED {st}", kalshi.market_money(m))

    # ---------- 3. candlesticks (historical price + volume) ----------
    for path, params in (
        (f"/series/{kalshi.SERIES}/markets/{open_ticker}/candlesticks",
         {"start_ts": int(time.time()) - 86400, "end_ts": int(time.time()),
          "period_interval": 60}),
    ):
        try:
            r = requests.get(f"{kalshi.BASE}{path}", params=params, timeout=TIMEOUT,
                             headers={"User-Agent": "mlb-edge-finder (research)"})
            print(f"\ncandlesticks HTTP {r.status_code}")
            if r.ok:
                d = r.json()
                cs = d.get("candlesticks") or []
                print(f"  candles returned: {len(cs)}")
                if cs:
                    _show("first candle", cs[0])
                    _show("last candle", cs[-1])
            else:
                print(f"  body: {r.text[:200]}")
        except Exception as exc:
            print(f"candlesticks failed: {exc}")

    # ---------- 3b. do candlesticks exist for OLD markets? ----------
    # The pre-game backtest lost 320 of 343 games to empty candle responses, so
    # find out whether that is age-based retention, a window-size limit, or
    # something else - the status code and body say which.
    import datetime as dt

    from .venue_volume import _ticker_date

    seen: dict[str, str] = {}
    for m in kalshi.settled_markets(limit_pages=6):
        d = _ticker_date(m.get("ticker") or "")
        if d and d not in seen:
            seen[d] = m["ticker"]
    for d in sorted(seen)[::max(1, len(seen) // 6)][:8]:
        tk = seen[d]
        try:
            end = int(dt.datetime.fromisoformat(d + "T23:59:00+00:00").timestamp())
            r = requests.get(
                f"{kalshi.BASE}/series/{kalshi.SERIES}/markets/{tk}/candlesticks",
                params={"start_ts": end - 86400, "end_ts": end,
                        "period_interval": PROBE_PERIOD},
                timeout=TIMEOUT, headers={"User-Agent": "mlb-edge-finder (research)"})
            n = len((r.json() or {}).get("candlesticks") or []) if r.ok else -1
            print(f"  {d} {tk}: HTTP {r.status_code}, candles={n}"
                  f"{'' if r.ok else ' | ' + r.text[:120]}")
        except Exception as exc:
            print(f"  {d} {tk}: failed {exc}")

    # ---------- 4. trade history ----------
    for path, params in (("/markets/trades", {"ticker": open_ticker, "limit": 5}),):
        try:
            r = requests.get(f"{kalshi.BASE}{path}", params=params, timeout=TIMEOUT,
                             headers={"User-Agent": "mlb-edge-finder (research)"})
            print(f"\ntrades HTTP {r.status_code}")
            if r.ok:
                d = r.json()
                tr = d.get("trades") or []
                print(f"  trades returned: {len(tr)}")
                if tr:
                    _show("sample trade", tr[0])
            else:
                print(f"  body: {r.text[:200]}")
        except Exception as exc:
            print(f"trades failed: {exc}")

    # ---------- 5. Polymarket volume fields ----------
    try:
        batch = pm_books._get(pm_books.GAMMA, tag_slug="mlb", closed="true",
                              limit=3, offset=0)
        if isinstance(batch, list) and batch:
            mk = (batch[0].get("markets") or [{}])[0]
            pop = {k: mk.get(k) for k in
                   ("volume", "volumeNum", "volume24hr", "liquidity",
                    "liquidityNum", "outcomes", "closed") if mk.get(k) is not None}
            _show("Polymarket CLOSED market volume fields", pop)
        else:
            print("\npolymarket: no closed markets returned")
    except Exception as exc:
        print(f"\npolymarket probe failed: {exc}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    probe()


if __name__ == "__main__":
    main()
