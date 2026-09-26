# Action Network scoreboard JSON — does it carry real handle?

`https://api.actionnetwork.com/web/v1/scoreboard/mlb`

_Confirming shape before writing any parser. The hunt scored this source **0** on "split pairs" and flagged covers matchups instead — both artefacts of the test: the pair test needs literal `%` characters and JSON stores bare numbers, while covers passed on 22 pairs that were all (50, 50) across 5 teams._

- HTTP **200**
- top-level keys: `league, games, content_live_count`
- games in the payload: **15**

- objects carrying a money-ish key: **12**

## Every object carrying a money-ish key

_The first pass printed only the first of these, which hid whatever the other eleven were._

| path | money keys and values |
|---|---|
| `games[0]` | `{"num_bets": 3352}` |
| `games[0].odds[0]` | `{"ml_away_money": null, "ml_home_money": null, "num_bets": null}` |
| `games[0].odds[1]` | `{"ml_away_money": null, "ml_home_money": null, "num_bets": null}` |
| `games[0].odds[2]` | `{"ml_away_money": null, "ml_home_money": null, "num_bets": null}` |
| `games[1]` | `{"num_bets": 4038}` |
| `games[1].odds[0]` | `{"ml_away_money": null, "ml_home_money": null, "num_bets": null}` |
| `games[1].odds[1]` | `{"ml_away_money": null, "ml_home_money": null, "num_bets": null}` |
| `games[1].odds[2]` | `{"ml_away_money": null, "ml_home_money": null, "num_bets": null}` |
| `games[2]` | `{"num_bets": 3317}` |
| `games[2].odds[0]` | `{"ml_away_money": null, "ml_home_money": null, "num_bets": null}` |
| `games[2].odds[1]` | `{"ml_away_money": null, "ml_home_money": null, "num_bets": null}` |
| `games[2].odds[2]` | `{"ml_away_money": null, "ml_home_money": null, "num_bets": null}` |

## Does it behave like a split?

- away/home money pairs found: **0**
- games with two named teams: **15**

## Other request shapes

| variant | status | bytes | has ml_*_money | has 'value' bets |
|---|---|---|---|---|
| v1 scoreboard | 200 | 449,319 | **yes** | no |
| v1 + periods/props | 400 | 113 | no | no |
| v1 + date | 200 | 449,319 | **yes** | no |
| v2 public betting | 200 | 470,065 | no | yes |
| v2 public betting + date | 200 | 470,065 | no | yes |

_A variant answering **yes** in the ml_*_money column is the call to build against._

## Inside v2's `bet_info`

- top-level keys: `league, games, market_rules, content_live_count`
- games: **15**

_First game's keys:_

```
id, league_id, status, real_status, status_display, start_time, away_team_id, home_team_id, winning_team_id, league_name, type, season, week, attendance, coverage, is_free, trending, away_rotation_number, home_rotation_number, teams, meta, num_bets, core_id, boxscore, player_stats, broadcast
```

_This game has no `bet_info`; the key may sit elsewhere or only on games with action._

_Keys exist but do not resolve into per-game away/home pairs here; the parser would need the sub-object that does._

## Before this is wired in

- a second run on a different day, to show the path is stable rather than a one-off
- team-name mapping to ours, since a source we cannot match to a game is a source we cannot use
- it joins as a THIRD handle source; changing `analysis`'s unanimity rule to a majority vote is a separate change that needs its own backtest
