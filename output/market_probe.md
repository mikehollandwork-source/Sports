# New-market probe — The Odds API

_Which keys return data, and which endpoint serves them. Credits are the constraint: the bulk endpoint bills once for the whole slate, per-event bills per game._

- credits before: **403**

## Bulk endpoint (`/odds` — BASE already carries the sport)

_Bills one credit per market per region for the ENTIRE slate._

- `totals`: **2** games, 2 with the market · e.g. `[{"name": "Over", "price": 114, "point": 6.5}, {"name": "Under", "price": -140, "point": 6.5}]`
- `h2h`: **2** games, 2 with the market · e.g. `[{"name": "Los Angeles Dodgers", "price": -104}, {"name": "Milwaukee Brewers", "price": -112}]`
- `spreads`: **2** games, 2 with the market · e.g. `[{"name": "Los Angeles Dodgers", "price": 180, "point": -1.5}, {"name": "Milwaukee Brewers", "price": -220, "point": 1.5}]`

## Per-event keys (one game: Los Angeles Dodgers @ Milwaukee Brewers)

- `pitcher_strikeouts`: **4** outcome(s) · e.g. `[{"name": "Over", "description": "Jacob Misiorowski", "price": 108, "point": 7.5}, {"name": "Under", "description": "Jacob Misiorowski", "price": -138, "point": 7.5}]`
- `pitcher_strikeouts_alternate`: **14** outcome(s) · e.g. `[{"name": "Over", "description": "Tarik Skubal", "price": -4000, "point": 3.5}, {"name": "Over", "description": "Tarik Skubal", "price": -1100, "point": 4.5}]`
- `totals_1st_5_innings`: **2** outcome(s) · e.g. `[{"name": "Over", "price": 122, "point": 3.5}, {"name": "Under", "price": -160, "point": 3.5}]`
- `h2h_1st_5_innings`: **2** outcome(s) · e.g. `[{"name": "Los Angeles Dodgers", "price": -106}, {"name": "Milwaukee Brewers", "price": -118}]`
- `spreads_1st_5_innings`: **2** outcome(s) · e.g. `[{"name": "Los Angeles Dodgers", "price": -170, "point": 0.5}, {"name": "Milwaukee Brewers", "price": 130, "point": -0.5}]`
- `batter_total_bases`: **34** outcome(s) · e.g. `[{"name": "Over", "description": "Luis Lara", "price": -105, "point": 0.5}, {"name": "Under", "description": "Luis Lara", "price": -125, "point": 0.5}]`

- credits after: **394**
- **this probe cost 9 credit(s)**

## What it decides

- a key that returns outcomes on the BULK endpoint can be logged for every game at ~1 credit a day
- a key that only works per event costs one credit per game, so it can only cover the games we bet, not the slate
- a key that is not served at all is simply off the table
