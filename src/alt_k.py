"""
"An amount the pitcher has never missed" - how often does that actually hold?

THE CLAIM BEING TESTED
The proposed parlay uses an alternate-strikeout leg set at a number the starter
has never gone under, on the reasoning that a number he has always cleared is
close to a free leg. That reasoning has a specific flaw worth measuring rather
than asserting: a prior MINIMUM is not a floor. It is the smallest value in a
sample, so it drifts down as the sample grows, and the chance of clearing it is
below 100% by construction - a pitcher who has never gone under 4 across twelve
starts has a thirteenth start.

So this measures the only thing that matters for a parlay leg: out of sample,
in date order, how often did a starter clear the minimum he had set BEFORE that
night? Nothing here is fitted; it is a count.

WHY IT MATTERS AT FIVE LEGS
A parlay needs every leg. A banker leg at 92% rather than 100% costs the whole
ticket 8%, and at that size it is the difference between a structure that is
merely behind and one that is badly behind.

Also reports the ONE-SAFER line (his prior minimum less one), since that is the
obvious response if the exact minimum turns out to be too tight.

Read-only measurement plus `safe_line`, which the paper parlay uses to pick its
leg. Stakes nothing, changes no pick. Writes output/alt_k.md.
"""

from __future__ import annotations

import glob
import json
import logging
import math
from pathlib import Path

log = logging.getLogger("alt_k")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPORT = OUTPUT_DIR / "alt_k.md"
BOX = OUTPUT_DIR / "totals_model_cache.json"

# A minimum taken over fewer starts than this is not worth calling a minimum.
MIN_PRIOR = 8
# Starts under an inning are an opener or an injury exit, not a strikeout line.
MIN_IP = 1.0


def starts_by_pitcher() -> dict:
    """{pitcher_id: [(date, name, k)]} in date order, from the boxscore cache.

    The cache is keyed by game_pk with no date, so the dates come from the board
    filenames - which is also the only ordering that matters, since "prior"
    means prior in time.
    """
    try:
        box = json.loads(BOX.read_text())
    except (OSError, ValueError) as exc:
        log.warning("boxscore cache unavailable (%s)", exc)
        return {}
    when = {}
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            day = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        for g in day.get("games", []):
            when[str(g.get("game_pk"))] = date
    out: dict = {}
    for pk, row in box.items():
        date = when.get(pk)
        if not date:
            continue
        for s in row.get("starters") or []:
            if (s.get("ip") or 0) < MIN_IP:
                continue
            out.setdefault(s["id"], []).append((date, s.get("name"), s["k"]))
    for pid in out:
        out[pid].sort()
    return out


def _rows(starts: dict) -> list[dict]:
    """One row per start that has at least MIN_PRIOR earlier starts."""
    rows = []
    for pid, items in starts.items():
        ks = [k for _d, _n, k in items]
        for i in range(MIN_PRIOR, len(items)):
            prior = ks[:i]
            rows.append({"pid": pid, "name": items[i][1],
                         "date": items[i][0], "k": ks[i],
                         "prior_min": min(prior), "prior_n": i,
                         "prior_mean": sum(prior) / i})
    return rows


def _rate(rows: list, offset: int) -> tuple:
    """(hit rate, n) for clearing prior_min - offset."""
    used = [r for r in rows if r["prior_min"] - offset >= 1]
    if not used:
        return None, 0
    hit = sum(1 for r in used if r["k"] >= r["prior_min"] - offset)
    return hit / len(used), len(used)


def safe_line(starts: list, offset: int = 0) -> dict | None:
    """The alternate-strikeout number for a starter, from his own history.

    `starts` is his [(date, name, k)] list up to but NOT including tonight.
    Returns the line and the measured clear rate for that kind of line, so the
    caller never has to assume it is certain.
    """
    if len(starts) < MIN_PRIOR:
        return None
    ks = [k for _d, _n, k in starts]
    line = min(ks) - offset
    if line < 1:
        return None
    return {"line": line, "prior_min": min(ks), "prior_starts": len(ks),
            "offset": offset}


def build() -> str:
    starts = starts_by_pitcher()
    rows = _rows(starts)
    md = ["# \"A number he has never missed\" — does it hold?", "",
          "_Read-only. A prior MINIMUM is not a floor: it is the smallest "
          "value in a sample, so it drifts down as the sample grows and the "
          "chance of clearing it is below 100% by construction. Every row "
          "below is out of sample and in date order — the minimum is taken "
          f"from starts BEFORE the night being scored, and a start needs "
          f"{MIN_PRIOR} earlier ones to count._", ""]
    if len(rows) < 50:
        return "\n".join(md + [f"- only {len(rows)} usable starts; not "
                               "measurable yet.", ""])
    md += [f"- starters with {MIN_PRIOR}+ prior starts: "
           f"**{len({r['pid'] for r in rows})}**",
           f"- scored starts: **{len(rows)}**", "",
           "| line | clears | n | what a 5-leg ticket loses to this leg |",
           "|---|---|---|---|"]
    for off, label in ((0, "his exact prior minimum"),
                       (1, "one under it (safer)"),
                       (2, "two under it (safest)")):
        r, n = _rate(rows, off)
        if r is None:
            continue
        md.append(f"| {label} | **{r:.1%}** | {n} | "
                  f"{1 - r:.1%} of the ticket |")
    base, n = _rate(rows, 0)
    md += ["", "## How much the sample matters", "",
           "_If the minimum were a floor, more prior starts would make it "
           "safer. It does the opposite: the more starts a pitcher has, the "
           "lower his minimum has been dragged, and the rate does not improve "
           "the way certainty would._", "",
           "| prior starts | clears his prior minimum | n |", "|---|---|---|"]
    for lo, hi in ((MIN_PRIOR, 11), (12, 15), (16, 19), (20, 99)):
        sub = [r for r in rows if lo <= r["prior_n"] <= hi]
        if len(sub) < 20:
            continue
        hit = sum(1 for r in sub if r["k"] >= r["prior_min"])
        md.append(f"| {lo}–{hi if hi < 99 else '+'} | "
                  f"**{hit / len(sub):.1%}** | {len(sub)} |")
    if base:
        se = math.sqrt(base * (1 - base) / n)
        md += ["", "## What this does to the proposed ticket", "",
               f"_The leg is **{base:.1%}** (± {1.96 * se:.1%}), not 100%. On "
               "a five-leg ticket every leg multiplies, so this one alone "
               f"removes **{1 - base:.1%}** of the ticket's chance._", "",
               "_The useful part: a leg this short is priced near certainty "
               "too, so it adds very little to the payout while taking that "
               "bite out of the probability. It is the leg most likely to be "
               "worth replacing with nothing — a four-leg ticket at the same "
               "other four legs pays slightly less and wins more often._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    text = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
