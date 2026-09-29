# Dog money — widest available sample

_Every complete two-sided game Kalshi has settled, using Kalshi alone: the ticker gives the teams and first pitch, `result` gives the winner, candles give pre-game volume and price. No picks file, no sportsbook line - so this is not limited to days we ran a board._

## Coverage

- two-sided settled events: **862**
- usable games: **856**
- dropped (no candles 0, no result 6, no start 0, tied volume 0)

_Candle fetch outcomes: `200` 1712._

## The dog subset, by lopsidedness threshold

_Backing the side with more pre-game volume, only when that side is the price underdog. Graded at the Kalshi close, and again with a one-cent entry haircut - an edge that only exists at the mid is not tradeable._

| min share | at close | with 1c haircut |
|---|---|---|
| 55% | 75-102 (42%) · -17.8u · **-10.0%** (n=177) | 75-102 (42%) · -21.1u · **-11.9%** (n=177) |
| 60% | 60-65 (48%) · +1.5u · **+1.2%** (n=125) | 60-65 (48%) · -1.1u · **-0.9%** (n=125) |
| 65% | 43-39 (52%) · +9.1u · **+11.1%** (n=82) | 43-39 (52%) · +7.2u · **+8.8%** (n=82) |
| 70% | 33-23 (59%) · +14.3u · **+25.6%** (n=56) | 33-23 (59%) · +12.9u · **+23.0%** (n=56) |
| 75% | 16-14 (53%) · +3.6u · **+12.1%** (n=30) | 16-14 (53%) · +2.9u · **+9.8%** (n=30) |
| 80% | 3-6 (33%) · -2.9u · **-32.0%** (n=9) _(thin)_ | 3-6 (33%) · -3.0u · **-33.3%** (n=9) _(thin)_ |

## Controls — is this an edge, or just backing favourites?

- the more-money side is the favourite in **348/404** (86%) of these games
- backing the FAVOURITE on the same games: **-1.7%**  ← if this matches, the money adds nothing

| subset | n | ROI |
|---|---|---|
| money side IS the favourite | 348 | +2.1% |
| money side is the DOG | 56 | +26.9% |

_The dog subset is 56 games — that is the real sample behind any edge here, not the headline n._

- market-calibrated null: **p = 0.106** (4000 redraws from de-vigged prices)

- in-sample (< 2026-07-23): **+4.7%** (n=348)
- holdout (>= 2026-07-23): **+10.8%** (n=56)

- day-block bootstrap 95% CI: **-3.7% to +13.7%**

_A flat profile across thresholds is the encouraging shape; a spike at one threshold that vanishes either side of it is the signature of fitting noise._