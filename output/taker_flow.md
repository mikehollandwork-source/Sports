# Aggressive money per side (Kalshi taker flow)

_Who crossed the spread, pre-game. Unlike volume - which counts both the buyer and the seller of every trade - taker notional is a direct read of money pushing a side. Both of a game's markets are combined: money on a team = YES takers in its own market + NO takers in its opponent's._

## Coverage

- games matched: **351**
- usable: **351**
- dropped, no trades: **0**
- dropped, under $100 pre-game flow: **0**

_Trade fetch outcomes: `200` 2150._

## Does the aggressive-money side win?

| strategy | result |
|---|---|
| back the MORE aggressive-money side | 205-146 (58%) · +9.7u · **+2.8%** (n=351) |
| back the LESS aggressive-money side | 146-205 (42%) · -40.4u · **-11.5%** (n=351) |

_Lopsided — one side holds 60%+ of aggressive flow:_

| strategy | result |
|---|---|
| back the MORE side | 155-113 (58%) · -1.5u · **-0.5%** (n=268) |
| back the LESS side | 113-155 (42%) · -20.9u · **-7.8%** (n=268) |

_Lopsided — one side holds 70%+ of aggressive flow:_

| strategy | result |
|---|---|
| back the MORE side | 109-79 (58%) · -5.5u · **-2.9%** (n=188) |
| back the LESS side | 79-109 (42%) · -9.9u · **-5.3%** (n=188) |

## Controls — is this an edge, or just backing favourites?

- the more-money side is the favourite in **171/188** (91%) of these games
- backing the FAVOURITE on the same games: **-2.4%**  ← if this matches, the money adds nothing

| subset | n | ROI |
|---|---|---|
| money side IS the favourite | 171 | -2.4% |
| money side is the DOG | 17 | -8.3% |

_The dog subset is 17 games — that is the real sample behind any edge here, not the headline n._

- market-calibrated null: **p = 0.411** (4000 redraws from de-vigged prices)

- in-sample (< 2026-07-23): **-6.0%** (n=125)
- holdout (>= 2026-07-23): **+3.2%** (n=63)

- day-block bootstrap 95% CI: **-13.1% to +7.7%**

_Same bar as the volume version: the favourite control decides whether this is an edge or a repriced favourite, and the favourite/dog split shows how many games actually carry it._