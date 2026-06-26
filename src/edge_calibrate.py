"""
Stat-edge calibration: does the statistically-favored team actually win more, and
does a bigger edge mean a bigger win rate?

For each completed game in a window, reconstruct the live stat edge point-in-time
(full last-5 lineup enrichment, no lookahead) and check whether the favorite won.
Bucketed by the edge margin so we can see if more edge = more wins.

Unlike the win-condition tool this needs the full per-game enrichment (lineups +
player logs), so it's run over a shorter window. Same point-in-time machinery as
backtest.py. Runs on GitHub Actions (the MLB API is firewalled in the sandbox).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import mlb_api
from .analysis import EDGE_FULL, statistical_favorite

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("edge_calibrate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
# margin buckets in team_score units (EDGE_FULL = 0.40 is a "full" edge)
BUCKETS = [(0.0, 0.10), (0.10, 0.20), (0.20, 0.40), (0.40, 99.0)]


def _date_range(end: str, days: int) -> list[str]:
    e = dt.date.fromisoformat(end)
    return [(e - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def collect(end: str, days: int) -> list[dict]:
    """One row per game: the stat-edge margin and whether the favorite won."""
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
            try:
                mlb_api.enrich_with_stats(g, d, as_of=d)  # point-in-time, no lookahead
            except Exception as exc:
                log.warning("enrich %s failed: %s", g.game_pk, exc)
                continue
            fav, hs, as_ = statistical_favorite(g)
            rows.append({"margin": round(abs(hs - as_), 4),
                         "fav_won": int(res["winner"] == fav.name)})
        log.info("collected through %s (%d games)", d, len(rows))
    return rows


def analyze(rows: list[dict]) -> dict:
    n = len(rows)
    fav_rate = sum(r["fav_won"] for r in rows) / n if n else 0.0
    buckets = []
    for lo, hi in BUCKETS:
        grp = [r for r in rows if lo <= r["margin"] < hi]
        buckets.append({"range": f"{lo:.2f}-{hi:.2f}" if hi < 90 else f"{lo:.2f}+",
                        "n": len(grp),
                        "fav_win_rate": round(sum(r["fav_won"] for r in grp) / len(grp), 3) if grp else None})
    big = [r for r in rows if r["margin"] >= 0.20]
    small = [r for r in rows if r["margin"] < 0.20]
    br = sum(r["fav_won"] for r in big) / len(big) if big else None
    sr = sum(r["fav_won"] for r in small) / len(small) if small else None
    return {"games": n, "favorite_win_rate": round(fav_rate, 3),
            "win_rate_big_edge_0_20plus": round(br, 3) if br is not None else None,
            "win_rate_small_edge_under_0_20": round(sr, 3) if sr is not None else None,
            "lift": round(br - sr, 3) if br is not None and sr is not None else None,
            "by_margin": buckets}


def summary_md(rep: dict) -> str:
    a = rep["analysis"]
    out = [f"# Stat-edge calibration — {rep['window']}", ""]
    out.append(f"**{a['games']} games** · the stat favorite won **{a['favorite_win_rate']:.0%}** overall")
    out.append("")
    out.append("Favorite win rate by edge size (does more edge = more wins?):")
    out.append("")
    out.append("| Edge margin | games | favorite won |")
    out.append("|---|---|---|")
    for b in a["by_margin"]:
        wr = f"{b['fav_win_rate']:.0%}" if b["fav_win_rate"] is not None else "—"
        out.append(f"| {b['range']} | {b['n']} | {wr} |")
    out.append("")
    if a["lift"] is not None:
        out.append(f"**Lift:** big edge (≥0.20) {a['win_rate_big_edge_0_20plus']:.0%} vs "
                   f"small (<0.20) {a['win_rate_small_edge_under_0_20']:.0%} = **{a['lift']:+.0%}**")
    out.append("")
    out.append(f"_Edge is the live last-5 team_score margin (EDGE_FULL={EDGE_FULL}). "
               "Lift near 0 = the stat edge doesn't pick winners; clearly positive = it does._")
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Calibrate the stat edge against actual results")
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--end", default=yesterday_eastern())
    args = p.parse_args()

    rows = collect(args.end, args.days)
    rep = {"window": f"{_date_range(args.end, args.days)[0]} → {args.end} ({args.days} days)",
           "analysis": analyze(rows)}
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "edge_calibration.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "edge_calibration.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
