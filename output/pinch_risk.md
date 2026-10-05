# How often is a hitter pulled from a game he started? — 2026

_From the boxscore: a starter's `battingOrder` ends in 00, and anyone replacing him in that slot gets the next number up. Counts any replacement - pinch hitter, pinch runner or defensive sub - since each ends his night and kills a hits prop equally._

Games scanned: **2459** · hitters with 20+ starts: **497**

| percentile | pulled-from-start rate |
|---|---|
| p10 | 3.6% |
| p25 | 7.0% |
| p50 | 15.3% |
| p75 | 27.6% |
| p90 | 42.3% |
| p95 | 50.0% |
| p99 | 64.0% |

## Worst 25 — what the gate has to catch

| hitter | pulled | starts | rate |
|---|---|---|---|
| Colby Thomas | 25 | 32 | **78.1%** |
| Jahmai Jones | 30 | 41 | **73.2%** |
| Travis d'Arnaud | 18 | 27 | **66.7%** |
| Rob Refsnyder | 17 | 26 | **65.4%** |
| David Fry | 34 | 53 | **64.2%** |
| Joshua Báez | 16 | 25 | **64.0%** |
| LaMonte Wade Jr. | 23 | 37 | **62.2%** |
| Jesús Sánchez | 52 | 84 | **61.9%** |
| Randal Grichuk | 34 | 55 | **61.8%** |
| Zach Dezenzo | 12 | 20 | **60.0%** |
| Braxton Fulford | 12 | 20 | **60.0%** |
| Andrés Chaparro | 32 | 54 | **59.3%** |
| Nelson Velázquez | 14 | 24 | **58.3%** |
| Gabriel Rincones Jr. | 15 | 26 | **57.7%** |
| Amed Rosario | 34 | 60 | **56.7%** |
| Trevor Larnach | 58 | 104 | **55.8%** |
| Kerry Carpenter | 35 | 64 | **54.7%** |
| Miguel Rojas | 31 | 57 | **54.4%** |
| Dustin Harris | 20 | 37 | **54.1%** |
| Davis Schneider | 21 | 40 | **52.5%** |
| Yohendrick Piñango | 24 | 46 | **52.2%** |
| Colt Keith | 54 | 104 | **51.9%** |
| Will Benson | 14 | 28 | **50.0%** |
| Blake Perkins | 12 | 24 | **50.0%** |
| Zack Short | 10 | 20 | **50.0%** |

## The two from 2026-10-04

- Sean Murphy: 7/35 = **20.0%**
- Lane Thomas: 15/82 = **18.3%**
- Ozzie Albies: 5/164 = **3.0%**
- Matt Olson: 8/166 = **4.8%**
- Ronald Acuña Jr.: 10/110 = **9.1%**

## Reading it

- set the gate against the median, not a round number: it has to catch the pulled bats without condemning ordinary hitters
- Albies, Olson and Acuña are printed as controls — they are the everyday bats the gate must NOT touch
- a hitter under MIN_STARTS returns None and is let through
