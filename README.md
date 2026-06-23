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
4. **Flag the edge** — if the statistically-advantaged team is *not* the public's
   majority side, that team is added to the day's `picks`.

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
(a team that feasted at Coors gets discounted). The full reported line is
AVG / OBP / SLG / OPS / ISO / wOBA / BB% / K% / SB-rate.

**Pitching** — FIP (skill, strips out defense/luck), starter + bullpen:

```
combined_FIP   = 0.55 * starter_FIP + 0.45 * bullpen_FIP   (last 5 outings)
pitching_index = (LEAGUE_FIP - combined_FIP) / LEAGUE_FIP
```

The team with the higher `team_score` has the advantage. **Every weight,
league baseline, and the wOBA/FIP constants live at the top of
`src/analysis.py`** — tune them in one place. Missing data contributes 0.

## Win condition (runs target + last-5 back-test)

On top of the advantage score, each game gets a concrete, countable **win
condition** per team — the runs total they'd need to beat the opponent — plus how
often they actually hit it recently:

```
expected opponent runs = opponent's last-5 runs/game * (team combined FIP / LEAGUE_FIP)
runs_to_win            = floor(expected opponent runs) + 1
hit_in_last5           = # of the team's last 5 games scoring >= runs_to_win
```

So a strong-pitching team facing a mild offense gets a low bar; a weak-pitching
team facing a hot offense gets a high one. Reported per team as
`runs_to_win`, `expected_opponent_runs`, `hit_in_last5`, `hit_rate`, and the raw
`last5_runs_scored`. This is a *reporting* signal today (it doesn't change the
flagged pick) — easy to fold into the decision later if you want.

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
  firewalled there). The selectors/URLs in `src/covers.py` are best-effort and
  **will likely need a small tweak after the first live Actions run.** Every
  covers parser fails *soft* — on any problem it logs a warning and returns empty
  data, so the MLB-stats analysis still produces output. Check the Actions log
  for `selectors likely need updating` warnings.
- **Forum sentiment is a blunt heuristic.** "Majority side" from forum text is a
  raw mention tally — it does not understand fades, sarcasm, or parlays. Treat
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
