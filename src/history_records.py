"""
Multi-season mismatch base rates, from free data only.

WHY THIS EXISTS
The question — is a short price on a big mismatch a tell? — died on sample
size: 57 games, and those 57 were mostly five teams' bad seasons (Colorado 40,
Kansas City 36, the Angels 35, the Giants 33, the Athletics 28). A cell like
that says "Colorado was bad in 2026", not "short prices are a tell".

I said the fix was buying historical odds. That was half wrong. The odds are
the only part that is sold; RECORDS AND RESULTS ARE FREE AND UNLIMITED from
the MLB Stats API, back decades. And the core of the question does not need
odds at all:

    how often does a team this much worse actually win?

That is a base rate, and a base rate needs only schedules and results. Once it
is known across many seasons and many different bad teams, the prices we
already hold for 2026 can be compared against it. If sub-.400 underdogs beat
good teams more often than -180 implies, the short price is not a tell - the
LONG price is the mistake, and the other way round.

WHAT THIS BUILDS
Every completed regular-season game across several seasons, each team's
record BEFORE that game (running totals, so nothing leaks from the future),
and the outcome. Then win rates by quality gap, stated next to the break-even
a given price demands.

THE LEAK THIS AVOIDS
Using a team's END-OF-SEASON record to classify a game played in April would
label a team by what it became, not what it was. Records here are accumulated
game by game in date order and read strictly before the game they describe,
and games before a minimum number played are skipped, since a 2-1 record is
not evidence of anything.

Writes output/history_records.md.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from . import mlb_api

log = logging.getLogger("history_records")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
SEASONS = [2023, 2024, 2025, 2026]
MIN_PLAYED = 20        # a record means nothing before this many games


def season_games(year: int) -> list[dict]:
    """Every completed regular-season game in a year, in date order."""
    out = []
    try:
        data = mlb_api._get("schedule", sportId=mlb_api.SPORT_ID,
                            startDate=f"{year}-03-01", endDate=f"{year}-11-15",
                            gameType="R")
    except Exception as exc:
        log.warning("season %s fetch failed: %s", year, exc)
        return out
    for day in data.get("dates", []):
        date = day.get("date")
        for g in day.get("games", []):
            t = g.get("teams") or {}
            h, a = t.get("home") or {}, t.get("away") or {}
            hs, as_ = h.get("score"), a.get("score")
            state = ((g.get("status") or {}).get("abstractGameState") or "")
            if state != "Final" or not isinstance(hs, int) or not isinstance(as_, int):
                continue
            if hs == as_:
                continue
            out.append({
                "date": date, "season": year,
                "home": (h.get("team") or {}).get("name"),
                "away": (a.get("team") or {}).get("name"),
                "home_won": hs > as_,
            })
    out.sort(key=lambda g: g["date"])
    return out


def with_prior_records(games: list[dict]) -> list[dict]:
    """Attach each team's record BEFORE the game. Running totals in date
    order, so nothing from the future can leak in."""
    rec: dict = defaultdict(lambda: [0, 0])      # team -> [w, l], per season
    rows = []
    season = None
    for g in games:
        if g["season"] != season:
            rec = defaultdict(lambda: [0, 0])
            season = g["season"]
        h, a = g["home"], g["away"]
        if not h or not a:
            continue
        hw, hl = rec[h]
        aw, al = rec[a]
        hp, ap = hw + hl, aw + al
        if hp >= MIN_PLAYED and ap >= MIN_PLAYED:
            rows.append({**g,
                         "home_wpct": hw / hp, "away_wpct": aw / ap,
                         "home_played": hp, "away_played": ap})
        rec[h][0 if g["home_won"] else 1] += 1
        rec[a][1 if g["home_won"] else 0] += 1
    return rows


def _breakeven(american: int) -> float:
    return (abs(american) / (abs(american) + 100) if american < 0
            else 100 / (american + 100))


def build() -> str:
    md = ["# How often do mismatches actually resolve? (free data only)", "",
          "_Records and results are free and unlimited from the MLB Stats "
          "API; only the odds are sold. The core question — how often does a "
          "team this much worse actually win — needs no odds at all._", ""]

    allrows, per_season = [], {}
    for yr in SEASONS:
        gs = season_games(yr)
        rows = with_prior_records(gs)
        per_season[yr] = (len(gs), len(rows))
        allrows += rows
    md += ["| season | completed games | usable (both teams ≥20 played) |",
           "|---|---|---|"]
    for yr, (g, r) in per_season.items():
        md.append(f"| {yr} | {g:,} | {r:,} |")
    md += ["", f"- **total usable games: {len(allrows):,}**", ""]
    if len(allrows) < 1000:
        return "\n".join(md + ["Not enough history fetched.", ""])

    md += [f"_Against **1,221** from the board alone — and spread over "
           f"{len(SEASONS)} seasons, so a bad team in one year is a different "
           "team from a bad team in another. That is the part the 57-game "
           "cell could not give: variety, not just volume._", ""]

    # --- the core table ---------------------------------------------------
    rows = []
    for g in allrows:
        for team, opp, wpct, owpct, won in (
                (g["home"], g["away"], g["home_wpct"], g["away_wpct"], g["home_won"]),
                (g["away"], g["home"], g["away_wpct"], g["home_wpct"], not g["home_won"])):
            rows.append({"wpct": wpct, "owpct": owpct, "gap": wpct - owpct,
                         "won": won, "home": team == g["home"]})
    weak = [r for r in rows if r["wpct"] < 0.400]
    md += ["## When a sub-.400 team plays someone better", "",
           f"- sub-.400 team-games: **{len(weak):,}**", "",
           "| opponent quality | sub-.400 team's record | they win |",
           "|---|---|---|"]
    bands = [("opponent .400-.499", lambda r: 0.400 <= r["owpct"] < 0.500),
             ("opponent .500-.549", lambda r: 0.500 <= r["owpct"] < 0.550),
             ("opponent .550-.599", lambda r: 0.550 <= r["owpct"] < 0.600),
             ("opponent .600+", lambda r: r["owpct"] >= 0.600)]
    for label, test in bands:
        sub = [r for r in weak if test(r)]
        if len(sub) < 50:
            md.append(f"| {label} | {len(sub)} | _too few_ |")
            continue
        w = sum(1 for r in sub if r["won"])
        md.append(f"| {label} | {w}-{len(sub)-w} | **{w/len(sub):.1%}** |")
    md.append("")

    # --- what price would that justify? ----------------------------------
    md += ["## What those rates make the favourite worth", "",
           "_A favourite needs the break-even below to be worth its price. "
           "Compare against what the market actually offered on our board: "
           "28% of sub-.400 matchups were priced shorter than -180._", "",
           "| favourite price | break-even it demands | actual win rate vs "
           "sub-.400 |", "|---|---|---|"]
    for band_label, test in (("all sub-.400 opponents", lambda r: True),
                             ("and favourite .550+", lambda r: r["owpct"] >= 0.550)):
        sub = [r for r in weak if test(r)]
        if len(sub) < 50:
            continue
        favwin = 1 - (sum(1 for r in sub if r["won"]) / len(sub))
        md.append(f"| _{band_label}_ | — | **{favwin:.1%}** (n={len(sub):,}) |")
        for price in (-150, -180, -200, -250):
            be = _breakeven(price)
            verdict = "favourite is VALUE" if favwin > be else "favourite is short"
            md.append(f"| {price} | {be:.1%} | {verdict} |")
    md += ["", "_This is the base rate, not a betting rule: it ignores the "
           "starting pitchers, which is most of what a single MLB game turns "
           "on. It says what the CLASS of matchup is worth, which is the "
           "thing the 57-game cell could not say._", ""]

    # --- home/away and gap size -------------------------------------------
    md += ["## By how far apart the teams are", "",
           "| win% gap | favourite wins | n |", "|---|---|---|"]
    for lo, hi in ((0.05, 0.10), (0.10, 0.15), (0.15, 0.20), (0.20, 0.30), (0.30, 1.0)):
        sub = [r for r in rows if lo <= r["gap"] < hi]
        if len(sub) < 100:
            continue
        w = sum(1 for r in sub if r["won"])
        md.append(f"| {lo:.2f}–{hi:.2f} | **{w/len(sub):.1%}** | {len(sub):,} |")
    md += ["", "_Read this against the prices on the board: if a 0.20 gap "
           "wins 58% and the market asks -180 (64.3%), the favourite is short "
           "as a class and the underdog is the side with value — which is the "
           "tell, stated from base rates rather than from 57 games._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "history_records.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
