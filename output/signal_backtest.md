# Signal backtest — 348 graded of 373 game snapshots

## Each signal alone (bet the advantage team when it fires)

| signal | record | units |
|---|---|---|
| margin (n=53) | 34-19 (64%) | +5.36u |
| favorite (n=263) | 145-118 (55%) | -12.05u |
| line (n=72) | 43-29 (60%) | +0.66u |
| consistency (n=132) | 70-62 (53%) | -6.38u |
| bvp (n=187) | 94-93 (50%) | -20.05u |
| sharp (n=7) | 3-4 (43%) | -1.69u |
| form (n=100) | 49-51 (49%) | -9.89u |
| pitching_dog (n=2) | 0-2 (0%) | -2.00u |

## By number of signals hit

| signals hit | record | units |
|---|---|---|
| 6/7 | 0-1 (0%) | -1.00u |
| 5/7 | 12-7 (63%) | +0.67u |
| 4/7 | 30-28 (52%) | -6.18u |
| 3/7 | 39-32 (55%) | -2.45u |
| 2/7 | 52-45 (54%) | -2.89u |
| 1/7 | 37-39 (49%) | -5.55u |
| 0/7 | 10-16 (38%) | -4.12u |

## Best signal combos (all present together, n≥10, by win%)

| combo | record | units |
|---|---|---|
| margin + line | 14-3 (82%) | +5.51u |
| margin + favorite + line | 14-3 (82%) | +5.51u |
| margin + line + bvp | 9-2 (82%) | +3.26u |
| margin + favorite + bvp | 20-9 (69%) | +3.91u |
| margin + favorite | 30-15 (67%) | +5.00u |
| margin + bvp | 22-12 (65%) | +3.06u |
| margin + favorite + consistency | 12-8 (60%) | -0.58u |
| favorite + consistency + bvp | 43-30 (59%) | +1.21u |
| margin + consistency + bvp | 10-7 (59%) | -0.89u |
| favorite + line | 39-29 (57%) | -3.61u |
| margin + consistency | 13-10 (57%) | -1.54u |
| favorite + consistency | 58-45 (56%) | -2.46u |

## Tailing the side VEGAS needed (book_needs) vs outcome

| slice | record | units |
|---|---|---|
| all games with a book read (n=332) | 142-190 (43%) | -44.11u |
|   ...money % (n=131) | 49-82 (37%) | -27.60u |
|   ...ticket % (n=201) | 93-108 (46%) | -16.51u |
| (vs our advantage side, same games) | 177-155 (53%) | -11.38u |

## Tailing Vegas (bet the side book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| tail Vegas, all games (n=332) | 142-190 (43%) | -44.11u |
|   + our stat side agrees (n=119) | 53-66 (45%) | -17.55u |
|   + agrees & margin (n=14) | 5-9 (36%) | -5.13u |
|   + agrees & favorite (n=71) | 34-37 (48%) | -11.15u |
|   + agrees & line (n=18) | 10-8 (56%) | -0.29u |
|   + agrees & consistency (n=49) | 20-29 (41%) | -11.35u |
|   + agrees & bvp (n=64) | 23-41 (36%) | -21.24u |
|   + agrees & sharp (n=1) | 0-1 (0%) | -1.00u |
|   + agrees & form (n=40) | 15-25 (38%) | -9.99u |
|   + agrees & pitching_dog (n=2) | 0-2 (0%) | -2.00u |

## Tail Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=106) | 45-61 (42%) | -22.82u | -21.5% |
| ≥2 signals (n=65) | 25-40 (38%) | -19.43u | -29.9% |
| ≥3 signals (n=32) | 16-16 (50%) | -3.45u | -10.8% |
| ≥4 signals (n=12) | 5-7 (42%) | -3.82u | -31.8% |

## Fading Vegas (bet the OPPOSITE of book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| fade Vegas, all games (n=332) | 190-142 (57%) | +13.95u |
|   + our stat side agrees (n=213) | 124-89 (58%) | +6.17u |
|   + agrees & margin (n=36) | 28-8 (78%) | +11.66u |
|   + agrees & favorite (n=182) | 109-73 (60%) | +5.29u |
|   + agrees & line (n=54) | 33-21 (61%) | +0.94u |
|   + agrees & consistency (n=83) | 50-33 (60%) | +4.97u |
|   + agrees & bvp (n=123) | 71-52 (58%) | +1.19u |
|   + agrees & sharp (n=6) | 3-3 (50%) | -0.69u |
|   + agrees & form (n=60) | 34-26 (57%) | +0.10u |
|   + agrees & pitching_dog (n=0) | 0 | — |

## Fade Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=201) | 120-81 (60%) | +9.45u | +4.7% |
| ≥2 signals (n=162) | 99-63 (61%) | +9.35u | +5.8% |
| ≥3 signals (n=89) | 54-35 (61%) | +2.43u | +2.7% |
| ≥4 signals (n=30) | 19-11 (63%) | +1.13u | +3.8% |

## Best MULTI-signal fade combos (stat side agrees, n≥10)

| combo | record | units |
|---|---|---|
| margin + line | 12-2 (86%) | +5.62u |
| margin + favorite + line | 12-2 (86%) | +5.62u |
| margin + bvp | 19-5 (79%) | +8.29u |
| margin + favorite + bvp | 17-5 (77%) | +6.14u |
| margin + favorite | 25-8 (76%) | +8.47u |
| margin + consistency + bvp | 9-3 (75%) | +2.74u |
| margin + consistency | 12-6 (67%) | +2.09u |
| consistency + bvp | 35-21 (62%) | +4.87u |
| favorite + consistency + bvp | 32-19 (63%) | +3.54u |
| margin + favorite + consistency | 11-6 (65%) | +1.05u |

## Our pick when the book's informed money was AGAINST us (⚠️ bucket)

| slice | record | units |
|---|---|---|
| stance-against plays (n=78) | 41-37 (53%) | -5.23u |

## NEW BOARD GATE — fade + core signal (what makes the board now)

| slice | record | units |
|---|---|---|
| BOARD: fade + core signal (n=101) | 66-35 (65%) | +14.54u |
| DROPPED: tail + core signal (was played, now cut) (n=58) | 24-34 (41%) | -12.85u |

## Board leak-finder — the live board by core-signal type

_Which picks on the current board (fade + core) carry ROI, and which are the drag we could tighten out. All bet the fade side, $1/pick._

| board subset | record | units | ROI/bet |
|---|---|---|---|
| has MARGIN (with anything) (n=36) | 28-8 (78%) | +11.66u | +32.4% |
| NO margin (core = line/consistency only) (n=65) | 38-27 (58%) | +2.88u | +4.4% |
|   ...line-only core (no margin, no consistency) | 0 | — | — |
|   ...consistency-only core (no margin, no line) (n=51) | 31-20 (61%) | +4.99u | +9.8% |
|   ...line AND consistency (no margin) (n=14) | 7-7 (50%) | -2.11u | -15.1% |
| 2+ core signals together (n=42) | 28-14 (67%) | +4.91u | +11.7% |

## Starred (⭐) plays vs the rest of the board

_The board split by the current star rule. Both bet the fade side, $1/pick._

| board tier | record | units | ROI/bet |
|---|---|---|---|
| ⭐ STARRED plays (n=28) | 20-8 (71%) | +4.82u | +17.2% |
| ✅ the rest of the board (n=73) | 46-27 (63%) | +9.71u | +13.3% |
| whole board (both tiers) (n=101) | 66-35 (65%) | +14.54u | +14.4% |

## Threshold sweeps on the fade side (does a tighter bar help?)

| margin ≥ | record | units |
|---|---|---|
| 0.30 | 52-35 (60%) | +3.04u |
| 0.40 | 40-21 (66%) | +8.16u |
| 0.50 | 28-8 (78%) | +11.66u |
| 0.60 | 13-3 (81%) | +5.74u |
| 0.70 | 3-1 (75%) | +0.75u |

| consistency (out-hit) ≥ | record | units |
|---|---|---|
| 3/5 | 50-33 (60%) | +4.97u |
| 4/5 | 16-14 (53%) | -1.29u |
| 5/5 | 5-3 (62%) | +0.94u |

## Does line-shading improve our picks? (our picks by shading gap)

| shading gap (tickets − implied) | record | units |
|---|---|---|
| < 5 (not shaded) | 81-74 (52%) | -7.33u |
| 5–15 (mild) | 75-67 (53%) | -9.27u |
| ≥ 15 (heavy shade) | 19-20 (49%) | -2.58u |

## Line-move timing — sharp window vs public window (n=34)

_open→11pm = instant strike on the fresh opener; open→6am = the full overnight/sharp window; 6am→close = daytime (public). Needs the off-hours snapshots, so n grows from the day those crons started._

| move toward us happened | record | units |
|---|---|---|
| overnight only (sharp) | 4-2 (67%) | +1.41u |
| daytime only (public) | 11-12 (48%) | -5.03u |
| both windows | 3-2 (60%) | -0.23u |
| instant strike on the opener (open→11pm) | 0 | — |
| overnight drift after the strike window (11pm→6am) | 0 | — |

## Polymarket vs the book — same picks, PM's frozen price (n=214)

_PM price is the gamma-API quote frozen in the snapshot: a mid/last price with no fee or slippage modeling, so treat PM units as a best-case. Unopened 50/50 placeholder markets excluded._

| venue (same picks, same outcomes) | record | units | ROI/bet |
|---|---|---|---|
| book (real prices) | 110-104 (51%) | -18.20u | -8.5% |
| Polymarket (frozen quote) | 110-104 (same games) | -6.01u | -2.8% |

_Avg price gap: PM sells our side +2.8 prob. points vs the book (positive = PM cheaper). PM was >=1pt cheaper on 195 of 214 picks._

_On those 195 PM-cheaper picks: book 104-91 -11.32u vs PM +0.78u._

_ARBITRAGE windows (PM one side + book the other, combined implied < 100%): 17 of 214 games; margins avg 6.3%, best 22.1%._

## Underdog study — our stat side priced as a DOG (ml > 0)

| slice | record | units | ROI/bet |
|---|---|---|---|
| all underdogs (n=85) | 35-50 (41%) | -9.47u | -11% |
| + edge margin ≥.50 (n=8) | 4-4 (50%) | +0.36u | +4% |
| + BvP edge (n=41) | 13-28 (32%) | -13.25u | -32% |
| + consistency ≥3 (n=29) | 12-17 (41%) | -3.92u | -14% |
| + FIP edge ≥.15 (pitching-edge dogs) (n=38) | 17-21 (45%) | -0.73u | -2% |
| + margin & BvP (n=5) | 2-3 (40%) | -0.85u | -17% |
| + consistency & BvP (n=18) | 5-13 (28%) | -7.49u | -42% |

## When money sources disagree — bet our stat side (n=39)

_The '⚠️ money sources disagree' flag fires rarely; every slice here is small — treat as exploratory, not a proven edge._

| slice | record | units | ROI/bet |
|---|---|---|---|
| advantage side (flag on) (n=39) | 23-16 (59%) | +4.17u | +11% |
| + margin (n=4) | 3-1 (75%) | +1.59u | +40% |
| + favorite (n=31) | 18-13 (58%) | +1.77u | +6% |
| + line (n=10) | 6-4 (60%) | +1.31u | +13% |
| + consistency (n=21) | 12-9 (57%) | +1.66u | +8% |
| + bvp (n=26) | 15-11 (58%) | +2.31u | +9% |
| + sharp | 0 | — | — |
| + form (n=18) | 9-9 (50%) | -0.94u | -5% |
| + pitching_dog (n=1) | 0-1 (0%) | -1.00u | -100% |
| + ≥1 signals stacked (n=38) | 22-16 (58%) | +3.04u | +8% |
| + ≥2 signals stacked (n=35) | 20-15 (57%) | +2.51u | +7% |
| + ≥3 signals stacked (n=23) | 13-10 (57%) | +1.34u | +6% |
| fade side (opp. of book_needs), flag on (n=39) | 22-17 (56%) | +2.18u | +6% |

_Signal combos inside the flag (bet our side, n≥3, by units):_

| combo | record | units | ROI/bet |
|---|---|---|---|
| consistency + bvp (n=14) | 9-5 (64%) | +2.99u | +21% |
| margin + favorite + bvp (n=3) | 3-0 (100%) | +2.59u | +86% |
| margin + bvp (n=3) | 3-0 (100%) | +2.59u | +86% |
| bvp (n=26) | 15-11 (58%) | +2.31u | +9% |
| favorite + consistency + bvp (n=9) | 6-3 (67%) | +1.77u | +20% |
| favorite (n=31) | 18-13 (58%) | +1.77u | +6% |
| consistency (n=21) | 12-9 (57%) | +1.66u | +8% |
| margin + favorite (n=4) | 3-1 (75%) | +1.59u | +40% |
| margin (n=4) | 3-1 (75%) | +1.59u | +40% |
| favorite + consistency + bvp + form (n=4) | 3-1 (75%) | +1.56u | +39% |
| line + consistency + bvp (n=6) | 4-2 (67%) | +1.48u | +25% |
| line + consistency (n=8) | 5-3 (62%) | +1.45u | +18% |
| favorite + consistency + form (n=8) | 5-3 (62%) | +1.40u | +18% |
| line (n=10) | 6-4 (60%) | +1.31u | +13% |
| consistency + bvp + form (n=7) | 4-3 (57%) | +0.64u | +9% |
| line + bvp (n=7) | 4-3 (57%) | +0.48u | +7% |
| consistency + form (n=11) | 6-5 (55%) | +0.48u | +4% |
| favorite + consistency (n=16) | 9-7 (56%) | +0.44u | +3% |
| line + consistency + form (n=4) | 2-2 (50%) | +0.05u | +1% |
| favorite + bvp (n=20) | 11-9 (55%) | +0.04u | +0% |
| favorite + form (n=13) | 7-6 (54%) | -0.07u | -1% |
| line + form (n=6) | 3-3 (50%) | -0.09u | -2% |
| favorite + line + consistency + bvp (n=4) | 2-2 (50%) | -0.74u | -18% |
| favorite + line + consistency (n=6) | 3-3 (50%) | -0.77u | -13% |
| favorite + line (n=8) | 4-4 (50%) | -0.91u | -11% |
| line + bvp + form (n=3) | 1-2 (33%) | -0.92u | -31% |
| form (n=18) | 9-9 (50%) | -0.94u | -5% |
| favorite + line + consistency + form (n=3) | 1-2 (33%) | -1.03u | -34% |
| favorite + line + form (n=5) | 2-3 (40%) | -1.17u | -23% |
| bvp + form (n=11) | 5-6 (45%) | -1.31u | -12% |
| favorite + bvp + form (n=7) | 3-4 (43%) | -1.44u | -21% |
| favorite + line + bvp (n=5) | 2-3 (40%) | -1.74u | -35% |

## What winning underdogs have in common (35 winners vs 50 losers)

| stat (advantage side edge) | winners median | losers median |
|---|---|---|
| team-score edge | +0.137 | +0.158 |
| edge margin | +0.187 | +0.183 |
| offense-index edge | +0.190 | +0.183 |
| pitching-index edge | +0.029 | +0.002 |
| FIP edge (opp−ours) | +0.118 | +0.005 |
| wOBA edge (park-neutral) | +0.057 | +0.046 |
| ISO edge (park-neutral) | +0.059 | +0.051 |
| K% gap | -0.024 | -0.004 |
| BvP edge (signed) | -0.025 | +0.014 |
| hot-lineup edge | +0.049 | +0.065 |
| dog price (ml) | +113.000 | +118.500 |

## Every underdog + signal combo (bet the dog, n≥5, by units)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin | 4-4 (50%) | +0.36u | +4% |
| margin + bvp | 2-3 (40%) | -0.85u | -17% |
| consistency + form | 7-9 (44%) | -1.46u | -9% |
| consistency | 12-17 (41%) | -3.92u | -14% |
| form | 11-17 (39%) | -4.25u | -15% |
| consistency + bvp + form | 2-8 (20%) | -5.82u | -58% |
| consistency + bvp | 5-13 (28%) | -7.49u | -42% |
| (any dog) | 35-50 (41%) | -9.47u | -11% |
| bvp + form | 3-15 (17%) | -11.77u | -65% |
| bvp | 13-28 (32%) | -13.25u | -32% |

## Value bet — our projected odds vs the market (n=348)

_proj_edge = our stat-projected win% minus the market's implied %. Positive = we think our side is underpriced. Recomputed from margin so it spans every graded game._

| our edge over the market | record | units | ROI/bet |
|---|---|---|---|
| market richer than us (<0) (n=126) | 72-54 (57%) | -5.25u | -4.2% |
| slight (0–5 pts) (n=74) | 39-35 (53%) | -2.78u | -3.8% |
| moderate (5–10) (n=87) | 43-44 (49%) | -5.09u | -5.9% |
| strong (10–20) (n=51) | 23-28 (45%) | -5.38u | -10.5% |
| huge (20+) (n=10) | 3-7 (30%) | -3.03u | -30.3% |

| bet only when edge ≥ | record | units | ROI/bet |
|---|---|---|---|
| 0 pts (n=222) | 108-114 (49%) | -16.28u | -7.3% |
| 3 pts (n=175) | 85-90 (49%) | -10.61u | -6.1% |
| 5 pts (n=148) | 69-79 (47%) | -13.50u | -9.1% |
| 8 pts (n=90) | 40-50 (44%) | -10.05u | -11.2% |
| 12 pts (n=48) | 20-28 (42%) | -6.97u | -14.5% |
| 15 pts (n=29) | 10-19 (34%) | -6.94u | -23.9% |

## Polymarket money agreeing with our pick (n=214)

_pm_edge = PM's implied % for our side minus the market's implied %. Positive = PM's live money leans our way harder than the sportsbook._

| PM lean vs the book | record | units | ROI/bet |
|---|---|---|---|
| PM against us (< -3) (n=56) | 27-29 (48%) | -8.69u | -15.5% |
| ≈ agree (±3) (n=156) | 83-73 (53%) | -7.51u | -4.8% |
| PM with us (3–8) | 0 | — | — |
| PM hard with us (8+) (n=2) | 0-2 (0%) | -2.00u | -100.0% |

## Sharp-window line move × core signal (n=162 core picks)

| slice | record | units | ROI/bet |
|---|---|---|---|
| core signal, any (n=162) | 91-71 (56%) | +0.52u | +0.3% |
| core + moved in the SHARP window (early) (n=5) | 4-1 (80%) | +2.25u | +45.0% |
| core + moved only in the PUBLIC window (late) (n=14) | 7-7 (50%) | -2.55u | -18.2% |
| core + sharps STRUCK the fresh opener | 0 | — | — |

## Value edge + core signal together

| slice | record | units | ROI/bet |
|---|---|---|---|
| proj_edge ≥5 AND a core signal (n=84) | 43-41 (51%) | -3.67u | -4.4% |
| proj_edge ≥8 AND a core signal (n=53) | 28-25 (53%) | +0.40u | +0.8% |
| proj_edge ≥12 AND a core signal (n=31) | 15-16 (48%) | -1.95u | -6.3% |

## ALL signal combinations — every graded pick (every signal subset, n≥10, by ROI/bet)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin + line | 14-3 (82%) | +5.51u | +32% |
| margin + favorite + line | 14-3 (82%) | +5.51u | +32% |
| margin + line + bvp | 9-2 (82%) | +3.26u | +30% |
| margin + favorite + line + bvp | 9-2 (82%) | +3.26u | +30% |
| margin + favorite + bvp + form | 8-4 (67%) | +1.82u | +15% |
| margin + favorite + form | 10-5 (67%) | +2.11u | +14% |
| margin + favorite + bvp | 20-9 (69%) | +3.91u | +13% |
| margin + favorite | 30-15 (67%) | +5.00u | +11% |
| margin | 34-19 (64%) | +5.36u | +10% |
| margin + bvp | 22-12 (65%) | +3.06u | +9% |
| margin + favorite + consistency + bvp | 10-5 (67%) | +1.11u | +7% |
| favorite + consistency + bvp | 43-30 (59%) | +1.21u | +2% |
| line | 43-29 (60%) | +0.66u | +1% |
| favorite + consistency | 58-45 (56%) | -2.46u | -2% |
| margin + favorite + consistency | 12-8 (60%) | -0.58u | -3% |
| favorite | 145-118 (55%) | -12.05u | -5% |
| favorite + bvp | 81-65 (55%) | -6.80u | -5% |
| consistency | 70-62 (53%) | -6.38u | -5% |
| margin + form | 10-8 (56%) | -0.89u | -5% |
| margin + consistency + bvp | 10-7 (59%) | -0.89u | -5% |

_worst 6:_
| combo | record | units | ROI/bet |
|---|---|---|---|
| favorite + line + consistency | 13-14 (48%) | -5.90u | -22% |
| line + bvp + form | 8-10 (44%) | -4.29u | -24% |
| line + consistency + form | 5-8 (38%) | -3.64u | -28% |
| bvp + form | 27-40 (40%) | -18.96u | -28% |
| favorite + line + bvp + form | 7-10 (41%) | -5.37u | -32% |
| favorite + line + consistency + form | 3-8 (27%) | -5.77u | -52% |

## ALL signal combinations — FADE-GATED picks (live board condition) (every signal subset, n≥10, by ROI/bet)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin + form | 10-2 (83%) | +5.11u | +43% |
| margin + favorite + form | 10-2 (83%) | +5.11u | +43% |
| margin + line | 12-2 (86%) | +5.62u | +40% |
| margin + favorite + line | 12-2 (86%) | +5.62u | +40% |
| margin + bvp | 19-5 (79%) | +8.29u | +35% |
| margin | 28-8 (78%) | +11.66u | +32% |
| margin + favorite + bvp | 17-5 (77%) | +6.14u | +28% |
| margin + favorite | 25-8 (76%) | +8.47u | +26% |
| margin + favorite + consistency + bvp | 9-3 (75%) | +2.74u | +23% |
| margin + consistency + bvp | 9-3 (75%) | +2.74u | +23% |
| margin + consistency | 12-6 (67%) | +2.09u | +12% |
| consistency + bvp | 35-21 (62%) | +4.87u | +9% |
| favorite + consistency + bvp | 32-19 (63%) | +3.54u | +7% |
| margin + favorite + consistency | 11-6 (65%) | +1.05u | +6% |
| consistency | 50-33 (60%) | +4.97u | +6% |
| favorite + consistency | 45-30 (60%) | +2.43u | +3% |
| favorite | 109-73 (60%) | +5.29u | +3% |
| line | 33-21 (61%) | +0.94u | +2% |
| bvp | 71-52 (58%) | +1.19u | +1% |
| form | 34-26 (57%) | +0.10u | +0% |

_worst 6:_
| combo | record | units | ROI/bet |
|---|---|---|---|
| favorite + line + consistency | 9-8 (53%) | -2.56u | -15% |
| favorite + line + consistency + bvp | 6-5 (55%) | -1.69u | -15% |
| line + bvp | 15-14 (52%) | -4.66u | -16% |
| favorite + line + bvp | 14-14 (50%) | -5.80u | -21% |
| line + bvp + form | 5-8 (38%) | -4.65u | -36% |
| favorite + line + bvp + form | 5-8 (38%) | -4.65u | -36% |

_Point-in-time: signals recomputed from the frozen pre-game snapshot; winners from the MLB Stats API; $1/bet at the frozen moneyline. A signal with no recorded input on an older board is excluded from that row only (see n=)._