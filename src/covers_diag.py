"""
Why is covers.com returning nothing? Structure, not guesswork.

source_health flagged a real outage on 2026-10-08: covers tickets 0/1 and
handle 0/1, with the board showing no plays on a one-game slate. The board
cannot tell that apart from a quiet night, which is why the check exists.

covers parsers fail SOFT by design - they log and return empty so the rest of
the board still runs - so an outage leaves no stack trace. This fetches the
pages the board depends on and reports what actually came back: status, final
URL after redirects, title, size, whether the data is client-rendered behind
__NEXT_DATA__, how many tables exist, and which class names are present. Then
it runs the CURRENT parser and says how many rows it got.

The point is to repair the selectors from evidence in one round trip rather
than fixing blind from a sandbox that cannot reach the site.

Writes output/covers_diag.md. Read-only; changes no pick.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from . import covers

log = logging.getLogger("covers_diag")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _probe(label: str, url: str) -> list[str]:
    out = [f"## {label}", "", f"`{url}`", ""]
    try:
        resp = covers.SESSION.get(url, timeout=covers.TIMEOUT)
    except Exception as exc:
        return out + [f"**request failed:** `{exc}`", ""]
    text = resp.text
    out += [f"- HTTP **{resp.status_code}** · {len(text):,} bytes · "
            f"content-type `{resp.headers.get('content-type','')}`",
            f"- final URL after redirects: `{resp.url}`"]
    if resp.status_code != 200:
        out += ["", "**Non-200 — the page itself is the problem, not the "
                "selectors.**", ""]
        return out
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(text, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    nd = covers._next_data(soup)
    out += [f"- title: `{title}`",
            f"- `__NEXT_DATA__` present: **{nd is not None}**",
            f"- tables: **{len(soup.find_all('table'))}** · "
            f"rows: **{len(soup.find_all('tr'))}**"]
    # Is this a block page rather than the real thing?
    low = text.lower()
    for marker in ("captcha", "access denied", "cloudflare", "are you a human",
                   "unusual traffic", "rate limit"):
        if marker in low:
            out.append(f"- ⚠️ page text contains **{marker!r}** — looks like a "
                       f"block, not a markup change")
    classes = sorted({c for el in soup.find_all(class_=True)
                      for c in el.get("class", [])})
    cov = [c for c in classes if "overs" in c or "onsensus" in c]
    out += ["", f"- class names containing 'overs'/'onsensus' "
            f"(**{len(cov)}**): " + (", ".join(f"`{c}`" for c in cov[:25])
                                     or "**none — the covers-* markup is gone**"),
            "", "<details><summary>first 40 class names on the page</summary>",
            "", "```", ", ".join(classes[:40]), "```", "</details>", ""]
    if nd:
        def keys(o, d=0):
            if d > 2 or not isinstance(o, dict):
                return []
            return [k for k in o] + [f"{k}.{s}" for k in o
                                     for s in keys(o[k], d + 1)][:40]
        out += ["- `__NEXT_DATA__` top keys: `"
                + ", ".join(keys(nd)[:30]) + "`", ""]
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    md = ["# covers.com diagnostic", "",
          "_Run because `source_health` reported covers tickets and handle at "
          "0/1 while the board showed no plays. The parsers fail soft, so an "
          "outage leaves no stack trace — this is what the site actually "
          "returned._", ""]
    md += _probe("Consensus (tickets + handle)", covers.CONSENSUS_URL)
    md += _probe("Odds / slate lines", covers.ODDS_URL)
    md += _probe("Forum listing", covers.FORUM_URL)

    md += ["## What the CURRENT parser gets", ""]
    try:
        con = covers.consensus()
        md.append(f"- `consensus()` returned **{len(con)}** teams")
        if con:
            k = list(con)[:3]
            md.append("- sample: `" + json.dumps({x: con[x] for x in k})[:300] + "`")
    except Exception as exc:
        md.append(f"- `consensus()` raised `{exc}`")
    try:
        lines = covers.slate_lines()
        md.append(f"- `slate_lines()` returned **{len(lines)}** games")
    except Exception as exc:
        md.append(f"- `slate_lines()` raised `{exc}`")
    md += ["", "## Reading it", "",
           "- a non-200, or a captcha/Cloudflare marker, means access is "
           "blocked and no selector change fixes it",
           "- 200 with **no `covers-*` class names** means the markup was "
           "rebuilt and the selectors need repinning",
           "- 200 with `__NEXT_DATA__` present means the numbers are rendered "
           "client-side and should be read from that JSON, not the DOM", ""]
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "covers_diag.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
