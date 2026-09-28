# Line movement, public money and the two venues, together

_Every consensus-qualifying game, not only the ones we bet. All features signed toward the ADVANTAGE side; the outcome is whether that side won. Order-book readings cut at first pitch minus 15 minutes._

- games: **978**

## Each signal against the result

_`r` is the correlation with the advantage side winning. The two ROI columns back that side when the signal is positive, and when it is negative._

| signal | n | r with winning | signal > 0 | signal < 0 |
|---|---|---|---|---|
| line movement | 973 | **+0.005** | 216-178 · **-6.2%** (n=394) | 235-185 · **+3.4%** (n=420) |
| handle share | 766 | **+0.144** | 305-215 · **-1.9%** (n=520) | 112-132 · **-4.9%** (n=244) |
| ticket majority | 978 | **+0.111** | 408-288 · **-0.9%** (n=696) | 131-151 · **-3.1%** (n=282) |
| Polymarket drift | 958 | **-0.026** | 243-189 · **-2.5%** (n=432) | 174-139 · **+3.5%** (n=313) |
| Polymarket size lean | 958 | **+0.033** | 274-224 · **-3.1%** (n=498) | 237-192 · **-0.1%** (n=429) |
| Kalshi drift | 772 | **+0.001** | 208-156 · **+0.2%** (n=364) | 130-102 · **+3.2%** (n=232) |
| Kalshi size lean | 772 | **-0.025** | 107-94 · **-0.4%** (n=201) | 330-241 · **+2.4%** (n=571) |
| venue price gap | 753 | **+0.005** | 182-138 · **+4.0%** (n=320) | 223-175 · **-0.9%** (n=398) |

## The lead: is the order-book size lean pointed the wrong way?

_`venue_signal` found losers averaging a STRONGER lean toward our side than winners (+0.363 against +0.219), on 103 post-hoc games. Gate 5 treats `imbalance > 0.20` as confirmation, so if that inversion is real the gate is backwards._

| Polymarket size lean toward the advantage side | that side |
|---|---|
| strong lean > +0.40 | 218-164 · **-0.1%** (n=382) |
| lean +0.20 to +0.40  (what gate 5 accepts) | 21-23 · **-14.6%** (n=44) |
| flat -0.20 to +0.20 | 96-75 · **+2.9%** (n=171) |
| lean against -0.40 to -0.20 | 26-19 · **+1.4%** (n=45) |
| strong lean against < -0.40 | 166-150 · **-4.7%** (n=316) |

_If the top rows are worse than the bottom rows, more lean goes with more losing and gate 5's condition is inverted._

## When the three families agree

_One vote each: line movement toward the advantage side, the public (handle and tickets), and the venues (Polymarket and Kalshi drift). Counting how many point the same way._

| families pointing at the advantage side | that side |
|---|---|
| 3 of 3 | 78-49 · **-1.1%** (n=127) |
| 2 of 3 | 146-118 · **-6.6%** (n=264) |
| 1 of 3 | 222-181 · **-1.4%** (n=403) |
| 0 of 3 | 90-88 · **+6.0%** (n=178) |

## Does the best of all of them beat the search?

- cells at n≥40: **20**
- best: **0 of 3** at +6.0%
- biggest a price-redraw manufactures: median **+7.8%**, 95th pct **+14.8%**
- **corrected p = 0.719**

**Does not clear.** A scan this wide manufactures a cell this good often enough that the number is the width of the search.

- split-half of **0 of 3**: 52-42 · **+16.5%** (n=94) against 38-46 · **-5.6%** (n=84)

_Two halves of the same cell landing far apart means the cell is noise, whatever its pooled number._

## How to read this

- a cell must clear the permutation AND repeat across halves; nothing this season has done both
- the size-lean table is the only part bearing on a LIVE gate, so it matters even if every other row is flat
- nothing here changes the board on its own.
