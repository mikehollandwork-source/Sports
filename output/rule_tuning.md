# Tuning the live rule's own thresholds

_Sixteen signal hunts found nothing, and every one asked what ELSE could select a bet. None asked whether the gates already doing the selecting are tuned. These four constants were set early, some on thin data, and have never been swept._

- games reaching the book gate (handle+tickets already agree): **623**

- parameter combinations tried: **288** (225 produced ≥25 picks)
- **live configuration**: readings≥2, spread≤0.15, imbalance>0.2, move≥1.0%, confirm=either
- live result: **+17.6%** over **99** picks

## Top ten configurations

| readings | spread | imbalance | move | confirm | picks | ROI | vs live |
|---|---|---|---|---|---|---|---|
| ≥2 | ≤0.1 | >0.4 | ≥2.0% | BOTH | 31 | **+34.7%** | +0.2pts |
| ≥2 | ≤0.15 | >0.4 | ≥2.0% | BOTH | 31 | **+34.7%** | +0.2pts |
| ≥2 | ≤0.25 | >0.4 | ≥2.0% | BOTH | 31 | **+34.7%** | +0.2pts |
| ≥3 | ≤0.1 | >0.4 | ≥2.0% | BOTH | 31 | **+34.7%** | +0.2pts |
| ≥3 | ≤0.15 | >0.4 | ≥2.0% | BOTH | 31 | **+34.7%** | +0.2pts |
| ≥3 | ≤0.25 | >0.4 | ≥2.0% | BOTH | 31 | **+34.7%** | +0.2pts |
| ≥5 | ≤0.1 | >0.4 | ≥2.0% | BOTH | 31 | **+34.7%** | +0.2pts |
| ≥5 | ≤0.15 | >0.4 | ≥2.0% | BOTH | 31 | **+34.7%** | +0.2pts |
| ≥5 | ≤0.25 | >0.4 | ≥2.0% | BOTH | 31 | **+34.7%** | +0.2pts |
| ≥2 | ≤0.1 | >0.0 | ≥2.0% | BOTH | 32 | **+34.2%** | +0.2pts |

## Does the best configuration beat the sweep itself?

- best gain over live: **+0.2 points**
- median best-gain from redrawn outcomes: **+13.5 points**
- 95th percentile: **+33.7 points**
- **corrected p = 0.370**

**Does not clear.** Sweeping this many combinations produces a gain this large from noise more often than 5% of the time, so the current settings are not demonstrably wrong.

- best config in-sample: **+105.0%** (n=2) · holdout: **+29.8%** (n=29)
- live in-sample: **+34.9%** · holdout: **+16.3%**

## One parameter at a time (others held at live values)

_A single threshold moved in isolation is a far smaller search than the grid, and a real effect should show up as a trend rather than a spike._

| parameter | value | picks | ROI |
|---|---|---|---|
| min readings | 2 ← live | 99 | +17.6% |
| min readings | 3 | 98 | +17.0% |
| min readings | 5 | 98 | +17.0% |
| max spread | 0.1 | 98 | +17.0% |
| max spread | 0.15 ← live | 99 | +17.6% |
| max spread | 0.25 | 101 | +18.6% |
| imbalance min | 0.0 | 103 | +13.2% |
| imbalance min | 0.2 ← live | 99 | +17.6% |
| imbalance min | 0.4 | 97 | +14.0% |
| imbalance min | 0.6 | 95 | +14.4% |
| line move min | 0.005 | 139 | +9.7% |
| line move min | 0.01 ← live | 99 | +17.6% |
| line move min | 0.02 | 54 | +27.1% |
| line move min | 0.03 | 22 | +31.4% |
| confirm | either ← live | 99 | +17.6% |
| confirm | BOTH | 51 | +31.2% |

## The two candidates, tested properly

_Both are SINGLE-parameter moves, a far smaller search than the grid. Each is split by holdout and permuted: labels shuffled, outcomes and prices fixed, asking only whether the threshold carries information._

### line move ≥2.0% vs live ≥1.0%

- kept: **+27.1%** (n=54) · dropped: **+6.1%** (n=45)
- gap **+21.0 points**, permutation **p = 0.104**
- kept in-sample -34.3% (n=3) · holdout **+30.7%** (n=51)
- volume cost: 99 picks → 54 (45% fewer)

### confirm BOTH vs live either

- kept: **+31.2%** (n=51) · dropped: **+1.2%** (n=64)
- gap **+30.0 points**, permutation **p = 0.028**
- kept in-sample +87.9% (n=4) · holdout **+26.4%** (n=47)
- volume cost: 99 picks → 51 (48% fewer)

## What to expect from confirm=BOTH

_A backtest ROI is an upper bound. The configuration was chosen because it looked best, so its realised return regresses toward the pool it was picked from - the same reason a 300-hitter picked for hitting .400 in April finishes nearer .300._

| | live (either) | confirm BOTH |
|---|---|---|
| picks | 99 | **51** |
| ROI | +17.6% | **+31.2%** |
| total units | +17.40u | **+15.93u** |

- ROI improves by **+13.7 points**
- but total units change by **-1.47u** over the same period, because volume falls 48%

**Higher ROI, fewer units.** At a flat stake this change makes LESS money in total while making each bet better. Which one matters depends on whether the stake is capped by bankroll or by opportunity.

- day-block 95% CI on the ROI gain: **+8.0 to +49.6 points**
- share of resamples where BOTH beats live: **100%**

- holdout only: live **+16.3%** (n=92) → BOTH **+26.4%** (n=47), gain **+10.2 points**

_The holdout gain is the number to plan around. The full-period gain includes the games the threshold was chosen on._

## Tighten the book gate, loosen the line gate

_`near_miss` found the gates are not equal. Games failing ONLY the line gate returned +1.0% over 312 games - near-neutral, so those rejections cost volume for little. Games failing ONLY the book gate returned -12.6%, stable at -12.4% and -12.7% across halves - that gate is carrying the work. So tighten what works and relax what does not, instead of tightening both._

| confirm | line move | picks | W-L | win rate | ROI | units |
|---|---|---|---|---|---|---|
| either | ≥0.0% | 225 | 141-84 | **62.7%** | +6.8% | +15.32u |
| either | ≥0.5% | 139 | 88-51 | **63.3%** | +9.7% | +13.43u |
| either ← live | ≥1.0% | 99 | 67-32 | **67.7%** | +17.6% | +17.40u |
| either | ≥2.0% | 54 | 39-15 | **72.2%** | +27.1% | +14.64u |
| BOTH | ≥0.0% | 127 | 82-45 | **64.6%** | +13.2% | +16.80u |
| BOTH | ≥0.5% | 67 | 48-19 | **71.6%** | +30.0% | +20.08u |
| BOTH | ≥1.0% | 51 | 37-14 | **72.5%** | +31.2% | +15.93u |
| BOTH | ≥2.0% | 31 | 22-9 | **71.0%** | +32.6% | +10.12u |

_No combination beats live on BOTH volume and total units._
