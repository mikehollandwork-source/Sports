# BvP and stat-edge margin — alone, combined, and against the line

- graded games with a price and a margin: **581**

## Baselines — the model betting itself

| what | result |
|---|---|
| back `advantage_team`, every game | 306-275 (53%) · -34.1u · **-5.9%** (n=581) |
| back the BvP `edge_team` | 262-268 (49%) · -39.3u · **-7.4%** (n=530) |
| back the bullpen-BvP `edge_team` | 246-237 (51%) · -11.2u · **-2.3%** (n=483) |

_This is the number the whole board rests on. Every cell below has to beat it, not merely beat zero._

## Margin alone (backing `advantage_team`)

| min margin | result |
|---|---|
| ≥0.00 | 306-275 (53%) · -34.1u · **-5.9%** (n=581) |
| ≥0.10 | 239-208 (53%) · -24.8u · **-5.5%** (n=447) |
| ≥0.20 | 161-155 (51%) · -36.3u · **-11.5%** (n=316) |
| ≥0.30 | 113-100 (53%) · -19.6u · **-9.2%** (n=213) |
| ≥0.50 | 50-32 (61%) · +2.2u · **+2.6%** (n=82) |

## BvP alone (backing the BvP `edge_team`)

| min gap | starter BvP | bullpen BvP |
|---|---|---|
| ≥0.00 | 262-268 (49%) · -39.3u · **-7.4%** (n=530) | 246-237 (51%) · -11.2u · **-2.3%** (n=483) |
| ≥0.04 | 178-206 (46%) · -51.5u · **-13.4%** (n=384) | 206-196 (51%) · -8.4u · **-2.1%** (n=402) |
| ≥0.08 | 131-138 (49%) · -25.2u · **-9.4%** (n=269) | 176-158 (53%) · -0.9u · **-0.3%** (n=334) |
| ≥0.14 | 73-64 (53%) · -2.5u · **-1.8%** (n=137) | 125-103 (55%) · +7.7u · **+3.4%** (n=228) |
| ≥0.25 | 27-16 (63%) · +5.7u · **+13.3%** (n=43) | 58-46 (56%) · +5.4u · **+5.2%** (n=104) |

_BvP flagged `meaningful`_: 141-175 (45%) · -52.3u · **-16.6%** (n=316)

## Combined — does BvP agree with the margin?

| case | backing `advantage_team` |
|---|---|
| BvP agrees | 157-148 (51%) · -27.1u · **-8.9%** (n=305) |
| BvP disagrees | 120-105 (53%) · -8.8u · **-3.9%** (n=225) |
| BvP disagrees — back the BvP side instead | 105-120 (47%) · -12.2u · **-5.4%** (n=225) |

### Agreement, swept on both thresholds

| min margin | gap ≥0.00 | gap ≥0.04 | gap ≥0.08 | gap ≥0.14 | gap ≥0.25 |
|---|---|---|---|---|---|
| ≥0.00 | 157-148 (51%) · -27.1u · **-8.9%** (n=305) | 105-117 (47%) · -36.9u · **-16.6%** (n=222) | 79-81 (49%) · -20.4u · **-12.7%** (n=160) | 40-37 (52%) · -6.5u · **-8.4%** (n=77) | 15-10 (60%) · +1.7u · **+6.7%** (n=25) _(thin)_ |
| ≥0.10 | 119-111 (52%) · -23.2u · **-10.1%** (n=230) | 84-91 (48%) · -28.8u · **-16.5%** (n=175) | 62-64 (49%) · -18.2u · **-14.4%** (n=126) | 30-29 (51%) · -7.0u · **-11.9%** (n=59) | 12-9 (57%) · -0.4u · **-1.8%** (n=21) _(thin)_ |
| ≥0.20 | 85-84 (50%) · -24.4u · **-14.4%** (n=169) | 59-70 (46%) · -29.3u · **-22.7%** (n=129) | 45-50 (47%) · -19.0u · **-20.0%** (n=95) | 24-23 (51%) · -6.8u · **-14.5%** (n=47) | 9-5 (64%) · +0.8u · **+5.8%** (n=14) _(thin)_ |
| ≥0.30 | 60-56 (52%) · -15.2u · **-13.1%** (n=116) | 41-48 (46%) · -21.0u · **-23.6%** (n=89) | 31-33 (48%) · -12.7u · **-19.9%** (n=64) | 16-12 (57%) · -1.5u · **-5.4%** (n=28) _(thin)_ | 7-3 (70%) · +1.4u · **+14.1%** (n=10) _(thin)_ |
| ≥0.50 | 26-20 (57%) · -2.9u · **-6.3%** (n=46) | 19-17 (53%) · -5.6u · **-15.6%** (n=36) _(thin)_ | 14-11 (56%) · -2.8u · **-11.3%** (n=25) _(thin)_ | 6-2 (75%) · +0.9u · **+11.1%** (n=8) _(thin)_ | 3-1 (75%) · +0.6u · **+14.0%** (n=4) _(thin)_ |

## Crossed with line movement

Both directions at every threshold, because choosing the direction after seeing the numbers turns a coin flip into a "finding".

| min move | agree + line TOWARD us | agree + line AGAINST us |
|---|---|---|
| ≥0.5% | 75-62 (55%) · -10.2u · **-7.4%** (n=137) | 52-59 (47%) · -14.6u · **-13.2%** (n=111) |
| ≥1.0% | 61-50 (55%) · -9.2u · **-8.2%** (n=111) | 40-45 (47%) · -10.0u · **-11.8%** (n=85) |
| ≥2.0% | 37-29 (56%) · -7.7u · **-11.7%** (n=66) | 22-29 (43%) · -8.0u · **-15.7%** (n=51) |
| ≥3.0% | 25-21 (54%) · -6.8u · **-14.9%** (n=46) | 10-15 (40%) · -4.9u · **-19.4%** (n=25) _(thin)_ |

| min move | margin≥0.30 + TOWARD | margin≥0.30 + AGAINST |
|---|---|---|
| ≥0.5% | 61-45 (58%) · -5.3u · **-5.0%** (n=106) | 35-37 (49%) · -9.4u · **-13.0%** (n=72) |
| ≥1.0% | 52-38 (58%) · -5.3u · **-5.9%** (n=90) | 29-31 (48%) · -8.2u · **-13.6%** (n=60) |
| ≥2.0% | 36-26 (58%) · -5.2u · **-8.3%** (n=62) | 13-20 (39%) · -9.4u · **-28.4%** (n=33) _(thin)_ |
| ≥3.0% | 22-18 (55%) · -5.9u · **-14.7%** (n=40) | 8-10 (44%) · -3.3u · **-18.5%** (n=18) _(thin)_ |

## Does the best cell beat the search itself?

- cells at n≥40: **51**
- best: `bvp>=0.25` at **+13.3%** (n=43)
- median best-in-noise: **+13.5%**
- 95th percentile in noise: **+26.6%**
- **corrected p = 0.509**

**Does not clear.** A grid this size produces a cell this good from noise more than 5% of the time.

- in-sample: 19-11 (63%) · +4.1u · **+13.6%** (n=30) _(thin)_
- holdout: 8-5 (62%) · +1.6u · **+12.5%** (n=13) _(thin)_

## Scored against the pre-registered bar

| requirement | met |
|---|---|
| n >= 100 (n=43) | ❌ |
| margin plateau above baseline (longest=1) | ❌ |
| corrected p <= 0.05 (p=0.509) | ❌ |
| holdout positive (+12.5%, n=13) | ✅ |
| beats the back-advantage baseline of -5.9% | ✅ |

**NOT promotable.** Recorded, not shipped.
