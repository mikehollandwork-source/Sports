"""
Wikipedia pageviews as a public-ATTENTION signal.

Sportsbook consensus is what one book reports; this measures what the public is
actually paying attention to - how many people read each team's Wikipedia article
in the days before the game. The more-read (more-popular/hyped) team is, for a fade
system, exactly the side you want to identify: the public piles onto popular teams.

Official Wikimedia REST API - no auth, datacenter-IP friendly, and it has full
history, so unlike consensus/forum signals this one is BACKTESTABLE (see
wiki_calibrate.py). Point-in-time: the window ends the day BEFORE the game, so no
lookahead. Fails soft: a missing article / network error just drops that team.

team_attention_counts(teams, date) -> {team_name: views} over the trailing window,
mirroring the other public sources so it slots into the same plumbing.
"""

from __future__ import annotations

import datetime as dt
import logging
import urllib.parse

import requests

log = logging.getLogger("wiki")

API = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
       "en.wikipedia/all-access/all-agents/{article}/daily/{start}/{end}")
TIMEOUT = 20
ATTENTION_DAYS = 3   # trailing days of pageviews that count as "pre-game attention"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "mlb-edge-finder/1.0 (personal betting research)"})

# Wikipedia article titles equal the MLB team name for all but a few teams.
SPECIAL = {"Athletics": "Athletics (baseball)"}

_CACHE: dict = {}


def _article(team_name: str) -> str:
    title = SPECIAL.get(team_name, team_name).replace(" ", "_")
    return urllib.parse.quote(title, safe="")


def _views(article: str, start: str, end: str) -> int | None:
    """Total daily pageviews for an article over [start, end] (YYYYMMDD), cached.
    None on a missing article (404) or any error - the caller drops that team."""
    key = (article, start, end)
    if key in _CACHE:
        return _CACHE[key]
    try:
        r = SESSION.get(API.format(article=article, start=start, end=end), timeout=TIMEOUT)
        if r.status_code == 404:
            _CACHE[key] = None
            return None
        r.raise_for_status()
        total = sum(int(it.get("views", 0) or 0) for it in r.json().get("items", []))
    except Exception as exc:
        log.warning("wiki pageviews failed for %s: %s", article, exc)
        total = None
    _CACHE[key] = total
    return total


def team_window_views(team_name: str, date: str, days: int = ATTENTION_DAYS) -> int | None:
    """Pageviews for a team in the `days` ending the day BEFORE `date` (no lookahead)."""
    end = dt.date.fromisoformat(date) - dt.timedelta(days=1)
    start = end - dt.timedelta(days=days - 1)
    return _views(_article(team_name), start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))


def team_attention_counts(teams: list[tuple[str, str]], date: str,
                          days: int = ATTENTION_DAYS) -> dict[str, int]:
    """{team_name: trailing-window pageviews} for the slate's teams. Teams whose
    article can't be read are simply omitted (fail soft)."""
    out: dict[str, int] = {}
    for name, _abbr in teams:
        v = team_window_views(name, date, days)
        if v is not None:
            out[name] = v
    log.info("wiki: pageviews for %d/%d team(s)", len(out), len(teams))
    return out
