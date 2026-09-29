# Is the book-confirm gate worthless, or are we reading the wrong venue?

_`gate_sweep` put the gate at +1.3 points on 958 games — nothing. But the gate reads Polymarket, and against the sportsbook's own de-vigged price Polymarket is off by 0.038 where the venues agree and 0.206 where they diverge, against Kalshi's 0.007 and 0.018. A gate fed by a price that noisy would measure nothing even if confirmation were real — so "worthless" and "fed garbage" predict the same +1.3, and only swapping the venue tells them apart._

- graded games with a majority side: **978**
- with a usable Polymarket read: **958**
- with a usable Kalshi read: **772**
- Kalshi usable where Polymarket is NOT: **19**

## The same gate, different venue

| gate | pass / fail | PASS | FAIL | worth | 95% CI on worth |
|---|---|---|---|---|---|
| Polymarket (what the rule reads now) | 687 / 271 | 396-291 · **-1.4%** | 152-119 · **-0.0%** | **-1.4 pts** | -14.4 to +11.6 |
| Kalshi (the better prices) | 489 / 283 | 267-222 · **-5.7%** | 170-113 · **+3.9%** | **-9.5 pts** | -25.4 to +5.6 |
| both venues confirm | 356 / 397 | 195-161 · **-6.8%** | 232-165 · **+2.4%** | **-9.2 pts** | -23.6 to +4.7 |
| Polymarket drift only | 458 / 500 | 261-197 · **-3.4%** | 287-213 · **+1.2%** | **-4.6 pts** | -17.0 to +7.6 |
| Kalshi drift only | 341 / 431 | 194-147 · **-3.7%** | 243-188 · **-1.0%** | **-2.7 pts** | -20.1 to +13.9 |

## Among games that already pass handle=tickets

_Where the gate actually sits in the rule._

| gate | pass / fail | PASS | FAIL | worth |
|---|---|---|---|---|
| Polymarket (what the rule reads now) | 490 / 167 | 286-204 · **-1.9%** | 98-69 · **+3.1%** | **-4.9 pts** |
| Kalshi (the better prices) | 331 / 192 | 188-143 · **-3.5%** | 109-83 · **-3.6%** | **+0.1 pts** |
| both venues confirm | 249 / 262 | 139-110 · **-6.2%** | 153-109 · **+0.4%** | **-6.6 pts** |
| Polymarket drift only | 334 / 323 | 191-143 · **-4.3%** | 193-130 · **+3.2%** | **-7.5 pts** |
| Kalshi drift only | 239 / 284 | 139-100 · **-3.0%** | 158-126 · **-3.9%** | **+0.9 pts** |

## Corrected for trying 5 venue variants

- best: **Polymarket (what the rule reads now)** at -1.4 pts · the best of 5 reaches +5.3 median, +13.8 at the 95th · **corrected p = 0.915**

- split-half of **Polymarket (what the rule reads now)**: -7.5 pts on one half, +5.3 pts on the other

## What follows

- if the **Kalshi** row is worth materially more than the Polymarket row, the gate was never worthless — it was mis-fed, and the fix is to read the other venue
- if both rows are near zero, order-book confirmation really does carry nothing and the gate should come out of the rule
- the **Kalshi usable where Polymarket is not** count is free sample either way: games like today's Atlanta, discarded for a 20-cent Polymarket spread while Kalshi quoted one cent
