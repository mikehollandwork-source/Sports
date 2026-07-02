"""
Season-quality scanner: do season-level quality gaps predict winning?

The session's lesson is that broad/season signals hold up while granular last-N
splits are noise. So this tests the gold-standard true-quality metrics - season
run differential per game and season win% - point-in-time. For each, it finds the
"quality favorite" (better season number) and reports how often they win overall
and at the biggest gaps (top third), so a small edge shows up if it exists.

Cheap (game logs + results). Runs on Actions.
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
log = logging.getLogger("quality_calibrate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
SIGNALS = {"rd_per_g": "season run-diff/game", "win_pct": "season win%"}
MIN_GAMES = 10   # need a real season sample for the quality number to mean anything


def _date_range(end: str, days: int) -> list[str]:
    e = dt.date.fromisoformat(end)
    return [(e - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def collect(end: str, days: int) -> list[dict]:
    """One row per game: home_won + each signal's home-minus-away gap."""
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
            try:
                hf = mlb_api.team_season_form(g.home.team_id, season, as_of=d)
                af = mlb_api.team_season_form(g.away.team_id, season, as_of=d)
            except Exception:
                continue
            if hf["games"] < MIN_GAMES or af["games"] < MIN_GAMES:
                continue
            gaps = {s: round(hf[s] - af[s], 4) for s in SIGNALS}
            rows.append({"home_won": int(res["winner"] == g.home.name), "gaps": gaps})
        log.info("collected through %s (%d games)", d, len(rows))
    return rows


def _analyze_signal(rows: list[dict], s: str) -> dict:
    # better team = home when gap>0 else away; did the better team win?
    pts = [{"won": (r["home_won"] if r["gaps"][s] > 0 else 1 - r["home_won"]),
            "gap": abs(r["gaps"][s])} for r in rows if r["gaps"][s] != 0]
    n = len(pts)
    if not n:
        return {"n": 0}
    overall = sum(p["won"] for p in pts) / n
    cut = sorted(p["gap"] for p in pts)[int(n * 2 / 3)]    # top-third gap threshold
    big = [p for p in pts if p["gap"] >= cut]
    small = [p for p in pts if p["gap"] < cut]
    bwr = sum(p["won"] for p in big) / len(big) if big else None
    swr = sum(p["won"] for p in small) / len(small) if small else None
    return {"n": n, "favorite_win_rate": round(overall, 3),
            "big_gap_win_rate": round(bwr, 3) if bwr is not None else None,
            "big_gap_n": len(big),
            "lift_big_vs_small": round(bwr - swr, 3) if bwr is not None and swr is not None else None}


def analyze(rows: list[dict]) -> dict:
    return {"games": len(rows), "signals": {s: _analyze_signal(rows, s) for s in SIGNALS}}


def summary_md(rep: dict) -> str:
    a = rep["analysis"]
    out = [f"# Season-quality scan — {rep['window']}", ""]
    out.append(f"**{a['games']} games** (both teams ≥{MIN_GAMES} games)")
    out.append("")
    out.append("For each metric: how often the season-quality favorite won overall, "
               "and at the biggest gaps (top third).")
    out.append("")
    out.append("| Metric | favorite won | big-gap won | big-gap lift |")
    out.append("|---|---|---|---|")
    for s, label in SIGNALS.items():
        v = a["signals"][s]
        if not v.get("n"):
            out.append(f"| {label} | — | — | — |")
            continue
        fw = f"{v['favorite_win_rate']:.0%}"
        bw = f"{v['big_gap_win_rate']:.0%} ({v['big_gap_n']})" if v["big_gap_win_rate"] is not None else "—"
        lf = f"{v['lift_big_vs_small']:+.0%}" if v["lift_big_vs_small"] is not None else "—"
        out.append(f"| {label} | {fw} | {bw} | **{lf}** |")
    out.append("")
    out.append("_Point-in-time season numbers (no lookahead). 'Big-gap won' is the "
               "favorite's win rate when the quality gap is in the top third._")
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Scan season-quality signals vs winning")
    p.add_argument("--days", type=int, default=95)
    p.add_argument("--end", default=yesterday_eastern())
    args = p.parse_args()

    rep = {"window": f"{_date_range(args.end, args.days)[0]} → {args.end} ({args.days} days)",
           "analysis": analyze(collect(args.end, args.days))}
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "quality_analysis.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "quality_analysis.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
