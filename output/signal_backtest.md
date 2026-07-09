# Signal backtest — 202 graded of 218 game snapshots

## Each signal alone (bet the advantage team when it fires)

| signal | record | units |
|---|---|---|
| margin (n=36) | 25-11 (69%) | +7.10u |
| favorite (n=144) | 83-61 (58%) | -0.70u |
| line (n=27) | 19-8 (70%) | +5.29u |
| consistency (n=53) | 33-20 (62%) | +4.86u |
| bvp (n=88) | 50-38 (57%) | +0.95u |
| sharp (n=1) | 0-1 (0%) | -1.00u |
| form (n=11) | 7-4 (64%) | +1.93u |

## By number of signals hit

| signals hit | record | units |
|---|---|---|
| 5/7 | 4-1 (80%) | +1.06u |
| 4/7 | 12-5 (71%) | +3.15u |
| 3/7 | 16-9 (64%) | +2.64u |
| 2/7 | 35-28 (56%) | +0.35u |
| 1/7 | 31-35 (47%) | -8.09u |
| 0/7 | 10-16 (38%) | -4.12u |

## Best signal combos (all present together, n≥10, by win%)

| combo | record | units |
|---|---|---|
| line + consistency | 9-2 (82%) | +4.21u |
| favorite + line + consistency | 8-2 (80%) | +3.07u |
| margin + consistency + bvp | 8-2 (80%) | +2.52u |
| margin + bvp | 15-5 (75%) | +5.08u |
| margin + consistency | 11-4 (73%) | +2.87u |
| margin + favorite + bvp | 13-5 (72%) | +2.93u |
| margin + favorite + consistency | 10-4 (71%) | +1.83u |
| favorite + consistency + bvp | 19-8 (70%) | +4.66u |
| line + bvp | 9-4 (69%) | +1.46u |
| favorite + line | 17-8 (68%) | +3.15u |
| margin + favorite | 21-10 (68%) | +3.74u |
| favorite + consistency | 28-14 (67%) | +5.46u |

## Tailing the side VEGAS needed (book_needs) vs outcome

| slice | record | units |
|---|---|---|
| all games with a book read (n=186) | 84-102 (45%) | -18.61u |
|   ...money % (n=11) | 4-7 (36%) | -2.60u |
|   ...ticket % (n=175) | 80-95 (46%) | -16.01u |
| (vs our advantage side, same games) | 105-81 (56%) | +5.14u |

## Tailing Vegas (bet the side book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| tail Vegas, all games (n=186) | 84-102 (45%) | -18.61u |
|   + our stat side agrees (n=63) | 33-30 (52%) | -0.83u |
|   + agrees & margin (n=8) | 5-3 (62%) | +0.87u |
|   + agrees & favorite (n=38) | 22-16 (58%) | +0.12u |
|   + agrees & line (n=5) | 4-1 (80%) | +1.69u |
|   + agrees & consistency (n=13) | 6-7 (46%) | -2.50u |
|   + agrees & bvp (n=24) | 10-14 (42%) | -5.48u |
|   + agrees & sharp (n=1) | 0-1 (0%) | -1.00u |
|   + agrees & form (n=3) | 1-2 (33%) | -0.95u |

## Tail Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=52) | 27-25 (52%) | -3.04u | -5.8% |
| ≥2 signals (n=23) | 11-12 (48%) | -3.72u | -16.2% |
| ≥3 signals (n=9) | 5-4 (56%) | -0.60u | -6.7% |
| ≥4 signals (n=4) | 3-1 (75%) | +0.69u | +17.2% |

## Fading Vegas (bet the OPPOSITE of book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| fade Vegas, all games (n=186) | 102-84 (55%) | +0.39u |
|   + our stat side agrees (n=123) | 72-51 (59%) | +5.96u |
|   + agrees & margin (n=25) | 19-6 (76%) | +7.40u |
|   + agrees & favorite (n=96) | 59-37 (61%) | +5.37u |
|   + agrees & line (n=22) | 15-7 (68%) | +3.61u |
|   + agrees & consistency (n=40) | 27-13 (68%) | +7.36u |
|   + agrees & bvp (n=64) | 40-24 (62%) | +6.43u |
|   + agrees & sharp (n=0) | 0 | — |
|   + agrees & form (n=8) | 6-2 (75%) | +2.88u |

## Fade Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=113) | 69-44 (61%) | +9.34u | +8.3% |
| ≥2 signals (n=81) | 53-28 (65%) | +10.99u | +13.6% |
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

_Point-in-time: signals recomputed from the frozen pre-game snapshot; winners from the MLB Stats API; $1/bet at the frozen moneyline. A signal with no recorded input on an older board is excluded from that row only (see n=)._