# Best execution — the same picks at a better price

_No pick changes. Same games, same sides, same dates; only the price paid to enter. There is no cell to select and no threshold to tune, so there is nothing here for a scan to overfit._

- settled board picks: **33**
- with a pre-game Polymarket quote: **33**
- with a pre-game Kalshi quote: **22**

## Same bets, priced three ways

| venue | on the quoted picks |
|---|---|
| sportsbook (what we booked) | 20-13 · +1.37u · **+4.1%** (n=33) |
| **Polymarket ask** | 20-13 · +1.61u · **+4.9%** (n=33) |
| Kalshi ask + fee | 13-9 · -0.04u · **-0.2%** (n=22) |
| _(sportsbook on those same Kalshi bets)_ | 13-9 · +0.64u · **+2.9%** (n=22) |

## What routing to the better price is worth

- Polymarket was cheaper on **17/33** (52%) of picks
- ROI: **+4.1%** booked → **+4.9%** routed (**+0.0 points**)
- units on the same bets: +1.37u → +1.61u (**+0.24u** on 33 bets)
- mean gain per bet: **+0.7%**, 95% CI **-11.1% to +16.5%**

The interval includes zero. Not actionable on this sample.

## Stability

| period | booked | routed |
|---|---|---|
| in-sample | — | — |
| holdout | 20-13 · +1.37u · **+4.1%** (n=33) | 20-13 · +1.61u · **+4.9%** (n=33) |

## Can it actually be filled?

- picks whose resting size covers a $20 bet: **31/33** (94%)
- median resting notional on our side: **$474**

_At this stake liquidity is not the binding constraint. It would become one long before the bankroll reached the size where the book price mattered more._

## The catch, stated plainly

- these are **quoted** prices, not fills; a real order pays the spread it crosses, and the ask is the right side of that but not a guarantee
- Polymarket is an exchange with no per-trade fee today; if that changes, the gain moves with it
- the quote used is the last one at or before first pitch, matching how the board freezes its own prices
- this measures only the **33** picks that carried a quote, not the whole record
