# Batter prop markets available — 2026-10-03

_One event probed. Costs roughly one API credit per market, against a free tier of ~150-240 a month, so this is a one-off._

_Why it matters: 1+ hit is a ~63% event priced near -200, where break-even is 66.7% and the hold eats the edge. A market nearer even money gives the same hitter read more room._

- event probed: **Chicago White Sox @ Cleveland Guardians**

| market | quoted? | outcomes | distinct lines | median OVER price |
|---|---|---|---|---|
| `batter_hits` | yes | 26 | 0.5, 1.5, 2.5 | +215 |
| `batter_total_bases` | yes | 14 | 1.5, 2.5, 5.5 | +230 |
| `batter_hits_runs_rbis` | yes | 52 | 0.5, 1.5, 2.5, 5.5 | +160 |
| `batter_runs_scored` | yes | 26 | 0.5, 1.5 | +425 |
| `batter_rbis` | yes | 24 | 0.5 | +600 |
| `batter_singles` | yes | 26 | 0.5, 1.5 | +295 |
| `batter_doubles` | yes | 54 | 0.5, 1.5 | +1000 |
| `batter_home_runs` | yes | 27 | 0.5, 1.5 | +2400 |
| `batter_walks` | yes | 24 | 0.5, 1.5 | +345 |

## Nearest even money (the whole point)

_Lower break-even leaves more room above the hold for a hitter read to matter._

| market | line | median OVER | break-even |
|---|---|---|---|
| `batter_hits_runs_rbis` | Over 0.5 | +160 | **38.5%** |
| `batter_hits_runs_rbis` | Over 1.5 | +205 | **32.8%** |
| `batter_hits` | Over 0.5 | +208 | **32.5%** |
| `batter_singles` | Over 0.5 | +285 | **26.0%** |
| `batter_total_bases` | Over 1.5 | +320 | **23.8%** |
| `batter_walks` | Over 0.5 | +345 | **22.5%** |
| `batter_walks` | Over 1.5 | +390 | **20.4%** |
| `batter_runs_scored` | Over 0.5 | +438 | **18.6%** |
| `batter_rbis` | Over 0.5 | +600 | **14.3%** |
| `batter_doubles` | Over 0.5 | +1100 | **8.3%** |
| `batter_home_runs` | Over 0.5 | +1900 | **5.0%** |
| `batter_home_runs` | Over 1.5 | +95000 | **0.1%** |

_Availability is not an edge. Nothing in this project has shown the hitter read beats a price in ANY market; a cheaper price only means less hold to overcome._
