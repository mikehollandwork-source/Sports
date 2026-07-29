# Polymarket viability — 81 consensus picks with a real pre-game order-book price

_Executed at the Polymarket ask before first pitch, net of a 2% fee on winnings. Compared against the sportsbook moneyline every backtest so far has used._

| board | at BOOK price | at POLYMARKET price |
|---|---|---|
| unfiltered consensus | 53-28 (65%) · **+8.3%** (n=81) | 53-28 (65%) · **+8.7%** (n=81) |
| line-against filtered (live board) | 11-5 (69%) · **+25.5%** (n=16) | 11-5 (69%) · **+23.7%** (n=16) |

## Why — the price gap

- Polymarket asks **+1.0 probability points** vs the sportsbook implied price on average (median -1.7).
- PM was the WORSE price on **36 of 81** picks (44%).
- Positive = we pay more on Polymarket, and that difference comes straight out of the edge.

## Liquidity at the moment of the bet

- Top-of-book size available: median **$97**, 25th pct **$35**, min **$0**.
- Picks with under $100 available: **41 of 81**.
- A stake beyond top-of-book walks the price up and cuts the edge further than the table above shows.

## Fee sensitivity (unfiltered board)

| fee on winnings | PM ROI |
|---|---|
| 0% | +9.6% |
| 2% | +8.7% |
| 5% | +7.4% |

_Every number here uses the REAL recorded ask at the last clean pre-game reading, so it reflects what a bot would have paid - not an assumed price._