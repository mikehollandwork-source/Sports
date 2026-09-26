# Probe: is there a third handle (money %) source?

_Probe only. Fetches candidates and reports what is there; parses nothing into the board and changes no rule._

## Why

Gate 1 needs the dollars to agree with the tickets. There are two handle sources and they must agree UNANIMOUSLY, so one disagreement is fatal. Over 1,201 board games that costs **20.4%** of the slate — 15.3% "sources split" plus 5.1% with no handle at all — and the rate is rising: 16% June, 18% July, 19% August, **25% September**.

## VSIN, by sportsbook (same parser we already use)

| candidate | status | bytes | rows parsed | tables | % tokens |
|---|---|---|---|---|---|
| vsin:dk (current) | ok | 361,200 | **1** | 1 | 201 |
| ↳ sample | `NYM` money 52 / `WSH` money 48 | | | | |
| vsin:circa | ok | 361,181 | **1** | 1 | 201 |
| ↳ sample | `NYM` money 52 / `WSH` money 48 | | | | |
| vsin:southpoint | ok | 361,168 | **1** | 1 | 201 |
| ↳ sample | `NYM` money 52 / `WSH` money 48 | | | | |
| vsin:betmgm | ok | 361,166 | **1** | 1 | 201 |
| ↳ sample | `NYM` money 52 / `WSH` money 48 | | | | |
| vsin:fanduel | ok | 361,181 | **1** | 1 | 201 |
| ↳ sample | `NYM` money 52 / `WSH` money 48 | | | | |
| vsin:caesars | ok | 361,198 | **1** | 1 | 201 |
| ↳ sample | `NYM` money 52 / `WSH` money 48 | | | | |

## Why the VSIN parser finds so few games

| measure | count |
|---|---|
| text tokens on the page | 746 |
| tokens recognised as a team | **2** |
| distinct teams recognised | 2 |
| moneyline price tokens | **2** |
| percent tokens the parser's regex accepts | 12 |
| rows the parser returns | **1** |

_A slate has ~13 games, so ~26 team tokens and ~26 ML prices are expected. Team tokens far below that means `_name_abbr` is not matching the page's team spelling; ML tokens far below it means the price format changed. Both are one-line fixes once seen - guessing which, without looking, is how the covers parsers rotted._

### First team-like tokens, as the page writes them

```
New York Mets, Washington Nationals
```

### First 40 tokens verbatim

```
VSiN - Betting Spl | Sign in | Join | My Account | Log Out | Sports | NFL | Today’s NFL Games | Vegas NFL Odds | NFL Live Odds | NFL Prop Analyzer | Opta AI Player Pro | NFL Injury Report | WR/CB Matchup Tool | Team Bets Analyzer | NFL Referee Analyz | Daily Matchup Rati | Makinen NFL Power  | NFL Betting Strate | VSiN Football Arti | NFL Draft | Super Bowl LX | College Football | Today’s CFB Games | Vegas CFB Odds | CFB Matchup Rating | Makinen CFB Power  | CFB Injury Report | Team Bets Analyzer | VSiN Football Arti | 2025 NFL Draft | NBA | Today’s NBA Games | Vegas NBA Odds | Live NBA Odds | Opta AI NBA Prop P | NBA Injury Report | Daily Matchup Rati | Makinen NBA Power  | NBA Prop Bet Analy
```

### Where the numbers actually live

- `<script>` tags: **60**
- scripts mentioning handle/bets/team names: **0**

_No script carries the numbers either - the page may fetch them from a separate endpoint, which the browser network tab would name._


_A view that parses rows with the EXISTING parser is the cheapest third source available: no new selectors, no new decay surface. Note the redirect check — several book views may serve the same default page, which would look like a new source while being the same numbers._

## Other free pages carrying a money column

| candidate | status | bytes | tables | % tokens | says handle | says bets |
|---|---|---|---|---|---|---|
| oddstrader | **fetch failed / blocked** | — | — | — | — | — |
| sbr-consensus | ok | 853,617 | 0 | 182 | no | no |
| covers-consensus | **fetch failed / blocked** | — | — | — | — | — |
| wagertalk | **fetch failed / blocked** | — | — | — | — | — |

_A page with a handle word, a table and plenty of percent tokens is worth writing a parser for. One that fetches but shows no percentages is almost certainly rendered client-side and not scrapeable this way._

## What this does NOT do

- it does not add a source to the board
- it does not change the unanimity rule in `analysis` — turning that into a majority vote would change which games pass gate 1, which is a rule change and needs a backtest, not a probe
