"""
Hot bats + umpire + line-against, against wins and losses.

THE MECHANISM, WHICH IS WHY THIS IS WORTH A RUN
Most things tested this season were correlations hunting for a story. This
one has the story first: an umpire who calls few strikeouts leaves more balls
in play, which is worth more to the side that is already hitting well than to
the side that is not. So an offence-friendly umpire should AMPLIFY a hitting
edge rather than shift the game evenly. Line-against then supplies the
discount, which is the one gate that keeps surviving.

WHAT IS AND IS NOT NEW HERE
Hot bats have been tested alone (`fade_hot_bats`, `hot_home_dog`,
`margin_form`) and are null. Line-against is the live gate. The umpire has
NEVER been tested as a signal - only yesterday, as a condition on
predictability, where it came back flat (p = 0.900). What is new is the
three-way interaction, and specifically the claim that the umpire matters
differently depending on which side is hitting.

946 games carry a form read, an umpire tendency and a line move.

THE COUNTERPART IS TESTED TOO
If a low-strikeout umpire helps the hotter bats, a HIGH-strikeout umpire
should help the better pitching side by the same logic. Testing only the
half that fits the story is how a coin flip becomes a finding, so both
directions enter the grid and both are paid for in the correction.

`k_extra` is the umpire's strikeouts above or below expectation - median
-0.08 across 1,017 games, range -3.11 to +2.86 - so it is already relative
and needs no park or team adjustment.

Writes output/bats_ump_line.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import _implied

log = logging.getLogger("bats_ump_line")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 3000
MIN_CELL = 40
MIN_HALF = 15
LINE_MIN = 0.01


def collect() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        for g in json.loads(Path(f).read_text()).get("games", []):
            res = results.get(g.get("game_pk"))
            m = g.get("matchup") or ""
            if not res or not res.get("final") or not res.get("winner") or " @ " not in m:
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            ut = g.get("ump_tend") or {}
            form = g.get("form") or {}
            dh = (form.get("home") or {}).get("delta")
            da = (form.get("away") or {}).get("delta")
            shift = (pc.get("line_check") or {}).get("implied_shift")
            kx = ut.get("k_extra")
            if (not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int)
                    or not isinstance(dh, (int, float)) or not isinstance(da, (int, float))
                    or not isinstance(shift, (int, float))
                    or not isinstance(kx, (int, float)) or dh == da):
                continue
            away, home = m.split(" @ ")
            if adv not in (away, home):
                continue
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            hot = home if dh > da else away
            cold = away if hot == home else home
            if hot not in price or cold not in price:
                continue
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0:
                continue
            toward_hot = shift if hot == adv else -shift
            rows.append({
                "date": date, "hot": hot, "cold": cold,
                "hot_odds": price[hot], "cold_odds": price[cold],
                "hot_won": res["winner"] == hot,
                "p_hot": _implied(price[hot]) / tot,
                "gap": abs(dh - da), "k_extra": kx,
                "toward_hot": toward_hot,
            })
    return rows


def _bets(rs, side="hot"):
    if side == "hot":
        return [(r["hot_odds"], r["hot_won"]) for r in rs]
    return [(r["cold_odds"], not r["hot_won"]) for r in rs]


def _roi(b) -> float:
    if not b:
        return 0.0
    return sum(grade.american_profit(o) if w else -1 for o, w in b) / len(b)


def _fmt(rs, side="hot") -> str:
    b = _bets(rs, side)
    if not b:
        return "—"
    w = sum(1 for _, won in b if won)
    return f"{w}-{len(b)-w} · **{_roi(b):+.1%}** (n={len(b)})"


def build() -> str:
    rows = collect()
    md = ["# Hot bats, the umpire, and the line moving against", "",
          "_The mechanism first: an umpire who calls few strikeouts leaves "
          "more balls in play, which is worth more to the side already "
          "hitting well. So an offence-friendly umpire should AMPLIFY a "
          "hitting edge rather than move the game evenly. Line-against "
          "supplies the discount._", "",
          f"- games with form, umpire and line all present: **{len(rows)}**", ""]
    if len(rows) < 300:
        return "\n".join(md + ["Not enough joined games.", ""])

    kx_med = st.median([r["k_extra"] for r in rows])
    md += [f"- umpire `k_extra` median: **{kx_med:+.2f}** (strikeouts above "
           "or below expectation, so already relative)",
           f"- baseline, backing the hotter-hitting side in every game: "
           f"{_fmt(rows)}",
           f"- baseline, backing the colder side: {_fmt(rows, 'cold')}", ""]

    friendly = lambda r: r["k_extra"] < kx_med        # noqa: E731
    against = lambda r: r["toward_hot"] <= -LINE_MIN  # noqa: E731

    md += ["## The 2×2×2", "",
           "_Backing the HOTTER-hitting side. `offence-friendly ump` is "
           "`k_extra` below the median; `line against` is the price moving "
           "away from the hot side by ≥1%._", "",
           "| umpire | line | backing the hot side |", "|---|---|---|"]
    cells = []
    for ulab, utest in (("offence-friendly", friendly),
                        ("strikeout-heavy", lambda r: not friendly(r))):
        for llab, ltest in (("moved against", against),
                            ("not against", lambda r: not against(r))):
            sub = [r for r in rows if utest(r) and ltest(r)]
            cells.append((f"hot · {ulab} · {llab}", sub, "hot"))
            md.append(f"| {ulab} | {llab} | {_fmt(sub)} |")
    md.append("")

    md += ["## The counterpart, so only half the story is not tested", "",
           "_If a low-strikeout umpire helps the hotter bats, a "
           "strikeout-heavy one should help the other side by the same "
           "logic. Backing the COLDER side here._", "",
           "| umpire | line | backing the cold side |", "|---|---|---|"]
    for ulab, utest in (("strikeout-heavy", lambda r: not friendly(r)),
                        ("offence-friendly", friendly)):
        for llab, ltest in (("moved against the hot side", against),
                            ("not against", lambda r: not against(r))):
            sub = [r for r in rows if utest(r) and ltest(r)]
            cells.append((f"cold · {ulab} · {llab}", sub, "cold"))
            md.append(f"| {ulab} | {llab} | {_fmt(sub, 'cold')} |")
    md.append("")

    # graded by how big the hitting edge is
    md += ["## Does a bigger hitting edge help more?", "",
           "_Offence-friendly umpire and line-against only, split by the size "
           "of the form gap._", "",
           "| form gap | backing the hot side |", "|---|---|"]
    base = [r for r in rows if friendly(r) and against(r)]
    if base:
        g_med = st.median([r["gap"] for r in base])
        for lab, test in ((f"gap ≥ {g_med:.3f} (bigger)", lambda r: r["gap"] >= g_med),
                          (f"gap < {g_med:.3f} (smaller)", lambda r: r["gap"] < g_med)):
            sub = [r for r in base if test(r)]
            cells.append((f"hot · friendly ump · against · {lab}", sub, "hot"))
            md.append(f"| {lab} | {_fmt(sub)} |")
    md.append("")

    # --- pay for the grid --------------------------------------------------
    pool = [(l, s, side) for l, s, side in cells if len(s) >= MIN_CELL]
    if not pool:
        return "\n".join(md + [f"No cell reaches n={MIN_CELL}.", ""])
    bl, bs, bside = max(pool, key=lambda c: _roi(_bets(c[1], c[2])))
    obs = _roi(_bets(bs, bside)) * 100
    plan = []
    for _, s, side in pool:
        plan.append([(grade.american_profit(r["hot_odds"] if side == "hot"
                                            else r["cold_odds"]),
                      r["p_hot"] if side == "hot" else 1 - r["p_hot"]) for r in s])
    rng = random.Random(55)
    null = [max(sum(w if rng.random() < p else -1 for w, p in pl) / len(pl)
                for pl in plan) * 100 for _ in range(TRIALS)]
    pv = (sum(1 for x in null if x >= obs) + 1) / (len(null) + 1)
    md += ["## Does the best cell beat the grid?", "",
           f"- cells at n≥{MIN_CELL}: **{len(pool)}** (both directions, so "
           "choosing the direction after the fact is paid for)",
           f"- best: **{bl}** at {obs:+.1f}%",
           f"- biggest a price-redraw manufactures: median "
           f"**{st.median(null):+.1f}%**, 95th pct "
           f"**{sorted(null)[int(.95*len(null))]:+.1f}%**",
           f"- **corrected p = {pv:.3f}**", "",
           ("**Clears the grid.**" if pv < 0.05 else "**Does not clear.**"), ""]

    rh = random.Random(99)
    tag = [rh.random() < 0.5 for _ in bs]
    a = [r for r, t in zip(bs, tag) if t]
    b = [r for r, t in zip(bs, tag) if not t]
    if min(len(a), len(b)) >= MIN_HALF:
        md += [f"- split-half of **{bl}**: {_fmt(a, bside)} against "
               f"{_fmt(b, bside)}", "",
               "_Halves landing far apart means noise, whatever the pooled "
               "number says._", ""]

    md += ["## How to read this", "",
           "- the umpire has never been tested as a signal before; as a "
           "CONDITION on predictability it came back flat (p = 0.900)",
           "- hot bats alone are null in three earlier files, and "
           "line-against is the gate the live rule already uses, so anything "
           "here has to come from the interaction rather than the parts",
           "- nothing here changes the board.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "bats_ump_line.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
