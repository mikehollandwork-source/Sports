# Back-testing the parlay structure

_Read-only. Stakes nothing, enters no ledger. Outcomes are graded from the boxscore._

## First finding: the FOUR-leg ticket is not back-testable

_Of 248 past plays, **241 stored no `hit_bats` pool at all** and most of the rest carry exactly ONE hitter. Boards posted a single prop until 2026-10-12. Three distinct hitters never existed in the record, so reconstructing four legs would mean inventing two of them — asking anyway returned six tickets, which is not a measurement. The four-leg record has to be built FORWARD, which is what `parlay_paper` is now doing._

## What the history does support: the moneyline pick + its prop

- gradeable rows: **142** (2026-07-22 to 2026-10-10)
- of those, prop legs with a REAL captured price: **88**

| leg | hit | rate |
|---|---|---|
| moneyline pick | 77/142 | **54.2%** |
| the posted prop, 1+ hit | 90/142 | **63.4%** |
| that same hitter, 2+ total bases | 55/142 | **38.7%** |

- **both together: 48/142 = 33.8%**, against 34.4% if they were independent → same-game lift **×0.984**
  _Positive is expected and is the only thing that makes a parlay better than its legs: a team winning and its hitter getting a hit are the same night going one way. Note the prop may be on EITHER team since 2026-10-12, which weakens exactly this._

## Does the pair beat its price?

| structure | wins | mean price | ROI |
|---|---|---|---|
| ML + 1 prop (2 legs, real prices) | 48/142 (33.8%) | +169 | **-12.8%** |
| + 2 total bases at +100 (3 legs) | 30/142 (21.1%) | +438 | **+7.5%** |
| + 2 total bases at +140 (3 legs) | 30/142 (21.1%) | +545 | **+29.0%** |
| + 2 total bases at +180 (3 legs) | 30/142 (21.1%) | +653 | **+50.5%** |

_The three-leg rows add total bases on the SAME hitter as the hit leg, which is a NESTED leg the live builder now forbids — 2+ total bases cannot happen without a hit. They are shown because the history has no second hitter to use, and they therefore FLATTER the structure: the real four-leg version needs a third hitter to also come through._

## What this says about the total-bases leg

- the board's own posted hitters reach 2+ total bases **38.7%** of the time, so a fair price is about **+158** before any hold
- that is the first measured number for that leg; it was a guess before

## Caveats

1. 54 of 142 prop legs use the assumed -200 rather than a captured price.
2. The props here were chosen by the OLD selector, which carried the `form` term since removed for scoring AUC 0.5053, and were drawn from the PICKED team only. Both changed on 2026-10-12.
3. Total-bases outcomes are real; no total-bases price was ever captured, so those columns are swept.
