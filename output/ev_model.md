# EV model — does anything we track beat the market's own price?

_Benter's fundamental model alone was not profitable; the change that made it work was feeding the public odds into the model, because the market already prices what a fundamental model knows. So the question is not whether our model beats the market - it does not, backing `advantage_team` returns -5.9% over 581 games - but whether it adds anything on top of it._

- graded games: **792**

- train (< 2026-07-23): **277** · holdout: **515**

## Holdout scoring — lower is better

| model | log-loss | Brier |
|---|---|---|
| market raw (de-vigged price) | 0.6720 | 0.2397 |
| market only, refit | 0.6749 | 0.2412 |
| **market + our signals** | **0.6762** | **0.2418** |
| **market + schedule/travel** | **0.6745** | **0.2410** |

### Schedule/travel, tested on its own

- schedule features change holdout log-loss by **+0.0004**
- 95% CI: **-0.0092 to +0.0098**
- fitted weights: `road_trip` -0.181, `homestand` +0.058, `rest_edge` -0.062

**No information beyond the price.** The road-trip gradient in `schedule_spots` does not survive being asked whether it adds anything the market has not already priced.

- our signals change holdout log-loss by **-0.0012** (worse than market alone)

- 95% CI on that gain: **-0.0084 to +0.0059**

**No information beyond the price.** The interval includes zero: on this evidence everything we track is already in the market's number, which is exactly what eleven failed selection tests and a -5.9% model baseline have been saying.

## What the fit learned

| feature | weight | reading |
|---|---|---|
| `mkt` | +0.444 | the market's own price |
| `margin` | -0.110 | pushes AGAINST the side it names |
| `bvp` | -0.154 | pushes AGAINST the side it names |
| `pen` | +0.059 | pushes toward the side it names |
| `form` | +0.038 | pushes toward the side it names |
| `line` | +0.012 | adds nothing |
| `lean` | -0.038 | pushes AGAINST the side it names |

## The Benter filter, applied for real

_EV = p·b − (1−p) at the real price, quarter-Kelly staked, holdout games only. Beating log-loss is necessary but not sufficient - a better-calibrated model still has to clear the vig._

- EV-positive bets: **439** of 1030 sides (43%)
- record: **227-212**
- staked 10.36u, P&L **+0.06u**, return on stake **+0.6%**
- mean EV claimed per bet: +0.081

_If the model had no edge, the EV it claims is fictional and this return is the vig showing up as a loss._
