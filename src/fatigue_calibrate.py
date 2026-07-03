"""
Travel / schedule fatigue calibration.

Everything here is reconstructed from the per-team season game logs we already
cache (date + isHome + opponent + runs), plus the ballpark coordinates already
in weather.STADIUMS - no new data source. For every completed game we compute,
point-in-time (only games strictly before it), each team's fatigue profile:

  road_streak   consecutive away games ending with this one (0 if home) -
                "deep in a road trip"
  days_straight consecutive calendar days played in a row (3+ = 3-in-3)
  games_last7   games in the 7 days before this one (schedule density)
  travel_mi     miles from the previous game's park to this one
  tz_east       time zones crossed since the previous game, EAST positive
                (~15 deg longitude/hour) - eastward is the harder body-clock jump

Then it back-tests each: head-to-head, when the two teams differ on a signal,
does the MORE-fatigued team win LESS? Plus a few buckets (6+ straight road games,
3-in-3, crossed a zone east). Only signals that show a real, sized dip should
graduate to a margin tilt - and even then display-first. Same discipline as the
clutch and umpire calibrations (one of which earned it, one didn't).

Writes output/fatigue_calibration.{json,md}. Cheap (30 cached game logs + a
teams lookup). Runs on Actions via calibrate.yml signal "fatigue".
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import math
import zoneinfo
from pathlib import Path

from . import mlb_api, weather

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("fatigue_calibrate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")


def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def _haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle miles between (lat, lon) points."""
    R = 3958.8
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def _team_meta(season: int) -> tuple[dict[int, str], dict[int, tuple[float, float]]]:
    """(team_id -> name, team_id -> home (lat, lon)). Coords map the API venue
    name onto weather.STADIUMS; unmapped parks just drop travel for those games."""
    data = mlb_api._get("teams", sportId=mlb_api.SPORT_ID, season=season)
    names: dict[int, str] = {}
    coords: dict[int, tuple[float, float]] = {}
    for t in data.get("teams", []):
        names[t["id"]] = t.get("name", "")
        spot = weather.STADIUMS.get(t.get("venue", {}).get("name", ""))
        if spot:
            coords[t["id"]] = (spot[0], spot[1])
    return names, coords


def _sequences(season: int) -> dict[int, list[dict]]:
    """team_id -> its games in date order: {date, home, opp_id, won}."""
    names, _ = _team_meta(season)
    seqs: dict[int, list[dict]] = {}
    for tid in names:
        try:
            hit, pit = mlb_api._team_gamelog(tid, season)
        except Exception as exc:
            log.warning("gamelog %s failed: %s", tid, exc)
            continue
        games = []
        for sp in hit:
            date = sp.get("date", "")
            rs = int(sp.get("stat", {}).get("runs", 0) or 0)
            ra = int(pit.get(date, {}).get("stat", {}).get("runs", 0) or 0)
            games.append({"date": date, "home": bool(sp.get("isHome")),
                          "opp_id": sp.get("opponent", {}).get("id"), "won": rs > ra})
        games.sort(key=lambda g: g["date"])
        seqs[tid] = games
    return seqs


def _profile(games: list[dict], i: int, tid: int,
             coords: dict[int, tuple[float, float]]) -> dict:
    """Fatigue profile for team `tid`'s game at index i, from games up to it."""
    g = games[i]
    # consecutive away games ending here (inclusive)
    streak, j = 0, i
    while j >= 0 and not games[j]["home"]:
        streak += 1
        j -= 1
    # consecutive calendar days in a row ending here
    days, j = 1, i
    while j - 1 >= 0 and (_d(games[j]["date"]) - _d(games[j - 1]["date"])).days == 1:
        days += 1
        j -= 1
    d0 = _d(g["date"])
    last7 = sum(1 for gg in games[:i] if 0 < (d0 - _d(gg["date"])).days <= 7)
    travel_mi = tz_east = None
    if i >= 1:
        prev = games[i - 1]
        v_prev = coords.get(tid if prev["home"] else prev["opp_id"])
        v_cur = coords.get(tid if g["home"] else g["opp_id"])
        if v_prev and v_cur:
            travel_mi = _haversine(v_prev, v_cur)
            tz_east = (v_cur[1] - v_prev[1]) / 15.0   # +east (longitude rises)
    return {"road_streak": streak, "days_straight": days, "games_last7": last7,
            "travel_mi": travel_mi, "tz_east": tz_east, "won": g["won"],
            "home": g["home"]}


def collect(end: str, days: int) -> list[dict]:
    """One row per completed game (deduped): each team's fatigue profile + who
    won. Restricted to the [end-days, end] window."""
    season = int(end[:4])
    lo, hi = (_d(end) - dt.timedelta(days=days)).isoformat(), end
    seqs = _sequences(season)
    _, coords = _team_meta(season)
    # date+opp index so a game can be matched from the opponent's sequence
    index: dict[int, dict[str, int]] = {
        tid: {g["date"] + str(g["opp_id"]): i for i, g in enumerate(games)}
        for tid, games in seqs.items()}

    rows, seen = [], set()
    for tid, games in seqs.items():
        for i, g in enumerate(games):
            if not (lo <= g["date"] <= hi):
                continue
            oid = g["opp_id"]
            key = (g["date"], min(tid, oid), max(tid, oid))
            if key in seen or oid not in seqs:
                continue
            oi = index.get(oid, {}).get(g["date"] + str(tid))
            if oi is None:
                continue
            seen.add(key)
            mine = _profile(games, i, tid, coords)
            theirs = _profile(seqs[oid], oi, oid, coords)
            rows.append({"me": mine, "opp": theirs, "won": mine["won"]})
    log.info("collected %d games (%s..%s)", len(rows), lo, hi)
    return rows


def _h2h(rows: list[dict], key: str, higher_is_tireder: bool = True) -> dict:
    """Head-to-head: when the two teams differ on `key`, the MORE-fatigued team's
    win rate (want < 50% if fatigue bites). None values skip the game."""
    n = won = 0
    for r in rows:
        a, b = r["me"].get(key), r["opp"].get(key)
        if a is None or b is None or a == b:
            continue
        me_tireder = (a > b) if higher_is_tireder else (a < b)
        n += 1
        won += r["won"] if me_tireder else (0 if r["won"] else 1)
    return {"n": n, "tired_team_won": round(won / n, 3) if n else None}


def _bucket(rows: list[dict], key: str, lo: float, label: str) -> dict:
    """Win rate of a team whose `key` >= lo (the fatigued side), regardless of
    the opponent's state."""
    n = won = 0
    for r in rows:
        for who in ("me", "opp"):
            v = r[who].get(key)
            if v is None or v < lo:
                continue
            n += 1
            side_won = r["won"] if who == "me" else (not r["won"])
            won += 1 if side_won else 0
    return {"label": label, "n": n, "win_rate": round(won / n, 3) if n else None}


def _away_by_streak(rows: list[dict]) -> list[dict]:
    """The KEY control: among AWAY games only, win rate bucketed by the away
    team's road_streak. This removes the home-field confound (a road_streak is
    only >0 for the away team), so a decline ACROSS buckets is real incremental
    fatigue; flat = the earlier 47% was just ordinary away disadvantage."""
    bands = [(1, 2), (3, 5), (6, 8), (9, 99)]
    out = []
    for lo, hi in bands:
        n = won = 0
        for r in rows:
            for who in ("me", "opp"):
                p = r[who]
                if p["home"] or not (lo <= p["road_streak"] <= hi):
                    continue
                n += 1
                won += 1 if (r["won"] if who == "me" else not r["won"]) else 0
        out.append({"road_streak": f"{lo}-{hi if hi < 99 else '+'}", "away_games": n,
                    "win_rate": round(won / n, 3) if n else None})
    return out


def analyze(rows: list[dict]) -> dict:
    return {
        "games": len(rows),
        "away_win_rate_by_road_streak": _away_by_streak(rows),
        "head_to_head": {
            "road_streak (deeper trip)": _h2h(rows, "road_streak"),
            "days_straight (less rest)": _h2h(rows, "days_straight"),
            "games_last7 (denser)": _h2h(rows, "games_last7"),
            "tz_east (traveled east)": _h2h(rows, "tz_east"),
            "travel_mi (farther)": _h2h(rows, "travel_mi"),
        },
        "buckets": [
            _bucket(rows, "road_streak", 6, "6+ straight road games"),
            _bucket(rows, "road_streak", 9, "9+ straight road games"),
            _bucket(rows, "days_straight", 3, "3+ games in a row (no off day)"),
            _bucket(rows, "games_last7", 6, "6+ games in last 7 days"),
            _bucket(rows, "tz_east", 1.0, "crossed 1+ time zone EAST"),
            _bucket(rows, "tz_east", 2.0, "crossed 2+ time zones EAST"),
            _bucket(rows, "travel_mi", 1500, "1500+ mile trip in"),
        ],
    }


def summary_md(rep: dict) -> str:
    a = rep["analysis"]
    out = [f"# Travel/schedule fatigue calibration — {rep['window']}", "",
           f"**{a['games']} games.**", "",
           "## Road-trip depth, home-field controlled (the decisive cut)",
           "AWAY games only — win rate by the away team's road_streak. A decline "
           "across bands = real incremental fatigue; flat = just ordinary away "
           "disadvantage. (Away baseline ≈ 47%.)", "",
           "| away team's road_streak | away games | win rate |", "|---|---|---|"]
    for b in a["away_win_rate_by_road_streak"]:
        wr = f"{b['win_rate']:.0%}" if b["win_rate"] is not None else "—"
        out.append(f"| {b['road_streak']} | {b['away_games']} | {wr} |")
    out += ["",
           "## Head-to-head — the MORE-fatigued team's win rate (want < 50%)",
           "", "| signal | games | tired team won |", "|---|---|---|"]
    for label, h in a["head_to_head"].items():
        wr = f"{h['tired_team_won']:.0%}" if h["tired_team_won"] is not None else "—"
        out.append(f"| {label} | {h['n']} | {wr} |")
    out += ["", "## Buckets — the fatigued side's win rate",
            "", "| condition | games | win rate |", "|---|---|---|"]
    for b in a["buckets"]:
        wr = f"{b['win_rate']:.0%}" if b["win_rate"] is not None else "—"
        out.append(f"| {b['label']} | {b['n']} | {wr} |")
    out += ["", "_Point-in-time, no lookahead. < ~47% for the fatigued side on a real "
            "sample = a genuine dip worth a small margin tilt; ~50% = noise, stays out._"]
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Travel/schedule fatigue calibration")
    p.add_argument("--days", type=int, default=120)
    p.add_argument("--end", default=yesterday_eastern())
    args = p.parse_args()

    rows = collect(args.end, args.days)
    rep = {"window": f"{(_d(args.end) - dt.timedelta(days=args.days)).isoformat()} → "
                     f"{args.end} ({args.days} days)",
           "analysis": analyze(rows)}
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "fatigue_calibration.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "fatigue_calibration.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
