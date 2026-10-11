"""
Which new markets does The Odds API actually serve, and what do they cost?

Asked to start tracking starting-pitcher strikeout lines and game totals (full
game and first five) to test as tells.

WHY PROBE BEFORE BUILDING
Credits are the binding constraint, not code. The API bills one credit per
MARKET per REGION on /events/{id}/odds, and the current ~213/month only works
because props are fetched for the ~2.3 games a day we actually bet rather than
the whole slate. Guessing a market key wrong wastes credits and returns
nothing, and guessing which endpoint serves it wrong is the difference between
1 credit a day and 15.

Two things this settles:
  1. the exact key strings that return data (candidates below are guesses)
  2. whether totals come back on the BULK endpoint, which bills once for the
     whole slate, or only per event

Spends a handful of credits deliberately. Refuses to run if remaining is near
RESERVE, because an experiment must never eat the budget the posted bets need.

Writes output/market_probe.md.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from . import prop_odds

log = logging.getLogger("market_probe")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

PER_EVENT = ["pitcher_strikeouts", "pitcher_strikeouts_alternate",
             "totals_1st_5_innings", "h2h_1st_5_innings",
             "spreads_1st_5_innings", "batter_total_bases"]
BULK = ["totals", "h2h", "spreads"]
MIN_FREE = 60          # refuse to probe below this many credits


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    md = ["# New-market probe — The Odds API", "",
          "_Which keys return data, and which endpoint serves them. Credits "
          "are the constraint: the bulk endpoint bills once for the whole "
          "slate, per-event bills per game._", ""]

    # credits_check() returns a human STRING; remaining() is the int. Comparing
    # the string against MIN_FREE is what crashed the first run.
    prop_odds.credits_check()                  # free call, refreshes the headers
    before = prop_odds.remaining()
    md.append(f"- credits before: **{before}**")
    if isinstance(before, int) and before < MIN_FREE:
        md.append(f"- **refusing to probe**: under {MIN_FREE}, the posted bets "
                  "need what is left")
        (OUTPUT_DIR / "market_probe.md").write_text("\n".join(md))
        print("\n".join(md))
        return

    # --- 1. the BULK endpoint: one call, all games
    md += ["", "## Bulk endpoint (`/odds` — BASE already carries the sport)", "",
           "_Bills one credit per market per region for the ENTIRE slate._", ""]
    for mk in BULK:
        try:
            data = prop_odds._get("/odds",
                                  regions="us", markets=mk, oddsFormat="american")
        except Exception as exc:
            md.append(f"- `{mk}`: **failed** — {exc}")
            continue
        games = len(data) if isinstance(data, list) else 0
        got = 0
        sample = ""
        for g in (data or []):
            for b in g.get("bookmakers") or []:
                for m in b.get("markets") or []:
                    if m.get("key") == mk and m.get("outcomes"):
                        got += 1
                        if not sample:
                            sample = json.dumps(m["outcomes"][:2])
                        break
                break
        md.append(f"- `{mk}`: **{games}** games, {got} with the market"
                  + (f" · e.g. `{sample[:150]}`" if sample else ""))

    # --- 2. per-event keys, tested on ONE upcoming game
    eid = None
    try:
        evs = prop_odds._get("/events", dateFormat="iso")
        for e in evs or []:
            if (e.get("commence_time") or "") > "2026-01-01":
                eid = e.get("id")
                md += ["", f"## Per-event keys (one game: "
                       f"{e.get('away_team')} @ {e.get('home_team')})", ""]
                break
    except Exception as exc:
        md.append(f"- /events failed: {exc}")
    if eid:
        for mk in PER_EVENT:
            try:
                data = prop_odds._get(f"/events/{eid}/odds", regions="us",
                                      markets=mk, oddsFormat="american")
            except Exception as exc:
                md.append(f"- `{mk}`: **not served** — {str(exc)[:110]}")
                continue
            out = []
            for b in data.get("bookmakers") or []:
                for m in b.get("markets") or []:
                    if m.get("key") == mk:
                        out = m.get("outcomes") or []
                        break
                if out:
                    break
            md.append(f"- `{mk}`: **{len(out)}** outcome(s)"
                      + (f" · e.g. `{json.dumps(out[:2])[:170]}`" if out else ""))

    after = prop_odds.remaining()
    md += ["", f"- credits after: **{after}**"]
    if isinstance(before, int) and isinstance(after, int):
        md.append(f"- **this probe cost {before - after} credit(s)**")
    md += ["", "## What it decides", "",
           "- a key that returns outcomes on the BULK endpoint can be logged "
           "for every game at ~1 credit a day",
           "- a key that only works per event costs one credit per game, so it "
           "can only cover the games we bet, not the slate",
           "- a key that is not served at all is simply off the table", ""]
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "market_probe.md").write_text("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main()
