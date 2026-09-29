"""
Most likely home run from the teams the board picked. Raw numbers only.

WHAT THIS DOES AND DOES NOT USE
No prop odds, no implied probabilities, no market anything - the instruction was
raw numbers, and there is a second reason to honour that: `ev_model` showed our
signals add nothing on top of a market price, so a number built FROM the market
would just be the market with extra steps. This is built from counting stats.

THE ESTIMATE
Everything reduces to one quantity: the chance this hitter homers in one plate
appearance, then compounded over a game's worth of them.

    p_season   HR / PA over the season
    p_recent   HR / PA over the last RECENT_GAMES games
    blend      p_recent shrunk toward p_season by its own sample size, so a
               2-for-8 hot streak cannot outvote 500 PA. w = pa / (pa + SHRINK)
    pitcher    opposing starter's HR/9 relative to league, clamped
    park       the board's park factor for the venue

    P(1+ HR) = 1 - (1 - p_adj) ** EXPECTED_PA

WHY A "SUPERSTAR" FILTER EXISTS
Ranking on rate alone hands you a bench bat with 3 homers in 40 PA, whose rate
is noise. MIN_PA and MIN_HR require a real season behind the number - the
question asked for a superstar, and that is also the statistically sounder read.

WHAT THIS IS NOT
A recommendation to bet a home-run prop. Those price around +300 to +900 and
this makes no claim about the price - only about which bat is likeliest. The
prop record in this repo is -6.7% on singles, and nothing here changes that.

Writes output/hr_pick_<date>.md.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import sys
import zoneinfo
from pathlib import Path

from . import mlb_api

log = logging.getLogger("hr_pick")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

RECENT_GAMES = 15      # power form window
SHRINK = 60            # PA at which recent form gets half the weight
EXPECTED_PA = 4.2      # a regular's plate appearances in a game
MIN_PA = 250           # "superstar": a real season behind the rate
MIN_HR = 10
LEAGUE_HR9 = 1.15      # league-average HR allowed per 9 innings
PITCHER_CLAMP = (0.70, 1.40)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _recent_power(pid: int, season: int, n: int = RECENT_GAMES) -> tuple[int, int]:
    """(HR, PA) over the player's last n games."""
    hr = pa = 0
    for sp in mlb_api._full_gamelog(pid, "hitting", season)[-n:]:
        st = sp.get("stat", {})
        hr += int(st.get("homeRuns", 0) or 0)
        pa += int(st.get("plateAppearances", 0) or 0)
    return hr, pa


def _pitcher_factor(pid: int | None, season: int) -> tuple[float, str]:
    if not pid:
        return 1.0, "no probable starter — league average assumed"
    try:
        line = mlb_api.pitcher_season_line(pid, season)
    except Exception:
        return 1.0, "starter line unavailable"
    ip = line.get("ip") or 0
    if ip < 20:
        return 1.0, f"only {ip:.0f} IP — league average assumed"
    hr9 = (line["hr"] * 9.0) / ip
    return _clamp(hr9 / LEAGUE_HR9, *PITCHER_CLAMP), f"{hr9:.2f} HR/9 over {ip:.0f} IP"


def candidates(date: str) -> list[dict]:
    try:
        day = json.loads((OUTPUT_DIR / f"picks_{date}.json").read_text())
    except (OSError, ValueError):
        return []
    season = mlb_api._season_for(date)
    games = {g.game_pk: g for g in mlb_api.schedule_for(date)}
    out: list[dict] = []

    for g in day.get("games", []):
        pc = g.get("pick_criteria") or {}
        if pc.get("play") != "pick" or not pc.get("bet_team"):
            continue
        team_name = pc["bet_team"]
        pk = g.get("game_pk")
        sched = games.get(pk)
        if not sched:
            continue
        is_home = sched.home.name == team_name
        side = sched.home if is_home else sched.away
        opp = sched.away if is_home else sched.home
        park = g.get("park_factor") or 1.0
        # Team.probable_pitcher is a Player, not an id
        prob = getattr(opp, "probable_pitcher", None)
        pf, pnote = _pitcher_factor(getattr(prob, "player_id", None), season)
        opp_name = getattr(prob, "name", None) or "TBD"

        try:
            hitters = mlb_api.lineup(pk, side.team_id, date, is_home)
        except Exception as exc:
            log.warning("lineup failed for %s: %s", team_name, exc)
            continue
        ids = [h.player_id for h in hitters if getattr(h, "player_id", None)]
        season_stats = mlb_api._season_hitting(ids, season)

        for h in hitters:
            pid = getattr(h, "player_id", None)
            st = season_stats.get(pid) or {}
            try:
                pa = int(st.get("plateAppearances", 0) or 0)
                hr = int(st.get("homeRuns", 0) or 0)
                ab = float(st.get("atBats", 0) or 0)
                hits = float(st.get("hits", 0) or 0)
                tb = float(st.get("totalBases", 0) or 0)
            except (TypeError, ValueError):
                continue
            if pa < MIN_PA or hr < MIN_HR:
                continue                      # not a superstar bat; rate is noise
            p_season = hr / pa
            rhr, rpa = _recent_power(pid, season)
            p_recent = (rhr / rpa) if rpa else p_season
            w = rpa / (rpa + SHRINK)
            p_blend = w * p_recent + (1 - w) * p_season
            p_adj = _clamp(p_blend * pf * float(park), 0.0, 0.25)
            p_game = 1 - (1 - p_adj) ** EXPECTED_PA
            iso = ((tb - hits) / ab) if ab else 0.0
            out.append({
                "team": team_name, "matchup": g.get("matchup"), "name": h.name,
                "pa": pa, "hr": hr, "iso": round(iso, 3),
                "season_rate": p_season, "recent_hr": rhr, "recent_pa": rpa,
                "recent_rate": p_recent, "blend": p_blend, "weight": round(w, 2),
                "pitcher": opp_name, "pitcher_factor": round(pf, 2),
                "pitcher_note": pnote, "park": round(float(park), 3),
                "p_game": p_game,
            })
    out.sort(key=lambda r: -r["p_game"])
    return out


def build(date: str) -> str:
    rows = candidates(date)
    md = [f"# Most likely home run — {date}", "",
          "_Raw counting stats only. No prop odds, no implied probabilities: the "
          "instruction was raw numbers, and a number built from the market would "
          "just be the market with extra steps._", ""]
    if not rows:
        md += ["No board picks with a usable lineup, so nothing to rank.", "",
               "_This needs a board with at least one pick AND a posted lineup. "
               "Lineups are usually up a few hours before first pitch._", ""]
        return "\n".join(md)

    top = rows[0]
    md += [f"## {top['name']} — {top['team']}", "",
           f"**{top['p_game']:.1%}** chance of a home run tonight "
           f"({top['matchup']}, vs {top['pitcher']}).", "",
           "| input | value |", "|---|---|",
           f"| season | {top['hr']} HR in {top['pa']} PA "
           f"({top['season_rate']:.3%} per PA) |",
           f"| last {RECENT_GAMES} games | {top['recent_hr']} HR in "
           f"{top['recent_pa']} PA ({top['recent_rate']:.3%} per PA) |",
           f"| form weight | {top['weight']:.0%} recent, "
           f"{1-top['weight']:.0%} season |",
           f"| ISO (raw power) | {top['iso']:.3f} |",
           f"| opposing starter | {top['pitcher']} — {top['pitcher_note']} "
           f"→ ×{top['pitcher_factor']} |",
           f"| park factor | ×{top['park']} |",
           f"| blended rate per PA | {top['blend']:.3%} |",
           f"| over {EXPECTED_PA} PA | **{top['p_game']:.1%}** |", ""]

    md += ["## Full ranking", "",
           "| # | hitter | team | HR/PA season | last "
           f"{RECENT_GAMES} | ISO | pitcher × | park × | P(HR) |",
           "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        md.append(f"| {i} | {r['name']} | {r['team']} | "
                  f"{r['hr']}/{r['pa']} ({r['season_rate']:.2%}) | "
                  f"{r['recent_hr']}/{r['recent_pa']} | {r['iso']:.3f} | "
                  f"×{r['pitcher_factor']} | ×{r['park']} | "
                  f"**{r['p_game']:.1%}** |")
    md += ["", f"_Filtered to ≥{MIN_PA} PA and ≥{MIN_HR} HR: ranking on rate "
           "alone hands you a bench bat with 3 homers in 40 PA._", "",
           "_Not a bet recommendation. HR props price around +300 to +900 and "
           "nothing here speaks to the price; this repo's prop singles record is "
           "-6.7%._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    date = (sys.argv[1] if len(sys.argv) > 1
            else dt.datetime.now(EASTERN).date().isoformat())
    md = build(date)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / f"hr_pick_{date}.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
