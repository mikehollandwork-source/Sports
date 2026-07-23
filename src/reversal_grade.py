"""
Reversal-play grading: settle the bvp+form "public-darling" FADE plays into
their OWN ledger, fully separate from the moneyline picks record.

A reversal play is a promoted no-play: when our advantage side carries the
bvp+form narrative profile (which fades profitably), we bet its OPPONENT at the
opponent moneyline. This grades those bets vs the result into
output/reversal_ledger.json - never touching the proven ML record.

Backtest-mined and validated on the no-play subset (24-12 / +25% ROI); this is
the forward, out-of-sample record that decides whether it earns a live promotion.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import grade, mlb_api

log = logging.getLogger("reversal_grade")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
LEDGER_PATH = OUTPUT_DIR / "reversal_ledger.json"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
STAKE = 1.0


def _empty() -> dict:
    return {"bankroll": 0.0, "record": {"wins": 0, "losses": 0, "bets": 0}, "entries": []}


def load_ledger() -> dict:
    try:
        led = json.loads(LEDGER_PATH.read_text())
        led.setdefault("fades", _empty())
        return led
    except (OSError, ValueError):
        return {"stake": STAKE, "fades": _empty()}


def grade_date(date: str) -> list:
    """Reversal (opponent-fade) entries for the date's FINAL games."""
    picks_path = OUTPUT_DIR / f"picks_{date}.json"
    if not picks_path.exists():
        return []
    payload = json.loads(picks_path.read_text())
    results = mlb_api.results_for(date)
    out = []
    for g in payload.get("games", []):
        rev = (g.get("pick_criteria") or {}).get("reversal")
        res = results.get(g.get("game_pk"))
        if not rev or not rev.get("bet") or rev.get("odds") is None:
            continue
        if not res or not res.get("final") or not res.get("winner"):
            continue
        won = res["winner"] == rev["bet"]
        score = f"{res['away']} {res['away_score']} @ {res['home']} {res['home_score']}"
        out.append({
            "key": f"{date}#{g['game_pk']}", "date": date, "matchup": g["matchup"],
            "bet": f"{rev['bet']} ML (fade bvp+form)", "result": "W" if won else "L",
            "score": score, "odds": int(rev["odds"]),
            "profit": round(grade.american_profit(int(rev["odds"])) if won else -STAKE, 2)})
    return out


def update(date: str) -> dict:
    led = load_ledger()
    added = grade._add(led["fades"], grade_date(date))
    if added:
        log.info("reversal %s: +%d fades (%+.2fu)", date, added, led["fades"]["bankroll"])
    OUTPUT_DIR.mkdir(exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(led, indent=2))
    return led


def records_lines(md: bool = True) -> list[str]:
    """The reversal fade record, windowed like the ML record. Always labeled as a
    separate, forward-test book."""
    led = load_ledger()
    today = dt.datetime.now(EASTERN).date()
    head = "🔄 REVERSAL FADES (bvp+form darlings · forward test · separate from ML)"
    out = [f"**{head}**"] if md else [head]
    book = led["fades"]
    rec = grade.windowed_records(book, today)
    if not rec:
        out.append("- **Reversal fades:** no settled fades yet" if md else "Reversal fades: none yet")
        return out
    w, l, u = grade._tally(book["entries"])
    if md:
        out.append("- **Reversal fades:** " + grade._fmt_windows(rec)
                   + f" · All-time {w}-{l} {u:+.2f}u")
    else:
        out.append("Reversal fades:")
        for label, (ww, ll, uu) in rec:
            out.append(f"   • {label}: {ww}-{ll} ({uu:+.2f}u)")
        out.append(f"   • All-time: {w}-{l} ({u:+.2f}u)")
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=(dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat())
    update(ap.parse_args().date)
    print("\n".join(records_lines(md=False)))


if __name__ == "__main__":
    main()
