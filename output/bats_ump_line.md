# Hot bats, the umpire, and the line moving against

_The mechanism first: an umpire who calls few strikeouts leaves more balls in play, which is worth more to the side already hitting well. So an offence-friendly umpire should AMPLIFY a hitting edge rather than move the game evenly. Line-against supplies the discount._

- games with form, umpire and line all present: **934**

- umpire `k_extra` median: **-0.08** (strikeouts above or below expectation, so already relative)
- baseline, backing the hotter-hitting side in every game: 473-461 · **-2.8%** (n=934)
- baseline, backing the colder side: 461-473 · **-2.9%** (n=934)

## The 2×2×2

_Backing the HOTTER-hitting side. `offence-friendly ump` is `k_extra` below the median; `line against` is the price moving away from the hot side by ≥1%._

| umpire | line | backing the hot side |
|---|---|---|
| offence-friendly | moved against | 62-60 · **-0.3%** (n=122) |
| offence-friendly | not against | 171-157 · **-0.7%** (n=328) |
| strikeout-heavy | moved against | 79-76 · **+4.8%** (n=155) |
| strikeout-heavy | not against | 161-168 · **-9.2%** (n=329) |

## The counterpart, so only half the story is not tested

_If a low-strikeout umpire helps the hotter bats, a strikeout-heavy one should help the other side by the same logic. Backing the COLDER side here._

| umpire | line | backing the cold side |
|---|---|---|
| strikeout-heavy | moved against the hot side | 76-79 · **-8.8%** (n=155) |
| strikeout-heavy | not against | 168-161 · **+2.0%** (n=329) |
| offence-friendly | moved against the hot side | 60-62 · **-6.2%** (n=122) |
| offence-friendly | not against | 157-171 · **-3.9%** (n=328) |

## Does a bigger hitting edge help more?

_Offence-friendly umpire and line-against only, split by the size of the form gap._

| form gap | backing the hot side |
|---|---|
| gap ≥ 0.032 (bigger) | 36-25 · **+12.7%** (n=61) |
| gap < 0.032 (smaller) | 26-35 · **-13.4%** (n=61) |

## Does the best cell beat the grid?

- cells at n≥40: **10** (both directions, so choosing the direction after the fact is paid for)
- best: **hot · friendly ump · against · gap ≥ 0.032 (bigger)** at +12.7%
- biggest a price-redraw manufactures: median **+10.7%**, 95th pct **+24.6%**
- **corrected p = 0.381**

**Does not clear.**

- split-half of **hot · friendly ump · against · gap ≥ 0.032 (bigger)**: 23-12 · **+25.8%** (n=35) against 13-13 · **-4.9%** (n=26)

_Halves landing far apart means noise, whatever the pooled number says._

## How to read this

- the umpire has never been tested as a signal before; as a CONDITION on predictability it came back flat (p = 0.900)
- hot bats alone are null in three earlier files, and line-against is the gate the live rule already uses, so anything here has to come from the interaction rather than the parts
- nothing here changes the board.
