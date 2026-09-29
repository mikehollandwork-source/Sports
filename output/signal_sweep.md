# Every signal, isolated, both directions

_**A losing signal is not automatically a winning fade.** Both directions pay the hold, so on the same games backing a side and backing its opponent sum to about MINUS TWICE THE VIG, not to zero. A fade only pays when the signal is wrong by more than the vig — the `sum` column is that bar, made visible._

- graded games: **1223**

| signal | n | BACK it | FADE it | sum |
|---|---|---|---|---|
| stat model (advantage_team) | 1223 | 672-551 · **-1.3%** | 551-672 · **-5.1%** | -6.4% |
| starter BvP | 1161 | 597-564 · **-3.3%** | 564-597 · **-3.1%** | -6.4% |
| bullpen BvP | 1123 | 578-545 · **-2.1%** | 545-578 · **-4.0%** | -6.2% |
| hotter bats (team delta) | 1042 | 522-520 · **-4.1%** | 520-522 · **-1.7%** | -5.8% |
| hot bats (sum of top bats) | 1050 | 549-501 · **+0.2%** | 501-549 · **-6.0%** | -5.9% |
| line moved TOWARD | 1022 | 506-516 · **-7.6%** | 516-506 · **+0.9%** | -6.7% |
| ticket majority | 1212 | 706-506 · **+1.4%** | 506-706 · **-7.9%** | -6.5% |
| handle majority | 890 | 513-377 · **-0.2%** | 377-513 · **-5.8%** | -6.1% |
| Polymarket drift | 962 | 557-405 · **+10.5%** | 405-557 · **-16.2%** | -5.8% |
| Polymarket size lean | 962 | 491-471 · **-2.1%** | 471-491 · **-3.7%** | -5.8% |
| PM quote beats book | 528 | 289-239 · **-4.6%** | 239-289 · **-3.5%** | -8.1% |
| board's own fair price | 917 | 418-499 · **-3.1%** | 499-418 · **-2.3%** | -5.4% |
| better record | 1196 | 656-540 · **-3.5%** | 540-656 · **-3.0%** | -6.4% |
| — home team | 1223 | 646-577 · **-3.4%** | 577-646 · **-3.0%** | -6.4% |
| — the favourite | 1223 | 712-511 · **-0.6%** | 511-712 · **-5.8%** | -6.4% |
| — the underdog | 1223 | 511-712 · **-5.8%** | 712-511 · **-0.6%** | -6.4% |

_Median `sum` across all signals: **-6.4%**. That is the hold, paid twice. A signal whose two directions sum to about that is carrying no information either way, and neither of its numbers is an opportunity — however bad one of them looks._

## Corrected in both tails

_Hunting for losers to fade means the MINIMUM matters as much as the maximum, and choosing whichever tail looks better afterwards is the error `margin_form` caught. Both are corrected separately._

- cells at n≥60: **32**
- best: **back Polymarket drift** at +10.5% · redraws reach +4.0% median · **corrected p = 0.006**
- worst: **fade Polymarket drift** at -16.2% · redraws reach -8.9% median · **corrected p = 0.003**

**Something clears.**

- split-half of **back Polymarket drift**: 270-201 · **+8.6%** (n=471) against 287-204 · **+12.2%** (n=491)
- split-half of **fade Polymarket drift**: 188-258 · **-16.3%** (n=446) against 217-299 · **-16.1%** (n=516)

## How to read this

- the three rows beginning `—` are baselines, not signals; a signal that merely matches 'back the favourite' has found nothing
- the `sum` column is the test of the fade idea: only a signal summing well BELOW the median is wrong by more than the vig and worth fading
- nothing here changes the board.
