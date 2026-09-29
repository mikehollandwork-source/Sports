# Both markets, every side they name, and the opposite of each

_**One piece of arithmetic first.** Where the venues disagree, "take Kalshi" and "take Polymarket" are the same bet inverted — backing one IS fading the other. Those cells sum to about minus twice the hold by construction and cannot both be positive, so the flip is already inside the straight version and the open question is only which venue is right when they split. Both are printed so the identity is visible rather than asserted._

_The same holds for every BACK/FADE pair, which is what the `sum` column is for: both directions pay the vig, so a cell at −6% has no +6% fade behind it._

_`signal_sweep2` already swept Kalshi drift, Kalshi size, both-agree and split-take-Kalshi: everything landed on the vig. What is new is a reason to look again — Kalshi sits 0.007 from the book's de-vigged price where the venues agree and 0.018 where they diverge, against Polymarket's 0.038 and 0.206, and the earlier sweep treated the two as peers. The cross cells were never tested at all._

- graded games: **978**
- with both venues readable: **753**

| side named by | n | BACK it | FADE it | sum |
|---|---|---|---|---|
| Polymarket drift | 746 | 382-364 · **-5.9%** | 364-382 · **-0.2%** | -6.1% |
| Kalshi drift | 597 | 310-287 · **-3.0%** | 287-310 · **-2.0%** | -5.0% |
| Polymarket resting size | 927 | 466-461 · **-4.7%** | 461-466 · **-1.5%** | -6.1% |
| Kalshi resting size | 772 | 347-425 · **-6.0%** | 425-347 · **+1.0%** | -5.0% |
| drift: both venues agree | 281 | 148-133 · **-4.5%** | 133-148 · **+1.0%** | -3.5% |
| drift: they split — take Kalshi | 169 | 85-84 · **-0.4%** | 84-85 · **-5.5%** | -5.9% |
| drift: they split — take Polymarket | 169 | 84-85 · **-5.5%** | 85-84 · **-0.4%** | -5.9% |
| size: both venues agree | 349 | 157-192 · **-7.9%** | 192-157 · **+2.8%** | -5.1% |
| size: they split — take Kalshi | 382 | 173-209 · **-3.2%** | 209-173 · **-2.2%** | -5.4% |
| Kalshi drift + Polymarket size agree | 328 | 168-160 · **-6.7%** | 160-168 · **-0.4%** | -7.1% |
| Polymarket drift + Kalshi size agree | 241 | 113-128 · **-9.4%** | 128-113 · **+1.2%** | -8.2% |
| Kalshi drift, Polymarket size DISAGREES | 242 | 129-113 · **+2.6%** | 113-129 · **-5.4%** | -2.8% |
| all four point the same way | 65 | 35-30 · **+3.4%** | 30-35 · **-12.3%** | -8.9% |
| both venues confirm the money side | 131 | 71-60 · **-10.5%** | 60-71 · **+8.0%** | -2.4% |
| both venues contradict the money side | 64 | 35-29 · **-2.2%** | 29-35 · **+0.4%** | -1.9% |

_Median `sum`: **-5.4%** — the hold, paid twice. A cell summing near that carries nothing in either direction._

_Identity check: backing **drift: they split — take Kalshi** is -0.4% and backing **drift: they split — take Polymarket** is -5.5%; they sum to **-5.9%**, which is the hold twice over — as they must, being the same games opposite ways._

## Corrected across 30 cells, both tails

- best: **fade both venues confirm the money side** at +8.0% (n=131) · redraws reach +14.3% median, +27.8% at the 95th · **corrected p = 0.911**
- worst: **fade all four point the same way** at -12.3% (n=65) · redraws reach -17.2% median, -30.0% at the 5th · **corrected p = 0.858**

- split-half of **fade both venues confirm the money side**: 25-50 · **-21.7%** (n=75) against 35-21 · **+47.9%** (n=56)
- split-half of **fade all four point the same way**: 10-20 · **-31.5%** (n=30) against 20-15 · **+4.2%** (n=35)

## Reading it

- a cell is worth something only if BACK beats the vig, it survives the correction, and both halves agree in sign
- the two "they split" rows are one fact stated twice; their sum being the double hold is a check that the arithmetic is right, not a finding
- **agreement cells shrink the sample.** Both venues pointing the same way is a smaller, easier population, so compare their n before their ROI
