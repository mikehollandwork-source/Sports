# Projecting runs and strikeouts — what the actuals say

_Read-only. No line, no stake, no ROI: this measures the shipped projection and three candidate changes against what actually happened. Beating a price is a separate question the accumulating `market_log` will answer._

- board games that reached a final with a linescore: **1286**
- of those, carrying an umpire tendency: **1038**
- OUT OF SAMPLE for the umpire table (after 2026-07-02): **1038**
- actual full-game runs mean **8.92**, first five **4.96**, game strikeouts **16.85**

## 1. Does the umpire table predict STRIKEOUTS?

_It has only ever been checked against win rates. The table was built `through 2026-07-02`, so the holdout column is games it has never seen - which is the column that matters._

| sample | n | r (k_extra vs game K) | low third K/gm | high third K/gm | gap |
|---|---|---|---|---|---|
| all boards | 1038 | -0.044 | 17.14 (356) | 16.36 (349) | **-0.78** |
| HOLDOUT | 1038 | -0.044 | 17.14 (356) | 16.36 (349) | **-0.78** |

## 2. Does it predict RUNS?

_Opposite sign expected: a strikeout is a ball not in play._

| sample | n | r vs full game | r vs first five | low third runs | high third runs |
|---|---|---|---|---|---|
| all boards | 1038 | +0.019 | -0.037 | 8.52 | 8.92 |
| HOLDOUT | 1038 | +0.019 | -0.037 | 8.52 | 8.92 |

## 3. The shipped runs projection, and splitting the bullpen out of the first five

_`bias` is projected minus actual, so positive means the projection runs hot. `MAE` is the mean absolute miss in runs - lower is better, and it is the number that decides this._

| model | n | bias | MAE | r |
|---|---|---|---|---|
| full game — current (starter FIP only) | 1284 | -0.20 | 3.62 | +0.075 |
| full game — CANDIDATE (starter + pen by innings) | 1284 | -0.19 | 3.54 | +0.097 |
| first five — current | 1284 | -0.11 | 2.66 | +0.063 |
| first five — CANDIDATE (unchanged by construction) | 1284 | -0.11 | 2.66 | +0.063 |

- full-game ΔMAE (candidate − current), day-block bootstrap: **[-0.107, -0.038]** → **the candidate is better** - the interval is entirely below zero

## 4. Starter strikeouts, with and without the umpire

_Point-in-time: the pitcher's K/9 and expected innings come from starts strictly before the game being projected, so nothing sees its own night. Starts under one inning are dropped - an opener or an injury exit is not a projection miss._

| model | n | bias | MAE | r |
|---|---|---|---|---|
| starter K — current | 2353 | +0.71 | 2.26 | +0.149 |
| starter K — CANDIDATE (× umpire) | 2353 | +0.69 | 2.26 | +0.147 |

- ΔMAE (with umpire − without): **[-0.008, +0.018]** → **no improvement - the interval spans zero**

- correlation between `k_extra` and what the current K projection MISSES (actual − projected), n=1894: **+0.012**
  _This is the cleanest form of the question: a positive number means a big-zone umpire adds strikeouts the projection does not already account for._

## 5. Is an umpire's strikeout rate a stable trait?

_Section 1 says the table does not predict. Two things could cause that: the table is three months stale, or there is nothing there to measure. This separates them. Each umpire's games are split into alternate halves and his K/game in one half is correlated with the other, across umpires - then Spearman-Brown lifts that to the reliability of his full record. A near-zero split-half means more games will not help._

## 6. Starter strikeouts: innings per START, not per appearance

_The projection divided ALL-APPEARANCE innings by games STARTED, which overstates how long a pitcher goes whenever he also relieved. Both rates below are point-in-time. `k9/exp_ip from starts` also takes his K rate from starts only, which is the rate a start should be projected at._

| model | n | bias | MAE | r |
|---|---|---|---|---|
| starter K — current (all appearances / starts) | 2353 | +0.71 | 2.26 | +0.149 |
| starter K — CANDIDATE (starts only) | 2353 | +0.06 | 1.89 | +0.404 |

- ΔMAE (starts-only − current): **[-0.435, -0.301]** → **better**

## 7. Two signals the earlier sweep could not have found

_`totals_signal` tested wind SPEED, where a gale blowing in and one blowing out are the same number and cancel; this is the signed component toward centre field. A depleted bullpen can only matter AFTER the starters leave, so it is read against the full game and the first five separately - if it is real, the full-game number is the larger of the two._

| signal | n | r vs full game | r vs first five | low third runs | high third runs | gap |
|---|---|---|---|---|---|---|
| wind out (+) / in (−), mph | 17 | — | — | — | — | — |
| bullpen arms down | 1071 | -0.044 | -0.043 | 8.88 | 8.66 | **-0.22** |
| bullpen innings last 5 | 1286 | -0.001 | +0.010 | 8.92 | 8.98 | **+0.06** |
| temperature °F | 1155 | +0.042 | +0.033 | 8.62 | 9.19 | **+0.57** |

_At n around a thousand the standard error on a correlation is about 0.032, so anything inside roughly ±0.06 is not distinguishable from nothing._
