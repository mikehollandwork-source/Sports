"""
Log the markets we have never tracked: totals, first five, and strikeout lines.

WHY THESE AND NOT ANOTHER SIGNAL
Seven searches in this repo have come back null, and every one of them re-cut
data that was already inside the moneyline. A starting pitcher's STRIKEOUT line
is different: it is a direct market estimate of his dominance that nothing here
currently reads. Same for the full-game and first-five totals - a priced view of
run environment, which we presently infer from park, weather and last-5 form
instead of reading off a market. New information is the one thing the nulls were
missing, so these are worth collecting even though the prior is poor.

LOGGING ONLY. Nothing here changes a pick, and nothing is staked. There is no
record to keep because no bet is placed - this builds the dataset that a test
needs, and the test cannot run for weeks.

CREDIT BUDGET, which is the real constraint
The Odds API bills one credit per MARKET per REGION. The probe
(`output/market_probe.md`) settled where each market lives:

    totals ................. BULK endpoint -> ONE credit for the whole slate
    pitcher_strikeouts ..... per event -> one credit per game
    totals_1st_5_innings ... per event -> one credit per game

So the full-game total is logged for EVERY game at trivial cost, while the two
per-event markets are capped. On a fifteen-game slate, logging both for
everything would cost 900 credits a month against a 500 allowance; the cap keeps
it bounded and `prop_odds.may_spend` makes this tier yield before the posted
bets do. A postseason slate of one to four games is covered in full.

Writes output/market_log_<date>.json, appending rather than overwriting so an
earlier poll's line is kept beside a later one.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import zoneinfo
from pathlib import Path

from . import prop_odds

log = logging.getLogger("market_log")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
# Per-event games to cover in one pass. Two markets each, so the real spend is
# twice this. Override with MARKET_LOG_MAX when a slate is worth more.
MAX_EVENTS = int(os.environ.get("MARKET_LOG_MAX", "4"))
PER_EVENT = ("pitcher_strikeouts", "totals_1st_5_innings")


def _best(outcomes: list, name: str) -> dict | None:
    for o in outcomes or []:
        if (o.get("name") or "").lower() == name:
            return {"price": o.get("price"), "point": o.get("point")}
    return None


def totals_slate() -> dict:
    """{matchup: {over, under, point}} for every game, on ONE credit."""
    out = {}
    try:
        data = prop_odds._get("/odds", regions="us", markets="totals",
                              oddsFormat="american")
    except Exception as exc:
        log.warning("bulk totals failed: %s", exc)
        return out
    for g in data or []:
        key = f"{g.get('away_team')}@{g.get('home_team')}"
        for b in g.get("bookmakers") or []:
            for m in b.get("markets") or []:
                if m.get("key") != "totals":
                    continue
                o, u = _best(m.get("outcomes"), "over"), _best(m.get("outcomes"), "under")
                if o and u:
                    out[key] = {"over": o["price"], "under": u["price"],
                                "point": o["point"], "book": b.get("key")}
                break
            if key in out:
                break
    return out


def _event_markets(event_id: str, market: str) -> list:
    try:
        data = prop_odds._get(f"/events/{event_id}/odds", regions="us",
                              markets=market, oddsFormat="american")
    except Exception as exc:
        log.warning("%s failed for %s: %s", market, event_id, exc)
        return []
    for b in data.get("bookmakers") or []:
        for m in b.get("markets") or []:
            if m.get("key") == market:
                return m.get("outcomes") or []
    return []


def per_event(event_id: str) -> dict:
    """Strikeout lines by pitcher, and the first-five total, for one game."""
    out = {}
    ks = _event_markets(event_id, "pitcher_strikeouts")
    by_p = {}
    for o in ks:
        who = o.get("description")
        if not who:
            continue
        side = (o.get("name") or "").lower()
        by_p.setdefault(who, {})[side] = {"price": o.get("price"),
                                          "point": o.get("point")}
    if by_p:
        out["strikeouts"] = by_p
    f5 = _event_markets(event_id, "totals_1st_5_innings")
    o, u = _best(f5, "over"), _best(f5, "under")
    if o and u:
        out["f5_total"] = {"over": o["price"], "under": u["price"],
                           "point": o["point"]}
    return out


def run(date: str | None = None) -> dict:
    date = date or dt.datetime.now(EASTERN).date().isoformat()
    path = OUTPUT_DIR / f"market_log_{date}.json"
    try:
        rec = json.loads(path.read_text())
    except (OSError, ValueError):
        rec = {"date": date, "polls": []}

    poll = {"at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "totals": {}, "events": {}}
    if prop_odds.may_spend("log"):
        poll["totals"] = totals_slate()
    else:
        log.info("market_log: skipping bulk totals, credits near reserve")

    try:
        evs = prop_odds._get("/events", dateFormat="iso") or []
    except Exception as exc:
        log.warning("events listing failed: %s", exc)
        evs = []
    done = 0
    for e in evs:
        if done >= MAX_EVENTS:
            break
        if not prop_odds.may_spend("log"):
            log.info("market_log: stopping per-event, credits near reserve")
            break
        eid = e.get("id")
        if not eid:
            continue
        got = per_event(eid)
        if got:
            poll["events"][f"{e.get('away_team')}@{e.get('home_team')}"] = got
            done += 1

    rec["polls"].append(poll)
    OUTPUT_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(rec, indent=1))
    log.info("market_log %s: %d total(s), %d event(s), remaining=%s",
             date, len(poll["totals"]), len(poll["events"]),
             prop_odds.remaining())
    return rec


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    rec = run()
    last = rec["polls"][-1]
    print(f"market_log {rec['date']}: {len(last['totals'])} full-game totals, "
          f"{len(last['events'])} games with K lines / F5")
    for k, v in list(last["totals"].items())[:6]:
        print(f"  {k:46s} O/U {v['point']}  {v['over']:+d}/{v['under']:+d}")
    for k, v in last["events"].items():
        f5 = v.get("f5_total")
        print(f"  {k}")
        if f5:
            print(f"     F5 total {f5['point']}  {f5['over']:+d}/{f5['under']:+d}")
        for p, sides in (v.get("strikeouts") or {}).items():
            o = sides.get("over") or {}
            print(f"     K {p:24s} o{o.get('point')} {o.get('price')}")


if __name__ == "__main__":
    main()
