# Record audit — what was posted vs what got graded

_The board is stateless and `settle_day` reads only the final committed version, so a pick that stops qualifying before its 15-minute lock window disappears. It was on Telegram; it is not in the ledger._

- games that were a pick in SOME version, and are final: **439**
- survived to the final board (graded): **242**
- **dropped before the lock (never graded): 197** (45%)

## Does dropping them flatter the record?

| population | at the price first posted |
|---|---|
| survived — what the ledger books | 143-99 (59%) · +4.49u · **+1.9%** (n=242) |
| **dropped — never graded** | **96-101 (49%) · -27.92u · **-14.2%** (n=197)** |
| everything ever posted | 239-200 (54%) · -23.43u · **-5.3%** (n=439) |

- the recorded population returns **+1.9%**; everything that actually appeared returns **-5.3%**
- **bias from silent dropping: +7.2 points**

The ledger is FLATTERED by +7.2 points: the picks that quietly vanished did worse than the ones that stayed.

## Is surviving to the lock actually predictive?

_Permuting the survived/dropped labels keeps every outcome and price fixed and asks only whether the label carries information._

- observed gap: **+16.0 points**
- **permutation p = 0.0283**

**Real.** A pick that still qualifies at its own lock window is a materially better bet than one that has stopped qualifying, and that is implementable: check the board ~15 minutes before first pitch and skip anything that has fallen out.

## Fading the picks the rule withdrew

_Backing the OTHER side of every pick that stopped qualifying, at that side's own real price. A -12.9% bet does not become +12.9% reversed - the fade pays its own vig, which is the whole reason a losing cell is not automatically a winning one backwards._

- withdrawn picks with a priced other side: **197**
- backing them (what the rule dropped): 96-101 · -27.92u · **-14.2%**
- **fading them: 101-96 · +24.11u · +12.2%**
- the two do not sum to zero: the gap is the vig paid twice (-1.9% combined)

- day-block 95% CI on the fade: **-4.3% to +29.1%**

**The fade does not clear zero.** The withdrawn picks lost, but not by enough to pay the vig on the other side - which is the usual fate of an inverted losing cell.

### Which kind of withdrawal is worth fading?

_A pick the order book turned against is a different event from one whose discount simply evaporated. Lumping them hides whichever carries the information._

| why it was dropped | n | backing it | fading it |
|---|---|---|---|
| price discount evaporated | 75 | -11.1% | **+10.8%** |
| other | 46 | -19.7% | **+14.2%** |
| book turned against it | 44 | -13.7% | **+12.5%** |
| handle/tickets stopped agreeing | 32 | -14.1% | **+12.3%** |

- best reason: `other` fading at **+14.2%** (n=46)
- median best-in-noise across 4 reasons: **+28.2%**
- **corrected p = 0.997**

### Fade by reason AND price of the side we would back

_The grid asked for. Cells below n=15 are italic and excluded from the correction - at 20 cells this dataset has manufactured a winner every time, so the corrected p below is the number that decides, not the greenest box._

| why dropped | ≤-150 | -149..-120 | -119..-101 | +100..+139 | ≥+140 |
|---|---|---|---|---|---|
| price discount evaporated | — | _+14% (3)_ | _+96% (3)_ | **+2%** (39) | **+13%** (30) |
| other | _+60% (1)_ | _-4% (11)_ | _+19% (13)_ | **+21%** (18) | _+5% (3)_ |
| book turned against it | — | _+79% (3)_ | _+12% (7)_ | **-1%** (18) | **+16%** (16) |
| handle/tickets stopped agreeing | — | _+22% (3)_ | _-19% (7)_ | **+20%** (18) | _+26% (4)_ |

- cells at n≥15: **6**
- best: `other @ +100..+139` at **+20.6%** (n=18)
- median best-in-noise: **+42.0%**
- **corrected p = 0.973**

**Does not clear.** Slicing further did not find a pocket - it found what a 20-cell grid always finds here.

_If the fade is added, the POOLED version is the statistically safer one: it selects nothing, so there is no selection to be wrong about. Picking the best cell of twenty is the move that has failed sixteen times in this repo._

## Guard: watch-only good dogs stay out of the record

_Boards from 2026-09-29 on, when the tag shipped. Earlier entries on teams the tag would now label were booked for other reasons - two July reversal picks match that and are not leaks._

- watch-only good dogs on those boards: **8**
- of those, present in the ledger: **0**
- **PASS** — none of them is in the record

## Guard: watch-only line-vs-money games stay out of the record

_Boards from 2026-10-01 on, when the tag shipped._

- watch-only tagged games on those boards: **1**
- of those, present in the ledger: **0**
- **PASS** — none of them is in the record

## Guard: the pitch-type context never would have changed a HR pick

_Leader takes his own multiplier; runner-up is credited with the measured ceiling ×1.010, so this is a bound, not an observation._

- HR picks carrying the context and a runner-up: **1**
- narrowest margin over the runner-up: **+4.34%** of HR probability
- picks it could have flipped: **0**
- **PASS** — no pick could have changed

## Guard: no prop on a hitter whose nights end early

_Threshold `props.SHORT_NIGHT_MAX` = 23%, the league median of the shrunk recent short-night rate over 2,459 games._

- posted props carrying a pull rate: **0**
- boards predating the gate (no rate stored): **154**
- _none yet; the gate ships with tonight's board._

## Price drift on the picks that survived

_The ledger books the frozen closing price; the channel showed the earlier one. If they differ, the recorded ROI is not the ROI a reader would have got._

- survivors whose price changed: **177/242**
- graded at the FIRST posted price: 143-99 (59%) · +4.49u · **+1.9%** (n=242)
- graded at the FINAL recorded price: 139-103 (57%) · -1.63u · **-0.7%** (n=242)

- difference: **+2.5 points** in favour of the posted price
