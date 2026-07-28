# Signal backtest — 413 graded of 451 game snapshots

## Each signal alone (bet the advantage team when it fires)

| signal | record | units |
|---|---|---|
| margin (n=63) | 39-24 (62%) | +3.60u |
| favorite (n=311) | 170-141 (55%) | -17.70u |
| line (n=92) | 52-40 (57%) | -4.85u |
| consistency (n=166) | 83-83 (50%) | -16.79u |
| bvp (n=235) | 121-114 (51%) | -19.85u |
| sharp (n=9) | 4-5 (44%) | -1.80u |
| form (n=142) | 71-71 (50%) | -10.63u |
| pitching_dog (n=5) | 0-5 (0%) | -5.00u |

## By number of signals hit

| signals hit | record | units |
|---|---|---|
| 6/7 | 0-3 (0%) | -3.00u |
| 5/7 | 16-12 (57%) | -1.85u |
| 4/7 | 37-32 (54%) | -5.19u |
| 3/7 | 51-47 (52%) | -7.50u |
| 2/7 | 59-48 (55%) | +0.08u |
| 1/7 | 41-40 (51%) | -2.69u |
| 0/7 | 10-17 (37%) | -5.12u |

## Best signal combos (all present together, n≥10, by win%)

| combo | record | units |
|---|---|---|
| margin + line + bvp | 10-3 (77%) | +2.53u |
| margin + line | 16-5 (76%) | +4.39u |
| margin + favorite + line | 16-5 (76%) | +4.39u |
| margin + favorite + bvp | 24-13 (65%) | +2.53u |
| margin + favorite | 35-20 (64%) | +3.24u |
| margin + bvp | 26-16 (62%) | +1.68u |
| favorite + line | 47-37 (56%) | -7.16u |
| favorite + bvp | 102-82 (55%) | -9.14u |
| line + bvp | 29-25 (54%) | -7.01u |
| favorite + consistency + bvp | 51-44 (54%) | -7.05u |
| favorite + line + bvp | 27-24 (53%) | -8.23u |
| favorite + consistency | 68-62 (52%) | -12.05u |

## Tailing the side VEGAS needed (book_needs) vs outcome

| slice | record | units |
|---|---|---|
| all games with a book read (n=397) | 173-224 (44%) | -43.32u |
|   ...money % (n=179) | 69-110 (39%) | -32.35u |
|   ...ticket % (n=218) | 104-114 (48%) | -10.96u |
| (vs our advantage side, same games) | 211-186 (53%) | -15.12u |

## Tailing Vegas (bet the side book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| tail Vegas, all games (n=397) | 173-224 (44%) | -43.32u |
|   + our stat side agrees (n=147) | 67-80 (46%) | -17.66u |
|   + agrees & margin (n=16) | 6-10 (38%) | -5.23u |
|   + agrees & favorite (n=83) | 40-43 (48%) | -12.14u |
|   + agrees & line (n=25) | 14-11 (56%) | +0.02u |
|   + agrees & consistency (n=64) | 26-38 (41%) | -14.48u |
|   + agrees & bvp (n=83) | 33-50 (40%) | -20.57u |
|   + agrees & sharp (n=1) | 0-1 (0%) | -1.00u |
|   + agrees & form (n=62) | 28-34 (45%) | -6.23u |
|   + agrees & pitching_dog (n=5) | 0-5 (0%) | -5.00u |

## Tail Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=131) | 57-74 (44%) | -24.25u | -18.5% |
| ≥2 signals (n=82) | 34-48 (41%) | -19.24u | -23.5% |
| ≥3 signals (n=43) | 21-22 (49%) | -5.41u | -12.6% |
| ≥4 signals (n=14) | 6-8 (43%) | -3.87u | -27.6% |

## Fading Vegas (bet the OPPOSITE of book_needs) + one of our signals

| slice | record | units |
|---|---|---|
| fade Vegas, all games (n=397) | 224-173 (56%) | +7.64u |
|   + our stat side agrees (n=250) | 144-106 (58%) | +2.54u |
|   + agrees & margin (n=44) | 32-12 (73%) | +10.01u |
|   + agrees & favorite (n=218) | 128-90 (59%) | +0.64u |
|   + agrees & line (n=67) | 38-29 (57%) | -4.87u |
|   + agrees & consistency (n=102) | 57-45 (56%) | -2.31u |
|   + agrees & bvp (n=152) | 88-64 (58%) | +0.72u |
|   + agrees & sharp (n=8) | 4-4 (50%) | -0.80u |
|   + agrees & form (n=80) | 43-37 (54%) | -4.40u |
|   + agrees & pitching_dog (n=0) | 0 | — |

## Fade Vegas (stat side agrees) by NUMBER of signals stacked

| signals stacked | record | units | ROI/bet |
|---|---|---|---|
| ≥1 signals (n=238) | 140-98 (59%) | +5.82u | +2.4% |
| ≥2 signals (n=197) | 117-80 (59%) | +4.29u | +2.2% |
| ≥3 signals (n=112) | 65-47 (58%) | -2.80u | -2.5% |
| ≥4 signals (n=40) | 23-17 (57%) | -2.91u | -7.3% |

## Best MULTI-signal fade combos (stat side agrees, n≥10)

| combo | record | units |
|---|---|---|
| margin + line + bvp | 8-2 (80%) | +2.63u |
| margin + line | 14-4 (78%) | +4.50u |
| margin + favorite + line | 14-4 (78%) | +4.50u |
| margin + bvp | 22-8 (73%) | +7.02u |
| margin + favorite + bvp | 20-8 (71%) | +4.87u |
| margin + favorite | 29-12 (71%) | +6.82u |
| consistency + bvp | 41-30 (58%) | -0.22u |
| margin + consistency + bvp | 9-6 (60%) | -0.26u |
| favorite + consistency + bvp | 38-28 (58%) | -1.55u |
| favorite + bvp | 78-57 (58%) | -3.25u |

## Our pick when the book's informed money was AGAINST us (⚠️ bucket)

| slice | record | units |
|---|---|---|
| stance-against plays (n=84) | 45-39 (54%) | -4.49u |

## NEW BOARD GATE — fade + core signal (what makes the board now)

| slice | record | units |
|---|---|---|
| BOARD: fade + core signal (n=125) | 77-48 (62%) | +8.61u |
| DROPPED: tail + core signal (was played, now cut) (n=74) | 31-43 (42%) | -15.09u |

## Board leak-finder — the live board by core-signal type

_Which picks on the current board (fade + core) carry ROI, and which are the drag we could tighten out. All bet the fade side, $1/pick._

| board subset | record | units | ROI/bet |
|---|---|---|---|
| has MARGIN (with anything) (n=44) | 32-12 (73%) | +10.01u | +22.8% |
| NO margin (core = line/consistency only) (n=81) | 45-36 (56%) | -1.40u | -1.7% |
|   ...line-only core (no margin, no consistency) | 0 | — | — |
|   ...consistency-only core (no margin, no line) (n=61) | 36-25 (59%) | +3.91u | +6.4% |
|   ...line AND consistency (no margin) (n=20) | 9-11 (45%) | -5.31u | -26.5% |
| 2+ core signals together (n=54) | 32-22 (59%) | -1.41u | -2.6% |

## Starred (⭐) plays vs the rest of the board

_The board split by the current star rule. Both bet the fade side, $1/pick._

| board tier | record | units | ROI/bet |
|---|---|---|---|
| ⭐ STARRED plays (n=39) | 24-15 (62%) | -0.49u | -1.3% |
| ✅ the rest of the board (n=86) | 53-33 (62%) | +9.10u | +10.6% |
| whole board (both tiers) (n=125) | 77-48 (62%) | +8.61u | +6.9% |

## Underdog discipline — drop dogs without margin / pitching edge

| board | record | units | ROI/bet |
|---|---|---|---|
| BEFORE (whole fade+core board) (n=125) | 77-48 (62%) | +8.61u | +6.9% |
| AFTER (dogs need margin/pitching) (n=118) | 73-45 (62%) | +7.11u | +6.0% |
| DROPPED (consistency-only dogs) (n=7) | 4-3 (57%) | +1.50u | +21.4% |

## Threshold sweeps on the fade side (does a tighter bar help?)

| margin ≥ | record | units |
|---|---|---|
| 0.30 | 63-45 (58%) | -0.58u |
| 0.40 | 46-27 (63%) | +5.77u |
| 0.50 | 32-12 (73%) | +10.01u |
| 0.60 | 14-7 (67%) | +2.01u |
| 0.70 | 4-5 (44%) | -2.98u |

| consistency (out-hit) ≥ | record | units |
|---|---|---|
| 3/5 | 57-45 (56%) | -2.31u |
| 4/5 | 19-19 (50%) | -4.07u |
| 5/5 | 5-5 (50%) | -1.06u |

## Does line-shading improve our picks? (our picks by shading gap)

| shading gap (tickets − implied) | record | units |
|---|---|---|
| < 5 (not shaded) | 99-89 (53%) | -7.69u |
| 5–15 (mild) | 89-82 (52%) | -13.59u |
| ≥ 15 (heavy shade) | 21-21 (50%) | -1.64u |

## Line-move timing — sharp window vs public window (n=55)

_open→11pm = instant strike on the fresh opener; open→6am = the full overnight/sharp window; 6am→close = daytime (public). Needs the off-hours snapshots, so n grows from the day those crons started._

| move toward us happened | record | units |
|---|---|---|
| overnight only (sharp) | 8-6 (57%) | -0.58u |
| daytime only (public) | 17-18 (49%) | -6.39u |
| both windows | 4-2 (67%) | +0.27u |
| instant strike on the opener (open→11pm) | 0 | — |
| overnight drift after the strike window (11pm→6am) | 0 | — |

## Polymarket vs the book — same picks, PM's frozen price (n=268)

_PM price is the gamma-API quote frozen in the snapshot: a mid/last price with no fee or slippage modeling, so treat PM units as a best-case. Unopened 50/50 placeholder markets excluded._

| venue (same picks, same outcomes) | record | units | ROI/bet |
|---|---|---|---|
| book (real prices) | 141-127 (53%) | -16.65u | -6.2% |
| Polymarket (frozen quote) | 141-127 (same games) | -3.13u | -1.2% |

_Avg price gap: PM sells our side +2.6 prob. points vs the book (positive = PM cheaper). PM was >=1pt cheaper on 242 of 268 picks._

_On those 242 PM-cheaper picks: book 132-110 -9.37u vs PM +4.91u._

_ARBITRAGE windows (PM one side + book the other, combined implied < 100%): 21 of 268 games; margins avg 6.6%, best 22.1%._

## Underdog study — our stat side priced as a DOG (ml > 0)

| slice | record | units | ROI/bet |
|---|---|---|---|
| all underdogs (n=102) | 44-58 (43%) | -7.57u | -7% |
| + edge margin ≥.50 (n=8) | 4-4 (50%) | +0.36u | +4% |
| + BvP edge (n=51) | 19-32 (37%) | -10.71u | -21% |
| + consistency ≥3 (n=36) | 15-21 (42%) | -4.74u | -13% |
| + FIP edge ≥.15 (pitching-edge dogs) (n=42) | 17-25 (40%) | -4.73u | -11% |
| + margin & BvP (n=5) | 2-3 (40%) | -0.85u | -17% |
| + consistency & BvP (n=22) | 7-15 (32%) | -7.35u | -33% |

## When money sources disagree — bet our stat side (n=56)

_The '⚠️ money sources disagree' flag fires rarely; every slice here is small — treat as exploratory, not a proven edge._

| slice | record | units | ROI/bet |
|---|---|---|---|
| advantage side (flag on) (n=56) | 34-22 (61%) | +9.02u | +16% |
| + margin (n=5) | 4-1 (80%) | +2.21u | +44% |
| + favorite (n=40) | 23-17 (57%) | +1.99u | +5% |
| + line (n=15) | 9-6 (60%) | +1.73u | +12% |
| + consistency (n=29) | 16-13 (55%) | +1.48u | +5% |
| + bvp (n=39) | 23-16 (59%) | +5.61u | +14% |
| + sharp | 0 | — | — |
| + form (n=31) | 18-13 (58%) | +4.17u | +13% |
| + pitching_dog (n=2) | 0-2 (0%) | -2.00u | -100% |
| + ≥1 signals stacked (n=55) | 33-22 (60%) | +7.89u | +14% |
| + ≥2 signals stacked (n=50) | 29-21 (58%) | +5.15u | +10% |
| + ≥3 signals stacked (n=35) | 19-16 (54%) | +0.70u | +2% |
| fade side (opp. of book_needs), flag on (n=56) | 28-28 (50%) | -3.74u | -7% |

_Signal combos inside the flag (bet our side, n≥3, by units):_

| combo | record | units | ROI/bet |
|---|---|---|---|
| bvp (n=39) | 23-16 (59%) | +5.61u | +14% |
| form (n=31) | 18-13 (58%) | +4.17u | +13% |
| favorite + consistency + form (n=12) | 8-4 (67%) | +3.09u | +26% |
| consistency + bvp (n=20) | 12-8 (60%) | +2.96u | +15% |
| bvp + form (n=21) | 12-9 (57%) | +2.85u | +14% |
| consistency + bvp + form (n=11) | 7-4 (64%) | +2.61u | +24% |
| margin + favorite + bvp (n=3) | 3-0 (100%) | +2.59u | +86% |
| margin + bvp (n=3) | 3-0 (100%) | +2.59u | +86% |
| favorite + consistency + bvp + form (n=7) | 5-2 (71%) | +2.39u | +34% |
| consistency + form (n=17) | 10-7 (59%) | +2.31u | +14% |
| margin + favorite (n=5) | 4-1 (80%) | +2.21u | +44% |
| margin (n=5) | 4-1 (80%) | +2.21u | +44% |
| favorite (n=40) | 23-17 (57%) | +1.99u | +5% |
| line (n=15) | 9-6 (60%) | +1.73u | +12% |
| favorite + form (n=19) | 11-8 (58%) | +1.54u | +8% |
| consistency (n=29) | 16-13 (55%) | +1.48u | +5% |
| line + consistency + bvp (n=8) | 5-3 (62%) | +1.44u | +18% |
| line + consistency (n=12) | 7-5 (58%) | +1.26u | +10% |
| favorite + consistency + bvp (n=14) | 8-6 (57%) | +0.60u | +4% |
| favorite + line (n=12) | 7-5 (58%) | +0.51u | +4% |
| line + bvp (n=9) | 5-4 (56%) | +0.44u | +5% |
| favorite + consistency (n=22) | 12-10 (55%) | +0.12u | +1% |
| favorite + line + consistency (n=9) | 5-4 (56%) | +0.04u | +0% |
| line + consistency + bvp + form (n=4) | 2-2 (50%) | +0.03u | +1% |
| line + consistency + form (n=8) | 4-4 (50%) | -0.14u | -2% |
| favorite + line + consistency + form (n=6) | 3-3 (50%) | -0.22u | -4% |
| line + form (n=10) | 5-5 (50%) | -0.29u | -3% |
| favorite + line + form (n=8) | 4-4 (50%) | -0.37u | -5% |
| favorite + bvp + form (n=12) | 6-6 (50%) | -0.69u | -6% |
| favorite + line + consistency + bvp (n=6) | 3-3 (50%) | -0.78u | -13% |
| line + bvp + form (n=5) | 2-3 (40%) | -0.97u | -19% |
| favorite + line + consistency + bvp + form (n=3) | 1-2 (33%) | -1.05u | -35% |
| favorite + bvp (n=27) | 14-13 (52%) | -1.20u | -4% |
| favorite + line + bvp (n=7) | 3-4 (43%) | -1.78u | -25% |
| favorite + line + bvp + form (n=4) | 1-3 (25%) | -2.05u | -51% |

## What winning underdogs have in common (44 winners vs 58 losers)

| stat (advantage side edge) | winners median | losers median |
|---|---|---|
| team-score edge | +0.127 | +0.146 |
| edge margin | +0.178 | +0.173 |
| offense-index edge | +0.184 | +0.166 |
| pitching-index edge | -0.044 | +0.009 |
| FIP edge (opp−ours) | -0.180 | +0.034 |
| wOBA edge (park-neutral) | +0.068 | +0.044 |
| ISO edge (park-neutral) | +0.075 | +0.050 |
| K% gap | -0.029 | -0.003 |
| BvP edge (signed) | -0.001 | +0.001 |
| hot-lineup edge | +0.072 | +0.051 |
| dog price (ml) | +113.000 | +115.000 |

## Every underdog + signal combo (bet the dog, n≥5, by units)

| combo | record | units | ROI/bet |
|---|---|---|---|
| line + consistency | 4-2 (67%) | +2.31u | +38% |
| line | 5-3 (62%) | +2.31u | +29% |
| line + form | 3-2 (60%) | +1.17u | +23% |
| margin | 4-4 (50%) | +0.36u | +4% |
| margin + bvp | 2-3 (40%) | -0.85u | -17% |
| consistency + form | 10-12 (45%) | -1.28u | -6% |
| form | 19-23 (45%) | -1.48u | -4% |
| consistency + bvp + form | 4-9 (31%) | -4.68u | -36% |
| consistency | 15-21 (42%) | -4.74u | -13% |
| pitching_dog | 0-5 (0%) | -5.00u | -100% |
| form + pitching_dog | 0-5 (0%) | -5.00u | -100% |
| consistency + bvp | 7-15 (32%) | -7.35u | -33% |
| (any dog) | 44-58 (43%) | -7.57u | -7% |
| bvp + form | 8-18 (31%) | -9.36u | -36% |
| bvp | 19-32 (37%) | -10.71u | -21% |

## Value bet — our projected odds vs the market (n=413)

_proj_edge = our stat-projected win% minus the market's implied %. Positive = we think our side is underpriced. Recomputed from margin so it spans every graded game._

| our edge over the market | record | units | ROI/bet |
|---|---|---|---|
| market richer than us (<0) (n=147) | 85-62 (58%) | -5.72u | -3.9% |
| slight (0–5 pts) (n=93) | 49-44 (53%) | -2.73u | -2.9% |
| moderate (5–10) (n=102) | 52-50 (51%) | -2.44u | -2.4% |
| strong (10–20) (n=60) | 25-35 (42%) | -10.36u | -17.3% |
| huge (20+) (n=11) | 3-8 (27%) | -4.03u | -36.6% |

| bet only when edge ≥ | record | units | ROI/bet |
|---|---|---|---|
| 0 pts (n=266) | 129-137 (48%) | -19.55u | -7.3% |
| 3 pts (n=208) | 102-106 (49%) | -10.44u | -5.0% |
| 5 pts (n=173) | 80-93 (46%) | -16.82u | -9.7% |
| 8 pts (n=107) | 48-59 (45%) | -11.20u | -10.5% |
| 12 pts (n=56) | 21-35 (38%) | -13.08u | -23.4% |
| 15 pts (n=32) | 10-22 (31%) | -9.94u | -31.1% |

## Polymarket money agreeing with our pick (n=268)

_pm_edge = PM's implied % for our side minus the market's implied %. Positive = PM's live money leans our way harder than the sportsbook._

| PM lean vs the book | record | units | ROI/bet |
|---|---|---|---|
| PM against us (< -3) (n=67) | 33-34 (49%) | -9.75u | -14.6% |
| ≈ agree (±3) (n=196) | 106-90 (54%) | -6.27u | -3.2% |
| PM with us (3–8) (n=1) | 0-1 (0%) | -1.00u | -100.0% |
| PM hard with us (8+) (n=4) | 2-2 (50%) | +0.37u | +9.2% |

## Sharp-window line move × core signal (n=202 core picks)

| slice | record | units | ROI/bet |
|---|---|---|---|
| core signal, any (n=202) | 109-93 (54%) | -7.65u | -3.8% |
| core + moved in the SHARP window (early) (n=10) | 6-4 (60%) | -0.11u | -1.1% |
| core + moved only in the PUBLIC window (late) (n=23) | 11-12 (48%) | -4.61u | -20.0% |
| core + sharps STRUCK the fresh opener | 0 | — | — |

## Value edge + core signal together

| slice | record | units | ROI/bet |
|---|---|---|---|
| proj_edge ≥5 AND a core signal (n=99) | 49-50 (49%) | -7.66u | -7.7% |
| proj_edge ≥8 AND a core signal (n=66) | 33-33 (50%) | -3.21u | -4.9% |
| proj_edge ≥12 AND a core signal (n=38) | 16-22 (42%) | -7.06u | -18.6% |

## ALL signal combinations — every graded pick (every signal subset, n≥10, by ROI/bet)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin + line | 16-5 (76%) | +4.39u | +21% |
| margin + favorite + line | 16-5 (76%) | +4.39u | +21% |
| margin + line + bvp | 10-3 (77%) | +2.53u | +19% |
| margin + favorite + line + bvp | 10-3 (77%) | +2.53u | +19% |
| margin + line + form | 7-3 (70%) | +1.32u | +13% |
| margin + favorite + line + form | 7-3 (70%) | +1.32u | +13% |
| margin + favorite + bvp | 24-13 (65%) | +2.53u | +7% |
| margin + favorite | 35-20 (64%) | +3.24u | +6% |
| margin | 39-24 (62%) | +3.60u | +6% |
| margin + bvp | 26-16 (62%) | +1.68u | +4% |
| margin + favorite + form | 13-9 (59%) | +0.04u | +0% |
| margin + favorite + bvp + form | 11-8 (58%) | -0.25u | -1% |
| favorite + bvp | 102-82 (55%) | -9.14u | -5% |
| line | 52-40 (57%) | -4.85u | -5% |
| favorite | 170-141 (55%) | -17.70u | -6% |
| favorite + consistency + bvp | 51-44 (54%) | -7.05u | -7% |
| form | 71-71 (50%) | -10.63u | -7% |
| bvp | 121-114 (51%) | -19.85u | -8% |
| favorite + line | 47-37 (56%) | -7.16u | -9% |
| favorite + form | 52-48 (52%) | -9.15u | -9% |

_worst 6:_
| combo | record | units | ROI/bet |
|---|---|---|---|
| favorite + line + consistency + form | 6-12 (33%) | -7.60u | -42% |
| margin + favorite + consistency + bvp + form | 3-7 (30%) | -4.71u | -47% |
| favorite + line + consistency + bvp + form | 4-9 (31%) | -6.42u | -49% |
| margin + favorite + consistency + form | 3-8 (27%) | -5.71u | -52% |
| margin + consistency + bvp + form | 3-9 (25%) | -6.71u | -56% |
| margin + consistency + form | 3-10 (23%) | -7.71u | -59% |

## ALL signal combinations — FADE-GATED picks (live board condition) (every signal subset, n≥10, by ROI/bet)

| combo | record | units | ROI/bet |
|---|---|---|---|
| margin + line + bvp | 8-2 (80%) | +2.63u | +26% |
| margin + favorite + line + bvp | 8-2 (80%) | +2.63u | +26% |
| margin + line | 14-4 (78%) | +4.50u | +25% |
| margin + favorite + line | 14-4 (78%) | +4.50u | +25% |
| margin + bvp | 22-8 (73%) | +7.02u | +23% |
| margin | 32-12 (73%) | +10.01u | +23% |
| margin + favorite + bvp + form | 10-4 (71%) | +2.86u | +20% |
| margin + bvp + form | 10-4 (71%) | +2.86u | +20% |
| margin + form | 12-5 (71%) | +3.15u | +19% |
| margin + favorite + form | 12-5 (71%) | +3.15u | +19% |
| margin + favorite + bvp | 20-8 (71%) | +4.87u | +17% |
| margin + favorite | 29-12 (71%) | +6.82u | +17% |
| bvp | 88-64 (58%) | +0.72u | +0% |
| favorite | 128-90 (59%) | +0.64u | +0% |
| consistency + bvp | 41-30 (58%) | -0.22u | -0% |
| margin + favorite + consistency + bvp | 9-6 (60%) | -0.26u | -2% |
| margin + consistency + bvp | 9-6 (60%) | -0.26u | -2% |
| consistency | 57-45 (56%) | -2.31u | -2% |
| favorite + consistency + bvp | 38-28 (58%) | -1.55u | -2% |
| favorite + bvp | 78-57 (58%) | -3.25u | -2% |

_worst 6:_
| combo | record | units | ROI/bet |
|---|---|---|---|
| favorite + line + consistency | 11-13 (46%) | -6.76u | -28% |
| favorite + line + consistency + bvp | 8-9 (47%) | -4.90u | -29% |
| line + bvp + form | 7-13 (35%) | -9.02u | -45% |
| favorite + line + bvp + form | 7-13 (35%) | -9.02u | -45% |
| line + consistency + form | 3-9 (25%) | -7.08u | -59% |
| favorite + line + consistency + form | 3-9 (25%) | -7.08u | -59% |

## Reversal finder — negative profiles, and whether fading them profits

_Combos (n≥25) where OUR side loses ≤−12% ROI. 'fade' bets the OPPONENT at its real price - the honest test of reversing the profile. The vig is paid on the fade too, so only a BADLY losing profile clears +EV. Scanning many combos for the worst also risks overfitting - trust n and a reason._

| profile | OUR side | FADE (bet opponent) |
|---|---|---|
| favorite + line + bvp + form (n=26) | 11-15 (42%) -8.3u (-32%) | 15-11 (58%) +6.1u (**+24%**) |
| line + bvp + form (n=27) | 12-15 (44%) -7.2u (-27%) | 15-12 (56%) +5.1u (**+19%**) |
| favorite + line + consistency (n=36) | 17-19 (47%) -8.3u (-23%) | 19-17 (53%) +6.5u (**+18%**) |
| favorite + line + consistency + bvp (n=27) | 13-14 (48%) -6.3u (-23%) | 14-13 (52%) +4.8u (**+18%**) |
| consistency + bvp + form (n=56) | 24-32 (43%) -12.4u (-22%) | 32-24 (57%) +7.8u (**+14%**) |
| favorite + consistency + bvp + form (n=43) | 20-23 (47%) -7.7u (-18%) | 23-20 (53%) +5.4u (**+13%**) |
| favorite + line + form (n=38) | 18-20 (47%) -8.1u (-21%) | 20-18 (53%) +4.6u (**+12%**) |
| line + consistency + bvp (n=30) | 15-15 (50%) -5.1u (-17%) | 15-15 (50%) +3.5u (**+12%**) |
| bvp + form (n=100) | 44-56 (44%) -20.7u (-21%) | 56-44 (56%) +10.5u (**+10%**) |
| line + consistency (n=42) | 21-21 (50%) -6.0u (-14%) | 21-21 (50%) +4.0u (**+9%**) |
| margin + consistency (n=27) | 13-14 (48%) -5.5u (-21%) | 14-13 (52%) +2.4u (**+9%**) |
| favorite + bvp + form (n=74) | 36-38 (49%) -11.4u (-15%) | 38-36 (51%) +6.0u (**+8%**) |
| line + form (n=43) | 21-22 (49%) -6.9u (-16%) | 22-21 (51%) +3.2u (**+7%**) |
| favorite + consistency + form (n=55) | 27-28 (49%) -6.8u (-12%) | 28-27 (51%) +3.6u (**+7%**) |
| favorite + line + bvp (n=51) | 27-24 (53%) -8.2u (-16%) | 24-27 (47%) +3.0u (**+6%**) |
| line + bvp (n=54) | 29-25 (54%) -7.0u (-13%) | 25-29 (46%) +1.6u (**+3%**) |
| consistency + bvp (n=117) | 58-59 (50%) -14.4u (-12%) | 59-58 (50%) +3.4u (**+3%**) |

## Promotion check — fade bvp+form, NO-PLAY subset (what we'd promote)

_The promotion only touches no-play games, so this subset is the one that matters. Fade = bet the opponent at its price._

| bvp+form fade | record | units | ROI/bet |
|---|---|---|---|
| all bvp+form (context) (n=100) | 56-44 (56%) | +10.50u | +10.5% |
| NO-PLAY subset (the promotion) (n=53) | 30-23 (57%) | +3.67u | +6.9% |
| already-played subset (context) (n=47) | 26-21 (55%) | +6.82u | +14.5% |

_Point-in-time: signals recomputed from the frozen pre-game snapshot; winners from the MLB Stats API; $1/bet at the frozen moneyline. A signal with no recorded input on an older board is excluded from that row only (see n=)._