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

### Operating it from a sandbox session

The dev sandbox firewalls covers.com and the MLB API, so **nothing live can be
tested here** — every real run is a GitHub Actions dispatch, and the committed
`output/` is how you read the result back.

```bash
# launch a board (this is "launch a fresh board")
gh api -X POST repos/mikehollandwork-source/Sports/actions/workflows/daily.yml/dispatches \
  -f ref=claude/claude-md-docs-jx2xtz
# then poll, then: git pull --rebase, and render
python -c "import json,sys; sys.path.insert(0,'.'); from src import main as m; \
  print(m.telegram_text(json.load(open('output/picks_<date>.json'))))"
```

**`gh api` CANNOT fetch Actions logs.** The endpoint 302s to
`productionresultssa*.blob.core.windows.net` and this client refuses redirects
off api.github.com, so a run's stdout is unreadable from here. Diagnose from
what the run COMMITTED instead — `output/picks_<date>.json`,
`output/source_health_<date>.md`, `output/covers_diag.md` — and if something
needs to be visible that currently only logs, write it to `output/`.

Schedules, all US/Eastern: `daily.yml` fires once at **11:00am**; `pregame.yml`
("Board refresh") hourly from **noon to 1:00am**, each kick running a ~4.75h
loop that also wakes at a game's lock. So an EARLY (1:05pm) game has only the
11am and noon runs before first pitch — dispatch manually if its lineup matters.
Other workflows worth knowing: `parlay_paper.yml` (builds/settles the paper
ticket, runs after the board), `covers_diag.yml` (dumps what covers.com
actually returned, for an outage), `source_health.yml`.

Secrets live in Actions (`THE_ODDS_API_KEY`, `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHAT_ID`, `REDDIT_*`) and are never echoed.

### Key conventions & gotchas

- **covers.com selectors are best-effort and unverified** — they will likely need
  tweaking after the first live run. All covers parsers fail *soft* (log a warning,
  return empty) so MLB-stats analysis still produces output.
- **Any covers↔MLB team match MUST go through `analysis._canon_abbr`.** The two
  disagree on eight clubs (covers: Chw, Sdp, Sfg, Tbr, Kcr, Az, Was/Wsn — MLB:
  CWS, SD, SF, TB, KC, ARI, WSH). `find_slate_line` canonicalised; `_name_hit`
  did not, so `_match_consensus` silently dropped the covers row for every game
  involving one of those teams. Measured cost before the fix: consensus missing
  on **36% of the 447 games involving an aliased club against 8% elsewhere** —
  roughly 125 games that lost their ticket % and handle read all season. It
  surfaced on 2026-10-08 when a one-game slate of Cle @ Chw reported "covers
  tickets 0/1" and the board posted no play; `source_health` correctly called it
  an outage while the fetch and the selectors had been fine throughout. The
  nickname fallback cannot cover for this — it takes the LAST word of the team
  name, so Chicago White Sox hunts for "sox" among abbreviations, and it is
  ambiguous between the two Sox anyway.
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
- **Do NOT add a "but he's red hot" override to the short-night gate.** It was
  measured over 32,564 starts (`short_night_form.py`,
  `output/short_night_form.md`) and the answer is no, for a blunter reason than
  "not quite enough": **hot form barely predicts a hit at all.** Form as the
  board defines it (last `props.RECENT_GAMES` games minus season, in points)
  scores **AUC 0.5053** against getting a hit — a coin flip — and P(1+ hit) is
  FLAT across the whole range: −20 or worse 64.0%, −10 to 0 64.4%, +10 to +20
  65.3%, +30 or more 64.9%. The hot hand is not there. Meanwhile the gate is
  worth +8.1 points (allowed 64.0% vs blocked 55.9%), and the hottest blocked
  band reaches only 58.2% ± 3.4%, whose interval does not touch 64.0%. So no
  form level buys back the lost plate appearances, and the gate stays absolute.
  **Corollary worth acting on separately:** `main._prop_score` weights that same
  near-inert `form` term, so it is contributing noise to which prop gets picked.
  Short-night rate itself is only AUC 0.5467 — weak but real, and the strongest
  of the two.
- **Batted-ball distance, park SHAPE and "has he homered here" were all tested
  for the HR pick and all came back empty** (`spray_probe.py`,
  `park_shape.py`, `output/park_shape.md`).
  **Distance/spray is not in MLB's feed at all** — a play record carries only
  atBatNumber, count, details, isPitch, pitchNumber, playId, with no `hitData`,
  so average fly-ball length and landing spot cannot come from there. Statcast
  DOES serve it and IS reachable (`baseballsavant` CSV: `hc_x`, `hc_y`,
  `hit_distance_sc`, `avg_hr_distance`, `brl_percent`) if ever needed.
  **Park fence distances ARE available** — `/venues?hydrate=fieldInfo` for all
  62 parks (leftLine, left, leftCenter, center, rightCenter, right, rightLine).
  But shape adds nothing to the HR factor already applied: within-hitter, a
  short pull-side fence is worth ×1.065 raw (p=0.1234) and only **×1.039
  (p=0.3583)** once exposure is weighted by the existing park factor — and the
  sign flips by handedness (RHB +0.371%, **LHB −0.145%**), which no real
  short-fence mechanism would do. That asymmetry is the tell that it was
  confounding, since hitter-friendly parks tend to have short fences.
  By the module's pre-registered logic a null here also closes the expensive
  Statcast version, which refines the same effect; the handedness proxy is
  admittedly crude, but the headroom left after the park factor is ×1.039, so
  the ceiling is low either way.
  **"Homered here before" is Simpson's paradox** — pooled +0.117% looks like
  ×1.039, but matched on prior PA at the park the signs alternate (10–25 PA
  −0.04%, 25–50 PA +0.40%, 50+ PA **−0.51%**) and the largest, best-matched
  bucket runs the wrong way. Nothing survives controlling for how often he has
  batted there and for his own power.
- **A POSTPONED game reads as `Final` in MLB's abstract state, and settling on
  that books losses on games that were never played** (`mlb_api._played`,
  `_state`, `results_for`). MLB serves a rained-out game as
  `abstractGameState: "Final"` with `detailedState: "Postponed"`,
  `codedGameState: "D"` and both scores `None` — the game is over as far as
  THAT DATE's schedule goes. `final = abstract == "Final"` therefore called it
  played, and `final` is the gate every settler keys on
  (`prop_grade`, `grade`, `parlay_paper`). The boxscore of an unplayed game has
  nobody batting, so `player_hits` returns 0, which reads as no hit and books a
  **LOSS**.
  **Measured cost: 4 ledger entries, and one of them is the opposite of the
  truth.** 2026-10-16 Rays @ Guardians was postponed for rain and Chandler
  Simpson (−216) and Chase DeLauter (−194) were each booked −1.00u on a game
  that did not happen. 2026-07-27 game 824490 was listed on that date, graded
  while postponed, then played on 07-28 where **Elly De La Cruz went 2-for-4** —
  the stale **L** stood because `grade._add` is idempotent per key and the
  makeup date's board carried no prop, so nothing ever looked again. (Its
  paired entry in the retired parlay book also reads L, which is the right
  answer by accident: the Reds ML leg genuinely lost 5–6.)
  The fix is at the source so every settler inherits it: `_played()` reads
  `detailedState`, `postponed` is its own state, and `final` now means PLAYED
  rather than merely off the schedule. Two downstream spots needed the same
  idea: `grade._all_games_final` counts a postponed game as DONE or the recap
  would wait on it forever, and `telegram_text` prints
  `— POSTPONED` instead of the locked props, because those props were chosen
  while the game was still going ahead and printing them offers a bet that
  cannot be placed.
  **CONFIRMED END TO END IN PRODUCTION.** Game 849817 was made up on
  **2026-10-18**, got its own board, locked its own props and settled them
  against a real boxscore — DeLauter +0.51, Díaz +0.43, Simpson +0.50, all
  against `Tampa Bay Rays 3 @ Cleveland Guardians 1`. So the makeup date
  grades normally and the voided 10-16 rows stayed voided through it. Nothing
  here needs re-investigating.
- **Any cross-feed PLAYER match MUST go through `prop_odds.fold_name`** — the
  player-name counterpart of the `analysis._canon_abbr` rule above, and it bit
  the same way. The Odds API and MLB disagree on accents **in both
  directions**: the feed served `jose ramirez` where MLB says `José Ramírez`,
  and served `agustín ramírez` alongside `ronald acuna jr.` for a man MLB
  spells `Acuña`. So neither side is canonical and a bare `.lower()` misses
  whichever way the pair happens to fall. **32 of 499 cached names (6.4%)
  cannot match on `.lower()`** — every accent, every `J.P.`/`A.J.`, every
  `max muncy (2002)` disambiguator. `fold_name` is NFKD, drop combining marks,
  strip parentheticals, collapse punctuation; `_row_for` tries the exact key
  first so caches already on disk match unchanged.
  Measured cost on 2026-10-13: José Ramírez's real **−193** (break-even 65.9%)
  sat in the cache under `jose ramirez`, the lookup missed it, the prop fell
  back to the assumed −200 (66.67%) and a **66.3%** read was withheld by four
  tenths of a point against a price no book was offering. Settlement is SAFE —
  `player_hits`, `player_total_bases`, `pitcher_strikeouts` and `prop_grade`
  all key on `player_id`, so nothing was ever mis-graded. The name path is used
  by `prop_odds` (all five lookups), `parlay_paper._pick_over`,
  `prop_price_drift` and `prop_rule_scan`; the last two silently dropped every
  accented hitter from their samples.
  `record_audit.price_match_guard` asserts it from the files, and it asserts
  the PRICE rather than the name on purpose: a guard that folded both sides
  itself would pass with the folding lookup removed.
- **An ASSUMED price must never withhold a prop** (`main._prop_withheld`). The
  gate's own rule is that the bar IS the price — so with no quote there is no
  bar, and holding a bet against a number no book published is the gate
  inventing the opinion it exists not to invent. `prop_grade.PROP_PRICE` is the
  ledger's ROI placeholder, not an offer, and it sits exactly where it does the
  most damage: −200 demands 66.67% while the reads cluster in the low 60s, so
  the fallback withheld nearly everything it touched (4 of the 6 withholds on
  the boards then on disk). An unpriced prop now POSTS, graded at the assumed
  price as it always was, and the board prints `-200 assumed` rather than
  `no line` so the number is visible where it is used. A REAL quote under its
  break-even still withholds, unchanged.
- **The board-changed test must look at PROPS, not just picks**
  (`pregame._board_state`). It compared `picks` and `coin_flips` only, and the
  board posts props too — the half that changes at a LOCK WAKE, which is the
  moment both lineups post, the selection freezes and the hitters appear. A
  lock wake runs `python -m src.pregame` WITHOUT `--telegram`, so
  `force_telegram` is False; and on a no-play slate `picks` is empty and
  unchanged all day, so `changed` is False too. **Both halves of the test were
  False at exactly the moment the board gained its content, and nothing was
  sent.** Seen on 2026-10-14: a no-play Brewers @ Dodgers slate whose two props
  (Contreras −174, Turang −153) appeared at the lock and were announced by
  nothing until the next on-the-hour post forced one.
  Only PUBLISHED props count — `props_locked` is the publication gate, so a
  provisional selection churning in the background must not put a board on the
  phone that the board is not yet willing to show. A re-price on a locked prop
  DOES count, since the board prints the price.
- **Skipping the props recompute must not mean WRITING NOTHING**
  (`main._carry_props`). There is a window where a game has stopped being
  `upcoming` but first pitch minus `LOCK_LEAD` has not arrived: the props loop
  refuses to compute (`state != "upcoming"`) and `_lock_started_games` refuses
  to restore (not yet in the lock window), so the row is written with NO props
  — and from the next run on the lock faithfully restores that now-empty
  snapshot, which makes the loss permanent. The two guards are correct
  individually and leave a hole between them.
  Seen live on 2026-10-13 CLE@TB: first pitch 00:00Z, lock window from 23:45Z,
  and the **23:44Z** refresh wiped a José Ramírez prop that had been published
  to Telegram at 23:28Z tagged LOCKED. `prop_grade` settles what the BOARD
  carries, so it would never have been graded — the board showed a bet it then
  declined to score. The prop block is now carried verbatim across the skip,
  never re-priced, because once the game has started the pre-game price is the
  only honest one. `_carry_props` fills only what the fresh row is MISSING, so
  a row the lock restored whole is untouched.
- **The frozen prop roster is `props_frozen`, not `props`**
  (`main._refresh_locked_props`). `prop_withheld` stores a SUMMARY of a held
  candidate — player, score, need, odds, reason — and not the candidate, so a
  refresh that walked only `props` lost every held bat permanently, and once
  the last posted prop fell under its price bar the next refresh had an empty
  list to walk and the game went silently propless with no explanation. Seen
  live on 2026-10-13 CLE@TB: Ramírez posted at 20:35, held at 22:01, gone by
  23:01. The lock stores every bat it chose, posted or held; the refresh
  re-decides which of them POST from the current price **in both directions**,
  so a price that improves brings a frozen prop back. The players still never
  change. Snapshots written before the key fall back to `props`.
- **Any backtest reading `pm_books` / `kalshi_books` must cut readings at first
  pitch minus `LOCK_LEAD`.** Those logs run through the game and past
  settlement, so a losing side's last reading is `0.00/1.00`. `consensus.book_metrics`
  now cuts for you; anything that walks `readings` itself must do the same, or its
  "drift" reports the winner instead of the money. Measured cost of getting this
  wrong: +9.9% against -5.0% on the same 714 games.

### OPEN — awaiting a decision, or known and not done

Carried forward so a fresh session neither drops these nor re-derives them.

- **The four entries the postponed bug wrote are CORRECTED** (2026-10-17, on
  an explicit instruction to fix the record). They were never ordinary
  results — three settled a game that was not played — so the usual
  never-alter-records rule did not apply to them.
  | key | was | now |
  |---|---|---|
  | `2026-10-16#849817#802415` Chandler Simpson 1+ H | L −1.00u | **VOID** — removed; game never played, so there was no bet |
  | `2026-10-16#849817#800050` Chase DeLauter 1+ H | L −1.00u | **VOID** — removed |
  | `2026-07-27#824490` Elly De La Cruz 1+ H | L −1.00u | **W +0.50** — played 07-28, went 2-for-4, graded at the assumed −200 it was booked under |
  | `2026-07-27#824490` (parlay book) Reds ML + Elly | L −1.00u | **L, unchanged** — the Reds ML leg genuinely lost 5–6; only its empty score string was filled |
  A void is a REMOVAL, not a 0.00 push: there was no bet. Both corrected rows
  carry a `corrected` field saying why. `bankroll_after` was recomputed as a
  cascade from the entries, and each book's bankroll and record recomputed
  from its own rows rather than adjusted by hand.
  **Singles moved 159 bets / 99-60 / −10.41u → 157 bets / 100-57 / −6.91u** at
  the time of the correction; the parlay book was unchanged at 20-47 / −18.89u.
  (Those are the BEFORE/AFTER of the edit, not a running total — as of
  2026-10-22 singles sit at 162 bets / 104-58 / −5.91u with later days graded
  on top.) Verified afterwards: no
  entry still carries a `None` score, all three cascades reconcile to their
  stated bankroll, and re-running `prop_grade.update` on both dates adds
  nothing back — the postponed fix now reports 849817 as
  `state: postponed / final: False`, which is what keeps it from returning.
- **The price bar's CONDITIONS trigger is deciding which props post more than
  the price is, and the effect is visible across three consecutive boards.**
  `_prop_withheld` fires only when the night suppresses contact AND the read is
  under the break-even, so on a neutral night a prop posts at ANY price. What
  that produced:
  | date | posted | withheld |
  |---|---|---|
  | 2026-10-17 | Chandler Simpson **−270** | Chase DeLauter −221, Yandy Díaz −250 |
  | 2026-10-19 | Chase DeLauter −177 | Yandy Díaz −220, Nathaniel Lowe **−139** |
  The dearest price on the 10-17 board posted while two cheaper ones were held,
  and on 10-19 the cheapest price on the board was held. **Both are the gate
  behaving exactly as specified** — it is a contact-conditions gate, not a
  price ceiling.
  **IMPORTANT CORRECTION, so nobody re-litigates it:** the −270 was NOT a case
  of the gate passing something it should have caught. Simpson's read was
  **0.7427** against the **0.7297** that −270 demands, so he cleared on merit
  and would have posted even with the gate engaged. The asymmetry is real and
  worth watching; the specific −270 was not a failure.
  **Nothing has been changed.** Adding an unconditional price ceiling is a
  genuine threshold change and must be PRE-REGISTERED before more results land,
  never fitted to the record it would then be judged against — the same rule
  CLAUDE.md sets for every other threshold here.
- **An EMPTY covers board is not an outage, and covers says so itself**
  (`covers.NO_MATCHUPS`, `CONSENSUS_EMPTY_UPSTREAM`;
  `source_health` `upstream_empty`). On 2026-10-28 `covers tickets` read 0/1
  and the report cried SILENT FAILURE — but `covers_diag` showed the page was
  **fine**: HTTP 200, 306KB, right title, `covers-CoversConsensus-*` chrome
  intact, no captcha. It just had `tables: 0 · rows: 0`, zero
  `pickleadersbyteam` anchors, and the words **"No other matchups
  available"** in its visible text. The AWAY, HOME and PUBLIC-MONEY views all
  said the same. Our selectors were never broken; covers published nothing.
  `consensus()` now checks the raw text for that phrase and sets
  `CONSENSUS_EMPTY_UPSTREAM`; `main` records it on the payload as
  `consensus_empty_upstream`; `source_health` routes it to a third bucket
  beside `no_data` and `unresolved`, so it does not count toward
  `silent_failure` and the report says *served correctly but empty at the
  source* instead.
  **A GENUINE break still alerts** — the flag is set ONLY when that phrase is
  present, so a markup change, a captcha or a failed fetch leaves it False,
  `_fingerprint` fires as before and `silent_failure` goes True. Verified all
  three ways on the real 2026-10-28 board: empty-upstream → no alert; same
  board with the flag False → SILENT FAILURE; flag ABSENT (every board written
  before this) → still alerts, because absent means unknown.
  **TWO TRAPS HIT WHILE DIAGNOSING THIS, both worth remembering.** (1) The
  first probe counted `NN%` in the RAW html, found 110, and I read it as "the
  data is still there" — they were `width:100%` in CSS. Count percentages in
  VISIBLE text with script/style stripped; the real count was 5, and 4 of
  those were an FAQ sentence about favourites winning "58% to 62%".
  (2) A count alone never settles it — the decisive evidence was dumping the
  text AROUND each percentage, which is where "No other matchups available"
  appeared. `covers_diag._hunt` now does all of this plus the sibling views.
- **`source_health` has no notion of TIME OF DAY**, so a board built before the
  public has bet cries outage. Every board in the repo was generated 19:44–23:20
  ET except one dispatched at **01:01 ET on 2026-10-14**, which is the only one
  that ever tripped `SILENT FAILURE` — consensus, forum, handle, scoresodds and
  vsin all measure public ACTION and have nothing to report at 1am. Four of the
  five recovered by the 4pm run on their own. A pre-noon board should not report
  those five as dead; nothing has been changed.
- **covers.com's FORUM page returned a captcha** in `covers_diag.md` on
  2026-10-14 (`0 tables`, `page text contains 'captcha'` — a block, not a markup
  change, so no selector fix helps). It was NOT costing anything then —
  `src: forum` read 1/1 healthy on real runs the same afternoon — so it looks
  intermittent or rate-limited from the diagnostic's own request. If forum starts
  reading dead on real runs, this is why. The CONSENSUS page is fine and parses
  (`covers-CoversConsensus-*` classes all present, HTTP 200).
- **The HR pick only attaches to a game the board has an OPINION on.**
  `main._attach_hr_prop` runs under `if adv:`, and `adv` is None unless the game
  is a `pick` or carries a good-dog tag — so a `stay_away` game never gets one.
  Asked for a Dodgers HR pick on 2026-10-14 and there was none for exactly this
  reason. The same argument that put hit props on every game (a prop is its own
  bet and does not need the moneyline rule to have landed) applies here and has
  NOT been acted on.
- **The prop-records header conflates two books.** It reads
  `1+ hit · N/M real lines, rest assumed -200` while counting singles and the
  retired parlays together, so the denominator is larger than the singles book
  it sits above. Flagged three times, never fixed — display only, it changes
  no number in either record.
- **Telegram delivery has never been confirmed from this side.** `send_telegram`
  fails SOFT — it logs a warning and returns False — and the logs are
  unreadable from a sandbox session (see above), so a silent send failure is
  indistinguishable from a quiet board. If boards stop arriving, the first move
  is to write the send result into `output/` rather than guess.

### Git & Branching

- Develop changes on a feature branch; do not commit directly to the default branch.
- Use clear, descriptive commit messages.
- Push with `git push -u origin <branch-name>`.
- Open a pull request only when explicitly requested.
- **THREE props a game, from BOTH lineups, and the bat must be rising**
  (`main.PROPS_POSTED`, `PROP_SELECTOR`). A hitter's chance of a hit has nothing
  to do with which side the moneyline rule landed on, so the old picked-team-only
  pool threw away half the candidates; each side is ranked against ITS OWN
  opposing starter, since the fit and platoon terms are matchup-specific.
  **`_prop_score` no longer carries `form`** — the five-game hit-rate delta scores
  **AUC 0.5053** against getting a hit over 32,564 starts and its sampling SD
  (21.6 points) swamped the signal spread, so it was noise deciding which prop
  got picked. Do not reinstate it without a measurement that beats 0.5053.
  The replacement is the BATTED-BALL trend (`hr_pick.trend_factor`: air rate and
  ISO, last 5 against the prior 10) used as a FILTER, not a weight — rising
  62.3% got a hit against falling 60.3% over 22,516 games, p=0.0025
  (`form_trend.hits_test`). An unreadable window returns exactly 1.0 and is
  excluded: unknown is not rising. It is probed **lazily down the score order**
  and stops once enough bats have risen — each probe is a full-season gamelog, so
  scoring all ~18 candidates would be ~160 fetches a slate to use three. It
  cannot reorder anything; the score is already fixed.
  **Ledger keys are now `date#game_pk#player_id`.** On the game key alone the
  three would collide and `grade._add` would keep only the first. `prop_audit`
  parses both shapes; entries up to 2026-10-11 keep the two-part key.
  `pick_criteria["props"]` is the list and `["prop"]` stays the top one for
  older readers; `["hit_bats"]` is now ARCHIVAL only — it is the top of the pool
  BEFORE the rising filter, which is what a later backtest of that filter needs.
  **Props post AND PRINT on EVERY upcoming game, no-action ones included.** A
  1+ hit prop is its own bet and does not need the moneyline rule to have
  landed anywhere;
  on 2026-10-12 a two-game slate of no-action games carried zero props. So
  PRESENCE IN `props` IS THE LEDGER GATE now, not `play == "pick"` — but only
  for new-format boards. On a LEGACY board the single `prop` was also computed
  for good-dog watch entries as CONTEXT, so there the pick test still applies,
  in `prop_grade` and in `main._hit_lines` alike (the board shows as a bet
  exactly what the ledger settles). Legacy entries also keep the bare
  `date#game_pk` key they were settled under: re-grading an old date must
  reproduce the same key or `grade._add` would append a duplicate beside a
  settled entry. Rendering all 2026 boards before and after this change is
  byte-identical.
  **THE PROP SELECTION FREEZES AT THE FIRST CONFIRMED LINEUP**
  (`pick_criteria["props_locked"]`, `main._refresh_locked_props`). This is the
  real reason props churned all day, and it is not noise:
  **`mlb_api.lineup` silently falls back to the WHOLE ACTIVE ROSTER** when no
  batting order is posted — ~13 non-pitchers, most of whom will not start — and
  gave the caller no way to tell a real lineup from that guess. A morning board
  therefore picked a hitter out of the roster and picked somebody else entirely
  once the real nine appeared. `mlb_api.lineup_confirmed(game_pk, team_id,
  date, home)` now reports which was used.
  Once BOTH orders are posted the chosen players never change again. Only the
  PRICE is refreshed, because a hit line often posts after the lineup does — so
  a late line still attaches, and the price bar can still DROP a frozen prop
  whose number turns bad. It can never swap in a different hitter.
  **PROVISIONAL PROPS ARE NOT SHOWN AT ALL.** Before confirmation the board
  prints only `⏳ props pending — lineup not posted yet`, and the HR pick is
  suppressed with them since it comes from the same pool. Printing a pick the
  board itself does not stand behind invites betting it. After confirmation
  they appear tagged **— LOCKED**, which is the only tag that can ever render.
  The discriminator is `lineup_confirmed` being PRESENT: it is absent on every
  board written before 2026-10-13, which is how legacy boards keep rendering
  exactly as they always did (verified: zero removed lines across all 2026
  boards). The selection is still free to move while provisional — it just is
  not published while it is.
  **THE LOCK APPLIES TO PROPS, and until 2026-10-13 it did not.**
  `_lock_started_games` restores a frozen snapshot from `LOCK_LEAD` before
  first pitch onward — but it runs at `main.py:182` and the props loop ran
  after it, recomputing props straight over the freeze. The loop's guard was
  `state == "final"`, which let every LIVE game through, and `state` is itself
  refreshed post-lock, so a started game looked fresh. Measured over the last
  20 dates: **4 of 29 board-games (14%) had their prop re-picked after first
  pitch**, including BOTH of 2026-10-12's — Brice Turang was chosen at 7:08pm
  for a 5:00pm game, off season gamelogs that by then contained that game's own
  at-bats, and the ledger settled him. Earlier examples: 2026-10-04 Sean Murphy
  → Ozzie Albies; 2026-10-12 José Ramírez → Jo Adell.
  The guard is now `game_pk in LOCKED_PKS or state != "upcoming"`, and
  `_lock_started_games` publishes `LOCKED_PKS` for exactly this. **Anything
  that WRITES to a game row after the lock must consult that set** — the lock
  is not self-enforcing, it only restores the row, and whatever runs next can
  overwrite it.
  **The affected ledger entries are NOT repaired and NOT re-graded** (records
  are never altered). Prop singles settled before 2026-10-13 may include picks
  made after first pitch; treat that population the way CLAUDE.md treats the 97
  `k_ticker_stale` Kalshi entries — real results of a contaminated selection.
  **THE TELEGRAM BOARD IS PICKS ONLY** (`telegram_text`): the matchup, the
  moneyline pick with its price if there is one, and the LOCKED props with
  theirs. Nothing else. Everything that used to print — stat edge, consensus,
  BvP, platoon, contact conditions, the pool census, the watch tags, the paper
  parlay, the records — is still computed and still in
  `output/picks_<date>.json`, and the readable version of it moved into
  `build_summary` → `latest_summary.md`. That move was not cosmetic: dropping
  those blocks from Telegram orphaned `_line_money_lines`, `_paper_parlay_lines`
  and the no-play props section, so they were re-wired into the markdown rather
  than left to rot.
  An empty board distinguishes **"No picks today"** from **"No picks yet —
  lineups not posted"**, because those are different facts and only one of them
  means look again later.
  **THE RECORDS LIVE IN THE END-OF-DAY RECAP** (`grade.day_recap_text`), which
  is now the one message that reports how it is going: each play with its score
  and units, then the day's PROPS with theirs, then the moneyline record
  windows and `prop_grade.records_lines`. With the board stripped to picks,
  nothing else carries them.
  **The recap also fires on a PROPS-ONLY day** (`grade._send_props_only_recap`).
  It used to return early on `not settled` — no moneyline play meant no recap —
  so 2026-10-11 and 2026-10-12 both had graded props and got no recap at all,
  which are exactly the days props are the only product. A props-only day is
  released by `_all_games_final`, since there is no settled play to prove the
  slate is over. Still once per date via `recaps_sent.json`.
  **`_game_lines`, `_stay_line` and `_telegram_records_lines` are now UNUSED**
  (`_game_lines` had no caller even before this). Left in place rather than
  deleted — they are the detailed per-game renderer and a records formatter,
  and reconstructing them to restore a richer board would be real work.
  **`build_summary` renders a `## Props — games with no play` section**, and it
  for the same reason it was once needed on Telegram: the selector posts props
  on every game and `prop_grade` settles them, but the renderers only ever
  walked PLAYS. On 2026-10-12 Max Muncy was posted at −133, stored and
  gradeable while the board read "No plays on the board." Storing a prop and
  showing it are separate code paths; changing one does not change the other.
  Plays carry their props inline via `_pick_line` → `_hit_lines`, and the
  section skips `_play(g) == "pick"`, so nothing prints twice.
  The second and third prop on one game cost no extra odds credits
  (`prop_odds.hit_line` caches the game's whole batter_hits board per day), but
  a game that is not a play is a new board to price, so it spends under the
  registered `prop_extra` tier and yields before a play's own line does.
- **Projections are OFF THE BOARD and must stay ATTACHED** (`projections.attach`
  at `main.py:106`; the render block in `main._hit_lines` is deliberately gone).
  Tracking a number and printing it are separate decisions and only the
  printing was dropped — an untested projection on the board reads like a call.
  **Do not remove the attach to "clean up" the unprinted field:**
  `market_track` reads `pick_criteria["projections"]` to score which side of
  the book's line our number took, so dropping it silently empties the tracking
  record. Re-printing is just restoring that block; the data is already on
  every game.
  Note the related fix that stays: a no-action game returns from `_game_lines`
  at `_stay_line`, which used to skip everything in `_hit_lines`, so its PROPS
  never printed either. Props on a no-action game still print.
- **The two run totals do NOT share a multiplier, and the umpire is NOT in the
  strikeout projection** (`projections.py`, measured in `totals_model.py` over
  1286 finished board games — five times the 251 `totals_signal` had).
  **SHIPPED, each with a day-block bootstrap behind it:**
  *First five is starter FIP alone; the full game weights starter and bullpen
  FIP by INNINGS* (`STARTER_IP_DEFAULT`/9 from the starters, the rest from the
  pen). Mechanism — the starters pitch the first five — and the data agrees
  twice: bullpen FIP correlates +0.139 with full-game runs against +0.030 with
  the first five, exactly that asymmetry, and head-to-head the split cuts
  full-game MAE 3.60→3.53, r +0.075→+0.097, ΔMAE **[−0.105, −0.038]**, entirely
  below zero. The first-five row is identical by construction.
  *League constants re-measured on 1286 games*: 8.66→**8.92** full, 4.71→**4.96**
  through five (55.6% of the game, not the 54% assumed). Not tuning — the
  constant is DEFINED as the league mean of the thing projected. It cut the
  cold bias from −0.45 to −0.19 runs.
  *`pitcher_season_line` now also returns `ip_gs`/`k_gs`, STARTS ONLY, and
  `projections.strikeouts` uses them.* Dividing all-appearance innings by games
  STARTED overstates how long anyone who also relieved goes. That one line was
  the single biggest error in the file: bias **+0.71→+0.06** K, MAE
  **2.26→1.89**, r **+0.149→+0.404** over 2353 starts, ΔMAE [−0.435, −0.301].
  **MEASURED AND REJECTED — the UMPIRE on strikeouts, which was asked for
  directly.** It fails three independent ways and twice with the WRONG SIGN:
  (1) raw `k_extra` vs the game's actual strikeouts is r=−0.044 over 1038 games
  all out of sample for the table, with the high-`k_extra` third of umpires
  seeing **16.36** K/game against **17.14** in the low third; (2) as a
  multiplier, ΔMAE [−0.008, +0.018], and against what the K projection misses
  r=+0.012; (3) residualised so the pitcher is removed by construction and
  split chronologically (first half builds the tendency, second half tests it),
  out-of-sample r=**−0.067** with a tercile gap of −0.38 K/start. **The
  decisive number is the noise floor**: the spread of umpires' residual
  tendencies is SD 0.57 K/start against a sampling floor of 0.64 — **0.90× the
  floor**, i.e. no wider than if every umpire were identical. Umpires that
  genuinely differed would spread WIDER. So this is not a stale table (it is
  stale — built `through 2026-07-02`) and not a build bug; the quantity is not
  there. Split-half reliability of raw K/game is +0.172 → Spearman-Brown
  **+0.293**, and that residue is mostly which PITCHERS he drew. Do not add an
  umpire strikeout term without a measurement that clears the noise floor.
  The umpire tilt in `analysis.statistical_favorite` is a separate claim about
  WIN rates and is untouched by this.
  **ON THE SHELF, not shipped:** temperature and wind-out read as ONE carry
  index (same mechanism — how far a struck ball carries) reaches r=+0.084 vs
  full-game runs on 803 games, a +0.95-run tercile gap and r +0.100→+0.121, but
  ΔMAE **[−0.041, +0.002]** spans zero, so it does not ship. Right sign, right
  mechanism, too small to lower the error. Re-test it when more games
  accumulate; do NOT re-fit the slope. Separately: signed wind needs the
  compass string (`wind_dir`, on all 1167 weather boards) because `wind_deg` is
  on only 24 — and `totals_signal` tested wind SPEED, where a gale blowing in
  and one blowing out are the same number and cancel, which is why it read
  −0.041. Bullpen arms down (−0.044) and bullpen innings (−0.001) are null.
- **The totals, first-five and strikeout markets are TRACKED, not bet**
  (`market_log` logs, `market_track` settles, `projections` supplies our side).
  Nothing is staked, no price is compared to a payout, no pick changes, and
  there is no ROI figure anywhere in it. The record answers two narrow things:
  how often the OVER hit, which is the market's own calibration and the
  baseline to beat, and — where we had a projection — which side it took and
  whether that side was right. **A hit rate is not an edge**: a 55% side at
  −115 is break-even and the vig on a two-sided total is ~4.5%, so nothing
  becomes bettable until a side clears its price by more than its own interval.
  **Readings are cut at first pitch minus `consensus.LOCK_LEAD`**, the same rule
  CLAUDE.md sets for `pm_books`: the poller runs three times a day, so an
  afternoon game is in progress by the later polls and its line has seen the
  score.
  **The log is keyed per GAME, not per team pair** (`market_log.event_key` =
  `away@home|commence`). A pair plays on consecutive days and `/events` lists
  several days at once, so a bare `away@home` key kept whichever event came
  last — the identical error that put the wrong Kalshi market on 97 entries.
  `market_track._find` matches the board game by commence time within
  `MATCH_TOLERANCE` and **REFUSES bare pair keys** rather than guessing; the
  count of refusals is printed. The 2026-10-11 log predates the key, so its
  readings are deliberately unusable and the record starts at the per-game key
  — same treatment as the 97, and for the same reason. `market_log` also now
  polls only events whose EASTERN start date matches the log date: `/events`
  spans days, so `MAX_EVENTS` could otherwise spend its whole budget on
  tomorrow's slate and log nothing for tonight.
  **`totals_signal._scores` must not cache a date whose games are unfinished.**
  It did, and `date in cache` made that permanent: 2026-10-11 and 2026-10-12
  both sat at `{}` with a live game on them, so the most recent games — the
  ones a tracker needs most — could never settle. A date is cached only once
  every game on it is done (postponed/cancelled/suspended excluded, since they
  never reach Final), and an empty cached entry is re-checked rather than
  trusted, which heals the dates already poisoned.
- **No parlay structure this data supports is positive, and the reason is
  arithmetic** (`parlay_structure.py`, `output/parlay_structure.md`). Asked how
  a professional would structure one to raise the hit rate or make it pay big.
  Those are opposite ends of one priced dial, and both ends were computed.
  **A parlay's edge is the leg's edge raised to the number of legs**, so it
  cannot rescue a losing leg, only lose faster: posted hit props at 62.6%
  against a 66.7% break-even are −6.1% as singles and −27.0% at five legs,
  −43.2% at nine. Hold compounds the same way — 4.5% a leg is 20.6% at five
  legs, 33.9% at nine. **$5 → $200 is decimal 40**, which these legs reach only
  at NINE of them, where they hit 1.48% against the 2.60% the price demands; in
  five legs each would have to pay +109, i.e. underdogs, not our props. The
  already-retired `prop_grade` parlay book is the live confirmation: 20-47,
  −28.2%, CI [−47.4%, −6.7%], the only interval in the system that excludes
  zero.
  **Correlation is the ONLY legitimate parlay edge** — a book prices legs as
  independent, so positively correlated legs are underpriced. Measured on 4517
  hitter-games: same-team pairs **×1.035**, same-team triples **×1.135**,
  while the OPPOSITE-team control sits at **×0.996** and ×1.052. That control
  landing on 1.000 is the validity check — two hitters facing different
  pitchers should not co-move. But p≈0.10, and crediting the lift in full a
  3-leg same-team parlay still returns **−6.5%** (−17.2% if the lift is zero).
  Correlation has the right sign and is too small to cover the compounding hold
  plus the 5.5-point deficit the legs start with.
  **TWO ESTIMATOR TRAPS, both hit here first and both worth remembering.**
  (1) Selecting hitters on a rate and then using that same rate as the
  expectation reported a ×0.807 lift — a 19% ANTI-correlation no mechanism
  explains — because filtering at 60% on an ~18-game rate (SE 0.115) selects
  upward noise, so the expectation overstates true skill. Holding the measured
  games out of the rate does NOT fix this; the bias is in the estimate, not the
  overlap. (2) The fix is to read the lift **relative to the permutation null**,
  which carries the identical selection bias and differs only in which game
  each outcome came from. The null sits at ×0.72–0.80, not ×1.000, and that gap
  IS the bias. Any future version of this must report the null, not just the
  raw ratio.
  **This cuts against how props are posted, deliberately:** three props from
  BOTH lineups is right for three SINGLES and wrong for a parlay, which wants
  correlated same-team legs. Different products; the board posts singles.
- **The paper ticket is now the HELD PAIR, by request** (`parlay_paper.STRUCTURE
  = "held_pair"`, from 2026-10-14). Two hitters who made the selection — rising
  filter, short-night gate, score order — but whose REAL price does not beat
  their read: exactly the `prop_withheld` population. Ranked by read, top two,
  and legs may come from DIFFERENT games because `leg_markets` corrected the
  same-team hit-prop lift to ×1.001, so there is nothing to harvest by staying
  in one game.
  **It is expected to lose MORE than the singles did and the arithmetic is not
  in doubt.** A parlay's EV is the PRODUCT of its legs' EVs, so two negative
  legs multiply. The first pair computed (Aranda 56.8% at −179, DeLuca 55.0% at
  −181) are −11.5% and −14.6% alone and **−24.4%** together — 31.2% delivered
  against the 41.3% the price demands. **The result does not depend on the
  reads being right**: if they are too low and regress up toward the 61.7%
  pooled rate, the legs get less bad but the parlay stays worse than the
  singles at EVERY calibration, and the moment a leg turns positive the correct
  move is to post it as a SINGLE. Reaching break-even on that first pair needed
  a ×1.323 correlation lift against the ×1.001 measured on 5800 combos.
  It is logged because it was asked for, it costs nothing, and a forward record
  is the only thing that settles a disagreement about a number. Every ticket
  stores `expected` — modelled joint rate, break-even, EV — so the record reads
  against the prediction rather than against zero.
  **The guard INVERTS for this structure.** A four-leg ticket's hits legs were
  POSTED props and each must ALSO exist as its own single; a held-pair ticket's
  legs were WITHHELD and must NOT appear in the singles book, or a prop the
  board declined to post is being settled as though it had been.
  `record_audit.paper_parlay_guard` branches on the `structure` stamp and
  asserts whichever direction applies, per ticket. The stamp also keeps the two
  products separable in one book — four-leg entries already settled must not be
  pooled with these. Legs carry their own `game_pk`; `_grade_leg` falls back to
  the ticket's, which is every four-leg ticket already on disk.
  `_prop_withheld` now returns `player_id` and `team` so a held bat is
  settleable at all — settlement keys on the id, never the name.
  **It is REPORTED IN THE RECAP** (`parlay_paper.recap_lines`, called from
  `grade._recap_paper_parlay`), LAST and under its own heading that says *not
  a bet · no money · not in any ledger* on the line itself — it sits directly
  beneath the real records and a reader skimming on a phone must not be able
  to confuse the two. Each settled ticket prints beside the expectation it was
  built with, so the record reads against the prediction. `recap_lines` calls
  `settle(date)` first, because the recap can fire before this module's own
  workflow has run and a result that exists must not be missing from the one
  message that reports how it is going; settlement is idempotent per date and
  all-or-nothing, so that can never double-book or book a partial ticket. Both
  it and `_recap_paper_parlay` fail SOFT: a paper experiment must never cost
  the recap its actual record. The running line SPLITS held-pair out whenever
  the book also holds four-leg entries — pooling two structures into one
  number is the thing the `structure` stamp exists to prevent.
  **THE FORWARD RECORD STARTS 2026-10-17.** Two tickets so far, **1-1,
  +2.50 on paper**:
  | date | legs | price | result |
  |---|---|---|---|
  | 2026-10-17 | Chase DeLauter + José Ramírez | +115 | L −5.00 |
  | 2026-10-19 | Yandy Díaz + Nathaniel Lowe | +150 | **W +7.50** |
  **Two tickets prove nothing and the win does not reopen the argument** — the
  structure is modelled at about **−24%**, so a 50% hit rate over two is
  exactly the variance you would expect to see either way early. Read it
  against each ticket's stored `expected`, never against zero, and do not let
  an early positive bankroll become an argument for staking it. The question
  this book answers needs dozens of tickets, not two.
- **The FOUR-leg ticket is PAPER TRADED in its own book** (`parlay_paper.py` →
  `output/parlay_paper.json`, built by its own workflow after the board).
  **SUPERSEDED as of 2026-10-14 by the held-pair structure above** — kept
  because its settled entries stay in the book and `_grade_leg` still has to
  grade every leg type they contain.
  Structure: the board's moneyline pick, two DIFFERENT players for 1+ hit, and
  2+ total bases for the power model's hitter. Nothing is staked. It touches no ledger — the hit props keep
  being recorded as singles exactly as before, and
  `record_audit.paper_parlay_guard` asserts both halves of that from the files:
  every hits leg must ALSO exist as its own single, and no paper date may
  appear in the booked-parlay book.
  **Expected to lose, slowly** — `parlay_structure.md` puts the best available
  structure at −6.5%; paper trading is how we find out whether a banker leg
  plus correlated legs lands nearer that than the −28.2% the retired parlays
  did. It is built SAME-GAME on purpose: that is where the measured ×1.035 /
  ×1.135 correlation lift lives.
  **The alternate-strikeout "banker" leg was DROPPED on the measurement that
  was meant to justify it** (`alt_k.py`, `output/alt_k.md`). "A number the
  pitcher has never missed" is NOT a floor — it is the smallest value in a
  sample, and it drifts down as the sample grows. Measured out of sample in
  date order over 891 starts from 142 starters: his exact prior minimum clears
  **92.0%**, one under it **97.0%**, two under **98.1%**, and it gets WORSE
  with more starts — 93.3% at 8–11 prior starts, 92.9% at 12–15, **89.4% at
  16+**. A leg priced near certainty adds almost nothing to the payout while
  removing 8% of the ticket, so four legs pay slightly less and win
  meaningfully more often. `alt_k` is KEPT and still refreshed: it is the
  standing justification for a structural decision, and a stale number backing
  a live decision is worse than a refreshed one. `_grade_leg` also keeps its
  `alt_strikeouts` branch, because a ticket file written before the drop still
  has one on disk and settlement must not mis-grade it.
  Settlement reads the boxscore directly (`mlb_api.pitcher_strikeouts`,
  `player_total_bases`, `player_hits`) and is **all-or-nothing per ticket** — an
  unconfirmable leg leaves the whole ticket unbooked for a later retry, so a
  feed gap can never book a partial ticket. Idempotent per date.
  **THREE DISTINCT HITTERS, and that is structural, not cosmetic. 2+ TOTAL
  BASES CANNOT HAPPEN WITHOUT A HIT**, so the same player on both the hits leg
  and the total-bases leg is a NESTED leg: the ticket carries three legs of
  real risk while being priced as four. The first live four-leg ticket did
  exactly that, putting Max Muncy on both. Relative to independent pricing a
  nested leg is actually FAVOURABLE, which is precisely why books refuse or
  re-price it — so it is not a bet that would stand, and a paper record of a
  bet that would be rejected teaches nothing.
  Ordering: the HR pick is RESERVED for total bases before the hits legs fill,
  since he is chosen by the power model and is the point of that leg. With no
  HR pick the hits legs fill FIRST and total bases takes a leftover — an
  earlier version took the top prop for total bases, so a night with one posted
  prop spent it there and left both hits legs empty. The hits legs are the
  measured product with their own recorded singles; total bases is the
  speculative one.
  **The price bar checks the starter the HITTER FACES, not either starter**
  (`_conditions_against(g, bat_team)`). The gate fires only when the night
  suppresses contact — cold, wind in, or a high-K starter — AND the read is
  under the break-even the price demands; the bar IS the price, not a chosen
  threshold. The strikeout half used to ask whether EITHER starter was high-K,
  which was a tolerable proxy while props came only from the picked team and
  became wrong the moment they came from both. On 2026-10-12 it held Teoscar
  Hernández on **Yamamoto's 10.04 K/9 — his own team's pitcher**, who never
  throws him one, while the man he actually faced sat at 9.1 under the 9.5 bar;
  same for José Ramírez, held on Griffin while facing Rasmussen at 8.9. Two of
  five holds that night were on the wrong pitcher. Temperature and wind stay
  game-level because they are. Omitting `bat_team` keeps the old either-starter
  behaviour, which is what a legacy prop with no `team` field falls back to.
  **No fallback to WITHHELD props.** A prop held by `_prop_withheld` is below
  its own break-even, and a leg's EV multiplies into a parlay exactly as it
  does into a single, so a held leg is bad in both. A ticket that cannot find
  four legs records what is `missing` and is not booked — on 2026-10-12 the
  slate had no play and one prop total, so no ticket existed at all, which is
  the correct outcome rather than a thin one.
- **The four-leg ticket CANNOT be back-tested on this history, and the ML+prop
  pairing gets NO correlation subsidy** (`parlay_backtest.py`,
  `output/parlay_backtest.md`). Of 248 past plays, **241 stored no `hit_bats`
  pool at all** and most of the rest carry exactly ONE hitter — boards posted a
  single prop until 2026-10-12, so three distinct hitters never existed in the
  record and a four-leg reconstruction would invent two of its legs. The
  four-leg record has to be built FORWARD; that is what `parlay_paper` is for.
  **What the 142 gradeable two-leg rows say:** moneyline pick **54.2%**, its
  posted prop **63.4%**, both together **33.8%** against 34.4% independent —
  a same-game lift of **×0.984**, i.e. NONE. One hit barely moves a game's
  outcome and a game's outcome barely moves one hitter's chance of a hit, so
  pairing the pick with a prop is just paying two holds: **−12.8%** at real
  prices. That is a different result from the same-TEAM hit-prop pair at
  ×1.035, and it means the ML leg contributes no correlation to the ticket.
  **The total-bases leg now has a measured fair price.** The board's own posted
  hitters reach 2+ total bases **38.7%** of the time → fair about **+158**
  before hold. The `+140` previously assumed is already a LOSING leg (demands
  41.7%, delivers 38.7%). ML + 2+ TB honestly priced returns −28.2% / −13.9% /
  +0.5% at +100 / +140 / +180.
  **BEWARE the nested-leg artifact, which this backtest produced at +29%.**
  Putting 2+ total bases on the SAME hitter as a 1+ hit leg wins on TWO legs of
  risk while being PAID for three, because 2+ TB cannot happen without a hit.
  The redundant leg multiplies the payout for free and that free multiplier IS
  the entire positive number. No book prices it that way. Any future report
  showing a positive parlay ROI should be checked for exactly this first.
- **All three hitter markets ARE back-testable on outcomes; only prices are
  partial** (`leg_markets.py`, `output/leg_markets.md`, 26,397 hitter-games over
  1286 final board games). `hrr_shadow`'s claim that H+R+RBI "cannot be
  back-tested" is true only of its PRICE — the outcome sat in the boxscores all
  season, and the outcome is the half that decides whether the read transfers.
  Hitters are filtered ONCE on their held-out HIT rate (what the selector
  estimates), then measured in all three markets.
  **Single legs, all near fair:** 1+ hit **61.7%** against the −173 median's
  63.4% = **−1.7 pts**; 2+ H+R+RBI **47.4%** against the +115 median's 46.5% =
  **+0.9 pts**; 2+ total bases **36.4%**, fair **+175**, and NO price was ever
  captured — capturing it is the single highest-value thing left to collect.
  **CORRECTION TO `parlay_structure`: the same-team HIT-prop lift was NOISE.**
  On 5800 combos instead of 834 it is **×1.001** for pairs and **×1.011** for
  triples, not ×1.035/×1.135. Hits are an individual event and do not co-move.
  Do not cite the old numbers.
  **H+R+RBI DOES co-move same-team** — ×1.098 for pairs, ×1.295 for triples —
  and the mechanism is obvious: runs and RBIs are TEAM events, so a team
  scoring lifts several hitters at once. But the OPPOSITE-team control sits at
  ×1.104 for triples rather than ×1.000, so part of that is a game-level
  scoring effect, not a same-team one; the same-team-specific part is nearer
  ×1.17. Pairs are clean (control ×0.984).
  **The apparent +14%/+37% H+R+RBI parlay ROI is NOT ESTABLISHED.** Price-matched
  — each captured quote resolved to the player it was for — the pooled rate over
  1571 held-out games is 50.8% against the 46.7% the average quote demands, a
  **+4.1-point pooled edge**, but only **24 of 42** quotes were beaten, inside
  chance (±15%). The binding limit is the PRICE sample: 42 quotes from four
  October dates. Widen `prop_odds.hrr_line` to log the whole board daily before
  trusting it.
  **PRICE CAPTURE IS NOW WIRED** (`prop_odds.warm`, called from `main` for
  every upcoming game, capped by `WARM_MAX_GAMES = 4`; both markets are per-day
  cached so only the first board run of the day spends). First night live:
  21 H+R+RBI quotes and the **first 2+ total-bases prices that have ever
  existed in this repo**.
  **And total bases looks BAD at the prices it is actually sold at.** Captured
  overs ran +115 to +156, median **+133**, which demands **42.9%** against the
  measured **36.4%** — a **−6.5-point** leg before any parlay multiplies it.
  Fair is +175 and nobody is offering it. That is the opposite of what the
  rate alone suggested, and it is a direct hit on the paper ticket's
  total-bases leg: re-read `parlay_paper`'s expectation once a few more nights
  land, and do not treat the 36.4% rate as if it were available at fair.
  **TWO BUGS WORTH REMEMBERING.** (1) `rate - need` is a FRACTION: formatting it
  `:+.1f` printed an 18-point edge as "+0.2 pts" and a 1.7-point gap as
  "-0.0 pts". It happened twice, one line apart. (2) The first price-match
  ranked 42 quotes by each hitter's own held-out rate and showed the top twelve
  — with `MIN_HALF = 6`, a rate reads 65% off four of six, so sorting by it puts
  the noisiest quotes on top. Use the POOLED outcome, never a ranked list of
  per-hitter estimates.
