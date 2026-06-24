"""
Get stricter after losing days; relax when it recovers.

Simple, intuitive risk control: the only thing that adapts is selectivity
(CONF_MIN). After back-to-back losing days the bar to make a pick rises; each
additional consecutive losing day raises it a bit more (capped). The moment a day
turns a profit, it snaps back to the default. Nothing else changes.

State is written to output/tuning.json, which analysis.py loads on the next run.
Fully reversible: delete that file to return to the analysis.py default.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

log = logging.getLogger("tune")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TUNING_PATH = OUTPUT_DIR / "tuning.json"

DEFAULT_CONF_MIN = 0.50    # baseline bar (matches analysis.py)
STREAK_TO_TIGHTEN = 2      # losing days in a row before tightening kicks in
STRICT_STEP = 0.03         # CONF_MIN bump per consecutive losing day
CONF_MIN_MAX = 0.65        # how strict it can ever get


def _daily_pnl(entries: list) -> list[tuple[str, float]]:
    """Net profit per settled date, oldest -> newest."""
    days: dict[str, float] = {}
    for e in entries:
        days[e["date"]] = round(days.get(e["date"], 0.0) + e.get("profit", 0.0), 2)
    return [(d, days[d]) for d in sorted(days)]


def _losing_streak(daily: list[tuple[str, float]]) -> int:
    """Consecutive losing days (net < 0) ending at the most recent settled day."""
    streak = 0
    for _, pnl in reversed(daily):
        if pnl < 0:
            streak += 1
        else:
            break
    return streak


def conf_min_for_streak(streak: int) -> float:
    """Default until a back-to-back losing streak, then +STRICT_STEP per day, capped."""
    if streak < STREAK_TO_TIGHTEN:
        return DEFAULT_CONF_MIN
    return round(min(CONF_MIN_MAX, DEFAULT_CONF_MIN + STRICT_STEP * (streak - 1)), 3)


def auto_tune(ledger: dict) -> dict:
    """Recompute CONF_MIN from the recent losing streak and persist tuning.json."""
    daily = _daily_pnl(ledger.get("entries", []))
    streak = _losing_streak(daily)
    conf = conf_min_for_streak(streak)

    prev = None
    history: list = []
    try:
        old = json.loads(TUNING_PATH.read_text())
        prev = old.get("params", {}).get("CONF_MIN")
        history = old.get("history", [])
    except (OSError, ValueError):
        pass
    if prev != conf:
        verb = "tightened" if conf > DEFAULT_CONF_MIN else "reset to default"
        history.append({"date": dt.date.today().isoformat(), "losing_streak": streak,
                        "conf_min": conf, "note": verb})
        log.info("auto-tune: %d losing day(s) in a row -> CONF_MIN %s (%s)", streak, conf, verb)
    else:
        log.info("auto-tune: streak %d, CONF_MIN %s (no change)", streak, conf)

    state = {
        "params": {"CONF_MIN": conf},
        "losing_streak": streak,
        "default_conf_min": DEFAULT_CONF_MIN,
        "daily_pnl": daily[-10:],
        "history": history[-50:],
    }
    OUTPUT_DIR.mkdir(exist_ok=True)
    TUNING_PATH.write_text(json.dumps(state, indent=2))
    return state


def status_line(state: dict | None = None) -> str:
    """One-line tuning status for the daily issue."""
    if state is None:
        try:
            state = json.loads(TUNING_PATH.read_text())
        except (OSError, ValueError):
            return ""
    streak = state.get("losing_streak", 0)
    conf = state["params"]["CONF_MIN"]
    if conf > state.get("default_conf_min", DEFAULT_CONF_MIN):
        return (f"**Auto-tune:** {streak} losing day(s) in a row → stricter, "
                f"CONF_MIN raised to {conf}.")
    return f"**Auto-tune:** no losing streak → CONF_MIN at default {conf}."
