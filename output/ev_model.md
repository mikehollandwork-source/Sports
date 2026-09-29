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
| **market + deep-trip flag (≥6)** | **0.6742** | **0.2406** |
| **market + signals + price interactions** | **0.6929** | **0.2488** |

### Does the closing price change what a signal is worth?

_Each signal multiplied by the market logit. A non-zero weight means the signal pays differently on favourites than on dogs - the same question the price grid asks, but with one coefficient instead of ~98 cells, and scored on every game._

- interactions change holdout log-loss by **-0.0167** vs signals alone
- 95% CI: **-0.0338 to -0.0001**
- weights: `margin_x_mkt` +0.066, `bvp_x_mkt` +0.006, `pen_x_mkt` -0.288, `form_x_mkt` +0.032, `line_x_mkt` +0.015, `lean_x_mkt` -0.175

**Price does not rescue any signal.** Interacting every signal with the market's own price adds nothing beyond the signals themselves, which already add nothing beyond the price.

_Deep-trip flag alone (visitor on 6+ straight road games): log-loss change **+0.0008**, 95% CI **-0.0119 to +0.0130**, weight `deep_trip` -0.282._

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
