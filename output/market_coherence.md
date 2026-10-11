# Do the prices agree — with each other, and with us?

_Not an edge hunt. A price that disagrees with another price on the same game, or with an outcome we recorded, is a stale line, a mis-joined event or a number we are reading wrong — and none of those shows up in an ROI table._

- priced hitter-games with a result: **3998**

## 1. Is the hit market calibrated?

_Implied probability still carries the vig, so a correctly-priced book should land BELOW the diagonal by roughly the hold (~6.5% on these), not on it._

| implied band | n | implied | actual | gap | 95% CI on actual |
|---|---|---|---|---|---|
| 0%–55% | 422 | 52.0% | 48.6% | -3.4% | 43.8% – 53.3% |
| 55%–62% | 1155 | 59.0% | 53.9% | -5.2% | 51.0% – 56.7% |
| 62%–67% | 1244 | 64.6% | 60.8% | -3.8% | 58.0% – 63.4% |
| 67%–72% | 1038 | 69.2% | 65.5% | -3.7% | 62.6% – 68.3% |
| 72%–100% | 139 | 73.0% | 61.9% | -11.2% | 53.6% – 69.5% |

_Mean gap **-5.4%**. A book carrying ~6.5% hold should read about −6.5% here. Much closer to zero means the prices are beatable; much more negative means they are worse than the vig alone._

## 2. Our realised rate against their price, hitter by hitter

_197 hitters with 10+ priced games._

- correlation between a hitter's mean price and his actual rate: **r = +0.437**
- mean implied 64.1% · mean actual 59.9% · gap **-4.2%**

| hitter | games | mean price implies | actually hit | gap |
|---|---|---|---|---|
| _most overpriced_ | | | | |
| wyatt langford | 10 | 67.3% | 20.0% | -47.3% |
| colson montgomery | 17 | 58.3% | 17.6% | -40.6% |
| taylor trammell | 14 | 54.1% | 21.4% | -32.7% |
| yandy diaz | 10 | 71.6% | 40.0% | -31.6% |
| _most underpriced_ | | | | |
| brandon lowe | 17 | 62.4% | 88.2% | +25.8% |
| michael harris ii | 14 | 67.3% | 92.9% | +25.6% |
| seiya suzuki | 10 | 66.0% | 90.0% | +24.0% |
| dominic canzone | 16 | 65.8% | 87.5% | +21.7% |

### Are those outliers real, or the tails of 197 coin flips?

- spread of (actual − implied): observed **0.01717**, expected from binomial noise alone **0.01692** (**1.02×**)
- chi-square 214.2 on 197 df → **z = +0.87**
- **Consistent with pure sampling noise.** The names above are the tails of 197 samples, not prices to fade — picking the worst four of 197 is what finds them.

## 2c. The margin is in the PLATE APPEARANCES

_Same prices, same hitters, split by how long his night ran._

| appearance | n | implied | actual | gap |
|---|---|---|---|---|
| all (as priced) | 3998 | 63.1% | 58.8% | **-4.4%** |
| 2+ PA | 3869 | 63.2% | 60.0% | **-3.2%** |
| 3+ PA | 3669 | 63.4% | 61.6% | **-1.8%** |
| 4+ PA | 3119 | 64.1% | 65.1% | **+1.0%** |

_**This is conditioning on the outcome and cannot be bet directly** — nobody knows in advance that a hitter will bat four times. But it locates the margin: the book's edge on these props is largely the chance of a short night, not a view on whether the hitter can hit. `pinch_risk` predicts short nights at AUC 0.762, so that is a lever we already hold and are currently using only as a crude on/off gate at SHORT_NIGHT_MAX._

## 3-4. The new markets

**First five against the full game** — runs through five innings are normally 55–60% of a game.

| game | F5 | full | ratio |
|---|---|---|---|
| Los Angeles Dodgers@Milwaukee Brewers | 3.5 | 6.5 | **54%** |
| Cleveland Guardians@Tampa Bay Rays | 3.5 | 6.5 | **54%** |

**Strikeout lines logged**

| game | pitcher | line |
|---|---|---|
| Los Angeles Dodgers@Milwaukee Brewers | Jacob Misiorowski | o7.5 |
| Los Angeles Dodgers@Milwaukee Brewers | Tarik Skubal | o7.5 |
| Cleveland Guardians@Tampa Bay Rays | Drew Rasmussen | o5.5 |

_Too few games yet to test the K line against the opposing lineup's hit prices; that check needs a sample._

## What a failure would look like

- calibration gap near **zero** → the book is not charging its own vig and the prices are beatable
- a hitter whose price and realised rate disagree by more than ~15 points over 10+ games → likely a name joined to the wrong player, not a market view
- an F5/full ratio outside 50–65% → a stale line or a mis-joined event, the same class of fault as the Kalshi ticker bug
