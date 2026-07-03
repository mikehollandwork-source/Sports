# Travel/schedule fatigue calibration — 2026-03-04 → 2026-07-02 (120 days)

**1296 games.**

## Road-trip depth, home-field controlled (the decisive cut)
AWAY games only — win rate by the away team's road_streak. A decline across bands = real incremental fatigue; flat = just ordinary away disadvantage. (Away baseline ≈ 47%.)

| away team's road_streak | away games | win rate |
|---|---|---|
| 1-2 | 438 | 49% |
| 3-5 | 574 | 46% |
| 6-8 | 250 | 48% |
| 9-+ | 34 | 35% |

## Head-to-head — the MORE-fatigued team's win rate (want < 50%)

| signal | games | tired team won |
|---|---|---|
| road_streak (deeper trip) | 1296 | 47% |
| days_straight (less rest) | 659 | 50% |
| games_last7 (denser) | 458 | 50% |
| tz_east (traveled east) | 375 | 53% |
| travel_mi (farther) | 375 | 52% |

## Buckets — the fatigued side's win rate

| condition | games | win rate |
|---|---|---|
| 6+ straight road games | 284 | 47% |
| 9+ straight road games | 34 | 35% |
| 3+ games in a row (no off day) | 1847 | 50% |
| 6+ games in last 7 days | 2174 | 50% |
| crossed 1+ time zone EAST | 86 | 49% |
| crossed 2+ time zones EAST | 39 | 54% |
| 1500+ mile trip in | 100 | 55% |

## ROI vs the CLOSING moneyline — fade the road team (bet home)
Betting the home team at its ESPN closing price, by the away team's road_streak. Baseline (bet every home team): **-4.4% ROI** over 1304/1304 priced games. If fatigue is a real *market* edge, ROI should climb with trip depth.

| away team's road_streak | bets | home win | ROI |
|---|---|---|---|
| 1-2 | 442 | 51% | -7.1% |
| 3-5 | 578 | 54% | -2.4% |
| 6-8 | 250 | 52% | -6.9% |
| 9-+ | 34 | 65% | +17.4% |

_ROI = units per $1. Around −4-5% is the no-edge / vig baseline; a band clearly ABOVE baseline (toward 0 or positive) that grows with depth is a real, priceable fatigue edge worth betting._

_Point-in-time, no lookahead. Win-rate cuts above are the raw signal; the ROI table is the money test against the closing line._