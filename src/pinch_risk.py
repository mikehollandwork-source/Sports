"""
Does this hitter get pulled before he finishes a game?

THE HARM
A hits prop needs plate appearances. A hitter lifted for a pinch hitter in the
sixth got two, and the prop was dead before first pitch. On 2026-10-04 the
Braves did it twice in one game - Murphy out for Tellez after 1 AB, Thomas out
for Yastrzemski after 2.

WHY THE EXISTING GATE DOES NOT CATCH IT
`props.MIN_AVG_PA` is a MEAN (3.2 PA across the team wins he played in). A mean
cannot express "ever pinch-hit for": a hitter who goes the distance in 85% of
his starts and is lifted in the other 15% averages about 4.0 and sails through,
while being exactly the risk worth avoiding. The quantity that matters is the
SHARE of starts that end early, not the average length of one.

THE MEASURE
short-start rate = starts ending in SHORT_PA or fewer plate appearances, over
starts. Starts only, when the feed carries gamesStarted - a hitter who entered
as a substitute is not a hitter who was pulled, and counting bench appearances
would condemn every part-timer for the wrong reason. Where gamesStarted is
missing the fallback is games with at least MIN_START_PA plate appearances,
which is a weaker proxy and is reported as such.

This module is READ-ONLY on its own; `props` imports `risk()` for the gate.
`python -m src.pinch_risk` writes output/pinch_risk.md, the distribution the
threshold was set from.
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import mlb_api

log = logging.getLogger("pinch_risk")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPORT = OUTPUT_DIR / "pinch_risk.md"

SHORT_PA = 2            # a start ending here or below is a pull, not a game
MIN_START_PA = 3        # fallback "he probably started" bar, when no gamesStarted
MIN_STARTS = 20         # starts needed before a rate is worth acting on


def _starts(pid: int, season: int) -> tuple[list[float], bool]:
    """(PA in each start, whether gamesStarted was available).

    Returns ([], False) on any failure, which `risk` reads as "unknown" and the
    gate treats as safe - a feed outage must not silently drop every prop.
    """
    try:
        rows = mlb_api._full_gamelog(pid, "hitting", season)
    except Exception as exc:
        log.warning("gamelog unavailable for %s (%s)", pid, exc)
        return [], False
    pas, exact = [], False
    for sp in rows:
        st = sp.get("stat") or {}
        try:
            pa = float(st.get("plateAppearances", 0) or 0)
        except (TypeError, ValueError):
            continue
        gs = st.get("gamesStarted")
        if gs is not None:
            exact = True
            try:
                if float(gs or 0) < 1:
                    continue
            except (TypeError, ValueError):
                continue
        elif pa < MIN_START_PA:
            continue
        if pa >= 1:
            pas.append(pa)
    return pas, exact


def risk(pid: int, season: int) -> dict | None:
    """{"rate", "short", "starts", "exact"} or None when the sample is too thin.

    None means "not enough to judge", never "fine" - the caller decides what to
    do with an unknown, and `props` lets it through rather than dropping a
    hitter for having a short season.
    """
    pas, exact = _starts(pid, season)
    if len(pas) < MIN_STARTS:
        return None
    short = sum(1 for pa in pas if pa <= SHORT_PA)
    return {"rate": short / len(pas), "short": short, "starts": len(pas),
            "exact": exact}


# --- the report the threshold was set from ------------------------------------
def build() -> str:
    try:
        teams = mlb_api._get("teams", sportId=1, season=2026).get("teams", [])
    except Exception as exc:
        log.warning("team list failed (%s)", exc)
        teams = []
    rows = []
    for t in teams:
        try:
            r = mlb_api._get(f"teams/{t['id']}/roster", rosterType="active")
        except Exception as exc:
            log.warning("roster failed for %s (%s)", t.get("name"), exc)
            continue
        for e in r.get("roster", []):
            if (e.get("position") or {}).get("type") == "Pitcher":
                continue
            person = e.get("person") or {}
            pid, name = person.get("id"), person.get("fullName")
            if not pid:
                continue
            rk = risk(pid, 2026)
            if rk:
                rows.append((name, t.get("abbreviation") or "", rk))
    md = ["# How often does a hitter get pulled before he finishes? — 2026", "",
          "_A hits prop needs plate appearances. `props.MIN_AVG_PA` is a MEAN "
          "and cannot express \"ever pinch-hit for\"; this is the share of "
          "STARTS ending in "
          f"{SHORT_PA} PA or fewer._", "",
          f"Hitters with {MIN_STARTS}+ starts: **{len(rows)}**", ""]
    if not rows:
        return "\n".join(md + ["_No usable rows._"])
    exact = sum(1 for _, _, r in rows if r["exact"])
    md += [f"gamesStarted available for {exact} of {len(rows)} "
           f"({'exact starts' if exact == len(rows) else 'rest use the PA fallback'})",
           ""]
    rates = sorted(r["rate"] for _, _, r in rows)
    def q(p):
        return rates[int(p * (len(rates) - 1))]
    md += ["| percentile | short-start rate |", "|---|---|"]
    for p in (0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99):
        md.append(f"| p{int(p*100)} | {q(p):.1%} |")
    md += ["", "## Worst 25 — these are what the gate must catch", "",
           "| hitter | team | short starts | starts | rate |", "|---|---|---|---|---|"]
    for name, abbr, r in sorted(rows, key=lambda x: -x[2]["rate"])[:25]:
        md.append(f"| {name} | {abbr} | {r['short']} | {r['starts']} "
                  f"| **{r['rate']:.1%}** |")
    md += ["", "## The two from 2026-10-04", ""]
    for want in ("Murphy", "Thomas", "Tellez", "Yastrzemski"):
        for name, abbr, r in rows:
            if want in (name or ""):
                md.append(f"- {name} ({abbr}): {r['short']}/{r['starts']} "
                          f"= **{r['rate']:.1%}**")
    md += ["", "## Reading it", "",
           "- the gate should sit where it catches the pulled bats without "
           "condemning ordinary hitters, so compare the worst list against the "
           "median rather than picking a round number",
           "- a hitter under MIN_STARTS returns None and is LET THROUGH: "
           "unknown is not the same as risky, and a feed outage must not "
           "silently drop every prop on the board",
           ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    OUTPUT_DIR.mkdir(exist_ok=True)
    text = build()
    REPORT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
