# NFL plumbing probe

_Everything here fails soft, so a broken NFL path looks identical to an empty schedule. This exercises it where the network is open._

## 1. ESPN team map

- name forms loaded: **0**
- distinct teams: **0** (expect 32)

**ESPN team list did not load — everything below is blocked.**

## 2. Schedule and kickoff times

- dates with games in the next 21: **0**

## 3. Kalshi vs ESPN abbreviations

- Kalshi abbreviations in open tickers: **32**
- ESPN abbreviations: **0**
- sample tickers: `KXNFLGAME-26AUG15DALSEA-SEA`, `KXNFLGAME-26AUG15DALSEA-DAL`, `KXNFLGAME-26AUG15PHIBAL-PHI`, `KXNFLGAME-26AUG15PHIBAL-BAL`, `KXNFLGAME-26AUG15LARKC-LAR`

- **in Kalshi but not ESPN: ['ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 'DAL', 'DEN', 'DET', 'GB', 'HOU', 'IND', 'JAC', 'KC', 'LAC', 'LAR', 'LV', 'MIA', 'MIN', 'NE', 'NO', 'NYG', 'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS']**
- in ESPN but not Kalshi: none

**These need alias entries.** Any team here has games that will never match, silently — the MLB equivalent of WAS/WSH and CHW/CWS. Off-season teams appearing only in the ESPN column are expected (not every team plays in a given window).

## 4. Polymarket NFL game markets

- matched game keys (both directions): **0** → ~**0** games

_No per-game markets matched. Either Polymarket has not listed NFL games yet, or the outcome labels do not resolve through `nfl_api.name_abbr` — check the sample titles in `sport_probe.md` before assuming the former._

_NFL stays `live=False` regardless of these results. This probe verifies the plumbing carries data, not that the rule works._