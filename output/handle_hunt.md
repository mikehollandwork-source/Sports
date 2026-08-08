# Hunting a WNBA handle source

_The consensus rule needs the DOLLAR majority, not just the ticket majority - handle-with-tickets returned +12.5%, handle-against -23.5%. Tickets alone are the losing half, so a WNBA board without handle would not be the same rule._

_A page is only useful if it carries COMPLEMENTARY percentage pairs (two numbers summing to ~100). A lone percentage could be anything._

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

_If no WNBA page carries complementary pairs alongside a money label, there is no handle source - and a 'WNBA board' would be the ticket half only, which is a DIFFERENT and historically losing rule, not the same one._