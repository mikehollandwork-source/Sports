# Polymarket trade-out backtest — 4 positions (2 were board PLAYS)

_Enter our side at lock (15 min pre-pitch) at the live PM price; 'lock at +X¢' sells the moment the price reaches entry+X (profit guaranteed regardless of the final score); otherwise the bet settles normally. $1 staked per position. Prices are ~10-min prints with no fee/spread/depth modeling - a stated best case._

_Side-mapping audit: 2 of 4 tokens flipped after price-validation vs the lock-time book price; median |entry - book| now 4.4 pts._

## ALL stat-advantage sides (n=4)

| strategy | locked | record | units | ROI/bet |
|---|---|---|---|---|
| hold to settlement | — | 3-1 | +1.17u | +29.4% |
| lock at +3¢ | 3/4 (75%) | — | +1.16u | +28.9% |
| lock at +5¢ | 3/4 (75%) | — | +1.26u | +31.6% |
| lock at +8¢ | 3/4 (75%) | — | +1.42u | +35.5% |
| lock at +10¢ | 3/4 (75%) | — | +1.53u | +38.1% |
| lock at +15¢ | 3/4 (75%) | — | +1.79u | +44.7% |
| lock at +20¢ | 3/4 (75%) | — | +2.05u | +51.3% |

_Best exit that ever existed (max price minus entry): median +37¢, mean +32¢. A winning position almost always passes through a lockable price on its way to $1 - the question the table answers is whether banking it early beats letting winners settle._

## BOARD PLAYS only (n=2)

| strategy | locked | record | units | ROI/bet |
|---|---|---|---|---|
| hold to settlement | — | 1-1 | -0.43u | -21.3% |
| lock at +3¢ | 2/2 (100%) | — | +0.11u | +5.5% |
| lock at +5¢ | 2/2 (100%) | — | +0.18u | +9.1% |
| lock at +8¢ | 2/2 (100%) | — | +0.29u | +14.6% |
| lock at +10¢ | 2/2 (100%) | — | +0.37u | +18.3% |
| lock at +15¢ | 2/2 (100%) | — | +0.55u | +27.4% |
| lock at +20¢ | 2/2 (100%) | — | +0.73u | +36.6% |

_Best exit that ever existed (max price minus entry): median +44¢, mean +44¢. A winning position almost always passes through a lockable price on its way to $1 - the question the table answers is whether banking it early beats letting winners settle._
