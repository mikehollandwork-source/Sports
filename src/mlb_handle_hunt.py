"""
Hunt for a free MLB HANDLE (money %) source, properly this time.

WHAT WENT WRONG IN THE FIRST ATTEMPT
`handle_probe` reported oddstrader, covers-consensus and wagertalk as "fetch
failed / blocked" and I treated that as settled. Two mistakes:

  1. every request went out with the project's bot User-Agent
     ("mlb-edge-finder/1.0; personal research"). Cloudflare-fronted sites
     refuse that on sight, so "blocked" may describe how we asked rather than
     whether the data is there.
  2. the probe collapsed 403, 404, timeout and DNS failure into one label, so
     a site that refuses a bot was indistinguishable from a dead URL.

Both are fixed here: a browser User-Agent with the Accept headers a browser
sends, and the actual status code reported per candidate.

A LEAD FROM THE REPO'S OWN HISTORY
`handle_hunt` (written for the WNBA) notes in passing that covers MATCHUP
pages "for MLB carry a bets/money split per game". covers is already scraped
successfully for tickets at ~82% coverage, so if its matchup pages carry
handle too, the third source is a domain we already talk to - no new decay
surface, no new vendor.

CANDIDATES
  covers matchups / consensus   already-working domain, may carry money
  Action Network scoreboard     public JSON used by its own front end
  OddsShark, BettingPros        free consensus APIs
  oddstrader, wagertalk         retried with a real User-Agent

WHAT COUNTS AS A HIT
Not "the page loaded" and not "there are percentages on it" - CSS is full of
percentages, which is exactly what fooled me on VSIN. A hit is a PAIR of
percentages summing to 95-105 found near an MLB team name, or JSON keys that
name bets/money share. Anything less gets reported as a miss.

Reports only. Adds no source, changes no rule, writes no board.
Writes output/mlb_handle_hunt.md.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

import requests

log = logging.getLogger("mlb_handle_hunt")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TIMEOUT = 20
DELAY = 1.0

BROWSER = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/129.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
}

TEAMS = ["Yankees", "Mets", "Dodgers", "Guardians", "Braves", "Astros",
         "Mariners", "Cubs", "Cardinals", "Brewers", "Phillies", "Padres",
         "Rangers", "Tigers", "Royals", "Nationals", "Orioles", "Angels",
         "Red Sox", "Blue Jays", "White Sox", "Giants", "Twins", "Pirates",
         "Reds", "Marlins", "Rockies", "Diamondbacks", "Athletics", "Rays"]

# JSON keys that would name a split share
KEYS = re.compile(r'"([a-z_]*(?:money|handle|bet|ticket|wager)[a-z_]*)"\s*:',
                  re.I)
PCT_PAIR = re.compile(r"(\d{1,3})\s*%[^%]{0,80}?(\d{1,3})\s*%")

CANDIDATES = [
    ("covers matchups", "https://www.covers.com/sports/mlb/matchups"),
    ("covers consensus",
     "https://contests.covers.com/consensus/topconsensus/mlb/overall"),
    ("action network scoreboard",
     "https://api.actionnetwork.com/web/v1/scoreboard/mlb"),
    ("action network v2 public",
     "https://api.actionnetwork.com/web/v2/scoreboard/publicbetting/mlb"),
    ("oddsshark consensus",
     "https://www.oddsshark.com/mlb/consensus-picks"),
    ("bettingpros splits",
     "https://api.bettingpros.com/v3/consensus?sport=MLB&market_id=52"),
    ("oddstrader public betting",
     "https://www.oddstrader.com/mlb/public-betting/"),
    ("wagertalk splits", "https://www.wagertalk.com/betting-splits"),
    ("sbr consensus",
     "https://www.sportsbookreview.com/betting-odds/mlb-baseball/consensus/"),
]


def _get(url: str) -> tuple[int | str, str, str]:
    """(status, content-type, body). Status is the code, or the error name."""
    try:
        r = requests.get(url, headers=BROWSER, timeout=TIMEOUT)
        return r.status_code, r.headers.get("content-type", "").split(";")[0], r.text
    except requests.exceptions.Timeout:
        return "timeout", "", ""
    except requests.exceptions.ConnectionError as exc:
        return f"conn ({type(exc).__name__})", "", ""
    except Exception as exc:
        return f"error ({type(exc).__name__})", "", ""


def _assess(body: str) -> dict:
    """Is there a real SPLIT here, or just percentages? CSS has percentages."""
    teams = sorted({t for t in TEAMS if t in body})
    keys = sorted(set(k.lower() for k in KEYS.findall(body)))
    pairs = [(int(a), int(b)) for a, b in PCT_PAIR.findall(body)]
    good = [(a, b) for a, b in pairs if 95 <= a + b <= 105 and a and b]
    return {"teams": len(teams), "team_sample": teams[:4],
            "keys": keys[:10], "pairs": len(pairs), "split_pairs": len(good),
            "sample_split": good[:3]}


def build() -> str:
    md = ["# Hunting a free MLB handle (money %) source", "",
          "_Retry with a browser User-Agent and real status codes. The first "
          "attempt sent the project's bot UA and reported every failure as "
          "\"blocked\", which confused how we ask with what is there._", "",
          "**A hit is not \"the page loaded\".** CSS is full of percentages - "
          "that is what made me misread VSIN. A hit is a PAIR of percentages "
          "summing to 95-105, or JSON keys naming a bets/money share.", "",
          "| candidate | status | type | bytes | teams | split pairs | "
          "split-ish keys |", "|---|---|---|---|---|---|---|"]

    results = []
    for name, url in CANDIDATES:
        status, ct, body = _get(url)
        time.sleep(DELAY)
        if not isinstance(status, int) or status >= 400 or not body:
            md.append(f"| {name} | **{status}** | {ct or '—'} | — | — | — | — |")
            continue
        a = _assess(body)
        results.append((name, url, a, body))
        md.append(f"| {name} | {status} | {ct or '?'} | {len(body):,} | "
                  f"{a['teams']} | **{a['split_pairs']}** | "
                  f"{', '.join(a['keys'][:4]) or '—'} |")
    md.append("")

    hits = [r for r in results if r[2]["split_pairs"] >= 3 and r[2]["teams"] >= 4]
    if not hits:
        md += ["## No candidate carries a real split", "",
               "Pages that loaded either name no MLB teams or show no pair of "
               "percentages summing to ~100. Percent counts alone are not "
               "evidence: CSS supplies plenty.", ""]
        near = [r for r in results if r[2]["teams"] >= 4]
        if near:
            md += ["_Closest, in case a different path on the same domain "
                   "carries it:_", ""]
            for name, url, a, _ in near:
                md.append(f"- **{name}** — {a['teams']} teams "
                          f"({', '.join(a['team_sample'])}), "
                          f"{a['pairs']} percent pairs, "
                          f"{a['split_pairs']} summing to ~100")
            md.append("")
        return "\n".join(md)

    md += ["## Candidates carrying a real split", ""]
    for name, url, a, body in hits:
        md += [f"### {name}", "", f"`{url}`", "",
               f"- MLB teams named: **{a['teams']}** "
               f"({', '.join(a['team_sample'])})",
               f"- percentage pairs summing to ~100: **{a['split_pairs']}** "
               f"(e.g. {a['sample_split']})",
               f"- split-ish JSON keys: {', '.join(a['keys']) or 'none'}", ""]
        if body.lstrip().startswith(("{", "[")):
            try:
                doc = json.loads(body)
                md += ["_Top-level JSON keys:_", "", "```",
                       ", ".join(list(doc)[:20]) if isinstance(doc, dict)
                       else f"array of {len(doc)}", "```", ""]
            except Exception:
                pass
        md += ["_First 400 characters:_", "", "```",
               body[:400].replace("`", "'"), "```", ""]
    md += ["_A parser gets written against whichever of these is JSON on a "
           "stable path, and only after a second run on a different day "
           "confirms it is not a one-off. Two sources decayed this season "
           "already; a third is worth having only if it is sturdier than what "
           "it joins._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "mlb_handle_hunt.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
