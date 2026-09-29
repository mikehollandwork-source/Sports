# Line movement, tickets, handle and the two venues

_Every order-book reading is cut at first pitch minus 15 minutes — the same moment the board freezes a pick. Both venues keep logging through the game and after settlement, and a Polymarket bid of 0.999 or a Kalshi 0.0/1.0 pair is a finished game, not a market read. Using them would predict outcomes perfectly and mean nothing._

- readings kept: **105,635** · discarded as at-or-after the freeze: **62,068**
- games with a result and a board row: **978**
- of those, both venues readable pre-game: **753**

## 1. Our settled plays: winners against losers

_62 won, 41 lost. Each column is signed toward the side we backed, so a positive line figure means the price moved our way. **This is the weakest test here** — two groups of ~70 make a 5-point difference indistinguishable from noise._

| pre-game measure | winners | losers |
|---|---|---|
| line move toward our side | -0.019 | -0.019 |
| Polymarket drift | +0.009 | +0.004 |
| Polymarket size lean | +0.219 | +0.363 |
| Kalshi drift | -0.003 | -0.006 |
| Kalshi size lean | -0.296 | -0.383 |
| handle % on our side | +79.695 | +74.462 |

## 2. When the two venues disagree on price

_Both are logged on the same side, so `gap` is Polymarket minus Kalshi on that side at the freeze. Backing that side at the sportsbook price._

- games: **753** · mean gap **-0.0026** · median **-0.0100**

| Polymarket vs Kalshi | backing the tracked side |
|---|---|
| PM richer by >3c | 136-103 · **+2.1%** (n=239) |
| PM richer 1–3c | 43-32 · **+8.4%** (n=75) |
| agree within 1c | 39-27 · **+10.4%** (n=66) |
| Kalshi richer 1–3c | 37-44 · **-18.2%** (n=81) |
| Kalshi richer by >3c | 173-119 · **+2.8%** (n=292) |

### Does the best bucket beat the search?

- best: **agree within 1c** at +10.4%
- biggest a price-redraw manufactures across 5 buckets: median **+8.1%**, 95th pct **+21.2%**
- **corrected p = 0.369**

**Does not clear.**

## 3. Does the gap predict where the sportsbook line goes?

_No game outcome needed, so this has the most power of the three. If the venues disagree at the freeze and the book has already moved toward one of them, the gap is information the book is still absorbing._

- games: **750**
- correlation between the venue gap and the book's move: **r = -0.051**

_Near zero. The venue gap and the book's movement are unrelated, so there is nothing here to trade on._

## How to read this

- section 1 answers what was asked and is the least reliable; section 3 is the most powered and needs no outcomes
- a bucket that clears the permutation still needs split-half before it is worth anything — that is the test that killed every other candidate this season
- nothing here changes the board.
