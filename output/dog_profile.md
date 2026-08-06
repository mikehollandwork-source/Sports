# What do winning underdogs have in common?

_Every underdog in the dataset, profiled against everything we record. The headline is not the best cell — it is whether the best cell beats what a scan of this size finds in noise._

## Baseline

- underdog games: **409**
- backing every underdog: 169-240 (41%) · -24.9u · **-6.1%** (n=409)
- raw underdog win rate: **41.3%**

- features scanned: **24**, cells (min n=25): **64**

## Best and worst cells

| cell | all underdogs in it | in-sample | holdout |
|---|---|---|---|
| `consistency_hits high` | 29-27 (52%) · +10.5u · **+18.7%** (n=56) | 16-11 (59%) · +7.9u · **+29.3%** (n=27) | 13-16 (45%) · +2.5u · **+8.8%** (n=29) |
| `form_edge = False` | 25-29 (46%) · +4.8u · **+8.8%** (n=54) | 6-10 (38%) · -0.4u · **-2.4%** (n=16) | 19-19 (50%) · +5.2u · **+13.6%** (n=38) |
| `public_pct_on_dog high` | 52-56 (48%) · +8.1u · **+7.5%** (n=108) | 33-37 (47%) · +3.8u · **+5.4%** (n=70) | 19-19 (50%) · +4.3u · **+11.3%** (n=38) |
| `confidence mid` | 63-72 (47%) · +7.7u · **+5.7%** (n=135) | 41-47 (47%) · +4.3u · **+4.9%** (n=88) | 22-25 (47%) · +3.4u · **+7.1%** (n=47) |
| `stat_margin_to_dog low` | 62-75 (45%) · +7.2u · **+5.3%** (n=137) | 37-45 (45%) · +1.1u · **+1.4%** (n=82) | 25-30 (45%) · +6.1u · **+11.0%** (n=55) |
| `bvp_ops_to_dog mid` | 45-53 (46%) · +5.0u · **+5.1%** (n=98) | 29-32 (48%) · +4.2u · **+6.9%** (n=61) | 16-21 (43%) · +0.7u · **+2.0%** (n=37) |
| `wind_mph low` | 53-64 (45%) · +5.3u · **+4.5%** (n=117) | 33-34 (49%) · +8.5u · **+12.7%** (n=67) | 20-30 (40%) · -3.3u · **-6.6%** (n=50) |
| `sp_dog_edge low` | 34-38 (47%) · +3.0u · **+4.2%** (n=72) | 13-14 (48%) · +0.9u · **+3.3%** (n=27) | 21-24 (47%) · +2.1u · **+4.7%** (n=45) |
| `park_factor low` | 78-94 (45%) · +6.8u · **+3.9%** (n=172) | 44-57 (44%) · +0.6u · **+0.6%** (n=101) | 34-37 (48%) · +6.2u · **+8.7%** (n=71) |
| `model_winprob_dog low` | 30-39 (43%) · +2.0u · **+3.0%** (n=69) | 10-14 (42%) · -2.6u · **-10.8%** (n=24) | 20-25 (44%) · +4.6u · **+10.3%** (n=45) |
| `dog_home = True` | 40-72 (36%) · -22.0u · **-19.6%** (n=112) | 26-47 (36%) · -15.7u · **-21.5%** (n=73) | 14-25 (36%) · -6.3u · **-16.2%** (n=39) |
| `public_pct_on_dog mid` | 36-68 (35%) · -21.2u · **-20.4%** (n=104) | 22-39 (36%) · -10.3u · **-16.9%** (n=61) | 14-29 (33%) · -10.8u · **-25.2%** (n=43) |
| `park_factor high` | 28-50 (36%) · -16.2u · **-20.7%** (n=78) | 21-32 (40%) · -6.5u · **-12.4%** (n=53) | 7-18 (28%) · -9.6u · **-38.4%** (n=25) |
| `ump_r_pg mid` | 31-65 (32%) · -23.0u · **-24.0%** (n=96) | 13-36 (27%) · -19.2u · **-39.3%** (n=49) | 18-29 (38%) · -3.8u · **-8.1%** (n=47) |
| `ump_k_pg low` | 35-67 (34%) · -24.6u · **-24.1%** (n=102) | 14-29 (33%) · -12.4u · **-28.8%** (n=43) | 21-38 (36%) · -12.2u · **-20.7%** (n=59) |

## The test that matters

Best cell: `consistency_hits high` at **+18.7%**.

_Outcomes redrawn 2000 times from each game's de-vigged market price, every cell recomputed, and the BEST cell recorded each time — the distribution of 'best result found while scanning noise'._

- median best-in-noise: **+18.8%**
- 95th percentile of best-in-noise: **+34.1%**
- our best cell: **+18.7%**
- **corrected p = 0.505**

**This does not clear the bar.** A scan of this many cells finds something this good in noise more than 5% of the time, so the headline number is what the search produced, not what the data contains. Whatever story fits the best cell, it is not evidence.

## Reading the cells above

A cell is only interesting if it is strong all-time AND holds in the holdout column AND the corrected p above clears. Any one of those alone is the pattern that has failed repeatedly here.
