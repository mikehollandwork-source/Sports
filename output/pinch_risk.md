# How often does a hitter's night end early? — 2026

_A start is SHORT at 3 plate appearances or fewer. The rate below is the last 30 starts shrunk toward the season rate — the measure the bake-off at the foot of this page picked over four others, including the pull count this started as._

Games scanned: **2459** · hitters with 20+ starts: **497**

| percentile | short-night rate |
|---|---|
| p10 | 3.7% |
| p25 | 9.3% |
| p50 | 22.8% |
| p75 | 41.4% |
| p90 | 53.6% |
| p95 | 60.0% |
| p99 | 72.8% |

## Worst 25 — what the gate has to catch

| hitter | short nights | starts | PA/start | rate |
|---|---|---|---|---|
| Travis d'Arnaud | 21 | 27 | 2.96 | **77.8%** |
| Colby Thomas | 23 | 32 | 3.06 | **75.5%** |
| Ke'Bryan Hayes | 45 | 74 | 3.27 | **75.2%** |
| Zac Veen | 15 | 20 | 3.00 | **75.0%** |
| Ali Sánchez | 23 | 31 | 2.90 | **73.5%** |
| Luisangel Acuña | 41 | 67 | 3.13 | **72.8%** |
| Pedro Pagés | 33 | 62 | 3.32 | **68.3%** |
| Jahmai Jones | 30 | 41 | 2.80 | **68.3%** |
| Enrique Hernández | 17 | 25 | 3.12 | **68.0%** |
| Carlos Narváez | 47 | 85 | 3.34 | **66.3%** |
| Christian Vázquez | 40 | 75 | 3.39 | **65.8%** |
| Jacob Gonzalez | 31 | 60 | 3.40 | **65.4%** |
| Denzel Clarke | 15 | 23 | 3.13 | **65.2%** |
| Zach Dezenzo | 13 | 20 | 3.30 | **65.0%** |
| Braxton Fulford | 13 | 20 | 3.10 | **65.0%** |
| Tyrone Taylor | 38 | 57 | 3.30 | **64.2%** |
| Tyler Heineman | 38 | 58 | 3.28 | **63.9%** |
| Bryce Teodosio | 14 | 22 | 3.14 | **63.6%** |
| Brock Rodden | 14 | 22 | 3.14 | **63.6%** |
| Hunter Feduccia | 48 | 76 | 3.13 | **63.3%** |
| Rodolfo Durán | 17 | 27 | 3.22 | **63.0%** |
| Davis Schneider | 24 | 40 | 3.23 | **62.5%** |
| Jesús Sánchez | 41 | 84 | 3.49 | **62.2%** |
| Miguel Rojas | 32 | 57 | 3.35 | **61.5%** |
| David Fry | 32 | 53 | 3.23 | **60.1%** |

## The two from 2026-10-04

- Sean Murphy: 13/35 short = **34.3%**, 3.69 PA/start
- Lane Thomas: 19/82 short = **28.3%**, 3.96 PA/start
- Ozzie Albies: 10/164 short = **11.5%**, 4.24 PA/start
- Matt Olson: 9/166 short = **13.9%**, 4.30 PA/start
- Ronald Acuña Jr.: 5/110 short = **3.6%**, 4.37 PA/start

## Which measure is best?

_Decided by forward test, not by argument: every measure built from PRIOR starts only, scored against what happened that night._

**32989 starts** judged, 17.9% of them short (PA <= 3).

_AUC is the chance a short night scores above a full one. 0.50 is a coin flip._

| measure | AUC |
|---|---|
| short_rate (PA<=3) | 0.7552 |
| pull_rate (any replacement) | 0.6807 |
| costly_rate (pulled AND short) | 0.7145 |
| mean PA per start (negated) | 0.7567 |
| recent 30 short_rate | 0.7600 |

**Best: recent 30 short_rate at AUC 0.7600.**


## Reading it

- set the gate against the median, not a round number: it has to catch the pulled bats without condemning ordinary hitters
- Albies, Olson and Acuña are printed as controls — they are the everyday bats the gate must NOT touch
- a hitter under MIN_STARTS returns None and is let through
