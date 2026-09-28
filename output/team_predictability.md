# Are some teams — or some conditions — harder to predict?

_Predictability here is how well the market's own de-vigged price tracks what happens, as log-loss. Lower is more predictable. This is not profitability: whether a team beats its price is already settled (team ROI spread p = 0.621; inside line-against the spread cleared at p = 0.036 but split-half came back r = +0.02)._

- team-games: **2446**

## 1. Do teams differ in how well the market prices them?

_The null redraws each team's outcomes from ITS OWN prices, so a team of heavy favourites is not flattered by an easy schedule of quotes._

- teams with ≥15 games: **30**
- observed spread of per-team log-loss: **0.0241**
- chance: median **0.0199**, 95th **0.0252**
- **p = 0.089**

_No difference beyond chance. The market prices every team about equally well._

### Does a team's predictability repeat across random halves?

- teams in both halves: **30** · **split-half r = +0.29**

_Does not repeat. Per-team log-loss in one half does not predict the other, so any spread above is noise._

| team | half A | half B |
|---|---|---|
| Colorado Rockies (most predictable, half A) | 0.611 | 0.603 |
| Kansas City Royals (most predictable, half A) | 0.635 | 0.663 |
| San Diego Padres (most predictable, half A) | 0.635 | 0.679 |
| Washington Nationals (most predictable, half A) | 0.636 | 0.636 |
| Milwaukee Brewers (most predictable, half A) | 0.639 | 0.652 |
| Pittsburgh Pirates (most predictable, half A) | 0.642 | 0.673 |
| Houston Astros (least predictable, half A) | 0.719 | 0.687 |
| Chicago White Sox (least predictable, half A) | 0.713 | 0.668 |
| Arizona Diamondbacks (least predictable, half A) | 0.711 | 0.722 |
| Boston Red Sox (least predictable, half A) | 0.709 | 0.653 |

## 2. Calibration — actual against priced

| team | n | priced to win | actually won | gap |
|---|---|---|---|---|
| Boston Red Sox | 83 | 54.3% | 65.1% | **+10.7%** |
| Seattle Mariners | 80 | 53.1% | 43.8% | **-9.3%** |
| Los Angeles Angels | 79 | 43.4% | 34.2% | **-9.3%** |
| Tampa Bay Rays | 84 | 54.1% | 63.1% | **+9.0%** |
| Athletics | 81 | 40.7% | 32.1% | **-8.6%** |
| San Diego Padres | 83 | 50.7% | 59.0% | **+8.3%** |
| Colorado Rockies | 81 | 39.4% | 32.1% | **-7.3%** |
| Milwaukee Brewers | 84 | 57.5% | 64.3% | **+6.8%** |

_The eight largest gaps in either direction. With 30 teams, gaps of this size are what chance produces — the spread test above is the one that judges them._

## 3. Conditions: is predictability about the game, not the team?

_Every game contributes a continuous score, so these are better powered than anything per-team. Higher log-loss means the market read that kind of game less well._

| condition | games | mean log-loss |
|---|---|---|
| wind < 5 mph | 382 | **0.6758** |
| wind 5-12 mph | 1678 | **0.6733** |
| wind > 12 mph | 186 | **0.6547** |
| temp < 60F | 32 | _too few_ |
| temp >= 80F | 1232 | **0.6749** |
| roof closed/dome | 78 | **0.6646** |
| roof open | 1660 | **0.6667** |
| ump K/9 high (>17) | 632 | **0.6702** |
| ump K/9 low (<15) | 68 | **0.6591** |
| hitter park (>1.03) | 326 | **0.6663** |
| pitcher park (<0.98) | 562 | **0.6695** |

- spread across conditions: **0.0064** against chance median **0.0100** (95th 0.0169)
- **p = 0.900**

_No difference beyond chance. Weather, roof, umpire and park do not change how well the market reads a game._

## What a result here would and would not mean

- a team or condition being LESS predictable does not make it profitable; it says the market's confidence is less earned there, which is where to look next — not what to bet
- a spread that clears without repeating across halves is thirty noisy numbers being wide, which is the trap this whole file is built to avoid
