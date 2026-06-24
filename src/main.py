"""
Entry point: build the daily edge list.

For each MLB game today:
  1. pull schedule + probable pitchers (MLB API)
  2. pull last-5-game hitting/pitching stats (MLB API)
  3. pull public majority from covers consensus + forum (covers.com)
  4. flag games where the statistically-advantaged team is NOT the public side

Writes output/picks_<date>.json. Date defaults to today (US/Eastern) and can be
overridden with --date YYYY-MM-DD or the PICKS_DATE env var.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import zoneinfo
from pathlib import Path

from . import covers, grade, notify, tune
from .analysis import evaluate_game
from .mlb_api import enrich_with_stats, schedule_for

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("main")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")


def today_eastern() -> str:
    return dt.datetime.now(EASTERN).date().isoformat()


def run(date: str) -> dict:
    log.info("Building edge list for %s", date)

    games = schedule_for(date)
    log.info("Found %d games", len(games))
    if not games:
        return {"date": date, "games": [], "picks": [], "note": "no games scheduled"}

    # Public sentiment (fetched once, shared across games).
    consensus = covers.consensus()
    teams = [(t.name, t.abbreviation) for g in games for t in (g.home, g.away)]
    forum_counts = covers.forum_majority(teams, date)

    results = []
    for g in games:
        try:
            enrich_with_stats(g, date)
        except Exception as exc:
            log.warning("stats enrichment failed for %s: %s", g.game_pk, exc)
        results.append(evaluate_game(g, consensus, forum_counts))

    picks = [r["pick"] for r in results if r["flagged"]]
    log.info("Flagged %d edge game(s)", len(picks))

    return {
        "date": date,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "games": results,
        "picks": picks,
    }


def build_summary(payload: dict) -> str:
    """Human-readable markdown for the daily picks issue."""
    date = payload["date"]
    picks = payload.get("picks", [])
    games = payload.get("games", [])
    out = [f"# MLB Public-vs-Stats Picks — {date}", ""]

    if not picks:
        out.append("**No edge picks today.** No game cleared the confidence threshold "
                   "while the public was fading the statistical favorite.")
    else:
        out.append(f"**{len(picks)} pick(s): {', '.join(picks)}**")
        out.append("")
        for g in games:
            if not g.get("flagged"):
                continue
            sa, pm, pc = g["statistical_advantage"], g["public_majority"], g["pick_criteria"]
            c = pc["components"]
            bl = g.get("betting_lines")
            out.append(f"## ✅ {g['pick']} — {g['matchup']}")
            out.append(f"- **Confidence {pc['confidence']}** (≥ {pc['threshold']}) = "
                       f"edge {c['stat_edge']['strength']} · "
                       f"fade {c['public_fade']['strength']} · "
                       f"win-cond {c['win_condition']['strength']}")
            out.append(f"- Statistical edge: **{sa['team']}** "
                       f"(home {sa['home_score']} / away {sa['away_score']}, "
                       f"margin {c['stat_edge']['margin']})")
            out.append(f"- Public is on (and we fade): **{pm['team']}** "
                       f"(fade strength {c['public_fade']['strength']})")
            out.append(f"- Win condition: **{c['win_condition']['hits']}/5**")
            if bl:
                m, n = bl["majority"], bl["non_majority"]
                out.append(f"- Moneyline: pick **{n['team']} {n['moneyline']}** — "
                           f"public on {m['team']} {m['moneyline']} ({m['consensus_pct']}%)")
            out.append("")

    out.append("")
    out.append(grade.bankroll_line())
    rev = grade.review_line()
    if rev:
        out.append("")
        out.append(rev)
    tune_status = tune.status_line()
    if tune_status:
        out.append("")
        out.append(tune_status)
    out.append(f"\n_Full per-game detail: `output/picks_{date}.json`_")
    return "\n".join(out)


def write_outputs(payload: dict, date: str) -> None:
    """Persist the picks JSON + the daily-issue artifacts (used by main and the
    pre-game refresh)."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / f"picks_{date}.json").write_text(json.dumps(payload, indent=2))
    (OUTPUT_DIR / "latest_summary.md").write_text(build_summary(payload))  # gitignored
    (OUTPUT_DIR / "latest_date.txt").write_text(date)                      # gitignored
    log.info("Wrote picks for %s (%d pick(s))", date, len(payload.get("picks", [])))


def telegram_text(payload: dict) -> str:
    """Plain-text picks summary for Telegram (no markdown that the API would garble)."""
    date = payload["date"]
    picks = payload.get("picks", [])
    lines = [f"⚾ MLB Picks — {date}"]
    if not picks:
        lines.append("No edge picks today.")
    else:
        lines.append(f"{len(picks)} pick(s): {', '.join(picks)}")
        for g in payload.get("games", []):
            if not g.get("flagged"):
                continue
            pc = g["pick_criteria"]
            c = pc["components"]
            bl = g.get("betting_lines")
            ml = f" {bl['non_majority']['moneyline']}" if bl else ""
            lines.append(
                f"• {g['pick']}{ml} — conf {pc['confidence']} "
                f"(edge {c['stat_edge']['strength']}/fade {c['public_fade']['strength']}/"
                f"wc {c['win_condition']['strength']}); fading {g['public_majority']['team']}")
    lines.append(grade.bankroll_line().replace("**", ""))
    ts = tune.status_line().replace("**", "")
    if ts:
        lines.append(ts)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="MLB public-vs-stats edge finder")
    parser.add_argument("--date", default=os.environ.get("PICKS_DATE") or today_eastern())
    args = parser.parse_args()

    payload = run(args.date)
    write_outputs(payload, args.date)
    notify.send_telegram(telegram_text(payload))
    print(json.dumps(payload.get("picks", []), indent=2))


if __name__ == "__main__":
    main()
