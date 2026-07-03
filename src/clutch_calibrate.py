"""
Clutch-hitting calibration: over a window of completed games, does a team's
last-5 "clutch" profile predict the next game?

Three candidate signals, each measured as the head-to-head gap (point-in-time,
no lookahead) between the two teams' previous 5 games:
  - clutch  = runs per hit (how well hits convert into runs)
  - hits    = hits per game (raw bat-to-ball volume)
  - lob     = runners left on base per game (lower = more clutch)

For each we report how often the better side won, plus gap-size buckets for the
runs-per-hit signal. If any shows real lift, it earns a spot next to the five
pick signals; otherwise it stays out (same bar every other signal cleared).

Cheap (cached team game logs + results only). Runs on Actions.
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
log = logging.getLogger("clutch_calibrate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
CLUTCH_GAP = 0.10   # runs-per-hit gap that counts as a clear edge


def _date_range(end: str, days: int) -> list[str]:
    e = dt.date.fromisoformat(end)
    return [(e - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _last5(team_id: int, season: int, as_of: str) -> list[dict]:
    """The team's 5 completed games before `as_of` as {runs, hits, lob} rows."""
    hit_splits, _ = mlb_api._team_gamelog(team_id, season)
    games = [sp for sp in hit_splits if sp.get("date", "") < as_of][-5:]
    rows = []
    for sp in games:
        st = sp.get("stat", {})
        rows.append({"runs": int(st.get("runs", 0) or 0),
                     "hits": int(st.get("hits", 0) or 0),
                     "lob": int(st.get("leftOnBase", 0) or 0)})
    return rows


def _profile(rows: list[dict]) -> dict | None:
    """{clutch (runs/hit), hits_pg, lob_pg} over the last-5 rows; None if thin."""
    if len(rows) < 5:
        return None
    runs = sum(r["runs"] for r in rows)
    hits = sum(r["hits"] for r in rows)
    lob = sum(r["lob"] for r in rows)
    if not hits:
        return None
    return {"clutch": runs / hits, "hits_pg": hits / len(rows), "lob_pg": lob / len(rows)}


def collect(end: str, days: int) -> list[dict]:
    """One row per completed game: home_won + the home-minus-away gap on each
    candidate signal (None when either side lacks 5 prior games)."""
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
                hp = _profile(_last5(g.home.team_id, season, d))
                ap = _profile(_last5(g.away.team_id, season, d))
            except Exception:
                hp = ap = None
            if not hp or not ap:
                continue
            rows.append({
                "home_won": int(res["winner"] == g.home.name),
                "clutch_gap": round(hp["clutch"] - ap["clutch"], 3),
                "hits_gap": round(hp["hits_pg"] - ap["hits_pg"], 2),
                "lob_gap": round(hp["lob_pg"] - ap["lob_pg"], 2),
            })
        log.info("collected through %s (%d games)", d, len(rows))
    return rows


def _better_side_wr(rows: list[dict], key: str, lower_is_better: bool = False) -> dict:
    """Win rate of the team with the better last-5 number on `key` (ties skipped)."""
    n = won = 0
    for r in rows:
        gap = r[key]
        if not gap:
            continue
        better_is_home = (gap < 0) if lower_is_better else (gap > 0)
        n += 1
        won += r["home_won"] if better_is_home else 1 - r["home_won"]
    return {"n": n, "win_rate": round(won / n, 3) if n else None}


def analyze(rows: list[dict]) -> dict:
    out = {
        "games": len(rows),
        "better_side_win_rate": {
            "clutch (runs/hit)": _better_side_wr(rows, "clutch_gap"),
            "hits/game": _better_side_wr(rows, "hits_gap"),
            "LOB/game (fewer)": _better_side_wr(rows, "lob_gap", lower_is_better=True),
        },
    }
    hi = [r for r in rows if abs(r["clutch_gap"]) >= CLUTCH_GAP]
    out["clutch_gap_buckets"] = {
        f"clear gap (>= {CLUTCH_GAP} runs/hit)": _better_side_wr(hi, "clutch_gap"),
        f"small gap (< {CLUTCH_GAP})": _better_side_wr(
            [r for r in rows if abs(r["clutch_gap"]) < CLUTCH_GAP], "clutch_gap"),
    }
    return out


def summary_md(rep: dict) -> str:
    a = rep["analysis"]
    out = [f"# Clutch-hitting calibration — {rep['window']}", ""]
    out.append(f"**{a['games']} games** — win rate of the side with the better last-5 number:")
    out.append("")
    out.append("| signal | games | better side won |")
    out.append("|---|---|---|")
    for label, b in a["better_side_win_rate"].items():
        wr = f"{b['win_rate']:.0%}" if b["win_rate"] is not None else "—"
        out.append(f"| {label} | {b['n']} | {wr} |")
    out.append("")
    out.append("Runs-per-hit gap size:")
    out.append("")
    out.append("| bucket | games | better side won |")
    out.append("|---|---|---|")
    for label, b in a["clutch_gap_buckets"].items():
        wr = f"{b['win_rate']:.0%}" if b["win_rate"] is not None else "—"
        out.append(f"| {label} | {b['n']} | {wr} |")
    out.append("")
    out.append("_Point-in-time last-5 profiles, no lookahead. ~55%+ with a real sample = worth "
               "considering as a sixth signal; ~50% = luck-noise, stays out of the picks._")
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Clutch-hitting (runs/hit, hits, LOB) calibration")
    p.add_argument("--days", type=int, default=60)
    p.add_argument("--end", default=yesterday_eastern())
    args = p.parse_args()

    rep = {"window": f"{_date_range(args.end, args.days)[0]} → {args.end} ({args.days} days)",
           "analysis": analyze(collect(args.end, args.days))}
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "clutch_calibration.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "clutch_calibration.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
