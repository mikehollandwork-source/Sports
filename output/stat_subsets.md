# Every combination of the seven stats — all 127 subsets

_Singles, pairs, triples, up to all seven at once. A cell is the games where EVERY stat in the subset favours the side we back._

- games where handle and tickets already agree: **772**
- backing the consensus side in all of them: **458-314 · +1.0%**

- subsets enumerated: **127** · reaching n≥25: **106**

## Best subset at each size

| stats stacked | best subset | record | n | ROI |
|---|---|---|---|---|
| 1 | `park` | 207-138 | 345 | **+2.3%** |
| 2 | `pen+record` | 114-73 | 187 | **-0.7%** |
| 3 | `bvp+pen+record` | 58-31 | 89 | **+4.7%** |
| 4 | `bvp+pen+park+record` | 22-10 | 32 | **+10.5%** |
| 5 | `bvp+consistency+margin+form+record` | 25-13 | 38 | **+6.2%** |

## Top fifteen of all 127

| subset | record | n | ROI |
|---|---|---|---|
| `bvp+pen+park+record` | 22-10 | 32 | **+10.5%** |
| `bvp+consistency+margin+form+record` | 25-13 | 38 | **+6.2%** |
| `bvp+pen+record` | 58-31 | 89 | **+4.7%** |
| `park` | 207-138 | 345 | **+2.3%** |
| `bvp+consistency+margin+record` | 35-20 | 55 | **+1.4%** |
| `record` | 236-150 | 386 | **+0.1%** |
| `bvp+pen+margin+record` | 39-22 | 61 | **-0.2%** |
| `pen+record` | 114-73 | 187 | **-0.7%** |
| `bvp+margin+record` | 80-48 | 128 | **-1.0%** |
| `bvp+park` | 97-69 | 166 | **-1.3%** |
| `bvp+margin+form+record` | 45-28 | 73 | **-1.4%** |
| `bvp` | 225-160 | 385 | **-1.6%** |
| `pen` | 224-161 | 385 | **-1.6%** |
| `margin+record` | 136-87 | 223 | **-2.0%** |
| `pen+park` | 96-70 | 166 | **-2.0%** |

## 1. Does the best of 127 beat the search?

- best: `bvp+pen+park+record` at **+10.5%** (22-10, n=32)
- median best-in-noise: **+19.0%**
- 95th percentile in noise: **+36.3%**
- **corrected p = 0.825**

**Does not clear.** With 127 nested subsets this is what the search itself produces.

## 2. Split-half — would acting on the best subset have worked?

| best-in-first-half subset | first | second |
|---|---|---|
| `pen+margin+form+park` | +15.9% | -19.8% |
| `pen+form+park` | +11.8% | -18.9% |
| `bvp+pen+record` | +9.0% | +1.3% |
| `pen+park+record` | +7.1% | -5.4% |
| `park` | +6.8% | -2.8% |

- correlation across **96** subsets: **r = +0.36**
- backing `pen+margin+form+park` (the first half's best) in the second half: **19-19 · -19.8%** (n=38)
- backing everything in the second half: **210-161 · -4.7%**

**The ranking does not hold.** Picking the best subset from one half does not beat taking everything in the next.

## 3. Does stacking more stats actually help?

_If combining genuinely adds, ROI should rise with subset size. If it only rises as n falls, that is thinning, not signal._

| stats stacked | subsets | median ROI | median n |
|---|---|---|---|
| 1 | 7 | -1.6% | 385 |
| 2 | 21 | -6.2% | 171 |
| 3 | 35 | -10.3% | 89 |
| 4 | 33 | -17.5% | 45 |
| 5 | 10 | -20.0% | 29 |
