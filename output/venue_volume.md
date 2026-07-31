# Historical money per side — Kalshi vs Polymarket

## 1. What Kalshi returns for settled markets

- settled market rows: **1708**
- complete two-sided games parsed: **852**
- field coverage in the first 400 rows: `result` 400, `close_time` 400, `event_ticker` 400

_sample row:_
```
{
 "ticker": "KXMLBGAME-26JUL302210SEALAD-SEA",
 "event_ticker": "KXMLBGAME-26JUL302210SEALAD",
 "volume": null,
 "open_interest": null,
 "result": "no",
 "close_time": "2026-07-31T05:04:24Z"
}
```

## 2. Matching to our historical games

- games matched to a Kalshi settled pair: **343**
- games with no Kalshi match: **0**
- usable rows (both sides priced, non-tied volume): **0**

## Verdict

Only **0** usable games - below the **20** needed for a meaningful read. Reporting counts only rather than a percentage on a handful of games.
