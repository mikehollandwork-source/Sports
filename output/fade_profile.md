# Fade profile — which withdrawals are worth fading?

_The fade is live. Pooled it returned +12.8% with a CI spanning zero, and slicing by reason (p=0.984) and reason x price (p=0.901) found no pocket. These are the two directions not yet tried._

- withdrawn picks reconstructed with an outcome: **144**
- pooled fade: **74-70 · +15.2% (n=144)**

## By how long the pick survived before being dropped

_A pick that flickered for one refresh was marginal all along; one that stood all afternoon and then died is the market changing its mind._

| board versions as a pick | fading it |
|---|---|
| 1 (flicker) | 22-19 · +15.8% (n=41) |
| 2-3 | 18-24 · -3.7% (n=42) |
| 4+ (sustained) | 34-27 · +27.9% (n=61) |

## By how late the withdrawal came

_Late withdrawals follow late money, which is the informed kind._

| hours before first pitch | fading it |
|---|---|
| > 6h out | 24-24 · +11.1% (n=48) |
| 2-6h out | 27-23 · +20.7% (n=50) |
| < 2h out (late) | 23-23 · +13.5% (n=46) |

## Did it come back?

_A pick that oscillates is sitting exactly on a threshold, and a threshold coin-flip is not a signal in either direction._

| | fading it |
|---|---|
| withdrawn and stayed out | 74-70 · +15.2% (n=144) |
| withdrawn then re-added | — |

## Can this be dialled in? The split-half test

_Rank the categories by first-half fade ROI, then back only the top ones in the second half. If the winners stay winners, dialling in is possible. If not, no further slicing will help._

| category | first half | second half |
|---|---|---|
| versions 4+ (sustained) | +32.3% (n=49) | +9.8% (n=12) |
| lead 2-6h out | +24.0% (n=28) | +16.5% (n=22) |
| lead < 2h out (late) | +14.1% (n=32) | +12.3% (n=14) |
| readded stayed out | +11.2% (n=86) | +21.1% (n=58) |
| versions 1 (flicker) | +5.2% (n=19) | +24.8% (n=22) |
| lead > 6h out | -6.2% (n=26) | +31.4% (n=22) |
| versions 2-3 | -39.9% (n=18) | +23.4% (n=24) |

- correlation between halves across 7 categories: **r = -0.64**
- backing the top half of categories in the second half: **25-23 · +13.6% (n=48)**
- the whole pooled fade in the second half: **32-26 · +21.1% (n=58)**

**Dialling in does not work.** A category's first-half record says little or nothing about its second, so picking the good ones is picking noise. The pooled fade, which selects nothing, remains the right version to run.
