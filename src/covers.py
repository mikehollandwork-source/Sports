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
        # Moneylines (away then home). American moneyline odds are always 3-4
        # signed digits (>= |100|); a run-line spread is +/-1.5 (one digit + a
        # decimal). Requiring 3-4 digits as a standalone token (no surrounding
        # digit/dot) means a spread can never be mistaken for the moneyline.
        odds = re.findall(r"(?<![\d.])[+-]\d{3,4}(?![\d.])", tr.get_text(" "))
        away_ml = odds[0] if len(odds) >= 2 else None
        home_ml = odds[1] if len(odds) >= 2 else None
        key = f"{teams[0]}@{teams[1]}".lower()
        out[key] = {
            "away": {"abbr": teams[0], "pct": away_pct, "moneyline": away_ml},
            "home": {"abbr": teams[1], "pct": home_pct, "moneyline": home_ml},
        }
    return out


def forum_majority(teams: list[tuple[str, str]], date: str) -> dict[str, int]:
    """
    Tally how often each team is mentioned across that day's MLB forum posts.
    `teams` is a list of (full_name, abbreviation); returns {full_name: count}.

    Forum posters lean on abbreviations ("BOS", "NYY", "LAD") as much as names,
    so each team matches on full name / nickname / city (as substrings) AND its
    abbreviation (as a whole word, so short codes don't hit inside other words).

    This is a deliberately simple heuristic (mention = implicit lean). It does
    not understand sarcasm, fades, or parlays - see README caveats.
    """
    soup, text, final_url = _fetch(FORUM_URL)
    counts = {name: 0 for name, _ in teams}
    if soup is None:
        return counts
    if DEBUG:
        _dump_forum_sample(soup)

    posts = _todays_thread_posts(soup, date)
    if not posts:
        _fingerprint(text, final_url, soup, "forum")

    matchers = {name: _team_patterns(name, abbr) for name, abbr in teams}
    for body in posts:
        for name in _post_moneyline_teams(body.lower(), matchers):
            counts[name] += 1
    return counts


FORUM_MAX_THREADS = 20  # most-recent threads to crawl for today's posts


def _todays_thread_posts(listing_soup: BeautifulSoup, date: str,
                         max_threads: int = FORUM_MAX_THREADS) -> list[str]:
    """Crawl the most-recent threads and return ONLY the post bodies whose own
    timestamp is `date`. Each post on a thread page is a `postBrick` with its own
    <time datetime> and a .raw-post-body, so this is strictly current-day - a
    thread started days ago contributes only its posts made today."""
    posts: list[str] = []
    for url in _thread_links(listing_soup)[:max_threads]:
        tsoup, _, _ = _fetch(url)
        if tsoup is None:
            continue
        for brick in tsoup.select(".covers-CoversForum-postBrick"):
            stamp = brick.find("time", attrs={"datetime": True})
            if not stamp or stamp.get("datetime", "")[:10] != date:
                continue
            body_el = brick.select_one(".raw-post-body")
            body = body_el.get_text(" ", strip=True) if body_el else ""
            if body:
                posts.append(body)
    return posts


# Run-line / spread language: a pick written next to one of these is a SPREAD
# pick (e.g. "NYY -1.5", "Sox run line", "take the Yanks to cover), NOT a
# moneyline pick - it should not feed the moneyline-based public tally.
SPREAD_RE = re.compile(r"[+-]\s?1\.5|1½|\brun[- ]?line\b|\brl\b|\bspread\b|\bats\b"
                       r"|\bcover(?:s|ed|ing)?\b", re.I)
# Explicit moneyline language overrides a nearby spread marker.
ML_RE = re.compile(r"\bml\b|\bmoney\s?line\b|\bm/?l\b|\bstraight[- ]?up\b|\bsu\b", re.I)


def _mention_spans(low_text: str, pats: dict) -> list[tuple[int, int]]:
    """Character spans where this team is named (substrings + boundaried abbr)."""
    spans: list[tuple[int, int]] = []
    for s in pats["subs"]:
        i = low_text.find(s)
        while i != -1:
            spans.append((i, i + len(s)))
            i = low_text.find(s, i + 1)
    for w in pats["words"]:
        spans.extend(m.span() for m in re.finditer(rf"\b{re.escape(w)}\b", low_text))
    return spans


def _post_moneyline_teams(low_text: str, matchers: dict) -> set[str]:
    """Teams leaned on as MONEYLINE picks in a post. Each team mention owns the
    text from it up to the next team mention, so a run-line/spread marker is
    attributed to the pick it follows (e.g. 'NYY ML, BOS -1.5' -> NYY only).
    A team is counted unless every one of its segments is a spread pick; an
    explicit 'ML' always counts."""
    marks: list[tuple[int, int, str]] = []
    for name, pats in matchers.items():
        for a, b in _mention_spans(low_text, pats):
            marks.append((a, b, name))
    marks.sort()

    out: set[str] = set()
    for i, (a, _b, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(low_text)
        scope = low_text[a:end]
        if ML_RE.search(scope) or not SPREAD_RE.search(scope):
            out.add(name)
    return out


def _abs_forum(href: str) -> str:
    if href.startswith("http"):
        return href
    return "https://www.covers.com" + href if href.startswith("/") else href


def _thread_links(soup: BeautifulSoup) -> list[str]:
    """Thread URLs from the forum listing (slug ending in a long post id), in
    page order (most-recently-active first). Pagination links are excluded."""
    seen: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"/forum/mlb-betting-27/.+-\d{6,}/?$", href):
            url = _abs_forum(href)
            if url not in seen:
                seen.append(url)
    return seen


def _dump_forum_sample(soup: BeautifulSoup) -> None:
    """In DEBUG, fetch the first thread so its per-post date/body markup can be
    inspected (the dump happens inside _fetch)."""
    links = _thread_links(soup)
    if links:
        _fetch(links[0])


def _dated_posts(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """(date, body) for every post node carrying a parseable datetime."""
    out: list[tuple[str, str]] = []
    for node in soup.select("[class*=post], [class*=thread], article"):
        stamp = node.find(attrs={"datetime": True})
        if not (stamp and stamp.get("datetime")):
            continue
        body = node.get_text(" ", strip=True)
        if body:
            out.append((stamp["datetime"][:10], body))
    return out


def forum_day_counts(teams: list[tuple[str, str]], dates: list[str],
                     max_pages: int = 25) -> dict[str, dict[str, int]]:
    """Page back through the forum and tally team mentions per day, for the
    backtest. Returns {date: {team_name: count}} for each date in `dates`.

    Posts are newest-first, so we walk pages until we've passed the oldest date
    we need (or hit max_pages / an empty page). Same name+abbr matching as the
    live forum tally."""
    want = set(dates)
    counts = {d: {name: 0 for name, _ in teams} for d in dates}
    if not want:
        return counts
    matchers = {name: _team_patterns(name, abbr) for name, abbr in teams}
    earliest = min(want)

    for page in range(1, max_pages + 1):
        url = FORUM_URL if page == 1 else f"{FORUM_URL}/{page}"
        soup, _, _ = _fetch(url)
        if soup is None:
            break
        dated = _dated_posts(soup)
        if not dated:
            break
        for d, body in dated:
            if d in counts:
                for name in _post_moneyline_teams(body.lower(), matchers):
                    counts[d][name] += 1
        if min(d for d, _ in dated) < earliest:  # paged past our window
            break
    return counts


def _team_patterns(name: str, abbr: str = "") -> dict:
    """Match patterns for a team. `subs` (full name, nickname, city) are matched
    as substrings; `words` (the abbreviation) are matched on word boundaries so a
    2-3 letter code can't trigger inside an unrelated word."""
    parts = name.strip().lower().split()
    subs = {name.strip().lower()}
    if parts:
        subs.add(parts[-1])             # nickname, e.g. "yankees"
        subs.add(" ".join(parts[:-1]))  # city, e.g. "new york"
    words = {abbr.lower()} if abbr else set()
    return {"subs": [s for s in subs if s], "words": [w for w in words if w]}
