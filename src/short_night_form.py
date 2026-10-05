"""
Can a hot bat buy its way past the short-night gate?

THE QUESTION
`props.SHORT_NIGHT_MAX` withholds a prop from a hitter whose starts tend to end
early, because a prop needs plate appearances. But fewer PA and hotter form push
the SAME quantity in opposite directions - the chance he gets a hit tonight - so
a hitter red hot enough should be able to clear the bar anyway. The override
threshold is therefore not a matter of taste: it is wherever a blocked hitter's
P(1+ hit) climbs back to what an allowed one delivers.

WHAT IS MEASURED
Per start, strictly from PRIOR games:
  - short-night rate, exactly as `pinch_risk.summarise` computes it
  - form, exactly as `props` computes it: hit rate over his last RECENT_GAMES
    games minus his season-to-date rate, in points. The same field the board
    already carries, because an override has to key off something that exists.
Outcome: did he get a hit in that start.

Reading it: if blocked-but-hot reaches the allowed group's rate, the override is
justified and the crossing point IS the threshold. If it never does, there is no
form lift that compensates and the gate should stay absolute.

Read-only. Writes output/short_night_form.md.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

from . import mlb_api, pinch_risk, props

log = logging.getLogger("short_night_form")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
LOGCACHE = OUTPUT_DIR / "short_night_logs.json"
REPORT = OUTPUT_DIR / "short_night_form.md"

SEASON = 2026
MIN_PRIOR_GAMES = 20       # before a form reading means anything


def _logs(pids: list[int]) -> dict:
    """{pid: {date: [pa, hits]}} - one gamelog per hitter, cached to disk."""
    try:
        cache = json.loads(LOGCACHE.read_text())
    except (OSError, ValueError):
        cache = {}
    missing = [p for p in pids if str(p) not in cache]
    for n, pid in enumerate(missing, 1):
        rows = {}
        for sp in props._game_log(pid, SEASON):
            st = sp.get("stat") or {}
            d = sp.get("date")
            if not d:
                continue
            try:
                rows[d] = [float(st.get("plateAppearances", 0) or 0),
                           float(st.get("hits", 0) or 0)]
            except (TypeError, ValueError):
                continue
        cache[str(pid)] = rows
        if n % 50 == 0:
            log.info("gamelogs %d/%d", n, len(missing))
    if missing:
        try:
            LOGCACHE.write_text(json.dumps(cache))
        except OSError as exc:
            log.warning("gamelog cache not written (%s)", exc)
    return cache


def rows() -> list[tuple[float, float, int]]:
    """(short_night_rate, form, got_a_hit) per start, all from prior games."""
    pc = pinch_risk._load()
    starts_by = pc.get("starts") or {}
    pids = [int(p) for p, r in starts_by.items()
            if len(r) >= pinch_risk.MIN_STARTS]
    logs = _logs(pids)
    out = []
    for pid in pids:
        gl = logs.get(str(pid)) or {}
        if not gl:
            continue
        starts = sorted(starts_by[str(pid)], key=lambda r: r[0])
        played = sorted((d, v) for d, v in gl.items() if v[0] >= 1)
        for i in range(pinch_risk.MIN_STARTS, len(starts)):
            date = starts[i][0]
            tonight = gl.get(date)
            if not tonight or tonight[0] < 1:
                continue
            prior = [(d, v) for d, v in played if d < date]
            if len(prior) < MIN_PRIOR_GAMES:
                continue
            season_rate = sum(1 for _, v in prior if v[1] >= 1) / len(prior)
            last = prior[-props.RECENT_GAMES:]
            form = (sum(1 for _, v in last if v[1] >= 1) / len(last)
                    - season_rate) * 100
            snr = pinch_risk.summarise(starts[:i])["rate"]
            out.append((snr, form, 1 if tonight[1] >= 1 else 0))
    return out


def _rate(sel) -> tuple[float, int]:
    n = len(sel)
    return ((sum(y for _, _, y in sel) / n) if n else 0.0, n)


def _ci(p: float, n: int) -> float:
    return 1.96 * math.sqrt(p * (1 - p) / n) if n else 0.0


def build() -> str:
    data = rows()
    gate = props.SHORT_NIGHT_MAX
    md = ["# Can a hot bat buy its way past the short-night gate?", "",
          "_The gate and hot form push the same quantity - his chance of a hit "
          "tonight - in opposite directions, so the override threshold is "
          "wherever a blocked hitter climbs back to what an allowed one "
          "delivers. Everything below is built from PRIOR games only._", "",
          f"**{len(data)} starts.** Gate at "
          f"`props.SHORT_NIGHT_MAX` = {gate:.0%}; form is the board's own "
          f"definition (last {props.RECENT_GAMES} games minus season, in "
          f"points).", ""]
    if not data:
        return "\n".join(md + ["_No rows._"])

    allowed = [r for r in data if r[0] <= gate]
    blocked = [r for r in data if r[0] > gate]
    ar, an = _rate(allowed)
    br, bn = _rate(blocked)
    md += ["| group | P(1+ hit) | n |", "|---|---|---|",
           f"| allowed (≤{gate:.0%}) | {ar:.1%} ± {_ci(ar,an):.1%} | {an} |",
           f"| blocked (>{gate:.0%}) | {br:.1%} ± {_ci(br,bn):.1%} | {bn} |",
           "",
           f"The gate is worth **{ar-br:+.1%}** of hit probability. That is "
           "the hole a hot bat has to climb out of.", "",
           "## Blocked hitters, by how hot they are", "",
           "| form (pts above his own season) | P(1+ hit) | n | vs allowed |",
           "|---|---|---|---|"]
    bands = [(-999, 0, "cold (≤0)"), (0, 10, "0 to +10"),
             (10, 20, "+10 to +20"), (20, 30, "+20 to +30"),
             (30, 999, "+30 or more")]
    crossing = None
    for lo, hi, label in bands:
        sel = [r for r in blocked if lo < r[1] <= hi]
        p, n = _rate(sel)
        if not n:
            md.append(f"| {label} | — | 0 | — |")
            continue
        mark = ""
        if p >= ar and crossing is None:
            crossing = label
            mark = "  ← clears the allowed group"
        md.append(f"| {label} | {p:.1%} ± {_ci(p,n):.1%} | {n} "
                  f"| {p-ar:+.1%}{mark} |")
    md += ["", "## For comparison, allowed hitters by the same bands", "",
           "| form | P(1+ hit) | n |", "|---|---|---|"]
    for lo, hi, label in bands:
        sel = [r for r in allowed if lo < r[1] <= hi]
        p, n = _rate(sel)
        md.append(f"| {label} | {p:.1%} | {n} |" if n
                  else f"| {label} | — | 0 |")
    md += ["", "## Verdict", ""]
    if crossing:
        md.append(f"- blocked hitters at **{crossing}** reach the allowed "
                  f"group's {ar:.1%}, so an override at that form level "
                  "restores what the gate protects — and no lower")
    else:
        md.append("- **no form band lifts a blocked hitter to the allowed "
                  "group's rate.** Being hot does not pay for the lost plate "
                  "appearances, and the gate should stay absolute")
    md += ["- read the ± before acting on a band: the hot cells are thin, and "
           "a band that clears only inside its own interval has not cleared",
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
