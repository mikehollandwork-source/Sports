# Do the stat signals separate winning fades from losing ones?

_ev_model showed these add nothing on top of the price across all games. The fade is a different population - games where the rule changed its mind - so it is worth testing rather than assuming._

- fades reconstructed with an outcome: **143**
- pooled: **73-70 · +16.4% (n=143)**

## Each stat, split at its median

_Every feature is signed TOWARD the side the fade backs, so "favours the fade" means the stat likes the team we are buying._

| stat | favours the fade | favours the other side |
|---|---|---|
| `bvp` | 40-30 · +24.9% (n=70) | 33-40 · +8.2% (n=73) |
| `pen` | 39-32 · +21.3% (n=71) | 34-38 · +11.5% (n=72) |
| `margin` | 38-33 · +15.7% (n=71) | 35-37 · +17.1% (n=72) |
| `form` | 36-35 · +16.5% (n=71) | 37-35 · +16.3% (n=72) |
| `consistency` | 37-33 · +21.6% (n=70) | 36-37 · +11.4% (n=73) |
| `park` | 35-36 · +11.2% (n=71) | 38-34 · +21.6% (n=72) |
| `record` | 38-33 · +14.2% (n=71) | 35-37 · +18.5% (n=72) |

## Does the best split beat the search?

- splits at n≥25: **14**
- best: `bvp high` at **+24.9%** (n=70)
- median best-in-noise: **+15.1%**
- **corrected p = 0.184**

**Does not clear.**

## The powered version — log-loss on every fade

_ROI on a subset is dominated by which coin flips landed. Log-loss scores the probability assigned to what actually happened on every fade, so it is informative at this sample._

- trained on fades before **2026-08-24** (**85**), scored on **58** after

_Every fade postdates the MLB holdout date, since the consensus rule went live after it. So this splits the fade population on its own median date instead._

| model | holdout log-loss |
|---|---|
| price only | 0.6997 |
| price + all stats | **0.7482** |

- stats change holdout log-loss by **-0.0485**
- 95% CI: **-0.1264 to +0.0301**
- weights: `bvp` -0.236, `pen` +0.013, `margin` -0.051, `form` +0.599, `consistency` -0.275, `park` -0.163, `record` -0.002

**No information beyond the price.** On the fade population too, everything we track is already in the number.
