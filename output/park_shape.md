# Does a park's SHAPE add to its home-run factor?

_`hr_pick` already multiplies by a park HR factor, but that is one number for the whole field and cannot express a left-handed pull hitter walking into a short right field. Within-hitter: each bat's own rate at short-pull-side parks against his own rate at long ones._

_MLB's feed carries no batted-ball distance or coordinates, so this tests the cheap proxy - pull side from which way he bats. If the cheap version is worth nothing, a Statcast spray profile almost certainly is too._

**288 hitters**, 133149 plate appearances.

| pull-side fence | HR/PA | HR | PA |
|---|---|---|---|
| short (below median) | 3.314% | 2318 | 69936 |
| long | 3.112% | 1967 | 63213 |

difference **+0.203%** per PA — a multiplier of **×1.065** — permutation p = **0.1234**

### Controlled for the park HR factor the model already applies

- short 3.279% vs long 3.157% per park-adjusted PA
- difference **+0.122%**, multiplier **×1.039**, permutation p = **0.3583**
- _if this collapses toward zero, the aggregate park factor already contains the shape and there is nothing to add_

- left-handed bats (131): raw -0.036%, park-controlled -0.145% per PA
- right-handed bats (157): raw +0.427%, park-controlled +0.371% per PA

## Has he gone deep at THIS park before?

_Conditioning on a past outcome, so both confounds are controlled: matched on prior plate appearances at the park, and scored against the hitter's OWN rate so it is a power hitter against himself._

| prior PA at the park | never homered here | has homered here |
|---|---|---|
| 10-25 PA | -0.235% (11442 PA) | -0.278% (6496 PA) |
| 25-50 PA | -0.313% (3892 PA) | +0.082% (5563 PA) |
| 50+ PA | +0.594% (4177 PA) | +0.080% (51430 PA) |

Pooled gap **+0.117%** per PA above each hitter's own rate — about **×1.039** on a league HR rate.

## What to conclude

- compare the multiplier against what the selector already swings: form ×1.30, wind ×1.24, park ×1.12. A shape term below about ×1.03 cannot change a pick and should not be wired
- a null here also closes the expensive version, since a real spray profile refines the same effect this proxy is testing
