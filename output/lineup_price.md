# Does lineup prop pricing beat the moneyline?

_Average 1+ hit price across each starting lineup, compared between the two teams, then tested against the moneyline rather than against nothing._

- graded games with both lineups priced: **213**

- mean starters priced per side: 7.9
- mean lineup hit probability (raw, vig included): 63.4%

## 1. On its own — and against the moneyline

| predictor of a home win | AUC |
|---|---|
| lineup prop edge | 0.5979 |
| **moneyline** | **0.6087** |

_Both should beat 0.50. The question is the next section._

## 2. Held against the moneyline

_Games split into thirds by moneyline, then each third split by prop edge. If the prop aggregate is only restating the price, the two halves inside a third win at the same rate._

| moneyline third | prop edge | n | home win% |
|---|---|---|---|
| longest home dogs | above median | 35 | 57.1% |
| longest home dogs | below median | 36 | 33.3% |
| middle | above median | 35 | 51.4% |
| middle | below median | 36 | 50.0% |
| biggest home favs | above median | 35 | 57.1% |
| biggest home favs | below median | 36 | 66.7% |

_Mean gap between the two halves, inside a moneyline third: **+5.2%**. That is the part the moneyline had not already priced._

## 3. Betting it

_Back the side the props favour, whenever they disagree with the moneyline by more than a threshold. Graded at the board's own price._

| disagreement | bets | record | units | ROI |
|---|---|---|---|---|
| edge ≥ 0% | 52 | 29-23 | +8.88u | **+17.1%** |
| edge ≥ 1% | 30 | 15-15 | +1.50u | **+5.0%** |
| edge ≥ 2% | 16 | 6-10 | -3.38u | **-21.1%** |
| edge ≥ 3% | 4 | _too few_ | | |

### Is any of that real?

- **edge ≥ 0%** (52 bets): +17.1% · fairly-priced bets land in -30.8% to +27.1% 95% of the time · **p = 0.102**
- **edge ≥ 1%** (30 bets): +5.0% · fairly-priced bets land in -38.2% to +34.4% 95% of the time · **p = 0.365**

_The betting rows are also NON-MONOTONIC: the return falls as the disagreement widens. A real edge gets better with conviction, not worse, and the control buckets above disagree in sign — one third runs the wrong way. Both are signatures of a single lucky cell, not a signal._


## How to read this

- section 1 proves nothing: a lineup the book prices highly wins more often, which is the moneyline restated
- section 2 is the real test. A gap near zero means the prop aggregate is already inside the team price and there is nothing to add
- section 3 pays the vig, so it has to clear roughly +3% to be worth anything at all, and n is small at the wider thresholds
- the per-hitter vig could not be removed (only 2% of stored prices are two-sided), so the edge is a difference of two inflated numbers — mostly cancelling, not perfectly
