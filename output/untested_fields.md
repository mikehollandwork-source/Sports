# The board fields nothing has ever read

_Every key on a board game cross-referenced against every analysis module; ten were referenced by none. Backing the ADVANTAGE side when each field points at it._

- graded games: **1223**

_`stay_bet` and `stay_odds` are populated on 0 of 1,271 rows — dead fields, noted so the loose end is closed rather than carried._

- baseline, backing the advantage side in every game: 672-551 · **-1.3%** (n=1223)

## Each field alone

| condition | backing the advantage side |
|---|---|
| PM says better than book | 289-239 · **-4.6%** (n=528) |
| PM edge ≥ 2 pts | 133-120 · **-8.9%** (n=253) |
| model fair beats price | 256-248 · **-0.8%** (n=504) |
| line vs money 'against' | 119-89 · **+2.5%** (n=208) |
| starred (any tag) | 22-16 · **-8.0%** (n=38) |
| public edge true | 162-202 · **-7.8%** (n=364) |
| public trusted | 591-478 · **-1.8%** (n=1069) |

## In combination

_Every non-empty subset of the seven, kept when it still has n≥40. Sorted best first; the correction below is what decides whether the top of this list means anything._

| combination | backing the advantage side |
|---|---|
| model fair beats price + public edge true | 113-118 · **+3.7%** (n=231) |
| model fair beats price + line vs money 'against' | 65-54 · **+3.1%** (n=119) |
| PM edge ≥ 2 pts + model fair beats price + public edge true | 24-25 · **+0.4%** (n=49) |
| PM says better than book + PM edge ≥ 2 pts + model fair beats price + public edge true | 24-25 · **+0.4%** (n=49) |
| line vs money 'against' + public trusted | 104-81 · **-0.4%** (n=185) |
| PM edge ≥ 2 pts + model fair beats price + public edge true + public trusted | 21-23 · **-0.7%** (n=44) |
| PM says better than book + PM edge ≥ 2 pts + model fair beats price + public edge true + public trusted | 21-23 · **-0.7%** (n=44) |
| model fair beats price + public edge true + public trusted | 91-112 · **-2.2%** (n=203) |
| model fair beats price + public trusted | 212-216 · **-3.4%** (n=428) |
| PM says better than book + model fair beats price | 117-116 · **-4.3%** (n=233) |
| model fair beats price + line vs money 'against' + public trusted | 51-49 · **-4.4%** (n=100) |
| PM says better than book + public trusted | 265-214 · **-4.5%** (n=479) |

_combinations reaching n≥40: **34**_

## Does the best of them beat the search?

- cells at n≥40: **40**
- best: **model fair beats price + public edge true** at +3.7%
- biggest a price-redraw manufactures: median **+20.6%**, 95th pct **+35.3%**
- **corrected p = 1.000**

**Does not clear.** A scan this wide manufactures a cell this good often enough that the number is the width of the search.

- split-half of **model fair beats price + public edge true**: 59-67 · **-0.3%** (n=126) against 54-51 · **+8.6%** (n=105)

_Two halves of the same cell landing far apart means noise, whatever the pooled number says._

## How to read this

- `pm_quote` was the one worth hoping for: a second real-money market disagreeing with the sportsbook is not our model talking
- `projected` restates the stat model's deviation from the market in odds, and `divergence` already found that deviation anti-informative, so a poor showing there confirms rather than surprises
- nothing here changes the board.
