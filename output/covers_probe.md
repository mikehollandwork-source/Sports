# covers.com coverage by sport

_The consensus rule needs only two covers inputs - which side the TICKETS are on and whether the HANDLE agrees. It never uses the stat model to pick. So if these pages exist for another sport, the rule runs there unchanged._

_MLB is the control: if it fails here, the probe is at fault, not the sport._

## WNBA

- `consensus` — reached · `https://contests.covers.com/consensus/topconsensus/wnba/overall`
  - 292822 chars · **114 percentage tokens** · 1 tables · 4 rows
- `odds` — reached · `https://www.covers.com/sport/basketball/wnba/odds`
  - 958172 chars · **119 percentage tokens** · 5 tables · 44 rows

## NBA

- `consensus` — reached · `https://contests.covers.com/consensus/topconsensus/nba/overall`
  - 284608 chars · **108 percentage tokens** · 0 tables · 0 rows
- `odds` — reached · `https://www.covers.com/sport/basketball/nba/odds`
  - 841769 chars · **119 percentage tokens** · 22 tables · 236 rows

## NFL

- `consensus` — reached · `https://contests.covers.com/consensus/topconsensus/nfl/overall`
  - 290442 chars · **115 percentage tokens** · 0 tables · 0 rows
- `odds` — reached · `https://www.covers.com/sport/football/nfl/odds`
  - 2522935 chars · **119 percentage tokens** · 5 tables · 136 rows

## MLB

- `consensus` — reached · `https://contests.covers.com/consensus/topconsensus/mlb/overall`
  - 338486 chars · **148 percentage tokens** · 1 tables · 20 rows
- `odds` — reached · `https://www.covers.com/sport/baseball/mlb/odds`
  - 2829970 chars · **119 percentage tokens** · 5 tables · 168 rows

## Does our parser extract games?

_Reaching a page with a table is not the same as parsing it. This runs `covers.consensus()` - the exact function the live rule uses - against each sport's URL._

| sport | games parsed | sample |
|---|---|---|
| WNBA | **3** | `sea@pdx` → Sea 38.0% (None) / Pdx 62.0% (None) |
| NBA | **0** |  |
| NFL | **0** |  |
| MLB | **19** | `ath@bos` → Ath 27.0% (+220) / Bos 73.0% (-275) |

_MLB parsing while another sport returns zero means the markup differs there and the selectors need work - not that the sport is unavailable._

_A consensus page that redirects elsewhere, or returns a page with no percentage tokens, does not carry that sport - and would otherwise parse to an empty result that looks like 'no games'._