"""
Does a RISING bat predict a home run, over and above an elevated one?

THE GAP THIS TESTS
`hr_pick.form_factor` compares a 15-game aggregate against the hitter's season
baseline. That is a LEVEL, not a trend: a hitter hot in games 1-10 and cold in
11-15 sums to the same factor as one cold then hot. The instruction was that
form should be trending upwards, so either the selector is missing something or
the trend carries nothing. This decides which, before anything is wired - the
same bar the pitch-mix term was held to and failed.

PRE-REGISTERED, BEFORE LOOKING
Primary test: the combined ratio (air_ratio x iso_ratio) ** 0.5, matching the
shape form_factor already uses, split at 1.0 into rising and falling. One test,
chosen for matching the existing formula rather than for performing best.
Secondary, reported but not the decision: air alone and ISO alone.

The windows are the last RECENT_N games against the REARLIER_N before them, and
both end strictly BEFORE the game being predicted - so every reading is out of
sample by construction. Three games would be about twelve plate appearances, at
which a slash line swings hundreds of points on one double (`trend.py` says the
same), so 5-against-10 is the shortest split the data can actually carry. That is
a departure from "the past couple games" and it is deliberate: a two-game slope
is noise, and fitting one would manufacture a signal.

Outcome is HR per plate appearance in the NEXT game. Rates, not per-game
averages, so a hitter who bats nine times is not weighted like one who bats
twice.

Permutation test over HITTERS, not over hitter-games: a hitter's own games share
his power, his park and his slot, so shuffling games would treat correlated rows
as independent and shrink the p-value for free.

Read-only. Writes output/form_trend.md. Nothing in the live pipeline imports it.
"""

from __future__ import annotations

import json
import logging
import math
import random
from pathlib import Path

from . import mlb_api

log = logging.getLogger("form_trend")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
CACHE = OUTPUT_DIR / "form_trend_cache.json"
REPORT = OUTPUT_DIR / "form_trend.md"

SEASON = 2026
RECENT_N = 5            # the "now" window
EARLIER_N = 10          # what it is rising against
MIN_BATTED = 8          # batted balls in a window before a ratio is readable
MIN_AB = 10
PERMUTATIONS = 2000
SEED = 20261004


def _rows(player_id: int, cache: dict) -> list[dict] | None:
    """Per-game air/ground/ab/hits/tb/pa/hr for one hitter, cached."""
    key = str(player_id)
    if key in cache:
        return cache[key]
    try:
        log_ = mlb_api._full_gamelog(player_id, "hitting", SEASON)
    except Exception as exc:
        log.warning("gamelog failed for %s (%s)", player_id, exc)
        return None
    out = []
    for sp in log_:
        st = sp.get("stat") or {}
        def g(k):
            try:
                return float(st.get(k, 0) or 0)
            except (TypeError, ValueError):
                return 0.0
        out.append({"air": g("airOuts"), "ground": g("groundOuts"),
                    "ab": g("atBats"), "hits": g("hits"), "tb": g("totalBases"),
                    "pa": g("plateAppearances"), "hr": g("homeRuns")})
    cache[key] = out
    return out


def _window(rows: list[dict]) -> dict:
    air = sum(r["air"] for r in rows)
    ground = sum(r["ground"] for r in rows)
    ab = sum(r["ab"] for r in rows)
    hits = sum(r["hits"] for r in rows)
    tb = sum(r["tb"] for r in rows)
    return {"air": air, "batted": air + ground, "ab": ab, "hits": hits,
            "iso": ((tb - hits) / ab) if ab else None}


def ratios(rows: list[dict], i: int) -> tuple[float, float] | None:
    """(air_ratio, iso_ratio) comparing the RECENT_N games before game i with
    the EARLIER_N before those. None when either window is too thin."""
    a = rows[i - RECENT_N:i]
    b = rows[i - RECENT_N - EARLIER_N:i - RECENT_N]
    if len(a) < RECENT_N or len(b) < EARLIER_N:
        return None
    wa, wb = _window(a), _window(b)
    if min(wa["batted"], wb["batted"]) < MIN_BATTED:
        return None
    if min(wa["ab"], wb["ab"]) < MIN_AB:
        return None
    if wa["iso"] is None or wb["iso"] is None or wb["iso"] <= 0:
        return None
    ar = (wa["air"] / wa["batted"]) / (wb["air"] / wb["batted"]) \
        if wb["air"] else None
    if not ar:
        return None
    return ar, wa["iso"] / wb["iso"]


def collect(ids: list[int], cache: dict) -> list[tuple[int, float, float, float, float]]:
    """(player_id, air_ratio, iso_ratio, HR, PA) one row per predicted game."""
    rows = []
    for pid in ids:
        gl = _rows(pid, cache)
        if not gl:
            continue
        for i in range(RECENT_N + EARLIER_N, len(gl)):
            r = ratios(gl, i)
            if not r:
                continue
            nxt = gl[i]
            if nxt["pa"] <= 0:
                continue
            rows.append((pid, r[0], r[1], nxt["hr"], nxt["pa"]))
    return rows


def _split(rows, key) -> tuple[tuple[float, float], tuple[float, float]]:
    """((rising HR, rising PA), (falling HR, falling PA))."""
    rh = rp = fh = fp = 0.0
    for row in rows:
        if key(row) > 1.0:
            rh += row[3]; rp += row[4]
        else:
            fh += row[3]; fp += row[4]
    return (rh, rp), (fh, fp)


def _gap(rows, key) -> float:
    (rh, rp), (fh, fp) = _split(rows, key)
    if not rp or not fp:
        return 0.0
    return rh / rp - fh / fp


def _perm_p(rows, key, observed: float) -> float:
    """Shuffle the rising/falling label BY HITTER, so a hitter's correlated
    games move together and the null keeps his own rate intact."""
    rng = random.Random(SEED)
    by_pid: dict[int, list] = {}
    for row in rows:
        by_pid.setdefault(row[0], []).append(row)
    pids = list(by_pid)
    hits = 0
    for _ in range(PERMUTATIONS):
        flip = {p: rng.random() < 0.5 for p in pids}
        rh = rp = fh = fp = 0.0
        for p, rs in by_pid.items():
            for row in rs:
                rising = key(row) > 1.0
                if flip[p]:
                    rising = not rising
                if rising:
                    rh += row[3]; rp += row[4]
                else:
                    fh += row[3]; fp += row[4]
        g = (rh / rp - fh / fp) if rp and fp else 0.0
        if abs(g) >= abs(observed):
            hits += 1
    return (hits + 1) / (PERMUTATIONS + 1)


KEYS = {
    "combined (air × ISO)**0.5": lambda r: math.sqrt(r[1] * r[2]),
    "air rate only": lambda r: r[1],
    "ISO only": lambda r: r[2],
}


def build() -> str:
    cache = {}
    try:
        cache = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        pass
    ids = []
    try:
        teams = mlb_api._get("teams", sportId=1, season=SEASON).get("teams", [])
    except Exception as exc:
        log.warning("team list failed (%s)", exc)
        teams = []
    for t in teams:
        try:
            r = mlb_api._get(f"teams/{t['id']}/roster", rosterType="active")
        except Exception as exc:
            log.warning("roster failed for %s (%s)", t.get("name"), exc)
            continue
        for e in r.get("roster", []):
            if (e.get("position") or {}).get("type") != "Pitcher":
                pid = (e.get("person") or {}).get("id")
                if pid:
                    ids.append(pid)
    rows = collect(ids, cache)
    try:
        CACHE.write_text(json.dumps(cache))
    except OSError as exc:
        log.warning("cache not written (%s)", exc)

    md = [f"# Does a RISING bat homer more than an elevated one? — {SEASON}", "",
          "_`hr_pick.form_factor` measures a level: a 15-game lump against the "
          "hitter's season. This asks whether DIRECTION adds anything, before a "
          "trend term is wired into the selector._", "",
          f"Windows: last {RECENT_N} games against the {EARLIER_N} before them, "
          f"both ending before the game predicted. Outcome: HR per PA in that "
          f"next game. Permutation over hitters, {PERMUTATIONS} draws.", "",
          f"**{len(rows)} hitter-games** from "
          f"{len({r[0] for r in rows})} hitters.", ""]
    if not rows:
        return "\n".join(md + ["_No usable rows._"])

    md += ["| split | rising HR/PA | falling HR/PA | gap | permutation p |",
           "|---|---|---|---|---|"]
    for i, (label, key) in enumerate(KEYS.items()):
        (rh, rp), (fh, fp) = _split(rows, key)
        gap = _gap(rows, key)
        p = _perm_p(rows, key, gap)
        tag = " ← primary" if i == 0 else ""
        md.append(f"| {label}{tag} | {rh/rp:.3%} ({rh:.0f}/{rp:.0f}) "
                  f"| {fh/fp:.3%} ({fh:.0f}/{fp:.0f}) | {gap:+.3%} | {p:.4f} |")
    md += ["",
           "## How to read this", "",
           "- the primary test is the combined ratio; the other two are "
           "reported so a split-specific result is visible, not so the best one "
           "can be chosen after the fact",
           "- a gap near zero means direction carries nothing beyond the level "
           "the selector already uses, and no trend term should be wired",
           "- translate any gap into a multiplier before judging it: the "
           "selector already swings form ×1.30 and wind ×1.24, so a gap worth "
           "less than a percent or two cannot change a pick",
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
