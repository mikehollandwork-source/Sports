# Probe: is there a third handle (money %) source?

_Probe only. Fetches candidates and reports what is there; parses nothing into the board and changes no rule._

## Why

Gate 1 needs the dollars to agree with the tickets. There are two handle sources and they must agree UNANIMOUSLY, so one disagreement is fatal. Over 1,201 board games that costs **20.4%** of the slate — 15.3% "sources split" plus 5.1% with no handle at all — and the rate is rising: 16% June, 18% July, 19% August, **25% September**.

## VSIN, by sportsbook (same parser we already use)

| candidate | status | bytes | rows parsed | tables | % tokens |
|---|---|---|---|---|---|
| vsin:dk (current) | ok | 361,181 | **1** | 1 | 201 |
| ↳ sample | `NYM` money 52 / `WSH` money 48 | | | | |
| vsin:circa | ok | 361,200 | **1** | 1 | 201 |
| ↳ sample | `NYM` money 52 / `WSH` money 48 | | | | |
| vsin:southpoint | ok | 361,181 | **1** | 1 | 201 |
| ↳ sample | `NYM` money 52 / `WSH` money 48 | | | | |
| vsin:betmgm | ok | 361,168 | **1** | 1 | 201 |
| ↳ sample | `NYM` money 52 / `WSH` money 48 | | | | |
| vsin:fanduel | ok | 361,198 | **1** | 1 | 201 |
| ↳ sample | `NYM` money 52 / `WSH` money 48 | | | | |
| vsin:caesars | ok | 361,183 | **1** | 1 | 201 |
| ↳ sample | `NYM` money 52 / `WSH` money 48 | | | | |

_A view that parses rows with the EXISTING parser is the cheapest third source available: no new selectors, no new decay surface. Note the redirect check — several book views may serve the same default page, which would look like a new source while being the same numbers._

## Other free pages carrying a money column

| candidate | status | bytes | tables | % tokens | says handle | says bets |
|---|---|---|---|---|---|---|
| oddstrader | **fetch failed / blocked** | — | — | — | — | — |
| sbr-consensus | ok | 850,820 | 0 | 182 | no | no |
| covers-consensus | **fetch failed / blocked** | — | — | — | — | — |
| wagertalk | **fetch failed / blocked** | — | — | — | — | — |

_A page with a handle word, a table and plenty of percent tokens is worth writing a parser for. One that fetches but shows no percentages is almost certainly rendered client-side and not scrapeable this way._

## What this does NOT do

- it does not add a source to the board
- it does not change the unanimity rule in `analysis` — turning that into a majority vote would change which games pass gate 1, which is a rule change and needs a backtest, not a probe
