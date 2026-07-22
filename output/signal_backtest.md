# Signal backtest — 335 graded of 373 game snapshots

## Each signal alone (bet the advantage team when it fires)

| signal | record | units |
|---|---|---|
| margin (n=48) | 32-16 (67%) | +7.13u |
| favorite (n=253) | 140-113 (55%) | -10.37u |
| line (n=63) | 39-24 (62%) | +3.26u |
| consistency (n=124) | 67-57 (54%) | -3.92u |
| bvp (n=176) | 89-87 (51%) | -17.37u |
| sharp (n=7) | 3-4 (43%) | -1.69u |
| form (n=92) | 46-46 (50%) | -7.56u |
| pitching_dog (n=0) | 0 | — |

## By number of signals hit

| signals hit | record | units |
|---|---|---|
| 5/7 | 11-6 (65%) | +1.06u |
| 4/7 | 27-23 (54%) | -3.21u |
| 3/7 | 38-32 (54%) | -3.13u |
| 2/7 | 51-45 (53%) | -4.02u |
| 1/7 | 37-39 (49%) | -5.55u |
| 0/7 | 10-16 (38%) | -4.12u |

## Best signal combos (all present together, n≥10, by win%)

| combo | record | units |
|---|---|---|
| margin + line | 12-1 (92%) | +6.28u |
| margin + favorite + line | 12-1 (92%) | +6.28u |
| margin + favorite + bvp | 18-8 (69%) | +3.67u |
| margin + favorite | 28-13 (68%) | +5.77u |
| margin + bvp | 20-10 (67%) | +3.82u |
| margin + favorite + consistency | 12-6 (67%) | +1.42u |
| margin + consistency + bvp | 10-6 (62%) | +0.11u |
| margin + consistency | 13-8 (62%) | +0.46u |
| line + consistency + bvp | 11-7 (61%) | +0.70u |
| favorite + consistency + bvp | 41-27 (60%) | +2.80u |
| line + consistency | 15-10 (60%) | +0.88u |
| favorite + line | 35-24 (59%) | -1.01u |

## Tailing the side VEGAS needed (book_needs) vs outcome

| slice | record | units |
|---|---|---|
| all games with a book read (n=319) | 139-180 (44%) | -37.82u |
|   ...money % (n=120) | 47-73 (39%) | -21.17u |
|   ...ticket % (n=199) | 92-107 (46%) | -16.65u |
| (vs our advantage side, same games) | 171-148 (54%) | -8.83u |

## Tailing Vegas (bet the side book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| tail Vegas, all games (n=319) | 139-180 (44%) | -37.82u |
|   + our stat side agrees (n=113) | 52-61 (46%) | -13.68u |
|   + agrees & margin (n=12) | 5-7 (42%) | -3.13u |
|   + agrees & favorite (n=68) | 34-34 (50%) | -8.15u |
|   + agrees & line (n=15) | 10-5 (67%) | +2.71u |
|   + agrees & consistency (n=44) | 19-25 (43%) | -8.48u |
|   + agrees & bvp (n=59) | 23-36 (39%) | -16.24u |
|   + agrees & sharp (n=1) | 0-1 (0%) | -1.00u |
|   + agrees & form (n=36) | 14-22 (39%) | -8.12u |
|   + agrees & pitching_dog (n=0) | 0 | — |

## Tail Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=100) | 44-56 (44%) | -18.95u | -18.9% |
| ≥2 signals (n=60) | 25-35 (42%) | -14.43u | -24.1% |
| ≥3 signals (n=29) | 16-13 (55%) | -0.45u | -1.6% |
| ≥4 signals (n=9) | 5-4 (56%) | -0.82u | -9.1% |

## Fading Vegas (bet the OPPOSITE of book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| fade Vegas, all games (n=319) | 180-139 (56%) | +8.02u |
|   + our stat side agrees (n=206) | 119-87 (58%) | +4.85u |
|   + agrees & margin (n=33) | 26-7 (79%) | +11.43u |
|   + agrees & favorite (n=175) | 104-71 (59%) | +3.97u |
|   + agrees & line (n=48) | 29-19 (60%) | +0.55u |
|   + agrees & consistency (n=80) | 48-32 (60%) | +4.55u |
|   + agrees & bvp (n=117) | 66-51 (56%) | -1.13u |
|   + agrees & sharp (n=6) | 3-3 (50%) | -0.69u |
|   + agrees & form (n=56) | 32-24 (57%) | +0.56u |
|   + agrees & pitching_dog (n=0) | 0 | — |

## Fade Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=194) | 115-79 (59%) | +8.13u | +4.2% |
| ≥2 signals (n=155) | 94-61 (61%) | +8.03u | +5.2% |
| ≥3 signals (n=82) | 49-33 (60%) | +1.11u | +1.4% |
| ≥4 signals (n=26) | 16-10 (62%) | +0.41u | +1.6% |

## Best MULTI-signal fade combos (stat side agrees, n≥10)

| combo | record | units |
|---|---|---|
| margin + line | 10-1 (91%) | +5.38u |
| margin + favorite + line | 10-1 (91%) | +5.38u |
| margin + bvp | 17-5 (77%) | +7.05u |
| margin + favorite | 23-7 (77%) | +8.24u |
| margin + favorite + bvp | 15-5 (75%) | +4.90u |
| margin + consistency + bvp | 9-3 (75%) | +2.74u |
| margin + consistency | 12-5 (71%) | +3.09u |
| margin + favorite + consistency | 11-5 (69%) | +2.05u |
| consistency + bvp | 33-21 (61%) | +3.46u |
| favorite + consistency + bvp | 30-19 (61%) | +2.13u |

## Our pick when the book's informed money was AGAINST us (⚠️ bucket)

| slice | record | units |
|---|---|---|
| stance-against plays (n=78) | 41-37 (53%) | -5.23u |

## NEW BOARD GATE — fade + core signal (what makes the board now)

| slice | record | units |
|---|---|---|
| BOARD: fade + core signal (n=96) | 62-34 (65%) | +12.89u |
| DROPPED: tail + core signal (was played, now cut) (n=52) | 23-29 (44%) | -8.98u |

## Board leak-finder — the live board by core-signal type

_Which picks on the current board (fade + core) carry ROI, and which are the drag we could tighten out. All bet the fade side, $1/pick._

| board subset | record | units | ROI/bet |
|---|---|---|---|
| has MARGIN (with anything) (n=33) | 26-7 (79%) | +11.43u | +34.6% |
| NO margin (core = line/consistency only) (n=63) | 36-27 (57%) | +1.46u | +2.3% |
|   ...line-only core (no margin, no consistency) | 0 | — | — |
|   ...consistency-only core (no margin, no line) (n=50) | 30-20 (60%) | +4.06u | +8.1% |
|   ...line AND consistency (no margin) (n=13) | 6-7 (46%) | -2.60u | -20.0% |
| 2+ core signals together (n=38) | 25-13 (66%) | +4.19u | +11.0% |

## Threshold sweeps on the fade side (does a tighter bar help?)

| margin ≥ | record | units |
|---|---|---|
| 0.30 | 48-34 (59%) | +1.40u |
| 0.40 | 38-20 (66%) | +7.93u |
| 0.50 | 26-7 (79%) | +11.43u |
| 0.60 | 12-3 (80%) | +5.13u |
| 0.70 | 3-1 (75%) | +0.75u |

| consistency (out-hit) ≥ | record | units |
|---|---|---|
| 3/5 | 48-32 (60%) | +4.55u |
| 4/5 | 15-14 (52%) | -2.21u |
| 5/5 | 5-3 (62%) | +0.94u |

## Does line-shading improve our picks? (our picks by shading gap)

| shading gap (tickets − implied) | record | units |
|---|---|---|
| < 5 (not shaded) | 79-70 (53%) | -4.94u |
| 5–15 (mild) | 71-64 (53%) | -9.10u |
| ≥ 15 (heavy shade) | 19-20 (49%) | -2.58u |

## Line-move timing — sharp window vs public window (n=26)

_open→11pm = instant strike on the fresh opener; open→6am = the full overnight/sharp window; 6am→close = daytime (public). Needs the off-hours snapshots, so n grows from the day those crons started._

| move toward us happened | record | units |
|---|---|---|
| overnight only (sharp) | 4-2 (67%) | +1.41u |
| daytime only (public) | 8-7 (53%) | -1.75u |
| both windows | 3-2 (60%) | -0.23u |
| instant strike on the opener (open→11pm) | 0 | — |
| overnight drift after the strike window (11pm→6am) | 0 | — |

## Polymarket vs the book — same picks, PM's frozen price (n=201)

_PM price is the gamma-API quote frozen in the snapshot: a mid/last price with no fee or slippage modeling, so treat PM units as a best-case. Unopened 50/50 placeholder markets excluded._

| venue (same picks, same outcomes) | record | units | ROI/bet |
|---|---|---|---|
| book (real prices) | 104-97 (52%) | -15.65u | -7.8% |
| Polymarket (frozen quote) | 104-97 (same games) | -4.12u | -2.0% |

_Avg price gap: PM sells our side +2.8 prob. points vs the book (positive = PM cheaper). PM was >=1pt cheaper on 183 of 201 picks._

_On those 183 PM-cheaper picks: book 98-85 -9.77u vs PM +1.66u._

_ARBITRAGE windows (PM one side + book the other, combined implied < 100%): 14 of 201 games; margins avg 7.3%, best 22.1%._

## Underdog study — our stat side priced as a DOG (ml > 0)

| slice | record | units | ROI/bet |
|---|---|---|---|
| all underdogs (n=82) | 34-48 (41%) | -8.60u | -10% |
| + edge margin ≥.50 (n=7) | 4-3 (57%) | +1.36u | +19% |
| + BvP edge (n=39) | 13-26 (33%) | -11.25u | -29% |
| + consistency ≥3 (n=27) | 11-16 (41%) | -4.05u | -15% |
| + FIP edge ≥.15 (pitching-edge dogs) (n=36) | 17-19 (47%) | +1.27u | +4% |
| + margin & BvP (n=4) | 2-2 (50%) | +0.15u | +4% |
| + consistency & BvP (n=17) | 5-12 (29%) | -6.49u | -38% |

## When money sources disagree — bet our stat side (n=37)

_The '⚠️ money sources disagree' flag fires rarely; every slice here is small — treat as exploratory, not a proven edge._

| slice | record | units | ROI/bet |
|---|---|---|---|
| advantage side (flag on) (n=37) | 23-14 (62%) | +6.17u | +17% |
| + margin (n=3) | 3-0 (100%) | +2.59u | +86% |
| + favorite (n=30) | 18-12 (60%) | +2.77u | +9% |
| + line (n=9) | 6-3 (67%) | +2.31u | +26% |
| + consistency (n=19) | 12-7 (63%) | +3.66u | +19% |
| + bvp (n=25) | 15-10 (60%) | +3.31u | +13% |
| + sharp | 0 | — | — |
| + form (n=16) | 9-7 (56%) | +1.06u | +7% |
| + pitching_dog | 0 | — | — |
| + ≥1 signals stacked (n=36) | 22-14 (61%) | +5.04u | +14% |
| + ≥2 signals stacked (n=33) | 20-13 (61%) | +4.51u | +14% |
| + ≥3 signals stacked (n=21) | 13-8 (62%) | +3.34u | +16% |
| fade side (opp. of book_needs), flag on (n=37) | 21-16 (57%) | +2.49u | +7% |

_Signal combos inside the flag (bet our side, n≥3, by units):_

| combo | record | units | ROI/bet |
|---|---|---|---|
| consistency + bvp (n=13) | 9-4 (69%) | +3.99u | +31% |
| consistency (n=19) | 12-7 (63%) | +3.66u | +19% |
| bvp (n=25) | 15-10 (60%) | +3.31u | +13% |
| favorite (n=30) | 18-12 (60%) | +2.77u | +9% |
| margin + favorite + bvp (n=3) | 3-0 (100%) | +2.59u | +86% |
| margin + favorite (n=3) | 3-0 (100%) | +2.59u | +86% |
| margin + bvp (n=3) | 3-0 (100%) | +2.59u | +86% |
| margin (n=3) | 3-0 (100%) | +2.59u | +86% |
| consistency + form (n=9) | 6-3 (67%) | +2.48u | +28% |
| line + consistency (n=7) | 5-2 (71%) | +2.45u | +35% |
| favorite + consistency + form (n=7) | 5-2 (71%) | +2.40u | +34% |
| line (n=9) | 6-3 (67%) | +2.31u | +26% |
| favorite + consistency + bvp (n=9) | 6-3 (67%) | +1.77u | +20% |
| consistency + bvp + form (n=6) | 4-2 (67%) | +1.64u | +27% |
| favorite + consistency + bvp + form (n=4) | 3-1 (75%) | +1.56u | +39% |
| line + consistency + bvp (n=6) | 4-2 (67%) | +1.48u | +25% |
| favorite + consistency (n=15) | 9-6 (60%) | +1.44u | +10% |
| form (n=16) | 9-7 (56%) | +1.06u | +7% |
| line + consistency + form (n=3) | 2-1 (67%) | +1.05u | +35% |
| favorite + form (n=12) | 7-5 (58%) | +0.93u | +8% |
| line + form (n=5) | 3-2 (60%) | +0.91u | +18% |
| line + bvp (n=7) | 4-3 (57%) | +0.48u | +7% |
| favorite + line + consistency (n=5) | 3-2 (60%) | +0.23u | +5% |
| favorite + line (n=7) | 4-3 (57%) | +0.09u | +1% |
| favorite + bvp (n=20) | 11-9 (55%) | +0.04u | +0% |
| favorite + line + form (n=4) | 2-2 (50%) | -0.17u | -4% |
| bvp + form (n=10) | 5-5 (50%) | -0.31u | -3% |
| favorite + line + consistency + bvp (n=4) | 2-2 (50%) | -0.74u | -18% |
| line + bvp + form (n=3) | 1-2 (33%) | -0.92u | -31% |
| favorite + bvp + form (n=7) | 3-4 (43%) | -1.44u | -21% |
| favorite + line + bvp (n=5) | 2-3 (40%) | -1.74u | -35% |

## What winning underdogs have in common (34 winners vs 48 losers)

| stat (advantage side edge) | winners median | losers median |
|---|---|---|
| team-score edge | +0.146 | +0.157 |
| edge margin | +0.188 | +0.164 |
| offense-index edge | +0.198 | +0.183 |
| pitching-index edge | +0.034 | -0.004 |
| FIP edge (opp−ours) | +0.138 | -0.015 |
| wOBA edge (park-neutral) | +0.048 | +0.043 |
| ISO edge (park-neutral) | +0.064 | +0.051 |
| K% gap | -0.022 | -0.004 |
| BvP edge (signed) | -0.006 | +0.001 |
| hot-lineup edge | +0.048 | +0.057 |
| dog price (ml) | +113.000 | +118.500 |

## Every underdog + signal combo (bet the dog, n≥5, by units)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin | 4-3 (57%) | +1.36u | +19% |
| consistency + form | 6-8 (43%) | -1.59u | -11% |
| form | 10-15 (40%) | -3.38u | -14% |
| consistency | 11-16 (41%) | -4.05u | -15% |
| consistency + bvp + form | 2-7 (22%) | -4.82u | -54% |
| consistency + bvp | 5-12 (29%) | -6.49u | -38% |
| (any dog) | 34-48 (41%) | -8.60u | -10% |
| bvp + form | 3-13 (19%) | -9.77u | -61% |
| bvp | 13-26 (33%) | -11.25u | -29% |

## Value bet — our projected odds vs the market (n=335)

_proj_edge = our stat-projected win% minus the market's implied %. Positive = we think our side is underpriced. Recomputed from margin so it spans every graded game._

| our edge over the market | record | units | ROI/bet |
|---|---|---|---|
| market richer than us (<0) (n=121) | 70-51 (58%) | -3.41u | -2.8% |
| slight (0–5 pts) (n=73) | 38-35 (52%) | -3.40u | -4.7% |
| moderate (5–10) (n=82) | 40-42 (49%) | -5.76u | -7.0% |
| strong (10–20) (n=49) | 23-26 (47%) | -3.38u | -6.9% |
| huge (20+) (n=10) | 3-7 (30%) | -3.03u | -30.3% |

| bet only when edge ≥ | record | units | ROI/bet |
|---|---|---|---|
| 0 pts (n=214) | 104-110 (49%) | -15.56u | -7.3% |
| 3 pts (n=167) | 81-86 (49%) | -9.89u | -5.9% |
| 5 pts (n=141) | 66-75 (47%) | -12.16u | -8.6% |
| 8 pts (n=84) | 38-46 (45%) | -8.11u | -9.7% |
| 12 pts (n=46) | 20-26 (43%) | -4.97u | -10.8% |
| 15 pts (n=28) | 10-18 (36%) | -5.94u | -21.2% |

## Polymarket money agreeing with our pick (n=201)

_pm_edge = PM's implied % for our side minus the market's implied %. Positive = PM's live money leans our way harder than the sportsbook._

| PM lean vs the book | record | units | ROI/bet |
|---|---|---|---|
| PM against us (< -3) (n=50) | 24-26 (48%) | -7.72u | -15.4% |
| ≈ agree (±3) (n=149) | 80-69 (54%) | -5.93u | -4.0% |
| PM with us (3–8) | 0 | — | — |
| PM hard with us (8+) (n=2) | 0-2 (0%) | -2.00u | -100.0% |

## Sharp-window line move × core signal (n=151 core picks)

| slice | record | units | ROI/bet |
|---|---|---|---|
| core signal, any (n=151) | 86-65 (57%) | +2.74u | +1.8% |
| core + moved in the SHARP window (early) (n=5) | 4-1 (80%) | +2.25u | +45.0% |
| core + moved only in the PUBLIC window (late) (n=7) | 4-3 (57%) | -0.27u | -3.9% |
| core + sharps STRUCK the fresh opener | 0 | — | — |

## Value edge + core signal together

| slice | record | units | ROI/bet |
|---|---|---|---|
| proj_edge ≥5 AND a core signal (n=77) | 40-37 (52%) | -2.34u | -3.0% |
| proj_edge ≥8 AND a core signal (n=47) | 26-21 (55%) | +2.34u | +5.0% |
| proj_edge ≥12 AND a core signal (n=29) | 15-14 (52%) | +0.05u | +0.2% |

## ALL signal combinations — every graded pick (every signal subset, n≥10, by ROI/bet)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin + line | 12-1 (92%) | +6.28u | +48% |
| margin + favorite + line | 12-1 (92%) | +6.28u | +48% |
| margin + favorite + form | 9-3 (75%) | +3.50u | +29% |
| margin + favorite + bvp + form | 7-3 (70%) | +2.21u | +22% |
| margin + favorite + consistency + bvp | 10-4 (71%) | +2.11u | +15% |
| margin | 32-16 (67%) | +7.13u | +15% |
| margin + favorite + bvp | 18-8 (69%) | +3.67u | +14% |
| margin + favorite | 28-13 (68%) | +5.77u | +14% |
| margin + bvp | 20-10 (67%) | +3.82u | +13% |
| margin + form | 9-5 (64%) | +1.50u | +11% |
| margin + favorite + consistency | 12-6 (67%) | +1.42u | +8% |
| line | 39-24 (62%) | +3.26u | +5% |
| favorite + consistency + bvp | 41-27 (60%) | +2.80u | +4% |
| line + consistency + bvp | 11-7 (61%) | +0.70u | +4% |
| line + consistency | 15-10 (60%) | +0.88u | +4% |
| margin + consistency | 13-8 (62%) | +0.46u | +2% |
| margin + bvp + form | 7-5 (58%) | +0.21u | +2% |
| margin + consistency + bvp | 10-6 (62%) | +0.11u | +1% |
| favorite + consistency | 56-41 (58%) | +0.13u | +0% |
| favorite + line | 35-24 (59%) | -1.01u | -2% |

_worst 6:_
| combo | record | units | ROI/bet |
|---|---|---|---|
| line + consistency + form | 5-6 (45%) | -1.64u | -15% |
| favorite + bvp + form | 22-23 (49%) | -6.73u | -15% |
| consistency + bvp + form | 16-19 (46%) | -6.27u | -18% |
| line + bvp + form | 7-8 (47%) | -2.90u | -19% |
| bvp + form | 25-36 (41%) | -16.50u | -27% |
| favorite + line + bvp + form | 6-8 (43%) | -3.98u | -28% |

## ALL signal combinations — FADE-GATED picks (live board condition) (every signal subset, n≥10, by ROI/bet)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin + form | 9-1 (90%) | +5.50u | +55% |
| margin + favorite + form | 9-1 (90%) | +5.50u | +55% |
| margin + line | 10-1 (91%) | +5.38u | +49% |
| margin + favorite + line | 10-1 (91%) | +5.38u | +49% |
| margin | 26-7 (79%) | +11.43u | +35% |
| margin + bvp | 17-5 (77%) | +7.05u | +32% |
| margin + favorite | 23-7 (77%) | +8.24u | +27% |
| margin + favorite + bvp | 15-5 (75%) | +4.90u | +25% |
| margin + favorite + consistency + bvp | 9-3 (75%) | +2.74u | +23% |
| margin + consistency + bvp | 9-3 (75%) | +2.74u | +23% |
| margin + consistency | 12-5 (71%) | +3.09u | +18% |
| margin + favorite + consistency | 11-5 (69%) | +2.05u | +13% |
| consistency + bvp | 33-21 (61%) | +3.46u | +6% |
| consistency | 48-32 (60%) | +4.55u | +6% |
| favorite + consistency + bvp | 30-19 (61%) | +2.13u | +4% |
| favorite + consistency | 43-29 (60%) | +2.01u | +3% |
| favorite | 104-71 (59%) | +3.97u | +2% |
| line | 29-19 (60%) | +0.55u | +1% |
| form | 32-24 (57%) | +0.56u | +1% |
| favorite + form | 30-22 (58%) | +0.41u | +1% |

_worst 6:_
| combo | record | units | ROI/bet |
|---|---|---|---|
| consistency + bvp + form | 10-11 (48%) | -3.58u | -17% |
| favorite + line + consistency + bvp | 5-5 (50%) | -2.18u | -22% |
| line + bvp | 11-13 (46%) | -6.05u | -25% |
| favorite + line + bvp | 10-13 (43%) | -7.19u | -31% |
| line + bvp + form | 4-7 (36%) | -4.27u | -39% |
| favorite + line + bvp + form | 4-7 (36%) | -4.27u | -39% |

_Point-in-time: signals recomputed from the frozen pre-game snapshot; winners from the MLB Stats API; $1/bet at the frozen moneyline. A signal with no recorded input on an older board is excluded from that row only (see n=)._