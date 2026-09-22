# Closing line value — did the market come to us?

_Not "did it win" but "did the price move our way after we bought". A continuous number per pick with roughly a fifth the variance of a win/loss, which is why it is the professional standard and why it can be measured on the sample we have when ROI cannot._

- board games with at least two committed versions: **1167**

- of those, games that carried a pick: **234**
- measurable (at least one board version after the pick appeared): **233**
- excluded because the pick first appeared in the final version, leaving no interval: **1**
- board refreshes between entry and close, median: **14**

## The guard (read this before anything else)

_The same measurement applied to every home team, picked or not. The market does not systematically drift toward home teams, so this MUST come out near zero. If it does not, the reconstruction is broken and no number below can be trusted._

| population | mean CLV | median | beat the close | n |
|---|---|---|---|---|
| every home team (control) | **+0.25 pp** | +0.03 pp | 51% | 1167 |

_Control mean is **+0.25 pp**, not zero. That is not a broken pipeline - prices parse correctly - but a systematic drift that applies to EVERY side on the board: as first pitch approaches the book's overround tightens, so a de-vigged probability measured at entry and again at the close does not have the same baseline. Whatever its cause, it is the floor under any number in this report, and the only meaningful quantity is a pick's CLV MINUS this._

## Our picks

| population | mean CLV | median | beat the close | n |
|---|---|---|---|---|
| **consensus-rule picks** | **+0.32 pp** | +0.12 pp | 52% | 233 |
| fade book (separate) | — | — | — | — |
| rejected games, home side (reference) | **+0.23 pp** | +0.00 pp | 49% | 933 |

- picks whose price did not move at all between entry and close: **34/233** (15%)

- rule picks **+0.32 pp** minus the board-wide drift **+0.25 pp** = **+0.07 pp** of actual closing line value
- day-block bootstrap 95% CI on that DIFFERENCE: **-0.18 to +0.29 pp**

**No closing line value.** Once the board-wide drift is subtracted the picks are worth +0.07 pp with an interval spanning zero. The market does not come to meet these picks any faster than it comes to meet an arbitrary side of an arbitrary game.

That does not make the ROI fake, but it removes the independent confirmation it was hoped this would provide: the record still rests on the record. It also leaves the discount-versus-warning question open rather than settling it - the line-against gate is buying something the closing price does not recognise either way.

## Does CLV predict the result on our own picks?

_If the picks that the market moved toward also won more, CLV is validated as the low-variance stand-in for ROI, and every future question can be answered on a fraction of the sample._

| CLV third | mean CLV | record | ROI |
|---|---|---|---|
| worst CLV third | -0.96 pp | 43-33 | **-2.2%** (n=76) |
| middle third | +0.18 pp | 41-35 | **-5.8%** (n=76) |
| best CLV third | +1.72 pp | 42-36 | **-7.3%** (n=78) |

- correlation between CLV and winning: **r = -0.02** over 230 picks

_A positive r says the two agree and CLV can stand in for ROI. Near zero on this sample says only that one season of picks cannot resolve it - it does not overturn the mean CLV above, which is the better-powered number._

## Over time

| period | mean CLV | median | beat the close | n |
|---|---|---|---|---|
| in-sample | — | — | — | — |
| holdout | **+0.32 pp** | +0.12 pp | 52% | 233 |
| 2026-07 | **+0.63 pp** | +0.16 pp | 56% | 27 |
| 2026-08 | **+0.28 pp** | +0.12 pp | 51% | 141 |
| 2026-09 | **+0.28 pp** | +0.12 pp | 52% | 65 |

_CLV is the one number here that does not care whether a month ran hot: a month can win at +59% on luck, but it cannot fake the market coming to meet it._

## How to read this

- **mean CLV** is the edge estimate; the bootstrap interval is whether it is distinguishable from zero
- **beat the close** is the same thing as a rate, and 50% is the no-edge benchmark
- CLV cannot be gamed by a hot streak, which is why it is worth more than the ROI table for deciding whether this system works
- nothing here changes the board. It is a measurement.
