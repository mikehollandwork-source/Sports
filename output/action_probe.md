# Action Network scoreboard JSON — does it carry real handle?

`https://api.actionnetwork.com/web/v1/scoreboard/mlb`

_Confirming shape before writing any parser. The hunt scored this source **0** on "split pairs" and flagged covers matchups instead — both artefacts of the test: the pair test needs literal `%` characters and JSON stores bare numbers, while covers passed on 22 pairs that were all (50, 50) across 5 teams._

- HTTP **200**
- top-level keys: `league, games, content_live_count`
- games in the payload: **15**

- objects carrying a money-ish key: **12**

## Where the numbers sit

- first at `games[0]`

_That object's keys:_

```
id, league_id, status, real_status, status_display, start_time, away_team_id, home_team_id, winning_team_id, league_name, type, season, week, attendance, coverage, is_free, trending, away_rotation_number, home_rotation_number, teams, meta, num_bets, boxscore, odds
```

_Its money-ish values:_

```
{
 "num_bets": 3352
}
```

## Does it behave like a split?

- away/home money pairs found: **0**
- games with two named teams: **15**

_Keys exist but do not resolve into per-game away/home pairs here; the parser would need the sub-object that does._

## Before this is wired in

- a second run on a different day, to show the path is stable rather than a one-off
- team-name mapping to ours, since a source we cannot match to a game is a source we cannot use
- it joins as a THIRD handle source; changing `analysis`'s unanimity rule to a majority vote is a separate change that needs its own backtest
