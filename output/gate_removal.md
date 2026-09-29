# Removing the book-confirm gate

_Four independent measurements say it does nothing: +1.3 points standing alone (`gate_sweep`), −1.4 on Polymarket and −9.5 on Kalshi's better prices (`venue_swap`, p = 0.915), sign-reversed in `disagreement` once the look-ahead was fixed, and −10.5% in `venue_cross`. Feeding it prices five to eleven times more accurate made it worse, which removes the last excuse that it was mis-fed rather than empty._

_Nothing is fitted here, so a walk-forward means temporal consistency: does dropping it help block after block, or once? That is the standard that reverted the gate tuning._

- graded games with a majority side: **1218**

## The three variants, whole sample

| rule | record | 95% CI on ROI |
|---|---|---|
| live rule (as it runs today) | 63-41 · **+5.5%** (n=104) | -10.3% to +21.5% |
| confirm gate dropped, read still required | 99-69 · **+4.3%** (n=168) | -8.4% to +16.7% |
| book dropped entirely | 124-84 · **+6.4%** (n=208) | -5.5% to +18.1% |

## The games removal actually adds

_The variants above share most of their picks, so their totals look alike whatever the truth is. These are the bets the change adds — passing handle=tickets and the line gate, failing the book gate. Their return IS what the change is worth._

| added by | record | 95% CI on ROI |
|---|---|---|
| dropping the confirm gate | 36-28 · **+2.3%** (n=64) | -17.7% to +22.4% |
| dropping the book entirely | 61-43 · **+7.3%** (n=104) | -10.3% to +24.5% |

- **the added bets are not distinguishable from break-even.** Removal is then justified by sample size and simplicity, not by profit: it stops discarding games on a signal measured at zero, and more picks at the same edge is still more edge.

## Block by block — 8 blocks of 10 board days

| block starts | live | confirm dropped | book dropped |
|---|---|---|---|
| 2026-07-05 | +87.9% (3) | +87.9% (3) | +27.1% (20) |
| 2026-07-18 | -19.4% (9) | -7.0% (18) | -7.0% (18) |
| 2026-07-28 | +4.2% (17) | +7.6% (32) | +9.6% (33) |
| 2026-08-07 | -11.1% (19) | -20.2% (24) | -23.4% (25) |
| 2026-08-17 | +5.8% (11) | +8.3% (20) | +11.1% (21) |
| 2026-08-27 | +41.7% (19) | +35.2% (27) | +35.2% (27) |
| 2026-09-06 | -31.7% (9) | -23.5% (16) | -28.0% (17) |
| 2026-09-16 | +9.4% (13) | -4.5% (21) | -4.5% (21) |

- confirm-dropped beat live in **4/8** blocks
- book-dropped beat live in **4/8** blocks
- **not consistent across time** — the variants trade blocks, which is what two rules of equal merit look like

## Leave August out

| period | live | confirm dropped | book dropped |
|---|---|---|---|
| all months | 63-41 · **+5.5%** (n=104) | 99-69 · **+4.3%** (n=168) | 124-84 · **+6.4%** (n=208) |
| **excluding August** | 31-23 · **+1.0%** (n=54) | 54-40 · **+2.2%** (n=94) | 78-54 · **+6.4%** (n=132) |
| September only | 22-15 · **+2.7%** (n=37) | 35-25 · **+1.3%** (n=60) | 35-26 · **-0.4%** (n=61) |

## The call

- removal is right if the added games are **not losing** and the variants hold across blocks — a gate measured at zero should not be discarding sample
- removal is wrong only if the added games lose materially, which would mean the gate was doing something the earlier tests missed
- either way this is a rule change, so the record starts counting from the change forward and nothing before it is restated
