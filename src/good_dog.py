"""
The "good dog" tag: a team the market usually favours, priced as an underdog.

WATCHING, NOT BETTING - AND THE REASON MATTERS
This tag changes no pick. It exists so forward evidence accumulates while the
question is still open, because the backtest cannot close it.

What the backtest found (`dogs_and_line.md`): the 2x2 is a clean monotonic
gradient - ordinary dog with no line move -12.2%, ordinary dog with the line
against -4.6%, good dog with no line move -2.0%, good dog with the line against
+9.9% - and it survives leave-August-out (+11.8% outside August against +6.8%
inside) and a split-half. But the two main effects come in at p = 0.154 and
p = 0.277 against a 0.025 threshold, and the corner cell sits exactly on the
noise median for a 16-cell scan.

The null width on these differences is +/-16 points, because underdog returns
are violently noisy - plus-money payouts mean a few results move everything.
Closing the question needs roughly 2.5x the data: about 2,100 underdog games,
or two and a half more seasons. No smarter test fixes that; only more games do.

Hence a tag. Label them, let them accumulate, look again with two seasons.

THE DEFINITION
Favoured in at least FAV_RATE of the team's PRIOR games this season, needing
MIN_PRIOR of them, and priced as an underdog in this one. Prior-only, so a team
that got hot is never labelled partly because of the games being judged.

FAV_RATE is 0.60 - a plain reading of "usually the favourite", chosen for its
meaning rather than its backtest, because all four cuts tested (0.55 to 0.70)
were statistically indistinguishable and picking the best-performing one would
be the selection this project keeps getting caught by.
"""

from __future__ import annotations

import glob
import json
import logging
from collections import defaultdict
from pathlib import Path

log = logging.getLogger("good_dog")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
FAV_RATE = 0.60
MIN_PRIOR = 20


def favourite_rates(before: str) -> dict[str, float]:
    """{team: share of prior games it was favoured in}, from board files dated
    strictly before `before`. Teams with fewer than MIN_PRIOR games are left out,
    so an unlabelled team means "not enough history", never "not good"."""
    tally: dict[str, list[int]] = defaultdict(list)
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        if date >= before:
            continue
        try:
            day = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        for g in day.get("games", []):
            m = g.get("matchup") or ""
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a, o = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if " @ " not in m or not adv or not isinstance(a, int) \
                    or not isinstance(o, int):
                continue
            away, home = m.split(" @ ")
            if adv not in (away, home):
                continue
            price = {adv: a, (home if adv == away else away): o}
            for t in (away, home):
                if t in price:
                    tally[t].append(1 if price[t] < 0 else 0)
    return {t: sum(v) / len(v) for t, v in tally.items() if len(v) >= MIN_PRIOR}


def tag(game: dict, rates: dict[str, float]) -> dict | None:
    """{"team", "rate", "odds"} when this game holds a good dog, else None.

    Reads the board's own prices, so it works whether or not the game is a pick.
    """
    m = game.get("matchup") or ""
    pc = game.get("pick_criteria") or {}
    adv = pc.get("advantage_team")
    a, o = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
    if " @ " not in m or not adv or not isinstance(a, int) or not isinstance(o, int):
        return None
    away, home = m.split(" @ ")
    if adv not in (away, home):
        return None
    opp = home if adv == away else away
    for team, odds in ((adv, a), (opp, o)):
        if odds > 0:                       # priced as the underdog
            r = rates.get(team)
            if r is not None and r >= FAV_RATE:
                return {"team": team, "rate": round(r, 3), "odds": odds}
    return None
