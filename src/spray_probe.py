"""
Probe: can the HR pick use batted-ball distance, direction and park dimensions?

Three questions, each of which could kill its own half of the idea:

 1. does a per-play record carry hitData - totalDistance, coordinates, launch
    angle - so a hitter's typical fly ball can be placed on the field?
 2. does the venue endpoint serve FENCE DISTANCES by direction, so "pull-heavy
    lefty into a short right field" is computable rather than imagined?
 3. can home runs be attributed to a VENUE, for the "has he gone deep here
    before" question?

The existing model already has a park HR factor, so the only thing worth adding
is the INTERACTION - this hitter's spray against this park's shape. An aggregate
park factor already covers the rest.

Writes output/spray_probe.md.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from . import mlb_api

log = logging.getLogger("spray_probe")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    pid = int(os.environ.get("PROBE_BATTER") or 657757)
    season = 2026
    out = ["# Spray / park-dimension probe", ""]

    # --- 1. hitData on a per-play record
    out += ["## 1. Does a play record carry batted-ball data?", ""]
    try:
        d = mlb_api._get(f"people/{pid}/stats", stats="playLog",
                         group="hitting", season=season)
        sp = [s for b in (d.get("stats") or []) for s in (b.get("splits") or [])]
        out.append(f"playLog splits: {len(sp)}")
        inplay = [s for s in sp
                  if (((s.get("stat") or {}).get("play") or {})
                      .get("details") or {}).get("isInPlay")]
        out.append(f"balls in play: {len(inplay)}")
        if inplay:
            play = (inplay[0].get("stat") or {}).get("play") or {}
            out += ["", "keys on a ball-in-play `play`:", "```",
                    ", ".join(sorted(play.keys())), "```"]
            hd = play.get("hitData")
            if hd:
                out += ["**hitData IS present.**", "```",
                        json.dumps(hd, indent=1)[:700], "```"]
                have = sum(1 for s in inplay
                           if ((s.get("stat") or {}).get("play") or {}).get("hitData"))
                out.append(f"present on {have} of {len(inplay)} balls in play")
                dists = []
                for s in inplay:
                    h = (((s.get("stat") or {}).get("play") or {})
                         .get("hitData") or {})
                    try:
                        if h.get("totalDistance"):
                            dists.append(float(h["totalDistance"]))
                    except (TypeError, ValueError):
                        pass
                if dists:
                    dists.sort()
                    out.append(f"totalDistance: n={len(dists)} "
                               f"min={dists[0]:.0f} median={dists[len(dists)//2]:.0f} "
                               f"max={dists[-1]:.0f}")
                else:
                    out.append("**no totalDistance values** — distance is absent")
            else:
                out.append("**hitData ABSENT** — no distance or coordinates, so "
                           "spray cannot be computed from here")
    except Exception as exc:
        out.append(f"playLog failed: {exc}")

    # --- 2. fence distances per venue
    out += ["", "## 2. Does the venue endpoint serve fence distances?", ""]
    try:
        v = mlb_api._get("venues", season=season, hydrate="fieldInfo,location")
        venues = v.get("venues") or []
        out.append(f"venues returned: {len(venues)}")
        withfi = [x for x in venues if x.get("fieldInfo")]
        out.append(f"with fieldInfo: {len(withfi)}")
        if withfi:
            out += ["", "example:", "```",
                    json.dumps({k: withfi[0].get(k)
                                for k in ("id", "name", "fieldInfo")},
                               indent=1)[:800], "```"]
            keys = set()
            for x in withfi:
                keys |= set((x.get("fieldInfo") or {}).keys())
            out += ["fieldInfo keys across all venues:", "```",
                    ", ".join(sorted(keys)), "```"]
            dirs = ("leftLine", "left", "leftCenter", "center",
                    "rightCenter", "right", "rightLine")
            have = [k for k in dirs
                    if sum(1 for x in withfi
                           if (x.get("fieldInfo") or {}).get(k)) > 20]
            out.append(f"direction distances populated league-wide: "
                       f"{have or 'NONE'}")
    except Exception as exc:
        out.append(f"venues failed: {exc}")

    # --- 3. home runs attributable to a venue
    out += ["", "## 3. Can home runs be tied to a ballpark?", ""]
    try:
        gl = mlb_api._full_gamelog(pid, "hitting", season)
        out.append(f"gamelog games: {len(gl)}")
        if gl:
            out += ["split keys:", "```", ", ".join(sorted(gl[0].keys())), "```"]
            g0 = gl[0].get("game") or {}
            out += ["`game` keys:", "```", ", ".join(sorted(g0.keys())), "```",
                    "_a venue here would make it a one-line join; otherwise it "
                    "needs the schedule, which the board already fetches._"]
        hrg = [s for s in gl
               if float((s.get("stat") or {}).get("homeRuns", 0) or 0) > 0]
        out.append(f"games with a HR: {len(hrg)} — "
                   f"so 'has he gone deep at THIS park' is at most a handful "
                   f"per venue, which is the real constraint")
    except Exception as exc:
        out.append(f"gamelog failed: {exc}")

    # --- 4. Statcast, the only place distance and spray live
    out += ["", "## 4. Is Statcast (baseballsavant) reachable, and useful?", "",
            "_MLB's own feed carries no hitData, so spray and distance can only "
            "come from here. Checked for reachability AND for the fields that "
            "matter, since a 200 that returns a login page is still a dead "
            "end._", ""]
    import csv as _csv
    import io as _io
    targets = [
        ("batted-ball leaderboard",
         "https://baseballsavant.mlb.com/leaderboard/statcast"
         f"?type=batter&year={season}&position=&team=&min=q&csv=true"),
        ("expected stats leaderboard",
         "https://baseballsavant.mlb.com/leaderboard/expected_statistics"
         f"?type=batter&year={season}&position=&team=&min=q&csv=true"),
        ("per-batted-ball search",
         "https://baseballsavant.mlb.com/statcast_search/csv?all=true"
         f"&player_type=batter&batters_lookup%5B%5D={pid}"
         f"&hfSea={season}%7C&type=details"),
    ]
    for label, url in targets:
        try:
            resp = mlb_api.SESSION.get(url, timeout=60)
            ct = resp.headers.get("content-type", "")
            body = resp.text
            out.append(f"**{label}** — HTTP {resp.status_code}, "
                       f"{len(body)} bytes, content-type `{ct}`")
            if resp.status_code != 200 or "html" in ct.lower():
                out.append("  - not CSV; treat as unavailable")
                continue
            rows = list(_csv.reader(_io.StringIO(body)))
            if not rows:
                out.append("  - empty")
                continue
            hdr = rows[0]
            out.append(f"  - {len(rows)-1} data rows, {len(hdr)} columns")
            want = [c for c in hdr if any(k in c.lower() for k in (
                "distance", "angle", "launch", "pull", "oppo", "cent",
                "barrel", "hc_x", "hc_y", "spray"))]
            out += ["  - relevant columns: "
                    + (", ".join(f"`{c}`" for c in want[:18]) or "**none**")]
        except Exception as exc:
            out.append(f"**{label}** — request failed: {exc}")

    text = "\n".join(out)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "spray_probe.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
