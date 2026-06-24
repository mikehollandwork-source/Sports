"""
Bankroll-driven auto-tuning of the pick decision parameters.

Adapts the decision over time from realized results, with deliberate guardrails so
it can't overfit a small sample or spiral:

  - INACTIVE until at least TUNE_MIN_SAMPLE settled picks exist (noise guard).
  - Tiny, bounded steps per update, every parameter clamped to a sane range.
  - A dead-band on ROI so it doesn't fidget around break-even.
  - Every change is logged to output/tuning.json (history) and is fully
    reversible - delete the file to snap back to the analysis.py defaults.

Two things adapt:
  1. CONF_MIN (selectivity) by bankroll ROI: losing -> raise the bar; winning ->
     lower it a touch. This is the direct "adjust with the bankroll" lever.
  2. The component weights (W_EDGE/W_FADE/W_WC) shift slightly toward whichever
     signal best separated past wins from losses, then renormalize.

analysis.py loads output/tuning.json at import, so the next run picks up the
tuned params. Runs from grade (the daily "grade yesterday" step) so today's picks
use the freshly-tuned values.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

log = logging.getLogger("tune")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TUNING_PATH = OUTPUT_DIR / "tuning.json"

# the parameters under tuning, with their factory defaults (kept in sync with
# analysis.py - if absent there, these are the fallback)
DEFAULTS = {"CONF_MIN": 0.50, "EDGE_FULL": 0.40, "W_EDGE": 0.34, "W_FADE": 0.33, "W_WC": 0.33}

# --- guardrails ---------------------------------------------------------------
TUNE_MIN_SAMPLE = 20        # settled picks required before tuning does anything
TUNE_ROI_DEADBAND = 0.05    # |units/pick| inside this -> leave selectivity alone
CONF_STEP = 0.01            # CONF_MIN nudge per update
CONF_RANGE = (0.45, 0.65)
WEIGHT_STEP = 0.01          # weight shifted from worst to best discriminator
WEIGHT_RANGE = (0.20, 0.50)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _mean(xs: list) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def load_params() -> dict:
    """Current tuned params (or factory defaults if no tuning file yet)."""
    try:
        t = json.loads(TUNING_PATH.read_text())
        return {k: float(t.get("params", {}).get(k, v)) for k, v in DEFAULTS.items()}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def _component_gaps(entries: list) -> dict | None:
    """For each component, mean strength on wins minus mean strength on losses.
    Positive => that signal was higher when we won (predictive)."""
    wins = [e for e in entries if e.get("result") == "W"]
    losses = [e for e in entries if e.get("result") == "L"]
    if not wins or not losses:
        return None
    gaps = {}
    for key, field in (("W_EDGE", "edge_strength"), ("W_FADE", "fade_strength"),
                       ("W_WC", "wc_strength")):
        w, l = _mean([e.get(field) for e in wins]), _mean([e.get(field) for e in losses])
        if w is not None and l is not None:
            gaps[key] = w - l
    return gaps or None


def auto_tune(ledger: dict) -> dict:
    """Recompute tuned params from the ledger and persist output/tuning.json.
    Returns the tuning state (always writes the file so status is visible)."""
    entries = ledger.get("entries", [])
    n = len(entries)
    cur = load_params()
    new = dict(cur)
    changes: list[str] = []
    roi = round(ledger.get("bankroll", 0.0) / n, 3) if n else 0.0

    if n >= TUNE_MIN_SAMPLE:
        # 1) selectivity from bankroll ROI
        if roi < -TUNE_ROI_DEADBAND:
            new["CONF_MIN"] = round(_clamp(cur["CONF_MIN"] + CONF_STEP, *CONF_RANGE), 3)
            if new["CONF_MIN"] != cur["CONF_MIN"]:
                changes.append(f"CONF_MIN {cur['CONF_MIN']}→{new['CONF_MIN']} (ROI {roi:+.2f} → tighten)")
        elif roi > TUNE_ROI_DEADBAND:
            new["CONF_MIN"] = round(_clamp(cur["CONF_MIN"] - CONF_STEP, *CONF_RANGE), 3)
            if new["CONF_MIN"] != cur["CONF_MIN"]:
                changes.append(f"CONF_MIN {cur['CONF_MIN']}→{new['CONF_MIN']} (ROI {roi:+.2f} → loosen)")

        # 2) shift weight from the least- to the most-predictive component
        gaps = _component_gaps(entries)
        if gaps and len(gaps) >= 2:
            best, worst = max(gaps, key=gaps.get), min(gaps, key=gaps.get)
            if best != worst and gaps[best] - gaps[worst] > 0:
                nb = _clamp(cur[best] + WEIGHT_STEP, *WEIGHT_RANGE)
                nw = _clamp(cur[worst] - WEIGHT_STEP, *WEIGHT_RANGE)
                if nb != cur[best] or nw != cur[worst]:
                    new[best], new[worst] = nb, nw
                    s = new["W_EDGE"] + new["W_FADE"] + new["W_WC"]
                    for k in ("W_EDGE", "W_FADE", "W_WC"):
                        new[k] = round(new[k] / s, 3)
                    changes.append(f"weight shift → {best} up, {worst} down")

    history = []
    try:
        history = json.loads(TUNING_PATH.read_text()).get("history", [])
    except (OSError, ValueError):
        pass
    if changes:
        history.append({"date": dt.date.today().isoformat(), "roi_per_pick": roi,
                        "samples": n, "changes": changes, "params": new})

    state = {
        "params": new,
        "active": n >= TUNE_MIN_SAMPLE,
        "samples": n,
        "min_samples": TUNE_MIN_SAMPLE,
        "roi_per_pick": roi,
        "history": history[-50:],
    }
    OUTPUT_DIR.mkdir(exist_ok=True)
    TUNING_PATH.write_text(json.dumps(state, indent=2))
    if changes:
        log.info("auto-tune applied: %s", "; ".join(changes))
    else:
        log.info("auto-tune: no change (active=%s, samples=%d/%d, ROI %.2f)",
                 state["active"], n, TUNE_MIN_SAMPLE, roi)
    return state


def status_line(state: dict | None = None) -> str:
    """One-line tuning status for the daily issue."""
    if state is None:
        try:
            state = json.loads(TUNING_PATH.read_text())
        except (OSError, ValueError):
            return ""
    p = state["params"]
    if not state["active"]:
        return (f"**Auto-tune:** warming up ({state['samples']}/{state['min_samples']} "
                f"settled picks) — using defaults.")
    last = state["history"][-1]["changes"] if state.get("history") else []
    tail = f" Last: {'; '.join(last)}." if last else " No change this run."
    return (f"**Auto-tune (active, ROI {state['roi_per_pick']:+.2f}/pick):** "
            f"CONF_MIN {p['CONF_MIN']}, weights edge {p['W_EDGE']}/fade {p['W_FADE']}/"
            f"wc {p['W_WC']}.{tail}")
