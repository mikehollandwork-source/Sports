# Do good teams beat their price when the market makes them dogs?

_Philadelphia went 4-12 as a dog, so the hypothesis was that usually-favourite teams UNDERperform as dogs. `league_calibration` found the opposite — every cut positive, +3.4% to +7.9% against −5.8% for dogs generally. The lead was backwards and this direction was found by scanning, which is the weakest provenance there is. What it has is size: 159–383 games against Philadelphia's sixteen._

- graded games: **1223** · underdog team-games: **1081**

## Season-long favourite rate

_Circular by construction — a team's favourite rate comes from the same season being scored — but it is what `league_calibration` reported, so it is here to compare against the honest version below._

| cut | teams | their dog games | record | vs OTHER dogs | difference | 95% CI |
|---|---|---|---|---|---|---|
| ≥55% | 18 | 383 | 183-200 · exp 167.8 · **+5.7%** | 263-435 · exp 288.3 · **-11.2%** | **+16.9 pts** | +2.1 to +31.5 |
| ≥60% | 15 | 276 | 134-142 · exp 121.2 · **+7.9%** | 312-493 · exp 335.0 · **-9.7%** | **+17.6 pts** | -0.0 to +35.2 |
| ≥65% | 13 | 213 | 102-111 · exp 94.6 · **+5.1%** | 344-524 · exp 361.5 · **-7.7%** | **+12.8 pts** | -6.2 to +31.6 |
| ≥70% | 11 | 159 | 75-84 · exp 70.8 · **+3.4%** | 371-551 · exp 385.3 · **-6.7%** | **+10.0 pts** | -9.4 to +29.3 |

## Favourite rate from PRIOR games only

_The honest version. A team's favourite rate is computed from its games before the one being scored, needing 20 of them, so a team that got hot is not labelled a favourite partly because of the wins being counted._

| cut | dog games | record | vs OTHER dogs | difference | 95% CI |
|---|---|---|---|---|---|
| ≥55% | 295 | 134-161 · exp 129.7 · **+1.6%** | 216-343 · exp 230.1 · **-8.9%** | **+10.5 pts** | -6.4 to +27.8 |
| ≥60% | 238 | 111-127 · exp 104.8 · **+4.4%** | 239-377 · exp 255.1 · **-9.0%** | **+13.3 pts** | -2.9 to +29.6 |
| ≥65% | 194 | 92-102 · exp 85.8 · **+5.2%** | 258-402 · exp 274.1 · **-8.3%** | **+13.5 pts** | -6.9 to +33.9 |
| ≥70% | 159 | 80-79 · exp 70.6 · **+11.2%** | 270-425 · exp 289.2 · **-9.0%** | **+20.2 pts** | -1.1 to +41.6 |

## Corrected across the 4 cuts (prior-games)

- best cut **≥70%** at +20.2 pts · the best of 4 cuts reaches +3.6 median, +17.7 at the 95th · **corrected p = 0.026**

- split-half: **+22.9 pts** on one half, **+17.3 pts** on the other
- **both halves agree in sign**

## Month by month

| month | good dogs | other dogs | difference |
|---|---|---|---|
| 2026-07 | 15-17 · exp 14.1 · **+2.7%** | 35-49 · exp 35.0 · **-4.3%** | **+7.0 pts** |
| 2026-08 | 39-32 · exp 31.5 · **+23.5%** | 123-205 · exp 137.4 · **-12.1%** | **+35.5 pts** |
| 2026-09 | 26-30 · exp 25.0 · **+0.4%** | 112-171 · exp 116.8 · **-6.9%** | **+7.3 pts** |

## Leave August out — the test that killed the gate change

_August was hot: `change_check` showed the gate change worth +9.6 points in August and −11.6 in September, and that is why it was reverted. This effect is +35.5 points in August against +7.0 and +7.3 either side, so it has to clear the same bar._

| period | good dogs | other dogs | difference |
|---|---|---|---|
| all months | 80-79 · exp 70.6 · **+11.2%** | 270-425 · exp 289.2 · **-9.0%** | **+20.2 pts** (-1 to +42) |
| **excluding August** | 41-47 · exp 39.2 · **+1.2%** | 147-220 · exp 151.8 · **-6.3%** | **+7.5 pts** (-21 to +35) |
| August only | 39-32 · exp 31.5 · **+23.5%** | 123-205 · exp 137.4 · **-12.1%** | **+35.5 pts** (+2 to +68) |

**Outside August it is worth +7.5 points.** The effect survives removing the hot month, so it is not the month talking.

## Temporal holdout — cut chosen on the first half only

_The split-half above assigns games at random, so both halves contain August. This picks the cut using only games before 2026-08-23 and scores it on games from 2026-08-23 on — the ordering a live rule actually faces._

- best cut on the first half: **≥70%** (+27.7 pts there)
- that cut on the held-out second half: 37-40 · exp 34.5 · **+3.9%** against 147-228 · exp 155.9 · **-8.4%** → **+12.3 pts**

## The bar

- the **difference** against other underdogs is the number, not the ROI — underdogs generally returned −5.8%, so a positive ROI here is partly just "underdogs did alright"
- it has to survive the correction across cuts AND agree in sign across halves AND not be one month
- the prior-games table is the one to believe; the season-long one peeks at the results it is being scored on
