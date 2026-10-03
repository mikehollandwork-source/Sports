"""
Which batter prop markets does the odds feed actually offer, and at what prices?

WHY
The board's only prop is 1+ HIT, priced around -200 because it is a ~63% event.
At that price break-even is 66.7%, so the hold eats most of any edge the hitter
read could produce. A market priced nearer even money gives the SAME read more
room above the vig - if those markets exist and are quoted.

CREDIT COST - READ BEFORE RUNNING
The Odds API bills one credit per market per region on /events/{id}/odds, and the
free tier is roughly 150-240 credits a MONTH, which `prop_odds` is deliberately
built to stay under. This probe asks for several markets on ONE event, so it costs
about as many credits as markets listed in CANDIDATES. It is a one-off diagnostic,
not something to put on a schedule.

Writes output/prop_markets.md.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import prop_odds

log = logging.getLogger("prop_markets_probe")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# batter markets worth knowing about. batter_hits is included as a CONTROL: it is
# already known to be quoted, so if it comes back empty the probe itself is broken
# rather than the market being unavailable.
CANDIDATES = [
    "batter_hits",             # control
    "batter_total_bases",
    "batter_hits_runs_rbis",
    "batter_runs_scored",
    "batter_rbis",
    "batter_singles",
    "batter_doubles",
    "batter_home_runs",
    "batter_walks",
]


def _upcoming_pairs(date: str) -> list[tuple[str, str]]:
    """(away, home) for board games that have NOT started."""
    try:
        board = json.loads(
            (OUTPUT_DIR / f"picks_{date}.json").read_text())
    except (OSError, ValueError):
        return []
    out = []
    for g in board.get("games", []):
        m = g.get("matchup") or ""
        if g.get("state") == "upcoming" and " @ " in m:
            a, h = m.split(" @ ")
            out.append((a, h))
    return out


def probe(date: str, markets: list[str]) -> tuple[str, dict]:
    """(event label, {market: [...]}) for one UPCOMING event.

    It must be upcoming. The first run of this probe took evs[0], the earliest
    event, which had been live for two hours - so Over 0.5 hits came back at
    +208 instead of the -200 that market actually prices pre-game, because the
    hitters had at-bats behind them. In-game prices answer a different question
    entirely.
    """
    evs = prop_odds._events(date)
    if not evs:
        return "", {}
    pairs = _upcoming_pairs(date)
    ev = next((e for e in evs if (e["away"], e["home"]) in pairs), None)
    if ev is None:
        log.warning("no upcoming event matched the board; not spending credits")
        return "", {}
    label = f"{ev['away']} @ {ev['home']}"
    data = prop_odds._get(f"/events/{ev['id']}/odds", regions="us",
                          markets=",".join(markets), oddsFormat="american")
    found: dict = defaultdict(list)
    for bk in (data or {}).get("bookmakers", []) or []:
        for mk in bk.get("markets", []) or []:
            key = mk.get("key")
            if key not in markets:
                continue
            for o in mk.get("outcomes", []) or []:
                if not isinstance(o.get("price"), (int, float)):
                    continue
                found[key].append({
                    "player": str(o.get("description") or "").strip(),
                    "point": o.get("point"), "side": o.get("name"),
                    "price": int(o["price"]), "book": bk.get("key")})
    return label, dict(found)


def build(date: str) -> str:
    md = [f"# Batter prop markets available — {date}", "",
          "_One event probed. Costs roughly one API credit per market, against a "
          "free tier of ~150-240 a month, so this is a one-off._", "",
          "_Why it matters: 1+ hit is a ~63% event priced near -200, where "
          "break-even is 66.7% and the hold eats the edge. A market nearer even "
          "money gives the same hitter read more room._", ""]
    if not prop_odds._key():
        return "\n".join(md + ["**No THE_ODDS_API_KEY in the environment** - "
                               "cannot probe. Nothing was spent.", ""])
    label, found = probe(date, CANDIDATES)
    if not label:
        return "\n".join(md + ["No UPCOMING event matched the board, so nothing "
                               "was probed and no credits were spent.", ""])
    md += [f"- event probed: **{label}** (upcoming — in-game prices "
           "would answer a different question)", ""]
    if "batter_hits" not in found:
        md += ["⚠ **The control market `batter_hits` came back empty**, so treat "
               "every 'not quoted' below as unproven - the probe may be at "
               "fault, not the feed.", ""]
    md += ["| market | quoted? | outcomes | distinct lines | median OVER price |",
           "|---|---|---|---|---|"]
    for mk in CANDIDATES:
        rows = found.get(mk) or []
        if not rows:
            md.append(f"| `{mk}` | **no** | 0 | — | — |")
            continue
        overs = [r["price"] for r in rows
                 if str(r["side"]).lower() == "over"]
        pts = sorted({r["point"] for r in rows if r["point"] is not None})
        med = f"{st.median(overs):+.0f}" if overs else "—"
        md.append(f"| `{mk}` | yes | {len(rows)} | "
                  f"{', '.join(str(p) for p in pts) or '—'} | {med} |")
    md.append("")

    # the point of the exercise: which quoted market sits nearest even money
    near = []
    for mk, rows in found.items():
        for pt in sorted({r["point"] for r in rows if r["point"] is not None}):
            overs = [r["price"] for r in rows
                     if r["point"] == pt and str(r["side"]).lower() == "over"]
            if len(overs) >= 3:
                m = st.median(overs)
                be = abs(m) / (abs(m) + 100) if m < 0 else 100 / (m + 100)
                near.append((abs(be - 0.5), mk, pt, m, be, len(overs)))
    if near:
        near.sort()
        md += ["## Nearest even money (the whole point)", "",
               "_Lower break-even leaves more room above the hold for a hitter "
               "read to matter._", "",
               "| market | line | median OVER | break-even |", "|---|---|---|---|"]
        for _, mk, pt, m, be, n in near[:12]:
            md.append(f"| `{mk}` | Over {pt} | {m:+.0f} | **{be:.1%}** |")
        md.append("")
    md += ["_Availability is not an edge. Nothing in this project has shown the "
           "hitter read beats a price in ANY market; a cheaper price only means "
           "less hold to overcome._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=os.environ.get("PICKS_DATE"))
    date = ap.parse_args().date
    if not date:
        from .main import today_eastern
        date = today_eastern()
    md = build(date)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "prop_markets.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
