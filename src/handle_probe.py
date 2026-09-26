"""
Find a third HANDLE (money %) source. Probe only - decides nothing, changes
nothing, writes no board.

THE PROBLEM, MEASURED
Gate 1 needs the dollars to agree with the ticket majority. There are exactly
two handle sources today (scoresodds_money, vsin_money) and `analysis` requires
them to be UNANIMOUS:

    money_side = money_sides[0] if len(set(money_sides)) == 1 else None

With two sources, one disagreement is fatal. Over 1,201 board games:

    with public       824   68.6%
    sources split     184   15.3%   <- the two handle sources disagreed
    against public    132   11.0%
    unknown            61    5.1%   <- no handle data at all

So 20.4% of games never reach the rest of the rule for want of a usable handle
read, and it is getting worse, not better: 16% in June, 18% July, 19% August,
25% September. That trend is scraper decay, not the market changing.

A THIRD SOURCE FIXES BOTH HALVES
It adds coverage on the 5.1% with nothing, and - if the unanimity requirement
becomes a majority vote - it breaks the tie on the 15.3%. The vote change is a
CHANGE TO GATE 1 and must be backtested before it ships; this file does not
touch it. This file only answers "is there a third source that works".

WHY A PROBE AND NOT A PARSER
The sandbox firewalls these hosts, so nothing here can be tested locally, and
writing selectors blind is how the covers parsers ended up "best-effort and
unverified". This fetches candidates on Actions and reports what is actually
there - status, size, whether the existing VSIN parser already handles it, and
how many percent-tokens and team-like tokens the page carries - so the real
parser is written against observed shape.

The cheapest candidate is first: VSIN publishes splits PER SPORTSBOOK, and
`vsin_splits()` already takes a url override. If a second book's view parses
with the parser we already have, the third source costs no new selectors and
carries no new decay risk.

Writes output/handle_probe.md.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from . import public_sources as PS

log = logging.getLogger("handle_probe")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# VSIN book views - same parser, different sportsbook. Param spelling is a
# guess; the probe reports which (if any) return a splits page.
VSIN_VIEWS = [
    ("vsin:dk (current)", PS.VSIN_URL),
    ("vsin:circa", PS.VSIN_URL + "?view=circa"),
    ("vsin:southpoint", PS.VSIN_URL + "?view=southpoint"),
    ("vsin:betmgm", PS.VSIN_URL + "?view=betmgm"),
    ("vsin:fanduel", PS.VSIN_URL + "?view=fanduel"),
    ("vsin:caesars", PS.VSIN_URL + "?view=caesars"),
]

# other free pages that publish a money/handle column
OTHER = [
    ("oddstrader", "https://www.oddstrader.com/mlb/public-betting/"),
    ("sbr-consensus",
     "https://www.sportsbookreview.com/betting-odds/mlb-baseball/consensus/"),
    ("covers-consensus",
     "https://www.covers.com/sport/baseball/mlb/consensus"),
    ("wagertalk", "https://www.wagertalk.com/betting-splits"),
]

PCT = re.compile(r"\b\d{1,3}\s?%")


def _shape(text: str, soup) -> dict:
    """Cheap description of a page, enough to tell a splits table from a 404."""
    pcts = PCT.findall(text or "")
    return {
        "bytes": len(text or ""),
        "pct_tokens": len(pcts),
        "tables": len((soup.find_all("table") if soup else []) or []),
        "has_handle_word": bool(re.search(r"handle|% of money|money%",
                                          (text or ""), re.I)),
        "has_bets_word": bool(re.search(r"% of bets|bets%|tickets",
                                        (text or ""), re.I)),
    }


def build() -> str:
    md = ["# Probe: is there a third handle (money %) source?", "",
          "_Probe only. Fetches candidates and reports what is there; parses "
          "nothing into the board and changes no rule._", "",
          "## Why", "",
          "Gate 1 needs the dollars to agree with the tickets. There are two "
          "handle sources and they must agree UNANIMOUSLY, so one disagreement "
          "is fatal. Over 1,201 board games that costs **20.4%** of the slate "
          "— 15.3% \"sources split\" plus 5.1% with no handle at all — and the "
          "rate is rising: 16% June, 18% July, 19% August, **25% September**.", "",
          "## VSIN, by sportsbook (same parser we already use)", "",
          "| candidate | status | bytes | rows parsed | tables | % tokens |",
          "|---|---|---|---|---|---|"]

    for name, url in VSIN_VIEWS:
        soup, text, final = PS._fetch(url)
        if soup is None:
            md.append(f"| {name} | **fetch failed** | — | — | — | — |")
            continue
        try:
            rows = PS._parse_vsin(soup)
        except Exception as exc:
            log.warning("%s parse raised: %s", name, exc)
            rows = []
        sh = _shape(text, soup)
        flag = "**" + str(len(rows)) + "**" if rows else "0"
        md.append(f"| {name} | ok | {sh['bytes']:,} | {flag} | "
                  f"{sh['tables']} | {sh['pct_tokens']} |")
        if rows:
            r = rows[0]
            md.append(f"| ↳ sample | `{r.get('away_abbr')}` money "
                      f"{r.get('away_money')} / `{r.get('home_abbr')}` money "
                      f"{r.get('home_money')} | | | | |")
    md += ["", "_A view that parses rows with the EXISTING parser is the "
           "cheapest third source available: no new selectors, no new decay "
           "surface. Note the redirect check — several book views may serve "
           "the same default page, which would look like a new source while "
           "being the same numbers._", ""]

    md += ["## Other free pages carrying a money column", "",
           "| candidate | status | bytes | tables | % tokens | says handle | "
           "says bets |", "|---|---|---|---|---|---|---|"]
    for name, url in OTHER:
        soup, text, final = PS._fetch(url)
        if soup is None:
            md.append(f"| {name} | **fetch failed / blocked** | — | — | — | — | — |")
            continue
        sh = _shape(text, soup)
        md.append(f"| {name} | ok | {sh['bytes']:,} | {sh['tables']} | "
                  f"{sh['pct_tokens']} | {'yes' if sh['has_handle_word'] else 'no'} "
                  f"| {'yes' if sh['has_bets_word'] else 'no'} |")
        if final and final.rstrip("/") != url.rstrip("/"):
            md.append(f"| ↳ redirected to | `{final}` | | | | | |")
    md += ["", "_A page with a handle word, a table and plenty of percent "
           "tokens is worth writing a parser for. One that fetches but shows "
           "no percentages is almost certainly rendered client-side and not "
           "scrapeable this way._", "",
           "## What this does NOT do", "",
           "- it does not add a source to the board",
           "- it does not change the unanimity rule in `analysis` — turning "
           "that into a majority vote would change which games pass gate 1, "
           "which is a rule change and needs a backtest, not a probe", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "handle_probe.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
