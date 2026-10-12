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
  **Props post on EVERY upcoming game, no-action ones included.** A 1+ hit prop
  is its own bet and does not need the moneyline rule to have landed anywhere;
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
