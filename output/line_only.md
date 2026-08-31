# Line movement alone — back the side the line moved against

_No handle, no tickets, no order book, no stat model. For every game the line moved on, back the side whose price got longer. Prices are the board's closing moneylines, frozen at first pitch._

- games with a non-zero line move: **736**

## Baseline — every game with any move

- 357-379 (49%) · -21.4u · **-2.9%** (n=736)
- as a favourite: 212-164 (56%) · +0.0u · **+0.0%** (n=376)
- as a dog: 145-215 (40%) · -21.5u · **-6.0%** (n=360)

## By size of the move

| min move | all | favourites | dogs |
|---|---|---|---|
| ≥0.5% | 313-345 (48%) · -24.9u · **-3.8%** (n=658) | 178-146 (55%) · -7.3u · **-2.2%** (n=324) | 135-199 (40%) · -17.6u · **-5.3%** (n=334) |
| ≥1.0% | 247-274 (47%) · -14.7u · **-2.8%** (n=521) | 130-107 (55%) · -4.8u · **-2.0%** (n=237) | 117-167 (41%) · -9.8u · **-3.5%** (n=284) |
| ≥2.0% | 144-161 (47%) · -2.7u · **-0.9%** (n=305) | 70-51 (58%) · +4.5u · **+3.7%** (n=121) | 74-110 (40%) · -7.1u · **-3.9%** (n=184) |
| ≥3.0% | 80-92 (47%) · +4.1u · **+2.4%** (n=172) | 32-22 (59%) · +3.3u · **+6.1%** (n=54) | 48-70 (41%) · +0.8u · **+0.7%** (n=118) |
| ≥5.0% | 20-28 (42%) · -3.5u · **-7.3%** (n=48) | 6-7 (46%) · -2.3u · **-17.8%** (n=13) _(thin)_ | 14-21 (40%) · -1.2u · **-3.3%** (n=35) |

## By move size and closing price

| min move | heavy fav (<= -200) | mod fav (-199..-130) | slight fav (-129..-101) | slight dog (+100..+139) | mod/heavy dog (>= +140) |
|---|---|---|---|---|---|
| ≥0.5% | 7-1 (88%) · +2.0u · **+24.7%** (n=8) _(thin)_ | 74-57 (56%) · -6.7u · **-5.1%** (n=131) | 97-88 (52%) · -2.5u · **-1.4%** (n=185) | 94-117 (45%) · -7.0u · **-3.3%** (n=211) | 41-82 (33%) · -10.6u · **-8.7%** (n=123) |
| ≥1.0% | 5-1 (83%) · +1.2u · **+19.4%** (n=6) _(thin)_ | 52-36 (59%) · -0.1u · **-0.1%** (n=88) | 73-70 (51%) · -5.9u · **-4.1%** (n=143) | 81-95 (46%) · +0.1u · **+0.0%** (n=176) | 36-72 (33%) · -9.9u · **-9.1%** (n=108) |
| ≥2.0% | 1-1 (50%) · -0.5u · **-25.0%** (n=2) _(thin)_ | 30-17 (64%) · +3.5u · **+7.5%** (n=47) | 39-33 (54%) · +1.4u · **+2.0%** (n=72) | 47-53 (47%) · +2.5u · **+2.5%** (n=100) | 27-57 (32%) · -9.6u · **-11.4%** (n=84) |
| ≥3.0% | 0-1 (0%) · -1.0u · **-100.0%** (n=1) _(thin)_ | 14-7 (67%) · +2.5u · **+11.8%** (n=21) _(thin)_ | 18-14 (56%) · +1.8u · **+5.6%** (n=32) | 26-30 (46%) · +1.4u · **+2.5%** (n=56) | 22-40 (35%) · -0.6u · **-0.9%** (n=62) |
| ≥5.0% | 0-1 (0%) · -1.0u · **-100.0%** (n=1) _(thin)_ | 3-1 (75%) · +1.1u · **+26.9%** (n=4) _(thin)_ | 3-5 (38%) · -2.4u · **-29.9%** (n=8) _(thin)_ | 9-7 (56%) · +3.7u · **+23.1%** (n=16) _(thin)_ | 5-14 (26%) · -4.9u · **-25.6%** (n=19) _(thin)_ |

## Does the best cell beat the search itself?

- cells at n≥25: **15**
- best cell: `≥2.0% / mod fav (-199..-130)` at **+7.5%**
- median best-in-noise: **+13.7%**
- 95th percentile of best-in-noise: **+31.4%**
- **corrected p = 0.779**

**Does not clear.** A grid this size produces a cell this good from noise more than 5% of the time, so the number is the search talking, not the data.

- best cell in-sample: 13-11 (54%) · -1.6u · **-6.6%** (n=24) _(thin)_
- best cell holdout: 17-6 (74%) · +5.1u · **+22.3%** (n=23) _(thin)_

_Every cell here shares one dataset, so reading the grid for the greenest number is the same mistake the underdog scan made - there the best of 64 cells matched the noise median almost exactly._