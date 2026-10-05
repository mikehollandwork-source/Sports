"""
One-off: write `game_type` onto saved boards that predate the field.

`good_dog` now refuses to tag postseason games, because with only good teams
left the favourite-rate condition stops discriminating (92% of the teams still
playing clear it, against 47% league-wide). But the tag's RECORD is rebuilt by
walking saved boards, and boards written before the field existed read as
regular season - so fifteen already-tagged October games would keep counting as
evidence for a tag that cannot mean there what it means in June.

This adds the field and nothing else. It does not touch any ledger, any price,
or any pick - the tag has never been a bet. Boards that already carry the field
are left alone, and a date whose schedule cannot be fetched is skipped rather
than guessed at.

Idempotent: safe to re-run.
"""

from __future__ import annotations

import glob
import json
import logging
from pathlib import Path

from . import mlb_api

log = logging.getLogger("backfill_gametype")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    changed = skipped = already = 0
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        path = Path(f)
        date = path.stem.split("picks_")[1]
        try:
            day = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        games = day.get("games") or []
        if not games or all("game_type" in g for g in games):
            already += 1
            continue
        try:
            sched = mlb_api._get("schedule", sportId=1, date=date)
        except Exception as exc:
            log.warning("%s: schedule unavailable (%s) - skipped", date, exc)
            skipped += 1
            continue
        types = {}
        for d in sched.get("dates") or []:
            for g in d.get("games") or []:
                types[g.get("gamePk")] = g.get("gameType") or "R"
        hit = 0
        for g in games:
            gt = types.get(g.get("game_pk"))
            if gt and "game_type" not in g:
                g["game_type"] = gt
                hit += 1
        if hit:
            # indent=2, matching main.py:1473 - writing indent=1 here would
            # reformat every board into a diff thousands of lines long
            path.write_text(json.dumps(day, indent=2))
            changed += 1
            post = sum(1 for g in games if g.get("game_type") in ("F","D","L","W","P"))
            log.info("%s: typed %d game(s), %d postseason", date, hit, post)
    log.info("boards changed %d, already typed %d, skipped %d",
             changed, already, skipped)


if __name__ == "__main__":
    main()
