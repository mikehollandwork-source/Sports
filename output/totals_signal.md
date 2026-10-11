# Can our signals predict RUNS?

_The totals markets began logging on 2026-10-11, so there is no history to backtest against a line. This tests the half that can be tested: signal against actual score. No line means no vig and no ROI — if these cannot predict runs unopposed, they will not beat a price._

- graded games with a score: **251**

- full-game runs: mean **8.66**, median 8.0, SD 4.16
- first-five runs: mean **4.71** (54% of the game), n=251

## Each signal against the actual score

| signal | n | r vs full game | r vs first five |
|---|---|---|---|
| park | 251 | +0.023 | +0.026 |
| temp | 250 | +0.101 | +0.088 |
| wind | 250 | -0.041 | -0.021 |
| lineup_rate | 251 | +0.035 | +0.062 |
| woba | 251 | -0.053 | -0.036 |
| offense_index | 251 | -0.089 | -0.043 |
| starter_fip | 250 | +0.069 | +0.082 |
| starter_fip_l5 | 251 | +0.180 | +0.138 |
| bullpen_fip | 251 | +0.139 | +0.030 |
| combined_fip | 251 | +0.175 | +0.122 |
| pitching_index | 251 | -0.175 | -0.122 |

_A correlation inside roughly ±0.10 at this sample is not distinguishable from nothing._

## Over/under the median (8.0 runs)

_No market line exists, so the bar is our own median. This shows whether a signal SORTS games, which is necessary before it can beat a price — not sufficient._

| signal | low third | high third | gap |
|---|---|---|---|
| park | 47.0% over | 52.9% over | **+6.0%** |
| temp | 45.8% over | 53.6% over | **+7.8%** |
| wind | 47.0% over | 42.9% over | **-4.1%** |
| lineup_rate | 45.8% over | 40.0% over | **-5.8%** |
| woba | 45.8% over | 47.1% over | **+1.3%** |
| offense_index | 44.6% over | 42.4% over | **-2.2%** |
| starter_fip | 45.8% over | 48.8% over | **+3.0%** |
| starter_fip_l5 | 38.6% over | 52.9% over | **+14.4%** |
| bullpen_fip | 39.8% over | 52.9% over | **+13.2%** |
| combined_fip | 38.6% over | 50.6% over | **+12.0%** |
| pitching_index | 50.6% over | 38.8% over | **-11.8%** |

## Pre-registered, for when the lines arrive

_Written while blind — the market data does not exist yet, so these cannot have been chosen to fit it. When the log has a season, the test is: does the signal beat the CLOSING line, corrected for the width of the search, with both tails checked._

- full game: park, temperature, wind, lineup hit rate, team wOBA, offense index, starter FIP (season and last-5), bullpen FIP, SoS-adjusted combined FIP, pitching index
- first five: the same, since the starters pitch it
- strikeout line: the starter's K price against the opposing lineup's hit prices, which should move opposite
- the bar is the vig, roughly 4.5% on a two-sided total, not zero
