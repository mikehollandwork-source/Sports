# Is an unusually LOW prop price a fade?

_Each hitter's baseline is a leave-one-out median of his OWN other quotes, so the day judged never feeds its own baseline. A quoted player who did not bat is dropped, never scored as a no-hit._

- quoted player-days that batted: **3600**
- with a baseline (player has ≥ 8 quotes): **2844** across 223 players
- overall hit rate 60.4% against a mean implied 64.1% → baseline market error **-3.7 pts** (this is the vig, and it is in every bucket)

## By how unusual tonight's price is for him

_`error` is actual minus implied. More negative = he underperformed the price, which is what a fade needs._

| tonight's price vs his own median | n | hit rate | implied | error |
|---|---|---|---|---|
| much cheaper (≤ −6 pts) | 206 | 54.4% | 55.4% | **-1.1 pts** |
| cheaper (−6 to −2) | 618 | 58.3% | 60.9% | **-2.7 pts** |
| about normal (±2) | 1217 | 62.4% | 64.9% | **-2.6 pts** |
| dearer (+2 to +6) | 674 | 61.6% | 67.3% | **-5.8 pts** |
| much dearer (≥ +6 pts) | 129 | 56.6% | 68.9% | **-12.3 pts** |

## Corrected for comparing five buckets

- observed spread between best and worst bucket error: **11.2 pts**
- shuffling outcomes, that spread is typically **14.6 pts** and reaches 11.2 **79.3%** of the time
- **corrected p = 0.7928**

- **the market's error does not depend on how unusual the price is.** An unusually low price is an accurate repricing, not an under-reaction, so there is nothing to fade.
