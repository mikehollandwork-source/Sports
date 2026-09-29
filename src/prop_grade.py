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

PARLAYS ARE RETIRED (see PARLAYS_RETIRED below). The 67 already settled stay in
the ledger untouched and keep being reported; no new ones are added.
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

# --- parlays: retired 2026-08-11 ---------------------------------------------
# The only measured result in this system whose confidence interval excludes
# zero, and it is a loss: 20-47, -28.2% ROI over 67 bets, day-block bootstrap
# CI -47.4% to -6.7%. Singles over the same 67 bets are -6.7% with a CI that
# still spans zero, so this is specific to the parlay, not to props.
#
# It is not variance, and the mechanism is arithmetic rather than a pattern:
# the parlay's first leg is `advantage_moneyline` - the STAT MODEL's advantage
# team, measured at -5.9% over 581 games in `bvp_margin.md` - and its second is
# the prop at -6.7%. Two negative legs multiplied, plus the vig of each leg
# compounding into one price. Expected EV from the legs alone is about -12%,
# and the extra parlay vig accounts for the rest of the gap to -28.2%.
#
# Breakeven at the median parlay price (+153) is 39.5%; the actual hit rate is
# 29.9%.
#
# Generation is gated rather than deleted so the retirement is one flag to
# reverse, and so nothing above is orphaned. Settled parlays are NOT removed or
# altered - the record stands as it was earned.
PARLAYS_RETIRED = True
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
        # real captured 1+ hit line if we have one, else the assumed fallback
        prop_price = int(prop.get("odds", PROP_PRICE))
        # single: the prop alone
        singles.append({
            "key": key, "date": date, "matchup": g["matchup"],
            "bet": f"{prop['player']} 1+ H", "result": "W" if got_hit else "L",
            "score": score, "odds": prop_price, "real_line": "odds" in prop,
            "profit": round(grade.american_profit(prop_price) if got_hit else -STAKE, 2)})
        # parlay: team ML + prop; needs a real team price
        ml = pc.get("advantage_moneyline")
        if ml is not None and not PARLAYS_RETIRED:
            won = team_won and got_hit
            po = parlay_odds(int(ml), prop_price)
            parlays.append({
                "key": key, "date": date, "matchup": g["matchup"],
                "bet": f"{adv} ML + {prop['player']} 1+ H",
                "result": "W" if won else "L", "score": score, "odds": po,
                "real_line": "odds" in prop,
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
    entries = led["singles"]["entries"] + led["parlays"]["entries"]
    n_real = sum(1 for e in entries if e.get("real_line"))
    if n_real and n_real == len(entries):
        pricing = "real lines"
    elif n_real:
        pricing = f"{n_real}/{len(entries)} real lines, rest assumed {price:+d}"
    else:
        pricing = f"assumed {price:+d}"
    head = f"🎯 PROP RECORDS (1+ hit · {pricing} · separate from ML)"
    out = [head] if not md else [f"**{head}**"]
    par_name = ("Prop parlays (RETIRED)" if PARLAYS_RETIRED
                else "Prop parlays (ML + prop)")
    for name, book in (("Prop singles", led["singles"]), (par_name, led["parlays"])):
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
