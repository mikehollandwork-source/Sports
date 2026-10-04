# Pitch-type split probe — 2026

_Does the idea have data under it? Checked before anything is built on it._

## Gavin Sheets (hitting, id 657757)

**Nothing returned.** The endpoint does not serve pitch-type splits for this group, so this half of the idea is dead.

## Logan Henderson (pitching, id 701656)

**Nothing returned.** The endpoint does not serve pitch-type splits for this group, so this half of the idea is dead.

## Alternative endpoints

_statSplits serves vr/vl fine, so it is the pitch-type CODES that are unpopulated. These are the documented alternatives._

- `pitchArsenal` (hitting): **12 split(s)**, fields: averageSpeed, count, percentage, totalPitches, type
- `pitchLog` (hitting): **1811 split(s)**, fields: play
- `playLog` (hitting): **421 split(s)**, fields: play
- `hotColdZones` (hitting): **5 split(s)**, fields: name, zones
- `sabermetrics` (hitting): **1 split(s)**, fields: baseRunning, batting, fielding, positional, rar, replacement, spd, ubr, wGdp, wLeague, wRaa, wRc, wRcPlus, wSb
- `pitchArsenal` (pitching): **4 split(s)**, fields: averageSpeed, count, percentage, totalPitches, type
- `pitchLog` (pitching): **1505 split(s)**, fields: play
- `playLog` (pitching): **372 split(s)**, fields: play
- `hotColdZones` (pitching): **7 split(s)**, fields: name, zones
- `sabermetrics` (pitching): **1 split(s)**, fields: eraMinus, exli, fip, fipMinus, gmli, inli, md, pli, ra9War, rar, sd, war, xfip

## Pitch-level records

_The real test: does a per-pitch record carry the pitch type AND the outcome? If yes, HR-by-pitch-type is computable directly._

### Gavin Sheets (hitting)

**arsenal (hitting)** — 12 type(s)
  - Four-seam FB: 0.3097736  (n=561, 95.3188586292333 mph)
  - Changeup: 0.14411928  (n=261, 87.1966779386973 mph)
  - Sinker: 0.13914964  (n=252, 94.16329760714285 mph)
  - Slider: 0.1198233  (n=217, 85.88436524423963 mph)
  - Curveball: 0.08448371  (n=153, 80.78189751633991 mph)
  - Cutter: 0.06957482  (n=126, 90.05896902380951 mph)
  - Sweeper: 0.06460519  (n=117, 83.34640433333337 mph)
  - Splitter: 0.041965764  (n=76, 87.88354425000004 mph)
  - Knuckle Curve: 0.017669795  (n=32, 80.3648658125 mph)
  - Slurve: 0.0060739922  (n=11, 81.40908818181816 mph)
  - Eephus Pitch: 0.0016565433  (n=3, 53.236671666666666 mph)
  - Forkball: 0.0011043622  (n=2, 82.110359 mph)
**playLog (hitting)** — 421 record(s)
one record, keys only:
```
{
 "season": "2026",
 "stat": {
  "play": {
   "details": {
    "call": {
     "code": "X",
     "description": "Hit Into Play - Out(s)"
    },
    "description": "Gavin Sheets grounds out, shortstop Javier B\u00e1ez to first baseman Spencer Torkelson. ",
    "event": "field_out",
    "eventType": "field_out",
    "isInPlay": true,
    "isStrike": false,
    "isBall": false,
    "isBaseHit": false,
    "isAtBat": true,
    "isPlateAppearance": true,
    "type": {
     "code": "SI",
     "description": "Sinker"
    },
    "batSide": {
     "code": "L",
     "description": "Left"
    },
    "pitchHand": {
     "code": "L",
     "description": "Left"
    }
   },
   "count": {
    "balls": 0,
    "strikes": 0,
    "outs": 0,
    "inning": 2,
    "isTopInning": false,
    "runnerOn1b": false,
    "runnerOn2b": false,
    "runnerOn3b": false
   },
   "playId": "00652e98-d20e-3508-ace7-3aa86c87fcd1",
   "pitchNumber": 1,
   "atBatNumber": 19,
   "isPitch": true
  }
 },
 "team": {
  "id": 135,
  "name": "San Diego Padres",
  "link": "/api/v1/teams/135"
 },
 "player": {
  "id": 657757,
  "fullName": "Gavin Sheets",
  "link": "/api/v1/people/657757"
 },
 "opponent": {
  "id": 116,
  "name": "Detroit Tigers",
  "link": "/api/v1/teams/116"
 },
 "date": "2026-03-26",
 "gameType": "R",
 "isHome": true,
 "pitcher": {
  "id": 669373,
  "fullName": "Tarik Skubal",
  "link": "/api/v1/people/669373"
 },
 "batter": {
  "id": 657757,
  "fullName": "Gavin Sheets",
  "link": "/api/v1/people/657757"
 },
 "game": {
  "gamePk": 823325,
  "link": "/api/v1.1/game/823325/feed/live",
  "content": {
   "link": "/api/v1/game/823325/content"
  },
  "gameNumber": 1,
  "dayNight": "day"
 }
}
```
**home-run records found: 0**

### Logan Henderson (pitching)

**arsenal (pitching)** — 4 type(s)
  - Four-seam FB: 0.46378738  (n=698, 93.13397745845278 mph)
  - Changeup: 0.35215947  (n=530, 82.93357349056592 mph)
  - Cutter: 0.15282393  (n=230, 87.83720650869564 mph)
  - Sweeper: 0.031229235  (n=47, 81.07943936170211 mph)
**playLog (pitching)** — 372 record(s)
one record, keys only:
```
{
 "season": "2026",
 "stat": {
  "play": {
   "details": {
    "call": {
     "code": "D",
     "description": "Hit Into Play - No Out(s)"
    },
    "description": "Maikel Garcia singles on a line drive to center fielder Garrett Mitchell. ",
    "event": "single",
    "eventType": "single",
    "isInPlay": true,
    "isStrike": false,
    "isBall": false,
    "isBaseHit": true,
    "isAtBat": true,
    "isPlateAppearance": true,
    "type": {
     "code": "FF",
     "description": "Four-seam FB"
    },
    "batSide": {
     "code": "R",
     "description": "Right"
    },
    "pitchHand": {
     "code": "R",
     "description": "Right"
    }
   },
   "count": {
    "balls": 1,
    "strikes": 0,
    "outs": 0,
    "inning": 1,
    "isTopInning": false,
    "runnerOn1b": false,
    "runnerOn2b": false,
    "runnerOn3b": false
   },
   "playId": "33b99e1e-ce63-3c8c-a7f0-c4d0a65310bd",
   "pitchNumber": 2,
   "atBatNumber": 4,
   "isPitch": true
  }
 },
 "team": {
  "id": 158,
  "name": "Milwaukee Brewers",
  "link": "/api/v1/teams/158"
 },
 "player": {
  "id": 701656,
  "fullName": "Logan Henderson",
  "link": "/api/v1/people/701656"
 },
 "opponent": {
  "id": 118,
  "name": "Kansas City Royals",
  "link": "/api/v1/teams/118"
 },
 "date": "2026-04-04",
 "gameType": "R",
 "isHome": false,
 "pitcher": {
  "id": 701656,
  "fullName": "Logan Henderson",
  "link": "/api/v1/people/701656"
 },
 "batter": {
  "id": 672580,
  "fullName": "Maikel Garcia",
  "link": "/api/v1/people/672580"
 },
 "game": {
  "gamePk": 824134,
  "link": "/api/v1.1/game/824134/feed/live",
  "content": {
   "link": "/api/v1/game/824134/content"
  },
  "gameNumber": 2,
  "dayNight": "day"
 }
}
```
**home-run records found: 0**

## What to conclude

- both tables populated with PA and HR -> the matchup term is buildable, with heavy shrinkage for the per-type sample
- a pitcher's PA per type doubles as his USAGE mix, which is the other half of the calculation
- totals far above a season mean the codes OVERLAP and must not be summed naively
