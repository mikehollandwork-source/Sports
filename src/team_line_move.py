"""
Line movement per TEAM, at several increments.

THE QUESTION
Do particular teams behave differently when the line moves on them - some
consistently worth backing when money leaves, others worth fading when it
arrives? If so, a per-team rule would pay more than the one-size-fits-all gate.

WHY THE OBVIOUS VERSION OF THIS TEST IS WORTHLESS
Thirty teams x three increments x two directions is ~180 cells over ~1700
team-games, so a typical cell holds under ten bets. This repo has measured what
a grid that wide produces from nothing: the 75-cell price scan's best cell came
in at +16.9% against a noise median of +18.6%, and the 64-cell underdog scan
landed one tenth of a point off its own noise median. A 180-cell team scan will
hand back a +40% team with certainty and no meaning.

There is also no mechanism. A team is not a strategy - rosters turn over, and a
club the market systematically misprices would be corrected within weeks. Any
team-level edge has to survive both the statistics and that objection.

THE TEST THAT ACTUALLY SETTLES IT
Rather than asking "which team is best" - a question a scan always answers - ask
whether team identity carries ANY information:

    DISPERSION. If teams genuinely differ, the SPREAD of per-team ROIs must be
    wider than chance produces. Redraw every winner from its de-vigged closing
    price, recompute all thirty team ROIs, take their standard deviation, and
    repeat. One test, one degree of freedom, all the data - and if the observed
    spread sits inside that distribution then no per-team rule can exist,
    whatever the table looks like.

That is the honest version of the question, and it is far better powered than
any individual cell. The per-team tables are printed underneath as description.

Writes output/team_line_move.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import HOLDOUT_FROM, _implied

log = logging.getLogger("team_line_move")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 3000
MIN_TEAM = 20          # team-games needed before a team enters the dispersion test
MIN_CELL = 15          # cell size below which a number is decoration

INCREMENTS = [0.005, 0.01, 0.02, 0.03, 0.04]


def collect() -> list[dict]:
    """Two rows per game - one per team - each with the move signed TOWARD it."""
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
            shift = (pc.get("line_check") or {}).get("implied_shift")
            if (not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int)
                    or not isinstance(shift, (int, float))):
                continue
            away, home = m.split(" @ ")
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            tot = _implied(a_ml) + _implied(o_ml)
            gi = len(recs) // 2          # game index shared by both rows
            for team in (away, home):
                toward = shift if team == adv else -shift
                recs.append({
                    "date": date, "game": gi, "team": team,
                    "odds": price[team], "won": res["winner"] == team,
                    "toward": toward,
                    "p": (_implied(price[team]) / tot) if tot > 0 else 0.5,
                    "is_adv": team == adv,
                })
    return recs


def _roi(rows, wins=None) -> float:
    if not rows:
        return 0.0
    u = 0.0
    for r in rows:
        won = r["won"] if wins is None else (
            wins[r["game"]] if r["is_adv"] else not wins[r["game"]])
        u += grade.american_profit(r["odds"]) if won else -1
    return u / len(rows)


def _fmt(rows) -> str:
    if not rows:
        return "—"
    w = sum(1 for r in rows if r["won"])
    roi = _roi(rows)
    tag = "" if len(rows) >= MIN_CELL else "_"
    return f"{tag}{roi:+.0%} ({w}-{len(rows)-w}){tag}"


def _split_half(recs, key_fn, min_each=8):
    """Per-team ROI in each half of the season, paired.

    The direct test of what anyone would DO with a per-team table: if the good
    teams in one half are the good teams in the other, the table is a rule. If
    the correlation is nil, the table is thirty coin flips read twice."""
    a, b = defaultdict(list), defaultdict(list)
    dates = sorted({r["date"] for r in recs})
    mid = dates[len(dates) // 2]
    for r in recs:
        if not key_fn(r):
            continue
        (a if r["date"] < mid else b)[r["team"]].append(r)
    pairs = [(t, _roi(a[t]), _roi(b[t]), len(a[t]), len(b[t]))
             for t in a if t in b and len(a[t]) >= min_each and len(b[t]) >= min_each]
    return mid, pairs


def _pearson(xs, ys) -> float:
    n = len(xs)
    if n < 3:
        return float("nan")
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    dy = (sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / (dx * dy) if dx and dy else float("nan")


def build() -> str:
    recs = collect()
    md = ["# Line movement per team, by increment", "",
          "_Two rows per game, one per team, with the move signed toward that "
          "team. Italic cells are below "
          f"n={MIN_CELL} and are decoration, not evidence._", "",
          f"- team-games: **{len(recs)}** over "
          f"**{len(set(r['game'] for r in recs))}** games", ""]
    if len(recs) < 400:
        return "\n".join(md + ["Too few games.", ""])

    by_team: dict = defaultdict(list)
    for r in recs:
        by_team[r["team"]].append(r)

    # ---- THE test: is there any team-level spread beyond chance? ----
    eligible = {t: rs for t, rs in by_team.items() if len(rs) >= MIN_TEAM}
    obs = st.pstdev([_roi(rs) for rs in eligible.values()])
    rng = random.Random(509)
    ngames = max(r["game"] for r in recs) + 1
    null = []
    for _ in range(TRIALS):
        wins = [False] * ngames
        for r in recs:
            if r["is_adv"]:
                wins[r["game"]] = rng.random() < r["p"]
        null.append(st.pstdev([_roi(rs, wins) for rs in eligible.values()]))
    beats = sum(1 for x in null if x >= obs) / TRIALS
    null.sort()

    md += ["## Does team identity carry any information at all?", "",
           "_If teams genuinely differ, the SPREAD of their ROIs must be wider "
           "than chance produces. One test, all the data - far better powered "
           "than asking which team looks best, a question a scan always "
           "answers._", "",
           f"- teams with ≥{MIN_TEAM} team-games: **{len(eligible)}**",
           f"- observed spread of team ROIs: **{obs:.1%}**",
           f"- median spread from redrawn outcomes: **{st.median(null):.1%}**",
           f"- 95th percentile of chance spread: **{null[int(.95*TRIALS)]:.1%}**",
           f"- **p = {beats:.3f}**", ""]
    md += (["**Teams differ by more than chance.** A per-team rule is at least "
            "possible; which teams is a separate and much weaker question.", ""]
           if beats <= 0.05 else
           ["**No team-level signal.** The spread of team ROIs sits inside what "
            "randomly redrawn outcomes produce, so no per-team rule can exist "
            "no matter how the table below reads. The extremes are the biggest "
            "and smallest of thirty noisy numbers, which is what thirty noisy "
            "numbers look like.", ""])

    # ---- description: per team, by increment and direction ----
    md += ["## Per team", "",
           "| team | n | all moves | " +
           " | ".join(f"toward ≥{t:.0%}" for t in INCREMENTS) + " | " +
           " | ".join(f"against ≥{t:.0%}" for t in INCREMENTS) + " |",
           "|---" * (3 + 2 * len(INCREMENTS)) + "|"]
    for team in sorted(eligible, key=lambda t: -_roi(eligible[t])):
        rs = eligible[team]
        cells = [_fmt([r for r in rs if r["toward"] >= t]) for t in INCREMENTS]
        cells += [_fmt([r for r in rs if r["toward"] <= -t]) for t in INCREMENTS]
        md.append(f"| {team} | {len(rs)} | {_fmt(rs)} | " + " | ".join(cells) + " |")
    md.append("")

    # ---- split-half: would last month's best teams have been this month's? ----
    md += ["## Would the good teams have stayed good?", "",
           "_Per-team ROI in the first half of the record against the second. "
           "This is the direct test of what anyone would DO with the table "
           "above: if the good teams in one half are the good teams in the "
           "other, it is a rule. If not, it is thirty coin flips read twice._",
           ""]
    for label, fn in (("all moves", lambda r: True),
                      ("line toward the team ≥1%", lambda r: r["toward"] >= 0.01),
                      ("line against the team ≥1%", lambda r: r["toward"] <= -0.01)):
        mid, pairs = _split_half(recs, fn)
        if len(pairs) < 8:
            md.append(f"- **{label}**: too few teams with games in both halves")
            continue
        r = _pearson([p[1] for p in pairs], [p[2] for p in pairs])
        # what you would actually have earned following the first half's leaders
        ranked = sorted(pairs, key=lambda p: -p[1])
        for k in (5, 10):
            picked = {p[0] for p in ranked[:k]}
            rows2 = [x for x in recs if fn(x) and x["team"] in picked
                     and x["date"] >= mid]
            if rows2:
                md.append(f"- **{label}** — backing the top {k} teams from the "
                          f"first half, in the second: {_fmt(rows2)}")
        md.append(f"  · correlation between halves across {len(pairs)} teams: "
                  f"**r = {r:+.2f}**")
    md += ["", "_A correlation near zero means a team's record in one half says "
           "nothing about the next. That is the whole per-team idea, tested "
           "directly._", ""]

    # ---- dispersion again, but at each increment separately ----
    md += ["## Team spread at each increment", "",
           "_Team differences might only emerge on big moves. Same dispersion "
           "test, run inside each bucket._", "",
           "| bucket | teams | observed spread | median in noise | p |",
           "|---|---|---|---|---|"]
    for label, fn in ([(f"toward ≥{t:.1%}", (lambda t: lambda r: r["toward"] >= t)(t))
                       for t in INCREMENTS]
                      + [(f"against ≥{t:.1%}", (lambda t: lambda r: r["toward"] <= -t)(t))
                         for t in INCREMENTS]):
        sub = [r for r in recs if fn(r)]
        elig = defaultdict(list)
        for r in sub:
            elig[r["team"]].append(r)
        elig = {t: rs for t, rs in elig.items() if len(rs) >= MIN_CELL}
        if len(elig) < 8:
            md.append(f"| {label} | {len(elig)} | — | — | too few teams |")
            continue
        o = st.pstdev([_roi(rs) for rs in elig.values()])
        rg = random.Random(577)
        nl = []
        for _ in range(1000):
            wins = [False] * ngames
            for r in recs:
                if r["is_adv"]:
                    wins[r["game"]] = rg.random() < r["p"]
            nl.append(st.pstdev([_roi(rs, wins) for rs in elig.values()]))
        pv = sum(1 for x in nl if x >= o) / len(nl)
        md.append(f"| {label} | {len(elig)} | {o:.1%} | {st.median(nl):.1%} | "
                  f"{pv:.3f} |")
    md.append("")

    # ---- max-statistic over the team x increment grid, for completeness ----
    cells: dict = {}
    for team, rs in eligible.items():
        for t in INCREMENTS:
            for lbl, sub in ((f"{team} toward≥{t:.0%}",
                              [r for r in rs if r["toward"] >= t]),
                             (f"{team} against≥{t:.0%}",
                              [r for r in rs if r["toward"] <= -t])):
                if len(sub) >= MIN_CELL:
                    cells[lbl] = sub
    if cells:
        best_label = max(cells, key=lambda k: _roi(cells[k]))
        best = _roi(cells[best_label])
        null_max = []
        rng2 = random.Random(521)
        for _ in range(TRIALS):
            wins = [False] * ngames
            for r in recs:
                if r["is_adv"]:
                    wins[r["game"]] = rng2.random() < r["p"]
            null_max.append(max(_roi(v, wins) for v in cells.values()))
        bm = sum(1 for x in null_max if x >= best) / TRIALS
        null_max.sort()
        md += ["## And the best cell, corrected for the width of the search", "",
               f"- cells at n≥{MIN_CELL}: **{len(cells)}**",
               f"- best: `{best_label}` at **{best:+.1%}** (n={len(cells[best_label])})",
               f"- median best-in-noise: **{st.median(null_max):+.1%}**",
               f"- **corrected p = {bm:.3f}**", ""]
        md += (["**Clears.**", ""] if bm <= 0.05 else
               ["**Does not clear**, as expected for a grid this wide.", ""])
        pre = [r for r in cells[best_label] if r["date"] < HOLDOUT_FROM]
        post = [r for r in cells[best_label] if r["date"] >= HOLDOUT_FROM]
        md += [f"- in-sample: {_fmt(pre)} · holdout: {_fmt(post)}", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "team_line_move.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
