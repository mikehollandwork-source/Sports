# Line movement alone — back the side the line moved against

_No handle, no tickets, no order book, no stat model. For every game the line moved on, back the side whose price got longer. Prices are the board's closing moneylines, frozen at first pitch._

- games with a non-zero line move: **515**

## Baseline — every game with any move

- 240-275 (47%) · -27.7u · **-5.4%** (n=515)
- as a favourite: 136-117 (54%) · -9.2u · **-3.6%** (n=253)
- as a dog: 104-158 (40%) · -18.5u · **-7.1%** (n=262)

## By size of the move

| min move | all | favourites | dogs |
|---|---|---|---|
| ≥0.5% | 213-257 (45%) · -33.6u · **-7.2%** (n=470) | 115-105 (52%) · -13.5u · **-6.1%** (n=220) | 98-152 (39%) · -20.1u · **-8.1%** (n=250) |
| ≥1.0% | 174-213 (45%) · -27.9u · **-7.2%** (n=387) | 89-80 (53%) · -8.6u · **-5.1%** (n=169) | 85-133 (39%) · -19.4u · **-8.9%** (n=218) |
| ≥2.0% | 107-132 (45%) · -9.8u · **-4.1%** (n=239) | 46-42 (52%) · -4.9u · **-5.6%** (n=88) | 61-90 (40%) · -4.9u · **-3.2%** (n=151) |
| ≥3.0% | 63-80 (44%) · -0.0u · **-0.0%** (n=143) | 19-19 (50%) · -3.8u · **-9.9%** (n=38) | 44-61 (42%) · +3.7u · **+3.6%** (n=105) |
| ≥5.0% | 19-24 (44%) · -0.4u · **-0.8%** (n=43) | 5-5 (50%) · -1.2u · **-11.9%** (n=10) _(thin)_ | 14-19 (42%) · +0.8u · **+2.5%** (n=33) |

## By move size and closing price

| min move | heavy fav (<= -200) | mod fav (-199..-130) | slight fav (-129..-101) | slight dog (+100..+139) | mod/heavy dog (>= +140) |
|---|---|---|---|---|---|
| ≥0.5% | 3-1 (75%) · +0.3u · **+6.7%** (n=4) _(thin)_ | 45-39 (54%) · -7.7u · **-9.2%** (n=84) | 67-65 (51%) · -6.0u · **-4.6%** (n=132) | 70-97 (42%) · -14.9u · **-8.9%** (n=167) | 28-55 (34%) · -5.3u · **-6.3%** (n=83) |
| ≥1.0% | 2-1 (67%) · -0.1u · **-3.5%** (n=3) _(thin)_ | 34-28 (55%) · -4.1u · **-6.5%** (n=62) | 53-51 (51%) · -4.4u · **-4.2%** (n=104) | 61-80 (43%) · -8.6u · **-6.1%** (n=141) | 24-53 (31%) · -10.8u · **-14.1%** (n=77) |
| ≥2.0% | 0-1 (0%) · -1.0u · **-100.0%** (n=1) _(thin)_ | 21-16 (57%) · -1.0u · **-2.8%** (n=37) | 25-25 (50%) · -2.9u · **-5.7%** (n=50) | 39-47 (45%) · -1.0u · **-1.2%** (n=86) | 22-43 (34%) · -3.9u · **-5.9%** (n=65) |
| ≥3.0% | 0-1 (0%) · -1.0u · **-100.0%** (n=1) _(thin)_ | 8-7 (53%) · -1.4u · **-9.2%** (n=15) _(thin)_ | 11-11 (50%) · -1.4u · **-6.3%** (n=22) _(thin)_ | 24-29 (45%) · -0.2u · **-0.4%** (n=53) | 20-32 (38%) · +3.9u · **+7.6%** (n=52) |
| ≥5.0% | 0-1 (0%) · -1.0u · **-100.0%** (n=1) _(thin)_ | 3-1 (75%) · +1.1u · **+26.9%** (n=4) _(thin)_ | 2-3 (40%) · -1.3u · **-25.3%** (n=5) _(thin)_ | 9-7 (56%) · +3.7u · **+23.1%** (n=16) _(thin)_ | 5-12 (29%) · -2.9u · **-16.8%** (n=17) _(thin)_ |

## Does the best cell beat the search itself?

- cells at n≥25: **14**
- best cell: `≥3.0% / mod/heavy dog (>= +140)` at **+7.6%**
- median best-in-noise: **+13.5%**
- 95th percentile of best-in-noise: **+31.7%**
- **corrected p = 0.745**

**Does not clear.** A grid this size produces a cell this good from noise more than 5% of the time, so the number is the search talking, not the data.

- best cell in-sample: 8-13 (38%) · +1.0u · **+4.6%** (n=21) _(thin)_
- best cell holdout: 12-19 (39%) · +3.0u · **+9.6%** (n=31)

_Every cell here shares one dataset, so reading the grid for the greenest number is the same mistake the underdog scan made - there the best of 64 cells matched the noise median almost exactly._