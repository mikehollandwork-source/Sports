# Real money vs public tickets — who is right?

_PUBLIC = share of BETS (covers consensus, VSiN) — the Scores & Odds style headcount, dominated by small tickets. MONEY = cash at risk (Polymarket resting depth, Kalshi traded volume). The interesting games are where the headcount and the cash disagree._

## Coverage

- games with a clean public read and a price: **340**

_Baseline — backing the favourite in every one of these games: 187-153 (55%) · -23.3u · **-6.9%** (n=340)._

## Polymarket order book

- money and public agree: **93**
- disagree, money on the FAVOURITE: **11**
- disagree, money on the DOG: **50**

| case | back the MONEY side | back the PUBLIC side |
|---|---|---|
| they agree | 57-36 (61%) · +2.5u · **+2.7%** (n=93) | — |
| money on FAVOURITE, public on dog | 3-8 (27%) · -5.4u · **-49.4%** (n=11) _(thin)_ | 8-3 (73%) · +4.8u · **+43.4%** (n=11) _(thin)_ |
| money on DOG, public on favourite | 26-24 (52%) · +4.4u · **+8.7%** (n=50) | 24-26 (48%) · -8.2u · **-16.4%** (n=50) |

_Favourite win rate, money on favourite: **3/11 (27%)**._
_Favourite win rate, money on dog: **24/50 (48%)**._

## Kalshi traded volume

- money and public agree: **253**
- disagree, money on the FAVOURITE: **7**
- disagree, money on the DOG: **41**

| case | back the MONEY side | back the PUBLIC side |
|---|---|---|
| they agree | 146-107 (58%) · -2.0u · **-0.8%** (n=253) | — |
| money on FAVOURITE, public on dog | 3-4 (43%) · -1.7u · **-24.8%** (n=7) _(thin)_ | 4-3 (57%) · +0.8u · **+11.1%** (n=7) _(thin)_ |
| money on DOG, public on favourite | 14-27 (34%) · -10.7u · **-26.1%** (n=41) | 27-14 (66%) · +4.9u · **+12.0%** (n=41) |

_Favourite win rate, money on favourite: **3/7 (43%)**._
_Favourite win rate, money on dog: **27/41 (66%)**._

## Polymarket AND Kalshi agree with each other

- money and public agree: **74**
- disagree, money on the FAVOURITE: **0**
- disagree, money on the DOG: **10**

| case | back the MONEY side | back the PUBLIC side |
|---|---|---|
| they agree | 45-29 (61%) · +0.6u · **+0.8%** (n=74) | — |
| money on FAVOURITE, public on dog | — | — |
| money on DOG, public on favourite | 4-6 (40%) · -1.3u · **-12.8%** (n=10) _(thin)_ | 6-4 (60%) · +0.4u · **+4.2%** (n=10) _(thin)_ |

_Favourite win rate, money on dog: **6/10 (60%)**._

## Controls on the disagreement cells

_Kalshi is used here because it has the widest coverage. Both directions get controls, so a good-looking cell cannot be reported without its holdout and CI._

_money on favourite → back the money: n=7, too thin for controls._

**Controls — money on dog → back the money**

- in-sample: **-42.4%** (n=26) · holdout: **+2.1%** (n=15)
- market-calibrated null: **p = 0.894**
- day-block bootstrap 95% CI: **-56.6% to -1.5%**

**Controls — money on dog → back the public favourite**

- in-sample: **+25.1%** (n=26) · holdout: **-10.8%** (n=15)
- market-calibrated null: **p = 0.109**
- day-block bootstrap 95% CI: **-7.4% to +35.8%**

_A cell only becomes a rule if it survives its holdout and its CI clears zero. Two disagreement directions x three venues is six chances to find a good-looking number by accident._