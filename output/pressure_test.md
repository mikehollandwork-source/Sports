# Pressure test — 413 graded games (352 in-sample, 61 holdout)

_Rules were derived from data through 2026-07-23 (exclusive), so the **holdout** column is the only honest read. $1/bet at the frozen price. A strategy is only real if it beats the BASELINES below in the holdout._

## 1. Baselines (dumb strategies, same games)

| strategy | ALL | in-sample | HOLDOUT |
|---|---|---|---|
| bet every FAVORITE | 229-168 · -4.4u · **-1.1%** (n=397) | 197-139 · +2.4u · **+0.7%** (n=336) | 32-29 · -6.8u · **-11.2%** (n=61) |
| bet every UNDERDOG | 168-229 · -31.3u · **-7.9%** (n=397) | 139-197 · -33.0u · **-9.8%** (n=336) | 29-32 · +1.7u · **+2.8%** (n=61) |
| bet every HOME team | 199-206 · -47.3u · **-11.7%** (n=405) | 169-175 · -39.8u · **-11.6%** (n=344) | 30-31 · -7.5u · **-12.3%** (n=61) |
| bet our STAT SIDE, every game (no gate) | 214-199 · -25.3u · **-6.1%** (n=413) | 181-171 · -23.6u · **-6.7%** (n=352) | 33-28 · -1.6u · **-2.7%** (n=61) |

## 2. The LIVE gate (what the board bets today)

| strategy | ALL | in-sample | HOLDOUT |
|---|---|---|---|
| LIVE GATE (fade + core[margin|consistency] + mild-public veto) | 77-53 · +3.3u · **+2.5%** (n=130) | 66-39 · +10.2u · **+9.7%** (n=105) | 11-14 · -6.9u · **-27.7%** (n=25) |

## 3. Ablations — does each gate piece earn its place?

| strategy | ALL | in-sample | HOLDOUT |
|---|---|---|---|
| core only (NO fade gate) | 109-93 · -7.7u · **-3.8%** (n=202) | 92-73 · -0.6u · **-0.4%** (n=165) | 17-20 · -7.0u · **-19.0%** (n=37) |
| fade gate only (NO core requirement) | 147-119 · -7.6u · **-2.9%** (n=266) | 127-103 · -5.0u · **-2.2%** (n=230) | 20-16 · -2.6u · **-7.3%** (n=36) |
| live gate, NO mild-public veto | 78-55 · +2.4u · **+1.8%** (n=133) | 67-41 · +9.4u · **+8.7%** (n=108) | 11-14 · -6.9u · **-27.7%** (n=25) |
| live gate, NO pitching-dog bypass | 77-48 · +8.3u · **+6.6%** (n=125) | 66-36 · +13.2u · **+12.9%** (n=102) | 11-12 · -4.9u · **-21.4%** (n=23) |
| core = margin ONLY | 33-13 · +9.8u · **+21.4%** (n=46) | 29-9 · +11.5u · **+30.2%** (n=38) | 4-4 · -1.6u · **-20.6%** (n=8) |
| core = consistency ONLY | 56-44 · -2.5u · **-2.5%** (n=100) | 49-33 · +3.8u · **+4.6%** (n=82) | 7-11 · -6.3u · **-34.9%** (n=18) |

## 4. Removed / trialed features, re-tested

| strategy | ALL | in-sample | HOLDOUT |
|---|---|---|---|
| PUT LINE BACK in core (removed this session) | 92-67 · -0.8u · **-0.5%** (n=159) | 80-51 · +7.6u · **+5.8%** (n=131) | 12-16 · -8.4u · **-30.1%** (n=28) |
| underdog discipline (reverted rule) | 74-50 · +2.9u · **+2.4%** (n=124) | 63-36 · +9.9u · **+10.0%** (n=99) | 11-14 · -6.9u · **-27.7%** (n=25) |
| FADE our own picks (bet opponent of live gate) | 52-76 · -15.9u · **-12.4%** (n=128) | 38-65 · -22.1u · **-21.4%** (n=103) | 14-11 · +6.2u · **+24.8%** (n=25) |
| pitching dogs alone | 0-5 · -5.0u · **-100.0%** (n=5) | 0-3 · -3.0u · **-100.0%** (n=3) | 0-2 · -2.0u · **-100.0%** (n=2) |
| STARRED plays only (margin+fav+line or 4+ proven) | 27-17 · -0.6u · **-1.4%** (n=44) | 23-11 · +3.7u · **+10.8%** (n=34) | 4-6 · -4.3u · **-43.2%** (n=10) |

### Price caps on the live gate

| strategy | ALL | in-sample | HOLDOUT |
|---|---|---|---|
| live gate, lay no worse than -250 | 75-51 · +4.6u · **+3.7%** (n=126) | 66-38 · +11.2u · **+10.8%** (n=104) | 9-13 · -6.6u · **-29.8%** (n=22) |
| live gate, lay no worse than -180 | 66-47 · +4.4u · **+3.9%** (n=113) | 58-36 · +9.4u · **+10.0%** (n=94) | 8-11 · -5.0u · **-26.3%** (n=19) |
| live gate, lay no worse than -150 | 53-38 · +5.7u · **+6.2%** (n=91) | 46-28 · +10.3u · **+13.9%** (n=74) | 7-10 · -4.6u · **-27.1%** (n=17) |
| live gate, lay no worse than -130 | 32-26 · +2.8u · **+4.8%** (n=58) | 28-19 · +6.5u · **+13.9%** (n=47) | 4-7 · -3.7u · **-33.9%** (n=11) |
| live gate, PLUS MONEY only | 6-8 · -1.5u · **-10.6%** (n=14) | 6-6 · +0.5u · **+4.3%** (n=12) | 0-2 · -2.0u · **-100.0%** (n=2) |

## 5. Reversal promotion (bvp+form → bet opponent), live since 07-24

| strategy | ALL | in-sample | HOLDOUT |
|---|---|---|---|
| reversal picks as booked (bet the opponent) | 6-11 · -5.4u · **-31.7%** (n=17) | — | 6-11 · -5.4u · **-31.7%** (n=17) |
| ...the same games if we'd bet our STAT side instead | 11-6 · +4.3u · **+25.6%** (n=17) | — | 11-6 · +4.3u · **+25.6%** (n=17) |
| bvp+form profile anywhere (fade opp) | 56-44 · +10.5u · **+10.5%** (n=100) | 43-28 · +12.7u · **+17.9%** (n=71) | 13-16 · -2.2u · **-7.6%** (n=29) |

## 6. Each signal alone (bet our stat side when it fires)

| strategy | ALL | in-sample | HOLDOUT |
|---|---|---|---|
| margin | 39-24 · +3.6u · **+5.7%** (n=63) | 34-19 · +5.4u · **+10.1%** (n=53) | 5-5 · -1.8u · **-17.5%** (n=10) |
| favorite | 170-141 · -17.7u · **-5.7%** (n=311) | 146-120 · -13.2u · **-5.0%** (n=266) | 24-21 · -4.5u · **-10.0%** (n=45) |
| line | 52-40 · -4.8u · **-5.3%** (n=92) | 43-30 · -0.3u · **-0.5%** (n=73) | 9-10 · -4.5u · **-23.7%** (n=19) |
| consistency | 83-83 · -16.8u · **-10.1%** (n=166) | 71-64 · -7.5u · **-5.6%** (n=135) | 12-19 · -9.3u · **-30.0%** (n=31) |
| bvp | 121-114 · -19.9u · **-8.4%** (n=235) | 95-96 · -22.2u · **-11.6%** (n=191) | 26-18 · +2.3u · **+5.3%** (n=44) |
| sharp | 4-5 · -1.8u · **-20.0%** (n=9) | 3-4 · -1.7u · **-24.2%** (n=7) | 1-1 · -0.1u · **-5.4%** (n=2) |
| form | 71-71 · -10.6u · **-7.5%** (n=142) | 50-54 · -12.0u · **-11.6%** (n=104) | 21-17 · +1.4u · **+3.6%** (n=38) |
| pitching_dog | 0-5 · -5.0u · **-100.0%** (n=5) | 0-3 · -3.0u · **-100.0%** (n=3) | 0-2 · -2.0u · **-100.0%** (n=2) |

_Point-in-time: signals recomputed from each frozen pre-game snapshot; winners from the MLB Stats API. The HOLDOUT column is the only out-of-sample evidence - treat in-sample numbers as curve-fits._