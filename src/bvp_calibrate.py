"""
Batter-vs-pitcher (BvP) test: does a lineup's career history vs the opposing
starter predict the game? Small window only - BvP needs a vs-pitcher fetch per
batter (heavy) and the samples are tiny, so this can't be validated at scale. Read
the result with heavy skepticism.

Per game: aggregate each lineup's PA-weighted career OPS vs the opposing starter
(only counting a side with >= MIN_PA total history). The "BvP favorite" is the team
whose starter has held the other lineup to the lower OPS. Then: did they win?
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import mlb_api

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bvp_calibrate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
MIN_PA = 30   # total lineup PA vs the starter needed for the matchup to count


def _date_range(end: str, days: int) -> list[str]:
    e = dt.date.fromisoformat(end)
    return [(e - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _lineup_ops_vs(game_pk: int, team_id: int, date: str, home: bool,
                   pitcher_id: int) -> tuple[float | None, int]:
    """PA-weighted career OPS of this lineup vs `pitcher_id`, and total PA."""
    pa_tot = ops_w = 0.0
    for b in mlb_api.lineup(game_pk, team_id, date, home):
        bvp = mlb_api.batter_vs_pitcher(b.player_id, pitcher_id)
        if bvp["pa"] > 0:
            pa_tot += bvp["pa"]
            ops_w += bvp["ops"] * bvp["pa"]
    return (round(ops_w / pa_tot, 3) if pa_tot else None), int(pa_tot)


def collect(end: str, days: int) -> list[dict]:
    rows: list[dict] = []
    for d in _date_range(end, days):
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
            if not hp or not ap:
                continue
            # away lineup vs home starter, and home lineup vs away starter
            away_ops, away_pa = _lineup_ops_vs(g.game_pk, g.away.team_id, d, False, hp)
            home_ops, home_pa = _lineup_ops_vs(g.game_pk, g.home.team_id, d, True, ap)
            if away_ops is None or home_ops is None or away_pa < MIN_PA or home_pa < MIN_PA:
                continue
            # the team whose starter held the other lineup to the lower OPS is favored
            fav = g.home if away_ops < home_ops else g.away
            rows.append({"bvp_fav_won": int(res["winner"] == fav.name),
                         "gap": round(abs(away_ops - home_ops), 3)})
        log.info("collected through %s (%d games with enough BvP history)", d, len(rows))
    return rows


def analyze(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"games": 0}
    overall = sum(r["bvp_fav_won"] for r in rows) / n
    cut = sorted(r["gap"] for r in rows)[int(n * 2 / 3)] if n >= 3 else 0
    big = [r for r in rows if r["gap"] >= cut]
    bwr = sum(r["bvp_fav_won"] for r in big) / len(big) if big else None
    return {"games": n, "bvp_favorite_win_rate": round(overall, 3),
            "big_gap_win_rate": round(bwr, 3) if bwr is not None else None,
            "big_gap_n": len(big)}


def summary_md(rep: dict) -> str:
    a = rep["analysis"]
    out = [f"# Batter-vs-pitcher analysis — {rep['window']}", ""]
    if not a.get("games"):
        out.append("No games with enough BvP history (lineups too unfamiliar with the starters).")
        return "\n".join(out)
    out.append(f"**{a['games']} games** (each lineup ≥{MIN_PA} career PA vs the starter) · "
               f"the BvP-favored team won **{a['bvp_favorite_win_rate']:.0%}**")
    if a["big_gap_win_rate"] is not None:
        out.append("")
        out.append(f"At the biggest OPS gaps (top third, {a['big_gap_n']} games): "
                   f"**{a['big_gap_win_rate']:.0%}**")
    out.append("")
    out.append("_Small window, tiny samples - read with heavy skepticism; BvP is the "
               "noisiest stat in baseball and this can't be validated at scale._")
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Batter-vs-pitcher analysis (small window)")
    p.add_argument("--days", type=int, default=5)
    p.add_argument("--end", default=yesterday_eastern())
    args = p.parse_args()

    rep = {"window": f"{_date_range(args.end, args.days)[0]} → {args.end} ({args.days} days)",
           "analysis": analyze(collect(args.end, args.days))}
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "bvp_analysis.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "bvp_analysis.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
