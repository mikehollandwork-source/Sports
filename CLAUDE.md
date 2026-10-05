# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## Project-Specific Instructions

### Project Overview

**MLB Public-vs-Stats Edge Finder.** A Python tool that, for each MLB game on a
given day, flags the team that the betting public is *not* on but which holds the
statistical advantage over the last 5 games — and writes those teams to a daily
JSON file (`output/picks_<date>.json`).

- **Language / runtime:** Python 3.11
- **Dependencies:** `requests`, `beautifulsoup4` (see `requirements.txt`)
- **Data sources:** official MLB Stats API (`statsapi.mlb.com`, schedule + last-5
  player stats) and covers.com (public consensus % + forum-post tally).
- **Runtime target:** GitHub Actions (full internet). The dev sandbox firewalls
  covers.com and the MLB API, so live fetching cannot be tested locally there —
  the first Actions run is the real integration test.

### Repository Structure

```
src/
  mlb_api.py   # MLB Stats API: schedule, rosters, last-5 game logs
  covers.py    # covers.com: consensus % + forum-post tally (selectors UNVERIFIED)
  analysis.py  # "statistical advantage" metric + public-vs-stats decision
  main.py      # orchestration; writes output/picks_<date>.json
.github/workflows/daily.yml   # manual + daily run; commits results back
output/        # generated picks_<date>.json files
```

### Common Commands

```bash
pip install -r requirements.txt        # setup
python -m src.main --date 2026-06-23    # run (omit --date for today, US/Eastern)
python -m py_compile src/*.py           # quick compile check
```

There is no test suite yet. The `analysis.py` decision logic is pure and easily
unit-testable with mock `Game`/`Team` objects.

### Key conventions & gotchas

- **covers.com selectors are best-effort and unverified** — they will likely need
  tweaking after the first live run. All covers parsers fail *soft* (log a warning,
  return empty) so MLB-stats analysis still produces output.
- **The advantage metric is documented in `src/analysis.py`** (and the README) and
  is meant to be tuned. All weights, league baselines, and the wOBA/FIP constants
  live at the top of `analysis.py` — keep the formula in one place. It is
  last-5-only, league-relative, additive: `offense_index + pitching_index`, where
  offense blends park-neutralized wOBA/ISO/discipline/speed with a platoon tilt and
  pitching is starter+bullpen FIP. Both sides are strength-of-schedule adjusted.
  `park_factors.py` holds the static park table; `strength.py` fetches opponent
  season win%/wOBA/FIP (cached) and `analysis.opp_*_factor` turn them into clamped
  multipliers.
- **Win condition** (`win_condition` in `analysis.py`): per-matchup `runs_to_win`
  and `runs_to_allow` bars, back-tested over the team's last 5 games (each re-rated
  by opponent strength) into counts of scored_target / held_under_ceiling /
  complete_win_condition / actually_won / out_hit. Reporting only — it does not
  change the flagged pick. `team_last5_gamelog` supplies the per-game data.
- Match the existing defensive style: degrade gracefully on network/parse errors;
  never let one game's failure abort the whole run.
- **Watch tags (`good_dog.py`, `line_money.py`) change no pick and must stay out
  of the ledger.** `record_audit` asserts the invariant for both. Their
  thresholds are PRE-REGISTERED (`FAV_RATE`; `MOVE_MIN` and `STRONG`) and must
  not be re-tuned against the forward record they are accumulating — that would
  re-create the selection bias the tags exist to escape. `line_money.SHIPPED`
  marks where forward evidence starts; boards before it are the selection data
  and are deliberately excluded from the tag's record.
- **Kalshi markets are chosen per GAME, not per team pair** (`kalshi.game_market_index`
  + `kalshi.pick`). A pair can have several OPEN events at once — tonight's game and
  last night's, which Kalshi leaves open until it settles, or both halves of a
  doubleheader — so the old pair-keyed index kept whichever paginated last. That put
  the wrong event on 97 logged entries, and 38 of 100 such entries opened on an
  already-DECIDED market (mid ≤ 0.05 or ≥ 0.95) against 0 of 704 correct ones. The
  ticker carries its own start in EASTERN time (`kalshi.event_start`), so validity is
  checkable offline. **Those 97 entries are marked `k_ticker_stale: true` and their
  `k_readings` must be skipped — the readings are another game's and cannot be
  repaired.** Affects `venue_signal`, `venue_cross`, `venue_swap`, `best_execution`,
  `signal_sweep2`, `triple_check`; none of them filters on the flag yet.
- **Pitch-type matchups were measured and REJECTED on size, not on principle**
  (`pitchmix_stability.py`, `output/pitchmix_stability.md`). The data does exist:
  `statSplits` serves none of the pitch-type sitCodes, but `playLog` carries pitch
  type, outcome, `pitchHand` and `batSide` on every plate appearance, and
  `pitchArsenal` gives a pitcher's usage mix. Only the FASTBALL family carries
  signal — breaking p=0.22, offspeed p=0.72 — and the fastball tilt replicates
  out-of-sample twice (2025→2026 r=+0.145 p=0.038; half-A→half-B r=+0.141
  p=0.026, Fisher p=0.0078 against a six-test Bonferroni bar of 0.0083). But its
  full achievable effect is **×0.991 to ×1.010**, where form reaches ×1.30 and
  wind ×1.24, so it cannot change a selection. A pitcher's HR-by-family is stable
  (fastball r=+0.248) yet unusable alone: his own mix times his own by-family
  rates is just his overall rate, so it only enters through the weak hitter side.
  **It ships as CONTEXT instead** (`pitch_mix.py`): the board prints the starter's
  fastball share, the hitter's fastball tilt and the multiplier that is *not*
  applied, and `record_audit.pitch_mix_guard` bounds-checks that it never would
  have changed a pick (leader gets his own multiplier, runner-up gets the ceiling
  `MAX_MULT`). `main._attach_hr_prop` calls it AFTER the hitter is chosen, so it
  cannot reorder candidates by construction — keep it there. `TILT_SLOPE` and
  `LEAGUE_FASTBALL_SHARE` are PRE-REGISTERED from the measurement and must not be
  re-fitted against the forward record the field is accumulating.
- **The HR selector has BOTH a level and a trend term, and they are different
  things.** `form_factor` compares a 15-game lump against the hitter's season —
  a LEVEL, which cannot tell a bat hot in games 1-10 and cold in 11-15 from the
  reverse. `trend_factor` adds direction: last 5 games against the prior 10, on
  air share and ISO. Measured in `form_trend.py` over 22,361 hitter-games from
  419 hitters, both windows ending BEFORE the game predicted — rising bats homer
  at 3.369% per PA against 3.085% falling (pooled 3.200%), permutation p=0.0215
  on the pre-registered primary split, permuted BY HITTER since a hitter's games
  share his park and slot. `TREND_UP`/`TREND_DOWN` are those rates over the
  pooled rate: derived, not fitted, and PRE-REGISTERED. The two terms are nearly
  independent (r=+0.132), so multiplying both is not double-counting. **Known
  gaps, both deliberate:** the split is 5-vs-10 rather than "the last couple
  games" because 3 games is ~12 PA where one double swings a slash line hundreds
  of points; and an earlier window with ISO 0 has no ratio, stays neutral, and so
  the sharpest slump-recovery cases are missed (3.7% of rows, ~41 HR — too few to
  support a rule). **Recorded for forward confirmation, NOT built in:** almost
  all the effect sits where the 15-game level is depressed (×1.147, p=0.0085)
  rather than elevated (×1.039, p=0.476) — coming out of a slump, not already
  hot. That is a post-hoc subgroup of an already-significant primary, so it is
  being watched rather than baked in. The air-rate trend alone is NULL (p=0.149);
  ISO alone carries it (p=0.0060), so "rising without hits" is specifically the
  half that does not work.
- **No hits prop on a hitter whose nights tend to end early** (`pinch_risk.py`,
  `props.SHORT_NIGHT_MAX`). A prop needs plate appearances; a hitter lifted in
  the sixth got two. `props.MIN_AVG_PA` cannot catch it — a mean over team wins
  stays near 4.0 for a hitter lifted in a quarter of his starts.
  **WHICH measure was decided by forward test, not assumption** — 32,989
  out-of-sample starts, each measure built from PRIOR starts only and scored by
  AUC against whether that night actually ran short:
  recent-30 short rate shrunk toward season **0.762** > mean PA per start 0.757
  > season short rate 0.755 > costly pulls 0.715 > **counting pulls 0.681**.
  Counting pinch hits — the first thing shipped — came LAST, because it cannot
  tell a ninth-inning defensive sub from a fifth-inning pinch hit. The winner's
  edge over mean-PA held in 100% of a hitter-level bootstrap, CI [+0.0010,
  +0.0093]. A start is "short" at `SHORT_PA = 3` (17.9% of starts; PA≤4 is 73%,
  too common to be a signal).
  The underlying pull detection is still read off the BOXSCORE — a starter's
  `battingOrder` ends in `00`, a replacement gets the next number up with
  `isSubstitute` true (`gamesStarted` is not served for hitters) — but the cache
  now stores per-start rows `[date, PA, pulled, opp starter]`, not a running
  count, which is what made the bake-off possible. `main` calls
  `pinch_risk.refresh(date)` before props: one boxscore per newly finished game.
  `SHORT_NIGHT_MAX = 0.23` is the LEAGUE MEDIAN of that measure (p25 9.3%, p75
  41.4%), set from the distribution BEFORE our record was consulted. The window
  is narrow and it sits inside: clears Bogaerts 19.0% (everyday), catches Thomas
  28.3% and Murphy 34.3% (both lifted 2026-10-04); Albies 11.5%, Olson 13.9%,
  Harris 13.0%, Acuña 3.6% pass. The retrospective is directional ONLY and is
  not the justification — blocked props 11-10 vs 80-42 allowed, n=21, p=0.246.
  **Under `MIN_STARTS` returns None and is LET THROUGH** — unknown is not risky,
  and a feed outage must not silently empty the board.
  `record_audit.pull_gate_guard` asserts it from the boards. The HR PICK is
  deliberately exempt and only reports its rate: a home run needs one plate
  appearance, not four. NOTE Gavin Sheets sits at 48.5%, so that exemption is
  load-bearing, not theoretical.
- **Any backtest reading `pm_books` / `kalshi_books` must cut readings at first
  pitch minus `LOCK_LEAD`.** Those logs run through the game and past
  settlement, so a losing side's last reading is `0.00/1.00`. `consensus.book_metrics`
  now cuts for you; anything that walks `readings` itself must do the same, or its
  "drift" reports the winner instead of the money. Measured cost of getting this
  wrong: +9.9% against -5.0% on the same 714 games.

### Git & Branching

- Develop changes on a feature branch; do not commit directly to the default branch.
- Use clear, descriptive commit messages.
- Push with `git push -u origin <branch-name>`.
- Open a pull request only when explicitly requested.
