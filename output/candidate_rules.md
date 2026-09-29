# Candidate rules — 413 games over 32 days (5 holdout days)

_Every rule bets our stat side at the frozen price. The HOLDOUT column decides; in-sample is shown only to expose curve-fitting (a rule that looks great in-sample and dies in holdout is noise)._

| candidate | ALL | in-sample | HOLDOUT | bets/day |
|---|---|---|---|---|
| current live gate (baseline) | 77-48 (62%) · +8.3u · **+6.6%** (n=125) | 66-36 (65%) · +13.2u · **+12.9%** (n=102) | 11-12 (48%) · -4.9u · **-21.4%** (n=23) | 3.9 |
| A. margin ≥0.5 only (drop consistency path) | 39-24 (62%) · +3.6u · **+5.7%** (n=63) | 34-19 (64%) · +5.4u · **+10.1%** (n=53) | 5-5 (50%) · -1.8u · **-17.5%** (n=10) | 2.0 |
| B. margin ≥0.5 + fade gate | 33-14 (70%) · +8.8u · **+18.8%** (n=47) | 29-10 (74%) · +10.5u · **+26.9%** (n=39) | 4-4 (50%) · -1.6u · **-20.6%** (n=8) | 1.5 |
| C. margin ≥0.5 + no big dogs (ml ≤ +140) | 39-23 (63%) · +4.6u · **+7.4%** (n=62) | 34-18 (65%) · +6.4u · **+12.2%** (n=52) | 5-5 (50%) · -1.8u · **-17.5%** (n=10) | 1.9 |
| D. margin ≥0.5 + price window −180..+140 | 32-19 (63%) · +5.5u · **+10.8%** (n=51) | 28-15 (65%) · +6.5u · **+15.2%** (n=43) | 4-4 (50%) · -1.0u · **-12.8%** (n=8) | 1.6 |
| E. margin ≥0.5 + fade + price −180..+140 | 28-10 (74%) · +10.6u · **+28.0%** (n=38) | 25-7 (78%) · +11.5u · **+36.1%** (n=32) | 3-3 (50%) · -0.9u · **-15.2%** (n=6) | 1.2 |
| F. live gate + no big dogs | 77-48 (62%) · +8.3u · **+6.6%** (n=125) | 66-36 (65%) · +13.2u · **+12.9%** (n=102) | 11-12 (48%) · -4.9u · **-21.4%** (n=23) | 3.9 |
| G. live gate + margin required (no consistency-only) | 33-13 (72%) · +9.8u · **+21.4%** (n=46) | 29-9 (76%) · +11.5u · **+30.2%** (n=38) | 4-4 (50%) · -1.6u · **-20.6%** (n=8) | 1.4 |
| H. price window only, no stat gate (−160..+140) | 165-161 (51%) · -15.3u · **-4.7%** (n=326) | 140-138 (50%) · -15.0u · **-5.4%** (n=278) | 25-23 (52%) · -0.3u · **-0.6%** (n=48) | 10.2 |
| I. margin ≥0.4 + price −180..+140 | 48-38 (56%) · -0.7u · **-0.9%** (n=86) | 43-32 (57%) · +1.4u · **+1.9%** (n=75) | 5-6 (45%) · -2.1u · **-19.3%** (n=11) | 2.7 |

## Margin threshold sweep (inside price window −180..+140)

_A real edge shows a PLATEAU across neighbouring thresholds. A single spiking cell with dips either side is noise._

| margin ≥ | ALL | in-sample | HOLDOUT | bets/day |
|---|---|---|---|---|
| 0.3 | 66-64 (51%) · -12.1u · **-9.3%** (n=130) | 59-54 (52%) · -7.3u · **-6.5%** (n=113) | 7-10 (41%) · -4.7u · **-27.7%** (n=17) | 4.1 |
| 0.4 | 48-38 (56%) · -0.7u · **-0.9%** (n=86) | 43-32 (57%) · +1.4u · **+1.9%** (n=75) | 5-6 (45%) · -2.1u · **-19.3%** (n=11) | 2.7 |
| 0.5 | 32-19 (63%) · +5.5u · **+10.8%** (n=51) | 28-15 (65%) · +6.5u · **+15.2%** (n=43) | 4-4 (50%) · -1.0u · **-12.8%** (n=8) | 1.6 |
| 0.6 | 13-11 (54%) · -1.8u · **-7.7%** (n=24) | 13-8 (62%) · +1.2u · **+5.5%** (n=21) | 0-3 (0%) · -3.0u · **-100.0%** (n=3) | 0.8 |
| 0.7 | 3-8 (27%) · -5.8u · **-53.0%** (n=11) | 3-5 (38%) · -2.8u · **-35.4%** (n=8) | 0-3 (0%) · -3.0u · **-100.0%** (n=3) | 0.3 |

## The margin dead zone (0.2–0.4) — what the consistency path lets in

- as played: 57-70 (45%) · -24.3u · **-19.1%** (n=127)

_Multiple comparisons: 10 candidates × 3 windows are scanned here. Prefer a rule with a PLATEAU and a reason over the single best cell._