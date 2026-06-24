# MLB Public-vs-Stats Edge Finder

Finds MLB games where **the team the betting public is NOT on also holds the
statistical advantage over the last 5 games**, and writes them to a daily JSON file.

## What it does

For every MLB game on a given day:

1. **Schedule + probable pitchers** — from the official MLB Stats API
   (`statsapi.mlb.com`, free, no key).
2. **Last-5-game stats** — each team's hitters' OPS over their last 5 games, and
   the probable starter's ERA/WHIP over their last 5 outings (MLB API).
3. **Public majority** — from covers.com, two ways:
   - **Consensus %** — covers' published public-betting percentages.
   - **Forum tally** — mentions of each team across that day's MLB forum posts.
4. **Pick the team** — a team is added to the day's `picks` only when **all three**
   line up on it:
   - it holds the **last-5 statistical advantage** (higher `team_score`), **and**
   - the covers.com **public majority is *not* on it** (the public-vs-stats edge), **and**
   - it **met the full win condition in ≥ 3 of its last 5 games** (scored its target
     *and* held the opponent under its ceiling, SOS-adjusted).

   The per-game `pick_criteria` block shows each of the three flags so you can see
   why a game did or didn't make the cut. The threshold lives in `WC_PICK_MIN`.
5. **Betting lines** — each game's `betting_lines` block splits the two sides into
   `majority` (the higher consensus %) and `non_majority`, with each side's team,
   `consensus_pct`, and `moneyline`. (covers' MLB consensus is moneyline-only —
   it carries no run-line/spread consensus, so only the moneyline is attached.)

Output: `output/picks_<date>.json` — full per-game breakdown plus a top-level
`picks` list.

## The "statistical advantage" metric

Everything is built from the **last 5 games** and expressed as a league-relative
index (0 = average) so the parts add up:

```
team_score = offense_index + pitching_index          (higher = better)
```

**Offense** — park-neutralized, platoon-adjusted last-5 line:

```
offense_index = 0.55 * wOBA-vs-league      (overall run value, the backbone)
              + 0.20 * ISO-vs-league       (power)
              + 0.15 * (BB% - K%)-vs-league (plate discipline)
              + 0.10 * SB-rate-vs-league    (baserunning)
then * platoon factor (lineup bat-hands vs opposing starter hand, ~3%/matchup)
```

The lineup's last-5 rate stats are **neutralized by the parks they played in**
(a team that feasted at Coors gets discounted) **and strength-adjusted for the
pitching they faced** (production vs tough arms counts more). The full reported
line is AVG / OBP / SLG / OPS / ISO / wOBA / BB% / K% / SB-rate.

**Pitching** — FIP (skill, strips out defense/luck), starter + bullpen, each
**strength-adjusted for the offenses faced** (suppressing strong bats counts more):

```
each FIP   -> regress to league mean by innings:  w = IP / (IP + FIP_PRIOR_IP)
              shrunk_FIP = w * FIP + (1-w) * LEAGUE_FIP        (small-sample guard)
combined_FIP   = 0.55 * starter_FIP + 0.45 * bullpen_FIP   (last 5, shrunk + SOS-adjusted)
pitching_index = (LEAGUE_FIP - combined_FIP) / LEAGUE_FIP
```

The **shrinkage** stops a tiny noisy sample from blowing up the index: a 2-IP spot
start with two homers (a ~12 FIP) gets pulled most of the way back to average,
while a genuinely bad FIP over a full ~30-IP sample is believed. `IP` behind each
FIP is reported alongside it.

The team with the higher `team_score` has the advantage. **Every weight,
league baseline, and the wOBA/FIP constants live at the top of
`src/analysis.py`** — tune them in one place. Missing data contributes 0.

### Strength of schedule (SOS)

Recent stats are re-rated by the **quality of opponents faced**, blending each
opponent's season FIP/wOBA (70%) with their win% (30%), clamped to ±25%:

```
opp_pitching_factor  (>1 vs tough arms)  scales hitters' production
opp_offense_factor   (>1 vs tough bats)  scales pitchers' FIP (divides -> better)
```

This feeds both the main advantage indices **and** the win-condition back-test
below. Opponent win% comes free from one standings call; FIP/wOBA is one cached
call per team.

## Win condition (multi-part target + SOS-adjusted back-test)

Each game gets a concrete, countable **win condition** per team, then back-tests
it against the team's own last 5 games — with each past game re-rated by the
opponent it came against:

```
runs_to_win   = floor(opp runs/g * team_FIP / LEAGUE_FIP) + 1    (must outscore)
runs_to_allow = floor(team runs/g * opp_FIP / LEAGUE_FIP)        (must hold under)

per past game (SOS-adjusted):
  adj_scored  = runs_scored  * opp_pitching_factor
  adj_allowed = runs_allowed / opp_offense_factor
```

`back_test` counts, out of the last 5, how often the team:
- **scored_target** — adj runs ≥ `runs_to_win`
- **held_under_ceiling** — adj runs allowed ≤ `runs_to_allow`
- **complete_win_condition** — both in the same game
- **actually_won** — outscored the opponent
- **out_hit** — more hits than allowed

Plus `avg_opp_win_pct_faced` and a `per_game` breakdown. **`complete_win_condition`
gates the pick:** the advantage team must have met it in ≥ `WC_PICK_MIN` (3) of its
last 5 games, on top of the public-vs-stats edge (see "What it does" above). The
other four counts are reported for context.

### Caveats baked into the metric

- **Pure last-5 is a tiny, noisy sample** (your choice) — no season blending, so
  one hot/cold week swings it. Read picks as "who's hot + better on paper now."
- **Platoon uses league-average magnitude**, not true last-5 splits (those aren't
  exposed by the API): each hitter's bat side vs the opposing starter's hand,
  scaled ~3%. Direction is right; it's an approximation.
- **Lineups** come from the posted batting order when available, else the active
  roster's position players — early-day runs (before lineups post) use the roster.
- **wOBA/ISO/discipline overlap** somewhat; wOBA is weighted as the backbone and
  the others are smaller tilts to limit double-counting.
- **SOS uses season opponent ratings**, not their form on the day they were played;
  it's clamped to ±25% so a soft/brutal stretch can't dominate.

## Bankroll (paper trading)

`src/grade.py` settles each flagged pick against the actual MLB final score and
keeps a running **$1-per-pick bankroll** in `output/ledger.json`. The daily
workflow grades the **prior day** (once its games are final) before generating
today's picks, so the bankroll line shows up in the daily issue and the ledger
is committed back. Grading is idempotent per pick (by `game_pk`), so re-running a
partially-complete day safely catches late finishers without double-counting.

Settlement uses each pick's **moneyline captured at pick time** (from
`betting_lines`): a $1 win pays the American odds (e.g. +106 → +$1.06), a loss is
−$1.00. Picks with no recorded line (forum-only games covers' consensus didn't
list) fall back to **even money (+100)**. Each entry records the odds and its
source. Run a specific date with `python -m src.grade --date YYYY-MM-DD` (or the
`grade_date` workflow input). *(True closing odds would need a separate odds-page
fetch right before first pitch — a possible follow-up.)*

**Learning from losses:** every settled pick stores its context (win-condition
hits, stat-edge margin, underdog/favorite, odds). The ledger's `review` block
compares wins vs losses and, once enough losses accrue, emits concrete tuning
**suggestions** (e.g. "losses skew to lower win-condition hits → raise
`WC_PICK_MIN`"). It's a *reporting* aid that surfaces what to change — it does not
silently rewrite the formula.

`src/backtest.py` is a point-in-time *historical* backtest (forum-only public
signal, even money). **Known limitation:** the covers forum listing exposes only
thread-creation dates, not per-day posts, so daily public sentiment can't be
reconstructed without crawling into individual threads (not built) — so it
currently finds ~0 picks. The forward bankroll above is the real measure of
performance; the backtest's point-in-time machinery is correct and waits on that
thread crawler.

## Running it

### On GitHub Actions (intended use)

The build/dev sandbox firewalls covers.com and the MLB API, but **GitHub's
runners have full internet access.** The workflow `.github/workflows/daily.yml`:

- Runs **manually** ("Run workflow" button — works from the GitHub mobile app),
  with an optional `date` input.
- Runs **daily** at 15:00 UTC (~11:00 ET).
- Commits `output/picks_<date>.json` back to the repo.

> Scheduled runs use the workflow file on the repo's **default branch**. If this
> work lives on a feature branch, merge it to the default branch (or set this
> branch as default) for the cron to fire. `workflow_dispatch` can run from any
> branch via the Actions UI.

### Locally

```bash
pip install -r requirements.txt
python -m src.main --date 2026-06-23   # omit --date for today (US/Eastern)
```

## ⚠️ Honest caveats — read before trusting output

- **covers.com selectors are unverified.** covers' HTML is undocumented and this
  code could not be tested against it from the build sandbox (covers is
  firewalled there). covers is a **Next.js site**, so the consensus numbers are
  rendered client-side in an embedded `__NEXT_DATA__` JSON blob — the parser tries
  that JSON first, then falls back to a table heuristic. Every covers parser fails
  *soft* — on a miss it logs a **structural fingerprint** (`... parse empty | ...`)
  instead of just a generic warning. To fix the selectors for real, run the
  workflow once with the **`covers_debug` input checked** (or `COVERS_DEBUG=1`):
  it dumps the raw HTML covers serves into `output/covers_debug/` and commits it
  back, so the exact markup is available to pin the parser to.
- **Forum sentiment is a blunt heuristic.** "Majority side" from forum text is a
  raw mention tally — it matches each team by name/nickname/city **and its
  abbreviation** (BOS, NYY, …), the abbreviation on word boundaries so a short
  code can't trigger inside another word (e.g. "bosses"). **Run-line / spread
  picks are disregarded:** each mention owns the text up to the next team
  mention, and if that text is a spread context (`-1.5`, `run line`, `RL`,
  `cover`, `ATS`) it isn't counted toward the *moneyline* tally — an explicit
  `ML` overrides. It still doesn't understand fades, sarcasm, or parlays. Treat
  the consensus % as the stronger signal; the forum tally is corroboration.
- **This is not betting advice.** A last-5-games stat edge ignores matchups,
  bullpens, weather, injuries, lineups, and market prices. It's a research
  signal, nothing more. Bet responsibly.
- **Respect covers.com's Terms of Service.** Requests are rate-limited and
  identify a custom User-Agent; keep volume low and personal.

## Layout

```
src/
  mlb_api.py   # MLB Stats API: schedule, rosters, last-5 game logs
  covers.py    # covers.com: consensus % + forum-post tally
  analysis.py  # advantage metric + the public-vs-stats decision
  main.py      # orchestration; writes output/picks_<date>.json
.github/workflows/daily.yml
output/        # generated picks_<date>.json files
```
