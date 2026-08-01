# Do our sources agree — and does disagreement pay?

_Every source's pick normalised to away/home so they are directly comparable: covers tickets, covers forum, VSiN bets, Polymarket bets, Vegas handle, sportsbook line movement, the Polymarket order book, and Kalshi pre-game traded volume._

## Coverage

- games with at least 3 sources: **392**
- sources per game: 3→43, 4→9, 5→40, 6→103, 7→104, 8→93

| source | games with a read |
|---|---|
| `covers` | 326 |
| `forum` | 361 |
| `vsin_bets` | 350 |
| `polymarket_bets` | 347 |
| `vegas` | 261 |
| `line` | 286 |
| `pm_book` | 174 |
| `kalshi_money` | 350 |

## 1. Unanimous vs split

- all sources agree: **46**
- sources disagree: **346**

| strategy | result |
|---|---|
| UNANIMOUS — back the agreed side | 25-21 (54%) · -5.3u · **-11.5%** (n=46) |
| UNANIMOUS — fade the agreed side | 21-25 (46%) · +4.5u · **+9.7%** (n=46) |
| SPLIT — back the majority | 187-127 (60%) · +14.7u · **+4.7%** (n=314) |
| SPLIT — fade the majority | 127-187 (40%) · -43.7u · **-13.9%** (n=314) |

## 2. When one source stands against the rest

_Only games where this source disagrees with the majority of the others. `back` follows the lone dissenter, `fade` follows the crowd._

| source | n | back the dissenter | fade it |
|---|---|---|---|
| `covers` | 60 | 24-36 (40%) · -13.4u · **-22.4%** (n=60) | 36-24 (60%) · +6.0u · **+10.1%** (n=60) |
| `forum` | 94 | 49-45 (52%) · +8.7u · **+9.2%** (n=94) | 45-49 (48%) · -14.0u · **-14.9%** (n=94) |
| `vsin_bets` | 63 | 35-28 (56%) · +2.1u · **+3.3%** (n=63) | 28-35 (44%) · -7.5u · **-11.9%** (n=63) |
| `polymarket_bets` | 69 | 28-41 (41%) · -17.6u · **-25.4%** (n=69) | 41-28 (59%) · +12.9u · **+18.8%** (n=69) |
| `vegas` | 222 | 89-133 (40%) · -30.3u · **-13.7%** (n=222) | 133-89 (60%) · +8.5u · **+3.8%** (n=222) |
| `line` | 91 | 38-53 (42%) · -14.2u · **-15.6%** (n=91) | 53-38 (58%) · +6.1u · **+6.7%** (n=91) |
| `pm_book` | 71 | 34-37 (48%) · -2.2u · **-3.0%** (n=71) | 37-34 (52%) · -4.5u · **-6.3%** (n=71) |
| `kalshi_money` | 75 | 30-45 (40%) · -14.2u · **-19.0%** (n=75) | 45-30 (60%) · +6.3u · **+8.4%** (n=75) |

## 3. Kalshi money vs everyone else

_Kalshi is the only source backed by settled cash rather than ticket counts, so it gets its own head-to-head._

| case | n | back Kalshi's side | back the others' side |
|---|---|---|---|
| agree | 239 | 144-95 (60%) · +6.8u · **+2.8%** (n=239) | 144-95 (60%) · +6.8u · **+2.8%** (n=239) |
| DISAGREE | 75 | 30-45 (40%) · -14.2u · **-19.0%** (n=75) | 45-30 (60%) · +6.3u · **+8.4%** (n=75) |

## 4. Holdout split on the headline cases

| case | in-sample | holdout |
|---|---|---|
| unanimous, back it | 25-20 (56%) · -4.3u · **-9.6%** (n=45) | 0-1 · _n=1, too few_ |
| split, back majority | 132-85 (61%) · +17.5u · **+8.0%** (n=217) | 55-42 (57%) · -2.7u · **-2.8%** (n=97) |
| kalshi disagrees, back kalshi | 19-30 (39%) · -10.9u · **-22.3%** (n=49) | 11-15 · _n=26, too few_ |
| kalshi disagrees, back others | 30-19 (61%) · +4.3u · **+8.8%** (n=49) | 15-11 · _n=26, too few_ |

_Rows under n=30 are shown as counts only. A source that looks brilliant as a lone dissenter on a handful of games is the single easiest way to fool yourself here._