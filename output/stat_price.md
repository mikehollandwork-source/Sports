# The stat model as a favourite and as a dog

_Everything the board measures - margin, BvP, bullpen, form, park, consistency, record - collapses into one output: `advantage_team`. Flat overall at -3.5% over 851 games. The question here is whether it is flat everywhere, or worthless on chalk and worth something on a dog._

- graded games: **1136**

## The control that was missing

_A price band is not a neutral container. If every team priced +110..+139 was profitable this season, then "stat dog" earns its return for being a dog and the stat model contributed nothing. So each band is shown with the NON-stat side at the same prices. The **delta** is what the stat model is worth._

| band | stat side (what we'd bet) | non-stat side (same prices) | delta |
|---|---|---|---|
| heavy fav ≤-200 | 61-20 · +5.7u · **+7.1%** (n=81) | 10-3 · +1.5u · **+11.7%** (n=13) _(thin)_ | **-4.7 pts** |
| fav -199..-140 | 202-134 · -9.0u · **-2.7%** (n=336) | 55-30 · +4.8u · **+5.7%** (n=85) | **-8.3 pts** |
| fav -139..-110 | 185-150 · +0.0u · **+0.0%** (n=335) | 110-108 · -16.7u · **-7.7%** (n=218) | **+7.7 pts** |
| pick'em -109..+109 | 91-108 · -17.7u · **-8.9%** (n=199) | 99-128 · -29.1u · **-12.8%** (n=227) | **+3.9 pts** |
| dog +110..+139 | 70-64 · +19.0u · **+14.2%** (n=134) | 145-170 · +8.0u · **+2.5%** (n=315) | **+11.6 pts** |
| dog +140..+199 | 14-33 · -10.7u · **-22.7%** (n=47) | 83-149 · -15.8u · **-6.8%** (n=232) | **-15.9 pts** |
| big dog ≥+200 | 1-3 · -0.8u · **-20.8%** (n=4) _(thin)_ | 10-36 · -13.7u · **-29.8%** (n=46) | **+9.0 pts** |

## Does the best band beat the search that found it?

- best band: **dog +110..+139**, delta **+11.6 points**
- bands entering the correction: **5**
- biggest delta a redraw manufactures: median **+12.1**, 95th pct **+33.8**
- **corrected p = 0.522**

**Does not clear.** A scan this wide manufactures a delta this large often enough that the number is the width of the search.

## Does the shape repeat? (split-half)

_The test that has actually discriminated here: it killed the team scan (r=-0.12), the fade profile (r=-0.64) and the stat combos (r=-0.20), and endorsed near_miss (r=+0.88)._

| band | delta, half A | delta, half B |
|---|---|---|
| fav -199..-140 | -9.7 pts | -4.9 pts |
| fav -139..-110 | +9.2 pts | +6.4 pts |
| pick'em -109..+109 | +21.9 pts | -12.8 pts |
| dog +110..+139 | -4.5 pts | +26.9 pts |
| dog +140..+199 | +11.4 pts | -39.3 pts |

- **split-half r = -0.49** over 5 bands

_Not repeatable. The per-band deltas in one half do not predict the other, which means the band-to-band pattern is noise being read as structure._

## The best band over time, and against line movement

- **dog +110..+139**, stat side, in-sample: 19-17 · +5.3u · **+14.9%** (n=36)
- **dog +110..+139**, stat side, holdout: 51-47 · +13.6u · **+13.9%** (n=98)

_Line movement is the one thing that has held up on this data, so the question is whether it compounds with the price band or just overlaps it._

| within the best band | stat side |
|---|---|
| line moved AGAINST the stat side (≥1.0%) | 30-22 · +13.8u · **+26.5%** (n=52) |
| line moved WITH it | 12-9 · +5.1u · **+24.5%** (n=21) _(thin)_ |
| flat | 28-33 · +0.1u · **+0.1%** (n=61) |

- market-calibrated null on that cell: **3%** of redraws reach or beat it

## How to read this

- the **delta** column is the only number that isolates the stat model; the raw band ROI includes whatever the price band did
- a band that clears the permutation but fails split-half is a cell that got lucky, not a property of price
- nothing here changes the board. The live rule does not consult `advantage_team` to choose a side - it is a coordinate system for reading the book, and that stays true whatever this says.
