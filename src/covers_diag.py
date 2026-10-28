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
    out += _hunt(text, soup)
    return out


def _hunt(text: str, soup) -> list[str]:
    """Where did the data GO? Run when the markup is present but the rows are not.

    On 2026-10-28 the consensus page came back 200, 306KB, right title, with
    the `covers-CoversConsensus-*` chrome intact - but `tables: 0 · rows: 0`
    and the three classes the parser keys on
    (`consensusTable--high`, `--low`, `consensusTableContainer`) simply absent.
    Page fine, table gone. `__NEXT_DATA__` was False, so it is not the usual
    Next.js case either, and none of the existing probes say where the numbers
    moved to. This looks for them: an endpoint the page calls, a JSON blob
    inlined in a script, or percentages hiding in data- attributes.
    """
    import re as _re
    from bs4 import BeautifulSoup
    out = ["<details><summary>where did the data go?</summary>", ""]

    # 1. endpoints the page might fetch the table from
    urls = sorted({u for u in _re.findall(
        r'["\'(]((?:https?:)?//[^"\'()\s]+|/[a-zA-Z0-9_\-/.]+)["\')]', text)
        if any(k in u.lower() for k in
               ("consensus", "api", "/data", ".json", "odds", "matchup"))})
    out += [f"- candidate data URLs (**{len(urls)}**):", ""]
    out += [f"    - `{u}`" for u in urls[:25]] or ["    - none"]

    # 2. inline JSON that smells like the table
    hits = []
    for sc in soup.find_all("script"):
        body = sc.string or sc.get_text() or ""
        if len(body) < 40:
            continue
        low = body.lower()
        if any(k in low for k in ("consensus", "percent", '"pct"', "wagers",
                                  "tickets")):
            var = _re.match(r"\s*(?:window\.|var\s+|const\s+)?([A-Za-z_$][\w$.]{2,40})\s*=",
                            body)
            hits.append((var.group(1) if var else "(anonymous)", len(body),
                         body.strip()[:160].replace("\n", " ")))
    out += ["", f"- scripts mentioning consensus/percent/tickets "
            f"(**{len(hits)}**):", ""]
    for nm, ln, head in hits[:8]:
        out += [f"    - `{nm}` ({ln:,} chars): `{head}`"]
    if not hits:
        out.append("    - none")

    # 3. the numbers themselves, wherever they are.
    #    RAW-TEXT COUNTS LIE. The first version of this reported 110 `NN%` in
    #    the HTML and I read that as "the data is there" - but they were
    #    mostly `width:100%` in CSS (the sample was 100,100,93,100,100,...).
    #    What decides it is percentages in VISIBLE text, with script and style
    #    stripped out first.
    pcts = _re.findall(r"\b(\d{1,3})\s?%", text)
    vis_soup = BeautifulSoup(text, "html.parser")
    for bad in vis_soup(["script", "style", "noscript"]):
        bad.decompose()
    visible = vis_soup.get_text(" ", strip=True)
    vis_pcts = _re.findall(r"\b(\d{1,3})\s?%", visible)
    out += ["", f"- `NN%` in RAW html: **{len(pcts)}** "
            f"(includes CSS widths — not evidence on its own)",
            f"- `NN%` in VISIBLE text, script/style stripped: **{len(vis_pcts)}**"
            + (f" (first few: {', '.join(vis_pcts[:12])})" if vis_pcts else
               " — **the percentages are genuinely NOT being delivered**")]
    # the anchor the old parser keyed teams off, and the visible shape
    team_links = vis_soup.select('a[href*="/consensus/pickleadersbyteam/"]')
    out += [f"- `pickleadersbyteam` team anchors: **{len(team_links)}**"
            + (f" (e.g. {', '.join(a.get_text(strip=True) for a in team_links[:6])})"
               if team_links else " — the team anchors are gone too")]
    out += [f"- visible text length: **{len(visible):,}** chars"]
    # CONTEXT around each visible percentage - the only thing that says
    # whether these are game rows in new markup or unrelated page furniture.
    if vis_pcts:
        out += ["", "    visible text around each `NN%`:", "", "    ```"]
        for m in list(_re.finditer(r"\b\d{1,3}\s?%", visible))[:8]:
            a, b = max(0, m.start() - 110), min(len(visible), m.end() + 110)
            out.append("    … " + visible[a:b].replace("\n", " ") + " …")
        out += ["    ```"]
        # and the HTML wrapper, so a selector can be written from it
        out += ["", "    HTML around the first one:", "", "    ```html"]
        node = vis_soup.find(string=_re.compile(r"\d{1,3}\s?%"))
        el = node.parent if node else None
        for _ in range(3):                      # climb to something container-ish
            if el is None or el.parent is None or el.parent.name in ("body", "[document]"):
                break
            el = el.parent
        snippet = (str(el)[:700] if el else "(not found)")
        out += ["    " + ln for ln in snippet.splitlines()[:18]]
        out += ["    ```"]
    dattrs = sorted({a for el in soup.find_all() for a in el.attrs
                     if a.startswith("data-")})
    out += [f"- distinct `data-*` attributes (**{len(dattrs)}**): "
            + (", ".join(f"`{a}`" for a in dattrs[:20]) or "none")]
    # 4. THE DECISIVE ONE: if the numbers ARE in the HTML but not in rows,
    #    the markup moved off <table>/<tr> and the parser needs repinning on
    #    whatever now wraps them. Print the ancestor chain of the first few so
    #    the new selector can be written from evidence, not guessed.
    pct_els = [el for el in soup.find_all(string=_re.compile(r"^\s*\d{1,3}\s?%\s*$"))]
    out += ["", f"- elements whose whole text is `NN%`: **{len(pct_els)}**"]
    for node in pct_els[:6]:
        chain = []
        el = node.parent
        for _ in range(5):
            if el is None or el.name in (None, "[document]"):
                break
            cls = ".".join(el.get("class", []) or [])
            chain.append(f"{el.name}" + (f".{cls}" if cls else ""))
            el = el.parent
        out.append(f"    - `{str(node).strip()}` in  "
                   + "  <  ".join(chain))
    out += ["", "</details>", ""]
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
