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