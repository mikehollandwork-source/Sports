# Deep dive — 413 graded games (152 with order-book drift after backfill)

## 1. Is the consensus edge real, or noise?

- **All:** 47-24 (66%) · **+9.8%** (n=71)
- **In-sample:** 27-15 (64%) · **+8.7%** (n=42)
- **Holdout:** 20-9 (69%) · **+11.5%** (n=29)

**Day-block bootstrap 95% CI on ROI: -5.1% to +20.7%** (median +9.9%) — **cannot rule out zero** — not yet proven.

_Resamples whole slates, since games on the same day share market conditions and are not independent bets._

Market-implied win rate for these exact bets: **60.4%**; actual **66.2%** (**+5.8 pts**). The bar to beat is the price, not 50%.

### Sensitivity — does the edge survive moving the threshold?

| drift/imbalance bar | ALL | in-sample | HOLDOUT |
|---|---|---|---|
| loose | 46-26 (64%) · **+5.8%** (n=72) | 27-16 (63%) · **+6.2%** (n=43) | 19-10 (66%) · **+5.3%** (n=29) |
| live setting | 47-24 (66%) · **+9.8%** (n=71) | 27-15 (64%) · **+8.7%** (n=42) | 20-9 (69%) · **+11.5%** (n=29) |
| tighter | 42-25 (63%) · **+3.6%** (n=67) | 23-16 (59%) · **-0.3%** (n=39) | 19-9 (68%) · **+9.0%** (n=28) |
| tightest | 41-24 (63%) · **+4.8%** (n=65) | 24-15 (62%) · **+4.4%** (n=39) | 17-9 (65%) · **+5.3%** (n=26) |

## 2. Everything that is positive in BOTH windows

_Scanned every 1- and 2-condition combination x 4 bet sides (n≥25, holdout n≥8), keeping only those profitable in-sample AND in holdout._

**Real scan found 15. On randomly shuffled outcomes the same scan finds 0.0 on average (95th pct 0).** The real scan beats what chance produces, so the survivors are worth a look.

| conditions | bet side | ALL | in-sample | HOLDOUT |
|---|---|---|---|---|
| consensus (money with public) + public-window move | opp | 15-11 (58%) · **+29.9%** (n=26) | 10-8 (56%) · **+24.4%** (n=18) | 5-3 (62%) · **+42.4%** (n=8) |
| PM drift down + PM size against adv | opp | 17-8 (68%) · **+27.2%** (n=25) | 9-5 (64%) · **+23.8%** (n=14) | 8-3 (73%) · **+31.5%** (n=11) |
| consensus (money with public) + PM drift down | opp | 23-16 (59%) · **+17.8%** (n=39) | 14-11 (56%) · **+18.1%** (n=25) | 9-5 (64%) · **+17.4%** (n=14) |
| line toward adv ≥2% + public-window move | opp | 16-15 (52%) · **+14.7%** (n=31) | 11-10 (52%) · **+15.0%** (n=21) | 5-5 (50%) · **+13.9%** (n=10) |
| public-window move | opp | 18-17 (51%) · **+13.8%** (n=35) | 12-11 (52%) · **+14.7%** (n=23) | 6-6 (50%) · **+12.2%** (n=12) |
| line toward adv ≥2% + PM size toward adv | anti-consensus | 14-15 (48%) · **+9.9%** (n=29) | 9-9 (50%) · **+9.6%** (n=18) | 5-6 (45%) · **+10.5%** (n=11) |
| PM drift up + PM size toward adv | consensus | 24-13 (65%) · **+12.4%** (n=37) | 11-6 (65%) · **+18.6%** (n=17) | 13-7 (65%) · **+7.1%** (n=20) |
| consensus (money with public) + PM size toward adv | consensus | 35-21 (62%) · **+5.8%** (n=56) | 19-13 (59%) · **+4.0%** (n=32) | 16-8 (67%) · **+8.4%** (n=24) |
| consensus (money with public) + line toward adv ≥2% | opp | 32-34 (48%) · **+10.6%** (n=66) | 23-28 (45%) · **+3.8%** (n=51) | 9-6 (60%) · **+33.3%** (n=15) |
| PM size toward adv | consensus | 44-28 (61%) · **+5.2%** (n=72) | 25-18 (58%) · **+3.0%** (n=43) | 19-10 (66%) · **+8.4%** (n=29) |
| consensus (money with public) + PM drift up | adv | 32-21 (60%) · **+3.6%** (n=53) | 19-13 (59%) · **+4.3%** (n=32) | 13-8 (62%) · **+2.6%** (n=21) |
| consensus (money with public) + public-window move | anti-consensus | 12-14 (46%) · **+8.8%** (n=26) | 8-10 (44%) · **+1.8%** (n=18) | 4-4 (50%) · **+24.5%** (n=8) |
| consensus (money with public) + PM drift up | consensus | 36-17 (68%) · **+16.7%** (n=53) | 23-9 (72%) · **+26.6%** (n=32) | 13-8 (62%) · **+1.5%** (n=21) |
| PM drift up | consensus | 47-27 (64%) · **+10.6%** (n=74) | 28-14 (67%) · **+17.8%** (n=42) | 19-13 (59%) · **+1.3%** (n=32) |
| consensus (money with public) | opp | 126-128 (50%) · **+1.3%** (n=254) | 105-107 (50%) · **+0.7%** (n=212) | 21-21 (50%) · **+3.9%** (n=42) |

_The permutation null is the honest yardstick: any large scan finds 'consistent winners' in pure noise, so a survivor only means something if the real count clearly exceeds the null count._