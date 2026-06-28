"""
Reddit as a second public-opinion forum, to compare against covers consensus.

covers' published consensus % is one book's self-reported number; the user trusts
actual discussion more. covers' own betting forum is one such source - this adds
Reddit's betting subreddits via the public JSON API (append `.json`, no auth), and
tallies team moneyline mentions the SAME way the covers forum does (reusing
covers._post_moneyline_teams), so the two forums are measured identically.

reddit_majority(teams, date) -> {team_name: mention_count}, mirroring
covers.forum_majority so it slots into the cross-check the same way.

Reddit requires a descriptive User-Agent (default agents get 429'd). Everything
fails *soft*: on any network/JSON problem it logs and returns zero counts, so the
rest of the public read still works. Reddit is firewalled in the build sandbox, so
the selectors/endpoints are validated on a live Actions run; set REDDIT_DEBUG=1 for
one run to dump the raw JSON into output/reddit_debug/.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import time
import zoneinfo
from pathlib import Path

import requests

from .covers import _post_moneyline_teams, _team_patterns

log = logging.getLogger("reddit")

# Betting-focused subreddits where people post daily MLB moneyline picks.
SUBREDDITS = ["sportsbook", "mlbbetting", "sportsbetting"]
LISTING = "https://www.reddit.com/r/{sub}/new.json?limit=50"
THREAD = "https://www.reddit.com{permalink}.json?limit=200&depth=4"

MAX_THREADS = 12          # most-recent qualifying threads per subreddit to crawl
THREAD_AGE_HOURS = 36     # only threads this fresh (today's slate discussion)
TIMEOUT = 20
POLITE_DELAY = 1.0
EASTERN = zoneinfo.ZoneInfo("America/New_York")

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "mlb-edge-finder/1.0 (personal betting research)"})

DEBUG = os.environ.get("REDDIT_DEBUG") == "1"
DEBUG_DIR = Path("output/reddit_debug")


def _get_json(url: str) -> dict | list | None:
    try:
        resp = SESSION.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        time.sleep(POLITE_DELAY)
        data = resp.json()
        if DEBUG:
            _dump(url, resp.text)
        return data
    except Exception as exc:
        log.warning("reddit fetch failed for %s: %s", url, exc)
        return None


def _dump(url: str, text: str) -> None:
    try:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        import re
        name = re.sub(r"\W+", "_", url.split("//", 1)[-1])[:80] + ".json"
        (DEBUG_DIR / name).write_text(text, encoding="utf-8")
    except Exception as exc:
        log.warning("reddit debug dump failed: %s", exc)


def _is_baseball(title: str) -> bool:
    """Keep threads that look like MLB/baseball pick discussion (skip NBA/NFL/etc.)."""
    t = title.lower()
    if any(w in t for w in ("nba", "nfl", "nhl", "soccer", "ufc", "tennis")):
        return False
    return any(w in t for w in ("mlb", "baseball", "pick", "play", "parlay",
                                "daily", "moneyline", "what are"))


def _recent_threads(sub: str, now: dt.datetime) -> list[str]:
    """Permalinks of fresh, baseball-ish threads in r/<sub>, newest first."""
    data = _get_json(LISTING.format(sub=sub))
    if not isinstance(data, dict):
        return []
    out: list[str] = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        created = dt.datetime.fromtimestamp(d.get("created_utc", 0), tz=dt.timezone.utc)
        if (now - created).total_seconds() > THREAD_AGE_HOURS * 3600:
            continue
        if not _is_baseball(d.get("title", "")):
            continue
        if d.get("permalink"):
            out.append(d["permalink"])
        if len(out) >= MAX_THREADS:
            break
    return out


def _walk_comments(node, bodies: list[str]) -> None:
    """Collect every comment body in a Reddit comment listing (recursively)."""
    if isinstance(node, dict):
        children = node.get("data", {}).get("children", [])
        for c in children:
            d = c.get("data", {})
            body = d.get("body")
            if body:
                bodies.append(body)
            replies = d.get("replies")
            if isinstance(replies, dict):
                _walk_comments(replies, bodies)


def _thread_bodies(permalink: str) -> list[str]:
    data = _get_json(THREAD.format(permalink=permalink))
    bodies: list[str] = []
    if isinstance(data, list) and len(data) >= 2:
        # data[0] = the post listing, data[1] = the comment listing
        if data[0].get("data", {}).get("children"):
            sel = data[0]["data"]["children"][0].get("data", {}).get("selftext")
            if sel:
                bodies.append(sel)
        _walk_comments(data[1], bodies)
    return bodies


def reddit_majority(teams: list[tuple[str, str]], date: str) -> dict[str, int]:
    """Tally team moneyline mentions across recent betting-subreddit threads, using
    the SAME mention logic as the covers forum. {full_name: count}; zeros on failure."""
    counts = {name: 0 for name, _ in teams}
    matchers = {name: _team_patterns(name, abbr) for name, abbr in teams}
    now = dt.datetime.now(dt.timezone.utc)
    threads = 0
    for sub in SUBREDDITS:
        for permalink in _recent_threads(sub, now):
            threads += 1
            for body in _thread_bodies(permalink):
                for name in _post_moneyline_teams(body.lower(), matchers):
                    counts[name] += 1
    log.info("reddit: tallied %d thread(s) across %d sub(s)", threads, len(SUBREDDITS))
    return counts
