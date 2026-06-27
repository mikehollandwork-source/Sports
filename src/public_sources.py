"""
Extra public-betting-% sources, to cross-check covers' consensus.

The whole point of #4: a single book's "public %" can be misleading (or massaged),
so we corroborate it against independent sources. covers.consensus() is one source;
this module adds Scores & Odds, which publishes TWO independent moneyline splits per
game on its consensus page:

  % of Bets  -> share of tickets (the public)
  % of Money -> share of dollars (sharper - where the money actually is)

The bets-vs-money divergence is itself the classic "the public % doesn't match the
money" tell, so we expose each as its own source ("scoresodds_bets",
"scoresodds_money"). (VegasInsider's free consensus page is HANDICAPPER picks, not
public money, so it isn't a usable public-% source and is intentionally not scraped.)

scoresandodds_consensus() returns rows {away_abbr, home_abbr, away_bets, home_bets,
away_money, home_money}, matched to games later by abbreviation. Selectors are
BEST-EFFORT (pinned from a captured Actions-egress page) and fail *soft*: on any
problem it logs a fingerprint and returns [], so the rest of the pipeline (covers +
forum + line) still produces a read. Set PUBLIC_DEBUG=1 for one run to dump the raw
HTML into output/public_debug/.
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

SCORESODDS_URL = "https://www.scoresandodds.com/mlb/consensus-picks"

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


def _parse_scoresodds(soup: BeautifulSoup) -> list[dict]:
    """Each game has three `li.consensus` blocks (Moneyline, Runline, Total). We want
    the Moneyline one: '<AWY> % of Bets <HOM> b_away% b_home% m_away% m_home%'. We
    skip Runline (labels carry '(-1.5)') and Total (labels are Over/Under), keeping
    only blocks whose two labels are bare team abbreviations."""
    out: list[dict] = []
    seen: set = set()
    for li in soup.select("li.consensus"):
        toks = [t.strip() for t in li.stripped_strings]
        if "% of Bets" not in toks:
            continue
        bi = toks.index("% of Bets")
        if bi == 0 or bi + 1 >= len(toks):
            continue
        away, home = toks[bi - 1].upper(), toks[bi + 1].upper()
        if away not in _VALID_ABBRS or home not in _VALID_ABBRS:
            continue                       # runline has '(-1.5)', total has Over/Under
        pcts = [int(p[:-1]) for p in toks[bi + 2:] if re.fullmatch(r"\d{1,3}%", p)]
        if len(pcts) < 4:                  # need bets(away,home) + money(away,home)
            continue
        key = (away, home)
        if key in seen:
            continue
        seen.add(key)
        out.append({"away_abbr": away, "home_abbr": home,
                    "away_bets": pcts[0], "home_bets": pcts[1],
                    "away_money": pcts[2], "home_money": pcts[3]})
    return out


def scoresandodds_consensus() -> list[dict]:
    """Scores & Odds MLB moneyline consensus: % of Bets + % of Money per game.
    Fail soft to []."""
    soup, text, final_url = _fetch(SCORESODDS_URL)
    if soup is None:
        return []
    out = _parse_scoresodds(soup)
    if not out:
        _fingerprint(text, final_url, soup, "scoresodds")
    return out


def all_sources() -> dict[str, list[dict]]:
    """Extra public sources for the cross-check. Scores & Odds yields two independent
    moneyline splits per game (tickets vs dollars), exposed as two sources. One fetch,
    failing soft to {} so a dead site can't sink the pipeline. {source_name: [rows]}
    where each row is {away_abbr, home_abbr, away_pct, home_pct}."""
    try:
        rows = scoresandodds_consensus()
    except Exception as exc:
        log.warning("scoresodds consensus failed: %s", exc)
        rows = []
    bets = [{"away_abbr": r["away_abbr"], "home_abbr": r["home_abbr"],
             "away_pct": r["away_bets"], "home_pct": r["home_bets"]} for r in rows]
    money = [{"away_abbr": r["away_abbr"], "home_abbr": r["home_abbr"],
              "away_pct": r["away_money"], "home_pct": r["home_money"]} for r in rows]
    log.info("scoresodds: %d game row(s) (bets + money)", len(rows))
    return {"scoresodds_bets": bets, "scoresodds_money": money}
