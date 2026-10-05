"""
How often is this hitter pulled out of a game he started?

THE HARM
A hits prop needs plate appearances. A hitter lifted in the sixth got two, and
the prop was dead before first pitch. On 2026-10-04 the Braves did it twice in
one game: Murphy out after 2 PA, Thomas out after 2.

WHY THE EXISTING GATE MISSES IT
`props.MIN_AVG_PA` is a MEAN - 3.2 PA across the team wins he played in. A mean
cannot express "ever pinch-hit for": a hitter who finishes 85% of his starts and
is lifted in the other 15% averages about 4.0 and sails through, while being
exactly the risk worth avoiding. What matters is the SHARE of starts that end
early, not the average length of one.

HOW IT IS DETECTED
From the boxscore, not inferred from plate appearances. Every batter carries a
`battingOrder`: a starter's ends in "00" (100, 200 ... 900) and anyone who
replaces him in that slot gets the next number up with `isSubstitute` true. So
slot 7 reading 700 / 701 / 702 means the starter was replaced, and no guessing
from a short line is needed. A first attempt tried to infer it from PA and
returned 0.0% for all 414 hitters - including Murphy, who had been pulled the
day before - because it skipped games under 3 PA and then looked for games of 2
PA or fewer among what was left.

This counts ANY replacement in the slot, not only a pinch hitter: a pinch
runner or a defensive sub ends the starter's night just as finally, and kills a
hits prop just as completely.

COST
One request per game, so the tally is cached by gamePk and refreshed
incrementally - a full season once, then roughly fifteen boxscores a day. The
board calls `refresh()` before building props.

`risk()` returns None under MIN_STARTS, and the gate LETS THOSE THROUGH:
unknown is not risky, and a feed outage must not silently empty the board.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from . import mlb_api

log = logging.getLogger("pinch_risk")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
CACHE = OUTPUT_DIR / "pinch_risk_cache.json"
REPORT = OUTPUT_DIR / "pinch_risk.md"

MIN_STARTS = 20        # starts before a rate is worth acting on
SEASON_START = "03/01"


def _load() -> dict:
    try:
        d = json.loads(CACHE.read_text())
        d.setdefault("games", [])
        d.setdefault("tally", {})
        return d
    except (OSError, ValueError):
        return {"games": [], "tally": {}}


def _save(cache: dict) -> None:
    try:
        CACHE.write_text(json.dumps(cache))
    except OSError as exc:
        log.warning("pinch-risk cache not written (%s)", exc)


def _scan(game_pk: int, tally: dict) -> bool:
    """Add one final game's starters to the tally. False if it could not be read.

    A starter is battingOrder ending "00" with isSubstitute false; he was pulled
    if any other entry shares his slot (the same leading digit).
    """
    try:
        bs = mlb_api._get(f"game/{game_pk}/boxscore")
    except Exception as exc:
        log.warning("boxscore %s unavailable (%s)", game_pk, exc)
        return False
    for side in ("away", "home"):
        players = ((bs.get("teams") or {}).get(side) or {}).get("players") or {}
        slots: dict[str, list[tuple[int, int, bool]]] = {}
        for p in players.values():
            bo = p.get("battingOrder")
            pid = (p.get("person") or {}).get("id")
            if not bo or not pid:
                continue
            try:
                n = int(bo)
            except (TypeError, ValueError):
                continue
            sub = bool((p.get("gameStatus") or {}).get("isSubstitute"))
            slots.setdefault(str(n // 100), []).append((n, pid, sub))
        for entries in slots.values():
            entries.sort()
            n, pid, sub = entries[0]
            if n % 100 != 0 or sub:
                continue                    # not a starter; skip the slot
            cell = tally.setdefault(str(pid), [0, 0])
            cell[1] += 1                                   # a start
            if len(entries) > 1:
                cell[0] += 1                               # and he was replaced
    return True


def refresh(through: str, limit: int | None = None) -> dict:
    """Bring the cache up to the day before `through` (YYYY-MM-DD).

    Only FINAL games are scanned, and each gamePk is scanned once, so calling
    this on every board build costs one request per newly finished game.
    """
    cache = _load()
    done = set(cache["games"])
    season = through[:4]
    try:
        sched = mlb_api._get("schedule", sportId=1, gameType="R,P",
                             startDate=f"{SEASON_START}/{season}",
                             endDate=f"{through[5:7]}/{through[8:10]}/{season}")
    except Exception as exc:
        log.warning("schedule for pinch risk unavailable (%s)", exc)
        return cache
    pks = []
    for d in sched.get("dates", []):
        if (d.get("date") or "") >= through:
            continue                      # never let today inform today
        for g in d.get("games", []):
            state = ((g.get("status") or {}).get("abstractGameState") or "")
            if state == "Final" and g.get("gamePk") not in done:
                pks.append(g["gamePk"])
    if limit:
        pks = pks[:limit]
    added = 0
    for pk in pks:
        if _scan(pk, cache["tally"]):
            cache["games"].append(pk)
            added += 1
    if added:
        log.info("pinch risk: scanned %d new boxscore(s)", added)
        _save(cache)
    return cache


def risk(pid: int, cache: dict | None = None) -> dict | None:
    """{"rate", "pulled", "starts"} or None when the sample is too thin."""
    cache = _load() if cache is None else cache
    cell = (cache.get("tally") or {}).get(str(pid))
    if not cell or cell[1] < MIN_STARTS:
        return None
    pulled, starts = cell
    return {"rate": pulled / starts, "pulled": pulled, "starts": starts}


# --- the report the threshold is set from -------------------------------------
def build(through: str) -> str:
    cache = refresh(through)
    names = {}
    tally = cache.get("tally") or {}
    ids = [int(p) for p, c in tally.items() if c[1] >= MIN_STARTS]
    for i in range(0, len(ids), 100):
        try:
            for pe in mlb_api._get("people", personIds=",".join(
                    str(x) for x in ids[i:i + 100])).get("people", []):
                names[pe["id"]] = pe.get("fullName")
        except Exception as exc:
            log.warning("name lookup failed (%s)", exc)
    rows = [(names.get(i, str(i)), risk(i, cache)) for i in ids]
    rows = [(n, r) for n, r in rows if r]
    md = [f"# How often is a hitter pulled from a game he started? — {through[:4]}",
          "",
          "_From the boxscore: a starter's `battingOrder` ends in 00, and "
          "anyone replacing him in that slot gets the next number up. Counts "
          "any replacement - pinch hitter, pinch runner or defensive sub - "
          "since each ends his night and kills a hits prop equally._", "",
          f"Games scanned: **{len(cache.get('games') or [])}** · "
          f"hitters with {MIN_STARTS}+ starts: **{len(rows)}**", ""]
    if not rows:
        return "\n".join(md + ["_No usable rows yet._"])
    rates = sorted(r["rate"] for _, r in rows)
    def q(p):
        return rates[int(p * (len(rates) - 1))]
    md += ["| percentile | pulled-from-start rate |", "|---|---|"]
    for p in (0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99):
        md.append(f"| p{int(p*100)} | {q(p):.1%} |")
    md += ["", "## Worst 25 — what the gate has to catch", "",
           "| hitter | pulled | starts | rate |", "|---|---|---|---|"]
    for n, r in sorted(rows, key=lambda x: -x[1]["rate"])[:25]:
        md.append(f"| {n} | {r['pulled']} | {r['starts']} | **{r['rate']:.1%}** |")
    md += ["", "## The two from 2026-10-04", ""]
    for want in ("Sean Murphy", "Lane Thomas", "Ozzie Albies",
                 "Matt Olson", "Ronald Acu"):
        for n, r in rows:
            if want in (n or ""):
                md.append(f"- {n}: {r['pulled']}/{r['starts']} "
                          f"= **{r['rate']:.1%}**")
    md += ["", "## Reading it", "",
           "- set the gate against the median, not a round number: it has to "
           "catch the pulled bats without condemning ordinary hitters",
           "- Albies, Olson and Acuña are printed as controls — they are the "
           "everyday bats the gate must NOT touch",
           "- a hitter under MIN_STARTS returns None and is let through",
           ""]
    return "\n".join(md)


def main() -> None:
    import datetime as dt
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    OUTPUT_DIR.mkdir(exist_ok=True)
    text = build(dt.date.today().isoformat())
    REPORT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
