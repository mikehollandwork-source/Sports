"""
Prop grading: settle the daily 1+ HIT props into their OWN ledger, kept fully
separate from the moneyline picks record and its all-time totals.

Two books (output/prop_ledger.json):
  singles - the player 1+ hit prop bet alone
  parlays - the ML pick + its prop as a 2-leg parlay (wins only if the picked
            team WINS and the player records a hit)

Real vs assumed: the player's hit and the team's win are graded from the box
score / results (REAL). ROI uses an assumed 1+hit price (PROP_PRICE, override
with the env var) because real prop lines aren't captured; the parlay combines
the REAL team moneyline with that assumed prop price. Idempotent per game.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import zoneinfo
from pathlib import Path

from . import grade, mlb_api

log = logging.getLogger("prop_grade")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
LEDGER_PATH = OUTPUT_DIR / "prop_ledger.json"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

PROP_PRICE = int(os.environ.get("PROP_PRICE", "-200"))   # assumed 1+ hit line
STAKE = 1.0


def _empty() -> dict:
    return {"bankroll": 0.0, "record": {"wins": 0, "losses": 0, "bets": 0}, "entries": []}


def load_ledger() -> dict:
    try:
        led = json.loads(LEDGER_PATH.read_text())
        led.setdefault("singles", _empty())
        led.setdefault("parlays", _empty())
        return led
    except (OSError, ValueError):
        return {"stake": STAKE, "prop_price": PROP_PRICE,
                "singles": _empty(), "parlays": _empty()}


def _dec(american: int) -> float:
    """American odds -> decimal multiplier (total return per 1 staked)."""
    return american / 100 + 1 if american > 0 else 100 / abs(american) + 1


def parlay_odds(a: int, b: int) -> int:
    """Two American odds combined into one American price for the 2-leg parlay."""
    dec = _dec(a) * _dec(b)
    return round((dec - 1) * 100) if dec >= 2 else -round(100 / (dec - 1))


def grade_date(date: str) -> tuple[list, list]:
    """(single_entries, parlay_entries) for the date's props on FINAL games."""
    picks_path = OUTPUT_DIR / f"picks_{date}.json"
    if not picks_path.exists():
        return [], []
    payload = json.loads(picks_path.read_text())
    results = mlb_api.results_for(date)
    singles, parlays = [], []
    for g in payload.get("games", []):
        pc = g.get("pick_criteria") or {}
        prop = pc.get("prop")
        adv = pc.get("advantage_team")
        pid = (prop or {}).get("player_id")
        res = results.get(g.get("game_pk"))
        if not prop or not pid or not adv or not res or not res.get("final"):
            continue
        hits = mlb_api.player_hits(g.get("game_pk"), pid)
        if hits is None:
            continue                       # can't confirm the prop -> skip, retry later
        got_hit = hits >= 1
        team_won = res.get("winner") == adv
        score = f"{res['away']} {res['away_score']} @ {res['home']} {res['home_score']}"
        key = f"{date}#{g['game_pk']}"
        # single: the prop alone, at the assumed prop price
        singles.append({
            "key": key, "date": date, "matchup": g["matchup"],
            "bet": f"{prop['player']} 1+ H", "result": "W" if got_hit else "L",
            "score": score, "odds": PROP_PRICE,
            "profit": round(grade.american_profit(PROP_PRICE) if got_hit else -STAKE, 2)})
        # parlay: team ML + prop; needs a real team price
        ml = pc.get("advantage_moneyline")
        if ml is not None:
            won = team_won and got_hit
            po = parlay_odds(int(ml), PROP_PRICE)
            parlays.append({
                "key": key, "date": date, "matchup": g["matchup"],
                "bet": f"{adv} ML + {prop['player']} 1+ H",
                "result": "W" if won else "L", "score": score, "odds": po,
                "profit": round(grade.american_profit(po) if won else -STAKE, 2)})
    return singles, parlays


def update(date: str) -> dict:
    led = load_ledger()
    s, p = grade_date(date)
    ns = grade._add(led["singles"], s)
    npar = grade._add(led["parlays"], p)
    if ns or npar:
        log.info("props %s: +%d singles, +%d parlays (singles %+.2fu / parlays %+.2fu)",
                 date, ns, npar, led["singles"]["bankroll"], led["parlays"]["bankroll"])
    OUTPUT_DIR.mkdir(exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(led, indent=2))
    return led


def records_lines(md: bool = True) -> list[str]:
    """Prop records (singles + parlays), windowed like the ML record. `md` picks
    the markdown vs telegram flavor. Always labeled as a separate, assumed-price book."""
    led = load_ledger()
    today = dt.datetime.now(EASTERN).date()
    price = led.get("prop_price", PROP_PRICE)
    head = f"🎯 PROP RECORDS (1+ hit · assumed {price:+d} · separate from ML)"
    out = [head] if not md else [f"**{head}**"]
    for name, book in (("Prop singles", led["singles"]), ("Prop parlays (ML + prop)", led["parlays"])):
        rec = grade.windowed_records(book, today)
        if not rec:
            out.append(f"- **{name}:** no settled props yet" if md else f"{name}: none yet")
            continue
        w, l, u = grade._tally(book["entries"])
        if md:
            out.append(f"- **{name}:** " + grade._fmt_windows(rec)
                       + f" · All-time {w}-{l} {u:+.2f}u")
        else:
            out.append(f"{name}:")
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
