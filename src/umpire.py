"""
HP-umpire strike-zone tendencies, built from free MLB boxscores.

Build pass (run via calibrate.yml, signal "ump"): every final game this season →
HP umpire + both lineups' K/BB/runs from the boxscore. Aggregates per ump into
output/ump_tendencies_<season>.json: {games, k_pg, bb_pg, r_pg, k_extra} where
k_extra = Ks/game above the league average (leave-self-out). Also back-tests the
signal it feeds: in games run by a big-zone ump, does the lower-strikeout team
win more often than under a neutral ump?

Live use (analysis.statistical_favorite): a big-zone ump (k_extra >= UMP_K_EXTRA
on >= UMP_MIN_GAMES) tilts the margin toward the lower-K lineup. The ump is only
posted near first pitch, so the tilt kicks in at the pre-game refresh; a missing
table or unknown ump = no tilt (fail-soft).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from .mlb_api import SPORT_ID, _get, team_season_offense

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("umpire")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

_TABLE_CACHE: dict[int, dict | None] = {}


def _table_path(season: int) -> Path:
    return OUTPUT_DIR / f"ump_tendencies_{season}.json"


def tendency(name: str | None, season: int) -> dict | None:
    """The committed tendency row for an ump, or None (unknown ump / no table)."""
    if not name:
        return None
    if season not in _TABLE_CACHE:
        try:
            _TABLE_CACHE[season] = json.loads(_table_path(season).read_text())
        except (OSError, ValueError):
            _TABLE_CACHE[season] = None
    tab = _TABLE_CACHE[season]
    return (tab or {}).get("umps", {}).get(name)


def _final_game_pks(season: int, start: str, end: str) -> list[int]:
    data = _get("schedule", sportId=SPORT_ID, startDate=start, endDate=end)
    pks = []
    for day in data.get("dates", []):
        for g in day.get("games", []):
            if g.get("status", {}).get("abstractGameState") == "Final" \
                    and g.get("gameType") == "R":
                pks.append(g["gamePk"])
    return pks


def _game_row(pk: int) -> dict | None:
    """(hp ump, per-side batting K/BB/runs, team ids) for one final game."""
    box = _get(f"game/{pk}/boxscore")
    hp = next((o.get("official", {}).get("fullName")
               for o in box.get("officials", [])
               if o.get("officialType") == "Home Plate"), None)
    if not hp:
        return None
    row = {"ump": hp}
    for side in ("home", "away"):
        t = box.get("teams", {}).get(side, {})
        b = t.get("teamStats", {}).get("batting", {})
        row[side] = {"id": t.get("team", {}).get("id"),
                     "k": int(b.get("strikeOuts", 0) or 0),
                     "bb": int(b.get("baseOnBalls", 0) or 0),
                     "runs": int(b.get("runs", 0) or 0)}
    return row


def build(season: int, start: str, end: str) -> dict:
    pks = _final_game_pks(season, start, end)
    log.info("building ump table from %d final games (%s..%s)", len(pks), start, end)
    rows = []
    for i, pk in enumerate(pks):
        try:
            r = _game_row(pk)
            if r:
                rows.append(r)
        except Exception as exc:
            log.warning("boxscore %s failed: %s", pk, exc)
        if (i + 1) % 200 == 0:
            log.info("  %d/%d boxscores", i + 1, len(pks))

    total_k = sum(r["home"]["k"] + r["away"]["k"] for r in rows)
    total_bb = sum(r["home"]["bb"] + r["away"]["bb"] for r in rows)
    total_r = sum(r["home"]["runs"] + r["away"]["runs"] for r in rows)
    n = len(rows)
    umps: dict[str, dict] = {}
    for r in rows:
        u = umps.setdefault(r["ump"], {"games": 0, "k": 0, "bb": 0, "runs": 0})
        u["games"] += 1
        u["k"] += r["home"]["k"] + r["away"]["k"]
        u["bb"] += r["home"]["bb"] + r["away"]["bb"]
        u["runs"] += r["home"]["runs"] + r["away"]["runs"]
    for name, u in umps.items():
        g = u["games"]
        # league baseline excluding this ump's own games (leave-self-out)
        og = n - g
        lg_k = (total_k - u["k"]) / og if og else 0
        u["k_pg"] = round(u["k"] / g, 2)
        u["bb_pg"] = round(u["bb"] / g, 2)
        u["r_pg"] = round(u["runs"] / g, 2)
        u["k_extra"] = round(u["k"] / g - lg_k, 2)
        for k in ("k", "bb", "runs"):
            del u[k]
    return {"season": season, "through": end, "games": n,
            "league": {"k_pg": round(total_k / n, 2), "bb_pg": round(total_bb / n, 2),
                       "r_pg": round(total_r / n, 2)},
            "umps": umps, "_rows": rows}


def backtest(table: dict, k_extra_min: float, min_games: int) -> dict:
    """In big-zone-ump games, does the lower-season-K% team win more often than
    it does under everyone else? (Season K% is a mild look-ahead - fine for a
    tendency check, the live tilt uses the point-in-time blend.)"""
    season = table["season"]
    kp: dict[int, float | None] = {}

    def team_k(tid):
        if tid not in kp:
            try:
                o = team_season_offense(tid, season)
                pa = o.get("pa", 0) or 0
                kp[tid] = (o.get("so", 0) or 0) / pa if pa else None
            except Exception:
                kp[tid] = None
        return kp[tid]

    big, rest = [], []
    for r in table["_rows"]:
        u = table["umps"].get(r["ump"], {})
        hk, ak = team_k(r["home"]["id"]), team_k(r["away"]["id"])
        if hk is None or ak is None or hk == ak:
            continue
        low_home = hk < ak
        home_won = r["home"]["runs"] > r["away"]["runs"]
        low_won = home_won == low_home
        (big if u.get("games", 0) >= min_games and u.get("k_extra", 0) >= k_extra_min
         else rest).append(low_won)
    def wr(xs):
        return {"n": len(xs), "low_k_team_won": round(sum(xs) / len(xs), 3) if xs else None}
    return {"big_zone_games": wr(big), "other_games": wr(rest)}


def main() -> None:
    from .analysis import UMP_K_EXTRA, UMP_MIN_GAMES
    p = argparse.ArgumentParser(description="Build HP-ump tendency table + backtest")
    p.add_argument("--days", type=int, default=120, help="how far back to scan")
    p.add_argument("--end", default=(dt.datetime.now(EASTERN).date()
                                     - dt.timedelta(days=1)).isoformat())
    args = p.parse_args()
    season = int(args.end[:4])
    start = max(f"{season}-03-15",
                (dt.date.fromisoformat(args.end) - dt.timedelta(days=args.days)).isoformat())

    table = build(season, start, args.end)
    bt = backtest(table, UMP_K_EXTRA, UMP_MIN_GAMES)
    rows = table.pop("_rows")
    OUTPUT_DIR.mkdir(exist_ok=True)
    _table_path(season).write_text(json.dumps(table, indent=2))

    big = [(n, u) for n, u in table["umps"].items()
           if u["games"] >= UMP_MIN_GAMES and u["k_extra"] >= UMP_K_EXTRA]
    md = [f"# HP-ump tendencies — {table['through']} ({table['games']} games)", "",
          f"League: {table['league']['k_pg']} K/gm · {table['league']['bb_pg']} BB/gm · "
          f"{table['league']['r_pg']} R/gm", "",
          f"**Big-zone umps** (K +{UMP_K_EXTRA}/gm vs league on {UMP_MIN_GAMES}+ games): "
          f"{len(big)} of {len(table['umps'])}", ""]
    for n, u in sorted(big, key=lambda x: -x[1]["k_extra"]):
        md.append(f"- {n}: K {u['k_pg']}/gm ({u['k_extra']:+.2f} vs lg), "
                  f"{u['r_pg']} R/gm, {u['games']} gm")
    md += ["", "## Does it predict? (lower-K team's win rate)",
           f"- under a big-zone ump: {bt['big_zone_games']['low_k_team_won']} "
           f"({bt['big_zone_games']['n']} games)",
           f"- under everyone else: {bt['other_games']['low_k_team_won']} "
           f"({bt['other_games']['n']} games)", "",
           "_The live tilt (analysis.statistical_favorite) only fires for big-zone umps "
           "and only when the lineups' blended K% actually differ._"]
    (OUTPUT_DIR / "ump_calibration.md").write_text("\n".join(md))
    (OUTPUT_DIR / "ump_calibration.json").write_text(json.dumps(
        {"backtest": bt, "big_zone_umps": dict(big)}, indent=2))
    print("\n".join(md))


if __name__ == "__main__":
    main()
