"""
ESPN odds: opening + current moneyline per game (free, no API key).

covers' odds page only renders an opening line for ~60% of games, so real
open->current line movement can't be computed for the rest. ESPN's API carries
open/current moneylines for essentially every game. We use ESPN purely for the
LINE (movement + captured price); public sentiment still comes from covers.

Like covers, ESPN is firewalled in the build sandbox - set ESPN_DEBUG=1 for one
run to dump the raw JSON into output/espn_debug/ so the exact field paths can be
verified, then the parser is finalized against that.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path

import requests

log = logging.getLogger("espn")

DEBUG = os.environ.get("ESPN_DEBUG") == "1"
DEBUG_DIR = Path("output/espn_debug")
HEADERS = {"User-Agent": "mlb-edge-finder (personal research)"}
SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={}"
EVENT_ODDS = ("https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb/"
              "events/{eid}/competitions/{eid}/odds")


def _get(url: str) -> dict | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:  # network/HTTP/JSON - degrade gracefully
        log.warning("espn fetch failed (%s): %s", url, exc)
        return None
    if DEBUG:
        _dump(url, data)
    return data


def _dump(url: str, data: dict) -> None:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"\W+", "_", url.split("://", 1)[-1])[:120] + ".json"
    (DEBUG_DIR / name).write_text(json.dumps(data, indent=2)[:2_000_000])


def _events(date: str) -> list[dict]:
    """[{eid, away_abbr, home_abbr}] for the date (date = YYYY-MM-DD)."""
    data = _get(SCOREBOARD.format(date.replace("-", "")))
    if not data:
        return []
    out: list[dict] = []
    for ev in data.get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        abbr = {}
        for c in comp.get("competitors", []):
            abbr[c.get("homeAway")] = (c.get("team") or {}).get("abbreviation")
        if abbr.get("home") and abbr.get("away"):
            out.append({"eid": ev.get("id"), "away_abbr": abbr["away"], "home_abbr": abbr["home"]})
    return out


def _american(ml: dict | None) -> int | None:
    """ESPN moneyLine object -> american int. 'EVEN' = +100; OFF/blank = None."""
    if not isinstance(ml, dict):
        return None
    a = ml.get("american")
    if a in (None, "", "OFF"):
        return None
    if str(a).upper() == "EVEN":
        return 100
    try:
        return int(str(a).replace("+", ""))
    except ValueError:
        return None


def _side(team_odds: dict | None) -> tuple[int | None, int | None]:
    """(open, current) american moneyline for one team's odds block."""
    t = team_odds or {}
    op = _american(t.get("open", {}).get("moneyLine"))
    cur = _american(t.get("current", {}).get("moneyLine"))
    if cur is None and isinstance(t.get("moneyLine"), (int, float)):
        cur = int(t["moneyLine"])
    return op, cur


def lines(date: str) -> list[dict]:
    """Open + current moneyline for every game on the date, from ESPN. Same shape as
    covers.slate_lines: {away_abbr, home_abbr, away_open, home_open, away_current,
    home_current}. One request per game (plus the scoreboard)."""
    out: list[dict] = []
    for e in _events(date):
        data = _get(EVENT_ODDS.format(eid=e["eid"]))
        items = (data or {}).get("items") or []
        if not items:
            continue
        it = items[0]  # primary provider
        ao, ac = _side(it.get("awayTeamOdds"))
        ho, hc = _side(it.get("homeTeamOdds"))
        if ac is None and hc is None:
            continue
        out.append({"away_abbr": e["away_abbr"], "home_abbr": e["home_abbr"],
                    "away_open": ao, "home_open": ho,
                    "away_current": ac, "home_current": hc})
        time.sleep(0.3)
    log.info("espn: parsed %d game line(s)", len(out))
    return out


def dump_debug(date: str) -> None:
    """Fetch the scoreboard + a couple events' odds and dump the JSON. Forces the
    dump on regardless of the ESPN_DEBUG env (this function is debug-only)."""
    global DEBUG
    DEBUG = True
    evs = _events(date)
    log.info("espn debug: %d events for %s", len(evs), date)
    for e in evs[:3]:
        _get(EVENT_ODDS.format(eid=e["eid"]))
        time.sleep(0.5)


if __name__ == "__main__":
    import argparse
    import datetime as dt
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=dt.date.today().isoformat())
    DEBUG = True
    dump_debug(p.parse_args().date)
