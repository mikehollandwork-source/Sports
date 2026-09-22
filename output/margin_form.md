# Margin and form together, as strengths rather than flags

_`stat_combos` already paired these as binaries - both favouring the stat side returned -6% over 237 games. That test threw away both magnitudes and did not control for price, and a big index gap plus hot bats both push a team toward being a favourite, so "both favour" is partly a price bucket in a stat costume. Here both are read as continuous strengths and price is held fixed by stratification._

- graded games with an index gap and a form read: **965**

## The strong corner, by how form is read

_Backing the stat side when BOTH the index gap and the form gap clear the same percentile. `delta` is the price-stratified difference against the stat side in games that miss the conjunction - the number that is not a price effect._

| tier | form read | back the stat side | price-stratified delta |
|---|---|---|---|
| both above median | team delta | 158-130 · -13.2u · **-4.6%** (n=288) | **-3.8 pts** (283 matched) |
| both above median | hot bats | 148-138 · -29.2u · **-10.2%** (n=286) | **-12.4 pts** (281 matched) |
| both above median | either | 147-136 · -27.2u · **-9.6%** (n=283) | **-11.2 pts** (277 matched) |
| both top third | team delta | 82-70 · -10.2u · **-6.7%** (n=152) | **-7.2 pts** (150 matched) |
| both top third | hot bats | 68-72 · -24.0u · **-17.1%** (n=140) | **-18.6 pts** (139 matched) |
| both top third | either | 68-72 · -24.0u · **-17.1%** (n=140) | **-18.6 pts** (139 matched) |
| both top quartile | team delta | 52-41 · -3.9u · **-4.2%** (n=93) | **-2.6 pts** (92 matched) |
| both top quartile | hot bats | 44-41 · -11.6u · **-13.6%** (n=85) | **-6.7 pts** (80 matched) |
| both top quartile | either | 44-41 · -11.6u · **-13.6%** (n=85) | **-6.7 pts** (80 matched) |

_Baseline for comparison: backing the stat side in every game is 528-437 · -17.0u · **-1.8%** (n=965)._

## Does the best corner beat the search that found it?

- best: **both top quartile / team delta**, price-stratified delta **-2.6 pts**
- cells entering the correction: **9**
- biggest a redraw manufactures: median **+6.1**, 95th pct **+18.9**
- **corrected p = 0.903**

**Does not clear the scan.**

## Does the ladder repeat? (split-half)

| tier / form | half A | half B |
|---|---|---|
| both above median / team delta | -7.4% | -1.2% |
| both above median / hot bats | -10.8% | -9.6% |
| both above median / either | -9.8% | -9.3% |
| both top third / team delta | -8.0% | -5.4% |
| both top third / hot bats | -23.9% | -8.1% |
| both top third / either | -23.9% | -8.1% |
| both top quartile / team delta | -8.4% | -0.1% |
| both top quartile / hot bats | -28.2% | +5.2% |
| both top quartile / either | -28.2% | +5.2% |

- **split-half r = -0.40** over 9 cells

_Not repeatable. The strong corner in one half does not predict the other._

## The best corner (both top quartile / team delta) over time and against the line

- in-sample: 14-12 · -0.9u · **-3.6%** (n=26) _(thin)_
- holdout: 38-29 · -3.0u · **-4.4%** (n=67)

- line moved AGAINST the stat side: 13-15 · -4.6u · **-16.6%** (n=28) _(thin)_
- line moved WITH it: 17-13 · -2.4u · **-8.1%** (n=30)

_If these two are similar, the split is not the price discount - it is 'the line moved at all', which in this dataset tracks data availability more than anything about the game. That trap was walked into once already in `stat_price`._

## How to read this

- the **delta** column is the only one that isolates the conjunction; the raw ROI still contains whatever its price mix did
- a corner that clears the permutation but fails split-half is a cell that got lucky
- the board does not consult margin or form to choose a side, and nothing here changes that on its own.
