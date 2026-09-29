# Every stat, crossed with line movement, price, and each other

_The widest search in this repo. ~105 cells, so the correction matters more here than anywhere - every grid tried has produced a best-looking cell, and the 75-cell price scan came in BELOW its own noise median._

- games where handle and tickets already agree: **772**
- backing the consensus side in all of them: **+1% (458-314)**

## Each stat x line movement against us

| stat favours the pick | ≥0.0% | ≥0.5% | ≥1.0% | ≥2.0% |
|---|---|---|---|---|
| `bvp` | +5% (128-82) | -2% (76-59) | +4% (58-39) | +5% (32-22) |
| `pen` | +1% (118-84) | +1% (71-52) | -1% (50-39) | +3% (27-20) |
| `consistency` | -3% (76-59) | -6% (50-42) | -2% (37-29) | +9% (25-15) |
| `margin` | -1% (129-90) | +0% (83-58) | +3% (58-38) | +8% (33-19) |
| `form` | +3% (125-87) | +10% (86-52) | +12% (60-35) | +23% (41-19) |
| `park` | +4% (110-74) | +5% (67-47) | +14% (49-28) | +12% (27-16) |
| `record` | +6% (137-80) | -0% (79-55) | +2% (59-39) | -0% (28-20) |

## Each stat x price band

| stat favours the pick | ≤-150 | -149..-120 | -119..-101 | +100..+139 | ≥+140 |
|---|---|---|---|---|---|
| `bvp` | +0% (115-61) | -6% (69-60) | -10% (25-28) | _+25% (16-11)_ | — |
| `pen` | -0% (108-58) | -10% (71-67) | +12% (33-23) | _+2% (12-13)_ | — |
| `consistency` | -4% (64-38) | -19% (47-55) | -11% (15-17) | _+30% (8-5)_ | — |
| `margin` | -0% (130-71) | -5% (74-62) | -15% (17-21) | _-3% (5-6)_ | — |
| `form` | -8% (87-59) | -1% (74-57) | +3% (27-23) | _+11% (13-12)_ | _+152% (1-0)_ |
| `park` | +4% (92-45) | -9% (75-69) | +32% (29-13) | _+5% (11-11)_ | — |
| `record` | +3% (142-69) | -5% (72-60) | +0% (18-16) | _-4% (4-5)_ | — |

## Every pair of stats

_Both favour the pick, versus the two disagreeing._

| pair | both favour | they disagree |
|---|---|---|
| `bvp` + `pen` | -3% (111-81) | -0% (227-159) |
| `bvp` + `consistency` | -8% (73-61) | -2% (213-153) |
| `bvp` + `margin` | -5% (126-88) | -0% (199-144) |
| `bvp` + `form` | -5% (103-79) | +1% (221-153) |
| `bvp` + `park` | -1% (97-69) | +2% (238-160) |
| `bvp` + `record` | -2% (121-77) | +1% (219-156) |
| `pen` + `consistency` | -16% (70-68) | +4% (218-140) |
| `pen` + `margin` | -10% (119-94) | +6% (212-133) |
| `pen` + `form` | -7% (106-88) | +4% (214-136) |
| `pen` + `park` | -2% (96-70) | +2% (239-159) |
| `pen` + `record` | -1% (114-73) | -1% (232-165) |
| `consistency` + `margin` | -11% (93-78) | -0% (174-119) |
| `consistency` + `form` | -10% (85-74) | +0% (166-118) |
| `consistency` + `park` | -17% (53-55) | +6% (235-143) |
| `consistency` + `record` | -13% (62-53) | +2% (246-159) |
| `margin` + `form` | -6% (134-103) | +3% (160-105) |
| `margin` + `park` | -4% (98-73) | +2% (237-152) |
| `margin` + `record` | -2% (136-87) | -2% (190-136) |
| `form` + `park` | -8% (86-72) | +6% (237-145) |
| `form` + `record` | -6% (91-68) | +3% (256-165) |
| `park` + `record` | -4% (87-63) | +5% (269-162) |

## 1. Does the best cell beat the search?

- cells at n≥30: **91**
- best: `park @ -119..-101` at **+31.8%** (n=42)
- median best-in-noise: **+17.8%**
- 95th percentile in noise: **+34.0%**
- **corrected p = 0.067**

**Does not clear.**

## 2. Split-half — do the good cells stay good?

| top-5 cell by first half | first | second |
|---|---|---|
| park @ -119..-101 | +26.8% | +38.5% |
| form @ -149..-120 | +17.6% | -19.8% |
| form + move≥0.0% | +12.9% | -2.9% |
| form + move≥1.0% | +12.2% | +12.6% |
| pen+form split | +11.9% | -2.8% |

- correlation across **91** cells: **r = -0.20**

**The ranking does not hold.** A cell's first-half record does not predict its second.

## 3. The powered version — every pairwise combination at once

_If any combination carries information, a model given all 21 of them predicts better. If it predicts worse, they are noise and the model memorised it._

- trained on **401** games before 2026-08-11, scored on **371**

| model | holdout log-loss |
|---|---|
| price only | 0.6856 |
| price + 7 stats + all 21 interactions | **0.7130** |

- change: **-0.0274**, 95% CI **-0.0512 to -0.0032**

**No information in any combination.** Everything in the picture is already in the price, alone and together.
