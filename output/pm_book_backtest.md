# Polymarket order-book backtest — 36 graded of 40 tracked plays

_Order-book money on our side (resting-size imbalance + pre-game price drift), NOT the mid quote. Bet our side at the book moneyline, $1/pick. Order-book logging is days old, so every row is small — read the n=._

## Order-book price DRIFT toward our side (money flowing in)

| slice | record | units | ROI/bet |
|---|---|---|---|
| drift up (>0) — money came to us (n=18) | 9-9 (50%) | -2.55u | -14.2% |
|   ...meaningful (drift ≥ +0.03) (n=7) | 2-5 (29%) | -3.37u | -48.1% |
| drift down (<0) — money left us (n=14) | 6-8 (43%) | -3.61u | -25.8% |

## Order-book SIZE imbalance (more resting money on our side)

| slice | record | units | ROI/bet |
|---|---|---|---|
| more money on us (imb > +0.2) (n=17) | 7-10 (41%) | -4.97u | -29.2% |
| balanced (±0.2) (n=7) | 5-2 (71%) | +1.24u | +17.7% |
| more money against us (imb < -0.2) (n=12) | 6-6 (50%) | -1.35u | -11.2% |

## Order-book money on us + each signal (does the pair net a win?)

_'book money on us' = price drifted up OR resting size leans our way._

| pair | record | units | ROI/bet |
|---|---|---|---|
| book money on us (alone) (n=28) | 13-15 (46%) | -6.00u | -21.4% |
|   + margin (n=6) | 2-4 (33%) | -2.59u | -43.2% |
|   + line (n=12) | 6-6 (50%) | -2.71u | -22.6% |
|   + consistency (n=20) | 8-12 (40%) | -6.32u | -31.6% |
|   + favorite (n=25) | 13-12 (52%) | -3.00u | -12.0% |
|   + bvp (n=20) | 9-11 (45%) | -4.59u | -22.9% |
|   + form (n=19) | 7-12 (37%) | -6.71u | -35.3% |

_Exploratory: pre-game order book vs the graded result; $1/bet at the book moneyline. Samples are small until the book log accumulates._