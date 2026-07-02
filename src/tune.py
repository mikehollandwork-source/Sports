"""
Get stricter after losing days; relax when it recovers.

Simple, intuitive risk control: the only thing that adapts is selectivity - the
required stat-edge threshold (EDGE_THRESHOLD). After back-to-back losing days the
edge a pick must clear rises; each additional consecutive losing day raises it a
bit more (capped). The moment a day turns a profit, it snaps back to the default.
Nothing else changes.

State is written to output/tuning.json, which analysis.py loads on the next run.
Fully reversible: delete that file to return to the analysis.py default.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

log = logging.getLogger("tune")

# Kill switch (user request): the auto-tuner is OFF for now. auto_tune() does
# nothing and status_line() stays silent; flip to True to re-enable.
TUNER_ENABLED = False

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TUNING_PATH = OUTPUT_DIR / "tuning.json"

DEFAULT_EDGE_THRESHOLD = 0.40   # baseline stat-edge bar (matches analysis.py)
STREAK_TO_TIGHTEN = 2           # losing days in a row before tightening kicks in
STRICT_STEP = 0.03              # raise the required edge per consecutive losing day
EDGE_THRESHOLD_MAX = 0.55       # how strict it can ever get


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


def edge_threshold_for_streak(streak: int) -> float:
    """Default until a back-to-back losing streak, then demand a bigger edge each
    consecutive losing day (+STRICT_STEP), capped."""
    if streak < STREAK_TO_TIGHTEN:
        return DEFAULT_EDGE_THRESHOLD
    return round(min(EDGE_THRESHOLD_MAX, DEFAULT_EDGE_THRESHOLD + STRICT_STEP * (streak - 1)), 3)


def auto_tune(ledger: dict) -> dict:
    """Recompute the required stat-edge threshold from the Picks book's recent
    losing streak (stricter = bigger edge demanded); persist."""
    if not TUNER_ENABLED:
        log.info("auto-tuner disabled")
        return {}
    daily = _daily_pnl(ledger.get("picks", {}).get("entries", []))
    streak = _losing_streak(daily)
    thr = edge_threshold_for_streak(streak)

    prev = None
    history: list = []
    try:
        old = json.loads(TUNING_PATH.read_text())
        prev = old.get("params", {}).get("EDGE_THRESHOLD")
        history = old.get("history", [])
    except (OSError, ValueError):
        pass
    if prev != thr:
        verb = "tightened" if thr > DEFAULT_EDGE_THRESHOLD else "reset to default"
        history.append({"date": dt.date.today().isoformat(), "losing_streak": streak,
                        "edge_threshold": thr, "note": verb})
        log.info("auto-tune: %d losing day(s) in a row -> EDGE_THRESHOLD %s (%s)", streak, thr, verb)
    else:
        log.info("auto-tune: streak %d, EDGE_THRESHOLD %s (no change)", streak, thr)

    state = {
        "params": {"EDGE_THRESHOLD": thr},
        "losing_streak": streak,
        "default_edge_threshold": DEFAULT_EDGE_THRESHOLD,
        "daily_pnl": daily[-10:],
        "history": history[-50:],
    }
    OUTPUT_DIR.mkdir(exist_ok=True)
    TUNING_PATH.write_text(json.dumps(state, indent=2))
    return state


def status_line(state: dict | None = None) -> str:
    """One-line tuning status for the daily issue."""
    if not TUNER_ENABLED:
        return ""
    if state is None:
        try:
            state = json.loads(TUNING_PATH.read_text())
        except (OSError, ValueError):
            return ""
    streak = state.get("losing_streak", 0)
    thr = state.get("params", {}).get("EDGE_THRESHOLD")
    if thr is None:   # pre-rewrite (old CONF_MIN schema) - skip until next grade
        return ""
    if thr > state.get("default_edge_threshold", DEFAULT_EDGE_THRESHOLD):
        return (f"**Auto-tune:** {streak} losing day(s) in a row → stricter, "
                f"stat-edge bar raised to {thr}.")
    return f"**Auto-tune:** no losing streak → stat-edge bar at default {thr}."
