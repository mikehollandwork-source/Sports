# Signal backtest — 206 graded of 231 game snapshots

## Each signal alone (bet the advantage team when it fires)

| signal | record | units |
|---|---|---|
| margin (n=36) | 25-11 (69%) | +7.10u |
| favorite (n=147) | 84-63 (57%) | -1.93u |
| line (n=28) | 19-9 (68%) | +4.29u |
| consistency (n=55) | 33-22 (60%) | +2.86u |
| bvp (n=89) | 50-39 (56%) | -0.05u |
| sharp (n=3) | 1-2 (33%) | -1.23u |
| form (n=14) | 8-6 (57%) | +0.70u |

## By number of signals hit

| signals hit | record | units |
|---|---|---|
| 5/7 | 4-1 (80%) | +1.06u |
| 4/7 | 12-6 (67%) | +2.15u |
| 3/7 | 17-10 (63%) | +2.41u |
| 2/7 | 35-29 (55%) | -0.65u |
| 1/7 | 31-35 (47%) | -8.09u |
| 0/7 | 10-16 (38%) | -4.12u |

## Best signal combos (all present together, n≥10, by win%)

| combo | record | units |
|---|---|---|
| margin + consistency + bvp | 8-2 (80%) | +2.52u |
| margin + bvp | 15-5 (75%) | +5.08u |
| line + consistency | 9-3 (75%) | +3.21u |
| margin + consistency | 11-4 (73%) | +2.87u |
| favorite + line + consistency | 8-3 (73%) | +2.07u |
| margin + favorite + bvp | 13-5 (72%) | +2.93u |
| margin + favorite + consistency | 10-4 (71%) | +1.83u |
| favorite + consistency + bvp | 19-8 (70%) | +4.66u |
| line + bvp | 9-4 (69%) | +1.46u |
| margin + favorite | 21-10 (68%) | +3.74u |
| favorite + line + bvp | 8-4 (67%) | +0.32u |
| favorite + line | 17-9 (65%) | +2.15u |

## Tailing the side VEGAS needed (book_needs) vs outcome

| slice | record | units |
|---|---|---|
| all games with a book read (n=190) | 85-105 (45%) | -20.32u |
|   ...money % (n=15) | 5-10 (33%) | -4.31u |
|   ...ticket % (n=175) | 80-95 (46%) | -16.01u |
| (vs our advantage side, same games) | 106-84 (56%) | +2.90u |

## Tailing Vegas (bet the side book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| tail Vegas, all games (n=190) | 85-105 (45%) | -20.32u |
|   + our stat side agrees (n=65) | 33-32 (51%) | -2.83u |
|   + agrees & margin (n=8) | 5-3 (62%) | +0.87u |
|   + agrees & favorite (n=39) | 22-17 (56%) | -0.88u |
|   + agrees & line (n=6) | 4-2 (67%) | +0.69u |
|   + agrees & consistency (n=15) | 6-9 (40%) | -4.50u |
|   + agrees & bvp (n=25) | 10-15 (40%) | -6.48u |
|   + agrees & sharp (n=1) | 0-1 (0%) | -1.00u |
|   + agrees & form (n=4) | 1-3 (25%) | -1.95u |

## Tail Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=54) | 27-27 (50%) | -5.04u | -9.3% |
| ≥2 signals (n=25) | 11-14 (44%) | -5.72u | -22.9% |
| ≥3 signals (n=10) | 5-5 (50%) | -1.60u | -16.0% |
| ≥4 signals (n=4) | 3-1 (75%) | +0.69u | +17.2% |

## Fading Vegas (bet the OPPOSITE of book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| fade Vegas, all games (n=190) | 105-85 (55%) | +1.70u |
|   + our stat side agrees (n=125) | 73-52 (58%) | +5.73u |
|   + agrees & margin (n=25) | 19-6 (76%) | +7.40u |
|   + agrees & favorite (n=98) | 60-38 (61%) | +5.14u |
|   + agrees & line (n=22) | 15-7 (68%) | +3.61u |
|   + agrees & consistency (n=40) | 27-13 (68%) | +7.36u |
|   + agrees & bvp (n=64) | 40-24 (62%) | +6.43u |
|   + agrees & sharp (n=2) | 1-1 (50%) | -0.23u |
|   + agrees & form (n=10) | 7-3 (70%) | +2.65u |

## Fade Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=115) | 70-45 (61%) | +9.11u | +7.9% |
| ≥2 signals (n=83) | 54-29 (65%) | +10.76u | +13.0% |
| ≥3 signals (n=36) | 26-10 (72%) | +7.76u | +21.6% |
| ≥4 signals (n=15) | 10-5 (67%) | +1.09u | +7.3% |

## Best MULTI-signal fade combos (stat side agrees, n≥10)

| combo | record | units |
|---|---|---|
| consistency + bvp | 18-6 (75%) | +6.80u |
| favorite + consistency + bvp | 16-5 (76%) | +5.66u |
| margin + bvp | 12-4 (75%) | +4.31u |
| margin + favorite | 16-6 (73%) | +4.21u |
| margin + consistency | 10-4 (71%) | +2.50u |
| margin + favorite + bvp | 10-4 (71%) | +2.16u |
| favorite + consistency | 23-11 (68%) | +5.01u |
| favorite + line | 14-7 (67%) | +2.47u |
| margin + favorite + consistency | 9-4 (69%) | +1.46u |
| favorite + bvp | 32-18 (64%) | +3.67u |

## Our pick when the book's informed money was AGAINST us (⚠️ bucket)

| slice | record | units |
|---|---|---|
| stance-against plays (n=46) | 23-23 (50%) | -4.65u |

## NEW BOARD GATE — fade + core signal (what makes the board now)

| slice | record | units |
|---|---|---|
| BOARD: fade + core signal (n=61) | 42-19 (69%) | +12.57u |
| DROPPED: tail + core signal (was played, now cut) (n=24) | 11-13 (46%) | -4.00u |

## Threshold sweeps on the fade side (does a tighter bar help?)

| margin ≥ | record | units |
|---|---|---|
| 0.30 | 32-22 (59%) | +1.49u |
| 0.40 | 27-13 (68%) | +6.66u |
| 0.50 | 19-6 (76%) | +7.40u |
| 0.60 | 7-2 (78%) | +2.79u |
| 0.70 | 2-1 (67%) | +0.11u |

| consistency (out-hit) ≥ | record | units |
|---|---|---|
| 3/5 | 27-13 (68%) | +7.36u |
| 4/5 | 7-5 (58%) | +0.39u |
| 5/5 | 4-1 (80%) | +1.99u |

## Does line-shading improve our picks? (our picks by shading gap)

| shading gap (tickets − implied) | record | units |
|---|---|---|
| < 5 (not shaded) | 52-42 (55%) | -0.34u |
| 5–15 (mild) | 38-32 (54%) | -1.56u |
| ≥ 15 (heavy shade) | 15-16 (48%) | -1.89u |

## Underdog study — our stat side priced as a DOG (ml > 0)

| slice | record | units | ROI/bet |
|---|---|---|---|
| all underdogs (n=59) | 25-34 (42%) | -5.31u | -9% |
| + edge margin ≥.50 (n=5) | 4-1 (80%) | +3.36u | +67% |
| + BvP edge (n=25) | 10-15 (40%) | -3.62u | -14% |
| + consistency ≥3 (n=12) | 5-7 (42%) | -1.60u | -13% |
| + margin & BvP (n=2) | 2-0 (100%) | +2.15u | +108% |
| + consistency & BvP (n=7) | 2-5 (29%) | -2.86u | -41% |
| + margin & BvP & consistency (all three) | 0 | — | — |

## Every underdog + signal combo (bet the dog, n≥5, by units)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin | 4-1 (80%) | +3.36u | +67% |
| consistency | 5-7 (42%) | -1.60u | -13% |
| consistency + bvp | 2-5 (29%) | -2.86u | -41% |
| bvp | 10-15 (40%) | -3.62u | -14% |
| (any dog) | 25-34 (42%) | -5.31u | -9% |

## ALL signal combinations — every graded pick (every signal subset, n≥10, by ROI/bet)

| combo | record | units | ROI/bet |
|---|---|---|---|
| line + consistency | 9-3 (75%) | +3.21u | +27% |
| margin + bvp | 15-5 (75%) | +5.08u | +25% |
| margin + favorite + consistency + bvp | 8-2 (80%) | +2.52u | +25% |
| margin + consistency + bvp | 8-2 (80%) | +2.52u | +25% |
| margin | 25-11 (69%) | +7.10u | +20% |
| margin + consistency | 11-4 (73%) | +2.87u | +19% |
| favorite + line + consistency | 8-3 (73%) | +2.07u | +19% |
| favorite + consistency + bvp | 19-8 (70%) | +4.66u | +17% |
| margin + favorite + bvp | 13-5 (72%) | +2.93u | +16% |
| line | 19-9 (68%) | +4.29u | +15% |
| margin + favorite + consistency | 10-4 (71%) | +1.83u | +13% |
| margin + favorite | 21-10 (68%) | +3.74u | +12% |
| line + bvp | 9-4 (69%) | +1.46u | +11% |
| favorite + consistency | 28-15 (65%) | +4.46u | +10% |
| favorite + line | 17-9 (65%) | +2.15u | +8% |
| favorite + form | 6-4 (60%) | +0.60u | +6% |
| favorite + bvp | 40-24 (62%) | +3.57u | +6% |
| consistency + bvp | 21-13 (62%) | +1.80u | +5% |
| consistency | 33-22 (60%) | +2.86u | +5% |
| form | 8-6 (57%) | +0.70u | +5% |

## ALL signal combinations — FADE-GATED picks (live board condition) (every signal subset, n≥10, by ROI/bet)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin | 19-6 (76%) | +7.40u | +30% |
| consistency + bvp | 18-6 (75%) | +6.80u | +28% |
| favorite + consistency + bvp | 16-5 (76%) | +5.66u | +27% |
| margin + bvp | 12-4 (75%) | +4.31u | +27% |
| form | 7-3 (70%) | +2.65u | +26% |
| margin + favorite | 16-6 (73%) | +4.21u | +19% |
| consistency | 27-13 (68%) | +7.36u | +18% |
| margin + consistency | 10-4 (71%) | +2.50u | +18% |
| line | 15-7 (68%) | +3.61u | +16% |
| margin + favorite + bvp | 10-4 (71%) | +2.16u | +15% |
| favorite + consistency | 23-11 (68%) | +5.01u | +15% |
| favorite + line | 14-7 (67%) | +2.47u | +12% |
| margin + favorite + consistency | 9-4 (69%) | +1.46u | +11% |
| bvp | 40-24 (62%) | +6.43u | +10% |
| favorite + bvp | 32-18 (64%) | +3.67u | +7% |
| favorite | 60-38 (61%) | +5.14u | +5% |
| line + bvp | 6-4 (60%) | -0.23u | -2% |

_Point-in-time: signals recomputed from the frozen pre-game snapshot; winners from the MLB Stats API; $1/bet at the frozen moneyline. A signal with no recorded input on an older board is excluded from that row only (see n=)._