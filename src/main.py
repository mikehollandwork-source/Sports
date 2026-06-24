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


def _ranked(games: list) -> list:
    """All games, strongest decision first (confidence desc)."""
    return sorted(games, key=lambda g: g.get("pick_criteria", {}).get("confidence", 0.0),
                  reverse=True)


def build_summary(payload: dict) -> str:
    """Markdown board for the daily issue: every matchup, its advantage team, a
    check for picks and a labelled LEAN (with the reason) for the rest."""
    date = payload["date"]
    picks = payload.get("picks", [])
    out = [f"# MLB Board — {date}", ""]
    out.append(f"**{len(picks)} pick(s)"
               + (f": {', '.join(picks)}**" if picks else " — no game cleared the bar today.**"))
    out.append("")

    for g in _ranked(payload.get("games", [])):
        pc = g["pick_criteria"]
        c = pc["components"]
        adv = pc["advantage_team"]
        comp = (f"edge {c['stat_edge']['strength']}/fade {c['public_fade']['strength']}/"
                f"wc {c['win_condition']['strength']}")
        if g.get("flagged"):
            bl = g.get("betting_lines")
            ml = f" · {bl['non_majority']['moneyline']}" if bl else ""
            out.append(f"✅ **{adv}** · {g['matchup']} · conf **{pc['confidence']}** "
                       f"({comp}){ml} · fading {g['public_majority']['team']}")
        else:
            out.append(f"🔸 LEAN **{adv}** · {g['matchup']} · conf {pc['confidence']} "
                       f"({comp}) · {pc['reason']}")
    out.append("")
    out.append("_✅ = pick (public fading the stat favorite + confidence ≥ threshold); "
               "🔸 = lean (advantage team shown, with why it missed)._")

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
    """Plain-text board for Telegram (every matchup; ✅ pick, 🔸 lean + reason)."""
    date = payload["date"]
    picks = payload.get("picks", [])
    head = f"⚾ MLB Board — {date} ({len(picks)} pick(s)"
    head += f": {', '.join(picks)})" if picks else ")"
    lines = [head]
    for g in _ranked(payload.get("games", [])):
        pc = g["pick_criteria"]
        adv = pc["advantage_team"]
        if g.get("flagged"):
            bl = g.get("betting_lines")
            ml = f" {bl['non_majority']['moneyline']}" if bl else ""
            lines.append(f"✅ {adv}{ml} ({g['matchup']}) conf {pc['confidence']} — "
                         f"fading {g['public_majority']['team']}")
        else:
            lines.append(f"🔸 {adv} ({g['matchup']}) conf {pc['confidence']} — {pc['reason']}")
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
