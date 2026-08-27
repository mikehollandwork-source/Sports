# EV model — does anything we track beat the market's own price?

_Benter's fundamental model alone was not profitable; the change that made it work was feeding the public odds into the model, because the market already prices what a fundamental model knows. So the question is not whether our model beats the market - it does not, backing `advantage_team` returns -5.9% over 581 games - but whether it adds anything on top of it._

- graded games: **795**

- train (< 2026-07-23): **336** · holdout: **459**

## Holdout scoring — lower is better

| model | log-loss | Brier |
|---|---|---|
| market raw (de-vigged price) | 0.6739 | 0.2406 |
| market only, refit | 0.6767 | 0.2420 |
| **market + our signals** | **0.6801** | **0.2435** |

- our signals change holdout log-loss by **-0.0034** (worse than market alone)

- 95% CI on that gain: **-0.0084 to +0.0014**

**No information beyond the price.** The interval includes zero: on this evidence everything we track is already in the market's number, which is exactly what eleven failed selection tests and a -5.9% model baseline have been saying.

## What the fit learned

| feature | weight | reading |
|---|---|---|
| `mkt` | +0.337 | the market's own price |
| `margin` | +0.056 | pushes toward the side it names |
| `bvp` | -0.057 | pushes AGAINST the side it names |
| `pen` | +0.045 | pushes toward the side it names |
| `form` | -0.013 | adds nothing |
| `line` | +0.000 | adds nothing |
| `lean` | +0.075 | pushes toward the side it names |

## The Benter filter, applied for real

_EV = p·b − (1−p) at the real price, quarter-Kelly staked, holdout games only. Beating log-loss is necessary but not sufficient - a better-calibrated model still has to clear the vig._

- EV-positive bets: **399** of 918 sides (43%)
- record: **208-191**
- staked 7.20u, P&L **-0.40u**, return on stake **-5.6%**
- mean EV claimed per bet: +0.062

_If the model had no edge, the EV it claims is fictional and this return is the vig showing up as a loss._
