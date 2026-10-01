# Source health — 2026-10-01

- board generated: `2026-10-01T06:20:53.913264+00:00`
- games on slate: **1** · picks: **0**

| input | games covered | state |
|---|---|---|
| covers tickets | 1/1 (100%) | ✅ ok |
| handle (usable) | 0/1 (0%) | ❌ dead |
| line movement | 0/1 (0%) | ❌ dead |
| moneylines | 1/1 (100%) | ✅ ok |
| PM order book | 1/1 (100%) | ✅ ok |
| src: covers | 1/1 (100%) | ✅ ok |
| src: forum | 1/1 (100%) | ✅ ok |
| src: polymarket_bets | 1/1 (100%) | ✅ ok |
| src: scoresodds_bets | 1/1 (100%) | ✅ ok |
| src: vsin_bets | 1/1 (100%) | ✅ ok |

## ❌ SILENT FAILURE

The board shows **0 picks** while these inputs are dead: **handle (usable), line movement**. That empty board is a data outage, not a quiet slate - the two are indistinguishable from the board alone, which is the reason this check exists.
