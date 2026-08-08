"""
Does covers.com carry a public-consensus table for another sport?

WHY THIS DECIDES THE WHOLE WNBA QUESTION
The consensus rule never uses the stat model to pick anything. `advantage_team`
appears three times in consensus.evaluate() - as the sign convention for the
line shift, as the index into which moneyline to read, and as the orientation
for the order-book check. The bet is always the ticket majority. Replace
`advantage_team` with "the home team" and the rule picks identically.

So the WNBA blocker was never stats. It is these two inputs:

    public_majority.team   which side the TICKETS are on
    public_check.money     whether the HANDLE agrees with them

Both come from covers.com. The MLB URLs carry the sport in the path, so the
question is simply whether the same pages exist for other sports. If they do,
the consensus rule runs on the WNBA unchanged - no model, no new signal, the
same rule on more games, which is the only volume lever that costs nothing.

Probes the consensus and odds pages for each sport and reports what parses.
Writes output/covers_probe.md.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from . import covers

log = logging.getLogger("covers_probe")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# covers puts the sport in the path; these mirror the MLB forms already in use.
CANDIDATES = {
    "wnba": {
        "consensus": "https://contests.covers.com/consensus/topconsensus/wnba/overall",
        "odds": "https://www.covers.com/sport/basketball/wnba/odds",
    },
    "nba": {
        "consensus": "https://contests.covers.com/consensus/topconsensus/nba/overall",
        "odds": "https://www.covers.com/sport/basketball/nba/odds",
    },
    "nfl": {
        "consensus": "https://contests.covers.com/consensus/topconsensus/nfl/overall",
        "odds": "https://www.covers.com/sport/football/nfl/odds",
    },
    "mlb": {   # the known-good control - if this fails, the probe is at fault
        "consensus": covers.CONSENSUS_URL,
        "odds": covers.ODDS_URL,
    },
}

_PCT = re.compile(r"\b\d{1,3}%")


def _check(url: str) -> dict:
    soup, text, final = covers._fetch(url)
    out = {"url": url, "reached": bool(soup or text), "final": final}
    if not (soup or text):
        out["note"] = "no response (firewalled locally - meaningful only on a runner)"
        return out
    body = text or ""
    out["chars"] = len(body)
    out["pct_tokens"] = len(_PCT.findall(body))
    out["tables"] = len(soup.select("table")) if soup else 0
    # a consensus page should carry many percentage tokens AND team names
    out["rows"] = len(soup.select("tr")) if soup else 0
    return out


def build() -> str:
    md = ["# covers.com coverage by sport", "",
          "_The consensus rule needs only two covers inputs - which side the "
          "TICKETS are on and whether the HANDLE agrees. It never uses the stat "
          "model to pick. So if these pages exist for another sport, the rule "
          "runs there unchanged._", "",
          "_MLB is the control: if it fails here, the probe is at fault, not the "
          "sport._", ""]
    for sport, urls in CANDIDATES.items():
        md.append(f"## {sport.upper()}")
        md.append("")
        for kind, url in urls.items():
            r = _check(url)
            status = "reached" if r["reached"] else "**no response**"
            md.append(f"- `{kind}` — {status} · `{url}`")
            if r["reached"]:
                md.append(f"  - {r.get('chars', 0)} chars · "
                          f"**{r.get('pct_tokens', 0)} percentage tokens** · "
                          f"{r.get('tables', 0)} tables · {r.get('rows', 0)} rows")
                if r.get("final") and r["final"] != url:
                    md.append(f"  - redirected to `{r['final']}`")
            elif r.get("note"):
                md.append(f"  - _{r['note']}_")
        md.append("")
    md.append("_A consensus page that redirects elsewhere, or returns a page "
              "with no percentage tokens, does not carry that sport - and would "
              "otherwise parse to an empty result that looks like 'no games'._")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "covers_probe.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
