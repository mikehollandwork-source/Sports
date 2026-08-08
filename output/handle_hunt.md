# Hunting a WNBA handle source

_The consensus rule needs the DOLLAR majority, not just the ticket majority - handle-with-tickets returned +12.5%, handle-against -23.5%. Tickets alone are the losing half, so a WNBA board without handle would not be the same rule._

_A page is only useful if it carries COMPLEMENTARY percentage pairs (two numbers summing to ~100). A lone percentage could be anything._

_CAVEAT on the VSiN table below: the MLB control scores the same 3 pairs as WNBA, yet `_parse_vsin` extracts 15 rows from MLB and 0 from WNBA. So this metric does not detect VSiN's structure and its VSiN rows are uninformative - the parser result is the real signal._

## covers.com pages

| page | reached | money words | ticket words | pct pairs | complementary |
|---|---|---|---|---|---|
| wnba consensus | yes | `{'money': 35, 'handle': 13}` | `{'bets': 2, 'consensus': 183}` | 2 | **0** |
| wnba odds | yes | `{'money': 103, 'handle': 12}` | `{'bets': 444, 'consensus': 82}` | 2 | **0** |
| wnba matchups | yes | `{'money': 17, 'handle': 28}` | `{'bets': 7, 'consensus': 115}` | 70 | **24** |
| mlb consensus (control) | yes | `{'money': 47, 'handle': 13, 'cash': 1}` | `{'bets': 12, 'consensus': 468}` | 3 | **0** |

## VSiN URL variants

| url | reached | complementary pairs |
|---|---|---|
| `https://data.vsin.com/wnba/betting-splits/`  | yes | **3** |
| `https://data.vsin.com/basketball/betting-splits/?sport=wnba`  | yes | **3** |
| `https://data.vsin.com/betting-splits/?sport=wnba`  | yes | **3** |
| `https://data.vsin.com/wnba/betting-splits`  | yes | **3** |
| `https://data.vsin.com/mlb/betting-splits/` control | yes | **3** |

## Context around the complementary pairs

_Counting pairs is not enough - a bets/money split and two unrelated percentages look identical to a counter. This prints the surrounding text so the pairs can be identified, with MLB's matchups page alongside for shape comparison._

**WNBA matchups**

- `...0,.5),rgba(0,0,0,0))}.swiper-lazy-preloader{width:42px;height:42px;position:absolute;left:50%;top:50%;margin-left:-21px;margin-top:-21px;z-in...`
- `...dynamic,.swiper-vertical>.swiper-pagination-bullets.swiper-pagination-bullets-dynamic{top:50%;transform:translateY(-50%);width:8px}.swiper-pagination-vertical....`
- `...er-pagination-horizontal.swiper-pagination-bullets.swiper-pagination-bullets-dynamic{left:50%;transform:translateX(-50%);white-space:nowrap}.swiper-horizontal>...`
- `...r(--swiper-scrollbar-size,4px);height:calc(100% - 2 * var(--swiper-scrollbar-sides-offset,1%))}.swiper-scrollbar-drag{height:100%;width:100%;position:relative;background...`
- `...s ease infinite;animation:AnimationName 3s ease infinite}@-webkit-keyframes AnimationName{0%{background-position:99% 0}50%{background-position:2% 100%}100%{...`
- `...background-position:2% 100%}100%{background-position:99% 0}}@-moz-keyframes AnimationName{0%{background-position:99% 0}50%{background-position:2% 100%}100%{...`

**MLB matchups (control)**

- `...0,.5),rgba(0,0,0,0))}.swiper-lazy-preloader{width:42px;height:42px;position:absolute;left:50%;top:50%;margin-left:-21px;margin-top:-21px;z-in...`
- `...dynamic,.swiper-vertical>.swiper-pagination-bullets.swiper-pagination-bullets-dynamic{top:50%;transform:translateY(-50%);width:8px}.swiper-pagination-vertical....`
- `...er-pagination-horizontal.swiper-pagination-bullets.swiper-pagination-bullets-dynamic{left:50%;transform:translateX(-50%);white-space:nowrap}.swiper-horizontal>...`
- `...r(--swiper-scrollbar-size,4px);height:calc(100% - 2 * var(--swiper-scrollbar-sides-offset,1%))}.swiper-scrollbar-drag{height:100%;width:100%;position:relative;background...`
- `...s ease infinite;animation:AnimationName 3s ease infinite}@-webkit-keyframes AnimationName{0%{background-position:99% 0}50%{background-position:2% 100%}100%{...`
- `...background-position:2% 100%}100%{background-position:99% 0}}@-moz-keyframes AnimationName{0%{background-position:99% 0}50%{background-position:2% 100%}100%{...`

_If no WNBA page carries complementary pairs alongside a money label, there is no handle source - and a 'WNBA board' would be the ticket half only, which is a DIFFERENT and historically losing rule, not the same one._