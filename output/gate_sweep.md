# Every gate, isolated, on the whole pool

_`gate_audit` does ablation — each gate judged on the sliver of games that already passed every OTHER gate. That answers whether a gate helps at the margin of the finished rule; it cannot say whether the gate carries any edge at all. `quality_gate` returning +23.8% on our own 104 picks and +0.1% on all 819 qualifying games was that mistake._

_So each gate stands alone here, on the whole pool, no other gate applied. A gate does not pick a side — the side is held fixed at the public-majority team — it only decides bet or don't. So the number that matters is **PASS minus FAIL**, not PASS on its own: a gate that merely selects short favourites shows a fat win rate and no edge, and its FAIL column is the control that catches it._

- graded games with a nameable majority side: **1218**

## The live rule's own gates

| gate | pass / fail | PASS | FAIL | worth | 95% CI on worth |
|---|---|---|---|---|---|
| handle agrees with tickets | 819 / 399 | 481-338 · **+0.2%** | 228-171 · **+3.8%** | **-3.6 pts** | -13.8 to +6.1 |
| an order-book read exists | 958 / 260 | 548-410 · **-1.0%** | 161-99 · **+10.2%** | **-11.2 pts** | -23.3 to +2.0 |
| book DRIFT confirms | 445 / 513 | 260-185 · **-0.8%** | 288-225 · **-1.2%** | **+0.3 pts** | -11.4 to +12.2 |
| book SIZE confirms | 457 / 501 | 265-192 · **+0.1%** | 283-218 · **-2.0%** | **+2.1 pts** | -8.3 to +13.0 |
| book confirms — EITHER (live) | 681 / 277 | 395-286 · **-0.6%** | 153-124 · **-1.9%** | **+1.3 pts** | -11.3 to +13.6 |
| book confirms — BOTH (reverted) | 221 / 737 | 130-91 · **+0.5%** | 418-319 · **-1.4%** | **+1.9 pts** | -11.0 to +15.1 |
| line moved against ≥1.0% (live) | 316 / 891 | 185-131 · **+6.0%** | 520-371 · **+0.2%** | **+5.8 pts** | -5.9 to +17.2 |
| line moved against ≥0.5% | 427 / 780 | 250-177 · **+5.4%** | 455-325 · **-0.3%** | **+5.6 pts** | -5.9 to +17.6 |
| line moved against at all | 501 / 706 | 301-200 · **+7.6%** | 404-302 · **-2.5%** | **+10.1 pts** | -0.8 to +21.6 |

## Board flags that have never been gates

| gate | pass / fail | PASS | FAIL | worth | 95% CI on worth |
|---|---|---|---|---|---|
| public sources trusted | 1066 / 146 | 633-433 · **+1.3%** | 73-73 · **+2.5%** | **-1.3 pts** | -19.0 to +16.4 |
| public verdict corroborated | 691 / 521 | 411-280 · **-1.2%** | 295-226 · **+4.9%** | **-6.1 pts** | -15.9 to +3.4 |
| stat edge is strong | 216 / 996 | 142-74 · **+8.5%** | 564-432 · **-0.1%** | **+8.6 pts** | -3.3 to +20.9 |
| public edge flag | 364 / 854 | 202-162 · **+1.5%** | 507-347 · **+1.3%** | **+0.2 pts** | -11.0 to +10.7 |
| confidence ≥ threshold | 459 / 753 | 277-182 · **+2.0%** | 429-324 · **+1.1%** | **+0.9 pts** | -9.2 to +10.7 |
| starred (any tag) | 38 / 924 | _one side too thin_ | | |
| win-condition hits ≥3 | 581 / 631 | 327-254 · **-2.3%** | 379-252 · **+4.8%** | **-7.1 pts** | -17.9 to +3.4 |
| BvP sample meaningful | 713 / 403 | 407-306 · **-1.2%** | 242-161 · **+4.7%** | **-5.9 pts** | -15.7 to +4.0 |
| sharp money flag | 34 / 783 | _one side too thin_ | | |
| pitching dog | 62 / 961 | 32-30 · **-4.9%** | 553-408 · **-0.6%** | **-4.3 pts** | -26.1 to +16.7 |
| book stance against us | 273 / 765 | 171-102 · **+5.8%** | 426-339 · **-2.4%** | **+8.2 pts** | -4.0 to +20.7 |
| book looks fooled | 392 / 646 | 242-150 · **+7.4%** | 355-291 · **-5.0%** | **+12.4 pts** | +1.5 to +22.6 |
| line vs money 'against' | 208 / 601 | 123-85 · **+5.8%** | 339-262 · **-3.7%** | **+9.5 pts** | -4.1 to +23.1 |
| PM quote better than book | 528 / 450 | 312-216 · **+1.6%** | 247-203 · **-4.3%** | **+5.9 pts** | -4.8 to +16.5 |
| board flagged it | 0 / 1218 | _one side too thin_ | | |

## Corrected across 21 gates, both tails

- best gate: **book looks fooled** worth +12.4 pts · a redraw's best gate reaches +11.5 median, +21.3 at the 95th · **corrected p = 0.415**
- most harmful: **an order-book read exists** worth -11.2 pts · a redraw's worst reaches -11.3 median, -21.3 at the 5th · **corrected p = 0.507**

- split-half of **book looks fooled**: worth +1.4 pts on one half, +23.3 pts on the other
- split-half of **an order-book read exists**: worth -13.7 pts on one half, -8.8 pts on the other

## Reading it

- **worth** is the gate's whole case. A gate earns its place only if its PASS beats its FAIL by more than the correction allows, and by the same sign in both halves
- a CI on **worth** that straddles zero means the gate is not doing anything measurable, whatever its PASS column says
- `book confirms — EITHER` and `BOTH` are the live and reverted settings side by side, on the whole pool rather than on our picks
