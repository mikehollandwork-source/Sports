# What do winning underdogs have in common?

_Every underdog in the dataset, profiled against everything we record. The headline is not the best cell — it is whether the best cell beats what a scan of this size finds in noise._

## Baseline

- underdog games: **415**
- backing every underdog: 173-242 (42%) · -21.9u · **-5.3%** (n=415)
- raw underdog win rate: **41.7%**

- features scanned: **24**, cells (min n=25): **64**

## Best and worst cells

| cell | all underdogs in it | in-sample | holdout |
|---|---|---|---|
| `consistency_hits high` | 29-27 (52%) · +10.5u · **+18.7%** (n=56) | 16-11 (59%) · +7.9u · **+29.3%** (n=27) | 13-16 (45%) · +2.5u · **+8.8%** (n=29) |
| `form_edge = False` | 26-29 (47%) · +5.8u · **+10.5%** (n=55) | 6-10 (38%) · -0.4u · **-2.4%** (n=16) | 20-19 (51%) · +6.2u · **+15.8%** (n=39) |
| `public_pct_on_dog high` | 52-56 (48%) · +8.1u · **+7.5%** (n=108) | 33-37 (47%) · +3.8u · **+5.4%** (n=70) | 19-19 (50%) · +4.3u · **+11.3%** (n=38) |
| `bvp_ops_to_dog mid` | 47-53 (47%) · +7.1u · **+7.1%** (n=100) | 30-32 (48%) · +5.3u · **+8.5%** (n=62) | 17-21 (45%) · +1.8u · **+4.8%** (n=38) |
| `confidence mid` | 65-73 (47%) · +8.9u · **+6.4%** (n=138) | 41-47 (47%) · +4.3u · **+4.9%** (n=88) | 24-26 (48%) · +4.6u · **+9.1%** (n=50) |
| `wind_mph low` | 56-66 (46%) · +7.2u · **+5.9%** (n=122) | 33-34 (49%) · +8.5u · **+12.7%** (n=67) | 23-32 (42%) · -1.3u · **-2.4%** (n=55) |
| `model_winprob_dog low` | 31-39 (44%) · +3.8u · **+5.4%** (n=70) | 10-14 (42%) · -2.6u · **-10.8%** (n=24) | 21-25 (46%) · +6.4u · **+13.8%** (n=46) |
| `park_factor low` | 80-94 (46%) · +8.9u · **+5.1%** (n=174) | 44-57 (44%) · +0.6u · **+0.6%** (n=101) | 36-37 (49%) · +8.3u · **+11.4%** (n=73) |
| `stat_margin_to_dog low` | 62-77 (45%) · +5.9u · **+4.3%** (n=139) | 36-45 (44%) · +0.1u · **+0.1%** (n=81) | 26-32 (45%) · +5.8u · **+10.0%** (n=58) |
| `sp_dog_edge low` | 35-39 (47%) · +2.6u · **+3.5%** (n=74) | 13-14 (48%) · +0.9u · **+3.3%** (n=27) | 22-25 (47%) · +1.7u · **+3.7%** (n=47) |
| `public_pct_on_dog mid` | 39-70 (36%) · -20.0u · **-18.3%** (n=109) | 22-39 (36%) · -10.3u · **-16.9%** (n=61) | 17-31 (35%) · -9.6u · **-20.1%** (n=48) |
| `dog_home = True` | 41-72 (36%) · -20.9u · **-18.5%** (n=113) | 26-47 (36%) · -15.7u · **-21.5%** (n=73) | 15-25 (38%) · -5.2u · **-13.0%** (n=40) |
| `park_factor high` | 28-51 (35%) · -17.2u · **-21.7%** (n=79) | 21-32 (40%) · -6.5u · **-12.4%** (n=53) | 7-19 (27%) · -10.6u · **-40.8%** (n=26) |
| `ump_r_pg mid` | 31-65 (32%) · -23.0u · **-24.0%** (n=96) | 13-36 (27%) · -19.2u · **-39.3%** (n=49) | 18-29 (38%) · -3.8u · **-8.1%** (n=47) |
| `ump_k_pg low` | 35-67 (34%) · -24.6u · **-24.1%** (n=102) | 14-29 (33%) · -12.4u · **-28.8%** (n=43) | 21-38 (36%) · -12.2u · **-20.7%** (n=59) |

## The test that matters

Best cell: `consistency_hits high` at **+18.7%**.

_Outcomes redrawn 2000 times from each game's de-vigged market price, every cell recomputed, and the BEST cell recorded each time — the distribution of 'best result found while scanning noise'._

- median best-in-noise: **+18.6%**
- 95th percentile of best-in-noise: **+33.4%**
- our best cell: **+18.7%**
- **corrected p = 0.496**

**This does not clear the bar.** A scan of this many cells finds something this good in noise more than 5% of the time, so the headline number is what the search produced, not what the data contains. Whatever story fits the best cell, it is not evidence.

## The other tail — are the LOSING cells real?

Worst cell: `ump_k_pg low` at **-24.1%**.

- median worst-in-noise: **-26.5%**
- 5th percentile of worst-in-noise: **-41.1%**
- our worst cell: **-24.1%**
- **corrected p = 0.615**

**The losing tail does not clear either.** A scan this wide produces cells this bad in noise routinely, so the losing cells are no more real than the winning ones — and reversing them would be betting on the search, not the data.

### Fading the worst cells — what it actually pays

_A dog cell losing 20% does NOT mean backing the favourite there wins 20%; the favourite is priced too. This is the same games, betting the other side._

| cell | backing the dog | backing the FAVOURITE instead |
|---|---|---|
| `public_pct_on_dog mid` | 39-70 (36%) · -20.0u · **-18.3%** (n=109) | 70-39 (64%) · +6.9u · **+6.4%** (n=109) |
| `dog_home = True` | 41-72 (36%) · -20.9u · **-18.5%** (n=113) | 72-41 (64%) · +8.4u · **+7.4%** (n=113) |
| `park_factor high` | 28-51 (35%) · -17.2u · **-21.7%** (n=79) | 51-28 (65%) · +8.3u · **+10.6%** (n=79) |
| `ump_r_pg mid` | 31-65 (32%) · -23.0u · **-24.0%** (n=96) | 65-31 (68%) · +13.7u · **+14.3%** (n=96) |
| `ump_k_pg low` | 35-67 (34%) · -24.6u · **-24.1%** (n=102) | 67-35 (66%) · +9.4u · **+9.2%** (n=102) |

_For reference, backing the favourite in every underdog game: 242-173 (58%) · -11.8u · **-2.8%** (n=415)._

## Reading the cells above

A cell is only interesting if it is strong all-time AND holds in the holdout column AND the corrected p above clears. Any one of those alone is the pattern that has failed repeatedly here.
