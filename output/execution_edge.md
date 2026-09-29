# Execution — making more without a new edge

_Six edge hunts died out of sample. This looks instead at what happens after the pick is chosen: whether we are getting good prices, and whether the market agrees with us._

## Coverage

- games clearing the consensus gate with a Kalshi close: **313**
- of those, actual board picks: **126**

## 1. Closing line value

_CLV = the de-vigged closing probability of our side minus the de-vigged price we booked. Positive means the market moved toward us. This is the low-variance read: it barely depends on who won._

| population | mean CLV | % beating the close | actual ROI |
|---|---|---|---|
| all consensus-gate games | **-0.10 pts** | 188/313 (60%) | 200-113 · +30.3u · **+9.7%** (n=313) |
| in-sample (< 07-23) | **+0.19 pts** | 108/173 (62%) | 110-63 · +17.2u · **+9.9%** (n=173) |
| holdout (>= 07-23) | **-0.44 pts** | 80/140 (57%) | 90-50 · +13.1u · **+9.4%** (n=140) |
| actual board picks | **-0.17 pts** | 76/126 (60%) | 75-51 · +0.8u · **+0.6%** (n=126) |

**CLV is roughly flat.** We are neither beating nor losing to the close, which is what a breakeven-before-vig selection looks like. The edge, if any, is small enough that price execution matters as much as selection.

## 2. Does CLV predict the winner?

_If picks that beat the close win more often, skipping the rest is a rule that needs no new signal._

| bucket | result |
|---|---|
| CLV positive (market moved to us) | 122-66 · +17.9u · **+9.5%** (n=188) |
| CLV negative (market moved away) | 78-47 · +12.4u · **+9.9%** (n=125) |

_Only decisive moves (2+ points of probability):_

| bucket | result |
|---|---|
| CLV > +2 pts | 5-3 · +0.6u · **+7.8%** (n=8) _(thin)_ |
| CLV < -2 pts | 6-5 · -0.8u · **-7.3%** (n=11) _(thin)_ |

_Holdout on the same split:_

| bucket | in-sample | holdout |
|---|---|---|
| CLV positive | 72-36 · +14.6u · **+13.5%** (n=108) | 50-30 · +3.3u · **+4.2%** (n=80) |
| CLV negative | 38-27 · +2.6u · **+4.0%** (n=65) | 40-20 · +9.8u · **+16.4%** (n=60) |

## 3. Price shopping — units left on the table

_Pure arithmetic, no prediction: for each bet, was Kalshi's ask cheaper than the sportsbook price we booked?_

- bets with a Kalshi ask to compare: **313**
- Kalshi paid better: **285** (91%)
- extra units from always taking the better price: **+12.24u** over 313 bets (**+3.91%** per bet)

_This is additive to whatever the selection edge is - it costs nothing and risks nothing, since it is the same bet at a better price. Execution slippage and Kalshi's fees are not modelled here, so treat it as an upper bound._

_CLV is the number to watch here. It is the one measurement in this repo that gives a usable read at this sample size._