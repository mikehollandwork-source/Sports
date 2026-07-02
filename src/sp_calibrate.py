"""
Starting-pitcher matchup analysis: does the better probable starter predict wins?

The starter is the biggest single-game lever in baseball, and the last-5 *team* FIP
only partly captures today's guy. For each completed game we take both probable
starters' season-to-date FIP (point-in-time), pick the team with the better (lower)
starter, and check whether they win - overall and at the biggest FIP gaps.

Cheap-ish (one cached game-log fetch per pitcher). Runs on Actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import mlb_api
from .analysis import FIP_CONSTANT

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("sp_calibrate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
MIN_IP = 20.0   # need a real season sample before trusting a starter's FIP


def _date_range(end: str, days: int) -> list[str]:
    e = dt.date.fromisoformat(end)
    return [(e - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _sp_fip(pitcher_id: int | None, season: int, as_of: str) -> float | None:
    if not pitcher_id:
        return None
    try:
        t = mlb_api.pitcher_season_line(pitcher_id, season, as_of=as_of)
    except Exception:
        return None
    if t["ip"] < MIN_IP:
        return None
    return round((13 * t["hr"] + 3 * (t["bb"] + t["hbp"]) - 2 * t["k"]) / t["ip"] + FIP_CONSTANT, 3)


def collect(end: str, days: int) -> list[dict]:
    """One row per game with both starters known: {sp_fav_won, gap}."""
    rows: list[dict] = []
    for d in _date_range(end, days):
        season = int(d[:4])
        try:
            games = mlb_api.schedule_for(d)
            results = mlb_api.results_for(d)
        except Exception as exc:
            log.warning("fetch %s failed: %s", d, exc)
            continue
        for g in games:
            res = results.get(g.game_pk)
            if not res or not res["final"] or not res["winner"]:
                continue
            hp = g.home.probable_pitcher.player_id if g.home.probable_pitcher else None
            ap = g.away.probable_pitcher.player_id if g.away.probable_pitcher else None
            hf, af = _sp_fip(hp, season, d), _sp_fip(ap, season, d)
            if hf is None or af is None:
                continue
            fav = g.home if hf < af else g.away          # lower FIP = better starter
            rows.append({"sp_fav_won": int(res["winner"] == fav.name),
                         "gap": round(abs(hf - af), 3)})
        log.info("collected through %s (%d games with both starters)", d, len(rows))
    return rows


def analyze(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"games": 0}
    overall = sum(r["sp_fav_won"] for r in rows) / n
    cut = sorted(r["gap"] for r in rows)[int(n * 2 / 3)]
    big = [r for r in rows if r["gap"] >= cut]
    small = [r for r in rows if r["gap"] < cut]
    bwr = sum(r["sp_fav_won"] for r in big) / len(big) if big else None
    swr = sum(r["sp_fav_won"] for r in small) / len(small) if small else None
    return {"games": n, "sp_favorite_win_rate": round(overall, 3),
            "big_gap_win_rate": round(bwr, 3) if bwr is not None else None,
            "big_gap_n": len(big), "big_gap_fip_cut": round(cut, 2),
            "lift_big_vs_small": round(bwr - swr, 3) if bwr is not None and swr is not None else None}


def summary_md(rep: dict) -> str:
    a = rep["analysis"]
    out = [f"# Starting-pitcher analysis — {rep['window']}", ""]
    if not a.get("games"):
        out.append("No games with both starters' season FIP available.")
        return "\n".join(out)
    out.append(f"**{a['games']} games** (both starters ≥{MIN_IP:.0f} IP) · the better "
               f"starter's team won **{a['sp_favorite_win_rate']:.0%}** overall")
    out.append("")
    if a["big_gap_win_rate"] is not None:
        out.append(f"At the **biggest FIP gaps** (top third, ≥{a['big_gap_fip_cut']} FIP apart, "
                   f"{a['big_gap_n']} games): **{a['big_gap_win_rate']:.0%}** "
                   f"(lift {a['lift_big_vs_small']:+.0%})")
    out.append("")
    out.append("_Probable starters' season-to-date FIP, point-in-time (no lookahead)._")
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Starting-pitcher matchup analysis")
    p.add_argument("--days", type=int, default=95)
    p.add_argument("--end", default=yesterday_eastern())
    args = p.parse_args()

    rep = {"window": f"{_date_range(args.end, args.days)[0]} → {args.end} ({args.days} days)",
           "analysis": analyze(collect(args.end, args.days))}
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "sp_analysis.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "sp_analysis.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
