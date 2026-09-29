# Which venue should confirm the pick?

_The live rule replayed on history, changing only the confirmation source. The order-book gate is the binding constraint on board size, so the plays-per-day column matters as much as ROI: a variant that earns a little less per bet while finding twice as many can still be the better rule._

## Coverage

- slate days: **39**
- games clearing the consensus gate: **295**
- of those, Polymarket has a read on **146**
- of those, Kalshi has a read on **256**

## line-against required (the live setting)

| confirmation | all-time | in-sample | holdout |
|---|---|---|---|
| `pm` | 12-5 · +4.8u · **+28.3%** (n=17, 0.4/day) _(thin)_ | 5-2 · +2.4u · **+34.9%** (n=7, 0.2/day) _(thin)_ | 7-3 · +2.4u · **+23.8%** (n=10, 0.3/day) _(thin)_ |
| `kalshi` | 30-20 · +5.2u · **+10.4%** (n=50, 1.3/day) | 21-12 · +6.1u · **+18.4%** (n=33, 0.8/day) | 9-8 · -0.9u · **-5.1%** (n=17, 0.4/day) _(thin)_ |
| `either` | 33-21 · +6.7u · **+12.3%** (n=54, 1.4/day) | 23-12 · +7.7u · **+22.1%** (n=35, 0.9/day) | 10-9 · -1.1u · **-5.6%** (n=19, 0.5/day) _(thin)_ |
| `both` | 9-4 · +3.4u · **+25.8%** (n=13, 0.3/day) _(thin)_ | 3-2 · +0.8u · **+15.5%** (n=5, 0.1/day) _(thin)_ | 6-2 · +2.6u · **+32.2%** (n=8, 0.2/day) _(thin)_ |
| `none` | 41-27 · +7.8u · **+11.5%** (n=68, 1.7/day) | 31-16 · +10.9u · **+23.2%** (n=47, 1.2/day) | 10-11 · -3.1u · **-14.6%** (n=21, 0.5/day) _(thin)_ |

## no line filter

| confirmation | all-time | in-sample | holdout |
|---|---|---|---|
| `pm` | 62-34 · +6.6u · **+6.9%** (n=96, 2.5/day) | 27-15 · +3.7u · **+8.7%** (n=42, 1.1/day) | 35-19 · +3.0u · **+5.5%** (n=54, 1.4/day) |
| `kalshi` | 139-88 · +11.2u · **+4.9%** (n=227, 5.8/day) | 97-59 · +11.7u · **+7.5%** (n=156, 4.0/day) | 42-29 · -0.5u · **-0.7%** (n=71, 1.8/day) |
| `either` | 148-94 · +11.0u · **+4.5%** (n=242, 6.2/day) | 102-61 · +13.3u · **+8.1%** (n=163, 4.2/day) | 46-33 · -2.3u · **-2.9%** (n=79, 2.0/day) |
| `both` | 53-28 · +6.8u · **+8.4%** (n=81, 2.1/day) | 22-13 · +2.1u · **+6.0%** (n=35, 0.9/day) | 31-15 · +4.7u · **+10.3%** (n=46, 1.2/day) |
| `none` | 180-115 · +14.3u · **+4.9%** (n=295, 7.6/day) | 132-80 · +17.2u · **+8.1%** (n=212, 5.4/day) | 48-35 · -2.8u · **-3.4%** (n=83, 2.1/day) |

## Do the two venues say the same thing?

- games where both have a read: **146**
- they agree: **88** (60%)

_When they disagree:_

| follow | result |
|---|---|
| Polymarket's read | 9-6 · -0.2u · **-1.3%** (n=15, 0.4/day) _(thin)_ |
| Kalshi's read | 22-21 · -3.0u · **-6.9%** (n=43, 1.1/day) |

_A variant only replaces the live rule if it beats it on the holdout as well as all-time. Higher volume alone is not a reason to switch - it is only a reason to look._