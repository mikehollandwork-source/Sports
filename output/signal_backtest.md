# Signal backtest — 261 graded of 278 game snapshots

## Each signal alone (bet the advantage team when it fires)

| signal | record | units |
|---|---|---|
| margin (n=41) | 28-13 (68%) | +7.34u |
| favorite (n=188) | 105-83 (56%) | -5.75u |
| line (n=41) | 26-15 (63%) | +3.59u |
| consistency (n=88) | 47-41 (53%) | -4.34u |
| bvp (n=124) | 64-60 (52%) | -9.69u |
| sharp (n=4) | 1-3 (25%) | -2.23u |
| form (n=47) | 24-23 (51%) | -1.74u |
| pitching_dog (n=0) | 0 | — |

## By number of signals hit

| signals hit | record | units |
|---|---|---|
| 5/7 | 6-3 (67%) | +0.69u |
| 4/7 | 18-14 (56%) | -1.62u |
| 3/7 | 25-20 (56%) | -0.94u |
| 2/7 | 41-35 (54%) | -1.31u |
| 1/7 | 36-37 (49%) | -4.32u |
| 0/7 | 10-16 (38%) | -4.12u |

## Best signal combos (all present together, n≥10, by win%)

| combo | record | units |
|---|---|---|
| margin + line | 9-1 (90%) | +4.13u |
| margin + favorite + line | 9-1 (90%) | +4.13u |
| margin + consistency + bvp | 9-3 (75%) | +2.47u |
| margin + favorite + consistency | 11-4 (73%) | +2.78u |
| margin + consistency | 12-5 (71%) | +2.82u |
| margin + favorite + bvp | 14-6 (70%) | +2.89u |
| margin + bvp | 16-7 (70%) | +4.04u |
| margin + favorite | 24-11 (69%) | +4.98u |
| favorite + consistency + bvp | 29-18 (62%) | +2.30u |
| line + consistency + bvp | 8-5 (62%) | +0.21u |
| line + bvp | 11-7 (61%) | -0.08u |
| favorite + line | 23-15 (61%) | +0.40u |

## Tailing the side VEGAS needed (book_needs) vs outcome

| slice | record | units |
|---|---|---|
| all games with a book read (n=245) | 106-139 (43%) | -30.36u |
|   ...money % (n=61) | 24-37 (39%) | -9.37u |
|   ...ticket % (n=184) | 82-102 (45%) | -20.99u |
| (vs our advantage side, same games) | 133-112 (54%) | -1.48u |

## Tailing Vegas (bet the side book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| tail Vegas, all games (n=245) | 106-139 (43%) | -30.36u |
|   + our stat side agrees (n=90) | 42-48 (47%) | -9.50u |
|   + agrees & margin (n=10) | 5-5 (50%) | -1.13u |
|   + agrees & favorite (n=52) | 27-25 (52%) | -4.70u |
|   + agrees & line (n=11) | 7-4 (64%) | +1.20u |
|   + agrees & consistency (n=30) | 11-19 (37%) | -10.01u |
|   + agrees & bvp (n=41) | 15-26 (37%) | -13.30u |
|   + agrees & sharp (n=1) | 0-1 (0%) | -1.00u |
|   + agrees & form (n=21) | 7-14 (33%) | -6.29u |
|   + agrees & pitching_dog (n=0) | 0 | — |

## Tail Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=77) | 34-43 (44%) | -14.77u | -19.2% |
| ≥2 signals (n=42) | 17-25 (40%) | -11.49u | -27.4% |
| ≥3 signals (n=19) | 9-10 (47%) | -3.41u | -17.9% |
| ≥4 signals (n=6) | 4-2 (67%) | +0.36u | +6.0% |

## Fading Vegas (bet the OPPOSITE of book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| fade Vegas, all games (n=245) | 139-106 (57%) | +9.81u |
|   + our stat side agrees (n=155) | 91-64 (59%) | +8.02u |
|   + agrees & margin (n=28) | 22-6 (79%) | +9.64u |
|   + agrees & favorite (n=126) | 76-50 (60%) | +5.14u |
|   + agrees & line (n=30) | 19-11 (63%) | +2.39u |
|   + agrees & consistency (n=58) | 36-22 (62%) | +5.67u |
|   + agrees & bvp (n=83) | 49-34 (59%) | +3.61u |
|   + agrees & sharp (n=3) | 1-2 (33%) | -1.23u |
|   + agrees & form (n=26) | 17-9 (65%) | +4.55u |
|   + agrees & pitching_dog (n=0) | 0 | — |

## Fade Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=144) | 87-57 (60%) | +10.30u | +7.2% |
| ≥2 signals (n=109) | 68-41 (62%) | +9.61u | +8.8% |
| ≥3 signals (n=54) | 35-19 (65%) | +5.29u | +9.8% |
| ≥4 signals (n=19) | 11-8 (58%) | -0.96u | -5.1% |

## Best MULTI-signal fade combos (stat side agrees, n≥10)

| combo | record | units |
|---|---|---|
| margin + bvp | 13-4 (76%) | +5.27u |
| margin + consistency + bvp | 8-2 (80%) | +3.10u |
| margin + favorite | 19-6 (76%) | +6.45u |
| margin + consistency | 11-4 (73%) | +3.45u |
| margin + favorite + bvp | 11-4 (73%) | +3.12u |
| margin + favorite + consistency | 10-4 (71%) | +2.41u |
| consistency + bvp | 26-13 (67%) | +6.22u |
| favorite + consistency + bvp | 23-12 (66%) | +3.89u |
| favorite + line | 18-11 (62%) | +1.25u |
| favorite + consistency | 31-20 (61%) | +2.13u |

## Our pick when the book's informed money was AGAINST us (⚠️ bucket)

| slice | record | units |
|---|---|---|
| stance-against plays (n=63) | 32-31 (51%) | -5.71u |

## NEW BOARD GATE — fade + core signal (what makes the board now)

| slice | record | units |
|---|---|---|
| BOARD: fade + core signal (n=83) | 55-28 (66%) | +13.65u |
| DROPPED: tail + core signal (was played, now cut) (n=42) | 17-25 (40%) | -10.71u |

## Threshold sweeps on the fade side (does a tighter bar help?)

| margin ≥ | record | units |
|---|---|---|
| 0.30 | 39-27 (59%) | +1.97u |
| 0.40 | 34-16 (68%) | +9.14u |
| 0.50 | 22-6 (79%) | +9.64u |
| 0.60 | 9-2 (82%) | +4.08u |
| 0.70 | 2-1 (67%) | +0.11u |

| consistency (out-hit) ≥ | record | units |
|---|---|---|
| 3/5 | 36-22 (62%) | +5.67u |
| 4/5 | 10-9 (53%) | -0.57u |
| 5/5 | 5-2 (71%) | +1.94u |

## Does line-shading improve our picks? (our picks by shading gap)

| shading gap (tickets − implied) | record | units |
|---|---|---|
| < 5 (not shaded) | 61-51 (54%) | -0.16u |
| 5–15 (mild) | 52-49 (51%) | -7.61u |
| ≥ 15 (heavy shade) | 18-18 (50%) | -1.51u |

## Line-move timing — sharp window vs public window (n=6)

_open→11pm = instant strike on the fresh opener; open→6am = the full overnight/sharp window; 6am→close = daytime (public). Needs the off-hours snapshots, so n grows from the day those crons started._

| move toward us happened | record | units |
|---|---|---|
| overnight only (sharp) | 3-0 (100%) | +2.33u |
| daytime only (public) | 1-1 (50%) | -0.33u |
| both windows | 0-1 (0%) | -1.00u |
| instant strike on the opener (open→11pm) | 0 | — |
| overnight drift after the strike window (11pm→6am) | 0 | — |

## Polymarket vs the book — same picks, PM's frozen price (n=134)

_PM price is the gamma-API quote frozen in the snapshot: a mid/last price with no fee or slippage modeling, so treat PM units as a best-case. Unopened 50/50 placeholder markets excluded._

| venue (same picks, same outcomes) | record | units | ROI/bet |
|---|---|---|---|
| book (real prices) | 69-65 (51%) | -9.74u | -7.3% |
| Polymarket (frozen quote) | 69-65 (same games) | -3.33u | -2.5% |

_Avg price gap: PM sells our side +2.8 prob. points vs the book (positive = PM cheaper). PM was >=1pt cheaper on 121 of 134 picks._

_On those 121 PM-cheaper picks: book 64-57 -7.03u vs PM -0.73u._

_ARBITRAGE windows (PM one side + book the other, combined implied < 100%): 11 of 134 games; margins avg 7.3%, best 22.1%._

## Underdog study — our stat side priced as a DOG (ml > 0)

| slice | record | units | ROI/bet |
|---|---|---|---|
| all underdogs (n=73) | 31-42 (42%) | -5.87u | -8% |
| + edge margin ≥.50 (n=6) | 4-2 (67%) | +2.36u | +39% |
| + BvP edge (n=32) | 11-21 (34%) | -8.43u | -26% |
| + consistency ≥3 (n=21) | 8-13 (38%) | -4.32u | -21% |
| + FIP edge ≥.15 (pitching-edge dogs) (n=33) | 17-16 (52%) | +4.27u | +13% |
| + margin & BvP (n=3) | 2-1 (67%) | +1.15u | +38% |
| + consistency & BvP (n=12) | 3-9 (25%) | -5.67u | -47% |

## When money sources disagree — bet our stat side (n=22)

_The '⚠️ money sources disagree' flag fires rarely; every slice here is small — treat as exploratory, not a proven edge._

| slice | record | units | ROI/bet |
|---|---|---|---|
| advantage side (flag on) (n=22) | 17-5 (77%) | +9.97u | +45% |
| + margin (n=3) | 3-0 (100%) | +2.59u | +86% |
| + favorite (n=17) | 13-4 (76%) | +6.65u | +39% |
| + line (n=5) | 4-1 (80%) | +2.41u | +48% |
| + consistency (n=12) | 8-4 (67%) | +2.90u | +24% |
| + bvp (n=14) | 11-3 (79%) | +6.55u | +47% |
| + sharp | 0 | — | — |
| + form (n=7) | 6-1 (86%) | +4.40u | +63% |
| + pitching_dog | 0 | — | — |
| + ≥1 signals stacked (n=21) | 16-5 (76%) | +8.84u | +42% |
| + ≥2 signals stacked (n=20) | 15-5 (75%) | +8.08u | +40% |
| + ≥3 signals stacked (n=11) | 9-2 (82%) | +5.57u | +51% |
| fade side (opp. of book_needs), flag on (n=22) | 16-6 (73%) | +7.94u | +36% |

_Signal combos inside the flag (bet our side, n≥3, by units):_

| combo | record | units | ROI/bet |
|---|---|---|---|
| favorite (n=17) | 13-4 (76%) | +6.65u | +39% |
| bvp (n=14) | 11-3 (79%) | +6.55u | +47% |
| form (n=7) | 6-1 (86%) | +4.40u | +63% |
| favorite + bvp (n=10) | 8-2 (80%) | +4.36u | +44% |
| favorite + form (n=5) | 5-0 (100%) | +4.35u | +87% |
| favorite + consistency + form (n=4) | 4-0 (100%) | +3.49u | +87% |
| consistency (n=12) | 8-4 (67%) | +2.90u | +24% |
| margin + favorite + bvp (n=3) | 3-0 (100%) | +2.59u | +86% |
| margin + favorite (n=3) | 3-0 (100%) | +2.59u | +86% |
| margin + bvp (n=3) | 3-0 (100%) | +2.59u | +86% |
| margin (n=3) | 3-0 (100%) | +2.59u | +86% |
| consistency + form (n=5) | 4-1 (80%) | +2.49u | +50% |
| line (n=5) | 4-1 (80%) | +2.41u | +48% |
| consistency + bvp (n=7) | 5-2 (71%) | +2.23u | +32% |
| favorite + consistency (n=9) | 6-3 (67%) | +1.76u | +20% |
| bvp + form (n=4) | 3-1 (75%) | +1.70u | +42% |
| line + consistency (n=4) | 3-1 (75%) | +1.56u | +39% |
| favorite + line (n=4) | 3-1 (75%) | +1.27u | +32% |
| favorite + consistency + bvp (n=4) | 3-1 (75%) | +1.09u | +27% |
| consistency + bvp + form (n=3) | 2-1 (67%) | +0.65u | +22% |
| line + consistency + bvp (n=3) | 2-1 (67%) | +0.58u | +19% |
| line + bvp (n=3) | 2-1 (67%) | +0.58u | +19% |
| favorite + line + consistency (n=3) | 2-1 (67%) | +0.42u | +14% |

## What winning underdogs have in common (31 winners vs 42 losers)

| stat (advantage side edge) | winners median | losers median |
|---|---|---|
| team-score edge | +0.156 | +0.157 |
| edge margin | +0.187 | +0.201 |
| offense-index edge | +0.190 | +0.183 |
| pitching-index edge | +0.044 | -0.017 |
| FIP edge (opp−ours) | +0.180 | -0.071 |
| wOBA edge (park-neutral) | +0.038 | +0.043 |
| ISO edge (park-neutral) | +0.068 | +0.050 |
| K% gap | -0.024 | -0.002 |
| BvP edge (signed) | -0.025 | -0.012 |
| hot-lineup edge | +0.049 | +0.076 |
| dog price (ml) | +114.000 | +121.000 |

## Every underdog + signal combo (bet the dog, n≥5, by units)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin | 4-2 (67%) | +2.36u | +39% |
| form | 7-9 (44%) | -0.65u | -4% |
| consistency + form | 3-5 (38%) | -1.86u | -23% |
| consistency | 8-13 (38%) | -4.32u | -21% |
| consistency + bvp | 3-9 (25%) | -5.67u | -47% |
| (any dog) | 31-42 (42%) | -5.87u | -8% |
| bvp + form | 1-8 (11%) | -6.95u | -77% |
| bvp | 11-21 (34%) | -8.43u | -26% |

## ALL signal combinations — every graded pick (every signal subset, n≥10, by ROI/bet)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin + line | 9-1 (90%) | +4.13u | +41% |
| margin + favorite + line | 9-1 (90%) | +4.13u | +41% |
| margin + favorite + consistency + bvp | 9-2 (82%) | +3.47u | +32% |
| margin + consistency + bvp | 9-3 (75%) | +2.47u | +21% |
| margin + favorite + consistency | 11-4 (73%) | +2.78u | +19% |
| margin | 28-13 (68%) | +7.34u | +18% |
| margin + bvp | 16-7 (70%) | +4.04u | +18% |
| margin + consistency | 12-5 (71%) | +2.82u | +17% |
| margin + favorite + bvp | 14-6 (70%) | +2.89u | +14% |
| margin + favorite | 24-11 (69%) | +4.98u | +14% |
| line | 26-15 (63%) | +3.59u | +9% |
| favorite + consistency + bvp | 29-18 (62%) | +2.30u | +5% |
| line + consistency + bvp | 8-5 (62%) | +0.21u | +2% |
| favorite + line | 23-15 (61%) | +0.40u | +1% |
| favorite + consistency | 39-28 (58%) | -0.02u | -0% |
| favorite + consistency + bvp + form | 8-6 (57%) | -0.04u | -0% |
| line + consistency | 11-8 (58%) | -0.07u | -0% |
| line + bvp | 11-7 (61%) | -0.08u | -0% |
| favorite + consistency + form | 10-8 (56%) | -0.19u | -1% |
| favorite + bvp | 53-39 (58%) | -1.26u | -1% |

_worst 6:_
| combo | record | units | ROI/bet |
|---|---|---|---|
| line + form | 6-6 (50%) | -1.16u | -10% |
| favorite + bvp + form | 10-10 (50%) | -2.58u | -13% |
| favorite + line + consistency | 9-8 (53%) | -2.26u | -13% |
| favorite + line + form | 5-6 (45%) | -2.21u | -20% |
| consistency + bvp + form | 8-10 (44%) | -4.04u | -22% |
| bvp + form | 11-18 (38%) | -9.53u | -33% |

## ALL signal combinations — FADE-GATED picks (live board condition) (every signal subset, n≥10, by ROI/bet)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin | 22-6 (79%) | +9.64u | +34% |
| margin + bvp | 13-4 (76%) | +5.27u | +31% |
| margin + favorite + consistency + bvp | 8-2 (80%) | +3.10u | +31% |
| margin + consistency + bvp | 8-2 (80%) | +3.10u | +31% |
| margin + favorite | 19-6 (76%) | +6.45u | +26% |
| margin + consistency | 11-4 (73%) | +3.45u | +23% |
| margin + favorite + bvp | 11-4 (73%) | +3.12u | +21% |
| form | 17-9 (65%) | +4.55u | +18% |
| margin + favorite + consistency | 10-4 (71%) | +2.41u | +17% |
| consistency + bvp | 26-13 (67%) | +6.22u | +16% |
| favorite + consistency + bvp | 23-12 (66%) | +3.89u | +11% |
| favorite + form | 15-9 (62%) | +2.40u | +10% |
| consistency | 36-22 (62%) | +5.67u | +10% |
| line | 19-11 (63%) | +2.39u | +8% |
| bvp | 49-34 (59%) | +3.61u | +4% |
| favorite + line | 18-11 (62%) | +1.25u | +4% |
| favorite + consistency | 31-20 (61%) | +2.13u | +4% |
| favorite | 76-50 (60%) | +5.14u | +4% |
| favorite + consistency + form | 8-6 (57%) | +0.29u | +2% |
| consistency + form | 8-6 (57%) | +0.29u | +2% |

_worst 6:_
| combo | record | units | ROI/bet |
|---|---|---|---|
| consistency + bvp + form | 6-5 (55%) | -0.55u | -5% |
| favorite + bvp + form | 8-7 (53%) | -1.09u | -7% |
| line + consistency | 7-6 (54%) | -0.96u | -7% |
| favorite + line + consistency | 6-6 (50%) | -2.10u | -18% |
| line + bvp | 6-6 (50%) | -2.23u | -19% |
| favorite + line + bvp | 5-6 (45%) | -3.37u | -31% |

_Point-in-time: signals recomputed from the frozen pre-game snapshot; winners from the MLB Stats API; $1/bet at the frozen moneyline. A signal with no recorded input on an older board is excluded from that row only (see n=)._