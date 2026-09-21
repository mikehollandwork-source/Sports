# Does retuning the gates ever pay?

_Walk the season forward one day at a time. On each day pick the configuration with the best ROI on games that finished BEFORE that day, and bet the day with it. No future data is used anywhere. The grid search is part of the strategy, so it is measured as part of the strategy._

- games reaching the book gate: **612**
- configurations available: **10** (EITHER/BOTH × line move 0.0%–2.0%)
- history required before tuning is allowed: **60** games

## The whole season, over the days the adaptive policy was live

_from **2026-07-23** onward_

| policy | record |
|---|---|
| **adaptive** (retune daily on all prior games) | 24-15 · +5.39u · **+13.8%** (n=39) |
| frozen live rule (EITHER / ≥1.0%) | 62-30 · +14.96u · **+16.3%** (n=92) |
| frozen tried-and-reverted (BOTH / ≥0.5%) | 43-18 · +16.58u · **+27.2%** (n=61) |

**Retuning lost to standing pat.** Picking the best-so-far configuration earned -13.4 points against the better frozen rule, which is what happens when the grid's cells differ by noise: you chase whichever cell got lucky and it reverts. This is the measurement that applies to the change just shipped, because that change was produced by exactly this procedure.

_Stated against itself: the adaptive policy bet only 39 games, because tuning keeps steering it into the tightest cells, so its ROI carries a wide interval and the gap above is not significant on its own. What is not a sample-size artifact is the table below - the configuration it chose changed repeatedly, and for most of the season it was not the cell that looks best in hindsight._

## How often did it change its mind?

- days tuned: **60** · configuration changed on **9** of them (15%)

| configuration | days it was the best-so-far |
|---|---|
| BOTH / ≥1.5% | 29 |
| BOTH / ≥2.0% | 18 |
| BOTH / ≥1.0% | 6 |
| EITHER / ≥1.0% | 3 |
| EITHER / ≥0.5% | 2 |
| BOTH / ≥0.0% | 2 |

_A parameter that is real stays selected. One that flips every few days is the last two weeks talking._

## The same grid scored with hindsight (for contrast only)

_Every cell over all games. This is the view that produced the change, and the spread here is the size of the temptation._

| configuration | record |
|---|---|
| BOTH / ≥2.0% | 22-9 · +10.12u · **+32.6%** (n=31) |
| BOTH / ≥1.0% | 37-14 · +15.93u · **+31.2%** (n=51) |
| BOTH / ≥0.5% ← shipped 2026-09-21, reverted the same day | 48-19 · +20.08u · **+30.0%** (n=67) |
| EITHER / ≥2.0% | 39-15 · +14.64u · **+27.1%** (n=54) |
| BOTH / ≥1.5% | 24-11 · +9.32u · **+26.6%** (n=35) |
| EITHER / ≥1.5% | 49-21 · +15.09u · **+21.6%** (n=70) |
| EITHER / ≥1.0% ← **live now** | 67-32 · +17.40u · **+17.6%** (n=99) |
| BOTH / ≥0.0% | 82-45 · +16.80u · **+13.2%** (n=127) |
| EITHER / ≥0.5% | 88-51 · +13.43u · **+9.7%** (n=139) |
| EITHER / ≥0.0% | 141-85 · +14.32u · **+6.3%** (n=226) |

_The best cell in hindsight is not a forecast. The walk-forward number above is the one that includes the cost of having chosen it._
