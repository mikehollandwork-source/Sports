"""
covers.com scraping: public betting consensus + forum-post sentiment.

This determines "what side the majority is on" two independent ways:
  1. consensus_percentages()  -> covers' published public-betting % per game
  2. forum_majority()         -> tally of team mentions in that day's forum posts

IMPORTANT (read before trusting output):
covers.com markup is not documented and changes over time. covers.com is a
Next.js site, so the live consensus numbers are rendered client-side and live in
the embedded __NEXT_DATA__ JSON, not in static <tr>s - the parser tries that JSON
first and falls back to a table heuristic. The CSS selectors and URLs are still
best-effort and may need adjustment after a live GitHub Actions run (this code
cannot be tested from the build sandbox, where covers.com is firewalled). Every
parser fails *soft*: on any problem it returns empty data and logs a structural
fingerprint, so the MLB-stats analysis still produces output. Set COVERS_DEBUG=1
for one run to dump the raw HTML covers serves into output/covers_debug/ - that's
what's needed to pin the selectors exactly.

covers.com has Terms of Service; this is intended for personal, low-volume
research. Requests are rate-limited and identify a custom User-Agent.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("covers")

# --- Endpoints ----------------------------------------------------------------
# The old www.covers.com/sport/... paths 404 now. Public-betting consensus lives
# on the contests subdomain; the MLB forum moved to /forum/mlb-betting-27.
CONSENSUS_URL = "https://contests.covers.com/consensus/topconsensus/mlb/overall"
FORUM_URL = "https://www.covers.com/forum/mlb-betting-27"

TIMEOUT = 20
POLITE_DELAY = 1.0  # seconds between requests
SESSION = requests.Session()
SESSION.headers.update(
    {"User-Agent": "Mozilla/5.0 (compatible; mlb-edge-finder/1.0; personal research)"}
)

# Set COVERS_DEBUG=1 in the Actions env for one run to dump the raw HTML covers
# actually serves into output/covers_debug/ - that markup is what's needed to
# pin the selectors exactly (we can't see it from the firewalled build sandbox).
DEBUG = os.environ.get("COVERS_DEBUG") == "1"
DEBUG_DIR = Path("output/covers_debug")


def _fetch(url: str) -> tuple[BeautifulSoup | None, str, str]:
    """Return (soup, raw_text, final_url). soup is None on failure."""
    try:
        resp = SESSION.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        time.sleep(POLITE_DELAY)
        if DEBUG:
            _dump(url, resp.text)
        return BeautifulSoup(resp.text, "html.parser"), resp.text, str(resp.url)
    except Exception as exc:  # network/HTTP/parse - degrade gracefully
        log.warning("covers fetch failed for %s: %s", url, exc)
        return None, "", url


def _dump(url: str, text: str) -> None:
    try:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        name = re.sub(r"\W+", "_", url.split("//", 1)[-1])[:80] + ".html"
        (DEBUG_DIR / name).write_text(text, encoding="utf-8")
        log.info("covers debug HTML written to %s", DEBUG_DIR / name)
    except Exception as exc:
        log.warning("covers debug dump failed: %s", exc)


def _next_data(soup: BeautifulSoup) -> dict | None:
    """The Next.js __NEXT_DATA__ JSON blob, where client-rendered sites stash
    their real data. Returns the parsed dict, or None if absent/unparseable."""
    tag = soup.find("script", id="__NEXT_DATA__")
    if tag and tag.string:
        try:
            return json.loads(tag.string)
        except Exception:
            pass
    return None


def _fingerprint(text: str, final_url: str, soup: BeautifulSoup, what: str) -> None:
    """When a parse yields nothing, log enough structure to fix selectors next
    time without another blind round-trip."""
    title = soup.title.get_text(strip=True) if soup.title else ""
    classes = sorted({c for el in soup.find_all(class_=True)
                      for c in el.get("class", [])})[:25]
    log.warning(
        "%s parse empty | final_url=%s | title=%r | bytes=%d | __NEXT_DATA__=%s | "
        "tables=%d | sample_classes=%s",
        what, final_url, title, len(text), _next_data(soup) is not None,
        len(soup.find_all("table")), classes,
    )


def consensus() -> dict[str, dict]:
    """
    Parse the contests.covers.com MLB consensus table.

    Returns {"away@home": {"away": side, "home": side}} where each `side` is
    {abbr, pct, moneyline}. Keys/abbrevs are matched to games by
    analysis._name_hit on team.abbreviation. Returns {} on any failure.

    moneyline is read off the consensus row (the signed odds next to the bet %).
    covers' MLB consensus is moneyline-only - it carries no run-line consensus.
    """
    soup, text, final_url = _fetch(CONSENSUS_URL)
    if soup is None:
        return {}
    out = _parse_consensus_rows(soup)
    if not out:
        _fingerprint(text, final_url, soup, "consensus")
    return out


def _pct(text: str) -> float | None:
    m = re.search(r"(\d{1,3})\s*%", text)
    return float(m.group(1)) if m else None


def _parse_consensus_rows(soup: BeautifulSoup) -> dict[str, dict]:
    """Each matchup row holds two team anchors (href /consensus/pickleadersbyteam/,
    text = abbreviation, e.g. 'Bos'), two bet-% spans
    (covers-CoversConsensus-consensusTable--high/--low, in away-then-home order),
    and the two moneylines as signed odds. --high/--low only styles the larger
    side, so percentages and odds are aligned to teams by position, not magnitude."""
    out: dict[str, dict] = {}
    for tr in soup.select("tr"):
        teams = [a.get_text(strip=True) for a in tr.find_all("a")
                 if "pickleadersbyteam" in a.get("href", "")]
        spans = tr.select(".covers-CoversConsensus-consensusTable--high,"
                          " .covers-CoversConsensus-consensusTable--low")
        if len(teams) < 2 or len(spans) < 2:
            continue
        away_pct, home_pct = _pct(spans[0].get_text()), _pct(spans[1].get_text())
        if away_pct is None or home_pct is None:
            continue
        odds = re.findall(r"[+-]\d{2,4}", tr.get_text(" "))  # moneylines, away then home
        away_ml = odds[0] if len(odds) >= 2 else None
        home_ml = odds[1] if len(odds) >= 2 else None
        key = f"{teams[0]}@{teams[1]}".lower()
        out[key] = {
            "away": {"abbr": teams[0], "pct": away_pct, "moneyline": away_ml},
            "home": {"abbr": teams[1], "pct": home_pct, "moneyline": home_ml},
        }
    return out


def forum_majority(team_names: list[str], date: str) -> dict[str, int]:
    """
    Tally how often each team in `team_names` is mentioned across that day's
    MLB forum posts. Returns {team_name: mention_count}.

    This is a deliberately simple heuristic (mention = implicit lean). It does
    not understand sarcasm, fades, or parlays - see README caveats.
    """
    soup, text, final_url = _fetch(FORUM_URL)
    counts = {name: 0 for name in team_names}
    if soup is None:
        return counts

    posts = _todays_posts(soup, date)
    if not posts:
        _fingerprint(text, final_url, soup, "forum")

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
