"""
Which hitter on a given team records a hit in almost every game the team wins?

WHAT IS COMPUTED
`props.best_hit_prop` already answers this for the single best bat. This prints
the whole lineup ranked, with the context the question asks for: tonight's
opposing starter and each hitter's record against him, the park, and the
board's own hot/cold form read.

  hit_rate_in_wins = team wins in which the hitter recorded >=1 hit
                     ------------------------------------------------
                     team wins in which the hitter had a plate appearance

WHY THAT NUMBER IS WEAKER THAN IT SOUNDS - READ BEFORE BETTING IT
It conditions on the outcome. A team that wins usually hit well, so EVERY
regular's hit rate rises inside wins; the statistic partly measures "did the
offence show up", which is the same thing that produced the win. It is not a
forecast of tonight, because tonight's win is not yet known.

The honest comparison is against the hitter's hit rate in ALL games, printed
beside it. A regular who gets a hit in 88% of wins but 70% of all games is
mostly telling you the team wins when he hits. A hitter whose two numbers are
close is the more dependable bat.

The real bar is the price. A 1+ hit prop is typically around -200, which needs
about 67% to break even, and this system's own settled prop singles run at
-6.7% ROI. A 78% hit-in-wins rate is not an edge at -250.

Everything comes from the MLB Stats API and the board - no outside sources.

Writes output/hit_in_wins.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import mlb_api, props

log = logging.getLogger("hit_in_wins")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
MIN_WINS = 12          # mirrors props.MIN_WINS_PLAYED
MIN_AVG_PA = 3.2       # mirrors props.MIN_AVG_PA


def _board_game(date: str, team: str) -> dict | None:
    try:
        d = json.loads((OUTPUT_DIR / f"picks_{date}.json").read_text())
    except (OSError, ValueError):
        return None
    for g in d.get("games", []):
        if team.lower() in (g.get("matchup") or "").lower():
            return g
    return None


def _rate(log_rows: list, pks: set | None) -> tuple[int, int, float]:
    """(games with >=1 hit, games played, total PA) over `pks` (all games if None)."""
    hit = played = 0
    pa_total = 0.0
    for s in log_rows:
        pk = (s.get("game") or {}).get("gamePk")
        if pks is not None and pk not in pks:
            continue
        st = s.get("stat") or {}
        try:
            pa = float(st.get("plateAppearances", 0) or 0)
            hits = float(st.get("hits", 0) or 0)
        except (TypeError, ValueError):
            continue
        if pa < 1:
            continue
        played += 1
        pa_total += pa
        if hits >= 1:
            hit += 1
    return hit, played, pa_total


def analyse(date: str, team: str) -> str:
    md = [f"# {team} — who hits when they win?", "",
          f"_asked of {date}; MLB Stats API and this board only_", ""]

    g = _board_game(date, team)
    if not g:
        return "\n".join(md + [f"No {team} game on the {date} board.", ""])

    matchup = g["matchup"]
    away, home = matchup.split(" @ ")
    is_home = team.lower() in home.lower()
    sa = g.get("statistical_advantage") or {}
    side = "home" if is_home else "away"          # the team asked about
    opp_side = "away" if is_home else "home"      # their opponent
    opp = (sa.get(opp_side) or {})
    sp_name = opp.get("probable_pitcher") or "TBD"
    sp_hand = opp.get("starter_hand") or "?"
    park = g.get("park_factor")

    # team + pitcher ids from the schedule (the board stores names, not ids)
    team_id = pitcher_id = None
    game_pk = g.get("game_pk")
    try:
        for sg in mlb_api.schedule_for(date):
            if sg.game_pk != game_pk:
                continue
            mine = sg.home if is_home else sg.away
            other = sg.away if is_home else sg.home
            team_id = mine.team_id
            if other.probable_pitcher:
                pitcher_id = other.probable_pitcher.player_id
                sp_name = other.probable_pitcher.name or sp_name
                sp_hand = other.probable_pitcher.hand or sp_hand
            break
    except Exception as exc:
        log.warning("schedule fetch failed: %s", exc)
    if team_id is None:
        return "\n".join(md + ["Could not resolve the team id from the schedule.", ""])

    md += [f"- **{matchup}** · {g.get('venue') or '?'} · park factor "
           f"**{park}**",
           f"- opposing starter: **{sp_name} ({sp_hand})**",
           f"- board form read for this lineup: delta "
           f"**{((g.get('form') or {}).get(side) or {}).get('delta')}**", ""]

    wins = props._team_win_pks(team_id, date)
    md += [f"- team wins this season in the sample: **{len(wins)}**", ""]
    if len(wins) < MIN_WINS:
        return "\n".join(md + ["Too few wins to compute a rate.", ""])

    try:
        bats = mlb_api.lineup(game_pk, team_id, date, is_home)[:props.MAX_LINEUP_BATS]
    except Exception as exc:
        return "\n".join(md + [f"Lineup unavailable: {exc}", ""])

    season = int(date[:4])
    form_side = (g.get("form") or {}).get(side) or {}
    hot = {p["name"]: p.get("delta") for p in (form_side.get("hot") or [])}
    cold = {p["name"]: p.get("delta") for p in (form_side.get("cold") or [])}

    rows = []
    for p in bats:
        rec = props._game_log(p.player_id, season)
        w_hit, w_played, w_pa = _rate(rec, wins)
        a_hit, a_played, _ = _rate(rec, None)
        if w_played < MIN_WINS or (w_pa / max(w_played, 1)) < MIN_AVG_PA:
            continue
        bvp = {}
        if pitcher_id:
            try:
                bvp = mlb_api.batter_vs_pitcher(p.player_id, pitcher_id) or {}
            except Exception:
                bvp = {}
        rows.append({
            "name": p.name,
            "win_rate": w_hit / w_played, "w_hit": w_hit, "w_played": w_played,
            "all_rate": (a_hit / a_played) if a_played else 0.0,
            "a_hit": a_hit, "a_played": a_played,
            "avg_pa": w_pa / w_played,
            "bvp_pa": bvp.get("pa") or 0, "bvp_ops": bvp.get("ops") or 0.0,
            "form": hot.get(p.name, cold.get(p.name)),
        })
    if not rows:
        return "\n".join(md + ["No hitter clears the everyday-bat guard.", ""])

    rows.sort(key=lambda r: (-r["win_rate"], -r["avg_pa"]))
    md += ["## Ranked by hit rate in team wins", "",
           "| hitter | hit in wins | in ALL games | gap | avg PA | vs " +
           f"{sp_name} | form |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        gap = (r["win_rate"] - r["all_rate"]) * 100
        bvp = (f"{r['bvp_ops']:.3f} OPS / {r['bvp_pa']} PA"
               if r["bvp_pa"] else "never faced")
        form = (f"{r['form']:+.3f}" if isinstance(r["form"], (int, float)) else "—")
        md.append(f"| {r['name']} | **{r['win_rate']:.0%}** "
                  f"({r['w_hit']}/{r['w_played']}) | {r['all_rate']:.0%} "
                  f"({r['a_hit']}/{r['a_played']}) | {gap:+.0f} pts | "
                  f"{r['avg_pa']:.1f} | {bvp} | {form} |")
    md.append("")

    top = rows[0]
    steady = min(rows, key=lambda r: abs(r["win_rate"] - r["all_rate"]))
    md += ["## Reading it", "",
           f"- highest hit rate in wins: **{top['name']}** at "
           f"{top['win_rate']:.0%} ({top['w_hit']}/{top['w_played']}), against "
           f"{top['all_rate']:.0%} in all games — a gap of "
           f"{(top['win_rate']-top['all_rate'])*100:+.0f} points",
           f"- least outcome-dependent: **{steady['name']}**, "
           f"{steady['win_rate']:.0%} in wins vs {steady['all_rate']:.0%} "
           "overall, so his hitting is closest to independent of whether the "
           "team won", "",
           "_The **gap** column is the part to distrust. A large positive gap "
           "means the number is describing wins, not the hitter: he hits when "
           "the offence rolls, which is when the team wins. The small-gap bat "
           "is the more dependable one._", "",
           f"_Park factor {park} and the opposing hand ({sp_hand}) shift the "
           "whole lineup, not one hitter, so neither changes this ranking. The "
           "vs-starter column is usually a handful of plate appearances and "
           "should not move a decision._", "",
           "_Price check: a 1+ hit prop near -200 needs ~67% to break even, "
           "and this system's settled prop singles run -6.7% ROI. Nothing "
           "above clears that on its own._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.datetime.now(EASTERN).date().isoformat())
    ap.add_argument("--team", default="Cleveland Guardians")
    a = ap.parse_args()
    md = analyse(a.date, a.team)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "hit_in_wins.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
