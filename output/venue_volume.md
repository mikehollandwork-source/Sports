# Historical money per side — Kalshi vs Polymarket

## 1. What Kalshi returns for settled markets

- settled market rows: **1708**
- complete two-sided games parsed: **852**
- field coverage in the first 400 rows: `volume_fp` 400, `open_interest_fp` 400, `result` 400, `close_time` 400, `event_ticker` 400

_sample row:_
```
{
 "ticker": "KXMLBGAME-26JUL302210SEALAD-SEA",
 "event_ticker": "KXMLBGAME-26JUL302210SEALAD",
 "volume_fp": "3241300.83",
 "open_interest_fp": "2149674.40",
 "result": "no",
 "close_time": "2026-07-31T05:04:24Z"
}
```

## 2. Matching to our historical games

- games matched to a Kalshi settled pair: **343**
- games with no Kalshi match: **0**
- usable rows (both sides priced, non-tied volume): **343**

## 3. Does the side with MORE Kalshi money win?

| strategy | result |
|---|---|
| back the MORE-money side | 179-164 (52%) · -11.7u · **-3.4%** (n=343) |
| back the LESS-money side | 164-179 (48%) · -19.0u · **-5.5%** (n=343) |

_Lopsided games only (one side holds 70%+ of the volume):_

| strategy | result |
|---|---|
| back the MORE-money side | 10-10 (50%) · -2.2u · **-10.9%** (n=20) |
| back the LESS-money side | 10-10 (50%) · -0.2u · **-1.1%** (n=20) |

_20 of 343 games are lopsided._

_Volume is total TRADED on each team's market, not a ledger of money backing that side - every trade has a buyer and a seller. Treat it as a proxy for interest, and the holdout discipline used elsewhere still applies before acting on anything here._