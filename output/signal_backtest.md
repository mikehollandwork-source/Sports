# Signal backtest — 196 graded of 218 game snapshots

## Each signal alone (bet the advantage team when it fires)

| signal | record | units |
|---|---|---|
| margin (n=36) | 25-11 (69%) | +7.10u |
| favorite (n=139) | 79-60 (57%) | -2.89u |
| line (n=26) | 18-8 (69%) | +4.32u |
| consistency (n=50) | 30-20 (60%) | +2.36u |
| bvp (n=83) | 47-36 (57%) | +0.73u |
| sharp (n=1) | 0-1 (0%) | -1.00u |
| form (n=6) | 4-2 (67%) | +1.57u |

## By number of signals hit

| signals hit | record | units |
|---|---|---|
| 5/7 | 4-1 (80%) | +1.06u |
| 4/7 | 10-5 (67%) | +1.48u |
| 3/7 | 14-8 (64%) | +2.11u |
| 2/7 | 35-27 (56%) | +1.35u |
| 1/7 | 31-35 (47%) | -8.09u |
| 0/7 | 10-16 (38%) | -4.12u |

## Best signal combos (all present together, n≥10, by win%)

| combo | record | units |
|---|---|---|
| line + consistency | 8-2 (80%) | +3.24u |
| margin + consistency + bvp | 8-2 (80%) | +2.52u |
| margin + bvp | 15-5 (75%) | +5.08u |
| margin + consistency | 11-4 (73%) | +2.87u |
| margin + favorite + bvp | 13-5 (72%) | +2.93u |
| margin + favorite + consistency | 10-4 (71%) | +1.83u |
| line + bvp | 9-4 (69%) | +1.46u |
| favorite + consistency + bvp | 17-8 (68%) | +3.13u |
| margin + favorite | 21-10 (68%) | +3.74u |
| favorite + line | 16-8 (67%) | +2.18u |
| favorite + line + bvp | 8-4 (67%) | +0.32u |
| favorite + consistency | 25-14 (64%) | +2.96u |

## Tailing the side VEGAS needed (book_needs) vs outcome

| slice | record | units |
|---|---|---|
| all games with a book read (n=180) | 82-98 (46%) | -16.68u |
|   ...money % (n=7) | 2-5 (29%) | -2.67u |
|   ...ticket % (n=173) | 80-93 (46%) | -14.01u |
| (vs our advantage side, same games) | 101-79 (56%) | +3.94u |

## Fading Vegas (bet the OPPOSITE of book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| fade Vegas, all games (n=180) | 98-82 (54%) | -0.34u |
|   + our stat side agrees (n=119) | 69-50 (58%) | +4.60u |
|   + agrees & margin (n=25) | 19-6 (76%) | +7.40u |
|   + agrees & favorite (n=92) | 56-36 (61%) | +4.01u |
|   + agrees & line (n=21) | 14-7 (67%) | +2.64u |
|   + agrees & consistency (n=38) | 25-13 (66%) | +5.70u |
|   + agrees & bvp (n=61) | 38-23 (62%) | +6.04u |
|   + agrees & sharp (n=0) | 0 | — |
|   + agrees & form (n=4) | 3-1 (75%) | +1.52u |

## Fade Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=109) | 66-43 (61%) | +7.98u | +7.3% |
| ≥2 signals (n=77) | 50-27 (65%) | +9.63u | +12.5% |
| ≥3 signals (n=34) | 24-10 (71%) | +6.09u | +17.9% |
| ≥4 signals (n=15) | 10-5 (67%) | +1.09u | +7.3% |

## Best MULTI-signal fade combos (stat side agrees, n≥10)

| combo | record | units |
|---|---|---|
| margin + bvp | 12-4 (75%) | +4.31u |
| consistency + bvp | 17-6 (74%) | +6.10u |
| favorite + consistency + bvp | 15-5 (75%) | +4.96u |
| margin + favorite | 16-6 (73%) | +4.21u |
| margin + consistency | 10-4 (71%) | +2.50u |
| margin + favorite + bvp | 10-4 (71%) | +2.16u |
| margin + favorite + consistency | 9-4 (69%) | +1.46u |
| favorite + consistency | 21-11 (66%) | +3.35u |
| favorite + line | 13-7 (65%) | +1.50u |
| favorite + bvp | 30-17 (64%) | +3.28u |

## Our pick when the book's informed money was AGAINST us (⚠️ bucket)

| slice | record | units |
|---|---|---|
| stance-against plays (n=44) | 22-22 (50%) | -4.48u |

_Point-in-time: signals recomputed from the frozen pre-game snapshot; winners from the MLB Stats API; $1/bet at the frozen moneyline. A signal with no recorded input on an older board is excluded from that row only (see n=)._