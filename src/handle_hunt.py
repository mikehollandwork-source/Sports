"""
Find a HANDLE source for the WNBA, or establish that there isn't one.

WHY THIS IS THE WHOLE QUESTION
The consensus rule fires only when the ticket majority and the dollar majority
agree. That agreement IS the edge - handle-with-tickets returned +12.5% while
handle-against returned -23.5%. Tickets alone are the losing half.

covers gives WNBA tickets (3 games parsed). VSiN's /wnba/betting-splits/ returns
zero rows while /mlb/ returns 15, so the obvious handle source is out. Before
concluding the WNBA cannot run the rule, this tries every other route:

  1. covers' own pages - the consensus and odds HTML, searched for money/handle
     columns alongside the bet percentages we already parse
  2. VSiN URL variants - the sport may sit under a different path segment
  3. covers matchup pages, which for MLB carry a bets/money split per game

Reports what each returns and, critically, whether any of it is a real SPLIT
(two percentages summing near 100) rather than a lone number that could be
anything.

Writes output/handle_hunt.md.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from . import covers

log = logging.getLogger("handle_hunt")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

COVERS_PAGES = {
    "wnba consensus": "https://contests.covers.com/consensus/topconsensus/wnba/overall",
    "wnba odds": "https://www.covers.com/sport/basketball/wnba/odds",
    "wnba matchups": "https://www.covers.com/sports/wnba/matchups",
    "mlb consensus (control)": "https://contests.covers.com/consensus/topconsensus/mlb/overall",
}

VSIN_VARIANTS = [
    "https://data.vsin.com/wnba/betting-splits/",
    "https://data.vsin.com/basketball/betting-splits/?sport=wnba",
    "https://data.vsin.com/betting-splits/?sport=wnba",
    "https://data.vsin.com/wnba/betting-splits",
    "https://data.vsin.com/mlb/betting-splits/",          # control
]

# words a handle/dollar column is labelled with, as opposed to ticket counts
MONEY_WORDS = ("money", "handle", "dollar", "$ %", "cash")
TICKET_WORDS = ("bets", "tickets", "wagers", "consensus")


def _scan(url: str) -> dict:
    soup, text, final = covers._fetch(url)
    out = {"reached": bool(soup or text), "final": final}
    if not (soup or text):
        return out
    body = (text or "")
    low = body.lower()
    out["chars"] = len(body)
    out["money_words"] = {w: low.count(w) for w in MONEY_WORDS if low.count(w)}
    out["ticket_words"] = {w: low.count(w) for w in TICKET_WORDS if low.count(w)}
    # a real split is two percentages that sum to ~100 near each other
    pairs = re.findall(r"(\d{1,3})%\D{0,40}?(\d{1,3})%", body)
    out["pct_pairs"] = len(pairs)
    out["complementary"] = sum(1 for a, b in pairs if 97 <= int(a) + int(b) <= 103)
    return out


def build() -> str:
    md = ["# Hunting a WNBA handle source", "",
          "_The consensus rule needs the DOLLAR majority, not just the ticket "
          "majority - handle-with-tickets returned +12.5%, handle-against "
          "-23.5%. Tickets alone are the losing half, so a WNBA board without "
          "handle would not be the same rule._", "",
          "_A page is only useful if it carries COMPLEMENTARY percentage pairs "
          "(two numbers summing to ~100). A lone percentage could be anything._",
          "",
          "_CAVEAT on the VSiN table below: the MLB control scores the same 3 "
          "pairs as WNBA, yet `_parse_vsin` extracts 15 rows from MLB and 0 from "
          "WNBA. So this metric does not detect VSiN's structure and its VSiN "
          "rows are uninformative - the parser result is the real signal._", ""]

    md += ["## covers.com pages", "",
           "| page | reached | money words | ticket words | pct pairs | complementary |",
           "|---|---|---|---|---|---|"]
    for label, url in COVERS_PAGES.items():
        r = _scan(url)
        if not r["reached"]:
            md.append(f"| {label} | no | | | | |")
            continue
        md.append(f"| {label} | yes | `{r.get('money_words') or '—'}` | "
                  f"`{r.get('ticket_words') or '—'}` | {r.get('pct_pairs', 0)} | "
                  f"**{r.get('complementary', 0)}** |")
    md.append("")

    md += ["## VSiN URL variants", "",
           "| url | reached | complementary pairs |", "|---|---|---|"]
    for url in VSIN_VARIANTS:
        r = _scan(url)
        tag = "control" if "/mlb/" in url else ""
        md.append(f"| `{url}` {tag} | {'yes' if r['reached'] else 'no'} | "
                  f"**{r.get('complementary', 0)}** |")
    md.append("")

    # ---- what ARE those complementary pairs on the matchups page? ----
    md += ["## Context around the complementary pairs", "",
           "_Counting pairs is not enough - a bets/money split and two unrelated "
           "percentages look identical to a counter. This prints the surrounding "
           "text so the pairs can be identified, with MLB's matchups page "
           "alongside for shape comparison._", ""]
    for label, url in (("WNBA matchups", "https://www.covers.com/sports/wnba/matchups"),
                       ("MLB matchups (control)", "https://www.covers.com/sports/mlb/matchups")):
        soup, text, _f = covers._fetch(url)
        md.append(f"**{label}**")
        md.append("")
        if not text:
            md += ["_no response_", ""]
            continue
        shown = 0
        for m in re.finditer(r"(\d{1,3})%\D{0,40}?(\d{1,3})%", text):
            a, b = int(m.group(1)), int(m.group(2))
            if not 97 <= a + b <= 103:
                continue
            lo = max(0, m.start() - 90)
            ctx = re.sub(r"\s+", " ", text[lo:m.end() + 40]).strip()
            md.append(f"- `...{ctx}...`")
            shown += 1
            if shown >= 6:
                break
        if not shown:
            md.append("- _no complementary pairs found_")
        md.append("")

    md.append("_If no WNBA page carries complementary pairs alongside a money "
              "label, there is no handle source - and a 'WNBA board' would be "
              "the ticket half only, which is a DIFFERENT and historically "
              "losing rule, not the same one._")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "handle_hunt.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
