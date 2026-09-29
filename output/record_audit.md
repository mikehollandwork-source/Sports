# Record audit — what was posted vs what got graded

_The board is stateless and `settle_day` reads only the final committed version, so a pick that stops qualifying before its 15-minute lock window disappears. It was on Telegram; it is not in the ledger._

- games that were a pick in SOME version, and are final: **418**
- survived to the final board (graded): **222**
- **dropped before the lock (never graded): 196** (47%)

## Does dropping them flatter the record?

| population | at the price first posted |
|---|---|
| survived — what the ledger books | 132-90 (59%) · +6.07u · **+2.7%** (n=222) |
| **dropped — never graded** | **95-101 (48%) · -28.79u · **-14.7%** (n=196)** |
| everything ever posted | 227-191 (54%) · -22.71u · **-5.4%** (n=418) |

- the recorded population returns **+2.7%**; everything that actually appeared returns **-5.4%**
- **bias from silent dropping: +8.2 points**

The ledger is FLATTERED by +8.2 points: the picks that quietly vanished did worse than the ones that stayed.

## Is surviving to the lock actually predictive?

_Permuting the survived/dropped labels keeps every outcome and price fixed and asks only whether the label carries information._

- observed gap: **+17.4 points**
- **permutation p = 0.0208**

**Real.** A pick that still qualifies at its own lock window is a materially better bet than one that has stopped qualifying, and that is implementable: check the board ~15 minutes before first pitch and skip anything that has fallen out.

## Fading the picks the rule withdrew

_Backing the OTHER side of every pick that stopped qualifying, at that side's own real price. A -12.9% bet does not become +12.9% reversed - the fade pays its own vig, which is the whole reason a losing cell is not automatically a winning one backwards._

- withdrawn picks with a priced other side: **196**
- backing them (what the rule dropped): 95-101 · -28.79u · **-14.7%**
- **fading them: 101-95 · +25.11u · +12.8%**
- the two do not sum to zero: the gap is the vig paid twice (-1.9% combined)

- day-block 95% CI on the fade: **-3.6% to +29.3%**

**The fade does not clear zero.** The withdrawn picks lost, but not by enough to pay the vig on the other side - which is the usual fate of an inverted losing cell.

### Which kind of withdrawal is worth fading?

_A pick the order book turned against is a different event from one whose discount simply evaporated. Lumping them hides whichever carries the information._

| why it was dropped | n | backing it | fading it |
|---|---|---|---|
| price discount evaporated | 75 | -11.1% | **+10.8%** |
| other | 45 | -22.1% | **+16.7%** |
| book turned against it | 44 | -13.7% | **+12.5%** |
| handle/tickets stopped agreeing | 32 | -14.1% | **+12.3%** |

- best reason: `other` fading at **+16.7%** (n=45)
- median best-in-noise across 4 reasons: **+28.6%**
- **corrected p = 0.984**

### Fade by reason AND price of the side we would back

_The grid asked for. Cells below n=15 are italic and excluded from the correction - at 20 cells this dataset has manufactured a winner every time, so the corrected p below is the number that decides, not the greenest box._

| why dropped | ≤-150 | -149..-120 | -119..-101 | +100..+139 | ≥+140 |
|---|---|---|---|---|---|
| price discount evaporated | — | _+14% (3)_ | _+96% (3)_ | **+2%** (39) | **+13%** (30) |
| other | _+60% (1)_ | _-4% (11)_ | _+19% (13)_ | **+28%** (17) | _+5% (3)_ |
| book turned against it | — | _+79% (3)_ | _+12% (7)_ | **-1%** (18) | **+16%** (16) |
| handle/tickets stopped agreeing | — | _+22% (3)_ | _-19% (7)_ | **+20%** (18) | _+26% (4)_ |

- cells at n≥15: **6**
- best: `other @ +100..+139` at **+27.7%** (n=17)
- median best-in-noise: **+42.6%**
- **corrected p = 0.901**

**Does not clear.** Slicing further did not find a pocket - it found what a 20-cell grid always finds here.

_If the fade is added, the POOLED version is the statistically safer one: it selects nothing, so there is no selection to be wrong about. Picking the best cell of twenty is the move that has failed sixteen times in this repo._

## Price drift on the picks that survived

_The ledger books the frozen closing price; the channel showed the earlier one. If they differ, the recorded ROI is not the ROI a reader would have got._

- survivors whose price changed: **159/222**
- graded at the FIRST posted price: 132-90 (59%) · +6.07u · **+2.7%** (n=222)
- graded at the FINAL recorded price: 132-90 (59%) · +4.43u · **+2.0%** (n=222)

- difference: **+0.7 points** in favour of the posted price
