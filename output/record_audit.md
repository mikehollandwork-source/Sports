# Record audit — what was posted vs what got graded

_The board is stateless and `settle_day` reads only the final committed version, so a pick that stops qualifying before its 15-minute lock window disappears. It was on Telegram; it is not in the ledger._

- games that were a pick in SOME version, and are final: **386**
- survived to the final board (graded): **208**
- **dropped before the lock (never graded): 178** (46%)

## Does dropping them flatter the record?

| population | at the price first posted |
|---|---|
| survived — what the ledger books | 123-85 (59%) · +4.70u · **+2.3%** (n=208) |
| **dropped — never graded** | **86-92 (48%) · -26.56u · **-14.9%** (n=178)** |
| everything ever posted | 209-177 (54%) · -21.86u · **-5.7%** (n=386) |

- the recorded population returns **+2.3%**; everything that actually appeared returns **-5.7%**
- **bias from silent dropping: +7.9 points**

The ledger is FLATTERED by +7.9 points: the picks that quietly vanished did worse than the ones that stayed.

## Is surviving to the lock actually predictive?

_Permuting the survived/dropped labels keeps every outcome and price fixed and asks only whether the label carries information._

- observed gap: **+17.2 points**
- **permutation p = 0.0288**

**Real.** A pick that still qualifies at its own lock window is a materially better bet than one that has stopped qualifying, and that is implementable: check the board ~15 minutes before first pitch and skip anything that has fallen out.

## Fading the picks the rule withdrew

_Backing the OTHER side of every pick that stopped qualifying, at that side's own real price. A -12.9% bet does not become +12.9% reversed - the fade pays its own vig, which is the whole reason a losing cell is not automatically a winning one backwards._

- withdrawn picks with a priced other side: **178**
- backing them (what the rule dropped): 86-92 · -26.56u · **-14.9%**
- **fading them: 92-86 · +22.78u · +12.8%**
- the two do not sum to zero: the gap is the vig paid twice (-2.1% combined)

- day-block 95% CI on the fade: **-4.8% to +30.6%**

**The fade does not clear zero.** The withdrawn picks lost, but not by enough to pay the vig on the other side - which is the usual fate of an inverted losing cell.

## Price drift on the picks that survived

_The ledger books the frozen closing price; the channel showed the earlier one. If they differ, the recorded ROI is not the ROI a reader would have got._

- survivors whose price changed: **157/208**
- graded at the FIRST posted price: 123-85 (59%) · +4.70u · **+2.3%** (n=208)
- graded at the FINAL recorded price: 123-85 (59%) · +3.07u · **+1.5%** (n=208)

- difference: **+0.8 points** in favour of the posted price
