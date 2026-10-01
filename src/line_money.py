"""
The "line against the money" tag: the price moved AWAY from where the dollars are.

WATCHING, NOT BETTING - AND THE REASON MATTERS
This tag changes no pick. It is here so forward evidence accumulates on the one
candidate that survived everything thrown at it, because nothing computable on
the data already in hand can finish the job.

WHAT THE BACKTEST FOUND (`line_vs_money.md`, `line_money_walk.md`)
When the line moves against the handle, backing the dollars went 209-146
(+5.3%, n=355) while backing the line side went 146-209 (-11.6%). Against the
games where line and handle AGREE (228-173, -4.2%) the difference is +10.5
points. It is spread through time - 6 of 8 ten-day blocks profitable, median
+10.2% - and a threshold chosen on past blocks only, scored on the next, still
returned +8.4% (30-21, n=51).

It also has a mechanism, which most of the ~50 candidates tested here did not:
a book repricing against its own money is acting on information the handle does
not reflect, and the public dollars are the side being taken.

WHY IT IS STILL NOT A BET
- The 95% CI on that +10.5 is **-4.8 to +25.5**. It spans zero.
- The effect SHRANK as data grew: +17.3% at n=55 became +5.3% at n=355.
- The cell was chosen out of roughly twenty configurations scanned over this
  same data, so its p = 0.043 is uncorrected; across twenty cells it is ~0.57.

The third point is the one that cannot be fixed by a better test. Every day of
data available here was already visible when the cell was picked, so no holdout,
block scheme or bootstrap on it is genuinely out-of-sample. Only games played
AFTER the tag ships can settle it. Hence a tag.

THE DEFINITION, PRE-REGISTERED
`implied_shift` is signed toward the advantage side, so its sign names the team
the price moved toward. The tag fires when that team is NOT the handle's money
side and the move is at least MOVE_MIN. The flagged side is the MONEY side.

Both bars are registered NOW, before any forward game is graded: MOVE_MIN at
1%, the original bar from `line_vs_money`, and STRONG at 3%, the bar the
out-of-sample procedure chose in 6 of 8 blocks. Recording both from the start
means the "which bar" question can be answered later from forward games without
re-running a selection over them - which is the trap this project keeps hitting.
Do not re-tune either number against the forward record.
"""

from __future__ import annotations

import glob
import json
import logging
from pathlib import Path

from . import grade, mlb_api

log = logging.getLogger("line_money")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
CACHE = OUTPUT_DIR / "line_money_cache.json"
MOVE_MIN = 0.01
STRONG = 0.03
# Forward evidence starts here. Boards before this date are the data the cell was
# selected on; counting them would restate the backtest and call it a record.
SHIPPED = "2026-10-01"


def tag(game: dict) -> dict | None:
    """{"team", "odds", "move", "strong", "line_team"} or None.

    Pure - reads only this game's own board fields, no history and no network, so
    it cannot fail a board build or shift under a team's later results.
    """
    m = game.get("matchup") or ""
    pc = game.get("pick_criteria") or {}
    chk = game.get("public_check") or {}
    adv = pc.get("advantage_team")
    a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
    shift = (pc.get("line_check") or {}).get("implied_shift")
    ms = chk.get("money_side")
    if " @ " not in m or not adv or not isinstance(a_ml, int) \
            or not isinstance(o_ml, int) or not isinstance(shift, (int, float)) \
            or ms not in ("home", "away"):
        return None
    away, home = m.split(" @ ")
    if adv not in (away, home):
        return None
    opp = home if adv == away else away
    price = {adv: a_ml, opp: o_ml}
    money_team = home if ms == "home" else away
    if money_team not in price:
        return None
    if abs(shift) < MOVE_MIN:
        return None
    line_team = adv if shift > 0 else opp          # abs(shift) >= MOVE_MIN > 0
    if line_team == money_team:
        return None                                # line and handle agree
    return {"team": money_team, "odds": price[money_team],
            "move": round(abs(shift), 4), "strong": abs(shift) >= STRONG,
            "line_team": line_team}


def _load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return {"days": {}}


def record(before: str) -> dict:
    """Forward record of the tag: {"all": [w, l, units], "strong": [...]}.

    Grades EVERY tagged game from SHIPPED onward, including ones the consensus
    rule also played. The candidate is "when the line fights the money, back the
    money" - a claim about the condition, not about the rule's leftovers - so
    excluding the overlap would measure something else.

    Days are cached once fully final, for the same reason good_dog.splits does
    it: a board built mid-afternoon must not freeze the day half-graded.

    Fails soft - an unfetchable date is skipped, so the board prints without the
    record rather than not printing.
    """
    cache = _load_cache()
    days = cache.setdefault("days", {})
    dirty = False
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        if date < SHIPPED or date >= before or date in days:
            continue
        try:
            day = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        tagged = [(g, t) for g in day.get("games", []) if (t := tag(g))]
        if not tagged:
            days[date] = []
            dirty = True
            continue
        try:
            res = mlb_api.results_for(date)
        except Exception as exc:
            log.warning("record: results unavailable for %s (%s)", date, exc)
            continue
        if not res or not all(v.get("final") for v in res.values()):
            continue                               # don't freeze a half-played day
        rows = []
        for g, t in tagged:
            r = res.get(g.get("game_pk")) or {}
            w = r.get("winner")
            if not r.get("final") or not w:
                continue
            rows.append({"won": w == t["team"], "odds": t["odds"],
                         "strong": t["strong"]})
        days[date] = rows
        dirty = True
    if dirty:
        try:
            CACHE.write_text(json.dumps(cache))
        except OSError as exc:
            log.warning("record: cache not written (%s)", exc)

    out = {"all": [0, 0, 0.0], "strong": [0, 0, 0.0]}
    for date, rows in days.items():
        if date < SHIPPED or date >= before:
            continue
        for r in rows:
            u = grade.american_profit(r["odds"]) if r["won"] else -1.0
            for key in ("all",) + (("strong",) if r["strong"] else ()):
                cell = out[key]
                cell[0 if r["won"] else 1] += 1
                cell[2] = round(cell[2] + u, 2)
    return out


def record_text(rec: dict) -> str:
    """'tag so far 4-3 (+1.20u, +17.1%)  ·  ≥3% 2-1', or '' before anything
    settles. Phrased as a tally, never as a recommendation."""
    w, l, u = rec["all"]
    if not (w + l):
        return ""
    parts = [f"tag so far {w}-{l} ({u:+.2f}u, {u/(w+l):+.1%})"]
    sw, sl, su = rec["strong"]
    if sw + sl:
        parts.append(f"of those, ≥{STRONG:.0%} moves {sw}-{sl} ({su:+.2f}u)")
    return "  ·  ".join(parts)
