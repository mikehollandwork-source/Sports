# Schedule & travel spots — road trips, rest, density

_Derived from 70 days of board history: every team's home/away sequence gives trip length, rest and density. Backward-looking, so knowable before first pitch. Teams are only included once observed at home, so no trip length is really "as far back as we can see"._

- usable graded games: **792**

## Baselines

| bet | result |
|---|---|
| back the home team, always | 418-374 (53%) · -30.6u · **-3.9%** (n=792) |
| back the road team, always | 374-418 (47%) · -21.8u · **-2.7%** (n=792) |

## Fading a team deep into a road trip

_Back the HOME side as the visitor's trip lengthens._

| visitor's consecutive road games | back home | back the road team |
|---|---|---|
| ≥3 | 280-270 (51%) · -43.4u · **-7.9%** (n=550) | 270-280 (49%) · +7.2u · **+1.3%** (n=550) |
| ≥4 | 208-214 (49%) · -47.1u · **-11.2%** (n=422) | 214-208 (51%) · +21.9u · **+5.2%** (n=422) |
| ≥5 | 151-165 (48%) · -46.1u · **-14.6%** (n=316) | 165-151 (52%) · +31.3u · **+9.9%** (n=316) |
| ≥6 | 95-112 (46%) · -36.9u · **-17.8%** (n=207) | 112-95 (54%) · +30.6u · **+14.8%** (n=207) |
| ≥7 | 46-52 (47%) · -17.2u · **-17.6%** (n=98) | 52-46 (53%) · +14.3u · **+14.6%** (n=98) |

## The specific spot: last game of a road trip

_Schedule lookahead only - the next listed game is at home. MLB schedules are published months ahead, so this is knowable pre-game._

| spot | back home | back the road team |
|---|---|---|
| any final road game | 58-61 (49%) · -14.1u · **-11.9%** (n=119) | 61-58 (51%) · +9.4u · **+7.9%** (n=119) |
| final game of a ≥4-game trip | 52-54 (49%) · -12.2u · **-11.5%** (n=106) | 54-52 (51%) · +8.9u · **+8.4%** (n=106) |
| final game of a ≥6-game trip | 51-53 (49%) · -11.8u · **-11.4%** (n=104) | 53-51 (51%) · +9.0u · **+8.6%** (n=104) |

## Rest

| spot | back home | back the road team |
|---|---|---|
| visitor on 0 days rest | 370-323 (53%) · -18.3u · **-2.6%** (n=693) | 323-370 (47%) · -29.1u · **-4.2%** (n=693) |
| home on 0 days rest | 368-322 (53%) · -16.4u · **-2.4%** (n=690) | 322-368 (47%) · -28.7u · **-4.2%** (n=690) |
| visitor rested, home not | 13-15 (46%) · -2.6u · **-9.4%** (n=28) _(thin)_ | 15-13 (54%) · +2.4u · **+8.4%** (n=28) _(thin)_ |
| home rested, visitor not | 15-16 (48%) · -4.6u · **-14.7%** (n=31) _(thin)_ | 16-15 (52%) · +2.0u · **+6.3%** (n=31) _(thin)_ |

## Schedule density (games in the last 7 days)

| spot | back home | back the road team |
|---|---|---|
| visitor played 6+ | 345-313 (52%) · -25.6u · **-3.9%** (n=658) | 313-345 (48%) · -13.1u · **-2.0%** (n=658) |
| visitor played 6+, home ≤5 | 18-15 (55%) · +1.1u · **+3.2%** (n=33) _(thin)_ | 15-18 (45%) · -1.9u · **-5.7%** (n=33) _(thin)_ |
| home played 6+ | 339-304 (53%) · -23.4u · **-3.6%** (n=643) | 304-339 (47%) · -16.3u · **-2.5%** (n=643) |

## Home team on a long homestand

| home's consecutive home games | back home | back the road team |
|---|---|---|
| ≥4 | 224-212 (51%) · -21.2u · **-4.9%** (n=436) | 212-224 (49%) · +8.3u · **+1.9%** (n=436) |
| ≥6 | 105-104 (50%) · -15.6u · **-7.5%** (n=209) | 104-105 (50%) · +14.1u · **+6.8%** (n=209) |

## Silencing the noise

- cells at n≥40: **30**
- best: `road>=6:away` at **+14.8%** (n=207)
- median best-in-noise: **+8.6%**
- 95th percentile in noise: **+20.0%**
- **corrected p = 0.160**

**Does not clear.** A grid this size produces a cell this good from noise more than 5% of the time, so the number is the search talking.

- in-sample: 42-26 (62%) · +19.7u · **+28.9%** (n=68)
- holdout: 70-69 (50%) · +10.9u · **+7.8%** (n=139)
