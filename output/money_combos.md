# The money side, crossed with everything else

_Every graded game that carries a handle read, anchored on the side the money is on, filtered by every other board stat singly and in pairs._

- graded games with a money side: **905**

## The anchor, before any filter

| | n | result |
|---|---|---|
| back the money side | 905 | 520-385 · **-0.6%** |
| fade the money side | 905 | 385-520 · **-5.6%** |

_Those two sum to -6.2%, which is the hold paid twice. Any filtered cell has to beat that bar, not zero._

- cells at n≥40: **1506** (from 991 combinations × 2 directions)

### Backing the money side on its own

_This one is not part of the search — it is the question as asked, so it takes no multiple-comparison penalty._

- backing the money side: **-0.6%** on 905 bets
- a no-information side at these prices returns about **-3.1%** (half the hold)
- simulating these same bets at their market prices: 95% of outcomes land in **-8.2% to +3.4%**, **p = 0.270** for reaching -0.6% by chance
- **does not beat zero.** It is +2.5 points better than a no-information side, so the handle is carrying something — but not enough to pay the hold, which is the only thing that counts

## The ten best cells — before correction

| cell | n | result |
|---|---|---|
| fade the money WHEN money AGAINST tickets AND pitcher-friendly park | 45 | 32-13 · **+32.7%** |
| fade the money WHEN line vs money: with AND board's fair price likes the money | 64 | 37-27 · **+22.3%** |
| fade the money WHEN money side is the underdog AND Polymarket size leans money | 49 | 33-16 · **+21.6%** |
| fade the money WHEN money AGAINST tickets AND PM quote beats the book | 49 | 31-18 · **+20.9%** |
| fade the money WHEN handle share 60%+ AND pitching dog | 41 | 23-18 · **+20.6%** |
| fade the money WHEN line vs money: with AND public sources corroborated | 120 | 59-61 · **+20.0%** |
| fade the money WHEN money AGAINST tickets AND public sources trusted | 60 | 40-20 · **+19.9%** |
| fade the money WHEN money side has hotter bats AND windy (10mph+) | 124 | 65-59 · **+19.3%** |
| fade the money WHEN money side is the underdog AND 3+ signals hit | 86 | 56-30 · **+18.7%** |
| fade the money WHEN money AGAINST tickets AND money side is the underdog | 67 | 44-23 · **+18.5%** |

_These are the numbers a search of this width produces. Whether any of them is real is the next section, and the answer is almost always no._

## Corrected for the width of the search

_Each trial simulates every game once at its market price and scores all cells on that same slate, so the heavy overlap between cells — and the fact that back and fade on one game cannot both win — is preserved rather than assumed away._

- best: **fade the money WHEN money AGAINST tickets AND pitcher-friendly park** at +32.7% (n=45) · a redraw's best reaches +31.4% median, +46.6% at the 95th · **corrected p = 0.428**
- worst: **back the money WHEN money AGAINST tickets AND pitcher-friendly park** at -41.1% (n=45) · a redraw's worst reaches -36.0% median · **corrected p = 0.230**

**Nothing clears.** The best cell is inside what this search produces from noise, so there is no rule here to ship.

- split-half of **fade the money WHEN money AGAINST tickets AND pitcher-friendly park**: 17-5 · **+45.4%** (n=22) against 15-8 · **+20.6%** (n=23)
- split-half of **back the money WHEN money AGAINST tickets AND pitcher-friendly park**: 6-16 · **-46.9%** (n=22) against 7-16 · **-35.7%** (n=23)
## Why the leaderboard looks one-sided

- of the ten best cells, **10 are fades**
- but every condition set is entered **twice**, as back and as fade, and the pair are mirror images: on the same games they sum to the hold paid twice
- the best and worst cells are the SAME condition set (money AGAINST tickets AND pitcher-friendly park) in opposite directions, +32.7% against -41.1% on the same 45 games
- so a top row being a fade means only that the money side LOST in that cell. It is not evidence that fading works; the mirrored back row is sitting at the bottom of the same list

_A plausible alternative was that fades crowd the top because they take plus-money prices, whose ROI has a long right tail at small n. The data does not support that here:_

- the ten best cells: 44% plus-money, median price -105
- all 1506 cells: 47% plus-money, median price -105
- bare back the money: 12% plus-money, median price -136
- bare fade the money: 79% plus-money, median price +122

_The leaders are no more plus-money than the pool, so the one-sidedness is the mirroring, not the price._


## How to read this

- the corrected p is the whole answer; an uncorrected +15% from a 274-cell search is the expected best from noise, not an edge
- a cell only matters if it clears correction AND both halves agree AND it beats the two-directions-sum bar above
- nothing here changes the board.
