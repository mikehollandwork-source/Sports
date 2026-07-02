"""
Grade the board against actual MLB results and keep two running $1/unit bankrolls
in output/ledger.json:

  - Picks: 2+ of the 5 signals hit. Bet the advantage team.
  - Leans: exactly 1 signal. Bet the advantage team.
  - Fades: the opponent matched the 9-1 profile (line toward them + public not
    against them). Bet AGAINST the advantage team at the opponent's price.
  Passes (everything else) are never booked. (leans_faded is frozen history.)

Each bet is $1 on the advantage team at its **pre-game moneyline** captured from
covers' odds page (pick_criteria.advantage_moneyline). A game whose real price
wasn't captured is **skipped, not booked at even money**, so every settled bet
reflects a real price. Each book keeps a W-L record and a dollar bankroll, and is
idempotent per game (by game_pk) so re-running a day never double-counts.

Runs on GitHub Actions (the MLB API is firewalled in the build sandbox). Default
date is yesterday (US/Eastern) - grade the prior day once its games are final.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import zoneinfo
from pathlib import Path

from . import mlb_api

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("grade")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
LEDGER_PATH = OUTPUT_DIR / "ledger.json"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

STAKE = 1.0


def american_profit(odds: int, stake: float = STAKE) -> float:
    """Win profit for a `stake` bet at American `odds` (a loss is always -stake)."""
    odds = int(odds)
    return stake * odds / 100.0 if odds > 0 else stake * 100.0 / abs(odds)


def _empty_book() -> dict:
    return {"bankroll": 0.0, "record": {"wins": 0, "losses": 0, "bets": 0}, "entries": []}


def empty_ledger() -> dict:
    return {"stake": STAKE,
            "odds_basis": "pre-game moneyline from covers odds page (unpriced games skipped)",
            "grade_from": None,   # if set (YYYY-MM-DD), dates before this are never booked
            "picks": _empty_book(), "leans": _empty_book(),
            "leans_faded": _empty_book(), "fades": _empty_book()}


def load_ledger() -> dict:
    led = empty_ledger()
    try:
        old = json.loads(LEDGER_PATH.read_text())
    except (OSError, ValueError):
        return led
    if "picks" in old and "leans" in old:
        old.setdefault("leans_faded", _empty_book())   # added after the two-book schema
        old.setdefault("fades", _empty_book())         # leans-and-fades era book
        old.pop("leans_strong", None)  # short-lived tier book, folded into leans itself
        old.setdefault("grade_from", None)
        return old
    # migrate the old single-book schema (picks only) into the new layout
    if old.get("entries") is not None:
        led["picks"] = {"bankroll": old.get("bankroll", 0.0),
                        "record": {"wins": old.get("record", {}).get("wins", 0),
                                   "losses": old.get("record", {}).get("losses", 0),
                                   "bets": old.get("record", {}).get("picks", 0)},
                        "entries": old.get("entries", [])}
    return led


def save_ledger(ledger: dict) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2))


def _price(g: dict, key: str) -> int | None:
    """The captured pre-game moneyline for a side, or None if it wasn't recorded
    (in which case we DON'T book the bet - no fake even-money entries)."""
    ml = g.get("pick_criteria", {}).get(key)
    return int(ml) if ml is not None else None


def _settle(date, g, res, bet, won, odds) -> dict:
    return {
        "key": f"{date}#{g['game_pk']}",
        "date": date, "matchup": g["matchup"], "bet": bet,
        "result": "W" if won else "L",
        "score": f"{res['away']} {res['away_score']} @ {res['home']} {res['home_score']}",
        "odds": odds, "odds_source": "pre-game moneyline",
        "profit": round(american_profit(odds) if won else -STAKE, 2),
    }


def _play(g: dict) -> str:
    """Mirror of main._play. Older frozen snapshots: flagged / strong-tier map to
    lean; anything unclassified is a pass (never booked)."""
    pc = g.get("pick_criteria", {})
    if pc.get("play") in ("pick", "lean", "fade", "pass"):
        return pc["play"]
    if g.get("flagged") or pc.get("lean_tier") == "strong":
        return "lean"
    return "pass"


def grade_date(date: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Settle every final game into (pick_entries, lean_entries, fade_entries).
    Picks/leans bet the advantage team at its pre-game price; fades bet the OTHER
    side at its price. Passes and games without a captured price are never booked."""
    picks_path = OUTPUT_DIR / f"picks_{date}.json"
    if not picks_path.exists():
        log.warning("no picks file for %s", date)
        return [], [], []
    payload = json.loads(picks_path.read_text())
    results = mlb_api.results_for(date)

    pick_entries: list[dict] = []
    lean_entries: list[dict] = []
    fade_entries: list[dict] = []
    for g in payload.get("games", []):
        pc = g.get("pick_criteria", {})
        adv = pc.get("advantage_team")
        res = results.get(g.get("game_pk"))
        if not adv or not res or not res["final"] or not res["winner"]:
            continue
        play = _play(g)
        if play in ("pick", "lean"):
            odds = _price(g, "advantage_moneyline")
            if odds is not None:
                entry = _settle(date, g, res, adv, res["winner"] == adv, odds)
                (pick_entries if play == "pick" else lean_entries).append(entry)
        elif play == "fade":
            opp = res["home"] if adv == res["away"] else res["away"]
            f_odds = _price(g, "opponent_moneyline")
            if f_odds is not None:
                fade_entries.append(_settle(date, g, res, opp, res["winner"] == opp, f_odds))
    return pick_entries, lean_entries, fade_entries


def _add(book: dict, entries: list[dict]) -> int:
    done = {e["key"] for e in book["entries"]}
    added = 0
    for e in entries:
        if e["key"] in done:
            continue
        book["bankroll"] = round(book["bankroll"] + e["profit"], 2)
        book["record"]["wins" if e["result"] == "W" else "losses"] += 1
        book["record"]["bets"] += 1
        e["bankroll_after"] = book["bankroll"]
        book["entries"].append(e)
        added += 1
    return added


def update_ledger(date: str) -> dict:
    """Settle a date into all books. Idempotent per game (game_pk). Dates before
    the ledger's grade_from cutoff (if set) are never booked."""
    ledger = load_ledger()
    gf = ledger.get("grade_from")
    if gf and date < gf:
        log.info("skip grading %s (before grade_from %s)", date, gf)
        save_ledger(ledger)
        return ledger
    pe, le, fe = grade_date(date)
    added = (_add(ledger["picks"], pe) + _add(ledger["leans"], le)
             + _add(ledger["fades"], fe))
    if added:
        ledger["review"] = review(ledger["picks"])
        log.info("graded %s: picks %+.2f (%d-%d), leans %+.2f (%d-%d), fades %+.2f (%d-%d)",
                 date, ledger["picks"]["bankroll"], ledger["picks"]["record"]["wins"],
                 ledger["picks"]["record"]["losses"], ledger["leans"]["bankroll"],
                 ledger["leans"]["record"]["wins"], ledger["leans"]["record"]["losses"],
                 ledger["fades"]["bankroll"], ledger["fades"]["record"]["wins"],
                 ledger["fades"]["record"]["losses"])
    else:
        log.info("nothing new to settle for %s", date)
    # Always persist so the ledger artifact exists from the first grade onward
    # (an unchanged rewrite produces no git diff).
    save_ledger(ledger)
    return ledger


# --- loss review / tuning input (operates on the Picks book) ------------------
def _avg(xs: list) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 2) if xs else None


def review(book: dict) -> dict:
    e = book["entries"]
    wins = [x for x in e if x["result"] == "W"]
    losses = [x for x in e if x["result"] == "L"]
    return {"wins": len(wins), "losses": len(losses),
            "losses_as_underdog": sum(1 for x in losses if x.get("odds", 0) > 0),
            "losses_as_favorite": sum(1 for x in losses if x.get("odds", 0) < 0)}


def review_line(ledger: dict | None = None) -> str:
    ledger = ledger or load_ledger()
    rev = ledger.get("review") or review(ledger["picks"])
    if not rev["losses"]:
        return ""
    return (f"**Loss review (picks):** {rev['losses']} loss(es) — "
            f"{rev['losses_as_underdog']} as a dog, {rev['losses_as_favorite']} as a favorite.")


def _book_line(name: str, book: dict, hypothetical: bool = False) -> str:
    r = book["record"]
    tag = " (hypothetical)" if hypothetical else ""
    return (f"**{name}{tag}: {book['bankroll']:+.2f}u** "
            f"({r['wins']}-{r['losses']} on {r['bets']} bets)")


def bankroll_line(ledger: dict | None = None) -> str:
    """One-line summary of both books for the daily issue."""
    ledger = ledger or load_ledger()
    return (_book_line("Picks", ledger["picks"]) + "  ·  "
            + _book_line("Leans", ledger["leans"]) + "  ·  "
            + _book_line("Fades", ledger["fades"])
            + "  _($1/bet at pre-game moneyline)_")


# --- windowed records (Day / Week / Month / YTD) ------------------------------
def _tally(entries: list[dict]) -> tuple[int, int, float]:
    w = sum(1 for e in entries if e["result"] == "W")
    l = sum(1 for e in entries if e["result"] == "L")
    return w, l, round(sum(e.get("profit", 0.0) for e in entries), 2)


def windowed_records(book: dict, today: dt.date) -> list[tuple[str, tuple[int, int, float]]]:
    """W-L-units for a book over Day / Week / Month / YTD. Day = the most recent
    settled date; Week/Month/YTD are calendar windows (since Monday / since the
    1st / since Jan 1) ending today. Empty list when the book has no settled bets."""
    e = book["entries"]
    if not e:
        return []
    last = max(x["date"] for x in e)
    monday = (today - dt.timedelta(days=today.weekday())).isoformat()
    first = today.replace(day=1).isoformat()
    jan1 = today.replace(month=1, day=1).isoformat()
    windows = [
        (f"Day ({last})", [x for x in e if x["date"] == last]),
        ("Week", [x for x in e if x["date"] >= monday]),
        ("Month", [x for x in e if x["date"] >= first]),
        ("YTD", [x for x in e if x["date"] >= jan1]),
    ]
    return [(label, _tally(rows)) for label, rows in windows]


def _fmt_windows(rec: list) -> str:
    return " · ".join(f"{label} {w}-{l} {u:+.2f}u" for label, (w, l, u) in rec)


def records_block(ledger: dict | None = None, today: dt.date | None = None) -> str:
    """Multi-line Day/Week/Month/YTD records for BOTH books (markdown)."""
    ledger = ledger or load_ledger()
    today = today or dt.datetime.now(EASTERN).date()
    lines = ["**Records** _($1/bet at pre-game moneyline)_:"]
    for name, key, hyp in (("Picks", "picks", False), ("Leans", "leans", False),
                           ("Fades", "fades", False)):
        tag = " (hypothetical)" if hyp else ""
        rec = windowed_records(ledger[key], today)
        lines.append(f"- **{name}{tag}:** " + (_fmt_windows(rec) if rec else "no settled bets yet"))
    return "\n".join(lines)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Grade the board + update the bankroll ledgers")
    parser.add_argument("--date", default=os.environ.get("GRADE_DATE") or yesterday_eastern(),
                        help="date to grade (YYYY-MM-DD); default = yesterday US/Eastern")
    args = parser.parse_args()
    ledger = update_ledger(args.date)
    from . import tune
    state = tune.auto_tune(ledger)
    print(bankroll_line(ledger))
    print(tune.status_line(state))


if __name__ == "__main__":
    main()
