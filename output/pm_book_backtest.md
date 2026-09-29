# Polymarket order-book backtest — 60 graded of 70 tracked plays

_Order-book money on our side (resting-size imbalance + pre-game price drift), NOT the mid quote. Bet our side at the book moneyline, $1/pick. Order-book logging is days old, so every row is small — read the n=._

## Order-book price DRIFT toward our side (money flowing in)

| slice | record | units | ROI/bet |
|---|---|---|---|
| drift up (>0) — money came to us (n=32) | 15-17 (47%) | -6.75u | -21.1% |
|   ...meaningful (drift ≥ +0.03) (n=13) | 5-8 (38%) | -4.44u | -34.2% |
| drift down (<0) — money left us (n=21) | 10-11 (48%) | -3.57u | -17.0% |

## Order-book SIZE imbalance (more resting money on our side)

| slice | record | units | ROI/bet |
|---|---|---|---|
| more money on us (imb > +0.2) (n=31) | 15-16 (48%) | -5.77u | -18.6% |
| balanced (±0.2) (n=9) | 6-3 (67%) | +1.38u | +15.3% |
| more money against us (imb < -0.2) (n=20) | 9-11 (45%) | -4.03u | -20.2% |

## Order-book money on us + each signal (does the pair net a win?)

_'book money on us' = price drifted up OR resting size leans our way._

| pair | record | units | ROI/bet |
|---|---|---|---|
| book money on us (alone) (n=46) | 22-24 (48%) | -9.00u | -19.6% |
|   + margin (n=12) | 4-8 (33%) | -5.56u | -46.3% |
|   + line (n=20) | 10-10 (50%) | -4.69u | -23.5% |
|   + consistency (n=35) | 15-20 (43%) | -9.35u | -26.7% |
|   + favorite (n=41) | 21-20 (51%) | -6.00u | -14.6% |
|   + bvp (n=35) | 18-17 (51%) | -4.58u | -13.1% |
|   + form (n=31) | 13-18 (42%) | -8.64u | -27.9% |

_Exploratory: pre-game order book vs the graded result; $1/bet at the book moneyline. Samples are small until the book log accumulates._