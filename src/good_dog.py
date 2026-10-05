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

REGULAR SEASON ONLY - AND NOT BECAUSE OCTOBER IS "DIFFERENT"
In the postseason only good teams are left, so "favoured in 60% of his prior
games" stops discriminating. Measured on this season's own boards: 92% of the
teams still playing clear the bar (11 of 12) against 47% league-wide, and the
tag fires on 50% of underdog games in October against 22% in the regular
season. At that point the first condition is close to always true and the tag
collapses into "is priced as an underdog tonight" - which is the ordinary-dog
control it was built to be compared AGAINST. There is no contrast class left.

So postseason games are not tagged. This is scoping, not re-tuning: FAV_RATE is
untouched, and the backtest behind the tag (`dogs_and_line.md`) was regular
season, so tagging in October was always an out-of-population extrapolation.
Lowering or raising FAV_RATE to "fix" October would be exactly the re-tuning
the docstring above warns against.

Boards written before `game_type` was stored have no code and are read as
regular season, which is what they are.
"""

from __future__ import annotations

import glob
import json
import logging
from collections import defaultdict
from pathlib import Path

from . import mlb_api

log = logging.getLogger("good_dog")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
CACHE = OUTPUT_DIR / "team_splits_cache.json"
FAV_RATE = 0.60
MIN_PRIOR = 20
# MLB gameType codes for the postseason: wild card, division, league
# championship, world series, and the legacy catch-all.
POSTSEASON = frozenset({"F", "D", "L", "W", "P"})
MIN_SPLIT = 8          # games needed before a split percentage is worth showing


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
    Postseason games are never tagged - see the module docstring: with only good
    teams left the favourite-rate condition stops discriminating and the tag
    degenerates into its own control group.
    """
    if (game.get("game_type") or "R") in POSTSEASON:
        return None
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


def _board_prices(date: str) -> dict[str, int]:
    """{team: its moneyline} from one board file."""
    out = {}
    try:
        day = json.loads((OUTPUT_DIR / f"picks_{date}.json").read_text())
    except (OSError, ValueError):
        return out
    for g in day.get("games", []):
        m = g.get("matchup") or ""
        pc = g.get("pick_criteria") or {}
        adv = pc.get("advantage_team")
        a, o = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
        if " @ " not in m or not adv or not isinstance(a, int) or not isinstance(o, int):
            continue
        away, home = m.split(" @ ")
        if adv not in (away, home):
            continue
        out[adv] = a
        out[home if adv == away else away] = o
    return out


def _load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return {"days": {}}


def splits(before: str) -> dict[str, dict]:
    """{team: {"fav": [w, l], "dog": [w, l]}} over games before `before`.

    Needs winners, which board files do not store, so results are fetched once
    per date and cached. A day is only cached when every game in it is final -
    otherwise a board built mid-afternoon would freeze that day half-graded and
    never correct it.

    Fails soft: a date that cannot be fetched is skipped, so the board still
    prints the tag without the splits rather than not printing at all.
    """
    cache = _load_cache()
    days = cache.setdefault("days", {})
    dirty = False
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        if date >= before or date in days:
            continue
        prices = _board_prices(date)
        if not prices:
            continue
        try:
            res = mlb_api.results_for(date)
        except Exception as exc:
            log.warning("splits: results unavailable for %s (%s)", date, exc)
            continue
        if not res or not all(v.get("final") for v in res.values()):
            continue                       # don't freeze a half-played day
        rows = []
        for v in res.values():
            w = v.get("winner")
            if not w:
                continue
            for t in (v.get("home"), v.get("away")):
                if t in prices:
                    rows.append({"t": t, "fav": prices[t] < 0, "won": t == w})
        days[date] = rows
        dirty = True
    if dirty:
        try:
            CACHE.write_text(json.dumps(cache))
        except OSError as exc:
            log.warning("splits: cache not written (%s)", exc)

    agg: dict[str, dict] = defaultdict(lambda: {"fav": [0, 0], "dog": [0, 0]})
    for date, rows in days.items():
        if date >= before:
            continue
        for r in rows:
            cell = agg[r["t"]]["fav" if r["fav"] else "dog"]
            cell[0 if r["won"] else 1] += 1
    return dict(agg)


def split_text(team: str, sp: dict, applies: str | None = None) -> str:
    """'as a dog 31% (9-20) · as a favourite 58% (32-23)', or '' when too thin.

    `applies` marks the side tonight's price puts them on ("fav" or "dog"), so
    the number that bears on this bet is not left for the reader to work out.
    """
    rec = sp.get(team)
    if not rec:
        return ""
    parts = []
    for key, label in (("dog", "as a dog"), ("fav", "as a favourite")):
        w, l = rec[key]
        if w + l >= MIN_SPLIT:
            mark = "  ← tonight" if key == applies else ""
            parts.append(f"{label} {w/(w+l):.0%} ({w}-{l}){mark}")
    return "  ·  ".join(parts)
