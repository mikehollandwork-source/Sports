"""
Grade the board against actual MLB results and keep the running $1/unit bankroll
in output/ledger.json:

  - Plays: the single betting tier (pick/lean split retired). A play needs a
    core signal (margin/line/consistency) and can't be into a mild public fade.
    Bet the advantage team.
  - Everything else is NO ACTION - listed on the board, never booked.
    (leans_faded is frozen history; the old coin-flip/LOCK book was removed from
    the record entirely - ledger v10 drops it on load.)

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
VOIDS_PATH = OUTPUT_DIR / "voids.json"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

STAKE = 1.0


def load_voids() -> dict:
    """Games the sportsbook voided/refunded (no action) - they must NOT be booked
    as a W or L. User-maintained in output/voids.json: either a bare list or
    {"voids": [...]}, each item {"date","matchup"} (matchup exactly as the board
    shows it, full team names) and/or {"game_pk": N}. Returns {pairs, pks}."""
    try:
        raw = json.loads(VOIDS_PATH.read_text())
    except (OSError, ValueError):
        return {"pairs": set(), "pks": set()}
    items = raw.get("voids", []) if isinstance(raw, dict) else raw
    pairs, pks = set(), set()
    for v in items if isinstance(items, list) else []:
        if isinstance(v, dict):
            if v.get("game_pk") is not None:
                try:
                    pks.add(int(v["game_pk"]))
                except (TypeError, ValueError):
                    pass
            if v.get("date") and v.get("matchup"):
                pairs.add((v["date"].strip(), v["matchup"].strip().casefold()))
        elif isinstance(v, str) and "|" in v:      # "YYYY-MM-DD | Away @ Home"
            d, m = v.split("|", 1)
            pairs.add((d.strip(), m.strip().casefold()))
    return {"pairs": pairs, "pks": pks}


def _voided(voids: dict, date: str, matchup: str, game_pk) -> bool:
    if game_pk is not None and int(game_pk) in voids["pks"]:
        return True
    return (date, (matchup or "").strip().casefold()) in voids["pairs"]


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
            "plays": _empty_book(), "leans_faded": _empty_book(),
            "vegas": _empty_book()}


def load_ledger() -> dict:
    led = empty_ledger()
    try:
        old = json.loads(LEDGER_PATH.read_text())
    except (OSError, ValueError):
        return led
    if "plays" in old or ("picks" in old and "leans" in old):
        old.setdefault("leans_faded", _empty_book())   # added after the two-book schema
        if old.get("locks", {}).get("entries"):        # brief 'locks' naming era
            old.setdefault("fades", _empty_book())
            old["fades"] = old.pop("locks")
        else:
            old.pop("locks", None)
        old.pop("leans_strong", None)  # short-lived tier book, folded into leans itself
        old.setdefault("grade_from", None)
        # taxonomy v6: LOCK plays graded into PICKS; stay-away money-fades became
        # the fades book. Migrate any entries the older layout booked.
        if "stay_away" in old:
            lock_book = old.get("fades") or _empty_book()
            old["fades"] = old.pop("stay_away")
            _add(old.setdefault("picks", _empty_book()), lock_book.get("entries", []))
        # taxonomy v7: LOCK plays grade in their own 'coin_flip' book. A lock is
        # the one bet NOT on its game's advantage team, so split any the v6 layout
        # merged into picks (checked against the day's frozen snapshot).
        if "coin_flip" not in old:
            keep, move = [], []
            for e in old.get("picks", {}).get("entries", []):
                (move if _is_opponent_bet(e) else keep).append(e)
            old["coin_flip"] = _empty_book()
            if move:
                pb = _empty_book()
                _add(pb, keep)
                _add(old["coin_flip"], move)
                old["picks"] = pb
        # taxonomy v8: fades (the money-fade "Vegas special") are retired - those
        # no-signal games are no-action now, so drop the book entirely.
        old.pop("fades", None)
        # taxonomy v9: the pick/lean split is retired - one PLAYS book. Merge
        # both old books' entries (replayed so bankroll/record rebuild cleanly).
        if "plays" not in old:
            merged = _empty_book()
            for k in ("picks", "leans"):
                _add(merged, (old.pop(k, None) or {}).get("entries", []))
            old["plays"] = merged
        # taxonomy v10: coin flips removed from the record entirely (user call).
        old.pop("coin_flip", None)
        # v11: display-only Vegas book (the side the SPORTSBOOK needs). Its own
        # record - never part of the all-plays/all-time line.
        old.setdefault("vegas", _empty_book())
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


def _is_opponent_bet(e: dict) -> bool:
    """True when a ledger entry bet the OPPONENT of its game's advantage team
    (i.e. it was a LOCK/coin-flip play), per the day's frozen snapshot."""
    try:
        day = json.loads((OUTPUT_DIR / f"picks_{e['date']}.json").read_text())
    except (OSError, ValueError):
        return False
    g = next((x for x in day.get("games", [])
              if x.get("matchup") == e.get("matchup")), None)
    adv = (g or {}).get("pick_criteria", {}).get("advantage_team")
    return bool(adv) and adv != e.get("bet")


def _play(g: dict) -> str:
    """Mirror of main._play (single PLAYS tier: legacy 'lean' counts as a play).
    Old 'fade' (same 9-1 rule) -> lock; anything unclassified -> stay_away."""
    pc = g.get("pick_criteria", {})
    play = pc.get("play")
    if play == "lean":
        return "pick"
    if play in ("lock", "fade", "pass"):   # coin flips retired entirely
        return "stay_away"
    if play in ("pick", "stay_away"):
        return play
    if g.get("flagged") or pc.get("lean_tier") == "strong":
        return "pick"
    return "stay_away"


def grade_date(date: str) -> list[dict]:
    """Settle every final game into play entries (bet the advantage team).
    No-action games are never booked; unpriced bets are never booked."""
    picks_path = OUTPUT_DIR / f"picks_{date}.json"
    if not picks_path.exists():
        log.warning("no picks file for %s", date)
        return []
    payload = json.loads(picks_path.read_text())
    results = mlb_api.results_for(date)
    voids = load_voids()

    play_entries: list[dict] = []
    for g in payload.get("games", []):
        pc = g.get("pick_criteria", {})
        adv = pc.get("advantage_team")
        res = results.get(g.get("game_pk"))
        if not adv or not res or not res["final"] or not res["winner"]:
            continue
        if _voided(voids, date, g.get("matchup"), g.get("game_pk")):
            log.info("skip voided game: %s %s", date, g.get("matchup"))
            continue
        play = _play(g)
        if play == "pick":
            odds = _price(g, "advantage_moneyline")
            if odds is not None:
                play_entries.append(_settle(date, g, res, adv, res["winner"] == adv, odds))
        # everything else (incl. legacy lock snapshots) is no-action: never booked.
    return play_entries


def grade_vegas(date: str) -> list[dict]:
    """Settle the display-only Vegas book: $1 on the team the SPORTSBOOK needed
    (frozen at build time in pick_criteria.vegas). Every game with a read is
    booked - it's the book's rooting interest, not one of our plays."""
    picks_path = OUTPUT_DIR / f"picks_{date}.json"
    if not picks_path.exists():
        return []
    payload = json.loads(picks_path.read_text())
    results = mlb_api.results_for(date)
    voids = load_voids()
    entries: list[dict] = []
    for g in payload.get("games", []):
        v = g.get("pick_criteria", {}).get("vegas") or {}
        bet, odds = v.get("bet"), v.get("odds")
        res = results.get(g.get("game_pk"))
        if not bet or odds is None or not res or not res["final"] or not res["winner"]:
            continue
        if _voided(voids, date, g.get("matchup"), g.get("game_pk")):
            continue
        entries.append(_settle(date, g, res, bet, res["winner"] == bet, int(odds)))
    return entries


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


def _entry_voided(voids: dict, e: dict) -> bool:
    pk = str(e.get("key", "")).rpartition("#")[2]
    if pk.isdigit() and int(pk) in voids["pks"]:
        return True
    return (e.get("date"), (e.get("matchup") or "").strip().casefold()) in voids["pairs"]


def _apply_voids(ledger: dict, voids: dict) -> int:
    """Remove any already-booked entry the void list now covers (a game the book
    refunded after we graded it), rebuilding each book's bankroll/record cleanly
    from the survivors. Returns how many were pulled."""
    removed = 0
    for k in ("plays", "vegas"):
        book = ledger.get(k)
        if not book:
            continue
        kept = [e for e in book["entries"] if not _entry_voided(voids, e)]
        if len(kept) != len(book["entries"]):
            removed += len(book["entries"]) - len(kept)
            book["entries"] = []
            book["bankroll"] = 0.0
            book["record"] = {"wins": 0, "losses": 0, "bets": 0}
            _add(book, kept)   # replay survivors -> fresh bankroll + bankroll_after
    return removed


def update_ledger(date: str) -> dict:
    """Settle a date into all books. Idempotent per game (game_pk). Dates before
    the ledger's grade_from cutoff (if set) are never booked."""
    ledger = load_ledger()
    # honor the void list first: pull any game the book refunded after we graded it
    voids = load_voids()
    if voids["pairs"] or voids["pks"]:
        pulled = _apply_voids(ledger, voids)
        if pulled:
            log.info("un-booked %d voided game(s) from the ledger", pulled)
            ledger["review"] = review(ledger["plays"])
    gf = ledger.get("grade_from")
    if gf and date < gf:
        log.info("skip grading %s (before grade_from %s)", date, gf)
        save_ledger(ledger)
        return ledger
    pe = grade_date(date)
    added = _add(ledger["plays"], pe)
    # display-only Vegas book: separate record, never in the all-time line
    va = _add(ledger.setdefault("vegas", _empty_book()), grade_vegas(date))
    if va:
        log.info("graded %s: vegas %+.2f (%d-%d)",
                 date, ledger["vegas"]["bankroll"], ledger["vegas"]["record"]["wins"],
                 ledger["vegas"]["record"]["losses"])
    if added:
        ledger["review"] = review(ledger["plays"])
        log.info("graded %s: plays %+.2f (%d-%d)",
                 date, ledger["plays"]["bankroll"], ledger["plays"]["record"]["wins"],
                 ledger["plays"]["record"]["losses"])
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
    rev = ledger.get("review") or review(ledger["plays"])
    if not rev["losses"]:
        return ""
    return (f"**Loss review (plays):** {rev['losses']} loss(es) — "
            f"{rev['losses_as_underdog']} as a dog, {rev['losses_as_favorite']} as a favorite.")


def _book_line(name: str, book: dict, hypothetical: bool = False) -> str:
    r = book["record"]
    tag = " (hypothetical)" if hypothetical else ""
    return (f"**{name}{tag}: {book['bankroll']:+.2f}u** "
            f"({r['wins']}-{r['losses']} on {r['bets']} bets)")


def combined_book(ledger: dict) -> dict:
    """Every settled bet across all live books as one synthetic book (for the
    all-plays combined record row)."""
    entries = list(ledger["plays"]["entries"])
    return {"entries": entries}


def bankroll_line(ledger: dict | None = None) -> str:
    """One-line summary of the books for the daily issue."""
    ledger = ledger or load_ledger()
    comb = combined_book(ledger)
    w, l, u = _tally(comb["entries"])
    return (_book_line("Plays", ledger["plays"]) + "  ·  "
            + f"**All plays: {u:+.2f}u** ({w}-{l})"
            + "  _($1/bet at pre-game moneyline)_")


# --- windowed records (Day / Week / Month / YTD) ------------------------------
def _tally(entries: list[dict]) -> tuple[int, int, float]:
    w = sum(1 for e in entries if e["result"] == "W")
    l = sum(1 for e in entries if e["result"] == "L")
    return w, l, round(sum(e.get("profit", 0.0) for e in entries), 2)


def windowed_records(book: dict, today: dt.date) -> list[tuple[str, tuple[int, int, float]]]:
    """W-L-units for a book over Today / Week / Month / YTD. Today = games settled
    with TODAY's date only (0-0 until today's games go final - yesterday's plays
    never carry over); Week/Month/YTD are calendar windows (since Monday / since
    the 1st / since Jan 1) ending today. Empty list when the book has no bets at all."""
    e = book["entries"]
    if not e:
        return []
    today_s = today.isoformat()
    monday = (today - dt.timedelta(days=today.weekday())).isoformat()
    first = today.replace(day=1).isoformat()
    jan1 = today.replace(month=1, day=1).isoformat()
    windows = [
        (f"Today ({today_s})", [x for x in e if x["date"] == today_s]),
        ("Week", [x for x in e if x["date"] >= monday]),
        ("Month", [x for x in e if x["date"] >= first]),
        ("YTD", [x for x in e if x["date"] >= jan1]),
    ]
    return [(label, _tally(rows)) for label, rows in windows]


def _fmt_windows(rec: list) -> str:
    return " · ".join(f"{label} {w}-{l} {u:+.2f}u" for label, (w, l, u) in rec)


def records_block(ledger: dict | None = None, today: dt.date | None = None) -> str:
    """Multi-line Day/Week/Month/YTD records per book plus the all-plays combined
    row (markdown)."""
    ledger = ledger or load_ledger()
    today = today or dt.datetime.now(EASTERN).date()
    lines = ["**Records** _($1/bet at pre-game moneyline)_:"]
    books = [("Plays", ledger["plays"]),
             ("Vegas (book's side, display only)", ledger.get("vegas") or _empty_book())]
    for name, book in books:
        rec = windowed_records(book, today)
        extra = ""
        if name == "All plays" and book["entries"]:
            w, l, u = _tally(book["entries"])
            extra = f" · All-time {w}-{l} {u:+.2f}u"
        lines.append(f"- **{name}:** "
                     + ((_fmt_windows(rec) + extra) if rec else "no settled bets yet"))
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
