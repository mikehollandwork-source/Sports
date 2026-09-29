# Is the market right about every team, or only most of them?

_"Only bet teams the market prices correctly" is backwards — a correctly priced team returns exactly minus the hold. The useful version is the mirror: is any team reliably MISpriced, and can it be told from the one team in thirty that looks mispriced by chance?_

_That last clause is why a single-team report cannot settle this. Philadelphia came back p = 0.651 and Atlanta p = 0.652 — both correctly priced — but scan thirty teams for the biggest gap and something always turns up. Here the scan itself is corrected for._

- graded games: **1223** · teams with ≥40 games: **30**

## Every team, most underrated first

| team | games | market expected | actual | gap | flat-stake |
|---|---|---|---|---|---|
| Boston Red Sox | 83 | 45.1 | 54 | **+8.9** | +18.4% |
| Tampa Bay Rays | 84 | 45.5 | 53 | **+7.5** | +12.9% |
| San Diego Padres | 83 | 42.1 | 49 | **+6.9** | +12.2% |
| Milwaukee Brewers | 84 | 48.3 | 54 | **+5.7** | +8.7% |
| Arizona Diamondbacks | 81 | 39.7 | 44 | **+4.3** | +12.3% |
| Atlanta Braves | 82 | 43.9 | 46 | **+2.1** | +2.9% |
| Chicago White Sox | 83 | 41.0 | 43 | **+2.0** | +2.4% |
| Baltimore Orioles | 79 | 39.1 | 41 | **+1.9** | +2.7% |
| Chicago Cubs | 82 | 44.1 | 46 | **+1.9** | +2.2% |
| Pittsburgh Pirates | 81 | 40.0 | 41 | **+1.0** | -3.0% |
| Cincinnati Reds | 83 | 37.0 | 38 | **+1.0** | +0.6% |
| New York Mets | 82 | 39.6 | 40 | **+0.4** | -1.6% |
| Texas Rangers | 82 | 41.7 | 42 | **+0.3** | -1.1% |
| Houston Astros | 80 | 41.8 | 42 | **+0.2** | -0.7% |
| Miami Marlins | 80 | 38.1 | 38 | **-0.1** | -2.8% |
| Minnesota Twins | 80 | 39.1 | 39 | **-0.1** | -3.3% |
| Cleveland Guardians | 81 | 43.2 | 43 | **-0.2** | -3.4% |
| New York Yankees | 81 | 44.4 | 44 | **-0.4** | -2.4% |
| Detroit Tigers | 81 | 41.5 | 41 | **-0.5** | -4.6% |
| Toronto Blue Jays | 82 | 40.7 | 40 | **-0.7** | -1.4% |
| Washington Nationals | 81 | 36.8 | 36 | **-0.8** | -9.7% |
| Kansas City Royals | 81 | 36.4 | 35 | **-1.4** | -9.3% |
| Philadelphia Phillies | 82 | 46.3 | 44 | **-2.3** | -10.1% |
| Los Angeles Dodgers | 80 | 50.5 | 48 | **-2.5** | -9.0% |
| St. Louis Cardinals | 83 | 38.3 | 35 | **-3.3** | -8.6% |
| San Francisco Giants | 82 | 36.2 | 32 | **-4.2** | -16.0% |
| Colorado Rockies | 81 | 31.9 | 26 | **-5.9** | -24.3% |
| Athletics | 81 | 33.0 | 26 | **-7.0** | -20.9% |
| Los Angeles Angels | 79 | 34.3 | 27 | **-7.3** | -22.4% |
| Seattle Mariners | 80 | 42.5 | 35 | **-7.5** | -19.7% |

## Corrected for scanning 30 teams

- most underrated: **Boston Red Sox** at +8.9 wins · the best of 30 teams on noise alone reaches +8.9 median, +13.0 at the 95th · **corrected p = 0.509**
- most overrated: **Seattle Mariners** at -7.5 wins · the worst reaches -9.0 median, -13.0 at the 5th · **corrected p = 0.797**

_Read the median column before the gap column. A gap of +8.9 wins is what the LUCKIEST of 30 teams shows when every price is perfect._

## League-wide, one row per game

_Per game, not per team: both sides' residuals sum to zero by construction, so pooling both would make any favourite-versus-dog comparison mechanically symmetric and guarantee a null._

| | games | expected | actual | gap | flat-stake |
|---|---|---|---|---|---|
| back every favourite | 1223 | 697.1 | 712 | **+14.9** | -0.6% |
| back every underdog | 1223 | 525.9 | 511 | **-14.9** | -5.8% |

## The Philadelphia shape, tested on the league

_Philadelphia met their price across 66 games as a favourite and went 4-12 as a dog. Sixteen games cannot test that. If it is real, teams who are usually favourites should underperform whenever they are priced as dogs._

| cut | teams | their games AS DOGS | expected | actual | gap | flat-stake |
|---|---|---|---|---|---|---|
| favourite ≥55% of the time | 17 | 383 | 167.8 | 183 | **+15.2** | +5.7% |
| favourite ≥60% of the time | 14 | 276 | 121.2 | 134 | **+12.8** | +7.9% |
| favourite ≥65% of the time | 12 | 213 | 94.6 | 102 | **+7.4** | +5.1% |
| favourite ≥70% of the time | 10 | 159 | 70.8 | 75 | **+4.2** | +3.4% |

_Four cuts are four looks; treat the best of them accordingly._

## Trend across price, pooled over every game

- correlation of the favourite's residual with its implied probability: **+0.015**
- permuted null 95% within ±0.057 · **two-sided p = 0.589**
- **no bias across price.** Philadelphia's p = 0.034 trend does not reproduce league-wide, which is what one look in nineteen at a single team predicts

## What this can and cannot support

- a team's gap only means something if it beats the **best of 30** on noise, not its own p-value
- a flat-stake return near **−4% to −5%** is a correctly priced team — that is the hold
- one season per team. Even the extremes here have roughly 80 games behind them, which is why the corrected column matters more than the ranking
