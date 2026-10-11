# Our own line, from measured hit rates

_Built from outcomes we recorded, not from the book's prices — so unlike the prop-price version it can actually disagree with the market. Nothing is fitted: every multiplier is pre-registered and AUC depends only on ranking._

- graded games with both lineups: **251**

- home teams won **51.8%** of them

## 1. Does it predict a winner at all?

| version | AUC |
|---|---|
| base | 0.4436 |
| hand | 0.4882 |
| form | 0.4807 |
| all | 0.5093 |
| all+park+wx | 0.5072 |
| **the market's moneyline** | **0.5922** |

_Park and weather are GAME-level — the same for both lineups — so in a home-minus-away difference they cancel almost exactly. They belong in a TOTALS model, not a win model, and the row above is the evidence._

## 2. Held against the market (using `all`)

_Thirds by moneyline, each split by our index. If we are only restating the price, both halves inside a third win equally._

| moneyline third | our index | n | home win% |
|---|---|---|---|
| home dogs | above median | 41 | 43.9% |
| home dogs | below median | 42 | 42.9% |
| middle | above median | 41 | 56.1% |
| middle | below median | 42 | 47.6% |
| home favourites | above median | 42 | 54.8% |
| home favourites | below median | 43 | 65.1% |

_Gap inside a third: +1.0%, +8.5%, -10.4% — mean **-0.3%**._

_**The thirds disagree in sign**, which is what one lucky cell looks like rather than a signal._

## How to read this

- section 1 cannot prove anything on its own: better hitters win more, and the moneyline already knows that
- section 2 is the test. A mean gap near zero, or thirds that disagree in sign, means the market already contains it
- nothing here changes a pick
