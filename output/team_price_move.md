# Team, price and line movement

_Two rows per game, one per team, the move signed toward that team._

- team-games: **2420**

## Why the full grid is decoration

_30 teams × 6 price bands × 2 directions is ~360 cells. Both parent grids are already null on their own — team spread p = 0.621, price × signal best cell p = 0.581 — so crossing them multiplies the cells, not the evidence._

- cells in that grid: **299** · median games per cell: **7**

_A median cell of a handful of games returns a huge ROI by arithmetic, not by insight._

## 1. Do teams differ, at each price?

_One test per band over all its games, rather than one per cell. If teams genuinely differ at a price, the SPREAD of their ROIs there beats what redrawn outcomes produce._

| price band | teams | observed spread | chance | 95th | p |
|---|---|---|---|---|---|
| ≤-200 | 17 | — | — | — | too few teams |
| -199..-140 | 16 | 17.6% | 16.8% | 22.5% | **0.408** |
| -139..-110 | 23 | 19.1% | 18.6% | 23.4% | **0.427** |
| -109..+109 | 24 | 25.1% | 24.1% | 30.2% | **0.383** |
| +110..+159 | 24 | 19.1% | 23.1% | 29.2% | **0.879** |
| ≥+160 | 25 | — | — | — | too few teams |

_Six bands tested, so a single p just under 0.05 here is roughly 0.3 after correcting for having run six._

## 2. The lead: teams inside "line moved against"

_`team_line_move` found spread tests clearing here and only here (p = 0.018 at ≥0.5%, p = 0.026 at ≥1.0%), on 2 of ~10 sub-tests._

- teams with ≥12 games: **30**
- observed spread **23.8%** against chance **19.0%** (95th 23.3%)
- **p = 0.036** · after correcting for ~10 sub-tests, roughly **0.36**

### Does a team's edge repeat across random halves?

- teams with ≥6 games in BOTH halves: **30**
- **split-half r = +0.02**

_Not repeatable. A team's line-against ROI in one half does not predict the other, so the wide spread is thirty noisy numbers being wide — which is what the spread test cannot distinguish on its own._

| team | half A | half B |
|---|---|---|
| Houston Astros | +96% | -4% |
| Arizona Diamondbacks | +64% | -54% |
| Boston Red Sox | +58% | +23% |
| Baltimore Orioles | +45% | +29% |
| Toronto Blue Jays | +35% | -4% |
| Athletics | +35% | -59% |
| Miami Marlins | +32% | -29% |
| Cincinnati Reds | +31% | +20% |
| Los Angeles Dodgers | +30% | -25% |
| Pittsburgh Pirates | +26% | +11% |

## The full table (decoration — see above)

| team | n | all | line toward | line against |
|---|---|---|---|---|
| Boston Red Sox | 81 | +19% (53-28) | +9% (20-12) | +44% (23-7) |
| Tampa Bay Rays | 83 | +12% (52-31) | -7% (16-13) | +9% (20-14) |
| San Diego Padres | 83 | +12% (49-34) | +7% (25-18) | +16% (13-8) |
| Arizona Diamondbacks | 80 | +11% (43-37) | -13% (18-22) | +27% (16-13) |
| Milwaukee Brewers | 84 | +9% (54-30) | -10% (19-14) | +16% (24-13) |
| Chicago White Sox | 82 | +4% (43-39) | +11% (17-13) | -9% (16-19) |
| Atlanta Braves | 82 | +3% (46-36) | -19% (17-19) | +24% (17-9) |
| Baltimore Orioles | 79 | +3% (41-38) | -18% (15-22) | +37% (18-8) |
| Chicago Cubs | 79 | +1% (44-35) | -19% (18-23) | +35% (13-5) |
| Toronto Blue Jays | 81 | -0% (40-41) | -2% (20-21) | +19% (12-10) |
| New York Mets | 81 | -0% (40-41) | +19% (18-11) | -18% (12-18) |
| Cincinnati Reds | 82 | -1% (37-45) | -17% (13-20) | +26% (18-14) |
| New York Yankees | 80 | -1% (44-36) | -13% (12-10) | -1% (22-21) |
| Houston Astros | 79 | -2% (41-38) | -21% (17-23) | +28% (13-6) |
| Texas Rangers | 81 | -2% (41-40) | +25% (21-11) | -19% (14-20) |
| Miami Marlins | 80 | -3% (38-42) | -6% (19-20) | -5% (10-13) |
| Detroit Tigers | 80 | -3% (41-39) | -3% (20-17) | -11% (12-14) |
| Cleveland Guardians | 81 | -3% (43-38) | +0% (23-18) | -23% (9-13) |
| Minnesota Twins | 79 | -4% (38-41) | -16% (13-17) | +25% (20-12) |
| Pittsburgh Pirates | 80 | -5% (40-40) | +1% (18-15) | +14% (15-11) |
| Kansas City Royals | 79 | -7% (35-44) | +13% (13-10) | -35% (12-27) |
| St. Louis Cardinals | 82 | -7% (35-47) | -4% (10-11) | -7% (19-28) |
| Washington Nationals | 80 | -9% (36-44) | -29% (15-26) | +16% (11-10) |
| Los Angeles Dodgers | 79 | -10% (47-32) | -6% (26-17) | -3% (12-6) |
| Philadelphia Phillies | 81 | -11% (43-38) | -10% (24-20) | -11% (12-12) |
| San Francisco Giants | 81 | -15% (32-49) | -32% (7-15) | +1% (20-24) |
| Seattle Mariners | 79 | -19% (35-44) | -3% (15-13) | -33% (13-23) |
| Los Angeles Angels | 79 | -22% (27-52) | -18% (18-30) | -51% (4-14) |
| Athletics | 80 | -23% (25-55) | -33% (7-19) | -19% (13-27) |
| Colorado Rockies | 81 | -24% (26-55) | -6% (12-16) | -30% (11-29) |

_Italic cells are under n=15. Nothing in this table is evidence; it is here to be read, not acted on._
