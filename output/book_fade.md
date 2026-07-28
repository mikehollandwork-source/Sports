# Book fade — back the side with LESS money in the Polymarket book

_153 games with a clean pre-game order-book reading. We back whichever side has less resting money, and only if that side's own price is no worse than -150. $1/bet at the real moneyline._

## Headline

- **All:** 60-85 (41%) · -23.1u · **-15.9%** (n=145)
- **In-sample:** 41-44 (48%) · -3.3u · **-3.9%** (n=85)
- **Holdout:** 19-41 (32%) · -19.8u · **-33.0%** (n=60)

**Day-block bootstrap 95% CI on ROI: -34.5% to +4.7%** (median -16.4%) — **cannot rule out zero**.

**Market-calibrated null p-value: 0.915** — with realistic prices and no edge at all, a result this good happens 91.5% of the time.  That is not significant.

Market-implied win rate for these exact bets: **49.2%**; actual **41.4%** (**-7.9 pts**).

## Mirror check — back the side with MORE money

_If backing the unloved side is a real edge, its exact opposite should lose. If BOTH look positive, the split is noise._

- **All:** 67-56 (54%) · +6.5u · **+5.3%** (n=123)
- **Holdout:** 33-16 (67%) · +15.3u · **+31.3%** (n=49)

## Sweep — minimum money lean required

| min imbalance | ALL | in-sample | HOLDOUT |
|---|---|---|---|
| ≥ 0.0 | 60-85 (41%) · -23.1u · **-15.9%** (n=145) | 41-44 (48%) · -3.3u · **-3.9%** (n=85) | 19-41 (32%) · -19.8u · **-33.0%** (n=60) |
| ≥ 0.1 | 58-77 (43%) · -17.5u · **-13.0%** (n=135) | 40-39 (51%) · +0.3u · **+0.4%** (n=79) | 18-38 (32%) · -17.8u · **-31.8%** (n=56) |
| ≥ 0.2 | 56-73 (43%) · -15.0u · **-11.6%** (n=129) | 38-36 (51%) · +1.8u · **+2.4%** (n=74) | 18-37 (33%) · -16.8u · **-30.5%** (n=55) |
| ≥ 0.4 | 53-69 (43%) · -14.2u · **-11.6%** (n=122) | 36-34 (51%) · +1.5u · **+2.2%** (n=70) | 17-35 (33%) · -15.7u · **-30.2%** (n=52) |
| ≥ 0.6 | 46-58 (44%) · -9.9u · **-9.5%** (n=104) | 31-28 (53%) · +2.6u · **+4.4%** (n=59) | 15-30 (33%) · -12.5u · **-27.7%** (n=45) |

## Sweep — how much are we willing to lay?

| price cap | ALL | in-sample | HOLDOUT |
|---|---|---|---|
| any price | 65-88 (42%) · -23.2u · **-15.2%** (n=153) | 45-46 (49%) · -3.1u · **-3.4%** (n=91) | 20-42 (32%) · -20.2u · **-32.5%** (n=62) |
| ≥ −250 | 65-88 (42%) · -23.2u · **-15.2%** (n=153) | 45-46 (49%) · -3.1u · **-3.4%** (n=91) | 20-42 (32%) · -20.2u · **-32.5%** (n=62) |
| ≥ −180 | 63-88 (42%) · -24.2u · **-16.0%** (n=151) | 43-46 (48%) · -4.0u · **-4.5%** (n=89) | 20-42 (32%) · -20.2u · **-32.5%** (n=62) |
| ≥ −150 (default) | 60-85 (41%) · -23.1u · **-15.9%** (n=145) | 41-44 (48%) · -3.3u · **-3.9%** (n=85) | 19-41 (32%) · -19.8u · **-33.0%** (n=60) |
| ≥ −130 | 53-76 (41%) · -19.0u · **-14.7%** (n=129) | 35-41 (46%) · -4.5u · **-6.0%** (n=76) | 18-35 (34%) · -14.5u · **-27.3%** (n=53) |
| plus money only | 26-44 (37%) · -10.8u · **-15.4%** (n=70) | 16-24 (40%) · -4.4u · **-10.9%** (n=40) | 10-20 (33%) · -6.4u · **-21.3%** (n=30) |

_Composition: 70 of 145 bets are plus-money (48%) — if this is ~100%, the strategy is really just 'bet underdogs' wearing an order-book costume._

_The p-value and the mirror are the honest tests: a real effect is significant against realistic prices AND has a losing opposite._