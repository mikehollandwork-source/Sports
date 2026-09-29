# Philadelphia Phillies, in depth

_`team_calibration` put their expected wins at 46.3 against 44 actual, p = 0.651 — inside a simulated range of 38 to 55. That is true and nearly content-free: the range is seventeen wins wide, so win totals alone cannot tell you whether a single team was mispriced. These are the questions that do not depend on win totals._

- graded games: **82**

## Is it a trend, or five cells alternating?

_A real favourite bias gets worse the shorter the price — a trend. Noise alternates. This correlates the residual (won, minus the probability the market gave them) against that probability, across all 82 games rather than in five cells of 15._

- correlation of residual with implied probability: **+0.233**
- permuted null: +0.002 average, 95% within ±0.213
- **two-sided p = 0.034** — a genuine trend across price

## Are the losses close, or are they blowouts?

_Same record, opposite conclusion: missing a price through one-run losses is variance that reverts; getting blown out is being worse than the price and does not._

- runs: **364 scored, 348 allowed** over 82 games
- Pythagorean expectation from those runs: **52.1%**, actual **53.7%** → they won **+1.3** games more than their run differential deserved
- average margin in wins **+3.64**, in losses **-3.79**
- one-run games: **9-10** (19 games)
- blowouts (5+): **16-11** (27 games)

## Where our model disagrees with the market about them

| | games | market expected | actual | gap | ROI |
|---|---|---|---|---|---|
| market made them favourite | 66 | 39.0 | 40 | **+1.0** | -1.1% |
| market made them underdog | 16 | 7.3 | 4 | **-3.3** | -47.4% |

## By month — has the market adjusted?

| | games | market expected | actual | gap | ROI |
|---|---|---|---|---|---|
| 2026-06 | 6 | 3.4 | 4 | **+0.6** | +4.8% |
| 2026-07 | 24 | 13.1 | 9 | **-4.1** | -37.3% |
| 2026-08 | 28 | 16.9 | 21 | **+4.1** | +23.6% |
| 2026-09 | 24 | 12.9 | 10 | **-2.9** | -26.0% |

## The standout cell, split in half

_Their +25.6% as a clear favourite (−179 to −140) is the best of five buckets. Every candidate of that shape has failed this season, so it gets the test rather than a mention._

- one half: +39.8% (n=14) · other half: +9.1% (n=12)
- **both halves agree in sign** — worth a proper walk-forward

## What to take from this

- win totals over one season cannot settle whether a team is mispriced; the trend test and the run differential can, because they use every game rather than a 15-game cell
- a flat-stake return near **−4% to −5%** is a correctly priced team. That is the hold, not a failing
