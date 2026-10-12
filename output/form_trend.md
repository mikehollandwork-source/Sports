# Does a RISING bat homer more than an elevated one? — 2026

_`hr_pick.form_factor` measures a level: a 15-game lump against the hitter's season. This asks whether DIRECTION adds anything, before a trend term is wired into the selector._

Windows: last 5 games against the 10 before them, both ending before the game predicted. Outcome: HR per PA in that next game. Permutation over hitters, 2000 draws.

**22505 hitter-games** from 427 hitters.

| split | rising HR/PA | falling HR/PA | gap | permutation p |
|---|---|---|---|---|
| combined (air × ISO)**0.5 ← primary | 3.364% (1216/36151) | 3.084% (1652/53569) | +0.280% | 0.0225 |
| air rate only | 3.287% (1453/44211) | 3.109% (1415/45509) | +0.177% | 0.1594 |
| ISO only | 3.376% (1237/36639) | 3.073% (1631/53081) | +0.304% | 0.0060 |

## Does the batted-ball trend predict a HIT?

_The five-game HIT-RATE form is a coin flip (AUC 0.5053) and was cut from the prop score. This is the other measurement - air rate and ISO, five games against the prior ten - the one that works for home runs. Whether it carries to hits is a separate question._

- rising: **62.3%** got a hit (8970 games)
- falling: **60.3%** got a hit (13546 games)
- gap **+2.0%**, permutation **p = 0.0025**
- **Real.** A trend requirement on props is justified.


## How to read this

- the primary test is the combined ratio; the other two are reported so a split-specific result is visible, not so the best one can be chosen after the fact
- a gap near zero means direction carries nothing beyond the level the selector already uses, and no trend term should be wired
- translate any gap into a multiplier before judging it: the selector already swings form ×1.30 and wind ×1.24, so a gap worth less than a percent or two cannot change a pick
