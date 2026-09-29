# NFL plumbing probe

_Everything here fails soft, so a broken NFL path looks identical to an empty schedule. This exercises it where the network is open._

## 1. Team table

- name forms loaded: **32**
- distinct teams: **32** (expect 32)

| probe string | resolves to |
|---|---|
| `Seattle Seahawks` | `SEA` |
| `Seahawks` | `SEA` |
| `Dallas Cowboys` | `DAL` |
| `Kansas City Chiefs` | `KC` |
| `Washington Commanders` | `WAS` |
| `Los Angeles Rams` | `LAR` |
| `Los Angeles Chargers` | `LAC` |
| `Jacksonville Jaguars` | `JAC` |
| `Tush Push banned for 2026 NFL Season?` | `None` |

## 1b. Odds API football sport keys

- exposed: `americanfootball_cfl`, `americanfootball_ncaaf`, `americanfootball_ncaaf_championship_winner`, `americanfootball_nfl`, `americanfootball_nfl_super_bowl_winner`
- we query: `americanfootball_nfl`

## 2. Schedule and kickoff times

- dates with games in the next 21: **0**

## 3. Kalshi vs our table's abbreviations

- Kalshi abbreviations in open tickers: **32**
- our table's abbreviations: **32**
- sample tickers: `KXNFLGAME-26AUG15DALSEA-SEA`, `KXNFLGAME-26AUG15DALSEA-DAL`, `KXNFLGAME-26AUG15PHIBAL-PHI`, `KXNFLGAME-26AUG15PHIBAL-BAL`, `KXNFLGAME-26AUG15LARKC-LAR`

- **in Kalshi but not our table: none**
- in our table but not Kalshi: none

_No Kalshi-side mismatches: every abbreviation Kalshi uses is in our table, so no alias entries are needed._

## 4. Polymarket NFL game markets

- matched game keys (both directions): **130** → ~**65** games

| pair |
|---|
| `CAR` vs `ARI` |
| `ARI` vs `CAR` |
| `CAR` vs `BUF` |
| `BUF` vs `CAR` |
| `PHI` vs `BAL` |
| `BAL` vs `PHI` |

## 5. Kickoff from Polymarket (fallback source)

_The odds API has no preseason coverage, so this checks whether gamma events carry a usable start time for games it cannot see._

_sample GAME event: Panthers vs. Cardinals_

| field | value |
|---|---|
| `startDate` | `2026-07-09T12:03:01.935741Z` |
| `creationDate` | `2026-08-07T00:00:00Z` |
| `endDate` | `2026-08-07T00:00:00Z` |
| `updatedAt` | `2026-08-07T06:10:41.619674Z` |
| `eventDate` | `2026-08-06` |
| `startTime` | `2026-08-07T00:00:00Z` |
| `ended` | `True` |
| `finishedTimestamp` | `2026-08-07T03:05:43.088393Z` |


- **kickoffs recovered from Polymarket: 65 games**

| teams | kickoff (UTC) | ended |
|---|---|---|
| ARI vs CAR | 2026-08-07T00:00:00Z | True |
| BUF vs CAR | 2026-08-15T17:00:00Z | False |
| BAL vs PHI | 2026-08-15T23:00:00Z | False |
| GB vs PIT | 2026-08-13T23:00:00Z | False |
| CIN vs DET | 2026-08-13T23:00:00Z | False |
| HOU vs LAC | 2026-08-14T00:00:00Z | False |

_NFL stays `live=False` regardless of these results. This probe verifies the plumbing carries data, not that the rule works._