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

## What to conclude

- both tables populated with PA and HR -> the matchup term is buildable, with heavy shrinkage for the per-type sample
- a pitcher's PA per type doubles as his USAGE mix, which is the other half of the calculation
- totals far above a season mean the codes OVERLAP and must not be summed naively
