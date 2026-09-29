# Edge finder — 413 games (352 in-sample, 61 holdout)

_Bets our stat side at its frozen price. The HOLDOUT column is the only out-of-sample evidence._

## 1. Calibration — does our margin track win rate?

_If win% climbs with margin, the model measures something real (and the problem is pricing). If it's flat, the model is noise._

| margin bucket | ALL | in-sample | HOLDOUT |
|---|---|---|---|
| < 0 (no edge) | — | — | — |
| 0.0–0.2 | 99-85 (54%) · +0.8% (n=184) | 83-74 (53%) · -1.4% (n=157) | 16-11 (59%) · +13.5% (n=27) |
| 0.2–0.4 | 57-70 (45%) · -19.1% (n=127) | 47-60 (44%) · -20.1% (n=107) | 10-10 (50%) · -13.9% (n=20) |
| 0.4–0.6 | 43-31 (58%) · +0.9% (n=74) | 37-28 (57%) · -0.9% (n=65) | 6-3 (67%) · +13.8% (n=9) |
| 0.6–0.9 | 15-12 (56%) · -7.6% (n=27) | 14-9 (61%) · +2.9% (n=23) | 1-3 (25%) · -68.3% (n=4) |
| 0.9+ | 0-1 (0%) · -100.0% (n=1) | — | 0-1 (0%) · -100.0% (n=1) |

_High margin (≥0.5) wins 61.9% vs low margin 50.0% — a **+11.9 point** spread. That spread IS the model's entire predictive claim._

## 2. Breakeven gap by price — what we NEED vs what we GET

_need% = the win rate that price requires just to break even. gap = actual − need. Positive gap = profitable territory._

| price bucket | need% | actual (ALL) | gap | HOLDOUT actual |
|---|---|---|---|---|
| ≤ −200 (heavy chalk) | 70.7% | 68.0% (n=25) | **-2.7pts** | 5-2 (71%) · -0.9% (n=7) |
| −200 to −160 | 63.4% | 61.2% (n=49) | **-2.2pts** | 3-2 (60%) · -5.1% (n=5) |
| −160 to −130 | 58.7% | 52.6% (n=95) | **-6.1pts** | 7-5 (58%) · -0.6% (n=12) |
| −130 to −110 | 54.5% | 55.7% (n=88) | **+1.2pts** | 6-7 (46%) · -15.2% (n=13) |
| −110 to +100 (pick'em) | 51.4% | 44.4% (n=54) | **-7.0pts** | 3-5 (38%) · -26.9% (n=8) |
| +100 to +150 | 47.0% | 46.7% (n=90) | **-0.3pts** | 9-6 (60%) · +26.0% (n=15) |
| +150 or better | 36.2% | 16.7% (n=12) | **-19.5pts** | 0-1 (0%) · -100.0% (n=1) |

## 3. What winners have in common (vs losers)

_Median of each stat for wins vs losses. A stat that separates in BOTH columns is a lead; in-sample-only separation is noise. NOTE: 11 stats × 2 windows are compared here — a couple of spurious gaps are expected._

| stat | in-sample W / L | holdout W / L |
|---|---|---|
| edge margin | +0.237 / +0.216 | +0.226 / +0.259 |
| team-score gap | +0.169 / +0.152 | +0.162 / +0.146 |
| offense-index gap | +0.085 / +0.113 | +0.121 / +0.123 |
| pitching-index gap | +0.111 / +0.080 | +0.028 / +0.106 |
| FIP gap (opp−ours) | +0.457 / +0.328 | +0.116 / +0.436 |
| wOBA gap | +0.031 / +0.038 | +0.042 / +0.047 |
| ISO gap | +0.033 / +0.040 | +0.060 / +0.030 |
| K% gap | -0.009 / -0.010 | +0.010 / -0.007 |
| BvP gap | +0.005 / +0.036 | +0.033 / -0.007 |
| form gap | +0.029 / +0.031 | +0.039 / +0.034 |
| price (ml) | -126.000 / -115.000 | -125.000 / -116.500 |

## 4. Underdogs — can we actually make dog money? (n=102)

| dog slice | ALL | in-sample | HOLDOUT |
|---|---|---|---|
| all underdogs | 44-58 (43%) · -7.4% (n=102) | 35-51 (41%) · -12.2% (n=86) | 9-7 (56%) · +18.1% (n=16) |
| + margin ≥ 0.4 | 7-10 (41%) · -12.5% (n=17) | 7-10 (41%) · -12.5% (n=17) | — |
| + margin ≥ 0.5 | 4-4 (50%) · +4.5% (n=8) | 4-4 (50%) · +4.5% (n=8) | — |
| + consistency | 15-21 (42%) · -13.2% (n=36) | 12-17 (41%) · -13.5% (n=29) | 3-4 (43%) · -11.7% (n=7) |
| + FIP gap ≥ 0.15 | 17-25 (40%) · -11.3% (n=42) | 17-22 (44%) · -4.4% (n=39) | 0-3 (0%) · -100.0% (n=3) |
| + pitching-index gap > 0 | 18-30 (38%) · -17.9% (n=48) | 18-26 (41%) · -10.4% (n=44) | 0-4 (0%) · -100.0% (n=4) |
| small dogs (+100 to +140) | 42-47 (47%) · +0.0% (n=89) | 33-41 (45%) · -5.2% (n=74) | 9-6 (60%) · +26.0% (n=15) |
| big dogs (> +140) | 2-11 (15%) · -58.5% (n=13) | 2-10 (17%) · -55.0% (n=12) | 0-1 (0%) · -100.0% (n=1) |

_Dogs need **45.7%** to break even; we hit **43.1%** (**-2.6 pts**). Every extra dog we add only helps if it clears that bar._

_Multiple comparisons caveat: this file scans many slices. Treat any single green cell as a hypothesis, never a rule, until it holds in the holdout AND has a reason to be true._