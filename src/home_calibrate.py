"""
Home/away context analysis: is home field worth adding to the edge, and does a
team's home-vs-road run-differential split predict the game?

For each completed game we measure (a) the plain home-field win rate, and (b)
whether a "split edge" - the home team's point-in-time home run-diff/game minus the
away team's away run-diff/game - predicts the home team winning. If the split adds
lift beyond plain home field, it's worth folding into the stat edge.

Cheap (game logs + results only, point-in-time, no lookahead). Runs on Actions.
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
log = logging.getLogger("home_calibrate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
SPLIT = 1.0   # run-diff/game gap that counts as a clear split edge


def _date_range(end: str, days: int) -> list[str]:
    e = dt.date.fromisoformat(end)
    return [(e - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def collect(end: str, days: int) -> list[dict]:
    """One row per game: {home_won, split} where split = home-team home rd/g minus
    away-team away rd/g (point-in-time); split is None when either side has no games."""
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
            home_won = int(res["winner"] == g.home.name)
            try:
                hh = mlb_api.team_home_away_split(g.home.team_id, season, as_of=d)["home"]["rd_per_g"]
                aa = mlb_api.team_home_away_split(g.away.team_id, season, as_of=d)["away"]["rd_per_g"]
            except Exception:
                hh = aa = None
            split = round(hh - aa, 3) if hh is not None and aa is not None else None
            rows.append({"home_won": home_won, "split": split})
        log.info("collected through %s (%d games)", d, len(rows))
    return rows


def _wr(rows: list[dict]) -> tuple[int, float | None]:
    n = len(rows)
    return n, (round(sum(r["home_won"] for r in rows) / n, 3) if n else None)


def analyze(rows: list[dict]) -> dict:
    n, home_wr = _wr(rows)
    have = [r for r in rows if r["split"] is not None]
    hi = [r for r in have if r["split"] >= SPLIT]     # home form clearly better
    mid = [r for r in have if -SPLIT < r["split"] < SPLIT]
    lo = [r for r in have if r["split"] <= -SPLIT]    # away form clearly better
    _, hr = _wr(hi)
    _, mr = _wr(mid)
    _, lr = _wr(lo)
    return {
        "games": n,
        "home_field_win_rate": home_wr,
        "split_buckets": {
            "home_form_better (>=+1 rd/g)": {"n": len(hi), "home_win_rate": hr},
            "even (-1..+1)": {"n": len(mid), "home_win_rate": mr},
            "away_form_better (<=-1 rd/g)": {"n": len(lo), "home_win_rate": lr},
        },
        "split_lift": round(hr - lr, 3) if hr is not None and lr is not None else None,
    }


def summary_md(rep: dict) -> str:
    a = rep["analysis"]
    out = [f"# Home/away analysis — {rep['window']}", ""]
    out.append(f"**{a['games']} games** · **home-field win rate {a['home_field_win_rate']:.0%}**")
    out.append("")
    out.append("Home-team win rate by the home/road form split "
               "(home team's home rd/g − away team's road rd/g):")
    out.append("")
    out.append("| Split | games | home won |")
    out.append("|---|---|---|")
    for label, b in a["split_buckets"].items():
        wr = f"{b['home_win_rate']:.0%}" if b["home_win_rate"] is not None else "—"
        out.append(f"| {label} | {b['n']} | {wr} |")
    out.append("")
    if a["split_lift"] is not None:
        out.append(f"**Split lift:** home-form-better vs away-form-better = **{a['split_lift']:+.0%}**")
    out.append("")
    out.append("_Home field is the base rate; the split lift shows whether home/road form "
               "adds anything beyond it. Point-in-time run diffs, no lookahead._")
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Home/away context analysis")
    p.add_argument("--days", type=int, default=95)
    p.add_argument("--end", default=yesterday_eastern())
    args = p.parse_args()

    rep = {"window": f"{_date_range(args.end, args.days)[0]} → {args.end} ({args.days} days)",
           "analysis": analyze(collect(args.end, args.days))}
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "home_analysis.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "home_analysis.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
