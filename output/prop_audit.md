# Props — what separates the winners from the losers

_Read-only. Every feature is corrected together by a max-statistic permutation, so the best of twelve is judged against the best of twelve on noise._

- graded props joined to their board: **142**
- overall: **89-53** = 62.7% · -8.63u · ROI -6.1%

_Fields the CURRENT selector uses - all_rate, form, BvP, platoon, fit - were added days ago and exist on 7 props. They are NOT tested here; three games is not evidence._

## Every feature, split at its median

| feature | cut | low side | high side | hit-rate gap | ROI gap |
|---|---|---|---|---|---|
| `hit_rate` | 78 | 60.3% (73) | 65.2% (69) | **+4.9%** | +6.4% |
| `wins_played` | 57 | 63.0% (73) | 62.3% (69) | **-0.7%** | -4.2% |
| `avg_pa` | 4.4 | 58.5% (82) | 68.3% (60) | **+9.8%** | +9.9% |
| `odds` | -200 | 66.0% (106) | 52.8% (36) | **-13.3%** | -10.7% |
| `park` | 1 | 68.5% (89) | 52.8% (53) | **-15.7%** | -24.4% |
| `temp` | 81 | 63.0% (73) | 62.3% (69) | **-0.7%** | -3.6% |
| `wind` | 7 | 62.0% (79) | 63.5% (63) | **+1.5%** | +0.7% |
| opp_k9 | — | _too lopsided to split_ | | | |
| `ump_k` | -0.07 | 57.6% (66) | 66.7% (66) | **+9.1%** | +15.4% |
| home | — | _too lopsided to split_ | | | |
| was_pick | — | _too lopsided to split_ | | | |
| `adv_ml` | -136 | 65.3% (72) | 60.0% (70) | **-5.3%** | -6.3% |

## Corrected for looking twelve times

- biggest gap found: **`park` at 15.7%**
- shuffling outcomes, the BEST of twelve gaps is typically **14.8%**, and clears 15.7% **44.1%** of the time
- **corrected p = 0.4410**

- **nothing here is distinguishable from noise.** At 142 props, twelve looks produce a gap this size routinely.

## Fading the prop — betting NO hit

_The posted hitter failed to get a hit in the complement of the hit rate. The question is whether the UNDER price covers that._

- posted hitters went **89-53**, so the fade would be **53-89** = **37.3%**

_The under price was never captured: `prop_odds` only ever requested Over 0.5. So it is derived from the over price plus an assumed hold, and shown across a range rather than at one invented figure._

| assumed hold | implied under price | under needs | fade ROI |
|---|---|---|---|
| 4% | +168 | 37.3% | **-0.0%** |
| 5% | +161 | 38.3% | **-2.6%** |
| 6% | +154 | 39.3% | **-5.1%** |
| 8% | +142 | 41.3% | **-9.7%** |
| 10% | +131 | 43.3% | **-13.9%** |

- the fade needs a no-hit rate above the under's implied probability; the actual rate is **37.3%**
- **backing and fading the same bets both lose.** Their ROIs sum to roughly minus twice the hold, which is the whole reason a losing record is not a signal to take the other side

- the −199 to −150 band did go **53.8%** no-hit on 26 props, which is the cell that would tempt. It is the same cell the max-statistic correction above already rejected (corrected p = 0.44), so it is a 26-game stretch, not a rule.

## Price, which is arithmetic rather than a discovery

_Break-even rises with the price, so this needs no significance test - it is what the numbers mean._

| price band | n | hit rate | needs | ROI |
|---|---|---|---|---|
| −250 or worse | 12 | 66.7% | 72.1% | **-8.1%** |
| −249 to −200 | 94 | 66.0% | 66.7% | **-2.8%** |
| −199 to −150 | 26 | 46.2% | 64.0% | **-28.0%** |
| −149 or better | 10 | 70.0% | 58.4% | **+22.4%** |
