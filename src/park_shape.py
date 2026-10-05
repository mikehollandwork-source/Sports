"""
Does a park's SHAPE add anything to its overall home-run factor?

THE IDEA
`hr_pick` already multiplies by a park HR factor, but that is one number for the
whole field. It cannot express a left-handed pull hitter walking into a short
right field. The shape might matter beyond the aggregate - or the aggregate
might already contain it, which is the usual answer and the reason this is
measured before anything is wired.

WHAT IS AND IS NOT AVAILABLE
MLB's own feed carries NO hitData: the play record has no distance and no
coordinates, so "average air-out length and where it lands" cannot come from
there (`spray_probe.py`). Statcast does serve it, but a hitter's pull direction
is mostly settled by which side he bats from, which the model already knows -
so this tests the cheap version first. If the cheap version is worth nothing,
the expensive one almost certainly is too; if it is worth something, THEN a real
spray profile is worth fetching.

Fence distances come from `/venues?hydrate=fieldInfo`, served for all 62 parks:
leftLine, left, leftCenter, center, rightCenter, right, rightLine.

THE DESIGN
Within-hitter, which removes the obvious confound for free. A hitter's own home
runs at parks with a SHORT pull-side fence are compared against his own rate at
parks with a long one, and only then averaged across hitters. Comparing hitters
to each other would mostly measure which hitters are good.

Pull side is rightCenter for a left-handed bat and leftCenter for a right-handed
one; switch hitters are dropped rather than guessed at.

Read-only. Writes output/park_shape.md.
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path

from . import mlb_api, props

log = logging.getLogger("park_shape")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPORT = OUTPUT_DIR / "park_shape.md"
CACHE = OUTPUT_DIR / "park_shape_cache.json"

SEASON = 2026
MIN_PA = 200           # season plate appearances before a hitter is usable
MIN_SIDE = 40          # PA needed on each side of the split
PERMUTATIONS = 2000
SEED = 20261005


def venues() -> dict[int, dict]:
    """{venue_id: fieldInfo} for every park."""
    out = {}
    try:
        data = mlb_api._get("venues", season=SEASON, hydrate="fieldInfo")
    except Exception as exc:
        log.warning("venues failed (%s)", exc)
        return out
    for v in data.get("venues") or []:
        fi = v.get("fieldInfo") or {}
        if fi.get("leftCenter") and fi.get("rightCenter"):
            out[v["id"]] = {"name": v.get("name"), **fi}
    return out


def game_venues() -> dict[int, int]:
    """{gamePk: venue_id} across the season, from one schedule call."""
    out = {}
    try:
        sched = mlb_api._get("schedule", sportId=1, gameType="R,P",
                             startDate=f"03/01/{SEASON}",
                             endDate=f"12/01/{SEASON}")
    except Exception as exc:
        log.warning("schedule failed (%s)", exc)
        return out
    for d in sched.get("dates") or []:
        for g in d.get("games") or []:
            vid = (g.get("venue") or {}).get("id")
            if vid:
                out[g["gamePk"]] = vid
    return out


def _bat_sides(ids: list[int]) -> dict[int, str]:
    out = {}
    for i in range(0, len(ids), 100):
        try:
            data = mlb_api._get("people", personIds=",".join(
                str(x) for x in ids[i:i + 100]))
        except Exception as exc:
            log.warning("people failed (%s)", exc)
            continue
        for p in data.get("people") or []:
            out[p["id"]] = ((p.get("batSide") or {}).get("code") or "")
    return out


def collect() -> list[dict]:
    """Per hitter: HR and PA split by whether the park's pull-side fence is
    short or long, each measured against the median park."""
    try:
        cache = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        cache = {}
    vmap, gmap = venues(), game_venues()
    if not vmap or not gmap:
        return []
    pulls = sorted(v["leftCenter"] for v in vmap.values())
    mid_l = pulls[len(pulls) // 2]
    pullr = sorted(v["rightCenter"] for v in vmap.values())
    mid_r = pullr[len(pullr) // 2]

    ids = [int(p) for p in cache.get("ids", [])]
    if not ids:
        try:
            teams = mlb_api._get("teams", sportId=1, season=SEASON).get("teams", [])
        except Exception as exc:
            log.warning("teams failed (%s)", exc)
            return []
        for t in teams:
            try:
                r = mlb_api._get(f"teams/{t['id']}/roster", rosterType="active")
            except Exception as exc:
                log.warning("roster failed (%s)", exc)
                continue
            for e in r.get("roster") or []:
                if (e.get("position") or {}).get("type") != "Pitcher":
                    pid = (e.get("person") or {}).get("id")
                    if pid:
                        ids.append(pid)
        cache["ids"] = ids
    sides = _bat_sides(ids)

    rows = []
    for pid in ids:
        side = sides.get(pid)
        if side not in ("L", "R"):
            continue                 # switch hitters dropped, not guessed
        short = {"hr": 0.0, "pa": 0.0}
        long_ = {"hr": 0.0, "pa": 0.0}
        for sp in props._game_log(pid, SEASON):
            st = sp.get("stat") or {}
            pk = (sp.get("game") or {}).get("gamePk")
            fi = vmap.get(gmap.get(pk) or -1)
            if not fi:
                continue
            try:
                pa = float(st.get("plateAppearances", 0) or 0)
                hr = float(st.get("homeRuns", 0) or 0)
            except (TypeError, ValueError):
                continue
            if pa < 1:
                continue
            if side == "L":
                is_short = fi["rightCenter"] < mid_r
            else:
                is_short = fi["leftCenter"] < mid_l
            cell = short if is_short else long_
            cell["hr"] += hr
            cell["pa"] += pa
        if short["pa"] >= MIN_SIDE and long_["pa"] >= MIN_SIDE \
                and short["pa"] + long_["pa"] >= MIN_PA:
            rows.append({"pid": pid, "side": side,
                         "short_hr": short["hr"], "short_pa": short["pa"],
                         "long_hr": long_["hr"], "long_pa": long_["pa"]})
    try:
        CACHE.write_text(json.dumps(cache))
    except OSError as exc:
        log.warning("cache not written (%s)", exc)
    return rows


def _delta(rows: list[dict]) -> float:
    """Pooled HR/PA at short pull-side parks minus long, within hitters."""
    sh = sum(r["short_hr"] for r in rows)
    sp = sum(r["short_pa"] for r in rows)
    lh = sum(r["long_hr"] for r in rows)
    lp = sum(r["long_pa"] for r in rows)
    return (sh / sp - lh / lp) if sp and lp else 0.0


def _perm_p(rows: list[dict], obs: float) -> float:
    """Flip each hitter's two cells at random: the null where the fence has no
    effect but each hitter keeps his own rate and his own two sample sizes."""
    rng = random.Random(SEED)
    hits = 0
    for _ in range(PERMUTATIONS):
        flipped = []
        for r in rows:
            if rng.random() < 0.5:
                flipped.append({"short_hr": r["long_hr"], "short_pa": r["long_pa"],
                                "long_hr": r["short_hr"], "long_pa": r["short_pa"]})
            else:
                flipped.append(r)
        if abs(_delta(flipped)) >= abs(obs):
            hits += 1
    return (hits + 1) / (PERMUTATIONS + 1)


def build() -> str:
    rows = collect()
    md = ["# Does a park's SHAPE add to its home-run factor?", "",
          "_`hr_pick` already multiplies by a park HR factor, but that is one "
          "number for the whole field and cannot express a left-handed pull "
          "hitter walking into a short right field. Within-hitter: each bat's "
          "own rate at short-pull-side parks against his own rate at long "
          "ones._", "",
          "_MLB's feed carries no batted-ball distance or coordinates, so this "
          "tests the cheap proxy - pull side from which way he bats. If the "
          "cheap version is worth nothing, a Statcast spray profile almost "
          "certainly is too._", ""]
    if not rows:
        return "\n".join(md + ["_No usable rows._"])
    d = _delta(rows)
    p = _perm_p(rows, d)
    sh = sum(r["short_hr"] for r in rows); sp = sum(r["short_pa"] for r in rows)
    lh = sum(r["long_hr"] for r in rows); lp = sum(r["long_pa"] for r in rows)
    md += [f"**{len(rows)} hitters**, {sp+lp:.0f} plate appearances.", "",
           "| pull-side fence | HR/PA | HR | PA |", "|---|---|---|---|",
           f"| short (below median) | {sh/sp:.3%} | {sh:.0f} | {sp:.0f} |",
           f"| long | {lh/lp:.3%} | {lh:.0f} | {lp:.0f} |", "",
           f"difference **{d:+.3%}** per PA — a multiplier of "
           f"**×{(sh/sp)/(lh/lp):.3f}** — permutation p = **{p:.4f}**", ""]
    for lab, s in (("left-handed", "L"), ("right-handed", "R")):
        sub = [r for r in rows if r["side"] == s]
        if len(sub) < 10:
            continue
        dd = _delta(sub)
        md.append(f"- {lab} bats ({len(sub)}): {dd:+.3%} per PA")
    md += ["", "## What to conclude", "",
           "- compare the multiplier against what the selector already swings: "
           "form ×1.30, wind ×1.24, park ×1.12. A shape term below about ×1.03 "
           "cannot change a pick and should not be wired",
           "- a null here also closes the expensive version, since a real "
           "spray profile refines the same effect this proxy is testing",
           ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    OUTPUT_DIR.mkdir(exist_ok=True)
    text = build()
    REPORT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
