# Walk-forward: line disagrees with handle, bet the money side

_`line_vs_money` had this at 34-21 (+17.3%) backing the dollars against 21-34 (−23.2%) backing the line side, holdout agreeing in direction. It has a mechanism — a book repricing against its own money is acting on information the handle does not reflect._

_**What this cannot establish.** The cell was selected out of ~20 configurations, and every day of data here was already visible when it was picked, so no genuinely out-of-sample period exists and no walk-forward can create one. Its p = 0.043 is uncorrected; across twenty cells that is roughly 0.57._

_**What it can.** Whether the effect is spread through time or is one stretch — the question selection bias does not touch, and the one that killed the gate change, the good dogs and the dogs-and-line conjunction._

- graded games with a line move, a handle side and prices: **756**

## The whole sample, for reference

| | bet the money side | bet the line side |
|---|---|---|
| line DISAGREES with handle | 209-146 · **+5.3%** (n=355) | 146-209 · **-11.6%** (n=355) |
| line AGREES with handle | 228-173 · **-4.2%** (n=401) | 228-173 · **-4.2%** (n=401) |

## Block by block, rule fixed at the original ≥1% bar

_Is it spread through time, or one stretch?_

| block starts | money side | n |
|---|---|---|
| 2026-07-02 | +18.9% | 22 |
| 2026-07-12 | +4.2% | 27 |
| 2026-07-26 | +9.7% | 31 |
| 2026-08-05 | -21.4% | 29 |
| 2026-08-15 | +28.6% | 24 |
| 2026-08-25 | +22.2% | 20 |
| 2026-09-04 | -12.3% | 31 |
| 2026-09-15 | +10.6% | 28 |

- profitable blocks: **6/8** · median block **+10.2%**
- **spread through time**, not one stretch

## Fitting the one free parameter honestly

_The 1% bar was set with no justification given. Here it is chosen on past blocks only and scored on the next._

- thresholds chosen: 3.0%×6
- **out-of-sample: 30-21 · **+8.4%** (n=51)**

| fixed bar over the same days | money side |
|---|---|
| ≥0.5% | 131-96 · **+2.6%** (n=227) |
| ≥1.0% | 95-71 · **+1.8%** (n=166) |
| ≥2.0% | 62-40 · **+9.7%** (n=102) |
| ≥3.0% | 30-21 · **+8.4%** (n=51) |

## Against the agreeing pool, day-block bootstrapped

- disagree: 132-95 · **+5.3%** (n=227) · agree: 172-131 · **-5.2%** (n=303)
- difference **+10.5 pts** · 95% CI **-4.8 to +25.5**

## The bar

- spread across blocks, an out-of-sample threshold choice that does not fall apart, and a difference whose interval clears zero
- none of which fixes the selection. Only games played AFTER today can do that
