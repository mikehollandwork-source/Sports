"""
covers.com scraping: public betting consensus + forum-post sentiment.

This determines "what side the majority is on" two independent ways:
  1. consensus_percentages()  -> covers' published public-betting % per game
  2. forum_majority()         -> tally of team mentions in that day's forum posts

IMPORTANT (read before trusting output):
covers.com markup is not documented and changes over time. The CSS selectors and
URLs below are best-effort and WILL likely need adjustment after the first live
GitHub Actions run (this code cannot be tested from the build sandbox, where
covers.com is firewalled). Every parser fails *soft*: on any problem it returns
empty data and logs a warning, so the MLB-stats analysis still produces output.

covers.com has Terms of Service; this is intended for personal, low-volume
research. Requests are rate-limited and identify a custom User-Agent.
"""

from __future__ import annotations

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("covers")

# --- Endpoints (verify/adjust after first live run) ---------------------------
CONSENSUS_URL = "https://www.covers.com/sport/baseball/mlb/consensus"
FORUM_URL = "https://www.covers.com/forums/mlb-betting-forum"

TIMEOUT = 20
POLITE_DELAY = 1.0  # seconds between requests
SESSION = requests.Session()
SESSION.headers.update(
    {"User-Agent": "Mozilla/5.0 (compatible; mlb-edge-finder/1.0; personal research)"}
)


def _fetch(url: str) -> BeautifulSoup | None:
    try:
        resp = SESSION.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        time.sleep(POLITE_DELAY)
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as exc:  # network/HTTP/parse - degrade gracefully
        log.warning("covers fetch failed for %s: %s", url, exc)
        return None


def consensus_percentages() -> dict[str, dict[str, float]]:
    """
    Return {matchup_key: {team_name_or_abbr: bet_percentage}}.

    matchup_key is a normalized "away@home"-ish string; callers match it to a
    game by team name. Returns {} on any failure.
    """
    soup = _fetch(CONSENSUS_URL)
    if soup is None:
        return {}

    out: dict[str, dict[str, float]] = {}
    # Heuristic: each consensus row references two teams and two percentages.
    # Selectors are intentionally broad; tighten after inspecting real HTML.
    rows = soup.select("[class*=consensus] tr, table tr")
    for row in rows:
        teams = [t.get_text(strip=True) for t in row.select("[class*=team], td a")]
        pcts = [
            float(m.group(1))
            for m in re.finditer(r"(\d{1,3})\s*%", row.get_text(" "))
        ]
        teams = [t for t in teams if t]
        if len(teams) >= 2 and len(pcts) >= 2:
            key = f"{teams[0]}@{teams[1]}".lower()
            out[key] = {teams[0]: pcts[0], teams[1]: pcts[1]}
    if not out:
        log.warning("consensus parse produced 0 rows - selectors likely need updating")
    return out


def forum_majority(team_names: list[str], date: str) -> dict[str, int]:
    """
    Tally how often each team in `team_names` is mentioned across that day's
    MLB forum posts. Returns {team_name: mention_count}.

    This is a deliberately simple heuristic (mention = implicit lean). It does
    not understand sarcasm, fades, or parlays - see README caveats.
    """
    soup = _fetch(FORUM_URL)
    counts = {name: 0 for name in team_names}
    if soup is None:
        return counts

    posts = _todays_posts(soup, date)
    if not posts:
        log.warning("forum parse found 0 posts for %s - selectors/date likely need updating", date)

    # Build a matcher per team: full name + last word (e.g. "Yankees") + city.
    matchers = {name: _team_patterns(name) for name in team_names}
    for text in posts:
        low = text.lower()
        for name, pats in matchers.items():
            if any(p in low for p in pats):
                counts[name] += 1
    return counts


def _todays_posts(soup: BeautifulSoup, date: str) -> list[str]:
    """Extract post bodies dated `date` (YYYY-MM-DD). Best-effort."""
    posts: list[str] = []
    # Broad selector for post/thread rows; refine with real markup.
    for node in soup.select("[class*=post], [class*=thread], article"):
        stamp = node.find(attrs={"datetime": True})
        node_date = ""
        if stamp and stamp.get("datetime"):
            node_date = stamp["datetime"][:10]
        # If we can read a date and it doesn't match, skip; otherwise include.
        if node_date and node_date != date:
            continue
        body = node.get_text(" ", strip=True)
        if body:
            posts.append(body)
    return posts


def _team_patterns(name: str) -> list[str]:
    """Lowercased match strings for a team: full name, nickname, city."""
    name = name.strip()
    parts = name.lower().split()
    pats = {name.lower()}
    if parts:
        pats.add(parts[-1])          # nickname, e.g. "yankees"
        pats.add(" ".join(parts[:-1]))  # city, e.g. "new york"
    return [p for p in pats if p]
