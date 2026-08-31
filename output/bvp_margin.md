# BvP and stat-edge margin — alone, combined, and against the line

- graded games with a price and a margin: **851**

## Baselines — the model betting itself

| what | result |
|---|---|
| back `advantage_team`, every game | 458-393 (54%) · -29.5u · **-3.5%** (n=851) |
| back the BvP `edge_team` | 402-395 (50%) · -41.4u · **-5.2%** (n=797) |
| back the bullpen-BvP `edge_team` | 392-361 (52%) · -4.0u · **-0.5%** (n=753) |

_This is the number the whole board rests on. Every cell below has to beat it, not merely beat zero._

## Margin alone (backing `advantage_team`)

| min margin | result |
|---|---|
| ≥0.00 | 458-393 (54%) · -29.5u · **-3.5%** (n=851) |
| ≥0.10 | 352-284 (55%) · -17.4u · **-2.7%** (n=636) |
| ≥0.20 | 239-212 (53%) · -38.9u · **-8.6%** (n=451) |
| ≥0.30 | 164-128 (56%) · -11.8u · **-4.0%** (n=292) |
| ≥0.50 | 62-35 (64%) · +6.2u · **+6.4%** (n=97) |

## BvP alone (backing the BvP `edge_team`)

| min gap | starter BvP | bullpen BvP |
|---|---|---|
| ≥0.00 | 402-395 (50%) · -41.4u · **-5.2%** (n=797) | 392-361 (52%) · -4.0u · **-0.5%** (n=753) |
| ≥0.04 | 278-290 (49%) · -48.2u · **-8.5%** (n=568) | 325-298 (52%) · -5.7u · **-0.9%** (n=623) |
| ≥0.08 | 199-194 (51%) · -23.3u · **-5.9%** (n=393) | 273-238 (53%) · +3.5u · **+0.7%** (n=511) |
| ≥0.14 | 101-93 (52%) · -7.4u · **-3.8%** (n=194) | 192-165 (54%) · +1.7u · **+0.5%** (n=357) |
| ≥0.25 | 32-18 (64%) · +8.3u · **+16.7%** (n=50) | 90-76 (54%) · +1.0u · **+0.6%** (n=166) |

_BvP flagged `meaningful`_: 231-252 (48%) · -52.3u · **-10.8%** (n=483)

## Combined — does BvP agree with the margin?

| case | backing `advantage_team` |
|---|---|
| BvP agrees | 243-211 (54%) · -22.2u · **-4.9%** (n=454) |
| BvP disagrees | 184-159 (54%) · -9.6u · **-2.8%** (n=343) |
| BvP disagrees — back the BvP side instead | 159-184 (46%) · -19.2u · **-5.6%** (n=343) |

### Agreement, swept on both thresholds

| min margin | gap ≥0.00 | gap ≥0.04 | gap ≥0.08 | gap ≥0.14 | gap ≥0.25 |
|---|---|---|---|---|---|
| ≥0.00 | 243-211 (54%) · -22.2u · **-4.9%** (n=454) | 173-157 (52%) · -23.7u · **-7.2%** (n=330) | 129-108 (54%) · -8.7u · **-3.7%** (n=237) | 62-52 (54%) · -4.3u · **-3.8%** (n=114) | 19-12 (61%) · +3.3u · **+10.5%** (n=31) _(thin)_ |
| ≥0.10 | 186-151 (55%) · -14.7u · **-4.4%** (n=337) | 139-119 (54%) · -16.6u · **-6.4%** (n=258) | 101-84 (55%) · -10.5u · **-5.7%** (n=185) | 47-40 (54%) · -5.4u · **-6.2%** (n=87) | 15-11 (58%) · -0.2u · **-0.9%** (n=26) _(thin)_ |
| ≥0.20 | 138-118 (54%) · -21.5u · **-8.4%** (n=256) | 102-95 (52%) · -24.0u · **-12.2%** (n=197) | 76-68 (53%) · -15.6u · **-10.8%** (n=144) | 36-33 (52%) · -8.6u · **-12.5%** (n=69) | 10-7 (59%) · -0.8u · **-4.6%** (n=17) _(thin)_ |
| ≥0.30 | 98-71 (58%) · -3.8u · **-2.2%** (n=169) | 72-61 (54%) · -12.1u · **-9.1%** (n=133) | 55-43 (56%) · -6.8u · **-6.9%** (n=98) | 25-17 (60%) · -0.5u · **-1.2%** (n=42) | 8-4 (67%) · +0.8u · **+6.8%** (n=12) _(thin)_ |
| ≥0.50 | 36-22 (62%) · +0.8u · **+1.5%** (n=58) | 29-19 (60%) · -1.9u · **-3.9%** (n=48) | 22-12 (65%) · +0.7u · **+1.9%** (n=34) _(thin)_ | 8-3 (73%) · +0.9u · **+8.3%** (n=11) _(thin)_ | 3-1 (75%) · +0.6u · **+14.0%** (n=4) _(thin)_ |

## Crossed with line movement

Both directions at every threshold, because choosing the direction after seeing the numbers turns a coin flip into a "finding".

| min move | agree + line TOWARD us | agree + line AGAINST us |
|---|---|---|
| ≥0.5% | 94-85 (53%) · -19.7u · **-11.0%** (n=179) | 89-87 (51%) · -11.8u · **-6.7%** (n=176) |
| ≥1.0% | 73-69 (51%) · -19.4u · **-13.7%** (n=142) | 62-61 (50%) · -7.5u · **-6.1%** (n=123) |
| ≥2.0% | 43-35 (55%) · -9.7u · **-12.5%** (n=78) | 33-35 (49%) · -4.5u · **-6.6%** (n=68) |
| ≥3.0% | 27-22 (55%) · -6.9u · **-14.0%** (n=49) | 17-17 (50%) · -0.1u · **-0.2%** (n=34) _(thin)_ |

| min move | margin≥0.30 + TOWARD | margin≥0.30 + AGAINST |
|---|---|---|
| ≥0.5% | 75-53 (59%) · -4.2u · **-3.3%** (n=128) | 60-48 (56%) · -1.5u · **-1.3%** (n=108) |
| ≥1.0% | 60-46 (57%) · -8.0u · **-7.6%** (n=106) | 41-36 (53%) · -4.4u · **-5.7%** (n=77) |
| ≥2.0% | 39-30 (57%) · -7.7u · **-11.1%** (n=69) | 21-22 (49%) · -5.6u · **-12.9%** (n=43) |
| ≥3.0% | 23-19 (55%) · -6.5u · **-15.5%** (n=42) | 13-11 (54%) · -0.9u · **-3.7%** (n=24) _(thin)_ |

## Does the best cell beat the search itself?

- cells at n≥40: **54**
- best: `bvp>=0.25` at **+16.7%** (n=50)
- median best-in-noise: **+13.4%**
- 95th percentile in noise: **+27.6%**
- **corrected p = 0.324**

**Does not clear.** A grid this size produces a cell this good from noise more than 5% of the time.

## The other tail — is anything reliably bad enough to invert?

- worst cell: `m30:tow>=0.03` at **-15.5%** (n=42)
- median worst-in-noise: **-19.8%**
- **corrected p = 0.744**
- backing the OTHER side of that cell instead: **19-23 (45%) · +6.4u · **+15.3%** (n=42)**

**Not invertible.** The worst of these cells is no more extreme than the worst a grid this size throws up by chance, so fading it is the same search one step removed - and the reversal still has to pay the vig on the other side.

- in-sample: 19-11 (63%) · +4.1u · **+13.6%** (n=30) _(thin)_
- holdout: 13-7 (65%) · +4.2u · **+21.2%** (n=20) _(thin)_

## Scored against the pre-registered bar

| requirement | met |
|---|---|
| n >= 100 (n=50) | ❌ |
| margin plateau above baseline (longest=1) | ❌ |
| corrected p <= 0.05 (p=0.324) | ❌ |
| holdout positive (+21.2%, n=20) | ✅ |
| beats the back-advantage baseline of -3.5% | ✅ |

**NOT promotable.** Recorded, not shipped.
