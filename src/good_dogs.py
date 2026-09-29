"""
Do good teams beat their price when the market makes them underdogs?

WHERE THIS CAME FROM, INCLUDING THE PART THAT WAS WRONG
Philadelphia went 4-12 as an underdog, so the hypothesis tested was that teams
who are usually favourites UNDERperform when priced as dogs. `league_calibration`
found the opposite at scale - every cut positive, ROI +3.4% to +7.9% against
-5.8% for underdogs generally. So the lead was backwards and the direction here
was found by scanning, which is the weakest possible provenance and the reason
this file exists rather than a conclusion.

What it has going for it is size: 159 to 383 games depending on the cut, against
Philadelphia's sixteen, and a plain mechanism - a good team priced as a dog is
the market pricing the matchup, not the team, and the public pays for names.

WHAT COULD MAKE IT FAKE, AND THE TEST FOR EACH
  the cut was chosen      four cuts were looked at. All four are corrected
                          together by a max-statistic permutation with winners
                          redrawn from de-vigged prices, so the best cut is
                          judged against the best of four on noise.
  it is one hot stretch   split-half, and month by month. The Philadelphia
                          +25.6% cell had one half carrying everything.
  it is just "back dogs"  underdogs generally returned -5.8%, so the control is
                          every other underdog over the same games. The number
                          that matters is the DIFFERENCE, bootstrapped by day.
  favourite-rate is
  circular                a team's favourite rate is computed from the same
                          season as the results, so a team that got hot is
                          labelled "usually a favourite" partly because of the
                          wins being scored. Also reported on a rate computed
                          from games BEFORE each game, which removes it.

Writes output/good_dogs.md.
"""

from __future__ import annotations

import logging
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import grade
from .league_calibration import collect, team_games

log = logging.getLogger("good_dogs")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 10000
CUTS = [0.55, 0.60, 0.65, 0.70]
MIN_PRIOR = 20      # games needed before a point-in-time favourite rate means anything


def _roi(rs) -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r["odds"]) if r["won"] else -1
               for r in rs) / len(rs)


def _fmt(rs) -> str:
    if not rs:
        return "—"
    w = sum(1 for r in rs if r["won"])
    exp = sum(r["p"] for r in rs)
    return f"{w}-{len(rs)-w} · exp {exp:.1f} · **{_roi(rs):+.1%}**"


def _boot_diff(a, b) -> tuple[float, float]:
    ga, gb = defaultdict(list), defaultdict(list)
    for r in a:
        ga[r["date"]].append(grade.american_profit(r["odds"]) if r["won"] else -1)
    for r in b:
        gb[r["date"]].append(grade.american_profit(r["odds"]) if r["won"] else -1)
    days = sorted(set(ga) | set(gb))
    if len(days) < 5:
        return (float("nan"), float("nan"))
    rng = random.Random(2222)
    out = []
    for _ in range(TRIALS):
        va, vb = [], []
        for _ in days:
            d = days[rng.randrange(len(days))]
            va += ga.get(d, [])
            vb += gb.get(d, [])
        if va and vb:
            out.append((st.mean(va) - st.mean(vb)) * 100)
    out.sort()
    return out[int(.025 * len(out))], out[int(.975 * len(out))]


def build() -> str:
    rows = collect()
    tg = team_games(rows)
    all_dogs = [dict(r, team=t) for t, v in tg.items() for r in v if r["odds"] > 0]
    md = ["# Do good teams beat their price when the market makes them dogs?", "",
          "_Philadelphia went 4-12 as a dog, so the hypothesis was that "
          "usually-favourite teams UNDERperform as dogs. `league_calibration` "
          "found the opposite — every cut positive, +3.4% to +7.9% against −5.8% "
          "for dogs generally. The lead was backwards and this direction was "
          "found by scanning, which is the weakest provenance there is. What it "
          "has is size: 159–383 games against Philadelphia's sixteen._", "",
          f"- graded games: **{len(rows)}** · underdog team-games: "
          f"**{len(all_dogs)}**", ""]
    if len(rows) < 300:
        return "\n".join(md + ["Not enough games.", ""])

    # season-long favourite rate (the circular version, reported for continuity)
    rate = {t: sum(1 for r in v if r["odds"] < 0) / len(v) for t, v in tg.items()}
    md += ["## Season-long favourite rate", "",
           "_Circular by construction — a team's favourite rate comes from the "
           "same season being scored — but it is what `league_calibration` "
           "reported, so it is here to compare against the honest version below._",
           "", "| cut | teams | their dog games | record | vs OTHER dogs | "
           "difference | 95% CI |", "|---|---|---|---|---|---|---|"]
    cells = {}
    for c in CUTS:
        who = {t for t, x in rate.items() if x >= c}
        mine = [r for r in all_dogs if r["team"] in who]
        rest = [r for r in all_dogs if r["team"] not in who]
        if len(mine) < 60:
            continue
        d = (_roi(mine) - _roi(rest)) * 100
        cells[f"≥{c:.0%}"] = (d, mine, rest)
        lo, hi = _boot_diff(mine, rest)
        md.append(f"| ≥{c:.0%} | {len(who)} | {len(mine)} | {_fmt(mine)} | "
                  f"{_fmt(rest)} | **{d:+.1f} pts** | "
                  + ("—" if lo != lo else f"{lo:+.1f} to {hi:+.1f}") + " |")
    md.append("")

    # point-in-time favourite rate - no peeking
    prior = defaultdict(list)
    pit = []
    for r in sorted(rows, key=lambda r: r["date"]):
        for t in (r["home"], r["away"]):
            hist = prior[t]
            if len(hist) >= MIN_PRIOR and r["price"][t] > 0:
                pit.append({"date": r["date"], "team": t, "odds": r["price"][t],
                            "p": r["prob"][t], "won": r["winner"] == t,
                            "rate": sum(hist) / len(hist)})
        for t in (r["home"], r["away"]):
            prior[t].append(1 if r["price"][t] < 0 else 0)
    md += ["## Favourite rate from PRIOR games only", "",
           "_The honest version. A team's favourite rate is computed from its "
           f"games before the one being scored, needing {MIN_PRIOR} of them, so "
           "a team that got hot is not labelled a favourite partly because of "
           "the wins being counted._", "",
           "| cut | dog games | record | vs OTHER dogs | difference | 95% CI |",
           "|---|---|---|---|---|---|"]
    pit_cells = {}
    for c in CUTS:
        mine = [r for r in pit if r["rate"] >= c]
        rest = [r for r in pit if r["rate"] < c]
        if len(mine) < 60 or len(rest) < 60:
            continue
        d = (_roi(mine) - _roi(rest)) * 100
        pit_cells[f"≥{c:.0%}"] = (d, mine, rest)
        lo, hi = _boot_diff(mine, rest)
        md.append(f"| ≥{c:.0%} | {len(mine)} | {_fmt(mine)} | {_fmt(rest)} | "
                  f"**{d:+.1f} pts** | "
                  + ("—" if lo != lo else f"{lo:+.1f} to {hi:+.1f}") + " |")
    md.append("")

    # correction across the four cuts, on the point-in-time version
    use = pit_cells or cells
    tag = "prior-games" if pit_cells else "season-long"
    if use:
        base = pit if pit_cells else all_dogs
        # index by identity: two rows can compare equal, and `r in list` on
        # dicts is both wrong for that reason and quadratic
        pos = {id(r): i for i, r in enumerate(base)}
        idx = {k: ([pos[id(r)] for r in v[1] if id(r) in pos],
                   [pos[id(r)] for r in v[2] if id(r) in pos])
               for k, v in use.items()}
        prof = [grade.american_profit(r["odds"]) for r in base]
        prob = [r["p"] for r in base]
        rng = random.Random(3333)
        hi_d = []
        for _ in range(TRIALS):
            draw = [prof[i] if rng.random() < prob[i] else -1 for i in range(len(base))]
            vals = []
            for pi, fi in idx.values():
                if pi and fi:
                    vals.append((sum(draw[i] for i in pi) / len(pi)
                                 - sum(draw[i] for i in fi) / len(fi)) * 100)
            if vals:
                hi_d.append(max(vals))
        best = max(use, key=lambda k: use[k][0])
        obs = use[best][0]
        pv = (sum(1 for x in hi_d if x >= obs) + 1) / (len(hi_d) + 1)
        md += [f"## Corrected across the {len(use)} cuts ({tag})", "",
               f"- best cut **{best}** at {obs:+.1f} pts · the best of "
               f"{len(use)} cuts reaches {st.median(hi_d):+.1f} median, "
               f"{sorted(hi_d)[int(.95*len(hi_d))]:+.1f} at the 95th · "
               f"**corrected p = {pv:.3f}**", ""]

        rh = random.Random(4444)
        _, mine, rest = use[best]
        tm = [rh.random() < 0.5 for _ in mine]
        tr = [rh.random() < 0.5 for _ in rest]
        ma = [x for x, t in zip(mine, tm) if t]; mb = [x for x, t in zip(mine, tm) if not t]
        ra = [x for x, t in zip(rest, tr) if t]; rb = [x for x, t in zip(rest, tr) if not t]
        if min(len(ma), len(mb), len(ra), len(rb)) >= 25:
            da = (_roi(ma) - _roi(ra)) * 100
            db = (_roi(mb) - _roi(rb)) * 100
            md += [f"- split-half: **{da:+.1f} pts** on one half, "
                   f"**{db:+.1f} pts** on the other",
                   "- " + ("**both halves agree in sign**" if (da > 0) == (db > 0)
                           else "**the halves disagree** — one half is the whole "
                                "effect, which is what a fluke looks like"), ""]

        by = defaultdict(lambda: ([], []))
        for r in mine:
            by[r["date"][:7]][0].append(r)
        for r in rest:
            by[r["date"][:7]][1].append(r)
        md += ["## Month by month", "",
               "| month | good dogs | other dogs | difference |", "|---|---|---|---|"]
        for mth in sorted(by):
            a, b = by[mth]
            if len(a) >= 15 and len(b) >= 15:
                md.append(f"| {mth} | {_fmt(a)} | {_fmt(b)} | "
                          f"**{(_roi(a)-_roi(b))*100:+.1f} pts** |")
        md.append("")

    md += ["## The bar", "",
           "- the **difference** against other underdogs is the number, not the "
           "ROI — underdogs generally returned −5.8%, so a positive ROI here is "
           "partly just \"underdogs did alright\"",
           "- it has to survive the correction across cuts AND agree in sign "
           "across halves AND not be one month",
           "- the prior-games table is the one to believe; the season-long one "
           "peeks at the results it is being scored on", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "good_dogs.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
