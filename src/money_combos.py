"""
The money side, crossed with everything else on the board.

THE REQUEST
"Look at every game we've graded, take what side the money is on, and pair it
with every other stat in different combinations to find a positive ROI."

WHY THE ANCHOR IS NEW AND THE SEARCH IS NOT
Six sweeps in this repo have already hunted for a profitable rule and all six
came back null - `signal_sweep` (best corrected p=0.974), `signal_sweep2`
(0.630), `stat_combos` (0.067), `stat_subsets` (0.825), `gate_sweep` (0.415).
What none of them did was ANCHOR on the handle and treat everything else as a
filter on it, which is what was asked, so the cells here are genuinely
different even though the machinery is the same.

THE ARITHMETIC OF THE SEARCH, STATED BEFORE THE NUMBERS
    2 directions (back the money / fade it)
    x (1 bare + 16 single conditions + 120 pairs)
    = 274 cells

With 274 cells the best one is GUARANTEED to look profitable. That is not a
risk, it is arithmetic. A sweep of this width has to be read against what the
same sweep produces from noise, which is why every number below is corrected by
the max statistic rather than reported on its own.

THE NULL
Each bet is resimulated at its own market-implied probability, then the MAXIMUM
across all 274 cells is taken, and that is repeated TRIALS times. This is the
right null for a question about ROI: it asks what the best cell of a search
this wide reaches when every bet is priced fairly. It bakes the vig in
correctly - under fair pricing expected ROI is minus the hold, not zero. Same
construction as `signal_sweep`, deliberately, so the numbers are comparable.

Both tails are corrected separately, because hunting for something to FADE
makes the minimum as meaningful as the maximum, and picking whichever tail
looks better afterwards is a bias this repo has already been caught by.

READ THE FADE COLUMN WITH THE VIG IN MIND
A losing cell is not automatically a winning fade. On the same games, backing a
side and backing its opponent sum to roughly MINUS TWICE THE HOLD, not zero.

Read-only. Writes output/money_combos.md. Changes no pick.
"""

from __future__ import annotations

import glob
import itertools
import json
import logging
import random
import statistics as st
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import _implied

log = logging.getLogger("money_combos")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPORT = OUTPUT_DIR / "money_combos.md"
MIN_CELL = 40          # below this an ROI is a rounding error
TRIALS = 2000
SEED = 20261006


def _conditions(g: dict, money: str, other: str, price: dict,
                adv: str, home: str) -> dict:
    """Binary filters, all phrased RELATIVE TO THE MONEY SIDE.

    Phrasing them all one way matters: a condition that sometimes means "about
    the money side" and sometimes "about the home team" would make the pairs
    incoherent.
    """
    pc = g.get("pick_criteria") or {}
    chk = g.get("public_check") or {}
    maj = chk.get("majority_side")
    maj_team = (home if maj == "home" else
                (other if home == money else money)) if maj else None
    shift = (pc.get("line_check") or {}).get("implied_shift")
    toward_adv = (isinstance(shift, (int, float)) and shift > 0)
    away_from_adv = (isinstance(shift, (int, float)) and shift < 0)
    line_toward_money = ((toward_adv and money == adv)
                         or (away_from_adv and money != adv))
    line_against_money = ((away_from_adv and money == adv)
                          or (toward_adv and money != adv))
    b = g.get("bvp") or {}
    form = g.get("form") or {}
    fh = (form.get("home") or {}).get("delta")
    fa = (form.get("away") or {}).get("delta")
    hotter = None
    if isinstance(fh, (int, float)) and isinstance(fa, (int, float)) and fh != fa:
        hotter = home if fh > fa else other if home == money else money
    sit = g.get("situational") or {}

    def wp(s):
        w, l = (s or {}).get("wins"), (s or {}).get("losses")
        return w / (w + l) if isinstance(w, int) and isinstance(l, int) and (w + l) else None
    rh, ra = wp(sit.get("home")), wp(sit.get("away"))
    better = None
    if rh is not None and ra is not None and rh != ra:
        better = home if rh > ra else (other if home == money else money)
    mpct = chk.get("money_pct")
    pf = g.get("park_factor")
    stance = pc.get("book_stance") or {}
    return {
        "money agrees with tickets": chk.get("money") == "with public",
        "money AGAINST tickets": chk.get("money") == "against public",
        "line moved against the money": line_against_money,
        "line moved toward the money": line_toward_money,
        "line flat": chk.get("line") == "flat",
        "money side is the favourite": price[money] < price[other],
        "money side is the underdog": price[money] > price[other],
        "money side is home": money == home,
        "public sources corroborated": chk.get("verdict") == "corroborated",
        "public sources trusted": bool(chk.get("trusted")),
        "money side has the stat edge": money == adv,
        "money side has the BvP edge": b.get("edge_team") == money,
        "money side has the better record": better == money,
        "money side has hotter bats": hotter == money,
        "hitter-friendly park": isinstance(pf, (int, float)) and pf > 1.0,
        "handle share 65%+": isinstance(mpct, (int, float)) and mpct >= 65,
        "book looks fooled": bool(stance.get("fooled")),
        "ticket majority is the money side": maj_team == money,
    }


def collect() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
        except Exception as exc:
            log.warning("%s: results unavailable (%s)", date, exc)
            continue
        for g in json.loads(Path(f).read_text()).get("games", []):
            res = results.get(g.get("game_pk"))
            m = g.get("matchup") or ""
            if not res or not res.get("final") or not res.get("winner") \
                    or " @ " not in m:
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            away, home = m.split(" @ ")
            if adv not in (away, home):
                continue
            chk = g.get("public_check") or {}
            side = chk.get("money_side")
            if side not in ("home", "away"):
                continue                 # no money read -> not this question
            money = home if side == "home" else away
            other = away if side == "home" else home
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0 or money not in price:
                continue
            rows.append({
                "date": date, "winner": res["winner"], "price": price,
                "money": money, "other": other,
                "p_money": (_implied(price[money]) / tot),
                "cond": _conditions(g, money, other, price, adv, home),
            })
    return rows


def _cell(rows, keys, fade=False):
    out = []
    for r in rows:
        if not all(r["cond"].get(k) for k in keys):
            continue
        bet = r["other"] if fade else r["money"]
        p = (1 - r["p_money"]) if fade else r["p_money"]
        out.append({"odds": r["price"][bet], "won": r["winner"] == bet, "p": p})
    return out


def _roi(rs) -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(x["odds"]) if x["won"] else -1
               for x in rs) / len(rs)


def _fmt(rs) -> str:
    if not rs:
        return "—"
    w = sum(1 for x in rs if x["won"])
    return f"{w}-{len(rs)-w} · **{_roi(rs):+.1%}**"


def build() -> str:
    rows = collect()
    md = ["# The money side, crossed with everything else", "",
          "_Every graded game that carries a handle read, anchored on the side "
          "the money is on, filtered by every other board stat singly and in "
          "pairs._", "",
          f"- graded games with a money side: **{len(rows)}**", ""]
    if len(rows) < 200:
        return "\n".join(md + ["_Not enough graded games._", ""])

    names = list(next(iter(rows))["cond"])
    combos = [()] + [(k,) for k in names] + list(itertools.combinations(names, 2))
    cells = []
    for keys in combos:
        for fade in (False, True):
            s = _cell(rows, keys, fade)
            if len(s) >= MIN_CELL:
                label = ("fade the money" if fade else "back the money")
                if keys:
                    label += " WHEN " + " AND ".join(keys)
                cells.append((label, s))

    base_b, base_f = _cell(rows, ()), _cell(rows, (), fade=True)
    md += ["## The anchor, before any filter", "",
           "| | n | result |", "|---|---|---|",
           f"| back the money side | {len(base_b)} | {_fmt(base_b)} |",
           f"| fade the money side | {len(base_f)} | {_fmt(base_f)} |", "",
           f"_Those two sum to {(_roi(base_b)+_roi(base_f))*100:+.1f}%, which is "
           "the hold paid twice. Any filtered cell has to beat that bar, not "
           "zero._", "",
           f"- cells at n≥{MIN_CELL}: **{len(cells)}** "
           f"(from {len(combos)} combinations × 2 directions)", ""]

    ranked = sorted(cells, key=lambda c: -_roi(c[1]))
    md += ["## The ten best cells — before correction", "",
           "| cell | n | result |", "|---|---|---|"]
    for lbl, s in ranked[:10]:
        md.append(f"| {lbl} | {len(s)} | {_fmt(s)} |")
    md += ["", "_These are the numbers a search of this width produces. "
           "Whether any of them is real is the next section, and the answer "
           "is almost always no._", ""]

    plan = [[(grade.american_profit(x["odds"]), x["p"]) for x in s]
            for _, s in cells]
    rng = random.Random(SEED)
    hi, lo = [], []
    for _ in range(TRIALS):
        vals = [sum(w if rng.random() < p else -1 for w, p in pl) / len(pl)
                for pl in plan]
        hi.append(max(vals) * 100)
        lo.append(min(vals) * 100)
    best_l, best_s = ranked[0]
    worst_l, worst_s = ranked[-1]
    obs_hi, obs_lo = _roi(best_s) * 100, _roi(worst_s) * 100
    p_hi = (sum(1 for x in hi if x >= obs_hi) + 1) / (TRIALS + 1)
    p_lo = (sum(1 for x in lo if x <= obs_lo) + 1) / (TRIALS + 1)
    md += ["## Corrected for the width of the search", "",
           f"- best: **{best_l}** at {obs_hi:+.1f}% (n={len(best_s)}) · "
           f"a redraw's best reaches {st.median(hi):+.1f}% median, "
           f"{sorted(hi)[int(.95*len(hi))]:+.1f}% at the 95th · "
           f"**corrected p = {p_hi:.3f}**",
           f"- worst: **{worst_l}** at {obs_lo:+.1f}% (n={len(worst_s)}) · "
           f"a redraw's worst reaches {st.median(lo):+.1f}% median · "
           f"**corrected p = {p_lo:.3f}**", "",
           ("**Something clears.** Split-half it below before believing it."
            if min(p_hi, p_lo) < 0.05 else
            "**Nothing clears.** The best cell is inside what this search "
            "produces from noise, so there is no rule here to ship."), ""]

    for lbl, sub in ((best_l, best_s), (worst_l, worst_s)):
        r2 = random.Random(abs(hash(lbl)) % 9999)
        tag = [r2.random() < 0.5 for _ in sub]
        a = [x for x, t in zip(sub, tag) if t]
        b = [x for x, t in zip(sub, tag) if not t]
        if min(len(a), len(b)) >= 20:
            md.append(f"- split-half of **{lbl}**: {_fmt(a)} (n={len(a)}) "
                      f"against {_fmt(b)} (n={len(b)})")
    md += ["", "## How to read this", "",
           "- the corrected p is the whole answer; an uncorrected +15% from a "
           "274-cell search is the expected best from noise, not an edge",
           "- a cell only matters if it clears correction AND both halves "
           "agree AND it beats the two-directions-sum bar above",
           "- nothing here changes the board.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    OUTPUT_DIR.mkdir(exist_ok=True)
    text = build()
    REPORT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
