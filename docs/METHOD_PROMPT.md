# Method prompt — porting the MLB edge-finder's discipline to NBA

Paste this whole file as your first message to Claude in the NBA repo.

---

## Read this before you use it

The MLB system this came from is **not profitable**. Current books:

| book | record | ROI |
|---|---|---|
| moneyline plays | 156-124 | **−2.6%** |
| 1+ hit prop singles | 107-62 | **−5.0%** |
| parlays (retired) | 20-47 | **−28.2%** |

So do not copy this expecting a winner. What it actually bought was **small
losses instead of large ones**, and the ability to tell the difference. The
parlay book is the proof: it ran −28.2% with a confidence interval excluding
zero, the method caught it, and it was retired. The method's main product is
**rejections** — things that looked profitable and were not:

- an umpire strikeout tendency (failed three ways, twice with the wrong sign)
- park shape and "has he homered here" (Simpson's paradox)
- a same-team correlation lift of ×1.035 that became **×1.001** on a bigger
  sample — pure noise
- an "unmissable" alternate-strikeout leg that cleared only 92% and got
  **worse** with more data
- a hot-hand form term scoring **AUC 0.5053** against getting a hit — a coin
  flip — that was silently deciding which prop got picked

Every one of those would have cost money. If your NBA system is losing more
than ~3%, the fastest profit is not a better model, it is deleting the terms
that do not work.

---

## The non-negotiables

### 1. A hit rate is not an edge

This is the one that matters most. For every market, compute the break-even
the price demands:

```python
def break_even(american):            # the ONLY number that decides a bet
    return abs(american)/(abs(american)+100) if american < 0 else 100/(american+100)
```

A 55% side at −115 is break-even. A 62.6% prop at −213 loses 5.5 points a
bet. **Nothing becomes bettable until the measured rate clears its price by
more than its own confidence interval.** Report edges in POINTS (rate minus
need, ×100) — and note that `rate - need` is a fraction: formatting it `:+.1f`
once printed an 18-point edge as "+0.2 pts".

NBA specifics: alt-lines and same-game parlays carry far more hold than
moneylines. Price the hold explicitly — `1-(1-h)^n` for n legs.

### 2. Pre-register every threshold, then never touch it

Set each cut-off from the data's own distribution (a league median, a measured
rate) **before** your forward record exists. Then leave it alone. Re-tuning a
threshold against the record it is judged by re-creates the selection bias the
threshold existed to escape. Write the number, the date and the justification
in a file; if you later want to change it, that is a new pre-registration with
its own forward record, not an edit.

### 3. Selecting on a rate and measuring with that rate manufactures effects

The single most expensive trap. Filtering hitters at 60% on an 18-game rate
(SE 0.115) selects upward noise, so the expectation overstates true skill —
it once reported a ×0.807 "anti-correlation" no mechanism could explain.
**Holding the measured games out of the rate does NOT fix it; the bias is in
the estimate.** The fix is to read every lift **relative to a permutation
null** that carries the identical bias and differs only in which game each
outcome came from. That null sat at ×0.72–0.80, not ×1.000, and the gap WAS
the bias. Always report the null, never the raw ratio.

NBA: this bites hardest on "players shooting well lately" screens.

### 4. Held-out halves, and out-of-sample in date order

Filter on one half of a player's games, measure on the other. For anything
time-dependent, build the measure from **prior** games only and score it
forward in date order. When you bake off competing measures, score them by AUC
against the real outcome on out-of-sample data and let the winner win — the
first thing shipped in the MLB system came **last** of five when finally
tested properly.

### 5. The noise floor decides whether a quantity exists at all

Before modelling a per-referee/per-coach/per-venue tendency, compare the
observed spread of those tendencies to the **sampling floor** (`per_unit_SD /
sqrt(n)`). Umpire strikeout tendencies spread at SD 0.57 against a floor of
0.64 — **0.90× the floor**, i.e. no wider than if every umpire were identical.
A real effect spreads WIDER than its floor. If it does not, stop; there is
nothing to model and no amount of feature engineering creates it.

NBA: run this on referee totals/pace effects before believing any of it.

### 6. Freeze the selection before the event, and never let the outcome leak in

The worst bug in the MLB system's history: **4 of 29 board-games (14%) had
their prop re-picked after first pitch**, off season gamelogs that by then
contained that game's own at-bats. One pick was made at 7:08pm for a 5:00pm
game and the ledger settled it.

- Freeze when the real lineup is confirmed, and distinguish a **confirmed**
  lineup from a fallback guess. The MLB bug was that the lineup call silently
  returned the whole active roster when no order was posted, giving the caller
  no way to tell.
- Publish nothing before the freeze. A provisional pick on the board invites
  betting it.
- After the freeze, only the PRICE may refresh. The players never change.
- Anything that writes to a row after the freeze must consult the frozen set —
  a lock is not self-enforcing.

**NBA is harder here than MLB**: inactives land ~30 minutes before tip, and a
late scratch changes everyone's minutes. Your freeze should key on the official
inactive list, and you need a rule for what happens when a starter is ruled out
after you froze.

### 7. A prop needs opportunity, and opportunity is predictable

A hitter lifted in the sixth got two plate appearances. The MLB fix gates on
how often a player's night runs short — and **which measure to use was decided
by a 33,000-start bake-off, not by assumption**. The winner was a recent short
rate shrunk toward season; counting substitutions came dead last because it
cannot tell a ninth-inning defensive sub from a fifth-inning pinch hit.

**This is the single biggest NBA transfer.** Minutes are far more volatile than
plate appearances: blowouts, garbage time, back-to-backs, rest management, foul
trouble. A player on a 20-point favourite is at real risk of sitting the
fourth. Build a minutes-risk gate, decide its measure by bake-off, and apply it
to every over.

**Unknown is not risky** — below the minimum sample, return None and let it
through. A feed outage must never silently empty the board.

### 8. Settle by immutable ID, never by name

Two feeds will disagree on names in both directions. The odds feed served
`jose ramirez` where the league said `José Ramírez`, and `agustín ramírez`
alongside `ronald acuna jr.` for a man spelled `Acuña`. **32 of 499 cached
names (6.4%) could not match on `.lower()`.** One missed match let a prop fall
back to an assumed −200 and withheld a 66.3% read by four tenths of a point
against a price no book was offering.

Fold names once (NFKD, drop combining marks, strip parentheticals, collapse
punctuation) and route every cross-feed match through that one function. Settle
on player IDs only. Then write a guard that asserts it **from the files**, and
make the guard compare the PRICE, not the name — a guard that folds both sides
itself will pass even after you delete the folding.

### 9. "No data" and "the data says no" are different facts

Three separate incidents, all the same shape:

- A postponed game reads as `Final` in the league's abstract state, with both
  scores null. Settling on that booked **losses on games never played**, and
  one entry was the exact opposite of the truth — the player went 2-for-4 in
  the makeup game.
- An empty consensus board got reported as a SILENT FAILURE when the source's
  own page said "No other matchups available". Our parser was fine.
- An empty cached odds board was never re-checked, so a price that posted
  later could never be picked up.

Build your health check to separate: **feed broken** / **feed fine but empty**
/ **our rule declined**. Only the first should alert. An alert that fires on
the other two gets trained into noise and then you miss the real one.

### 10. Never alter the record, with one exception

The forward record is the only thing that settles a disagreement about a
number, and it is worthless if it gets edited when inconvenient. Never re-grade
to reflect a model change. Never re-tune against it.

The one exception is a **settlement bug**: entries for games that did not
happen, or graded against the wrong outcome. Those are not results. Void them
(remove — a void is an absence, not a 0.00 push), recompute the running
balance as a cascade from the entries themselves, and stamp each corrected row
with why.

### 11. Track before you bet, and keep the books separable

Anything unproven gets its own book with nothing staked, labelled so it cannot
be mistaken for the real record. Store the **expectation** on every entry —
modelled rate, break-even, EV — so the record reads against the prediction
rather than against zero. Stamp the structure, so when you change the design
you do not pool two different products into one ROI.

### 12. Parlays: the arithmetic is not negotiable

A parlay's EV is the **product** of its legs' EVs, so negative legs multiply.
Two legs at −11.5% and −14.6% are **−24.4%** together. This does not depend on
your reads being right: if they are too low and regress upward, the legs get
less bad but the parlay stays worse than the singles at every calibration — and
the moment a leg turns positive, the correct move is to post it as a single.

The only legitimate parlay edge is **correlation**, because books price legs as
independent. In MLB, hit props do not co-move (×1.001 on 5800 combos) but
H+R+RBI does (×1.098 pairs), because runs and RBIs are team events.

**NBA is the opposite of MLB here, and this is your biggest genuine
opportunity.** Pace lifts every total in a game. A teammate's assists correlate
with another's made shots. Minutes redistribute when someone sits. Measure
these against a permutation null and an opposite-team control — the control
landing on ×1.000 is your validity check — and remember a ×1.17 lift still has
to cover compounding hold plus whatever deficit the legs start with.

### 13. Beware the nested leg

2+ total bases cannot happen without a hit, so the same player on both legs is
three legs of risk priced as four. That artifact produced a **+29%** backtest
ROI that was entirely fake. **NBA is full of these**: points and PRA, 3PM and
points, assists and PRA. Any positive parlay ROI you compute should be checked
for this first.

---

## How to work

1. State assumptions before coding. If two readings exist, say both.
2. Define success as a verifiable check, then loop until it passes.
3. Make surgical changes; every changed line should trace to the request.
4. Degrade gracefully — one game's failure must never abort the run.
5. **Write down what you killed and why.** The rejections are the asset. Every
   null above is in the MLB repo's CLAUDE.md with its p-value and sample size,
   which is the only reason nobody re-litigates them.

## Order to build it in

1. Break-even arithmetic and a record keyed on IDs. Nothing else matters yet.
2. A health check that tells broken from empty.
3. The freeze, keyed on confirmed inactives.
4. The minutes-risk gate, measure chosen by bake-off.
5. One signal at a time, each pre-registered, each with a held-out measurement
   and a permutation null, each either shipped or written up as dead.

Expect most of them to be dead. That is the method working.
