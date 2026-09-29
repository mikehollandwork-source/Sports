# Is the Polymarket drift signal real, or is it reading the game?

_`signal_sweep` returned backing Polymarket drift at +10.5%, corrected p = 0.006, split-half +8.6% / +12.2% — the first result this season to clear everything. `book_metrics` computes drift across the WHOLE day file with no time cut, and 37% of readings fall at or after first pitch, so that number may simply be the price moving during the game._

- games: **962**

- readings per game: **87.3** in the whole file, **63.3** before the freeze (**28%** discarded)

## The same signal, computed two ways

| drift measured | backing the side it points at |
|---|---|
| whole day file (what the backtest did) | 501-339 · **+11.6%** (n=840) |
| **pre-game only** (before first pitch − 15 min) | 382-363 · **-5.8%** (n=745) |

_On the identical subset of games, so the difference is the measurement and not the sample:_

| drift measured | same games |
|---|---|
| whole day file | 422-292 · **+9.9%** (n=714) |
| pre-game only | 370-344 · **-5.0%** (n=714) |

- the two measures point at the SAME side in **602/714** (84%) of games

## Does the pre-game version stand on its own?

- pre-game drift: **-5.0%** (n=714)
- market-calibrated null: median -2.2%, 95th +3.8%
- **p = 0.779** (single test, no grid to correct — this was specified before looking)

- split-half: 185-178 · **-6.7%** (n=363) against 185-166 · **-3.2%** (n=351)

## What follows either way

- **if the pre-game version holds**, it is the find of the season and a candidate signal in its own right
- **if it collapses**, the +10.5% was circular, and the same contamination sits in every backtest that calls `book_metrics` on a completed day — including the ones used to validate the live rule's gates. Those would all need re-reading.
- the live RECORD is unaffected either way: those were real bets placed before first pitch, from a file that held only pre-game readings at the time.
