# Fade the hot-bats team when the line moves against it

_Back the side whose bats are COLDER, when the market is already walking away from the hotter side. Swept by the price of the side we back, because a single cutoff cannot be evaluated - only a curve can._

- games with form on both sides, both prices and a line move: **394**

## The two populations

- every game (fade the hotter bats regardless of the line): 193-201 (49%) · -16.5u · **-4.2%** (n=394)
- **line also moving against the hot side**: 70-60 (54%) · -4.3u · **-3.3%** (n=130)

## By price of the side we back

The control is the SAME price bucket in every game, ignoring form and line movement. It is what "just bet cheap favourites" returns on its own. The edge column is the only one that is about hot bats.

| we pay no worse than | qualifying cell | same-price control | edge |
|---|---|---|---|
| -110 or cheaper | 3-5 (38%) · -2.2u · **-27.2%** (n=8) _(thin)_ | 17-22 (44%) · -5.8u · **-14.9%** (n=39) | **-12.3%** |
| -120 or cheaper | 9-10 (47%) · -1.9u · **-9.9%** (n=19) _(thin)_ | 39-47 (45%) · -11.7u · **-13.6%** (n=86) | **+3.7%** |
| -130 or cheaper | 19-15 (56%) · +1.1u · **+3.4%** (n=34) | 58-65 (47%) · -14.5u · **-11.8%** (n=123) | **+15.1%** |
| -140 or cheaper | 23-23 (50%) · -3.8u · **-8.3%** (n=46) | 70-81 (46%) · -21.6u · **-14.3%** (n=151) | **+5.9%** |
| -150 or cheaper | 30-26 (54%) · -2.0u · **-3.6%** (n=56) | 83-89 (48%) · -20.7u · **-12.0%** (n=172) | **+8.4%** |
| -175 or cheaper | 40-28 (59%) · +2.0u · **+3.0%** (n=68) | 104-95 (52%) · -13.8u · **-6.9%** (n=199) | **+9.9%** |
| -200 or cheaper | 48-32 (60%) · +2.3u · **+2.9%** (n=80) | 114-100 (53%) · -13.4u · **-6.3%** (n=214) | **+9.2%** |
| -250 or cheaper | 53-35 (60%) · +1.5u · **+1.7%** (n=88) | 119-103 (54%) · -14.2u · **-6.4%** (n=222) | **+8.2%** |

## Plateau or spike?

- longest run of adjacent thresholds with a positive edge: **6** of 6
- a real effect degrades gracefully either side of its optimum; a lone positive surrounded by negatives is the shape that killed the +40% dog signal.

## Does the best threshold beat the sweep itself?

- thresholds at n>=30: **6**
- best: `-130 or cheaper` at an edge of **+15.1%**
- median best-edge in noise: **+3.9%**
- 95th percentile in noise: **+22.3%**
- **corrected p = 0.153**

**Does not clear.** A sweep this size produces an edge this good from noise more than 5% of the time.

- edge CI vs same-price control: **-18.9% to +50.9%**
- in-sample: 8-10 (44%) · -3.3u · **-18.5%** (n=18) _(thin)_
- holdout: 11-5 (69%) · +4.5u · **+27.9%** (n=16) _(thin)_
- games needed to call a real +10% edge: ~**663**

## Scored against the pre-registered bar

| requirement | met |
|---|---|
| n >= 100 in the cell (n=34) | ❌ |
| plateau of >= 3 adjacent thresholds (longest=6) | ✅ |
| corrected p <= 0.05 (p=0.153) | ❌ |
| holdout positive (+27.9%) | ✅ |
| edge CI excludes zero (-18.9%..+50.9%) | ❌ |

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
