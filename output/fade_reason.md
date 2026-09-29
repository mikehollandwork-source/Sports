# Which withdrawals does the fade rule live on, and do they still happen?

_First, a correction to my own guess: `fade_profile` is **not** contaminated by the look-ahead fixed on 2026-09-29. It reads `pick_criteria` out of committed board versions, and those boards were built live, when the day file held only pre-game readings. The look-ahead only affected backtests that recompute `book_metrics` on a completed file._

_The real problem is larger. The book-confirm gate was REMOVED from the live rule, and a fade is triggered by a withdrawal — so two of the five withdrawal reasons (`no order-book read` and `book did not confirm`) can no longer occur. However the fade rule performed, its forward population is a different population._

_The reason is read, not recomputed: `reject_reason()` is written into every stay-away game at board time, so the version immediately after a withdrawal records which gate stopped passing, as judged live._

- withdrawals reconstructed with an outcome: **145**

## By the gate that caused the withdrawal

| withdrawal reason | still possible? | fading it | 95% CI |
|---|---|---|---|
| line moved wrong way | yes | 31-35 · **+11.7%** (n=66) | -22.0% to +43.9% |
| book did not confirm | **NO — gate removed** | 26-23 · **+13.2%** (n=49) | -10.7% to +38.8% |
| handle/ticket | yes | 17-12 · **+26.6%** (n=29) | -9.9% to +57.6% |
| other/unrecorded | yes | 0-1 · **-100.0%** (n=1) | — |

## The split that decides it

| population | fading it | 95% CI |
|---|---|---|
| withdrawals that STILL happen | 48-48 · **+15.0%** (n=96) | -12.3% to +41.4% |
| withdrawals that can no longer happen | 26-23 · **+13.2%** (n=49) | -10.7% to +38.8% |

- **34% of the fade rule's historical triggers came from the book gate**, which no longer exists

- so the forward-relevant record is **48-48 · **+15.0%** (n=96)**, not the pooled **74-71 · **+14.4%** (n=145)** the rule was shipped on

## The call

- the surviving population returns **+15.0%** with an interval of -12.3% to +41.4%, which spans zero. The fade rule is then running on evidence that no longer describes its input, and the honest options are to restrict it to the reasons that still occur and re-baseline the expectation, or to pause it until the new population has a record of its own

- either way the historical pooled figure should stop being quoted for it: a third of its triggers are gone
