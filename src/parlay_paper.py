"""
The five-leg ticket, PAPER TRADED in its own book. Nothing is staked.

WHAT THIS IS
A requested structure, logged at real market prices and settled honestly so it
accumulates a record of its own:

  1. the moneyline pick already on the board
  2. and 3. two different players to get one hit
  4. total bases 2+ for the hitter our power model likes most

FOUR LEGS, NOT FIVE. The alternate-strikeout "banker" was dropped on the
measurement that was supposed to justify it. `alt_k.md` scored it out of sample
over 891 starts: a starter clears his exact prior minimum only 92.0% of the
time, and it gets WORSE with more starts (89.4% at 16+ prior starts) because a
minimum is the smallest value in a sample and drifts down. A leg like that is
priced near certainty, so it added almost nothing to the payout while removing
8% of the ticket. Four legs at the same other four pay slightly less and win
meaningfully more often, which is the whole trade.

SEPARATE FROM EVERYTHING, BY DESIGN
It writes to `output/parlay_paper.json` and touches NOTHING else. Not the
moneyline ledger, not `prop_ledger`, not the bankroll. The individual hit props
keep being recorded as singles in their own book exactly as before, and a leg
appearing here does not change, remove or duplicate that single.
`record_audit.paper_parlay_guard` asserts the separation from the files
themselves rather than trusting this docstring.

IT IS BUILT AS A SAME-GAME TICKET, and that is a measured choice, not a
convenience. `parlay_structure.md` found same-team hit props co-move at ×1.035
for pairs and ×1.135 for triples while the opposite-team control sits at ×0.996
— so legs drawn from one game have a higher true joint probability than a book
pricing them independently assumes. The team winning, its hitters getting hits
and its opposing starter recording fewer strikeouts are the same night going one
way. That correlation is the only thing that makes a parlay better than its
legs. (Many books now price same-game parlays WITH a correlation adjustment; if
this book does, the captured price already contains it and the paper record
will show that honestly.)

THE STRUCTURE CHANGED ON 2026-10-14, BY REQUEST: the ticket is now TWO
HITTERS WHO MADE THE SELECTION BUT WHOSE PRICE DOES NOT BEAT THEIR READ -
exactly the `prop_withheld` population, the bats that cleared the rising
filter, the short-night gate and the score order and were then held because a
REAL quote demanded more than the read delivers.

THIS IS EXPECTED TO LOSE MORE THAN THE SINGLES DID, AND THE ARITHMETIC SAYING
SO IS NOT IN DOUBT. A parlay's EV is the PRODUCT of its legs' EVs, so two
negative legs multiply: the first pair this was computed on (Aranda 56.8% at
-179, DeLuca 55.0% at -181) are -11.5% and -14.6% alone and **-24.4%**
together, needing 41.3% and delivering 31.2%. Nor does it depend on the reads
being right - if they are too low and the true rates regress up toward the
61.7% pooled rate, the legs get less bad but the parlay stays worse than the
singles at every calibration, and the moment a leg turns positive the correct
move is to post it as a SINGLE. The only thing that can make a parlay beat its
legs is correlation, and `leg_markets` measured same-team HIT props at ×1.001
on 5800 combos - noise. Reaching break-even on that first pair would have
taken ×1.323.

It is logged anyway because it was asked for, it costs nothing, and a forward
record is the only thing that settles a disagreement about a number. Each
ticket therefore stores `expected` - the modelled joint rate, the break-even
the price demands and the EV - so the record can be read against what it was
predicted to do rather than against zero.

NO LEG HERE IS ALSO A SINGLE, and that inverts the old guard. The four-leg
ticket's hits legs were POSTED props, so each had to exist in the singles book
beside it; these are WITHHELD props, which by definition were not posted and
must NOT appear there. `record_audit.paper_parlay_guard` asserts whichever
direction applies, per ticket, from the `structure` stamp.

WHAT IT IS EXPECTED TO DO
Lose, slowly. `parlay_structure.md` puts the best available structure at −6.5%
with the correlation lift credited in full, and the retired `prop_grade` parlay
book ran −28.2% over 67 bets with a CI that excludes zero. The point of paper
trading is that it costs nothing to find out whether THIS structure, with a
near-certain banker and correlated legs, lands closer to the first number than
the second.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import market_log, mlb_api, prop_odds

log = logging.getLogger("parlay_paper")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
BOOK = OUTPUT_DIR / "parlay_paper.json"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

STAKE = 5.0                # notional only; nothing is placed
TB_POINT = 1.5             # "2+ total bases" is the OVER 1.5 outcome
HITS_POINT = 0.5           # "1+ hit" is the OVER 0.5 outcome
TIER = "log"               # yields to the posted bets in prop_odds.may_spend

# Stamped on every ticket so the book stays separable: the four-leg tickets
# already settled are a different product and must not be pooled with these.
STRUCTURE = "held_pair"
LEGS_WANTED = 2

TB_MARKET = "batter_total_bases"


def _ticket_path(date: str) -> Path:
    return OUTPUT_DIR / f"parlay_paper_{date}.json"


def _dec(american: int) -> float:
    return american / 100 + 1 if american > 0 else 100 / abs(american) + 1


def _american(dec: float) -> int:
    return round((dec - 1) * 100) if dec >= 2 else -round(100 / (dec - 1))


def _outcomes(event_id: str, market: str) -> list:
    if not prop_odds.may_spend(TIER):
        log.info("parlay_paper: credits near reserve, skipping %s", market)
        return []
    return market_log._event_markets(event_id, market)


def _pick_over(outs: list, who: str, point: float) -> int | None:
    """The Over price for this player at this exact point, or None."""
    for o in outs:
        if (o.get("name") or "").lower() != "over":
            continue
        # Folded, like every other cross-feed name match: The Odds API and
        # MLB disagree on accents in both directions, so a bare .lower() loses
        # the price and the whole ticket goes unbooked for a missing leg.
        if prop_odds.fold_name(o.get("description") or "") != \
                prop_odds.fold_name(who):
            continue
        if abs(float(o.get("point", -999)) - point) < 1e-6:
            return o.get("price")
    return None


def build_ticket(date: str) -> dict | None:
    """Assemble tonight's held-pair ticket from the board. Returns it, or None.

    The pool is every WITHHELD prop on an upcoming game: a bat that made the
    data cut and whose price does not beat its read. Ranked by that read and
    the top two taken, which is the same order the props themselves are
    ranked in.

    Legs may come from DIFFERENT GAMES and that is deliberate. The four-leg
    ticket was same-game because `parlay_structure` credited a same-team
    correlation lift; `leg_markets` then corrected that to ×1.001 on 5800
    combos, so for HIT props there is nothing to harvest by staying in one
    game, and ranking across the slate finds two held bats on nights one game
    has only one.
    """
    board_path = OUTPUT_DIR / f"picks_{date}.json"
    try:
        board = json.loads(board_path.read_text())
    except (OSError, ValueError) as exc:
        log.warning("no board for %s (%s)", date, exc)
        return None

    pool = []
    for g in board.get("games", []):
        if g.get("state") != "upcoming":
            continue
        pc = g.get("pick_criteria") or {}
        held = pc.get("prop_withheld")
        for h in (held if isinstance(held, list) else [held]) if held else []:
            # A real captured quote is the whole point of the structure: the
            # leg is here BECAUSE the price beats the read, which cannot be
            # said of an assumed price. `_prop_withheld` only withholds on a
            # real quote now, so this is belt and braces.
            if not isinstance(h, dict) or not h.get("player_id") \
                    or not isinstance(h.get("odds"), int) \
                    or not isinstance(h.get("score"), (int, float)):
                continue
            pool.append({**h, "game_pk": g.get("game_pk"),
                         "matchup": g.get("matchup")})
    pool.sort(key=lambda h: h["score"], reverse=True)

    legs, used, missing = [], set(), []
    for h in pool:
        if len(legs) >= LEGS_WANTED:
            break
        if h["player_id"] in used:
            continue
        used.add(h["player_id"])
        legs.append({"leg": "hits", "player": h.get("player"),
                     "player_id": h["player_id"], "game_pk": h["game_pk"],
                     "matchup": h.get("matchup"), "team": h.get("team"),
                     "line": HITS_POINT, "odds": h["odds"],
                     "read": round(float(h["score"]), 4),
                     "needs": round(float(h.get("need") or 0), 4),
                     "note": "1+ hit; HELD as a single - the price does not "
                             "beat the read"})
    if len(legs) < LEGS_WANTED:
        missing.append(f"hits ({LEGS_WANTED - len(legs)} short of "
                       f"{LEGS_WANTED} held bats; the slate withheld "
                       f"{len(pool)} priced prop(s))")

    ticket = {"date": date, "structure": STRUCTURE,
              "matchup": " + ".join(sorted({x["matchup"] for x in legs
                                            if x.get("matchup")})) or None,
              "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "stake": STAKE, "paper": True,
              "legs": legs, "missing": missing}
    if legs and not missing:
        dec = 1.0
        joint = 1.0
        for x in legs:
            dec *= _dec(int(x["odds"]))
            joint *= x["read"]
        ticket["parlay_odds"] = _american(dec)
        ticket["returns"] = round(STAKE * dec, 2)
        # Stored so the forward record is read against the prediction rather
        # than against zero. `joint` assumes independence, which is what the
        # ×1.001 measured lift says to assume for hit props.
        ticket["expected"] = {
            "joint_rate": round(joint, 4),
            "break_even": round(1 / dec, 4),
            "ev": round(joint * dec - 1, 4),
            "basis": "legs independent (leg_markets same-team hit lift "
                     "x1.001 on 5800 combos)"}
    OUTPUT_DIR.mkdir(exist_ok=True)
    _ticket_path(date).write_text(json.dumps(ticket, indent=1))
    log.info("parlay_paper %s: %s, %d/%d leg(s), missing=%s",
             date, STRUCTURE, len(legs), LEGS_WANTED, missing or "none")
    return ticket


# --- settlement ---------------------------------------------------------------

def _grade_leg(leg: dict, pk: int, results: dict) -> bool | None:
    """Did this leg win? None when it cannot be confirmed yet.

    `pk` is the ticket's game. A held-pair ticket may draw its legs from
    DIFFERENT games, so a leg carrying its own `game_pk` settles against that
    one; a leg without it falls back to the ticket's, which is every leg on
    every four-leg ticket already written to disk.
    """
    pk = leg.get("game_pk") or pk
    kind = leg["leg"]
    if kind == "moneyline":
        r = results.get(pk)
        if not r or not r.get("final"):
            return None
        return r.get("winner") == leg["team"]
    if kind == "hits":
        h = mlb_api.player_hits(pk, leg["player_id"])
        return None if h is None else h >= 1
    if kind == "total_bases":
        tb = mlb_api.player_total_bases(pk, leg["player_id"])
        return None if tb is None else tb >= leg["line"] + 0.5
    if kind == "alt_strikeouts":
        # The leg is no longer built, but a ticket file written before it was
        # dropped still has one on disk, and settlement must not silently
        # mis-grade it. Kept for that, not because anything generates it.
        k = mlb_api.pitcher_strikeouts(pk, leg["player_id"])
        return None if k is None else k >= leg["line"]
    return None


def _load_book() -> dict:
    try:
        return json.loads(BOOK.read_text())
    except (OSError, ValueError):
        return {"paper": True, "stake": STAKE, "bankroll": 0.0,
                "record": {"wins": 0, "losses": 0, "tickets": 0},
                "entries": []}


def settle(date: str) -> dict:
    """Grade the date's ticket into the paper book. Idempotent per date."""
    book = _load_book()
    if any(e["date"] == date for e in book["entries"]):
        return book
    try:
        ticket = json.loads(_ticket_path(date).read_text())
    except (OSError, ValueError):
        return book
    legs = ticket.get("legs") or []
    if not legs or "parlay_odds" not in ticket:
        log.info("parlay_paper %s: ticket was never fully priced, not booked",
                 date)
        return book
    pk = ticket.get("game_pk")          # absent on a held-pair ticket
    results = mlb_api.results_for(date)
    graded = []
    for leg in legs:
        leg = {**leg, "_date": date}
        got = _grade_leg(leg, pk, results)
        if got is None:
            log.info("parlay_paper %s: %s not settled yet", date, leg["leg"])
            return book                 # all or nothing; retry later
        graded.append({**{k: v for k, v in leg.items() if k != "_date"},
                       "won": got})
    won = all(x["won"] for x in graded)
    profit = (round(ticket["returns"] - STAKE, 2) if won else -STAKE)
    book["entries"].append({
        "date": date, "matchup": ticket["matchup"],
        "structure": ticket.get("structure", "four_leg"),
        "expected": ticket.get("expected"),
        "odds": ticket["parlay_odds"], "legs": graded,
        "result": "W" if won else "L", "profit": profit,
        "lost_on": [x["leg"] for x in graded if not x["won"]]})
    book["record"]["tickets"] = len(book["entries"])
    book["record"]["wins"] = sum(1 for e in book["entries"]
                                 if e["result"] == "W")
    book["record"]["losses"] = sum(1 for e in book["entries"]
                                   if e["result"] == "L")
    book["bankroll"] = round(sum(e["profit"] for e in book["entries"]), 2)
    OUTPUT_DIR.mkdir(exist_ok=True)
    BOOK.write_text(json.dumps(book, indent=1))
    log.info("parlay_paper %s: %s (%+.2f) — book %d-%d %+.2fu",
             date, "WON" if won else "lost", profit,
             book["record"]["wins"], book["record"]["losses"],
             book["bankroll"] / STAKE)
    return book


def lines() -> list[str]:
    """Human-readable state of the paper book. Always labelled."""
    book = _load_book()
    n = len(book["entries"])
    out = ["📄 PAPER PARLAY — nothing staked, separate from every ledger"]
    if not n:
        return out + ["   no settled tickets yet"]
    roi = book["bankroll"] / (n * STAKE) * 100
    out.append(f"   {book['record']['wins']}-{book['record']['losses']} · "
               f"{book['bankroll']:+.2f} of {n * STAKE:.0f} staked "
               f"({roi:+.1f}% paper ROI)")
    for e in book["entries"][-5:]:
        out.append(f"   {e['date']} {e['odds']:+d} {e['result']}"
                   + (f" — lost on {', '.join(e['lost_on'])}"
                      if e["lost_on"] else ""))
    return out


def recap_lines(date: str) -> list[str]:
    """The day's paper ticket and the book's running record, for the recap.

    Settles first, because the recap can fire before this module's own
    workflow has run and a result that exists must not be missing from the
    one message that reports how it is going. `settle` is idempotent per date
    and all-or-nothing, so calling it here can never double-book or book a
    partial ticket.

    LABELLED PAPER ON EVERY LINE IT CAN BE. It sits directly under the real
    records in the recap, and a reader skimming on a phone must not be able to
    mistake one for the other.
    """
    try:
        settle(date)
    except Exception as exc:                 # never cost the recap its records
        log.warning("paper settle during recap failed: %s", exc)
    book = _load_book()
    entries = book.get("entries") or []
    today = [e for e in entries if e.get("date") == date]
    out = ["", "📄 PAPER PARLAY (not a bet · no money · not in any ledger)"]
    if today:
        for e in today:
            mark = "✅ WON " if e["result"] == "W" else "❌ LOST"
            legs = " + ".join(f"{x.get('player') or x.get('team')}"
                              for x in e.get("legs") or [])
            out.append(f"{mark}  {legs} ({e['odds']:+d})")
            exp = e.get("expected") or {}
            if exp:
                out.append(f"        modelled {exp['joint_rate']:.0%} vs the "
                           f"{exp['break_even']:.0%} it needed "
                           f"({exp['ev']:+.0%} expected)")
            if e.get("lost_on"):
                lost = ", ".join(
                    x.get("player") or x.get("team") or x["leg"]
                    for x in e.get("legs") or [] if not x.get("won"))
                out.append(f"        lost on {lost}")
    else:
        # Say WHICH, because "no ticket" and "not settled" mean different
        # things and only one of them means look again.
        try:
            t = json.loads(_ticket_path(date).read_text())
            out.append("   built but not settled: "
                       + (", ".join(t.get("missing") or [])
                          or "waiting on a final boxscore"))
        except (OSError, ValueError):
            out.append("   no ticket today")
    n = len(entries)
    if n:
        roi = book["bankroll"] / (n * STAKE) * 100
        out.append(f"   Paper record: {book['record']['wins']}-"
                   f"{book['record']['losses']} ({roi:+.1f}% on paper)")
        # The structure changed on 2026-10-14, so a pooled line over both is
        # two products in one number. Split whenever both are present.
        held = [e for e in entries if e.get("structure") == "held_pair"]
        if held and len(held) != n:
            hp = sum(e["profit"] for e in held)
            hw = sum(1 for e in held if e["result"] == "W")
            out.append(f"   of which held-pair: {hw}-{len(held) - hw} "
                       f"({hp / (len(held) * STAKE) * 100:+.1f}%)")
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    import argparse
    ap = argparse.ArgumentParser()
    today = dt.datetime.now(EASTERN).date()
    ap.add_argument("--date", default=today.isoformat())
    ap.add_argument("--settle", default=(today - dt.timedelta(days=1)).isoformat())
    a = ap.parse_args()
    build_ticket(a.date)
    settle(a.settle)
    print("\n".join(lines()))


if __name__ == "__main__":
    main()
