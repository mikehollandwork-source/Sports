# Which withdrawals does the fade rule live on, and do they still happen?

_First, a correction to my own guess: `fade_profile` is **not** contaminated by the look-ahead fixed on 2026-09-29. It reads `pick_criteria` out of committed board versions, and those boards were built live, when the day file held only pre-game readings. The look-ahead only affected backtests that recompute `book_metrics` on a completed file._

_The real problem is larger. The book-confirm gate was REMOVED from the live rule, and a fade is triggered by a withdrawal — so two of the five withdrawal reasons (`no order-book read` and `book did not confirm`) can no longer occur. However the fade rule performed, its forward population is a different population._

_The reason is read, not recomputed: `reject_reason()` is written into every stay-away game at board time, so the version immediately after a withdrawal records which gate stopped passing, as judged live._

- withdrawals reconstructed with an outcome: **0**

Too few withdrawals to judge.
