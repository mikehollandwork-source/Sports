"""
The five-leg ticket, PAPER TRADED in its own book. Nothing is staked.

WHAT THIS IS
A requested structure, logged at real market prices and settled honestly so it
accumulates a record of its own:

  1. alternate strikeouts on a starter, at a number he has essentially always
     cleared
  2. the moneyline pick already on the board
  3. total bases 2+ for the hitter our power model likes most
  4. and 5. two different players to get one hit

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

WHAT IT IS EXPECTED TO DO
Lose, slowly. `parlay_structure.md` puts the best available structure at −6.5%
with the correlation lift credited in full, and the retired `prop_grade` parlay
book ran −28.2% over 67 bets with a CI that excludes zero. The point of paper
trading is that it costs nothing to find out whether THIS structure, with a
near-certain banker and correlated legs, lands closer to the first number than
the second.

THE BANKER LEG IS DELIBERATELY ONE UNDER HIS PRIOR MINIMUM, not at it.
`alt_k.md` measured both out of sample: the exact prior minimum clears 92.0% and
one under it clears 97.0%. "A number he has never missed" is a minimum over a
sample, and it gets WORSE with more starts (93.3% at 8-11 prior starts, 89.4% at
16+) because the minimum drifts down. Flip `BANKER_OFFSET` to 0 for the literal
version.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import alt_k, market_log, mlb_api, prop_odds

log = logging.getLogger("parlay_paper")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
BOOK = OUTPUT_DIR / "parlay_paper.json"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

STAKE = 5.0                # notional only; nothing is placed
BANKER_OFFSET = 1          # one under his prior minimum - see the docstring
TB_POINT = 1.5             # "2+ total bases" is the OVER 1.5 outcome
HITS_POINT = 0.5           # "1+ hit" is the OVER 0.5 outcome
TIER = "log"               # yields to the posted bets in prop_odds.may_spend

ALT_K_MARKET = "pitcher_strikeouts_alternate"
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
        if (o.get("description") or "").strip().lower() != who.strip().lower():
            continue
        if abs(float(o.get("point", -999)) - point) < 1e-6:
            return o.get("price")
    return None


def _alt_k_over(outs: list, who: str, line: int) -> int | None:
    """Alternate strikeout markets quote one outcome per number, so the "line"
    is the point and clearing it means Over that many. Books differ on whether
    `N+` is listed at point N or N-0.5; both are accepted."""
    for o in outs:
        if (o.get("description") or "").strip().lower() != who.strip().lower():
            continue
        pt = o.get("point")
        if not isinstance(pt, (int, float)):
            continue
        if abs(pt - line) < 1e-6 or abs(pt - (line - 0.5)) < 1e-6:
            return o.get("price")
    return None


def build_ticket(date: str) -> dict | None:
    """Assemble tonight's ticket from the board. Returns it, or None.

    One game only, chosen as the board's PLAY if there is one - that is the
    game whose moneyline leg exists - otherwise the first upcoming game.
    """
    board_path = OUTPUT_DIR / f"picks_{date}.json"
    try:
        board = json.loads(board_path.read_text())
    except (OSError, ValueError) as exc:
        log.warning("no board for %s (%s)", date, exc)
        return None
    games = [g for g in board.get("games", [])
             if g.get("state") == "upcoming"]
    if not games:
        log.info("parlay_paper: no upcoming game on %s", date)
        return None
    plays = [g for g in games
             if (g.get("pick_criteria") or {}).get("play") == "pick"]
    g = (plays or games)[0]
    pc = g.get("pick_criteria") or {}
    away, home = (g.get("matchup") or " @ ").split(" @ ")

    eid = None
    try:
        for e in prop_odds._get("/events", dateFormat="iso") or []:
            if (e.get("away_team") == away and e.get("home_team") == home
                    and market_log._et_date(e.get("commence_time")) == date):
                eid = e.get("id")
                break
    except Exception as exc:
        log.warning("event lookup failed: %s", exc)

    legs = []
    missing = []

    # 1. the banker: alternate strikeouts on a starter
    hist = alt_k.starts_by_pitcher()
    best = None
    for side in ("home", "away"):
        sp = ((g.get("statistical_advantage") or {}).get(side) or {}).get(
            "probable_pitcher")
        if not sp:
            continue
        for pid, items in hist.items():
            if items and items[-1][1] == sp:
                prior = [x for x in items if x[0] < date]
                sl = alt_k.safe_line(prior, BANKER_OFFSET)
                if sl and (best is None or sl["line"] > best[1]["line"]):
                    best = (sp, sl, pid)
                break
    if best:
        who, sl, pid = best
        price = _alt_k_over(_outcomes(eid, ALT_K_MARKET), who,
                            sl["line"]) if eid else None
        legs.append({"leg": "alt_strikeouts", "player": who, "player_id": pid,
                     "line": sl["line"], "prior_min": sl["prior_min"],
                     "prior_starts": sl["prior_starts"], "odds": price,
                     "measured_rate": 0.970 if BANKER_OFFSET else 0.920,
                     "note": f"{sl['line']}+ K; his prior minimum was "
                             f"{sl['prior_min']} over {sl['prior_starts']} "
                             "starts"})
    else:
        missing.append("alt_strikeouts (no starter with enough prior starts)")

    # 2. the board's moneyline pick
    ml = pc.get("bet_moneyline")
    team = pc.get("bet_team")
    if ml is None:
        ml, team = pc.get("advantage_moneyline"), pc.get("advantage_team")
    if pc.get("play") == "pick" and team and isinstance(ml, int):
        legs.append({"leg": "moneyline", "team": team, "odds": ml,
                     "note": "the pick already on the board"})
    else:
        missing.append("moneyline (no play on this game)")

    # 4 and 5 FIRST: two different players for one hit.
    #
    # Deliberately before the total-bases leg. On a thin slate the board may
    # post only one prop, and taking it for total bases consumed the only
    # hitter and left the two hits legs empty - which is backwards, because the
    # hits legs are the measured product with their own recorded singles and
    # the total-bases leg is the speculative one.
    used: set = set()
    for b in pc.get("props") or []:
        if len(used) >= 2:
            break
        pid_ = b.get("player_id")
        if pid_ in used:
            continue              # never two legs on the same player
        used.add(pid_)
        legs.append({"leg": "hits", "player": b.get("player"),
                     "player_id": pid_, "line": HITS_POINT,
                     "odds": b.get("odds"),
                     "note": "1+ hit; also recorded as its own single"})
    short = 2 - len(used)
    if short > 0:
        missing.append(f"hits ({short} short of two distinct players; the "
                       "board posted "
                       f"{len(pc.get('props') or [])} prop(s) on this game)")

    # 3. total bases 2+ for the power model's hitter, from the HR pick if there
    # is one, otherwise the best posted bat NOT already carrying a hits leg.
    hp = pc.get("hr_prop") or {}
    tb_who, tb_id = hp.get("player"), hp.get("player_id")
    if not tb_who:
        spare = [b for b in (pc.get("props") or [])
                 if b.get("player_id") not in used]
        if spare:
            tb_who, tb_id = spare[0].get("player"), spare[0].get("player_id")
    if tb_who:
        price = _pick_over(_outcomes(eid, TB_MARKET), tb_who,
                           TB_POINT) if eid else None
        legs.append({"leg": "total_bases", "player": tb_who,
                     "player_id": tb_id, "line": TB_POINT, "odds": price,
                     "note": "2+ total bases; the bat the power model likes"
                             + ("" if hp.get("player") else
                                " (no HR pick tonight, so the best posted bat "
                                "not already on a hits leg)")})
    else:
        missing.append("total_bases (no hitter left to use)")

    priced = [x for x in legs if isinstance(x.get("odds"), int)]
    ticket = {"date": date, "game_pk": g.get("game_pk"),
              "matchup": g.get("matchup"), "event_id": eid,
              "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "stake": STAKE, "paper": True,
              "legs": legs, "missing": missing,
              "banker_offset": BANKER_OFFSET}
    if len(priced) == len(legs) and legs:
        dec = 1.0
        for x in legs:
            dec *= _dec(int(x["odds"]))
        ticket["parlay_odds"] = _american(dec)
        ticket["returns"] = round(STAKE * dec, 2)
    else:
        ticket["unpriced"] = [x["leg"] for x in legs
                              if not isinstance(x.get("odds"), int)]
    OUTPUT_DIR.mkdir(exist_ok=True)
    _ticket_path(date).write_text(json.dumps(ticket, indent=1))
    log.info("parlay_paper %s: %d leg(s), %d priced, missing=%s",
             date, len(legs), len(priced), missing or "none")
    return ticket


# --- settlement ---------------------------------------------------------------

def _grade_leg(leg: dict, pk: int, results: dict) -> bool | None:
    """Did this leg win? None when it cannot be confirmed yet."""
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
    pk = ticket["game_pk"]
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
