"""
Line-movement analysis: does the open->close moneyline move predict who wins?

For every team in every completed game over a window, compute that team's implied
win-prob shift from open to current/close, and whether they won. Then:
  - win rate when the line moved TOWARD a team vs AGAINST it (the lift), and
  - among the winners, how their lines had moved.

Cheap (odds + results only, no lineup enrichment), so it can span many days.
Runs on GitHub Actions (APIs firewalled in the sandbox).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import covers, espn, mlb_api
from .analysis import _implied, find_slate_line

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("line_calibrate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
TOWARD = 0.02   # implied-prob shift that counts as a real move toward a team


def _date_range(end: str, days: int) -> list[str]:
    e = dt.date.fromisoformat(end)
    return [(e - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _slate(date: str) -> list:
    try:
        s = espn.lines(date)
    except Exception:
        s = []
    if not s:
        try:
            s = covers.slate_lines()
        except Exception:
            s = []
    return s


def collect(end: str, days: int) -> list[dict]:
    """One row per team-game: {shift, won} where shift = implied(current)-implied(open)."""
    rows: list[dict] = []
    for d in _date_range(end, days):
        try:
            games = mlb_api.schedule_for(d)
            results = mlb_api.results_for(d)
        except Exception as exc:
            log.warning("fetch %s failed: %s", d, exc)
            continue
        slate = _slate(d)
        for g in games:
            res = results.get(g.game_pk)
            if not res or not res["final"] or not res["winner"]:
                continue
            e = find_slate_line(g, slate)
            if not e:
                continue
            for team, side in ((g.home, "home"), (g.away, "away")):
                op, cur = e.get(f"{side}_open"), e.get(f"{side}_current")
                if op is None or cur is None:
                    continue
                rows.append({"shift": round(_implied(cur) - _implied(op), 4),
                             "won": int(res["winner"] == team.name)})
        log.info("collected through %s (%d team-games with line data)", d, len(rows))
    return rows


def _wr(rows: list[dict]) -> tuple[int, float | None]:
    n = len(rows)
    return n, (round(sum(r["won"] for r in rows) / n, 3) if n else None)


def analyze(rows: list[dict]) -> dict:
    n, base = _wr(rows)
    toward = [r for r in rows if r["shift"] >= TOWARD]
    against = [r for r in rows if r["shift"] <= -TOWARD]
    flat = [r for r in rows if -TOWARD < r["shift"] < TOWARD]
    tn, tw = _wr(toward)
    an, aw = _wr(against)
    fn, fw = _wr(flat)
    winners = [r for r in rows if r["won"]]
    wn = len(winners) or 1
    return {
        "team_games": n, "base_win_rate": base,
        "moved_toward": {"n": tn, "win_rate": tw},
        "flat": {"n": fn, "win_rate": fw},
        "moved_against": {"n": an, "win_rate": aw},
        "lift_toward_vs_against": round(tw - aw, 3) if tw is not None and aw is not None else None,
        "among_winners": {
            "toward_pct": round(sum(1 for r in winners if r["shift"] >= TOWARD) / wn, 3),
            "flat_pct": round(sum(1 for r in winners if -TOWARD < r["shift"] < TOWARD) / wn, 3),
            "against_pct": round(sum(1 for r in winners if r["shift"] <= -TOWARD) / wn, 3),
        },
    }


def summary_md(rep: dict) -> str:
    a = rep["analysis"]
    out = [f"# Line-movement analysis — {rep['window']}", ""]
    out.append(f"**{a['team_games']} team-games with line data** · base win rate "
               f"{a['base_win_rate']:.0%}" if a["base_win_rate"] is not None else "no data")
    out.append("")
    out.append("Win rate by how that team's line moved (open→close):")
    out.append("")
    out.append("| Line moved | team-games | won |")
    out.append("|---|---|---|")
    for label, key in (("TOWARD the team (≥+2%)", "moved_toward"),
                       ("flat (±2%)", "flat"),
                       ("AGAINST the team (≤−2%)", "moved_against")):
        b = a[key]
        wr = f"{b['win_rate']:.0%}" if b["win_rate"] is not None else "—"
        out.append(f"| {label} | {b['n']} | {wr} |")
    out.append("")
    if a["lift_toward_vs_against"] is not None:
        out.append(f"**Lift:** moved-toward {a['moved_toward']['win_rate']:.0%} vs "
                   f"moved-against {a['moved_against']['win_rate']:.0%} = "
                   f"**{a['lift_toward_vs_against']:+.0%}**")
    w = a["among_winners"]
    out.append("")
    out.append(f"**Among the winners:** their line had moved toward them "
               f"{w['toward_pct']:.0%}, flat {w['flat_pct']:.0%}, against them {w['against_pct']:.0%}.")
    out.append("")
    out.append("_Open→close moneyline from ESPN/covers, converted to implied win prob. "
               "Each game contributes both teams, so the base rate is 50% by construction._")
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Analyze line movement vs winning")
    p.add_argument("--days", type=int, default=10)
    p.add_argument("--end", default=yesterday_eastern())
    args = p.parse_args()

    rep = {"window": f"{_date_range(args.end, args.days)[0]} → {args.end} ({args.days} days)",
           "analysis": analyze(collect(args.end, args.days))}
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "line_analysis.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "line_analysis.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
