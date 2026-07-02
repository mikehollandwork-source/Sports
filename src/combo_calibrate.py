"""
Combo calibration: does combining the last-5 stat edge with the season run-diff
favorite beat either signal alone?

Item #2 from the "do both" list. For each completed game we compute, point-in-time:
  - the LAST-5 stat-edge favorite (full lineup enrichment) + its team_score margin
  - the SEASON run-diff/game favorite + its rd/g gap

Then we report each signal's solo win rate and, crucially, the win rate when the two
AGREE on a side - both overall and when the edge also clears EDGE_THRESHOLD (today's
pick gate). If "agree" beats either alone, the run-diff agreement is a worthwhile
extra filter; if not, it's redundant with the edge.

Needs full per-game enrichment (lineups + logs), so it runs over a shorter window,
same machinery as edge_calibrate.py. Runs on GitHub Actions (MLB API firewalled in
the sandbox).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import mlb_api
from .analysis import EDGE_THRESHOLD, statistical_favorite

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("combo_calibrate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
MIN_GAMES = 10    # season sample needed before the run-diff number means anything
RD_MIN = 0.25     # rd/g gap below this is a run-diff coin flip (no real lean)


def _date_range(end: str, days: int) -> list[str]:
    e = dt.date.fromisoformat(end)
    return [(e - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def collect(end: str, days: int) -> list[dict]:
    """One row per game with both signals available."""
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
            try:
                mlb_api.enrich_with_stats(g, d, as_of=d)  # point-in-time, no lookahead
            except Exception as exc:
                log.warning("enrich %s failed: %s", g.game_pk, exc)
                continue
            edge_fav, hs, as_ = statistical_favorite(g)
            rd_gap = hf["rd_per_g"] - af["rd_per_g"]
            rd_fav = g.home if rd_gap > 0 else g.away
            rows.append({
                "winner_is_edge_fav": int(res["winner"] == edge_fav.name),
                "winner_is_rd_fav": int(res["winner"] == rd_fav.name),
                "edge_margin": round(abs(hs - as_), 4),
                "rd_gap": round(abs(rd_gap), 4),
                "agree": int(edge_fav.name == rd_fav.name),
            })
        log.info("collected through %s (%d games)", d, len(rows))
    return rows


def _wr(rows: list[dict], key: str) -> tuple[int, float | None]:
    n = len(rows)
    return n, (round(sum(r[key] for r in rows) / n, 3) if n else None)


def analyze(rows: list[dict]) -> dict:
    n = len(rows)
    _, edge_solo = _wr(rows, "winner_is_edge_fav")
    _, rd_solo = _wr(rows, "winner_is_rd_fav")

    agree = [r for r in rows if r["agree"]]
    disagree = [r for r in rows if not r["agree"]]
    ag_n, ag_wr = _wr(agree, "winner_is_edge_fav")   # agree -> both favor the same team
    dis_n, dis_edge = _wr(disagree, "winner_is_edge_fav")
    _, dis_rd = _wr(disagree, "winner_is_rd_fav")

    # the pick gate today is edge_margin >= EDGE_THRESHOLD; does run-diff agreement
    # on top of that gate raise the win rate?
    gated = [r for r in rows if r["edge_margin"] >= EDGE_THRESHOLD]
    g_n, g_wr = _wr(gated, "winner_is_edge_fav")
    gated_agree = [r for r in gated if r["agree"]]
    ga_n, ga_wr = _wr(gated_agree, "winner_is_edge_fav")
    # run-diff lean must also be non-trivial
    gated_strong = [r for r in gated if r["agree"] and r["rd_gap"] >= RD_MIN]
    gs_n, gs_wr = _wr(gated_strong, "winner_is_edge_fav")

    return {
        "games": n,
        "edge_favorite_win_rate": edge_solo,
        "rundiff_favorite_win_rate": rd_solo,
        "agree": {"n": ag_n, "win_rate": ag_wr},
        "disagree": {"n": dis_n, "edge_won": dis_edge, "rundiff_won": dis_rd},
        "edge_gate": {"n": g_n, "win_rate": g_wr},
        "edge_gate_and_agree": {"n": ga_n, "win_rate": ga_wr},
        "edge_gate_and_agree_strong_rd": {"n": gs_n, "win_rate": gs_wr,
                                          "rd_min": RD_MIN},
    }


def summary_md(rep: dict) -> str:
    a = rep["analysis"]
    out = [f"# Edge + run-diff combo — {rep['window']}", ""]
    if not a["games"]:
        out.append("No qualifying games.")
        return "\n".join(out)
    out.append(f"**{a['games']} games** (both teams ≥{MIN_GAMES} season games)")
    out.append("")
    out.append("**Each signal alone:**")
    out.append(f"- last-5 stat edge favorite won **{a['edge_favorite_win_rate']:.0%}**")
    out.append(f"- season run-diff favorite won **{a['rundiff_favorite_win_rate']:.0%}**")
    out.append("")
    ag = a["agree"]
    dis = a["disagree"]
    out.append("**When they agree on a side vs disagree:**")
    if ag["win_rate"] is not None:
        out.append(f"- agree ({ag['n']} games): that team won **{ag['win_rate']:.0%}**")
    if dis["edge_won"] is not None:
        out.append(f"- disagree ({dis['n']} games): edge side won {dis['edge_won']:.0%}, "
                   f"run-diff side won {dis['rundiff_won']:.0%}")
    out.append("")
    out.append("**On top of today's pick gate** (edge margin ≥ "
               f"{EDGE_THRESHOLD}):")
    eg = a["edge_gate"]
    ga = a["edge_gate_and_agree"]
    gs = a["edge_gate_and_agree_strong_rd"]
    if eg["win_rate"] is not None:
        out.append(f"- gate alone ({eg['n']} games): **{eg['win_rate']:.0%}**")
    if ga["win_rate"] is not None:
        out.append(f"- gate + run-diff agrees ({ga['n']} games): **{ga['win_rate']:.0%}**")
    if gs["win_rate"] is not None:
        out.append(f"- gate + run-diff agrees ≥{gs['rd_min']} rd/g ({gs['n']} games): "
                   f"**{gs['win_rate']:.0%}**")
    out.append("")
    out.append("_Point-in-time, no lookahead. If 'gate + agrees' beats 'gate alone' "
               "by more than noise, run-diff agreement is a worthwhile extra filter; "
               "if not, it's redundant with the stat edge._")
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Edge + season run-diff combo calibration")
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--end", default=yesterday_eastern())
    args = p.parse_args()

    rows = collect(args.end, args.days)
    rep = {"window": f"{_date_range(args.end, args.days)[0]} → {args.end} ({args.days} days)",
           "analysis": analyze(rows)}
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "combo_calibration.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "combo_calibration.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
