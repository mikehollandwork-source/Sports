"""
Do hitters on the WINNING team homer more often than hitters on the losing team?

THE QUESTION
The hit props showed a 1.4-point edge to the losing side - 62.5% vs 63.9% - which
I called noise at the time and which checks out: an 8.2-point standard error,
p = 0.86. The question now is whether the same intuition should steer the HOME RUN
pick to the opposing lineup.

THE PRIOR POINTS THE OTHER WAY. A single barely moves a game, so hits and winning
are nearly independent. A home run SCORES RUNS, so home runs and winning should be
POSITIVELY correlated by construction - the event is part of the thing that
decides the outcome. If so, picking from the side expected to LOSE is picking
against the correlation.

This measures it instead of assuming it, on every batter in every board game:
HR per plate appearance for hitters whose team won against hitters whose team
lost. Thousands of player-games, which is the one place this project has a big
enough sample to settle something.

A batter who did not bat is skipped. One boxscore per game.

Writes output/hr_side_scan.md.
"""

from __future__ import annotations

import glob
import json
import logging
import math
from pathlib import Path

import requests

from . import apitime, mlb_api

log = logging.getLogger("hr_side_scan")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TIMEOUT = 20


def _box_rows(game_pk: int) -> list[dict]:
    """One row per batter with a PA: {team, pa, hr, ab, hits}."""
    out = []
    try:
        with apitime.timed("mlb", f"box/{game_pk}"):
            box = requests.get(
                f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore",
                timeout=TIMEOUT).json()
    except Exception as exc:
        log.warning("boxscore %s failed: %s", game_pk, exc)
        return out
    for side in ("home", "away"):
        team = ((box.get("teams", {}).get(side, {}) or {}).get("team") or {})
        for p in ((box["teams"][side].get("players")) or {}).values():
            bat = (p.get("stats", {}) or {}).get("batting", {}) or {}
            try:
                pa = int(bat.get("plateAppearances", 0) or 0)
            except (TypeError, ValueError):
                pa = 0
            if pa < 1:
                continue
            out.append({"team": team.get("name", ""), "pa": pa,
                        "hr": int(bat.get("homeRuns", 0) or 0),
                        "ab": int(bat.get("atBats", 0) or 0),
                        "hits": int(bat.get("hits", 0) or 0)})
    return out


def collect() -> list[dict]:
    rows = []
    seen = set()
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            board = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        try:
            res = mlb_api.results_for(date)
        except Exception:
            continue
        for g in board.get("games", []):
            pk = g.get("game_pk")
            if not pk or pk in seen:
                continue
            r = res.get(pk) or {}
            w = r.get("winner")
            if not r.get("final") or not w:
                continue
            seen.add(pk)
            for b in _box_rows(pk):
                if not b["team"]:
                    continue
                rows.append({**b, "won": b["team"] == w, "date": date})
    return rows


def build() -> str:
    rows = collect()
    md = ["# Do winners homer more than losers?", "",
          "_Every batter with a plate appearance in every board game. The hit "
          "props' 1.4-point lean to the losing side was noise (SE 8.2 points, "
          "p = 0.86); a home run is a different event because it SCORES, so the "
          "prior says winners should homer more._", ""]
    if len(rows) < 500:
        return "\n".join(md + [f"Only {len(rows)} batter-games.", ""])
    win = [r for r in rows if r["won"]]
    lose = [r for r in rows if not r["won"]]

    def rate(rs, key="hr"):
        pa = sum(r["pa"] for r in rs)
        return (sum(r[key] for r in rs) / pa if pa else 0.0), pa

    hw, paw = rate(win)
    hl, pal = rate(lose)
    md += [f"- batter-games: **{len(rows)}** over {len({r['date'] for r in rows})} dates",
           "", "| side | batter-games | PA | HR | HR per PA |", "|---|---|---|---|---|",
           f"| team **WON** | {len(win)} | {paw} | {sum(r['hr'] for r in win)} "
           f"| **{hw:.2%}** |",
           f"| team **LOST** | {len(lose)} | {pal} | {sum(r['hr'] for r in lose)} "
           f"| **{hl:.2%}** |", ""]
    se = math.sqrt(hw * (1 - hw) / paw + hl * (1 - hl) / pal)
    z = (hw - hl) / se if se else 0.0
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    md += [f"- winners homer **{(hw-hl)*100:+.2f} points per PA** more "
           f"(a **{hw/hl if hl else 0:.2f}x** rate)",
           f"- standard error {se*100:.2f} points · z = {z:+.1f} · "
           f"**p = {p:.2e}**" if p < 1e-4 else
           f"- standard error {se*100:.2f} points · z = {z:+.1f} · **p = {p:.4f}**",
           ""]
    # the same split for HITS, as the control the hit-prop question asked about
    ahw, _ = rate(win, "hits")
    ahl, _ = rate(lose, "hits")
    md += ["## For contrast, the same split on HITS", "",
           f"- team won: **{ahw:.2%}** hits per PA · team lost: **{ahl:.2%}**",
           f"- difference **{(ahw-ahl)*100:+.2f} points**, against "
           f"{(hw-hl)*100:+.2f} for home runs", "",
           "_Hits barely separate the two sides; home runs separate them sharply, "
           "because a home run is part of what makes a team the winner._", ""]
    md += ["## What this means for the board", "",
           ("- **Pick from the side you expect to WIN.** Taking the home run from "
            "the opposing lineup bets against a correlation this strong."
            if hw > hl else
            "- the losing side homers more, which is the opposite of the prior "
            "and worth a second look before anything is acted on"), "",
           "_This is a measurement of the BASE RATE, not of our selection. It "
           "says which side to draw from; it does not say the model picks the "
           "right bat, and the home-run book still has no graded entries._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "hr_side_scan.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
