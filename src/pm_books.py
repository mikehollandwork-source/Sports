"""
Stage 2: live Polymarket ORDER-BOOK collection for the day's board.

The trade-out backtest died on reconstructed history (only 4/147 games had a
real pre-game print), so the dataset gets collected forward instead: during
game hours a poller records, for every game with a stat-advantage side, the
REAL order book of our side's token - best bid, best ask, and top-of-book size
- every ~10 minutes from before lock through the game. That measures the two
things the auto-bettor needs before any wallet exists:

  1. entry quality: is there actually depth to fill 15 min before first pitch,
     and at what spread vs the book's moneyline?
  2. the trade-out rule: with real quotes, does 'sell at entry + X cents'
     beat holding to settlement?

Day file output/pm_books_<date>.json:
  {date, games: {game_pk: {matchup, side, token, play, ref, game_datetime,
                           readings: [{t, bid, ask, bid_sz, ask_sz} | {t, empty}]}}}

The side's token is chosen once per game on a PRE-GAME reading, validated
against the board's frozen moneyline (the trade-out backtest showed gamma's
name->token pairing can't be trusted blind); later readings reuse it, because
in-game prices legitimately diverge from the pre-game reference. Endpoints are
best-effort/fail-soft like every other fetcher here.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import time
import zoneinfo
from pathlib import Path

import requests

from . import apitime, grade, kalshi
from .public_sources import _name_abbr

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pm_books")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
GAMMA = "https://gamma-api.polymarket.com/events"
BOOK = "https://clob.polymarket.com/book"
TIMEOUT = 15
SIDE_TOL = 0.12   # pre-game mid must sit within this of the board's moneyline


def _get(url: str, **params):
    try:
        with apitime.timed("pm", url.rsplit("/", 1)[-1]):
            r = requests.get(url, params=params, timeout=TIMEOUT,
                             headers={"User-Agent": "mlb-edge-finder (personal research)"})
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        log.warning("fetch failed (%s): %s", url, exc)
        return None


def _implied(ml) -> float:
    ml = int(ml)
    return 100.0 / (ml + 100) if ml > 0 else -ml / (-ml + 100.0)


def open_market_index() -> dict:
    """{(away_abbr, home_abbr): {abbr: token_id}} for OPEN MLB game markets."""
    index: dict = {}
    offset = 0
    while True:
        batch = _get(GAMMA, tag_slug="mlb", closed="false", limit=100, offset=offset)
        if not isinstance(batch, list) or not batch:
            break
        for ev in batch:
            for m in ev.get("markets") or []:
                try:
                    outcomes, tokens = m.get("outcomes"), m.get("clobTokenIds")
                    if isinstance(outcomes, str):
                        outcomes = json.loads(outcomes)
                    if isinstance(tokens, str):
                        tokens = json.loads(tokens)
                    if not outcomes or not tokens or len(outcomes) != 2 or len(tokens) != 2:
                        continue
                    a1, a2 = _name_abbr(str(outcomes[0])), _name_abbr(str(outcomes[1]))
                    if not a1 or not a2 or a1 == a2:
                        continue
                    tok = {a1: tokens[0], a2: tokens[1]}
                    index[(a1, a2)] = tok
                    index[(a2, a1)] = tok
                except Exception:
                    continue
        offset += 100
        if len(batch) < 100:
            break
        time.sleep(0.2)
    log.info("gamma: %d open market keys", len(index))
    return index


def best_of_book(token_id: str) -> dict | None:
    """{bid, ask, bid_sz, ask_sz} top-of-book for a token, or None on failure.
    An empty (untraded) book returns {'empty': True}."""
    data = _get(BOOK, token_id=token_id)
    if data is None:
        return None
    try:
        bids = [(float(b["price"]), float(b["size"])) for b in data.get("bids") or []]
        asks = [(float(a["price"]), float(a["size"])) for a in data.get("asks") or []]
    except Exception:
        return None
    if not bids and not asks:
        return {"empty": True}
    out: dict = {}
    if bids:
        p, s = max(bids, key=lambda x: x[0])
        out["bid"], out["bid_sz"] = p, s
    if asks:
        p, s = min(asks, key=lambda x: x[0])
        out["ask"], out["ask_sz"] = p, s
    return out


def _mid(b: dict) -> float | None:
    if b.get("bid") is not None and b.get("ask") is not None:
        return (b["bid"] + b["ask"]) / 2
    return b.get("bid") if b.get("bid") is not None else b.get("ask")


def _pick_token(tok: dict, adv_ab: str, opp_ab: str, ref: float | None,
                pregame: bool) -> tuple[str | None, dict | None]:
    """Our side's token. Pre-game with a moneyline reference, the chosen token's
    mid must sit near it - if the named token misses but the opponent's token
    matches, gamma's pairing was inverted and we take the flip. Returns
    (token_id, its book reading) or (None, None) when nothing validates."""
    named = tok.get(adv_ab)
    book = best_of_book(named) if named else None
    if not pregame or ref is None:
        return (named, book) if book else (None, None)
    m = _mid(book) if book and not book.get("empty") else None
    if m is not None and abs(m - ref) <= SIDE_TOL:
        return named, book
    other = tok.get(opp_ab)
    ob = best_of_book(other) if other else None
    om = _mid(ob) if ob and not ob.get("empty") else None
    if om is not None and abs(om - ref) <= SIDE_TOL:
        log.info("side flip: %s token matched the moneyline, %s did not", opp_ab, adv_ab)
        return other, ob
    # neither side matches the reference pre-game: book is empty/way off - keep
    # the named token but only if its book at least exists, so depth gets logged.
    return (named, book) if book else (None, None)


def path_for(date: str) -> Path:
    return OUTPUT_DIR / f"pm_books_{date}.json"


def load_day(date: str) -> dict:
    """A day's recorded books ({} when the poller hasn't produced one yet)."""
    try:
        return json.loads(path_for(date).read_text())
    except (OSError, ValueError):
        return {}


def run(date: str | None = None) -> int:
    date = date or dt.datetime.now(EASTERN).date().isoformat()
    picks_path = OUTPUT_DIR / f"picks_{date}.json"
    if not picks_path.exists():
        log.info("no picks file for %s - nothing to poll", date)
        return 0
    games = json.loads(picks_path.read_text()).get("games", [])
    targets = [g for g in games if (g.get("pick_criteria") or {}).get("advantage_team")]
    if not targets:
        log.info("no advantage sides on %s - nothing to poll", date)
        return 0

    try:
        day = json.loads(path_for(date).read_text())
    except (OSError, ValueError):
        day = {"date": date, "games": {}}

    index = None    # PM markets, fetched lazily if some game needs registration
    kindex = None   # Kalshi markets, same
    now = int(time.time())
    polled = 0
    for g in targets:
        pk = str(g.get("game_pk"))
        pc = g["pick_criteria"]
        if " @ " not in g.get("matchup", ""):
            continue
        away, home = g["matchup"].split(" @ ")
        a_ab, h_ab = _name_abbr(away), _name_abbr(home)
        adv = pc["advantage_team"]
        adv_ab = h_ab if adv == home else a_ab
        opp_ab = a_ab if adv == home else h_ab
        ml = pc.get("advantage_moneyline")
        ref = _implied(ml) if ml is not None else None
        start = str(g.get("game_datetime", ""))
        pregame = True
        try:
            st = dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
            pregame = now < int(st.timestamp())
        except Exception:
            pass

        entry = day["games"].get(pk)
        book = None
        if entry is None or not entry.get("token"):
            if index is None:
                index = open_market_index()
            tok = index.get((a_ab, h_ab)) if a_ab and h_ab else None
            if tok and adv_ab in tok:
                token, book = _pick_token(tok, adv_ab, opp_ab, ref, pregame)
                if token:
                    entry = entry or {"matchup": g["matchup"], "side": adv,
                                      "play": grade._play(g) == "pick", "ref": ref,
                                      "game_datetime": start, "readings": []}
                    entry["token"] = token
                    day["games"][pk] = entry
        else:
            book = best_of_book(entry["token"])
        if entry is not None and book is not None:
            entry["readings"].append({"t": now, **book})
            polled += 1
        time.sleep(0.25)

        # ---- Kalshi leg: same game, second venue, same cadence ----
        if entry is None:
            # no PM market found yet; still track Kalshi alone so the venue
            # comparison isn't biased toward games PM happened to list.
            entry = day["games"].get(pk)
            if entry is None:
                entry = {"matchup": g["matchup"], "side": adv,
                         "play": grade._play(g) == "pick", "ref": ref,
                         "game_datetime": start, "readings": []}
                day["games"][pk] = entry
        if not entry.get("k_ticker"):
            if kindex is None:
                kindex = kalshi.game_markets()
            pair = kindex.get((a_ab, h_ab)) if a_ab and h_ab else None
            kt = (pair or {}).get(adv_ab)
            if kt:
                kb = kalshi.top_of_book(kt)
                m = _mid(kb) if kb and not kb.get("empty") else None
                # pre-game the named market's mid must match the moneyline; if it
                # doesn't but the other team's does, the name mapping was wrong.
                if pregame and ref is not None and m is not None and abs(m - ref) > SIDE_TOL:
                    ko = (pair or {}).get(opp_ab)
                    kob = kalshi.top_of_book(ko) if ko else None
                    om = _mid(kob) if kob and not kob.get("empty") else None
                    if om is not None and abs(om - ref) <= SIDE_TOL:
                        kt, kb = ko, kob
                if kb is not None:
                    entry["k_ticker"] = kt
                    entry.setdefault("k_readings", []).append({"t": now, **kb})
        else:
            kb = kalshi.top_of_book(entry["k_ticker"])
            if kb is not None:
                entry.setdefault("k_readings", []).append({"t": now, **kb})
        time.sleep(0.25)

    OUTPUT_DIR.mkdir(exist_ok=True)
    path_for(date).write_text(json.dumps(day, indent=1))
    log.info("pm books: %d game(s) polled -> %s", polled, path_for(date).name)
    return polled


def main() -> None:
    run()


if __name__ == "__main__":
    main()
