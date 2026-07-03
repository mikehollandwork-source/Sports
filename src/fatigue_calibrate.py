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

from . import espn, mlb_api, weather
from .analysis import _canon_abbr

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


def _team_abbrs(season: int) -> dict[int, str]:
    data = mlb_api._get("teams", sportId=mlb_api.SPORT_ID, season=season)
    return {t["id"]: t.get("abbreviation", "") for t in data.get("teams", [])}


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


def _profit(ml: int, won: bool) -> float:
    """$1 profit at American ML (loss = -1)."""
    return (ml / 100 if ml > 0 else 100 / -ml) if won else -1.0


def collect_roi(end: str, days: int) -> list[dict]:
    """One row per completed game keyed on the AWAY team's fatigue (its road_streak
    etc.), joined with ESPN closing moneylines. This is the clean ROI frame: every
    game has exactly one away team, so no dedup - and the bet we test is fading the
    road team (betting the home team) at its closing price."""
    season = int(end[:4])
    lo, hi = (_d(end) - dt.timedelta(days=days)).isoformat(), end
    seqs = _sequences(season)
    _, coords = _team_meta(season)
    abbrs = _team_abbrs(season)

    lines_cache: dict[str, list[dict]] = {}

    def closing(date: str, away_ab: str, home_ab: str) -> tuple[int | None, int | None]:
        if date not in lines_cache:
            try:
                lines_cache[date] = espn.lines(date)
            except Exception as exc:
                log.warning("espn lines %s failed: %s", date, exc)
                lines_cache[date] = []
        a, h = _canon_abbr(away_ab), _canon_abbr(home_ab)
        for e in lines_cache[date]:
            if _canon_abbr(e["away_abbr"]) == a and _canon_abbr(e["home_abbr"]) == h:
                return e.get("away_current"), e.get("home_current")
        return None, None

    rows = []
    for tid, games in seqs.items():
        for i, g in enumerate(games):
            if g["home"] or not (lo <= g["date"] <= hi):
                continue   # key each game off its AWAY team
            away_ml, home_ml = closing(g["date"], abbrs.get(tid, ""),
                                       abbrs.get(g["opp_id"], ""))
            prof = _profile(games, i, tid, coords)
            rows.append({"date": g["date"], "road_streak": prof["road_streak"],
                         "days_straight": prof["days_straight"],
                         "games_last7": prof["games_last7"],
                         "home_won": not g["won"],   # g["won"] is the away team's result
                         "away_ml": away_ml, "home_ml": home_ml})
    priced = sum(1 for r in rows if r["home_ml"] is not None)
    log.info("ROI frame: %d games, %d with a closing line (%s..%s)",
             len(rows), priced, lo, hi)
    return rows


def _roi_band(rows: list[dict], lo: int, hi: int) -> dict:
    """Fade the away team on a road_streak in [lo,hi]: bet the HOME team at its
    closing ML. Reports bets, home win rate, and ROI (units per $1 bet)."""
    bets = [r for r in rows if lo <= r["road_streak"] <= hi and r["home_ml"] is not None]
    if not bets:
        return {"band": f"{lo}-{hi if hi < 99 else '+'}", "bets": 0,
                "home_win": None, "roi": None}
    u = sum(_profit(int(r["home_ml"]), r["home_won"]) for r in bets)
    w = sum(1 for r in bets if r["home_won"])
    return {"band": f"{lo}-{hi if hi < 99 else '+'}", "bets": len(bets),
            "home_win": round(w / len(bets), 3), "roi": round(u / len(bets), 3)}


def roi_analyze(rows: list[dict]) -> dict:
    priced = [r for r in rows if r["home_ml"] is not None]
    base_u = sum(_profit(int(r["home_ml"]), r["home_won"]) for r in priced)
    return {
        "games": len(rows),
        "games_priced": len(priced),
        "baseline_bet_home_roi": round(base_u / len(priced), 3) if priced else None,
        "fade_road_team_by_depth": [_roi_band(rows, lo, hi)
                                    for lo, hi in ((1, 2), (3, 5), (6, 8), (9, 99))],
    }


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
    roi = rep.get("roi")
    if roi:
        out += ["", "## ROI vs the CLOSING moneyline — fade the road team (bet home)",
                f"Betting the home team at its ESPN closing price, by the away team's "
                f"road_streak. Baseline (bet every home team): "
                f"**{_pct(roi['baseline_bet_home_roi'])} ROI** over "
                f"{roi['games_priced']}/{roi['games']} priced games. If fatigue is a "
                f"real *market* edge, ROI should climb with trip depth.", "",
                "| away team's road_streak | bets | home win | ROI |", "|---|---|---|---|"]
        for b in roi["fade_road_team_by_depth"]:
            hw = f"{b['home_win']:.0%}" if b["home_win"] is not None else "—"
            out.append(f"| {b['band']} | {b['bets']} | {hw} | {_pct(b['roi'])} |")
        out += ["", "_ROI = units per $1. Around −4-5% is the no-edge / vig baseline; "
                "a band clearly ABOVE baseline (toward 0 or positive) that grows with "
                "depth is a real, priceable fatigue edge worth betting._"]
    out += ["", "_Point-in-time, no lookahead. Win-rate cuts above are the raw signal; "
            "the ROI table is the money test against the closing line._"]
    return "\n".join(out)


def _pct(x: float | None) -> str:
    return f"{x:+.1%}" if x is not None else "—"


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
    # the money test: ROI vs ESPN closing moneylines (slow - one odds fetch per
    # game-day; wrapped so a partial/odds failure still leaves the win-rate report)
    try:
        rep["roi"] = roi_analyze(collect_roi(args.end, args.days))
    except Exception as exc:
        log.warning("ROI pass failed (win-rate report still written): %s", exc)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "fatigue_calibration.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "fatigue_calibration.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
