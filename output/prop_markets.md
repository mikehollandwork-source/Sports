# Batter prop markets available — 2026-10-03

_One event probed. Costs roughly one API credit per market, against a free tier of ~150-240 a month, so this is a one-off._

_Why it matters: 1+ hit is a ~63% event priced near -200, where break-even is 66.7% and the hold eats the edge. A market nearer even money gives the same hitter read more room._

- event probed: **Atlanta Braves @ Los Angeles Dodgers** (upcoming — in-game prices would answer a different question)

| market | quoted? | outcomes | distinct lines | median OVER price |
|---|---|---|---|---|
| `batter_hits` | yes | 128 | 0.5, 1.5 | -185 |
| `batter_total_bases` | yes | 174 | 0.5, 1.5 | +115 |
| `batter_hits_runs_rbis` | yes | 120 | 0.5, 1.5, 2.5 | +102 |
| `batter_runs_scored` | yes | 72 | 0.5 | +132 |
| `batter_rbis` | yes | 88 | 0.5 | +188 |
| `batter_singles` | yes | 72 | 0.5 | +116 |
| `batter_doubles` | yes | 90 | 0.5 | +425 |
| `batter_home_runs` | yes | 34 | 0.5, 1.5 | +1100 |
| `batter_walks` | yes | 36 | 0.5 | +238 |

## Nearest even money (the whole point)

_Lower break-even leaves more room above the hold for a hitter read to matter._

| market | line | median OVER | break-even |
|---|---|---|---|
| `batter_hits_runs_rbis` | Over 1.5 | +105 | **48.8%** |
| `batter_hits_runs_rbis` | Over 0.5 | -112 | **52.9%** |
| `batter_singles` | Over 0.5 | +116 | **46.4%** |
| `batter_total_bases` | Over 1.5 | +128 | **44.0%** |
| `batter_runs_scored` | Over 0.5 | +132 | **43.0%** |
| `batter_total_bases` | Over 0.5 | -140 | **58.3%** |
| `batter_hits` | Over 0.5 | -185 | **64.9%** |
| `batter_rbis` | Over 0.5 | +188 | **34.7%** |
| `batter_walks` | Over 0.5 | +238 | **29.6%** |
| `batter_doubles` | Over 0.5 | +425 | **19.0%** |
| `batter_home_runs` | Over 0.5 | +575 | **14.8%** |
| `batter_home_runs` | Over 1.5 | +6500 | **1.5%** |

_Availability is not an edge. Nothing in this project has shown the hitter read beats a price in ANY market; a cheaper price only means less hold to overcome._
