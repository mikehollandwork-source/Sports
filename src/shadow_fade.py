"""
Shadow ledger for the fade-hot-bats rule. Records, grades, decides nothing.

THE RULE, FROZEN
Back the COLD-bats side when all of the following hold:
  * both teams have a form read, and the deltas differ
  * the line moved AGAINST the hotter side by at least MOVE_MIN
  * the cold side is priced between -130 and even money
Fixed at the values below and not to be tuned. Tuning a rule while recording it
is how a shadow ledger turns into another in-sample fit.

WHY THIS IS SHADOW AND NOT A PLAY
It failed four of its five pre-registered checks: n=34, corrected p=0.478, and
an edge CI of -27.8% to +38.9% against a price-only control. The one thing it
has going for it is that -130 sat at the top of the sweep and the cell itself
was positive. That is worth a forward record and nothing more.

The honest expectation, stated now so it cannot be revised later: the backtest
cell returned +3.4% against a price-only control of -1.7%, so the edge on offer
is about +5 points, and ~663 games would be needed to call a real +10% edge.
This ledger accrues roughly 34 games a quarter. It will not be conclusive for
years. It exists so that IF it is ever acted on, the decision rests on
out-of-sample games rather than on the scan that produced it.

WHY IT READS THE BOARD A DAY LATE
`_lock_started_games` freezes each game at first pitch, so the next day's board
file holds exactly the closing prices the backtest measured. Reading it
retrospectively reproduces the backtest's inputs exactly and removes any
question of when to snapshot. Nothing is decided with hindsight - the rule is
fixed above, and only games on or after START_FROM are eligible.

START_FROM is the day after the analysis ran. Backfilling earlier dates would
re-import the very games the rule was selected on and quietly relabel in-sample
data as a forward record.

output/shadow_fade_hot_bats.json:
  {rule: {...}, entries: [{date, game_pk, matchup, bet, odds, hot, cold,
                           form_delta_hot, form_delta_cold, implied_shift,
                           recorded_at, won, profit}]}

Touches no ledger, no board, no record. Fails soft everywhere.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
from pathlib import Path

from . import grade, mlb_api

log = logging.getLogger("shadow_fade")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
LEDGER = OUTPUT_DIR / "shadow_fade_hot_bats.json"

# --- the frozen rule ---------------------------------------------------------
MOVE_MIN = 0.01          # line must move at least this far against the hot side
PRICE_FLOOR = -130       # cold side no more expensive than this
START_FROM = "2026-08-11"

RULE = {"move_min": MOVE_MIN, "price_floor": PRICE_FLOOR,
        "start_from": START_FROM,
        "description": "back the cold-bats side when the line moves against the "
                       "hot side and the cold side is -130 or cheaper"}


def load() -> dict:
    try:
        d = json.loads(LEDGER.read_text())
        d.setdefault("entries", [])
        return d
    except (OSError, ValueError):
        return {"rule": RULE, "entries": []}


def save(d: dict) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    d["rule"] = RULE
    LEDGER.write_text(json.dumps(d, indent=1))


def candidates(date: str) -> list[dict]:
    """Games on `date`'s frozen board that satisfy the rule. Prices only; no
    results are read here, so this is exactly what a live selector would see."""
    try:
        board = json.loads((OUTPUT_DIR / f"picks_{date}.json").read_text())
    except (OSError, ValueError):
        return []
    out = []
    for g in board.get("games", []):
        matchup = g.get("matchup") or ""
        if " @ " not in matchup:
            continue
        pc = g.get("pick_criteria") or {}
        adv = pc.get("advantage_team")
        a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
        if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
            continue
        away, home = matchup.split(" @ ")
        opp = home if adv == away else away
        price = {adv: a_ml, opp: o_ml}

        form = g.get("form") or {}
        fh, fa = form.get("home") or {}, form.get("away") or {}
        dh, da = fh.get("delta"), fa.get("delta")
        if not isinstance(dh, (int, float)) or not isinstance(da, (int, float)):
            continue
        if dh == da:
            continue
        hot, cold = (home, away) if dh > da else (away, home)

        shift = (pc.get("line_check") or {}).get("implied_shift")
        if not isinstance(shift, (int, float)):
            continue
        if (shift if hot == adv else -shift) > -MOVE_MIN:
            continue                                  # line not against the hot side
        if not (PRICE_FLOOR <= price[cold] < 0):
            continue                                  # outside the price band

        out.append({
            "date": date, "game_pk": g.get("game_pk"), "matchup": matchup,
            "bet": cold, "odds": price[cold], "hot": hot, "cold": cold,
            "form_delta_hot": dh if hot == home else da,
            "form_delta_cold": da if hot == home else dh,
            "implied_shift": shift,
        })
    return out


def _board_dates() -> list[str]:
    return sorted(Path(f).stem.split("picks_")[1]
                  for f in glob.glob(str(OUTPUT_DIR / "picks_2026-*.json")))


def run() -> dict:
    """Record any new qualifying games, then grade anything now final.

    Idempotent and self-healing: re-running re-grades open entries and skips
    games already recorded, so a missed day backfills itself on the next run."""
    led = load()
    seen = {(e["date"], e["game_pk"]) for e in led["entries"]}
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    added = 0
    for date in _board_dates():
        if date < START_FROM:
            continue
        for c in candidates(date):
            if (date, c["game_pk"]) in seen:
                continue
            c.update({"recorded_at": now, "won": None, "profit": None})
            led["entries"].append(c)
            added += 1

    graded = 0
    by_date: dict = {}
    for e in led["entries"]:
        if e.get("won") is None:
            by_date.setdefault(e["date"], []).append(e)
    for date, entries in by_date.items():
        try:
            results = mlb_api.results_for(date)
        except Exception as exc:
            log.warning("results unavailable for %s: %s", date, exc)
            continue
        for e in entries:
            res = results.get(e["game_pk"])
            if not res or not res.get("final") or not res.get("winner"):
                continue
            e["won"] = res["winner"] == e["bet"]
            e["profit"] = round(
                grade.american_profit(e["odds"]) if e["won"] else -1.0, 3)
            graded += 1

    led["entries"].sort(key=lambda e: (e["date"], e["game_pk"] or 0))
    save(led)
    log.info("shadow fade: +%d recorded, %d graded, %d total",
             added, graded, len(led["entries"]))
    return led


def report(led: dict | None = None) -> str:
    led = led or load()
    entries = led.get("entries") or []
    done = [e for e in entries if e.get("won") is not None]
    md = ["# Shadow ledger — fade the hot bats at -130 or cheaper", "",
          "_Forward record only. No money, no board, no effect on the main "
          "ledger. Recorded from each day's frozen board, which holds the same "
          "closing prices the backtest used._", "",
          f"- rule: `{RULE['description']}`",
          f"- recording since **{START_FROM}**",
          f"- qualifying games: **{len(entries)}** · graded: **{len(done)}**", ""]
    if not done:
        md += ["No graded games yet.", ""]
        return "\n".join(md)

    w = sum(1 for e in done if e["won"])
    u = sum(e["profit"] for e in done)
    md += ["## Running record", "",
           f"- **{w}-{len(done)-w}** ({w/len(done):.0%}) · {u:+.2f}u · "
           f"**{u/len(done):+.1%}** ROI", "",
           "For context, and not as a target: the backtest cell returned +3.4% "
           "on n=34 with a corrected p of 0.478, and ~663 games would be needed "
           "to call a real +10% edge. At roughly 34 qualifying games a quarter "
           "this stays inconclusive for years.", "",
           "## Games", "", "| date | matchup | bet | odds | result |",
           "|---|---|---|---|---|"]
    for e in done[-40:]:
        md.append(f"| {e['date']} | {e['matchup']} | {e['bet']} | {e['odds']:+d} "
                  f"| {'W' if e['won'] else 'L'} {e['profit']:+.2f}u |")
    md.append("")
    pend = [e for e in entries if e.get("won") is None]
    if pend:
        md += [f"_{len(pend)} recorded but not yet graded._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    led = run()
    md = report(led)
    (OUTPUT_DIR / "shadow_fade_hot_bats.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
