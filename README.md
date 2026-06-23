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

```
team_score = offense_rating + pitching_rating
  offense_rating  = avg OPS of the team's hitters over their last 5 games
  pitching_rating = (LEAGUE_ERA - era)/LEAGUE_ERA + (LEAGUE_WHIP - whip)/LEAGUE_WHIP
                    (probable starter, last 5 outings; higher = better)
```

The higher `team_score` has the advantage. Baselines `LEAGUE_ERA`/`LEAGUE_WHIP`
live in `src/analysis.py` — **tune these (and the formula) to taste.** Missing
data contributes 0 and is noted in the output.

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
