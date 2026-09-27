# Source health — 2026-09-27

- board generated: `2026-09-27T05:12:19.645064+00:00`
- games on slate: **15** · picks: **0**

| input | games covered | state |
|---|---|---|
| covers tickets | 8/15 (53%) | ⚠️ degraded |
| handle (usable) | 8/15 (53%) | ⚠️ degraded |
| line movement | 8/15 (53%) | ⚠️ degraded |
| moneylines | 11/15 (73%) | ✅ ok |
| PM order book | 15/15 (100%) | ✅ ok |
| src: covers | 8/15 (53%) | ⚠️ degraded |
| src: forum | 5/15 (33%) | ⚠️ degraded |
| src: polymarket_bets | 15/15 (100%) | ✅ ok |
| src: scoresodds_bets | 8/15 (53%) | ⚠️ degraded |
| src: vsin_bets | 1/15 (7%) | ❌ dead |

## ❌ SILENT FAILURE

The board shows **0 picks** while these inputs are dead: **src: vsin_bets**. That empty board is a data outage, not a quiet slate - the two are indistinguishable from the board alone, which is the reason this check exists.
