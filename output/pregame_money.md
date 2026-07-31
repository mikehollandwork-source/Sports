# Pre-game money per side (Kalshi candlesticks)

_Volume truncated at first pitch, so in-game trading - which is driven by the score rather than by conviction - is excluded. This is the correction to `venue_volume.md`, whose totals included the whole game._

## Coverage

- games matched with a start time: **343**
- usable (candles on both sides): **343**
- dropped, no candles: **0**

_Candle fetch outcomes: `200` 686._

## Is candle `volume_fp` cumulative or per-period?

Reconciled against each market's known total on 40 markets: last-candle matched **0**, sum-of-candles matched **40** — treating it as **per-period**.

## Does the pre-game money side win?

| strategy | result |
|---|---|
| back the MORE pre-game money side | 189-154 (55%) · -7.2u · **-2.1%** (n=343) |
| back the LESS pre-game money side | 154-189 (45%) · -23.5u · **-6.9%** (n=343) |

_Lopsided — one side holds 60%+ of pre-game volume:_

| strategy | result |
|---|---|
| back the MORE side | 150-100 (60%) · +11.9u · **+4.8%** (n=250) |
| back the LESS side | 100-150 (40%) · -34.9u · **-13.9%** (n=250) |

_Lopsided — one side holds 70%+ of pre-game volume:_

| strategy | result |
|---|---|
| back the MORE side | 104-65 (62%) · +11.9u · **+7.0%** (n=169) |
| back the LESS side | 65-104 (38%) · -25.7u · **-15.2%** (n=169) |

_Volume counts both sides of every trade, so this is a proxy for interest in a side, not a ledger of money backing it. Holdout discipline still applies before any of this touches the board._