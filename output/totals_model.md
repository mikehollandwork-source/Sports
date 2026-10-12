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

- umpires with 10+ board games: **74** (mean 11.6 games each)
- split-half correlation of K/game: **+0.172**
- Spearman-Brown, lifted to the full record: **+0.293**
- **a trait exists, but a weak one.** At this reliability the honest use of `k_extra` is to shrink it toward zero by roughly that fraction - which makes an already-null term smaller, not larger. And note what this number cannot separate: an umpire's K/game also reflects the PITCHERS he drew, and over ~12 games that is most of it. Section 8 strips that out.

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
| wind out (+) / in (−), mph | 803 | +0.055 | +0.028 | 8.68 | 9.21 | **+0.54** |
| bullpen arms down | 1071 | -0.044 | -0.043 | 8.88 | 8.66 | **-0.22** |
| bullpen innings last 5 | 1286 | -0.001 | +0.010 | 8.92 | 8.98 | **+0.06** |
| temperature °F | 1155 | +0.042 | +0.033 | 8.62 | 9.19 | **+0.57** |

_At n around a thousand the standard error on a correlation is about 0.032, so anything inside roughly ±0.06 is not distinguishable from nothing._

## 8. The umpire, measured as strikeouts ABOVE the pitchers

_`k_extra` is raw K/game, so over a dozen games it largely measures which PITCHERS the umpire drew - which is the likeliest reason section 1 comes back wrong-signed. This averages the projection's residual instead, which removes the pitcher by construction, and then asks the first half of the season to predict the second._

- usable starts: **1900**, split at **2026-08-16**
- umpires with 12+ starts in the first half: **40**
- second-half starts under one of them: **432**
- spread of their residual tendencies: SD **0.57** K/start, range -1.51 to +1.24
- noise floor for that spread: **0.64** (per-start residual SD 2.36 over √14 starts each)
- **the spread is 0.90× the floor, i.e. no larger than pure sampling noise.** Umpires that genuinely differed would spread WIDER than this. There is no umpire-level variance to find, which is a stronger result than the correlation below: it is not that the table is stale or built wrong, it is that the quantity it is trying to measure is not there.

- **OUT-OF-SAMPLE correlation, first-half tendency vs second-half residual: -0.067** (n=432, SE about 0.048)
- second-half residual by first-half tendency: low third **+0.01** K/start (154), high third **-0.37** (152), gap **-0.38**
- **still nothing.** Removing the pitcher confound does not rescue it, so the umpire is not a usable strikeout term in this data - not because the table is stale or built wrong, but because the effect is too small to survive one start's variance.

## 9. Temperature and wind-out as ONE carry term

_Both are the same mechanism - how far a struck ball carries - and section 7 leaves each at about 1.5 standard errors with the right sign. Read as one standardized index instead. The combination was chosen after seeing both halves, so the correlation is not a clean p-value; the MAE line is what decides it._

- games with temperature and a readable wind: **803**
- carry index vs full-game runs: **+0.084** (SE about 0.035)
- carry index vs first-five runs: **+0.057**
- full-game runs: low third **8.51**, high third **9.46**, gap **+0.95**
- derived slope: **+0.509 runs per unit of the index** (one unit is about 10°F and the same again in wind)

| model | n | bias | MAE | r |
|---|---|---|---|---|
| full game — shipped (starter + pen) | 801 | -0.23 | 3.55 | +0.100 |
| full game — + carry term | 801 | -0.23 | 3.53 | +0.121 |

- ΔMAE (with carry − without), day-block bootstrap: **[-0.041, +0.002]** → **do not ship.** The interval spans zero: the term is the right sign and the right mechanism and still does not lower the error, which is what a 1.5-sigma signal looks like when it is real but too small to matter
