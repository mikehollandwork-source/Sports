# Every signal, sliced by closing price

_A signal can be flat overall and still live in one price range. Price is also the easiest thing in this dataset to over-slice, so the grid below is scored against what a grid this wide manufactures from noise._

- graded games: **851**

_Cells show ROI and (n). Italic cells are below n=30 and are excluded from the correction._

## BACKING the side each signal names

| signal | overall | heavy fav ≤-200 | fav -199..-140 | fav -139..-110 | pick'em -109..+109 | dog +110..+139 | dog +140..+199 | big dog ≥+200 |
|---|---|---|---|---|---|---|---|---|
| margin (advantage_team) | **-3.5%** (851) | **+2.0%** (56) | **-4.2%** (254) | **-1.1%** (263) | **-11.7%** (158) | **+16.9%** (90) | _-50% (n=26)_ | _-21% (n=4)_ |
| starter BvP | **-5.2%** (797) | **+1.0%** (48) | **-3.5%** (170) | **-5.8%** (195) | **-3.9%** (160) | **+1.1%** (156) | **-36.2%** (60) | _+21% (n=8)_ |
| bullpen BvP | **-0.5%** (753) | **+0.8%** (38) | **-7.5%** (140) | **+5.4%** (191) | **+3.8%** (154) | **+4.1%** (143) | **-18.0%** (75) | _-20% (n=12)_ |
| hotter bats | **-4.4%** (672) | _+0% (n=27)_ | **-12.2%** (134) | **+5.5%** (151) | **-4.5%** (146) | **+1.7%** (126) | **-19.2%** (76) | _-20% (n=12)_ |
| line moved TOWARD | **-3.8%** (736) | **-4.7%** (48) | **+8.6%** (164) | **-7.2%** (190) | **-23.2%** (146) | **+9.4%** (118) | **+3.1%** (62) | _-62% (n=8)_ |
| line moved AGAINST | **-2.9%** (736) | _+29% (n=11)_ | **-14.1%** (109) | **+5.9%** (187) | **-8.1%** (141) | **+3.2%** (159) | **-13.6%** (107) | _+4% (n=22)_ |
| public lean | **-0.4%** (845) | **+5.6%** (50) | **-3.6%** (190) | **+5.3%** (255) | **-15.9%** (140) | **+16.1%** (141) | **-15.6%** (62) | _-55% (n=7)_ |

## FADING the side each signal names

| signal | overall | heavy fav ≤-200 | fav -199..-140 | fav -139..-110 | pick'em -109..+109 | dog +110..+139 | dog +140..+199 | big dog ≥+200 |
|---|---|---|---|---|---|---|---|---|
| margin (advantage_team) | **-3.3%** (851) | _+15% (n=10)_ | **+13.0%** (58) | **-4.6%** (171) | **-14.9%** (181) | **+3.7%** (241) | **-3.5%** (162) | _-19% (n=28)_ |
| starter BvP | **-1.6%** (797) | _+8% (n=16)_ | **+6.4%** (121) | **-0.2%** (207) | **-20.7%** (156) | **+8.7%** (155) | **+4.7%** (118) | _-32% (n=24)_ |
| bullpen BvP | **-5.9%** (753) | _+2% (n=24)_ | **+9.5%** (128) | **-13.5%** (191) | **-24.6%** (148) | **+6.3%** (146) | **-0.9%** (96) | _-19% (n=20)_ |
| hotter bats | **-1.5%** (672) | _+6% (n=23)_ | **+11.8%** (110) | **-12.5%** (183) | **-13.1%** (124) | **+9.2%** (135) | **+7.2%** (81) | _-21% (n=16)_ |
| line moved TOWARD | **-2.9%** (736) | _+29% (n=11)_ | **-14.1%** (109) | **+5.9%** (187) | **-8.1%** (141) | **+3.2%** (159) | **-13.6%** (107) | _+4% (n=22)_ |
| line moved AGAINST | **-3.8%** (736) | **-4.7%** (48) | **+8.6%** (164) | **-7.2%** (190) | **-23.2%** (146) | **+9.4%** (118) | **+3.1%** (62) | _-62% (n=8)_ |
| public lean | **-6.3%** (845) | _-1% (n=16)_ | **+3.3%** (120) | **-14.0%** (176) | **-11.3%** (196) | **+1.2%** (187) | **-8.5%** (125) | _-9% (n=25)_ |

## Does the best cell beat the search itself?

- cells at n≥30: **75**
- best: `back margin (advantage_team) @ dog +110..+139` at **+16.9%** (n=90)
- median best-in-noise: **+18.6%**
- 95th percentile in noise: **+34.6%**
- **corrected p = 0.581**

**Does not clear.** A grid of 75 cells produces one this good from noise more than 5% of the time, so the number is the width of the search, not a property of the price.

- in-sample: 19-17 · +14.9% (n=36)
- holdout: 29-25 · +18.3% (n=54)

_The properly-powered version of this question lives in `ev_model.md`: signal x price interaction terms scored by holdout log-loss, which uses every game instead of a cell of them._