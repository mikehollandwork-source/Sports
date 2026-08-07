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

_NFL stays `live=False` regardless of these results. This probe verifies the plumbing carries data, not that the rule works._