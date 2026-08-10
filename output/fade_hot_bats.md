# Fade the hot-bats team when the line moves against it

_Back the side whose bats are COLDER, when the market is already walking away from the hotter side. Swept by the price of the side we back, because a single cutoff cannot be evaluated - only a curve can._

- games with form on both sides, both prices and a line move: **394**

## The two populations

- every game (fade the hotter bats regardless of the line): 193-201 (49%) · -16.5u · **-4.2%** (n=394)
- **line also moving against the hot side**: 70-60 (54%) · -4.3u · **-3.3%** (n=130)

## By price of the side we back

Two controls, because they answer different questions. **Fade-only** drops the line-movement requirement, so the gap to it is what the line filter adds. **Price-only** backs the favourite at that price in every game with no reference to form or the line at all - it is literally "just bet cheap favourites", and the gap to IT is the only number that is about hot bats.

| we pay no worse than | qualifying cell | fade-only | price-only (the confound) | edge vs price-only |
|---|---|---|---|---|
| -110 or cheaper | 3-5 (38%) · -2.2u · **-27.2%** (n=8) _(thin)_ | 17-22 (44%) · -5.8u · **-14.9%** (n=39) | 9-5 (64%) · +3.3u · **+23.8%** (n=14) _(thin)_ | **-51.0%** |
| -120 or cheaper | 9-10 (47%) · -1.9u · **-9.9%** (n=19) _(thin)_ | 39-47 (45%) · -11.7u · **-13.6%** (n=86) | 50-47 (52%) · -3.1u · **-3.2%** (n=97) | **-6.7%** |
| -130 or cheaper | 19-15 (56%) · +1.1u · **+3.4%** (n=34) | 58-65 (47%) · -14.5u · **-11.8%** (n=123) | 88-77 (53%) · -2.9u · **-1.7%** (n=165) | **+5.1%** |
| -140 or cheaper | 23-23 (50%) · -3.8u · **-8.3%** (n=46) | 70-81 (46%) · -21.6u · **-14.3%** (n=151) | 118-104 (53%) · -7.6u · **-3.4%** (n=222) | **-4.9%** |
| -150 or cheaper | 30-26 (54%) · -2.0u · **-3.6%** (n=56) | 83-89 (48%) · -20.7u · **-12.0%** (n=172) | 152-125 (55%) · -5.3u · **-1.9%** (n=277) | **-1.7%** |
| -175 or cheaper | 40-28 (59%) · +2.0u · **+3.0%** (n=68) | 104-95 (52%) · -13.8u · **-6.9%** (n=199) | 191-147 (57%) · -3.3u · **-1.0%** (n=338) | **+4.0%** |
| -200 or cheaper | 48-32 (60%) · +2.3u · **+2.9%** (n=80) | 114-100 (53%) · -13.4u · **-6.3%** (n=214) | 206-159 (56%) · -7.3u · **-2.0%** (n=365) | **+4.9%** |
| -250 or cheaper | 53-35 (60%) · +1.5u · **+1.7%** (n=88) | 119-103 (54%) · -14.2u · **-6.4%** (n=222) | 216-168 (56%) · -11.8u · **-3.1%** (n=384) | **+4.8%** |

## Plateau or spike?

- longest run of adjacent thresholds with a positive edge: **3** of 6
- a real effect degrades gracefully either side of its optimum; a lone positive surrounded by negatives is the shape that killed the +40% dog signal.

## Does the best threshold beat the sweep itself?

- thresholds at n>=30: **6**
- best: `-130 or cheaper` at an edge of **+5.1%** over price-only (its own ROI is +3.4%)
- median best-edge in noise: **+4.4%**
- 95th percentile in noise: **+26.1%**
- **corrected p = 0.478**

**Does not clear.** A sweep this size produces an edge this good from noise more than 5% of the time.

- edge CI vs price-only control: **-27.8% to +38.9%**
- in-sample: 8-10 (44%) · -3.3u · **-18.5%** (n=18) _(thin)_
- holdout: 11-5 (69%) · +4.5u · **+27.9%** (n=16) _(thin)_
- games needed to call a real +10% edge: ~**663**

## Scored against the pre-registered bar

| requirement | met |
|---|---|
| n >= 100 in the cell (n=34) | ❌ |
| plateau of >= 3 adjacent thresholds (longest=3) | ✅ |
| corrected p <= 0.05 (p=0.478) | ❌ |
| holdout positive (+27.9%) | ✅ |
| edge CI excludes zero (-27.8%..+38.9%) | ❌ |

**NOT promotable.** Recorded, not shipped.

## Consistency — does the effect need the trimmings?

| subset of the best cell | backing the cold side |
|---|---|
| all of it | 19-15 (56%) · +1.1u · **+3.4%** (n=34) |
| hot side was the home team | 9-5 (64%) · +2.4u · **+17.5%** (n=14) _(thin)_ |
| hot side was a home dog (the original cell) | 6-0 (100%) · +4.8u · **+80.3%** (n=6) _(thin)_ |
| hot side's stars also outproducing | 16-12 (57%) · +1.7u · **+5.9%** (n=28) _(thin)_ |
| form gap in the top half | 12-5 (71%) · +5.3u · **+31.4%** (n=17) _(thin)_ |

_A real effect should survive these restrictions, not depend on them. If it only appears in one sliver, that sliver is the search talking._
