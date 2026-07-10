# Underdog research — 979 dog games (2026-03-25..2026-07-09)

**Baseline: bet every dog at close — 431-548 (44%), -1.74u, -0% ROI**

## Winning dogs vs losing dogs — median of each stat

| stat (dog edge) | winners | losers |
|---|---|---|
| winpct_gap | -0.042 | -0.051 |
| rd_gap | -0.599 | -0.542 |
| role_winpct | +0.455 | +0.465 |
| last10_gap | +0.000 | -0.100 |
| sp_fip_gap | -0.709 | -0.724 |
| dog_winpct | +0.471 | +0.466 |
| line_move | +0.000 | -0.004 |

## Best single-stat thresholds (bet dogs meeting it, n≥25, by ROI)

| rule | record | units | ROI |
|---|---|---|---|
| sp_fip_gap ≥ +0.641 | 89-87 (51%) | +18.60u | +11% |
| dog_winpct ≤ +0.416 | 136-154 (47%) | +25.16u | +9% |
| rd_gap ≤ -0.878 | 175-212 (45%) | +27.47u | +7% |
| role_winpct ≤ +0.381 | 131-158 (45%) | +17.06u | +6% |
| line_move ≥ +0.012 | 94-102 (48%) | +9.95u | +5% |
| last10_gap ≥ +0.100 | 154-171 (47%) | +15.04u | +5% |
| winpct_gap ≤ -0.085 | 169-218 (44%) | +12.46u | +3% |

## Categorical splits

| slice | record | units | ROI |
|---|---|---|---|
| dog at HOME | 124-172 (42%) | -21.58u | -7% |
| dog on ROAD | 307-376 (45%) | +19.84u | +3% |
| price short (+100..+130) | 300-351 (46%) | -11.14u | -2% |
| price mid (+131..+180) | 111-154 (42%) | +8.67u | +3% |
| price long (>+180) | 20-43 (32%) | +0.73u | +1% |

## Line movement (open→close, dog implied prob)

| slice | record | units | ROI |
|---|---|---|---|
| dog STEAMED (line toward dog, +0.02) | 70-71 (50%) | +12.69u | +9% |
| dog drifted (line away, -0.02) | 104-134 (44%) | +10.28u | +4% |
| line flat | 257-343 (43%) | -24.71u | -4% |

## Best 2-stat combos (median split each, n≥25, by ROI)

| rule | record | units | ROI |
|---|---|---|---|
| last10_gap ≥ med & line_move ≥ med | 152-169 (47%) | +14.13u | +4% |
| winpct_gap ≥ med & line_move ≥ med | 114-131 (47%) | +5.56u | +2% |
| role_winpct ≥ med & last10_gap ≥ med | 149-180 (45%) | +1.83u | +1% |
| rd_gap ≥ med & line_move ≥ med | 107-126 (46%) | +1.29u | +1% |
| winpct_gap ≥ med & last10_gap ≥ med | 176-208 (46%) | +1.83u | +0% |
| winpct_gap ≥ med & dog_winpct ≥ med | 169-200 (46%) | +0.53u | +0% |
| last10_gap ≥ med & dog_winpct ≥ med | 159-191 (45%) | +0.11u | +0% |
| rd_gap ≥ med & dog_winpct ≥ med | 142-169 (46%) | -2.41u | -1% |
| winpct_gap ≥ med & sp_fip_gap ≥ med | 96-113 (46%) | -2.54u | -1% |
| last10_gap ≥ med & sp_fip_gap ≥ med | 126-154 (45%) | -4.25u | -2% |
| winpct_gap ≥ med & role_winpct ≥ med | 144-178 (45%) | -5.09u | -2% |
| role_winpct ≥ med & dog_winpct ≥ med | 168-212 (44%) | -7.09u | -2% |

_Point-in-time features (no lookahead); market underdog by ESPN closing moneyline; $1/dog at the closing price. Season scan via the MLB Stats API._