# Does a faster refresh find better picks, or just more?

_The order-book gate replayed at every timestamp `pm_books` logged. `any` is what 'refresh constantly and post whatever qualifies' comes to; `t30` is a fixed decision point 30 minutes before first pitch; `last` is closest to today's hourly board._

## Coverage

- games clearing the consensus gate with a usable book log: **202**
- slate days: **20**

## How much does the gate actually flap?

- games where the book confirmed at some point: **195**
- of those, NOT confirming by the last pre-game reading: **71** — these are picks a fast refresh would have posted and the rule would later have withdrawn
- games whose confirmation flips at least once: **161** of 202
- median logged readings per game: **101**

## line-against required (the live setting)

| entry policy | all-time | in-sample | holdout |
|---|---|---|---|
| `any` | 28-19 · +4.4u · **+9.4%** (n=47, 2.4/day) | 7-3 · +3.3u · **+33.0%** (n=10, 0.5/day) _(thin)_ | 21-16 · +1.1u · **+3.1%** (n=37, 1.9/day) |
| `first` | 28-19 · +4.4u · **+9.4%** (n=47, 2.4/day) | 7-3 · +3.3u · **+33.0%** (n=10, 0.5/day) _(thin)_ | 21-16 · +1.1u · **+3.1%** (n=37, 1.9/day) |
| `t30` | 12-10 · -0.3u · **-1.4%** (n=22, 1.1/day) _(thin)_ | 3-2 · +0.5u · **+10.7%** (n=5, 0.2/day) _(thin)_ | 9-8 · -0.9u · **-5.0%** (n=17, 0.8/day) _(thin)_ |
| `last` | 13-8 · +2.5u · **+11.8%** (n=21, 1.1/day) _(thin)_ | 4-2 · +1.4u · **+22.7%** (n=6, 0.3/day) _(thin)_ | 9-6 · +1.1u · **+7.5%** (n=15, 0.8/day) _(thin)_ |
| `none` | 29-20 · +4.4u · **+8.9%** (n=49, 2.5/day) | 8-3 · +4.2u · **+38.5%** (n=11, 0.6/day) _(thin)_ | 21-17 · +0.1u · **+0.4%** (n=38, 1.9/day) |

## no line filter

| entry policy | all-time | in-sample | holdout |
|---|---|---|---|
| `any` | 126-69 · +20.3u · **+10.4%** (n=195, 9.8/day) | 40-22 · +7.2u · **+11.6%** (n=62, 3.1/day) | 86-47 · +13.1u · **+9.9%** (n=133, 6.7/day) |
| `first` | 126-69 · +20.3u · **+10.4%** (n=195, 9.8/day) | 40-22 · +7.2u · **+11.6%** (n=62, 3.1/day) | 86-47 · +13.1u · **+9.9%** (n=133, 6.7/day) |
| `t30` | 78-46 · +7.2u · **+5.8%** (n=124, 6.2/day) | 23-17 · -1.0u · **-2.6%** (n=40, 2.0/day) | 55-29 · +8.3u · **+9.8%** (n=84, 4.2/day) |
| `last` | 80-44 · +9.6u · **+7.7%** (n=124, 6.2/day) | 26-18 · -0.1u · **-0.2%** (n=44, 2.2/day) | 54-26 · +9.6u · **+12.0%** (n=80, 4.0/day) |
| `none` | 130-72 · +20.5u · **+10.1%** (n=202, 10.1/day) | 41-22 · +8.1u · **+12.9%** (n=63, 3.1/day) | 89-50 · +12.3u · **+8.9%** (n=139, 7.0/day) |

## Reading this

If `any` beats `t30` on ROI, faster refreshing is catching real late signal and is worth doing. If `any` carries more bets at a worse ROI, the extra picks are noise crossings - the gate was sampled until it said yes - and the current cadence is already taking the better half.

_Only the order-book gate is replayed over time; the consensus and line gates are held at their stored end-of-day values, since the picks file keeps only the final public read. That limit isolates the book gate, which is the component driven by a noisy instantaneous quantity and the one under suspicion._