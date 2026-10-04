# Does a RISING bat homer more than an elevated one? — 2026

_`hr_pick.form_factor` measures a level: a 15-game lump against the hitter's season. This asks whether DIRECTION adds anything, before a trend term is wired into the selector._

Windows: last 5 games against the 10 before them, both ending before the game predicted. Outcome: HR per PA in that next game. Permutation over hitters, 2000 draws.

**22361 hitter-games** from 419 hitters.

| split | rising HR/PA | falling HR/PA | gap | permutation p |
|---|---|---|---|---|
| combined (air × ISO)**0.5 ← primary | 3.369% (1213/36008) | 3.085% (1642/53224) | +0.284% | 0.0215 |
| air rate only | 3.290% (1448/44009) | 3.111% (1407/45223) | +0.179% | 0.1489 |
| ISO only | 3.384% (1234/36468) | 3.072% (1621/52764) | +0.312% | 0.0060 |

## How to read this

- the primary test is the combined ratio; the other two are reported so a split-specific result is visible, not so the best one can be chosen after the fact
- a gap near zero means direction carries nothing beyond the level the selector already uses, and no trend term should be wired
- translate any gap into a multiplier before judging it: the selector already swings form ×1.30 and wind ×1.24, so a gap worth less than a percent or two cannot change a pick
