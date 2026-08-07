# Sport registry probe

_Verifying the Kalshi series and Polymarket tags in `sports.py` against the live endpoints. Only MLB's were previously confirmed; the rest are pattern guesses. An off-season sport showing zero OPEN markets is expected - settled markets persist, so those are the real test of whether a series name is right._

## MLB (`mlb`)  ✅

- Kalshi series `KXMLBGAME`: open **90**, settled **200**
  - sample_ticker: `KXMLBGAME-26AUG092020HOUSD-SD`
  - open_parsed_team: `90/90`
  - open_two_sided_events: `45/45`
  - settled_parsed_team: `200/200`
  - settled_two_sided_events: `100/100`
  - settled_with_volume: `200/200`
- Polymarket tag `mlb`: open events **20**
  - sample: _MLB World Series Champion 2026_

## NFL (`nfl`)  ✅

- Kalshi series `KXNFLGAME`: open **64**, settled **2**
  - sample_ticker: `KXNFLGAME-26AUG15DALSEA-SEA`
  - open_parsed_team: `64/64`
  - open_two_sided_events: `32/32`
  - settled_parsed_team: `2/2`
  - settled_two_sided_events: `1/1`
  - settled_with_volume: `2/2`
- Polymarket tag `nfl`: open events **20**
  - sample: _Tush Push banned for 2026 NFL Season?_

## NBA (`nba`)  ✅

- Kalshi series `KXNBAGAME`: open **0**, settled **20**
  - settled_parsed_team: `20/20`
  - settled_two_sided_events: `10/10`
  - settled_with_volume: `20/20`
- Polymarket tag `nba`: open events **20**
  - sample: _Will LeBron James retire before next NBA season?_

## NHL (`nhl`)  ✅

- Kalshi series `KXNHLGAME`: open **0**, settled **22**
  - settled_parsed_team: `22/22`
  - settled_two_sided_events: `11/11`
  - settled_with_volume: `22/22`
- Polymarket tag `nhl`: open events **4**
  - sample: _NHL: 2027 Champion_

_A sport is only safe to build on once its settled-market count is non-zero AND tickers parse into two-sided events, because that is what every downstream module assumes._