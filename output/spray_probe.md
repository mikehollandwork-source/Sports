# Spray / park-dimension probe

## 1. Does a play record carry batted-ball data?

playLog splits: 421
balls in play: 280

keys on a ball-in-play `play`:
```
atBatNumber, count, details, isPitch, pitchNumber, playId
```
**hitData ABSENT** — no distance or coordinates, so spray cannot be computed from here

## 2. Does the venue endpoint serve fence distances?

venues returned: 62
with fieldInfo: 62

example:
```
{
 "id": 1,
 "name": "Angel Stadium",
 "fieldInfo": {
  "capacity": 45517,
  "turfType": "Grass",
  "roofType": "Open",
  "leftLine": 330,
  "left": 347,
  "leftCenter": 389,
  "center": 396,
  "rightCenter": 365,
  "right": 348,
  "rightLine": 330
 }
}
```
fieldInfo keys across all venues:
```
capacity, center, left, leftCenter, leftLine, right, rightCenter, rightLine, roofType, turfType
```
direction distances populated league-wide: ['leftLine', 'left', 'leftCenter', 'center', 'rightCenter', 'rightLine']

## 3. Can home runs be tied to a ballpark?

gamelog games: 127
split keys:
```
date, game, gameType, isHome, isWin, league, opponent, player, positionsPlayed, season, sport, stat, team
```
`game` keys:
```
content, dayNight, gameNumber, gamePk, link
```
_a venue here would make it a one-line join; otherwise it needs the schedule, which the board already fetches._
games with a HR: 16 — so 'has he gone deep at THIS park' is at most a handful per venue, which is the real constraint

## 4. Is Statcast (baseballsavant) reachable, and useful?

_MLB's own feed carries no hitData, so spray and distance can only come from here. Checked for reachability AND for the fields that matter, since a 200 that returns a login page is still a dead end._

**batted-ball leaderboard** — HTTP 200, 29862 bytes, content-type `text/csv; charset=utf-8`
  - 246 data rows, 19 columns
  - relevant columns: `avg_hit_angle`, `anglesweetspotpercent`, `max_distance`, `avg_distance`, `avg_hr_distance`, `ev95percent`, `barrels`, `brl_percent`
**expected stats leaderboard** — HTTP 200, 35030 bytes, content-type `text/csv; charset=utf-8`
  - 246 data rows, 15 columns
  - relevant columns: **none**
**per-batted-ball search** — HTTP 200, 1361832 bytes, content-type `application/download; charset=utf-8`
  - 2026 data rows, 119 columns
  - relevant columns: `break_angle_deprecated`, `hc_x`, `hc_y`, `hit_distance_sc`, `launch_speed`, `launch_angle`, `estimated_ba_using_speedangle`, `estimated_woba_using_speedangle`, `launch_speed_angle`, `miss_distance`, `estimated_slg_using_speedangle`, `arm_angle`, `attack_angle`