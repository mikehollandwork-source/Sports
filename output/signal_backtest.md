# Signal backtest — 322 graded of 356 game snapshots

## Each signal alone (bet the advantage team when it fires)

| signal | record | units |
|---|---|---|
| margin (n=47) | 31-16 (66%) | +6.49u |
| favorite (n=241) | 134-107 (56%) | -9.21u |
| line (n=60) | 38-22 (63%) | +4.44u |
| consistency (n=115) | 62-53 (54%) | -4.03u |
| bvp (n=165) | 83-82 (50%) | -17.21u |
| sharp (n=7) | 3-4 (43%) | -1.69u |
| form (n=83) | 43-40 (52%) | -3.92u |
| pitching_dog (n=0) | 0 | — |

## By number of signals hit

| signals hit | record | units |
|---|---|---|
| 5/7 | 10-5 (67%) | +1.42u |
| 4/7 | 24-21 (53%) | -3.75u |
| 3/7 | 37-30 (55%) | -2.05u |
| 2/7 | 50-43 (54%) | -2.75u |
| 1/7 | 37-39 (49%) | -5.55u |
| 0/7 | 10-16 (38%) | -4.12u |

## Best signal combos (all present together, n≥10, by win%)

| combo | record | units |
|---|---|---|
| margin + line | 12-1 (92%) | +6.28u |
| margin + favorite + line | 12-1 (92%) | +6.28u |
| margin + favorite + bvp | 17-8 (68%) | +3.03u |
| margin + favorite | 27-13 (68%) | +5.13u |
| margin + bvp | 19-10 (66%) | +3.18u |
| margin + favorite + consistency | 11-6 (65%) | +0.78u |
| line + consistency + bvp | 10-6 (62%) | +0.88u |
| line + consistency | 14-9 (61%) | +1.06u |
| favorite + line | 34-22 (61%) | +0.17u |
| margin + consistency | 12-8 (60%) | -0.18u |
| margin + consistency + bvp | 9-6 (60%) | -0.53u |
| favorite + consistency + bvp | 36-25 (59%) | +0.69u |

## Tailing the side VEGAS needed (book_needs) vs outcome

| slice | record | units |
|---|---|---|
| all games with a book read (n=306) | 132-174 (43%) | -38.49u |
|   ...money % (n=110) | 42-68 (38%) | -21.17u |
|   ...ticket % (n=196) | 90-106 (46%) | -17.32u |
| (vs our advantage side, same games) | 165-141 (54%) | -6.67u |

## Tailing Vegas (bet the side book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| tail Vegas, all games (n=306) | 132-174 (43%) | -38.49u |
|   + our stat side agrees (n=109) | 50-59 (46%) | -13.31u |
|   + agrees & margin (n=12) | 5-7 (42%) | -3.13u |
|   + agrees & favorite (n=64) | 32-32 (50%) | -7.78u |
|   + agrees & line (n=14) | 9-5 (64%) | +1.89u |
|   + agrees & consistency (n=41) | 17-24 (41%) | -9.11u |
|   + agrees & bvp (n=57) | 21-36 (37%) | -17.88u |
|   + agrees & sharp (n=1) | 0-1 (0%) | -1.00u |
|   + agrees & form (n=34) | 13-21 (38%) | -7.93u |
|   + agrees & pitching_dog (n=0) | 0 | — |

## Tail Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=96) | 42-54 (44%) | -18.58u | -19.4% |
| ≥2 signals (n=57) | 23-34 (40%) | -15.07u | -26.4% |
| ≥3 signals (n=27) | 14-13 (52%) | -2.08u | -7.7% |
| ≥4 signals (n=8) | 4-4 (50%) | -1.64u | -20.5% |

## Fading Vegas (bet the OPPOSITE of book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| fade Vegas, all games (n=306) | 174-132 (57%) | +9.83u |
|   + our stat side agrees (n=197) | 115-82 (58%) | +6.65u |
|   + agrees & margin (n=32) | 25-7 (78%) | +10.78u |
|   + agrees & favorite (n=167) | 100-67 (60%) | +4.77u |
|   + agrees & line (n=46) | 29-17 (63%) | +2.55u |
|   + agrees & consistency (n=74) | 45-29 (61%) | +5.08u |
|   + agrees & bvp (n=108) | 62-46 (57%) | +0.67u |
|   + agrees & sharp (n=6) | 3-3 (50%) | -0.69u |
|   + agrees & form (n=49) | 30-19 (61%) | +4.01u |
|   + agrees & pitching_dog (n=0) | 0 | — |

## Fade Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=185) | 111-74 (60%) | +9.93u | +5.4% |
| ≥2 signals (n=146) | 90-56 (62%) | +9.83u | +6.7% |
| ≥3 signals (n=76) | 46-30 (61%) | +1.64u | +2.2% |
| ≥4 signals (n=24) | 15-9 (62%) | +0.77u | +3.2% |

## Best MULTI-signal fade combos (stat side agrees, n≥10)

| combo | record | units |
|---|---|---|
| margin + line | 10-1 (91%) | +5.38u |
| margin + favorite + line | 10-1 (91%) | +5.38u |
| margin + bvp | 16-5 (76%) | +6.41u |
| margin + favorite | 22-7 (76%) | +7.59u |
| margin + favorite + bvp | 14-5 (74%) | +4.26u |
| margin + consistency + bvp | 8-3 (73%) | +2.10u |
| margin + consistency | 11-5 (69%) | +2.45u |
| margin + favorite + consistency | 10-5 (67%) | +1.41u |
| consistency + bvp | 30-18 (62%) | +3.98u |
| favorite + consistency + bvp | 27-17 (61%) | +1.65u |

## Our pick when the book's informed money was AGAINST us (⚠️ bucket)

| slice | record | units |
|---|---|---|
| stance-against plays (n=74) | 39-35 (53%) | -4.68u |

## NEW BOARD GATE — fade + core signal (what makes the board now)

| slice | record | units |
|---|---|---|
| BOARD: fade + core signal (n=113) | 72-41 (64%) | +12.18u |
| DROPPED: tail + core signal (was played, now cut) (n=54) | 24-30 (44%) | -9.20u |

## Threshold sweeps on the fade side (does a tighter bar help?)

| margin ≥ | record | units |
|---|---|---|
| 0.30 | 46-31 (60%) | +2.83u |
| 0.40 | 37-18 (67%) | +9.28u |
| 0.50 | 25-7 (78%) | +10.78u |
| 0.60 | 11-3 (79%) | +4.49u |
| 0.70 | 2-1 (67%) | +0.11u |

| consistency (out-hit) ≥ | record | units |
|---|---|---|
| 3/5 | 45-29 (61%) | +5.08u |
| 4/5 | 15-13 (54%) | -1.21u |
| 5/5 | 5-3 (62%) | +0.94u |

## Does line-shading improve our picks? (our picks by shading gap)

| shading gap (tickets − implied) | record | units |
|---|---|---|
| < 5 (not shaded) | 76-65 (54%) | -2.49u |
| 5–15 (mild) | 69-63 (52%) | -9.47u |
| ≥ 15 (heavy shade) | 18-19 (49%) | -2.51u |

## Line-move timing — sharp window vs public window (n=24)

_open→11pm = instant strike on the fresh opener; open→6am = the full overnight/sharp window; 6am→close = daytime (public). Needs the off-hours snapshots, so n grows from the day those crons started._

| move toward us happened | record | units |
|---|---|---|
| overnight only (sharp) | 4-2 (67%) | +1.41u |
| daytime only (public) | 8-6 (57%) | -0.75u |
| both windows | 2-2 (50%) | -1.05u |
| instant strike on the opener (open→11pm) | 0 | — |
| overnight drift after the strike window (11pm→6am) | 0 | — |

## Polymarket vs the book — same picks, PM's frozen price (n=189)

_PM price is the gamma-API quote frozen in the snapshot: a mid/last price with no fee or slippage modeling, so treat PM units as a best-case. Unopened 50/50 placeholder markets excluded._

| venue (same picks, same outcomes) | record | units | ROI/bet |
|---|---|---|---|
| book (real prices) | 99-90 (52%) | -12.56u | -6.6% |
| Polymarket (frozen quote) | 99-90 (same games) | -1.49u | -0.8% |

_Avg price gap: PM sells our side +2.8 prob. points vs the book (positive = PM cheaper). PM was >=1pt cheaper on 171 of 189 picks._

_On those 171 PM-cheaper picks: book 93-78 -6.68u vs PM +4.30u._

_ARBITRAGE windows (PM one side + book the other, combined implied < 100%): 14 of 189 games; margins avg 7.3%, best 22.1%._

## Underdog study — our stat side priced as a DOG (ml > 0)

| slice | record | units | ROI/bet |
|---|---|---|---|
| all underdogs (n=81) | 34-47 (42%) | -7.60u | -9% |
| + edge margin ≥.50 (n=7) | 4-3 (57%) | +1.36u | +19% |
| + BvP edge (n=38) | 13-25 (34%) | -10.25u | -27% |
| + consistency ≥3 (n=26) | 11-15 (42%) | -3.05u | -12% |
| + FIP edge ≥.15 (pitching-edge dogs) (n=35) | 17-18 (49%) | +2.27u | +6% |
| + margin & BvP (n=4) | 2-2 (50%) | +0.15u | +4% |
| + consistency & BvP (n=16) | 5-11 (31%) | -5.49u | -34% |

## When money sources disagree — bet our stat side (n=34)

_The '⚠️ money sources disagree' flag fires rarely; every slice here is small — treat as exploratory, not a proven edge._

| slice | record | units | ROI/bet |
|---|---|---|---|
| advantage side (flag on) (n=34) | 21-13 (62%) | +5.44u | +16% |
| + margin (n=3) | 3-0 (100%) | +2.59u | +86% |
| + favorite (n=27) | 16-11 (59%) | +2.04u | +8% |
| + line (n=7) | 5-2 (71%) | +2.49u | +36% |
| + consistency (n=16) | 10-6 (62%) | +2.93u | +18% |
| + bvp (n=22) | 13-9 (59%) | +2.59u | +12% |
| + sharp | 0 | — | — |
| + form (n=14) | 8-6 (57%) | +1.15u | +8% |
| + pitching_dog | 0 | — | — |
| + ≥1 signals stacked (n=33) | 20-13 (61%) | +4.31u | +13% |
| + ≥2 signals stacked (n=30) | 18-12 (60%) | +3.78u | +13% |
| + ≥3 signals stacked (n=18) | 11-7 (61%) | +2.61u | +14% |
| fade side (opp. of book_needs), flag on (n=34) | 20-14 (59%) | +3.58u | +11% |

_Signal combos inside the flag (bet our side, n≥3, by units):_

| combo | record | units | ROI/bet |
|---|---|---|---|
| consistency + bvp (n=10) | 7-3 (70%) | +3.26u | +33% |
| consistency (n=16) | 10-6 (62%) | +2.93u | +18% |
| line + consistency (n=5) | 4-1 (80%) | +2.64u | +53% |
| margin + favorite + bvp (n=3) | 3-0 (100%) | +2.59u | +86% |
| margin + favorite (n=3) | 3-0 (100%) | +2.59u | +86% |
| margin + bvp (n=3) | 3-0 (100%) | +2.59u | +86% |
| margin (n=3) | 3-0 (100%) | +2.59u | +86% |
| bvp (n=22) | 13-9 (59%) | +2.59u | +12% |
| consistency + form (n=7) | 5-2 (71%) | +2.57u | +37% |
| favorite + consistency + form (n=5) | 4-1 (80%) | +2.49u | +50% |
| line (n=7) | 5-2 (71%) | +2.49u | +36% |
| favorite (n=27) | 16-11 (59%) | +2.04u | +8% |
| line + form (n=4) | 3-1 (75%) | +1.91u | +48% |
| consistency + bvp + form (n=4) | 3-1 (75%) | +1.73u | +43% |
| line + consistency + bvp (n=4) | 3-1 (75%) | +1.66u | +42% |
| form (n=14) | 8-6 (57%) | +1.15u | +8% |
| favorite + consistency + bvp (n=6) | 4-2 (67%) | +1.04u | +17% |
| favorite + form (n=10) | 6-4 (60%) | +1.02u | +10% |
| favorite + line + form (n=3) | 2-1 (67%) | +0.83u | +28% |
| favorite + consistency (n=12) | 7-5 (58%) | +0.71u | +6% |
| line + bvp (n=5) | 3-2 (60%) | +0.66u | +13% |
| favorite + line + consistency (n=3) | 2-1 (67%) | +0.42u | +14% |
| favorite + line (n=5) | 3-2 (60%) | +0.27u | +5% |
| bvp + form (n=8) | 4-4 (50%) | -0.22u | -3% |
| favorite + bvp (n=17) | 9-8 (53%) | -0.68u | -4% |
| favorite + bvp + form (n=5) | 2-3 (40%) | -1.35u | -27% |
| favorite + line + bvp (n=3) | 1-2 (33%) | -1.56u | -52% |

## What winning underdogs have in common (34 winners vs 47 losers)

| stat (advantage side edge) | winners median | losers median |
|---|---|---|
| team-score edge | +0.146 | +0.157 |
| edge margin | +0.188 | +0.158 |
| offense-index edge | +0.198 | +0.189 |
| pitching-index edge | +0.034 | -0.007 |
| FIP edge (opp−ours) | +0.138 | -0.030 |
| wOBA edge (park-neutral) | +0.048 | +0.044 |
| ISO edge (park-neutral) | +0.064 | +0.050 |
| K% gap | -0.022 | -0.004 |
| BvP edge (signed) | -0.006 | -0.004 |
| hot-lineup edge | +0.048 | +0.062 |
| dog price (ml) | +113.000 | +119.000 |

## Every underdog + signal combo (bet the dog, n≥5, by units)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin | 4-3 (57%) | +1.36u | +19% |
| consistency + form | 6-7 (46%) | -0.59u | -5% |
| form | 10-14 (42%) | -2.38u | -10% |
| consistency | 11-15 (42%) | -3.05u | -12% |
| consistency + bvp + form | 2-6 (25%) | -3.82u | -48% |
| consistency + bvp | 5-11 (31%) | -5.49u | -34% |
| (any dog) | 34-47 (42%) | -7.60u | -9% |
| bvp + form | 3-12 (20%) | -8.77u | -58% |
| bvp | 13-25 (34%) | -10.25u | -27% |

## Value bet — our projected odds vs the market (n=322)

_proj_edge = our stat-projected win% minus the market's implied %. Positive = we think our side is underpriced. Recomputed from margin so it spans every graded game._

| our edge over the market | record | units | ROI/bet |
|---|---|---|---|
| market richer than us (<0) (n=116) | 66-50 (57%) | -5.68u | -4.9% |
| slight (0–5 pts) (n=71) | 38-33 (54%) | -1.40u | -2.0% |
| moderate (5–10) (n=78) | 39-39 (50%) | -3.68u | -4.7% |
| strong (10–20) (n=47) | 22-25 (47%) | -3.02u | -6.4% |
| huge (20+) (n=10) | 3-7 (30%) | -3.03u | -30.3% |

| bet only when edge ≥ | record | units | ROI/bet |
|---|---|---|---|
| 0 pts (n=206) | 102-104 (50%) | -11.13u | -5.4% |
| 3 pts (n=161) | 79-82 (49%) | -7.46u | -4.6% |
| 5 pts (n=135) | 64-71 (47%) | -9.73u | -7.2% |
| 8 pts (n=82) | 37-45 (45%) | -7.75u | -9.5% |
| 12 pts (n=45) | 19-26 (42%) | -5.61u | -12.5% |
| 15 pts (n=28) | 10-18 (36%) | -5.94u | -21.2% |

## Polymarket money agreeing with our pick (n=189)

_pm_edge = PM's implied % for our side minus the market's implied %. Positive = PM's live money leans our way harder than the sportsbook._

| PM lean vs the book | record | units | ROI/bet |
|---|---|---|---|
| PM against us (< -3) (n=47) | 23-24 (49%) | -6.63u | -14.1% |
| ≈ agree (±3) (n=140) | 76-64 (54%) | -3.93u | -2.8% |
| PM with us (3–8) | 0 | — | — |
| PM hard with us (8+) (n=2) | 0-2 (0%) | -2.00u | -100.0% |

## Sharp-window line move × core signal (n=170 core picks)

| slice | record | units | ROI/bet |
|---|---|---|---|
| core signal, any (n=170) | 97-73 (57%) | +1.80u | +1.1% |
| core + moved in the SHARP window (early) (n=9) | 6-3 (67%) | +1.36u | +15.1% |
| core + moved only in the PUBLIC window (late) (n=13) | 7-6 (54%) | -1.42u | -10.9% |
| core + sharps STRUCK the fresh opener | 0 | — | — |

## Value edge + core signal together

| slice | record | units | ROI/bet |
|---|---|---|---|
| proj_edge ≥5 AND a core signal (n=80) | 42-38 (52%) | -1.28u | -1.6% |
| proj_edge ≥8 AND a core signal (n=48) | 26-22 (54%) | +1.55u | +3.2% |
| proj_edge ≥12 AND a core signal (n=28) | 14-14 (50%) | -0.59u | -2.1% |

## ALL signal combinations — every graded pick (every signal subset, n≥10, by ROI/bet)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin + line | 12-1 (92%) | +6.28u | +48% |
| margin + favorite + line | 12-1 (92%) | +6.28u | +48% |
| margin + favorite + form | 8-3 (73%) | +2.86u | +26% |
| margin | 31-16 (66%) | +6.49u | +14% |
| margin + favorite | 27-13 (68%) | +5.13u | +13% |
| margin + favorite + bvp | 17-8 (68%) | +3.03u | +12% |
| margin + favorite + consistency + bvp | 9-4 (69%) | +1.47u | +11% |
| margin + bvp | 19-10 (66%) | +3.18u | +11% |
| line | 38-22 (63%) | +4.44u | +7% |
| line + form | 14-9 (61%) | +1.54u | +7% |
| margin + form | 8-5 (62%) | +0.86u | +7% |
| line + consistency + bvp | 10-6 (62%) | +0.88u | +6% |
| line + consistency | 14-9 (61%) | +1.06u | +5% |
| margin + favorite + consistency | 11-6 (65%) | +0.78u | +5% |
| favorite + consistency + bvp | 36-25 (59%) | +0.69u | +1% |
| favorite + line | 34-22 (61%) | +0.17u | +0% |
| margin + consistency | 12-8 (60%) | -0.18u | -1% |
| favorite + consistency | 51-38 (57%) | -0.98u | -1% |
| favorite + form | 33-26 (56%) | -1.54u | -3% |
| favorite + line + form | 12-9 (57%) | -0.59u | -3% |

_worst 6:_
| combo | record | units | ROI/bet |
|---|---|---|---|
| favorite + line + consistency | 11-9 (55%) | -2.21u | -11% |
| favorite + line + bvp | 16-13 (55%) | -3.43u | -12% |
| favorite + bvp + form | 19-19 (50%) | -5.10u | -13% |
| favorite + line + bvp + form | 6-6 (50%) | -1.98u | -16% |
| consistency + bvp + form | 13-16 (45%) | -5.64u | -19% |
| bvp + form | 22-31 (42%) | -13.87u | -26% |

## ALL signal combinations — FADE-GATED picks (live board condition) (every signal subset, n≥10, by ROI/bet)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin + line | 10-1 (91%) | +5.38u | +49% |
| margin + favorite + line | 10-1 (91%) | +5.38u | +49% |
| margin | 25-7 (78%) | +10.78u | +34% |
| margin + bvp | 16-5 (76%) | +6.41u | +31% |
| margin + favorite | 22-7 (76%) | +7.59u | +26% |
| margin + favorite + bvp | 14-5 (74%) | +4.26u | +22% |
| margin + favorite + consistency + bvp | 8-3 (73%) | +2.10u | +19% |
| margin + consistency + bvp | 8-3 (73%) | +2.10u | +19% |
| margin + consistency | 11-5 (69%) | +2.45u | +15% |
| margin + favorite + consistency | 10-5 (67%) | +1.41u | +9% |
| consistency + bvp | 30-18 (62%) | +3.98u | +8% |
| form | 30-19 (61%) | +4.01u | +8% |
| line + form | 10-6 (62%) | +1.13u | +7% |
| favorite + line + form | 10-6 (62%) | +1.13u | +7% |
| consistency | 45-29 (61%) | +5.08u | +7% |
| favorite + form | 28-18 (61%) | +2.86u | +6% |
| line | 29-17 (63%) | +2.55u | +6% |
| favorite + consistency + bvp | 27-17 (61%) | +1.65u | +4% |
| favorite + line | 28-17 (62%) | +1.41u | +3% |
| favorite | 100-67 (60%) | +4.77u | +3% |

_worst 6:_
| combo | record | units | ROI/bet |
|---|---|---|---|
| favorite + line + consistency | 8-6 (57%) | -1.05u | -8% |
| favorite + bvp + form | 15-14 (52%) | -3.02u | -10% |
| favorite + consistency + bvp + form | 8-8 (50%) | -2.13u | -13% |
| consistency + bvp + form | 8-8 (50%) | -2.13u | -13% |
| line + bvp | 11-11 (50%) | -4.05u | -18% |
| favorite + line + bvp | 10-11 (48%) | -5.19u | -25% |

_Point-in-time: signals recomputed from the frozen pre-game snapshot; winners from the MLB Stats API; $1/bet at the frozen moneyline. A signal with no recorded input on an older board is excluded from that row only (see n=)._