"""
What does the VSIN splits page actually call to fill its table?

WHY THIS EXISTS
The handle (money %) gate loses 20% of the slate and rising - 25% in
September. Two earlier probes narrowed the cause:

  * all six VSIN per-sportsbook views return byte-identical pages, so the
    ?view= parameter does nothing and there is no third source there
  * the page we fetch carries 746 text tokens, almost all navigation, and
    exactly one server-rendered game; 60 script tags mention neither handle,
    bets, nor any team name

I initially read the 201 percent-tokens in the raw HTML as "the data is there,
our parser cannot reach it". That was wrong - those are almost certainly CSS
widths. The page genuinely does not ship the splits. A browser fills the table
from somewhere else, and this finds out where.

WHAT IT DOES
Loads the page in headless Chromium, records every response, and scores each
one for MLB team names and percent values. A JSON endpoint that scores highly
is a free, stable replacement for scraping rendered HTML - no selectors, no
decay surface, and it would restore VSIN from one game a slate to all of them.

If nothing scores, that is the answer too: the free routes are exhausted and a
paid splits feed is the honest remaining option.

Reports only. Adds no source, changes no rule, writes no board.
Writes output/vsin_net_probe.md.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

log = logging.getLogger("vsin_net_probe")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
URL = "https://data.vsin.com/mlb/betting-splits/"
WAIT_MS = 25_000
MAX_BODY = 2_000_000          # do not hold a huge asset in memory

TEAMS = ["Yankees", "Mets", "Dodgers", "Guardians", "Braves", "Astros",
         "Mariners", "Cubs", "Cardinals", "Brewers", "Phillies", "Padres",
         "Rangers", "Tigers", "Royals", "Nationals", "Orioles", "Angels"]
PCT = re.compile(r"\b(?:100|[1-9]?\d)(?:\.\d+)?\s*%")
NUMPCT = re.compile(r'"(?:handle|bets|money|tickets)[A-Za-z_]*"\s*:\s*"?\d')


def _score(body: str) -> tuple[int, int, int]:
    teams = sum(1 for t in TEAMS if t in body)
    pcts = len(PCT.findall(body))
    keyed = len(NUMPCT.findall(body))
    return teams, pcts, keyed


def build() -> str:
    md = ["# What does the VSIN splits page call?", "",
          "_Headless capture of every network response the page makes, scored "
          "for team names and percent values. Reports only._", "",
          f"- page: `{URL}`", ""]
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return "\n".join(md + [f"**Playwright unavailable: {exc}**", ""])

    seen: list[dict] = []
    rendered_rows = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()

            def on_response(resp):
                try:
                    ct = (resp.headers or {}).get("content-type", "")
                    if not any(k in ct for k in ("json", "text", "javascript")):
                        return
                    body = resp.text()
                except Exception:
                    return
                if not body or len(body) > MAX_BODY:
                    return
                teams, pcts, keyed = _score(body)
                if teams >= 2 or keyed:
                    seen.append({"url": resp.url, "status": resp.status,
                                 "ct": ct.split(";")[0], "bytes": len(body),
                                 "teams": teams, "pcts": pcts, "keyed": keyed,
                                 "head": body[:400]})

            page.on("response", on_response)
            page.goto(URL, wait_until="networkidle", timeout=WAIT_MS)
            page.wait_for_timeout(4000)
            # did the table actually render once JS ran?
            try:
                rendered_rows = page.locator("table tr").count()
            except Exception:
                rendered_rows = -1
            browser.close()
    except Exception as exc:
        return "\n".join(md + [f"**Capture failed: {exc}**", ""])

    md += [f"- rows in the DOM after JavaScript ran: **{rendered_rows}**",
           f"- responses carrying team names or split keys: **{len(seen)}**", ""]
    if rendered_rows > 5:
        md += ["_The table DOES render once JavaScript runs, so the data is "
               "reachable - it simply is not in the HTML we fetch today._", ""]

    if not seen:
        md += ["## Nothing scored", "",
               "No response carried MLB team names or handle/bets keys. The "
               "free routes are exhausted: VSIN per-book views are identical, "
               "the page ships no data, and no endpoint exposes it plainly. "
               "The honest remaining option is a paid splits feed.", ""]
        return "\n".join(md)

    seen.sort(key=lambda r: (-r["keyed"], -r["teams"], -r["pcts"]))
    md += ["## Candidate endpoints", "",
           "| url | status | type | bytes | teams | % | split keys |",
           "|---|---|---|---|---|---|---|"]
    for r in seen[:12]:
        u = r["url"]
        if len(u) > 90:
            u = u[:87] + "…"
        md.append(f"| `{u}` | {r['status']} | {r['ct']} | {r['bytes']:,} | "
                  f"{r['teams']} | {r['pcts']} | {r['keyed']} |")
    md.append("")

    best = seen[0]
    md += ["## Best candidate", "", f"`{best['url']}`", "",
           f"- {best['teams']} team names, {best['pcts']} percent values, "
           f"{best['keyed']} handle/bets-style keys", "",
           "_First 400 characters:_", "", "```",
           best["head"].replace("`", "'"), "```", "",
           "_If this is JSON on a stable path, it replaces HTML scraping "
           "entirely: no selectors to rot, and full-slate handle data instead "
           "of the one game the current parser finds. The parser gets written "
           "against this shape, and only after a second run confirms the path "
           "is stable rather than a one-off signed URL._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "vsin_net_probe.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
