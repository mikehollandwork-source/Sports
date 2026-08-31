"""
Schedule and travel spots: long road trips, rest, and schedule density.

WHY THIS FAMILY IS WORTH TESTING WHEN THE OTHERS FAILED
Every signal tested so far - margin, BvP, form, line movement, public lean - is
something the market watches too. `ev_model` showed they add nothing on top of
the price, which is what you would expect for inputs every book already models.

Schedule spots are a different bet: not "we know the teams better" but "the
market underweights fatigue". That is at least a coherent story for an
inefficiency, which none of the previous eleven had. It may still be wrong, and
this is built to find that out rather than to confirm it.

WHERE THE DATA COMES FROM
Nothing on the board records travel, so it is DERIVED from the board history
itself: 70 daily files give every team's home/away sequence, from which road-trip
length, days of rest and schedule density fall out. All backward-looking, so
every feature is knowable before first pitch.

THE TRUNCATION THAT MATTERS
Boards start 2026-06-23, so a road trip already in progress on that date is
undercounted. Any streak is therefore only trusted once the team has been
OBSERVED at home first - `_seen_home` - which throws away the earliest games
rather than reporting a trip length that is really "as far back as we can see".

    end_of_trip uses the NEXT scheduled game to know the trip is ending. That is
    schedule lookahead, not outcome lookahead - MLB schedules are published
    months ahead, so this is knowable pre-game. It is flagged separately anyway.

Two board dates are absent in the span (2026-07-13 and 07-15), both inside the
All-Star break, so the 4-day rests they produce are real time off rather than
missing files. Rest is measured between OBSERVED games, so a genuinely missing
board would inflate it - checked, and these two are the only gaps.

SILENCING THE NOISE
Same apparatus that killed the other eleven: every cell at n>=MIN_CELL enters one
max-statistic permutation with outcomes redrawn from de-vigged closing prices, so
the reported p is corrected for the whole search rather than for a cell chosen
out of it. A grid this size reliably manufactures a +15% cell from nothing; the
correction is what tells them apart.

Writes output/schedule_spots.md.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import HOLDOUT_FROM, _implied

log = logging.getLogger("schedule_spots")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MIN_CELL = 40
TRIALS = 3000


def _history() -> tuple[dict, list[str]]:
    """{date: {team: is_home}} plus the sorted list of board dates."""
    hist: dict[str, dict[str, bool]] = {}
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        day = {}
        try:
            games = json.loads(Path(f).read_text()).get("games", [])
        except (OSError, ValueError):
            continue
        for g in games:
            m = g.get("matchup") or ""
            if " @ " not in m:
                continue
            away, home = m.split(" @ ")
            day[away] = False
            day[home] = True
        if day:
            hist[date] = day
    return hist, sorted(hist)


def _team_spots(hist: dict, dates: list[str]) -> dict:
    """{(date, team): {road_streak, home_streak, days_rest, g7, seen_home,
                       end_of_trip}} - all backward-looking except end_of_trip."""
    prev: dict[str, list[tuple[str, bool]]] = defaultdict(list)
    out: dict = {}
    for i, d in enumerate(dates):
        for team, is_home in hist[d].items():
            past = prev[team]
            # consecutive road/home games ending at this one
            streak = 1
            for pd, ph in reversed(past):
                if ph == is_home:
                    streak += 1
                else:
                    break
            seen_home = any(ph for _pd, ph in past)
            rest = None
            if past:
                rest = ((dt.date.fromisoformat(d)
                         - dt.date.fromisoformat(past[-1][0])).days - 1)
            g7 = sum(1 for pd, _ in past
                     if (dt.date.fromisoformat(d)
                         - dt.date.fromisoformat(pd)).days <= 7)
            # schedule lookahead only: is the next listed game at home?
            nxt = None
            for j in range(i + 1, min(i + 6, len(dates))):
                if team in hist[dates[j]]:
                    nxt = hist[dates[j]][team]
                    break
            out[(d, team)] = {
                "road_streak": streak if not is_home else 0,
                "home_streak": streak if is_home else 0,
                "days_rest": rest, "g7": g7, "seen_home": seen_home,
                "is_home": is_home,
                "end_of_trip": (not is_home) and (nxt is True),
            }
            prev[team].append((d, is_home))
    return out


def collect() -> list[dict]:
    hist, dates = _history()
    spots = _team_spots(hist, dates)
    recs = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        for g in json.loads(Path(f).read_text()).get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            m = g.get("matchup") or ""
            if " @ " not in m:
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            away, home = m.split(" @ ")
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            sa, sh = spots.get((date, away)), spots.get((date, home))
            if not sa or not sh or not sa["seen_home"] or not sh["seen_home"]:
                continue                      # trip length not trustworthy yet
            tot = _implied(price[home]) + _implied(price[away])
            recs.append({
                "date": date, "matchup": m, "home": home, "away": away,
                "home_ml": price[home], "away_ml": price[away],
                "home_won": res["winner"] == home,
                "p_home": (_implied(price[home]) / tot) if tot > 0 else 0.5,
                "away_road_streak": sa["road_streak"],
                "away_end_trip": sa["end_of_trip"],
                "home_home_streak": sh["home_streak"],
                "away_rest": sa["days_rest"], "home_rest": sh["days_rest"],
                "away_g7": sa["g7"], "home_g7": sh["g7"],
            })
    return recs


def _view(rows, side: str) -> list[dict]:
    """Back `side` ('home' or 'away') in each row, at its real price."""
    return [{"_i": r["_i"],
             "odds": r["home_ml"] if side == "home" else r["away_ml"],
             "won": r["home_won"] if side == "home" else not r["home_won"],
             "invert": side != "home"} for r in rows]


def _stat(rows, wins=None):
    w = u = 0
    for x in rows:
        won = x["won"] if wins is None else (
            (not wins[x["_i"]]) if x["invert"] else wins[x["_i"]])
        w += 1 if won else 0
        u += grade.american_profit(x["odds"]) if won else -1
    return w, len(rows) - w, u, (u / len(rows) if rows else 0.0)


def _roi(rows, wins=None) -> float:
    return _stat(rows, wins)[3]


def _fmt(rows) -> str:
    if not rows:
        return "—"
    w, l, u, roi = _stat(rows)
    tag = "" if len(rows) >= MIN_CELL else " _(thin)_"
    return f"{w}-{l} ({w/len(rows):.0%}) · {u:+.1f}u · **{roi:+.1%}** (n={len(rows)}){tag}"


def build() -> str:
    recs = collect()
    for i, r in enumerate(recs):
        r["_i"] = i
    md = ["# Schedule & travel spots — road trips, rest, density", "",
          "_Derived from 70 days of board history: every team's home/away "
          "sequence gives trip length, rest and density. Backward-looking, so "
          "knowable before first pitch. Teams are only included once observed "
          "at home, so no trip length is really \"as far back as we can see\"._",
          "", f"- usable graded games: **{len(recs)}**", ""]
    if len(recs) < MIN_CELL * 2:
        return "\n".join(md + ["Too few games once truncation is respected.", ""])

    cells: dict = {}

    def cell(label, rows):
        if len(rows) >= MIN_CELL:
            cells[label] = rows
        return _fmt(rows)

    md += ["## Baselines", "", "| bet | result |", "|---|---|",
           f"| back the home team, always | {cell('base:home', _view(recs,'home'))} |",
           f"| back the road team, always | {cell('base:away', _view(recs,'away'))} |", ""]

    md += ["## Fading a team deep into a road trip", "",
           "_Back the HOME side as the visitor's trip lengthens._", "",
           "| visitor's consecutive road games | back home | back the road team |",
           "|---|---|---|"]
    for lo in (3, 4, 5, 6, 7):
        sub = [r for r in recs if r["away_road_streak"] >= lo]
        md.append(f"| ≥{lo} | {cell(f'road>={lo}:home', _view(sub,'home'))} | "
                  f"{cell(f'road>={lo}:away', _view(sub,'away'))} |")
    md.append("")

    end = [r for r in recs if r["away_end_trip"]]
    md += ["## The specific spot: last game of a road trip", "",
           "_Schedule lookahead only - the next listed game is at home. MLB "
           "schedules are published months ahead, so this is knowable pre-game._",
           "", "| spot | back home | back the road team |", "|---|---|---|",
           f"| any final road game | {cell('endtrip:home', _view(end,'home'))} | "
           f"{cell('endtrip:away', _view(end,'away'))} |"]
    for lo in (4, 6):
        sub = [r for r in end if r["away_road_streak"] >= lo]
        md.append(f"| final game of a ≥{lo}-game trip | "
                  f"{cell(f'endtrip{lo}:home', _view(sub,'home'))} | "
                  f"{cell(f'endtrip{lo}:away', _view(sub,'away'))} |")
    md.append("")

    md += ["## Rest", "", "| spot | back home | back the road team |", "|---|---|---|"]
    for label, test in (
        ("visitor on 0 days rest", lambda r: r["away_rest"] == 0),
        ("home on 0 days rest", lambda r: r["home_rest"] == 0),
        ("visitor rested, home not", lambda r: (r["away_rest"] or 0) >= 1 and r["home_rest"] == 0),
        ("home rested, visitor not", lambda r: (r["home_rest"] or 0) >= 1 and r["away_rest"] == 0),
    ):
        sub = [r for r in recs if test(r)]
        md.append(f"| {label} | {cell(f'{label}:home', _view(sub,'home'))} | "
                  f"{cell(f'{label}:away', _view(sub,'away'))} |")
    md.append("")

    md += ["## Schedule density (games in the last 7 days)", "",
           "| spot | back home | back the road team |", "|---|---|---|"]
    for label, test in (
        ("visitor played 6+", lambda r: r["away_g7"] >= 6),
        ("visitor played 6+, home ≤5", lambda r: r["away_g7"] >= 6 and r["home_g7"] <= 5),
        ("home played 6+", lambda r: r["home_g7"] >= 6),
    ):
        sub = [r for r in recs if test(r)]
        md.append(f"| {label} | {cell(f'{label}:home', _view(sub,'home'))} | "
                  f"{cell(f'{label}:away', _view(sub,'away'))} |")
    md.append("")

    md += ["## Home team on a long homestand", "",
           "| home's consecutive home games | back home | back the road team |",
           "|---|---|---|"]
    for lo in (4, 6):
        sub = [r for r in recs if r["home_home_streak"] >= lo]
        md.append(f"| ≥{lo} | {cell(f'stand>={lo}:home', _view(sub,'home'))} | "
                  f"{cell(f'stand>={lo}:away', _view(sub,'away'))} |")
    md.append("")

    # ---- the correction ----
    if not cells:
        return "\n".join(md + [f"No cell reaches n={MIN_CELL}.", ""])
    best_label = max(cells, key=lambda k: _roi(cells[k]))
    best_rows = cells[best_label]
    best = _roi(best_rows)
    rng = random.Random(191)
    null_max = []
    for _ in range(TRIALS):
        w = [rng.random() < r["p_home"] for r in recs]
        null_max.append(max(_roi(v, w) for v in cells.values()))
    beats = sum(1 for m in null_max if m >= best) / TRIALS
    null_max.sort()
    md += ["## Silencing the noise", "",
           f"- cells at n≥{MIN_CELL}: **{len(cells)}**",
           f"- best: `{best_label}` at **{best:+.1%}** (n={len(best_rows)})",
           f"- median best-in-noise: **{st.median(null_max):+.1%}**",
           f"- 95th percentile in noise: **{null_max[int(.95*TRIALS)]:+.1%}**",
           f"- **corrected p = {beats:.3f}**", ""]
    md += (["**Clears the bar.** Better than a grid this size finds in noise.", ""]
           if beats <= 0.05 else
           ["**Does not clear.** A grid this size produces a cell this good from "
            "noise more than 5% of the time, so the number is the search "
            "talking.", ""])

    pre = [r for r in best_rows if recs[r["_i"]]["date"] < HOLDOUT_FROM]
    post = [r for r in best_rows if recs[r["_i"]]["date"] >= HOLDOUT_FROM]
    md += [f"- in-sample: {_fmt(pre)}", f"- holdout: {_fmt(post)}", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "schedule_spots.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
