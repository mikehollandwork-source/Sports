# Polymarket trade-out backtest — 147 positions (65 were board PLAYS)

_Enter our side at lock (15 min pre-pitch) at the live PM price; 'lock at +X¢' sells the moment the price reaches entry+X (profit guaranteed regardless of the final score); otherwise the bet settles normally. $1 staked per position. Prices are ~10-min prints with no fee/spread/depth modeling - a stated best case._

_Side-mapping audit: 26 of 147 tokens flipped after price-validation vs the lock-time book price; median |entry - book| now 8.5 pts._

## ALL stat-advantage sides (n=147)

| strategy | locked | record | units | ROI/bet |
|---|---|---|---|---|
| hold to settlement | — | 78-69 | +23.61u | +16.1% |
| lock at +3¢ | 96/147 (65%) | — | +54.47u | +37.1% |
| lock at +5¢ | 93/147 (63%) | — | +54.89u | +37.3% |
| lock at +8¢ | 91/147 (62%) | — | +59.98u | +40.8% |
| lock at +10¢ | 88/147 (60%) | — | +63.49u | +43.2% |
| lock at +15¢ | 81/147 (55%) | — | +69.94u | +47.6% |
| lock at +20¢ | 75/147 (51%) | — | +71.41u | +48.6% |

_Best exit that ever existed (max price minus entry): median +22¢, mean +22¢. A winning position almost always passes through a lockable price on its way to $1 - the question the table answers is whether banking it early beats letting winners settle._

## BOARD PLAYS only (n=65)

| strategy | locked | record | units | ROI/bet |
|---|---|---|---|---|
| hold to settlement | — | 38-27 | +5.23u | +8.0% |
| lock at +3¢ | 42/65 (65%) | — | +13.35u | +20.5% |
| lock at +5¢ | 40/65 (62%) | — | +12.61u | +19.4% |
| lock at +8¢ | 39/65 (60%) | — | +13.55u | +20.8% |
| lock at +10¢ | 37/65 (57%) | — | +14.91u | +22.9% |
| lock at +15¢ | 34/65 (52%) | — | +18.68u | +28.7% |
| lock at +20¢ | 33/65 (51%) | — | +20.26u | +31.2% |

_Best exit that ever existed (max price minus entry): median +22¢, mean +21¢. A winning position almost always passes through a lockable price on its way to $1 - the question the table answers is whether banking it early beats letting winners settle._
