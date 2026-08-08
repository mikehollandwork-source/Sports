# League probe — WNBA

_Asks the venues what the teams are, rather than checking a table written from memory. A hand-written guess that gets 'verified' by a check built to agree with it is not verified._

- Kalshi series `KXWNBAGAME` · Polymarket tag `wnba` · Odds API `basketball_wnba`

## Kalshi

- open markets: **20** · settled: **200**
- distinct abbreviations: **17**

_sample tickers:_

- `KXWNBAGAME-26AUG10CHISEA-SEA`
- `KXWNBAGAME-26AUG10CHISEA-CHI`
- `KXWNBAGAME-26AUG10TORATL-TOR`
- `KXWNBAGAME-26AUG10TORATL-ATL`

- abbreviations: `ATL`, `CHI`, `CONN`, `COO`, `DAL`, `GS`, `IND`, `LA`, `LV`, `MIN`, `NY`, `PDX`, `PHX`, `SEA`, `SPN`, `TOR`, `WSH`

_Ticker time format: carries HHMM (start time available from the ticker)._

## The Odds API

- distinct team names in listed events: **8**

_sample events:_

- Golden State Valkyries @ Dallas Wings  (2026-08-08T01:41)
- Las Vegas Aces @ Minnesota Lynx  (2026-08-08T17:00)
- Indiana Fever @ Chicago Sky  (2026-08-08T19:30)
- Seattle Storm @ Portland Fire  (2026-08-09T00:30)

- names: Chicago Sky, Dallas Wings, Golden State Valkyries, Indiana Fever, Las Vegas Aces, Minnesota Lynx, Portland Fire, Seattle Storm

## Polymarket

- distinct outcome labels on two-sided markets: **20**
- game events exposing `startTime`: **39**

_sample game titles:_

- WNBA: 2026 Champion
- WNBA: 2026 MVP
- WNBA: 2026 Rookie of the Year
- WNBA: 2026 Defensive Player of the Year

- labels: `Yes`, `No`, `Over`, `Under`, `Las Vegas Aces`, `Connecticut Sun`, `Atlanta Dream`, `Washington Mystics`, `Indiana Fever`, `Phoenix Mercury`, `Dallas Wings`, `Minnesota Lynx`, `Chicago Sky`, `Golden State Valkyries`, `Los Angeles Sparks`, `Seattle Storm`, `New York Liberty`, `Toronto Tempo`, `Portland Fire`, `PortlandFire`

## Proposed mapping (abbr → name), built from the above

_Matched by nickname: the last word of the Odds API name against the Kalshi abbreviation and the Polymarket label. Anything unmatched is listed separately and needs a human eye._

- Kalshi abbreviations with no name match: **['ATL', 'CHI', 'CONN', 'COO', 'DAL', 'GS', 'IND', 'LA', 'LV', 'MIN', 'NY', 'PDX', 'PHX', 'SEA', 'SPN', 'TOR', 'WSH']**
- Odds API names with no abbreviation: **['Chicago Sky', 'Dallas Wings', 'Golden State Valkyries', 'Indiana Fever', 'Las Vegas Aces', 'Minnesota Lynx', 'Portland Fire', 'Seattle Storm']**

_Nickname matching is a starting point, not the answer — write the final table by hand from these lists, then let the probe confirm it._