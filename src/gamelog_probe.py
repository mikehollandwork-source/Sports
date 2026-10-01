"""
Probe: does the hitting gameLog return POSTSEASON games?

WHY
On 2026-10-01 every Braves hitter's log stopped at 09-27, yet the team played
09-29 and 09-30 (both final on their boards). `props._game_log` requests
`stats=gameLog&group=hitting&season=<yr>` with no gameType, and the suspicion is
that this returns REGULAR SEASON only - which would freeze every form number in
the project at the end of the regular season.

That matters well beyond one report: `props.hit_in_wins_ranked` is what produces
the board's `form`, its LIKELY HITS block and the prop ledger.

Prints the last dates returned for each gameType so the answer is visible rather
than assumed. Writes output/gamelog_probe.md.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from . import mlb_api

log = logging.getLogger("gamelog_probe")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def dates_for(player_id: int, season: int, game_type: str | None) -> list[str]:
    kw = {"stats": "gameLog", "group": "hitting", "season": season}
    if game_type:
        kw["gameType"] = game_type
    try:
        data = mlb_api._get(f"people/{player_id}/stats", **kw)
    except Exception as exc:
        log.warning("fetch failed (%s, %s): %s", player_id, game_type, exc)
        return []
    out = []
    for s in (data.get("stats") or [{}])[0].get("splits", []) or []:
        d = s.get("date")
        st = s.get("stat") or {}
        if d:
            out.append(f"{d} {st.get('hits', '?')}-{st.get('atBats', '?')}")
    return sorted(out)


def team_dates(team_id: int, season: int, game_type: str | None) -> dict:
    """{group: [dates]} from the TEAM gameLog endpoint, which is a different
    endpoint with a different parameter set - it must be checked separately
    before anything relies on gameType working there."""
    kw = {"stats": "gameLog", "group": "hitting,pitching", "season": season}
    if game_type:
        kw["gameType"] = game_type
    try:
        data = mlb_api._get(f"teams/{team_id}/stats", **kw)
    except Exception as exc:
        return {"ERROR": [str(exc)]}
    out: dict = {}
    for st in data.get("stats", []):
        grp = st.get("group", {}).get("displayName", "?")
        out.setdefault(grp, []).extend(
            sp.get("date") for sp in st.get("splits", []) if sp.get("date"))
    return {k: sorted(v) for k, v in out.items()}


def build(player_id: int, name: str, season: int, team_id: int = 0) -> str:
    md = [f"# gameLog probe — {name} ({player_id}), {season}", "",
          "_Does the hitting gameLog include postseason games?_", ""]
    for label, gt in (("no gameType (what props._game_log sends)", None),
                      ("gameType=R (regular season)", "R"),
                      ("gameType=P (postseason)", "P"),
                      ("gameType=R,P (both)", "R,P")):
        ds = dates_for(player_id, season, gt)
        md += [f"## {label}", "",
               f"- games returned: **{len(ds)}**",
               f"- last 6: {' · '.join(ds[-6:]) if ds else '—'}", ""]
    if team_id:
        md += ["# TEAM gameLog endpoint", "",
               "_Different endpoint. The advantage metric's last-5 wOBA/ISO/FIP "
               "comes through here, so gameType must be confirmed to work before "
               "anything depends on it._", ""]
        for label, gt in (("no gameType (what _team_gamelog sends)", None),
                          ("gameType=R", "R"), ("gameType=P", "P"),
                          ("gameType=R,P", "R,P")):
            res = team_dates(team_id, season, gt)
            md += [f"## team: {label}", ""]
            for grp, ds in res.items():
                md.append(f"- **{grp}**: {len(ds)} game(s), last 4: "
                          f"{' · '.join(ds[-4:]) if ds else '—'}")
            md.append("")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--player", type=int,
                    default=int(os.environ.get("PROBE_PLAYER") or 0))
    ap.add_argument("--name", default=os.environ.get("PROBE_NAME") or "player")
    ap.add_argument("--season", type=int,
                    default=int(os.environ.get("PROBE_SEASON") or 2026))
    a = ap.parse_args()
    if not a.player:
        print("pass --player <mlb id>")
        return
    md = build(a.player, a.name, a.season,
               int(os.environ.get("PROBE_TEAM") or 0))
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "gamelog_probe.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
