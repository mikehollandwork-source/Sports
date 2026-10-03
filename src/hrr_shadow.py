"""
Shadow book: hits+runs+RBIs OVER 1.5 on the hitter the board already posts.

NOTHING HERE IS BET. This is a watch log, like good_dog and line_money, kept in
its OWN ledger so it can never touch the prop record or the moneyline record.

WHY IT EXISTS
The posted 1+ hit prop has gone 89-53 - a 62.7% hit rate - for -8.63u, because at
its median -200 the break-even is 66.7%. The hit rate was never the problem;
paying through it was. H+R+RBI over 1.5 was quoted at +105 on 2026-10-03, a 48.8%
break-even: the same hitter read with 16 points less hold to overcome.

WHY IT IS SHADOWED AND NOT BET
It CANNOT be back-tested. The cached odds only ever held batter_hits, so no
historical H+R+RBI price exists anywhere in this repo. There is no evidence the
read transfers - H+R+RBI is a DIFFERENT event, whose run and RBI components depend
on teammates, while the selector estimates P(he gets a hit). A lower break-even is
less hold, not an edge. So it accumulates forward evidence and is left alone.

GRADING
H + R + RBI >= 2 wins. Taken from the boxscore batting line, one fetch per game.
A player who did not bat is skipped, not scored - it would have been a void, not
a loss.

Writes output/hrr_shadow_ledger.json and output/hrr_shadow.md.
"""

from __future__ import annotations

import glob
import json
import logging
import statistics as st
from pathlib import Path

import requests

from . import apitime, grade, mlb_api

log = logging.getLogger("hrr_shadow")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
LEDGER = OUTPUT_DIR / "hrr_shadow_ledger.json"
STAKE = 1.0
TIMEOUT = 20


def _line(game_pk: int, player_id: int) -> dict | None:
    """{"h","r","rbi","pa"} for one batter, or None when he did not bat."""
    try:
        with apitime.timed("mlb", f"box/{game_pk}"):
            box = requests.get(
                f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore",
                timeout=TIMEOUT).json()
    except Exception as exc:
        log.warning("boxscore %s failed: %s", game_pk, exc)
        return None
    for side in ("home", "away"):
        p = ((box.get("teams", {}).get(side, {}).get("players")) or {}).get(
            f"ID{player_id}")
        if not p:
            continue
        bat = (p.get("stats", {}) or {}).get("batting", {}) or {}
        try:
            pa = int(bat.get("plateAppearances", 0) or 0)
        except (TypeError, ValueError):
            pa = 0
        if pa < 1:
            return None
        return {"h": int(bat.get("hits", 0) or 0),
                "r": int(bat.get("runs", 0) or 0),
                "rbi": int(bat.get("rbi", 0) or 0), "pa": pa}
    return None


def _load() -> dict:
    try:
        return json.loads(LEDGER.read_text())
    except (OSError, ValueError):
        return {"stake": STAKE, "market": "hits+runs+RBIs over 1.5",
                "bet": False, "entries": []}


def settle(dates: list[str] | None = None) -> int:
    """Grade every shadow entry on final games. Idempotent, keyed by date#pk."""
    book = _load()
    have = {e["key"] for e in book["entries"]}
    added = 0
    files = (sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json")))
             if dates is None else
             [str(OUTPUT_DIR / f"picks_{d}.json") for d in dates])
    for f in files:
        date = Path(f).stem.split("picks_")[1]
        try:
            board = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        shadows = [(g, (g.get("pick_criteria") or {}).get("shadow_hrr"))
                   for g in board.get("games", [])]
        shadows = [(g, s) for g, s in shadows if s and s.get("player_id")]
        if not shadows:
            continue
        try:
            res = mlb_api.results_for(date)
        except Exception as exc:
            log.warning("results unavailable for %s: %s", date, exc)
            continue
        for g, sh in shadows:
            pk = g.get("game_pk")
            key = f"{date}#{pk}"
            if key in have:
                continue
            r = res.get(pk) or {}
            if not r.get("final"):
                continue
            line = _line(pk, sh["player_id"])
            if line is None:
                continue                      # did not bat: a void, not a loss
            total = line["h"] + line["r"] + line["rbi"]
            won = total >= 2
            odds = int(sh["over"])
            book["entries"].append({
                "key": key, "date": date, "matchup": g.get("matchup"),
                "bet": f"{sh['player']} H+R+RBI o1.5 (SHADOW, not bet)",
                "result": "W" if won else "L", "total": total,
                "line": f"{line['h']}H {line['r']}R {line['rbi']}RBI",
                "odds": odds,
                "profit": round(grade.american_profit(odds) if won else -STAKE, 2)})
            have.add(key)
            added += 1
    book["entries"].sort(key=lambda e: e["key"])
    run = 0.0
    for e in book["entries"]:
        run = round(run + e["profit"], 2)
        e["bankroll_after"] = run
    w = sum(1 for e in book["entries"] if e["result"] == "W")
    book["record"] = {"wins": w, "losses": len(book["entries"]) - w,
                      "bets": len(book["entries"])}
    OUTPUT_DIR.mkdir(exist_ok=True)
    LEDGER.write_text(json.dumps(book, indent=1))
    return added


def report() -> str:
    book = _load()
    e = book["entries"]
    md = ["# Shadow book — hits+runs+RBIs over 1.5", "",
          "_**Nothing here is bet.** Its own ledger, so it can never touch the "
          "prop record or the moneyline record._", "",
          "_Why: the posted 1+ hit prop is 89-53 (62.7%) for -8.63u, because at "
          "its median -200 the break-even is 66.7%. H+R+RBI over 1.5 quoted +105, "
          "a 48.8% break-even - the same read with 16 points less hold. It cannot "
          "be back-tested (those prices were never captured), and it is a "
          "DIFFERENT event whose run and RBI parts depend on teammates, so this "
          "accumulates forward evidence instead of being acted on._", ""]
    if not e:
        return "\n".join(md + ["No graded shadow entries yet.", ""])
    w = sum(1 for x in e if x["result"] == "W")
    u = sum(x["profit"] for x in e)
    od = [x["odds"] for x in e]
    med = st.median(od)
    be = abs(med) / (abs(med) + 100) if med < 0 else 100 / (med + 100)
    md += [f"- **{w}-{len(e)-w}** = {w/len(e):.1%} · **{u:+.2f}u** · "
           f"ROI {u/len(e):+.1%}",
           f"- median price **{med:+.0f}** (break-even **{be:.1%}**) → "
           f"**{(w/len(e)-be)*100:+.1f} points**", "",
           "| date | hitter | line | H+R+RBI | price | result | units |",
           "|---|---|---|---|---|---|---|"]
    for x in e[-25:]:
        who = x["bet"].split(" H+R+RBI")[0]
        md.append(f"| {x['date']} | {who} | {x['line']} | {x['total']} "
                  f"| {x['odds']:+d} | {x['result']} | {x['profit']:+.2f} |")
    md += ["", f"_{len(e)} graded. A meaningful read needs roughly 50; before "
           "that this table is a record, not a verdict._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    n = settle()
    log.info("hrr shadow: %d new entry(ies)", n)
    md = report()
    (OUTPUT_DIR / "hrr_shadow.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
