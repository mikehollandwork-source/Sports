# Which market on our hitters is actually worth taking?

_Read-only. Stakes nothing, enters no ledger. Every OUTCOME is graded from a boxscore; prices are the ones actually captured, and the market with no captured price says so._

- hitter-games on final board games: **26397** across **1286** games
- hitters with both halves usable: **505**; measured on **12856** held-out hitter-games

## One leg at a time — the rate, and the price it is sold at

_Hitters are filtered ONCE on the held-out HIT rate at 60%, the population the board's selector posts from, and then measured in all three markets. **187** hitters, **5641** hitter-games._

| market | rate | fair price | real median price | it needs | edge |
|---|---|---|---|---|---|
| 1+ hit | **61.7%** | -161 | -173 _(n=4484)_ | 63.4% | **-0.0 pts** |
| 2+ total bases | **36.4%** | +175 | _never captured_ | — | — |
| 2+ hits+runs+RBIs | **47.4%** | +111 | +115 _(n=42)_ | 46.5% | **+0.0 pts** |

_`edge` is percentage POINTS of hit rate over the break-even the price demands. Multiply by roughly 1.5 to read it as ROI at a short price, or 2 at plus money._

## Do two of them on the same team co-move?

_A parlay is priced as if its legs are independent, so a positive lift is the only thing that makes one better than its legs. Read **vs null**: the raw ratio carries the quality filter's winner's curse, the permutation null carries the identical bias and differs only in which game each outcome came from, so the ratio of the two is the part that is actually correlation._

| market | legs | pairing | combos | observed | independent | vs null |
|---|---|---|---|---|---|---|
| 1+ hit | 2 | same team | 5800 | 37.88% | 45.84% | **×1.001** |
| 1+ hit | 2 | opposite | 6299 | 37.72% | 45.90% | **×0.990** |
| 1+ hit | 3 | same team | 3542 | 23.15% | 30.93% | **×1.011** |
| 1+ hit | 3 | opposite | 12976 | 23.22% | 31.08% | **×0.992** |
| 2+ total bases | 2 | same team | 5800 | 13.69% | 16.58% | **×1.039** |
| 2+ total bases | 2 | opposite | 6299 | 12.94% | 16.68% | **×0.984** |
| 2+ total bases | 3 | same team | 3542 | 5.53% | 6.70% | **×1.158** |
| 2+ total bases | 3 | opposite | 12976 | 5.09% | 6.82% | **×1.071** |
| 2+ hits+runs+RBIs | 2 | same team | 5800 | 24.45% | 26.89% | **×1.098** |
| 2+ hits+runs+RBIs | 2 | opposite | 6299 | 22.05% | 26.78% | **×0.984** |
| 2+ hits+runs+RBIs | 3 | same team | 3542 | 13.41% | 13.95% | **×1.295** |
| 2+ hits+runs+RBIs | 3 | opposite | 12976 | 11.65% | 13.95% | **×1.104** |

## The same-team parlay, market by market

_True joint probability from the observed rate, against what the real median price demands once it is multiplied. The total-bases row has no real price, so it is omitted rather than guessed._

| market | legs | true P(all) | price | needs | ROI |
|---|---|---|---|---|---|
| 1+ hit | 2 | 38.16% | +149 | 40.16% | **-5.0%** |
| 1+ hit | 3 | 23.79% | +293 | 25.45% | **-6.5%** |
| 2+ hits+runs+RBIs | 2 | 24.69% | +362 | 21.63% | **+14.1%** |
| 2+ hits+runs+RBIs | 3 | 13.84% | +894 | 10.06% | **+37.6%** |

## The decisive check: each captured price against ITS OWN hitter

_The table above pairs a rate measured on QUALITY hitters with a median price taken over EVERY hitter the book listed. Good hitters are priced shorter, so that mismatch alone could manufacture the edge. Here each quoted name is resolved to the player and scored against his own held-out rate._

- captured prices resolved to a measured hitter: **42** (0 unresolved)
- median price **+115**, so the average quote needs **46.7%**
- POOLED rate of those hitters over **1571** held-out games: **50.8%**
- **pooled edge: +4.1 points**
- quotes the hitter's own (noisy) rate beat: **24/42** = 57%, against 50% by chance (±15%)

- **NOT ESTABLISHED.** The pooled edge is +4.1 points, but 24 of 42 quotes beaten is inside chance at this sample. 42 prices from four October dates cannot settle it, and the per-hitter edges are far too noisy to rank — six games is the minimum half, so a rate can read 65% off four of six.

## Caveats

1. Prices are the MEDIAN of what was captured, not what was available on each individual night, so a single leg's real edge varies around the number shown.
2. 2+ total bases has no captured price anywhere in the repo. Its rate is real; whether it is sold near fair is unknown, and that is the one thing worth capturing next.
3. Hitters are filtered on their HIT rate for every market, because that is what the selector estimates. A selector built for total bases or H+R+RBI would pick different hitters and could do better than these numbers.
