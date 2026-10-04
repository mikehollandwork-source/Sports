# Is home-run tilt by pitch family stable? — 2025 vs 2026

_Measured before the pitch-mix term is built, because one probe already showed a hitter whose family ordering reversed between seasons._

tilt = (share of HR on the family) − (share of PA-ending pitches on it). Needs 150+ PA and 5+ HR in a season. p from 2000 permutations.

## Hitters

**Split-half within 2026 (alternating games) — the reliability CEILING**

| family | n | r | permutation p |
|---|---|---|---|
| fastball | 251 | +0.121 | 0.050 |
| breaking | 251 | +0.051 | 0.425 |
| offspeed | 251 | +0.062 | 0.362 |

**2025 tilt vs 2026 tilt — does it carry forward?**

| family | n | r | permutation p |
|---|---|---|---|
| fastball | 210 | +0.111 | 0.101 |
| breaking | 210 | +0.047 | 0.492 |
| offspeed | 210 | +0.123 | 0.086 |

### Would 2025's fastball tilt have helped in 2026?

| 2025 fastball tilt | n | 2026 fastball HR% − own overall |
|---|---|---|
| lowest (-0.399 to -0.059) | 52 | -0.068%  (401 HR / 13977 PA) |
| 2nd (-0.057 to +0.018) | 52 | +0.129%  (545 HR / 15239 PA) |
| 3rd (+0.019 to +0.119) | 52 | +0.194%  (547 HR / 14025 PA) |
| highest (+0.122 to +0.364) | 54 | +0.310%  (595 HR / 15773 PA) |

## Pitchers (HR allowed)

**Split-half within 2026 (alternating games)**

| family | n | r | permutation p |
|---|---|---|---|
| fastball | 209 | +0.139 | 0.053 |
| breaking | 209 | +0.142 ** | 0.037 |
| offspeed | 209 | +0.089 | 0.209 |

**2025 vs 2026**

| family | n | r | permutation p |
|---|---|---|---|
| fastball | 174 | +0.248 ** | 0.002 |
| breaking | 174 | +0.140 | 0.060 |
| offspeed | 174 | +0.221 ** | 0.003 |

## How big is it, though?

_A p-value says the signal exists. This says whether it is worth wiring, on the same scale as the factors already in the selector._

slope +0.0087 per unit tilt (n=251) · hitter fastball tilt p10 -0.148 / p90 +0.218 · starter fastball share p10 41% / mean 56% / p90 72%

| hitter | starter | multiplier on HR rate |
|---|---|---|
| p90 fastball tilt | p90 fastball share | ×1.0097 |
| p90 fastball tilt | p10 fastball share | ×0.9906 |
| p10 fastball tilt | p90 fastball share | ×0.9934 |
| p10 fastball tilt | p10 fastball share | ×1.0064 |

**Full achievable range ×0.991 to ×1.010** — a 1.9% spread, and only between the extremes of both distributions.

For scale, the factors the selector already applies: form up to ×1.30, win probability ×1.27, wind ×1.24, park ×1.12, temperature ×1.08, opposing pitching ×1.05.

## How to read this

- split-half r near zero means the season cannot agree with itself, so nothing carries forward by construction and the term must not be built
- a split-half r that is clearly positive while the year-over-year r is not means the tilt is real within a season but does not persist - usable only from the CURRENT season, never from last year's
- the quartile table is the one that matters: if the highest group does not out-homer the lowest on fastballs, last year's tilt is not information
- a pitcher's MIX is stable regardless; it is his HR-by-family that is being questioned here
