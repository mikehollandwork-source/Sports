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
import time
import urllib.parse

import requests

log = logging.getLogger("wiki")

API = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
       "en.wikipedia/all-access/all-agents/{article}/daily/{start}/{end}")
TIMEOUT = 20
ATTENTION_DAYS = 3      # trailing days of pageviews that count as "pre-game attention"
POLITE_DELAY = 0.2      # Wikimedia throttles bursts; space the calls out
PREFETCH_DAYS = 130     # on first touch, pull a wide series so one call serves a whole
                        # calibration window (avoids the per-game 429 storm)

SESSION = requests.Session()
# Wikimedia asks for a descriptive UA with contact/URL; a generic agent gets 429'd.
SESSION.headers.update({"User-Agent": "mlb-edge-finder/1.0 "
                        "(https://github.com/mikehollandwork-source/sports; betting research)"})

# Wikipedia article titles equal the MLB team name for all but a few teams.
SPECIAL = {"Athletics": "Athletics (baseball)"}

_SERIES: dict[str, dict[str, int]] = {}        # article -> {YYYYMMDD: views}
_COVERED: dict[str, tuple[str, str]] = {}      # article -> (min, max) date fetched


def _article(team_name: str) -> str:
    title = SPECIAL.get(team_name, team_name).replace(" ", "_")
    return urllib.parse.quote(title, safe="")


def _fetch_series(article: str, start: str, end: str) -> dict[str, int] | None:
    """Daily {YYYYMMDD: views} for [start, end]. None on error; {} on a 404 (no
    such article / no data)."""
    try:
        r = SESSION.get(API.format(article=article, start=start, end=end), timeout=TIMEOUT)
        time.sleep(POLITE_DELAY)
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        return {it["timestamp"][:8]: int(it.get("views", 0) or 0)
                for it in r.json().get("items", [])}
    except Exception as exc:
        log.warning("wiki pageviews failed for %s: %s", article, exc)
        return None


def _ensure_series(article: str, start: dt.date, end: dt.date) -> None:
    """Make sure the cached daily series for `article` covers [start, end]. On first
    touch we pull a wide trailing window (PREFETCH_DAYS) so a whole backtest is one
    request per team rather than one per game."""
    s8, e8 = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
    cov = _COVERED.get(article)
    if cov and cov[0] <= s8 and cov[1] >= e8:
        return
    fstart = min(start, end - dt.timedelta(days=PREFETCH_DAYS))
    if cov:                                   # widen to also keep what we had
        fstart = min(fstart, dt.datetime.strptime(cov[0], "%Y%m%d").date())
        end = max(end, dt.datetime.strptime(cov[1], "%Y%m%d").date())
    series = _fetch_series(article, fstart.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
    if series is None:                        # transient error - don't poison the cache
        return
    _SERIES.setdefault(article, {}).update(series)
    _COVERED[article] = (fstart.strftime("%Y%m%d"), end.strftime("%Y%m%d"))


def team_window_views(team_name: str, date: str, days: int = ATTENTION_DAYS) -> int | None:
    """Pageviews for a team in the `days` ending the day BEFORE `date` (no lookahead).
    None if the series couldn't be fetched or has no data in the window."""
    article = _article(team_name)
    end = dt.date.fromisoformat(date) - dt.timedelta(days=1)
    start = end - dt.timedelta(days=days - 1)
    _ensure_series(article, start, end)
    series = _SERIES.get(article)
    if not series:
        return None
    total, hit = 0, False
    d = start
    while d <= end:
        v = series.get(d.strftime("%Y%m%d"))
        if v is not None:
            total += v
            hit = True
        d += dt.timedelta(days=1)
    return total if hit else None


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
