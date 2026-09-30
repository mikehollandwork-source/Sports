"""
When the tickets flip late and the money does not, who wins?

THE OBSERVATION
On 2026-09-30 the Boston/Yankees game read "with public" from 04:05 to 21:03 -
handle and tickets both on the Yankees, money climbing 60% to 76%. At 22:03 the
TICKET majority flipped to Boston while the money stayed on the Yankees at 76%.
The rule's first gate then failed and the game was passed on.

That is a specific, mechanical event: a pile of small late bets landing on the
other side while the dollars do not move. The rule treats it as a reason to sit
out. This asks whether that is right, and what actually happens.

WHAT IS DETECTED
Walking every committed version of every board, a game counts as a LATE TICKET
FLIP when, in versions before its own lock:

    an earlier version says money == "with public"
    a later version says money == "against public"
    and the money SIDE is the same in both

That last clause is what makes it the tickets moving rather than the money. A
game where the money side itself changed is a different event and is counted
separately.

WHAT IS MEASURED
For each flipped game: did the MONEY side win, and did backing it pay? Against
a control of games that stayed "with public" from first sight to lock - the
population the rule actually bets.

The flip side is also priced, since "sit out" is only correct if BOTH sides are
bad. If the money side still wins these, the gate is throwing away good bets.

Needs full git history (fetch-depth: 0) and the MLB API, so it runs in Actions.
Writes output/ticket_flip.md.
"""

from __future__ import annotations

import datetime as dt
import glob
import logging
import random
from collections import defaultdict
from pathlib import Path

from . import grade, mlb_api
from .fade_profile import _at, _versions
from .pregame_money import _implied

log = logging.getLogger("ticket_flip")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 10000
LOCK_LEAD = dt.timedelta(minutes=15)


def collect() -> tuple[list[dict], int]:
    rows, with_history = [], 0
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        rel = f"output/picks_{date}.json"
        shas = _versions(rel)
        if len(shas) < 2:
            continue
        with_history += 1
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        seq: dict = defaultdict(list)
        meta: dict = {}
        for sha in shas:
            day = _at(sha, rel)
            if not day:
                continue
            stamp = day.get("generated_at") or ""
            for g in day.get("games", []):
                pk = g.get("game_pk")
                chk = g.get("public_check") or {}
                pc = g.get("pick_criteria") or {}
                start = g.get("game_datetime")
                if start:
                    try:
                        cut = (dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
                               - LOCK_LEAD)
                        if stamp and dt.datetime.fromisoformat(stamp) > cut:
                            continue          # after the lock: not actionable
                    except ValueError:
                        pass
                seq[pk].append({
                    "money": chk.get("money"), "side": chk.get("money_side"),
                    "maj": (g.get("public_majority") or {}).get("team"),
                })
                meta.setdefault(pk, {})
                if pc.get("advantage_team"):
                    meta[pk] = {"matchup": g.get("matchup"),
                                "adv": pc.get("advantage_team"),
                                "a_ml": pc.get("advantage_moneyline"),
                                "o_ml": pc.get("opponent_moneyline")}
        for pk, states in seq.items():
            res = results.get(pk)
            m = meta.get(pk) or {}
            if not res or not res.get("final") or not res.get("winner"):
                continue
            mt, adv = m.get("matchup"), m.get("adv")
            a_ml, o_ml = m.get("a_ml"), m.get("o_ml")
            if not mt or " @ " not in mt or not adv \
                    or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            away, home = mt.split(" @ ")
            if adv not in (away, home):
                continue
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            withs = [s for s in states if s["money"] == "with public"]
            against = [s for s in states if s["money"] == "against public"]
            if not withs:
                continue
            first_with = states.index(withs[0])
            later_against = [i for i, s in enumerate(states)
                             if s["money"] == "against public" and i > first_with]
            # the money side as it stood while they agreed
            money_team = None
            ms = withs[0].get("side")
            if ms in ("home", "away"):
                money_team = home if ms == "home" else away
            if not money_team or money_team not in price:
                continue
            if later_against:
                s2 = states[later_against[-1]]
                same_side = s2.get("side") == ms
                kind = "ticket flip" if same_side else "money side moved"
            else:
                kind = "stayed agreed" if not against else "other"
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0:
                continue
            rows.append({
                "date": date, "kind": kind, "money_team": money_team,
                "odds": price[money_team],
                "won": res["winner"] == money_team,
                "p": _implied(price[money_team]) / tot,
                "opp_odds": price[opp if money_team == adv else adv],
                "opp_won": res["winner"] != money_team,
            })
    return rows, with_history


def _roi(rs, odds="odds", won="won") -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r[odds]) if r[won] else -1 for r in rs) / len(rs)


def _fmt(rs, odds="odds", won="won") -> str:
    if not rs:
        return "—"
    w = sum(1 for r in rs if r[won])
    return f"{w}-{len(rs)-w} · **{_roi(rs, odds, won):+.1%}** (n={len(rs)})"


def build() -> str:
    rows, hist = collect()
    md = ["# When the tickets flip late and the money does not, who wins?", "",
          "_On 2026-09-30 Boston/Yankees read \"with public\" from 04:05 to 21:03 — "
          "handle and tickets both on the Yankees, money climbing 60% to 76%. At "
          "22:03 the TICKET majority flipped to Boston while the money stayed on "
          "the Yankees at 76%. Gate 1 failed and the game was passed on._", "",
          "_A game counts as a late ticket flip when a pre-lock board said \"with "
          "public\", a later pre-lock board said \"against public\", **and the money "
          "side was the same in both** — which is what makes it the tickets "
          "moving rather than the money._", ""]
    if hist == 0:
        return "\n".join(md + [
            "**No board history — broken run, not a result.** Fewer than two "
            "committed versions of every board, which means a shallow checkout. "
            "The workflow needs `fetch-depth: 0`.", ""])
    md += [f"- boards with version history: **{hist}** · graded games: "
           f"**{len(rows)}**", ""]
    if len(rows) < 40:
        return "\n".join(md + [f"Only {len(rows)} graded games — too few.", ""])

    by = defaultdict(list)
    for r in rows:
        by[r["kind"]].append(r)
    md += ["## Backing the MONEY side, by what the tickets did", "",
           "| what happened | backing the money side | backing the other side |",
           "|---|---|---|"]
    for k in ("stayed agreed", "ticket flip", "money side moved", "other"):
        v = by.get(k) or []
        if len(v) >= 10:
            md.append(f"| {k} | {_fmt(v)} | "
                      f"{_fmt(v, 'opp_odds', 'opp_won')} |")
    md.append("")

    flip, ctrl = by.get("ticket flip") or [], by.get("stayed agreed") or []
    if len(flip) >= 20 and len(ctrl) >= 20:
        d = (_roi(flip) - _roi(ctrl)) * 100
        rng = random.Random(6161)
        # is the flip population distinguishable from the agreeing one?
        pool = flip + ctrl
        n = len(flip)
        null = []
        for _ in range(TRIALS):
            s = rng.sample(pool, n)
            rest = [x for x in pool if id(x) not in {id(y) for y in s}]
            if rest:
                null.append((_roi(s) - _roi(rest)) * 100)
        p = (sum(1 for x in null if abs(x) >= abs(d)) + 1) / (len(null) + 1)
        md += ["## Is the flip population actually different?", "",
               f"- money side after a ticket flip: **{_roi(flip):+.1%}** "
               f"(n={len(flip)})",
               f"- money side when they stayed agreed: **{_roi(ctrl):+.1%}** "
               f"(n={len(ctrl)})",
               f"- difference **{d:+.1f} pts** · shuffling the two groups gives "
               f"±{sorted(abs(x) for x in null)[int(.95*len(null))]:.1f} · "
               f"**p = {p:.3f}**", "",
               "- " + ("the flip really does mark a worse population, so sitting "
                       "out is right" if p < 0.05 and d < 0 else
                       "**not distinguishable.** The gate is sitting out a "
                       "population it cannot show is worse — which is a cost, "
                       "not a saving, if the money side still wins them"), ""]
    md += ["## Reading it", "",
           "- sitting out is only correct if BOTH columns are bad. If the money "
           "side still pays after a ticket flip, the gate is discarding good bets",
           "- this was found by watching one game, so it is an observation "
           "looking for support, not a tested rule", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "ticket_flip.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
