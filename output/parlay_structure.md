# Structuring a parlay with the data we have

_Read-only. Stakes nothing, changes no pick, enters no ledger._

## Why the tax grows

_Each leg of a two-sided market carries about 4.5% hold. Parlaying multiplies the prices, so the holds compound._

| legs | hold you are paying |
|---|---|
| 1 | **4.5%** |
| 2 | **8.8%** |
| 3 | **12.9%** |
| 5 | **20.6%** |
| 9 | **33.9%** |

## The arithmetic, before any data

_Every leg is a posted hit prop: measured **62.6%** at **-200** (break-even 66.7%). A $5 stake._

| legs | parlay price | $5 returns | needs | independent legs give | edge |
|---|---|---|---|---|---|
| 1 | -200 | $8 | 66.67% | 62.60% | **-6.1%** |
| 2 | +125 | $11 | 44.44% | 39.19% | **-11.8%** |
| 3 | +238 | $17 | 29.63% | 24.53% | **-17.2%** |
| 4 | +406 | $25 | 19.75% | 15.36% | **-22.3%** |
| 5 | +659 | $38 | 13.17% | 9.61% | **-27.0%** |
| 7 | +1609 | $85 | 5.85% | 3.77% | **-35.6%** |
| 9 | +3744 | $192 | 2.60% | 1.48% | **-43.2%** |

_Two things fall out of this table._

1. **The edge per leg does not change - it compounds.** A leg that is x% bad is x% bad every time it is multiplied, so the parlay's edge is just the leg's edge raised to the number of legs. A parlay cannot rescue a losing leg; it can only lose faster.
2. **$5 into $200 is decimal 40**, which these legs reach at nine of them, and nine of them hit 1.48% against the 2.60% the price demands. To get there in five legs instead, each leg has to pay +109 - a 47.8% break-even, i.e. underdogs, not our props.

- hitter-games with a plate appearance: **4517** across **251** games, **514** hitters
- rates built from held-out halves: **191** hitters; measured on **1398** hitter-games across **237** games

## The only mechanism that could beat the price: correlation

_A parlay is priced as if its legs are independent. Two hitters in the SAME lineup face the same starter in the same conditions, so they should not be._

_`observed` is how often every leg actually hit and `independent` is the product of the legs' rates, each built from a HELD-OUT half of that hitter's games. **Read the `vs null` column, not `lift`.** Filtering hitters at 60% selects upward noise in the half the rate is built from, so those rates overstate true skill and `independent` inherits it - which is why even the permuted null sits below ×1.000. The null carries that bias identically, differing from the real data only in which game each outcome came from, so dividing by it leaves the part that is actually correlation._

| legs | pairing | combos | observed | independent | lift | null lift | **vs null** | p |
|---|---|---|---|---|---|---|---|---|
| 2 | same team | 834 | 45.444% | 54.942% | ×0.827 | ×0.799 | **×1.035** | 0.132 |
| 2 | opposite teams | 717 | 41.702% | 53.766% | ×0.776 | ×0.779 | **×0.996** | 0.562 |
| 3 | same team | 533 | 34.146% | 42.010% | ×0.813 | ×0.716 | **×1.135** | 0.099 |
| 3 | opposite teams | 1297 | 30.763% | 39.962% | ×0.770 | ×0.731 | **×1.052** | 0.273 |

## What that lift is worth, against what it has to beat

- **2 same-team legs:** correlation is worth **+3.4%** over independent pricing, against a compounded hold of **8.8%** → **still negative**, by -5.4% _(n=834)_
- **3 same-team legs:** correlation is worth **+13.0%** over independent pricing, against a compounded hold of **12.9%** → **clears the hold** by +0.1% _(n=533)_

### The best structure available, priced out

_Legs are our posted hit props: **62.6%** at **-200**. `correlated` applies the same-team lift measured above. The band is there because that lift is not significant (p around 0.10), so the honest read spans "the lift is real" to "the lift is zero"._

| structure | true P(all hit) | price needs | ROI |
|---|---|---|---|
| 2 legs, independent (lift = 1.00) | 39.19% | 44.44% | **-11.8%** |
| 2 legs, SAME TEAM (lift = 1.034) | 40.51% | 44.44% | **-8.9%** |
| 3 legs, independent (lift = 1.00) | 24.53% | 29.63% | **-17.2%** |
| 3 legs, SAME TEAM (lift = 1.130) | 27.72% | 29.63% | **-6.5%** |

_So the best structure this data supports - the shortest parlay, same lineup, correlation credited in full - is still negative. Correlation is a real effect with the right sign and it is simply not large enough to cover both the compounding hold and the deficit the legs start with._

_Note this cuts against how the props are currently posted: three props from BOTH lineups is right for three SINGLE bets, since it spreads the risk, and wrong for a parlay, which wants the correlated same-team legs. They are different products and the board posts singles._

_And that comparison is the generous version, because it credits the legs with a fair price to begin with. Our posted props hit 62.6% against a 66.7% break-even, so each leg starts about 5.5 points behind before any correlation is applied. A lift has to cover the hold AND that deficit, compounded._

_One more thing a book does: most price same-game parlays WITH a correlation adjustment already. Where that is true the lift below is in the price and there is nothing left to take. The edge, if it exists at all, lives only where legs are combined at independent pricing._
