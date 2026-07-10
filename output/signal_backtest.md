# Signal backtest — 215 graded of 246 game snapshots

## Each signal alone (bet the advantage team when it fires)

| signal | record | units |
|---|---|---|
| margin (n=37) | 26-11 (70%) | +8.05u |
| favorite (n=153) | 89-64 (58%) | +1.01u |
| line (n=29) | 20-9 (69%) | +5.34u |
| consistency (n=61) | 37-24 (61%) | +4.35u |
| bvp (n=94) | 53-41 (56%) | +0.40u |
| sharp (n=3) | 1-2 (33%) | -1.23u |
| form (n=19) | 12-7 (63%) | +3.19u |
| live_dog (n=1) | 0-1 (0%) | -1.00u |

## By number of signals hit

| signals hit | record | units |
|---|---|---|
| 5/7 | 5-1 (83%) | +2.01u |
| 4/7 | 13-6 (68%) | +2.90u |
| 3/7 | 19-12 (61%) | +2.20u |
| 2/7 | 36-29 (55%) | +0.08u |
| 1/7 | 32-36 (47%) | -8.32u |
| 0/7 | 10-16 (38%) | -4.12u |

## Best signal combos (all present together, n≥10, by win%)

| combo | record | units |
|---|---|---|
| margin + consistency + bvp | 9-2 (82%) | +3.47u |
| line + consistency | 10-3 (77%) | +4.26u |
| margin + bvp | 16-5 (76%) | +6.04u |
| margin + consistency | 12-4 (75%) | +3.82u |
| margin + favorite + bvp | 14-5 (74%) | +3.89u |
| margin + favorite + consistency | 11-4 (73%) | +2.78u |
| favorite + line + consistency | 8-3 (73%) | +2.07u |
| favorite + consistency + bvp | 22-9 (71%) | +6.10u |
| line + bvp | 9-4 (69%) | +1.46u |
| margin + favorite | 22-10 (69%) | +4.69u |
| favorite + line + bvp | 8-4 (67%) | +0.32u |
| favorite + consistency | 31-16 (66%) | +5.90u |

## Tailing the side VEGAS needed (book_needs) vs outcome

| slice | record | units |
|---|---|---|
| all games with a book read (n=199) | 86-113 (43%) | -27.27u |
|   ...money % (n=22) | 6-16 (27%) | -9.26u |
|   ...ticket % (n=177) | 80-97 (45%) | -18.01u |
| (vs our advantage side, same games) | 112-87 (56%) | +4.89u |

## Tailing Vegas (bet the side book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| tail Vegas, all games (n=199) | 86-113 (43%) | -27.27u |
|   + our stat side agrees (n=69) | 34-35 (49%) | -4.78u |
|   + agrees & margin (n=8) | 5-3 (62%) | +0.87u |
|   + agrees & favorite (n=40) | 22-18 (55%) | -1.88u |
|   + agrees & line (n=7) | 5-2 (71%) | +1.74u |
|   + agrees & consistency (n=18) | 7-11 (39%) | -5.45u |
|   + agrees & bvp (n=27) | 10-17 (37%) | -8.48u |
|   + agrees & sharp (n=1) | 0-1 (0%) | -1.00u |
|   + agrees & form (n=6) | 2-4 (33%) | -1.90u |
|   + agrees & live_dog (n=1) | 0-1 (0%) | -1.00u |

## Tail Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=58) | 28-30 (48%) | -6.99u | -12.1% |
| ≥2 signals (n=27) | 12-15 (44%) | -5.67u | -21.0% |
| ≥3 signals (n=11) | 5-6 (45%) | -2.60u | -23.6% |
| ≥4 signals (n=4) | 3-1 (75%) | +0.69u | +17.2% |

## Fading Vegas (bet the OPPOSITE of book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| fade Vegas, all games (n=199) | 113-86 (57%) | +7.15u |
|   + our stat side agrees (n=130) | 78-52 (60%) | +9.67u |
|   + agrees & margin (n=26) | 20-6 (77%) | +8.35u |
|   + agrees & favorite (n=103) | 65-38 (63%) | +9.08u |
|   + agrees & line (n=22) | 15-7 (68%) | +3.61u |
|   + agrees & consistency (n=43) | 30-13 (70%) | +9.81u |
|   + agrees & bvp (n=67) | 43-24 (64%) | +8.88u |
|   + agrees & sharp (n=2) | 1-1 (50%) | -0.23u |
|   + agrees & form (n=13) | 10-3 (77%) | +5.09u |
|   + agrees & live_dog (n=0) | 0 | — |

## Fade Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=120) | 75-45 (62%) | +13.05u | +10.9% |
| ≥2 signals (n=86) | 57-29 (66%) | +13.21u | +15.4% |
| ≥3 signals (n=39) | 29-10 (74%) | +10.20u | +26.2% |
| ≥4 signals (n=16) | 11-5 (69%) | +2.04u | +12.8% |

## Best MULTI-signal fade combos (stat side agrees, n≥10)

| combo | record | units |
|---|---|---|
| consistency + bvp | 21-6 (78%) | +9.24u |
| favorite + consistency + bvp | 19-5 (79%) | +8.10u |
| margin + bvp | 13-4 (76%) | +5.27u |
| margin + consistency + bvp | 8-2 (80%) | +3.10u |
| margin + consistency | 11-4 (73%) | +3.45u |
| margin + favorite | 17-6 (74%) | +5.16u |
| margin + favorite + bvp | 11-4 (73%) | +3.12u |
| favorite + consistency | 26-11 (70%) | +7.46u |
| margin + favorite + consistency | 10-4 (71%) | +2.41u |
| favorite + line | 14-7 (67%) | +2.47u |

## Our pick when the book's informed money was AGAINST us (⚠️ bucket)

| slice | record | units |
|---|---|---|
| stance-against plays (n=50) | 26-24 (52%) | -3.40u |

## NEW BOARD GATE — fade + core signal (what makes the board now)

| slice | record | units |
|---|---|---|
| BOARD: fade + core signal (n=64) | 45-19 (70%) | +15.01u |
| DROPPED: tail + core signal (was played, now cut) (n=27) | 12-15 (44%) | -4.95u |

## Threshold sweeps on the fade side (does a tighter bar help?)

| margin ≥ | record | units |
|---|---|---|
| 0.30 | 34-22 (61%) | +3.17u |
| 0.40 | 29-13 (69%) | +8.34u |
| 0.50 | 20-6 (77%) | +8.35u |
| 0.60 | 7-2 (78%) | +2.79u |
| 0.70 | 2-1 (67%) | +0.11u |

| consistency (out-hit) ≥ | record | units |
|---|---|---|
| 3/5 | 30-13 (70%) | +9.81u |
| 4/5 | 8-5 (62%) | +1.34u |
| 5/5 | 5-1 (83%) | +2.94u |

## Does line-shading improve our picks? (our picks by shading gap)

| shading gap (tickets − implied) | record | units |
|---|---|---|
| < 5 (not shaded) | 54-42 (56%) | +1.66u |
| 5–15 (mild) | 41-35 (54%) | -2.31u |
| ≥ 15 (heavy shade) | 16-16 (50%) | -1.16u |

## Underdog study — our stat side priced as a DOG (ml > 0)

| slice | record | units | ROI/bet |
|---|---|---|---|
| all underdogs (n=62) | 26-36 (42%) | -6.26u | -10% |
| + edge margin ≥.50 (n=5) | 4-1 (80%) | +3.36u | +67% |
| + BvP edge (n=26) | 10-16 (38%) | -4.62u | -18% |
| + consistency ≥3 (n=14) | 6-8 (43%) | -1.55u | -11% |
| + FIP edge ≥0.15 (live-dog half, full coverage) (n=28) | 13-15 (46%) | -0.08u | -0% |
| + LIVE DOG (FIP & form; only 9 dogs have form data) (n=1) | 0-1 (0%) | -1.00u | -100% |

## What winning underdogs have in common (26 winners vs 36 losers)

| stat (advantage side edge) | winners median | losers median |
|---|---|---|
| team-score edge | +0.164 | +0.157 |
| edge margin | +0.192 | +0.177 |
| offense-index edge | +0.207 | +0.166 |
| pitching-index edge | +0.034 | -0.012 |
| FIP edge (opp−ours) | +0.138 | -0.051 |
| wOBA edge (park-neutral) | +0.048 | +0.037 |
| ISO edge (park-neutral) | +0.070 | +0.048 |
| K% gap | -0.028 | -0.002 |
| BvP edge (signed) | -0.004 | -0.012 |
| hot-lineup edge | +0.127 | +0.025 |
| dog price (ml) | +113.500 | +118.500 |

## Every underdog + signal combo (bet the dog, n≥5, by units)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin | 4-1 (80%) | +3.36u | +67% |
| form | 3-3 (50%) | +0.15u | +2% |
| consistency | 6-8 (43%) | -1.55u | -11% |
| consistency + bvp | 2-5 (29%) | -2.86u | -41% |
| bvp | 10-16 (38%) | -4.62u | -18% |
| (any dog) | 26-36 (42%) | -6.26u | -10% |

## ALL signal combinations — every graded pick (every signal subset, n≥10, by ROI/bet)

| combo | record | units | ROI/bet |
|---|---|---|---|
| line + consistency | 10-3 (77%) | +4.26u | +33% |
| margin + favorite + consistency + bvp | 9-2 (82%) | +3.47u | +32% |
| margin + consistency + bvp | 9-2 (82%) | +3.47u | +32% |
| margin + bvp | 16-5 (76%) | +6.04u | +29% |
| margin + consistency | 12-4 (75%) | +3.82u | +24% |
| favorite + form | 9-4 (69%) | +3.04u | +23% |
| margin | 26-11 (70%) | +8.05u | +22% |
| margin + favorite + bvp | 14-5 (74%) | +3.89u | +20% |
| favorite + consistency + bvp | 22-9 (71%) | +6.10u | +20% |
| favorite + line + consistency | 8-3 (73%) | +2.07u | +19% |
| margin + favorite + consistency | 11-4 (73%) | +2.78u | +19% |
| line | 20-9 (69%) | +5.34u | +18% |
| form | 12-7 (63%) | +3.19u | +17% |
| margin + favorite | 22-10 (69%) | +4.69u | +15% |
| favorite + consistency | 31-16 (66%) | +5.90u | +13% |
| line + bvp | 9-4 (69%) | +1.46u | +11% |
| consistency + bvp | 24-14 (63%) | +3.24u | +9% |
| favorite + line | 17-9 (65%) | +2.15u | +8% |
| favorite + bvp | 43-25 (63%) | +5.02u | +7% |
| consistency | 37-24 (61%) | +4.35u | +7% |

## ALL signal combinations — FADE-GATED picks (live board condition) (every signal subset, n≥10, by ROI/bet)

| combo | record | units | ROI/bet |
|---|---|---|---|
| form | 10-3 (77%) | +5.09u | +39% |
| consistency + bvp | 21-6 (78%) | +9.24u | +34% |
| favorite + consistency + bvp | 19-5 (79%) | +8.10u | +34% |
| favorite + form | 9-3 (75%) | +4.04u | +34% |
| margin | 20-6 (77%) | +8.35u | +32% |
| margin + bvp | 13-4 (76%) | +5.27u | +31% |
| margin + favorite + consistency + bvp | 8-2 (80%) | +3.10u | +31% |
| margin + consistency + bvp | 8-2 (80%) | +3.10u | +31% |
| margin + consistency | 11-4 (73%) | +3.45u | +23% |
| consistency | 30-13 (70%) | +9.81u | +23% |
| margin + favorite | 17-6 (74%) | +5.16u | +22% |
| margin + favorite + bvp | 11-4 (73%) | +3.12u | +21% |
| favorite + consistency | 26-11 (70%) | +7.46u | +20% |
| margin + favorite + consistency | 10-4 (71%) | +2.41u | +17% |
| line | 15-7 (68%) | +3.61u | +16% |
| bvp | 43-24 (64%) | +8.88u | +13% |
| favorite + line | 14-7 (67%) | +2.47u | +12% |
| favorite + bvp | 35-18 (66%) | +6.12u | +12% |
| favorite | 65-38 (63%) | +9.08u | +9% |
| line + bvp | 6-4 (60%) | -0.23u | -2% |

_Point-in-time: signals recomputed from the frozen pre-game snapshot; winners from the MLB Stats API; $1/bet at the frozen moneyline. A signal with no recorded input on an older board is excluded from that row only (see n=)._