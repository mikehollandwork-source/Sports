# How often does a hitter get pulled before he finishes? — 2026

_A hits prop needs plate appearances. `props.MIN_AVG_PA` is a MEAN and cannot express "ever pinch-hit for"; this is the share of STARTS ending in 2 PA or fewer._

Hitters with 20+ starts: **414**

gamesStarted available for 0 of 414 (rest use the PA fallback)

| percentile | short-start rate |
|---|---|
| p10 | 0.0% |
| p25 | 0.0% |
| p50 | 0.0% |
| p75 | 0.0% |
| p90 | 0.0% |
| p95 | 0.0% |
| p99 | 0.0% |

## Worst 25 — these are what the gate must catch

| hitter | team | short starts | starts | rate |
|---|---|---|---|---|
| Alika Williams | ATH | 0 | 51 | **0.0%** |
| Brian Serven | ATH | 0 | 21 | **0.0%** |
| Carlos Cortes | ATH | 0 | 84 | **0.0%** |
| Darell Hernaiz | ATH | 0 | 39 | **0.0%** |
| Donovan Walton | ATH | 0 | 62 | **0.0%** |
| Henry Bolte | ATH | 0 | 110 | **0.0%** |
| Jeff McNeil | ATH | 0 | 120 | **0.0%** |
| Jonah Heim | ATH | 0 | 92 | **0.0%** |
| Lawrence Butler | ATH | 0 | 124 | **0.0%** |
| Max Muncy | ATH | 0 | 68 | **0.0%** |
| Shea Langeliers | ATH | 0 | 104 | **0.0%** |
| Tommy White | ATH | 0 | 47 | **0.0%** |
| Zack Gelof | ATH | 0 | 101 | **0.0%** |
| Brandon Lowe | PIT | 0 | 143 | **0.0%** |
| Bryan Reynolds | PIT | 0 | 156 | **0.0%** |
| Esmerlyn Valdez | PIT | 0 | 66 | **0.0%** |
| Henry Davis | PIT | 0 | 75 | **0.0%** |
| Jacob Gonzalez | PIT | 0 | 48 | **0.0%** |
| Jake Mangum | PIT | 0 | 108 | **0.0%** |
| Jared Triolo | PIT | 0 | 84 | **0.0%** |
| Konnor Griffin | PIT | 0 | 78 | **0.0%** |
| Nick Gonzales | PIT | 0 | 140 | **0.0%** |
| Nick Yorke | PIT | 0 | 23 | **0.0%** |
| Oneil Cruz | PIT | 0 | 92 | **0.0%** |
| Rafael Flores Jr. | PIT | 0 | 39 | **0.0%** |

## The two from 2026-10-04

- Sean Murphy (ATL): 0/35 = **0.0%**
- Thomas Saggese (STL): 0/41 = **0.0%**
- Colby Thomas (PHI): 0/25 = **0.0%**
- Lane Thomas (ATL): 0/81 = **0.0%**
- Mike Yastrzemski (ATL): 0/91 = **0.0%**

## Reading it

- the gate should sit where it catches the pulled bats without condemning ordinary hitters, so compare the worst list against the median rather than picking a round number
- a hitter under MIN_STARTS returns None and is LET THROUGH: unknown is not the same as risky, and a feed outage must not silently drop every prop on the board
