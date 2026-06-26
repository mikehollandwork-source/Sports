"""
Extra public-betting-% sources, to cross-check covers' consensus.

The whole point of #4: a single book's "public %" can be misleading (or massaged),
so we corroborate it against independent sources. covers.consensus() is one source;
this module adds two more free ones:

  scoresandodds_consensus() -> Scores & Odds public bet %
  vegasinsider_consensus()  -> VegasInsider consensus %

Each returns a list of rows {away_abbr, home_abbr, away_pct, home_pct} (the two
teams + each side's public %), matched to games later by abbreviation. Like every
covers parser these are BEST-EFFORT and UNVERIFIED — the selectors can only be
confirmed on a live GitHub Actions run (both sites are firewalled in the build
sandbox). Every parser fails *soft*: on any problem it logs a fingerprint and
returns [], so the rest of the pipeline (covers + forum + line) still produces a
read. Set PUBLIC_DEBUG=1 for one run to dump the raw HTML into output/public_debug/.
"""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("public_sources")

SCORESODDS_URL = "https://www.scoresandodds.com/mlb"
VEGASINSIDER_URL = "https://www.vegasinsider.com/mlb/consensus/"

TIMEOUT = 20
POLITE_DELAY = 1.0
SESSION = requests.Session()
SESSION.headers.update(
    {"User-Agent": "Mozilla/5.0 (compatible; mlb-edge-finder/1.0; personal research)"}
)

DEBUG = os.environ.get("PUBLIC_DEBUG") == "1"
DEBUG_DIR = Path("output/public_debug")

# MLB abbreviations these sites use, normalized to our canonical set elsewhere.
_VALID_ABBRS = {
    "ARI", "AZ", "ATL", "BAL", "BOS", "CHC", "CWS", "CHW", "CIN", "CLE", "COL",
    "DET", "HOU", "KC", "KCR", "LAA", "LAD", "MIA", "MIL", "MIN", "NYM", "NYY",
    "OAK", "ATH", "PHI", "PIT", "SD", "SDP", "SEA", "SF", "SFG", "STL", "TB",
    "TBR", "TEX", "TOR", "WSH", "WAS", "WSN",
}


def _fetch(url: str) -> tuple[BeautifulSoup | None, str, str]:
    try:
        resp = SESSION.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        time.sleep(POLITE_DELAY)
        if DEBUG:
            _dump(url, resp.text)
        return BeautifulSoup(resp.text, "html.parser"), resp.text, str(resp.url)
    except Exception as exc:
        log.warning("public source fetch failed for %s: %s", url, exc)
        return None, "", url


def _dump(url: str, text: str) -> None:
    try:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        name = re.sub(r"\W+", "_", url.split("//", 1)[-1])[:80] + ".html"
        (DEBUG_DIR / name).write_text(text, encoding="utf-8")
        log.info("public-source debug HTML written to %s", DEBUG_DIR / name)
    except Exception as exc:
        log.warning("public-source debug dump failed: %s", exc)


def _fingerprint(text: str, final_url: str, soup: BeautifulSoup, what: str) -> None:
    title = soup.title.get_text(strip=True) if soup.title else ""
    classes = sorted({c for el in soup.find_all(class_=True)
                      for c in el.get("class", [])})[:25]
    log.warning("%s parse empty | final_url=%s | title=%r | bytes=%d | tables=%d | "
                "sample_classes=%s", what, final_url, title, len(text),
                len(soup.find_all("table")), classes)


def _rows_from_blocks(blocks, source: str) -> list[dict]:
    """Generic extractor: from each candidate row/block, pull exactly two known MLB
    abbreviations and two percentages (away listed first, the site convention) and
    pair them. Orientation is reconciled to the game later by abbreviation, so a
    site that lists home-first still matches; we just need both teams + both %s."""
    out: list[dict] = []
    seen: set = set()
    for b in blocks:
        txt = b.get_text(" ", strip=True)
        abbrs = [a for a in re.findall(r"\b([A-Z]{2,3})\b", txt) if a in _VALID_ABBRS]
        pcts = [float(p) for p in re.findall(r"(\d{1,3})\s*%", txt)]
        # need exactly two distinct teams and at least two percentages
        teams: list[str] = []
        for a in abbrs:
            if a not in teams:
                teams.append(a)
        if len(teams) < 2 or len(pcts) < 2:
            continue
        key = (teams[0], teams[1])
        if key in seen:
            continue
        seen.add(key)
        out.append({"away_abbr": teams[0], "home_abbr": teams[1],
                    "away_pct": pcts[0], "home_pct": pcts[1], "source": source})
    return out


def scoresandodds_consensus() -> list[dict]:
    """Scores & Odds MLB public bet %. UNVERIFIED selectors — fail soft to []."""
    soup, text, final_url = _fetch(SCORESODDS_URL)
    if soup is None:
        return []
    blocks = soup.select("[class*=event], [class*=matchup], tr") or soup.find_all("tr")
    out = _rows_from_blocks(blocks, "scoresodds")
    if not out:
        _fingerprint(text, final_url, soup, "scoresodds")
    return out


def vegasinsider_consensus() -> list[dict]:
    """VegasInsider MLB consensus %. UNVERIFIED selectors — fail soft to []."""
    soup, text, final_url = _fetch(VEGASINSIDER_URL)
    if soup is None:
        return []
    blocks = soup.select("[class*=consensus] tr, [class*=matchup], tr") or soup.find_all("tr")
    out = _rows_from_blocks(blocks, "vegasinsider")
    if not out:
        _fingerprint(text, final_url, soup, "vegasinsider")
    return out


def all_sources() -> dict[str, list[dict]]:
    """Every extra public source, each fetched independently and failing soft to []
    so one dead site can't sink the others. {source_name: [rows]}."""
    sources: dict[str, list[dict]] = {}
    for name, fn in (("scoresodds", scoresandodds_consensus),
                     ("vegasinsider", vegasinsider_consensus)):
        try:
            rows = fn()
        except Exception as exc:
            log.warning("%s consensus failed: %s", name, exc)
            rows = []
        sources[name] = rows
        log.info("%s: %d game row(s)", name, len(rows))
    return sources
