# covers.com coverage by sport

_The consensus rule needs only two covers inputs - which side the TICKETS are on and whether the HANDLE agrees. It never uses the stat model to pick. So if these pages exist for another sport, the rule runs there unchanged._

_MLB is the control: if it fails here, the probe is at fault, not the sport._

## WNBA

- `consensus` — **no response** · `https://contests.covers.com/consensus/topconsensus/wnba/overall`
  - _no response (firewalled locally - meaningful only on a runner)_
- `odds` — **no response** · `https://www.covers.com/sport/basketball/wnba/odds`
  - _no response (firewalled locally - meaningful only on a runner)_

## NBA

- `consensus` — **no response** · `https://contests.covers.com/consensus/topconsensus/nba/overall`
  - _no response (firewalled locally - meaningful only on a runner)_
- `odds` — **no response** · `https://www.covers.com/sport/basketball/nba/odds`
  - _no response (firewalled locally - meaningful only on a runner)_

## NFL

- `consensus` — **no response** · `https://contests.covers.com/consensus/topconsensus/nfl/overall`
  - _no response (firewalled locally - meaningful only on a runner)_
- `odds` — **no response** · `https://www.covers.com/sport/football/nfl/odds`
  - _no response (firewalled locally - meaningful only on a runner)_

## MLB

- `consensus` — **no response** · `https://contests.covers.com/consensus/topconsensus/mlb/overall`
  - _no response (firewalled locally - meaningful only on a runner)_
- `odds` — **no response** · `https://www.covers.com/sport/baseball/mlb/odds`
  - _no response (firewalled locally - meaningful only on a runner)_

## Does our parser extract games?

_Reaching a page with a table is not the same as parsing it. This runs `covers.consensus()` - the exact function the live rule uses - against each sport's URL._

| sport | games parsed | sample |
|---|---|---|
| WNBA | **0** |  |
| NBA | **0** |  |
| NFL | **0** |  |
| MLB | **0** |  |

_MLB parsing while another sport returns zero means the markup differs there and the selectors need work - not that the sport is unavailable._

## VSiN handle splits

_covers gives tickets; VSiN gives dollars. The rule only fires when the two AGREE, so a sport without VSiN cannot run it at all._

| sport | rows parsed | sample |
|---|---|---|
| WNBA | **0** | `` |
| NBA | **0** | `` |
| NFL | **2** | `{'away_abbr': 'STL', 'home_abbr': 'SF', 'away_money': 57, 'home_money': 54, 'away_bets': 3` |
| MLB | **15** | `{'away_abbr': 'NYM', 'home_abbr': 'PIT', 'away_money': 55, 'home_money': 45, 'away_bets': ` |

_Zero rows for an in-season sport means the splits page differs there. Without handle, the consensus rule has nothing to agree with._

_A consensus page that redirects elsewhere, or returns a page with no percentage tokens, does not carry that sport - and would otherwise parse to an empty result that looks like 'no games'._