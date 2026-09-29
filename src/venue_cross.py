"""
Every side the two markets can name, crossed, and both directions of each.

THE REQUEST
Take a side from Polymarket, take a side from Kalshi, do the opposite of each,
and use the two markets against each other to confirm.

ONE PIECE OF ARITHMETIC FIRST, BECAUSE IT SHAPES THE ANSWER
Where the venues DISAGREE, "take Kalshi" and "take Polymarket" are the same bet
inverted - backing one is fading the other. Those two cells therefore sum to
about minus twice the hold by construction and cannot both be positive. So the
flip is already inside the straight version, and the open question is only which
venue is right when they split: one number, not four. The table prints both
anyway so the identity is visible rather than asserted.

The same holds for every BACK/FADE pair here, which is why the `sum` column
exists: both directions pay the vig, so a signal at -6% does not have a +6%
fade waiting behind it. Only a signal summing well below the median is wrong by
more than the vig.

WHY RE-TEST A FAMILY ALREADY SWEPT
`signal_sweep2` covered Kalshi drift, Kalshi size, Kalshi's closing favourite,
both-venues-agree and disagree-take-Kalshi. Everything landed on the vig: sums
-4.2% to -5.8%, best cell +1.3%. That is the honest prior here.

What is new is a reason to look again. Measured against the sportsbook's own
de-vigged price, Kalshi is off by 0.007 where the venues agree and 0.018 where
they diverge; Polymarket by 0.038 and 0.206. One venue is five to eleven times
more accurate than the other, and the earlier sweep treated them as peers. The
cross cells - one venue's drift with the other's resting size, and agreement
measured across different quantities - were never tested at all.

CORRECTION
Roughly thirty cells. Best and worst both corrected by a shared-redraw
permutation with winners drawn from de-vigged prices, then split-halved. With
this many cells the correction is most of the work, which is the point.

Writes output/venue_cross.md.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
import random
import statistics as st
from pathlib import Path

from . import consensus as C, grade, mlb_api, pm_books
from .pregame_money import _implied
from .venue_swap import _metrics

log = logging.getLogger("venue_cross")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 10000
MIN_CELL = 60


def collect() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
            books = (pm_books.load_day(date) or {}).get("games") or {}
        except Exception:
            continue
        for g in json.loads(Path(f).read_text()).get("games", []):
            pk = g.get("game_pk")
            res = results.get(pk)
            m = g.get("matchup") or ""
            if not res or not res.get("final") or not res.get("winner") or " @ " not in m:
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            away, home = m.split(" @ ")
            if adv not in (away, home) or not isinstance(a_ml, int) \
                    or not isinstance(o_ml, int):
                continue
            opp = home if adv == away else away
            tot = _implied(a_ml) + _implied(o_ml)
            gb = books.get(str(pk)) or {}
            side = gb.get("side")
            start = gb.get("game_datetime") or g.get("game_datetime")
            if tot <= 0 or side not in (away, home) or not start:
                continue
            try:
                cut = (dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
                       - C.LOCK_LEAD).timestamp()
            except ValueError:
                continue
            flip = 1 if side == adv else -1     # both logs are `side`'s token
            P = _metrics(gb.get("readings"), cut)
            K = _metrics(gb.get("k_readings"), cut)
            maj = (g.get("public_majority") or {}).get("team")
            rows.append({
                "date": date, "winner": res["winner"], "adv": adv, "opp": opp,
                "price": {adv: a_ml, opp: o_ml},
                "p_adv": _implied(a_ml) / tot,
                "money": maj if maj in (away, home)
                and (g.get("public_check") or {}).get("money") == "with public" else None,
                "P": {"drift": P["drift"] * flip,
                      "size": P["imbalance"] * flip} if P else None,
                "K": {"drift": K["drift"] * flip,
                      "size": K["imbalance"] * flip} if K else None,
            })
    return rows


def _side(r, venue, key):
    v = r.get(venue)
    if not v or v[key] == 0:
        return None
    return r["adv"] if v[key] > 0 else r["opp"]


def sides(r: dict) -> dict:
    Pd, Kd = _side(r, "P", "drift"), _side(r, "K", "drift")
    Ps, Ks = _side(r, "P", "size"), _side(r, "K", "size")
    out = {
        "Polymarket drift": Pd,
        "Kalshi drift": Kd,
        "Polymarket resting size": Ps,
        "Kalshi resting size": Ks,
        # --- the two markets against each other, on drift ---
        "drift: both venues agree": Pd if (Pd and Pd == Kd) else None,
        "drift: they split — take Kalshi": Kd if (Pd and Kd and Pd != Kd) else None,
        "drift: they split — take Polymarket": Pd if (Pd and Kd and Pd != Kd) else None,
        # --- and on resting size ---
        "size: both venues agree": Ps if (Ps and Ps == Ks) else None,
        "size: they split — take Kalshi": Ks if (Ps and Ks and Ps != Ks) else None,
        # --- the cross cells, never tested ---
        "Kalshi drift + Polymarket size agree": (
            Kd if (Kd and Ps and Kd == Ps) else None),
        "Polymarket drift + Kalshi size agree": (
            Pd if (Pd and Ks and Pd == Ks) else None),
        "Kalshi drift, Polymarket size DISAGREES": (
            Kd if (Kd and Ps and Kd != Ps) else None),
        # --- all four quantities pointing one way ---
        "all four point the same way": (
            Pd if (Pd and Pd == Kd == Ps == Ks) else None),
        # --- against the money ---
        "both venues confirm the money side": (
            r["money"] if (r["money"] and Pd == r["money"] and Kd == r["money"])
            else None),
        "both venues contradict the money side": (
            r["money"] if (r["money"] and Pd and Kd and Pd != r["money"]
                           and Kd != r["money"]) else None),
    }
    return out


PAIRS = [("drift: they split — take Kalshi", "drift: they split — take Polymarket")]


def _view(rows, sig, fade=False):
    out = []
    for r in rows:
        s = sides(r).get(sig)
        if not s or s not in r["price"]:
            continue
        bet = (r["opp"] if s == r["adv"] else r["adv"]) if fade else s
        p = r["p_adv"] if bet == r["adv"] else 1 - r["p_adv"]
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
    order = list(sides(rows[0]) if rows else {})
    md = ["# Both markets, every side they name, and the opposite of each", "",
          "_**One piece of arithmetic first.** Where the venues disagree, \"take "
          "Kalshi\" and \"take Polymarket\" are the same bet inverted — backing one "
          "IS fading the other. Those cells sum to about minus twice the hold by "
          "construction and cannot both be positive, so the flip is already "
          "inside the straight version and the open question is only which venue "
          "is right when they split. Both are printed so the identity is visible "
          "rather than asserted._", "",
          "_The same holds for every BACK/FADE pair, which is what the `sum` "
          "column is for: both directions pay the vig, so a cell at −6% has no "
          "+6% fade behind it._", "",
          "_`signal_sweep2` already swept Kalshi drift, Kalshi size, both-agree "
          "and split-take-Kalshi: everything landed on the vig. What is new is a "
          "reason to look again — Kalshi sits 0.007 from the book's de-vigged "
          "price where the venues agree and 0.018 where they diverge, against "
          "Polymarket's 0.038 and 0.206, and the earlier sweep treated the two as "
          "peers. The cross cells were never tested at all._", "",
          f"- graded games: **{len(rows)}**",
          f"- with both venues readable: "
          f"**{sum(1 for r in rows if r['P'] and r['K'])}**", ""]
    if len(rows) < 300:
        return "\n".join(md + ["Not enough games.", ""])

    md += ["| side named by | n | BACK it | FADE it | sum |", "|---|---|---|---|---|"]
    cells, sums = [], []
    for sig in order:
        bk, fd = _view(rows, sig), _view(rows, sig, fade=True)
        if len(bk) < MIN_CELL:
            md.append(f"| {sig} | {len(bk)} | _too few_ | | |")
            continue
        s = (_roi(bk) + _roi(fd)) * 100
        sums.append(s)
        cells += [(f"back {sig}", bk), (f"fade {sig}", fd)]
        md.append(f"| {sig} | {len(bk)} | {_fmt(bk)} | {_fmt(fd)} | {s:+.1f}% |")
    md.append("")
    if sums:
        md += [f"_Median `sum`: **{st.median(sums):+.1f}%** — the hold, paid "
               "twice. A cell summing near that carries nothing in either "
               "direction._", ""]

    for a, b in PAIRS:
        va, vb = _view(rows, a), _view(rows, b)
        if va and vb:
            md += [f"_Identity check: backing **{a}** is {_roi(va):+.1%} and "
                   f"backing **{b}** is {_roi(vb):+.1%}; they sum to "
                   f"**{(_roi(va)+_roi(vb))*100:+.1f}%**, which is the hold "
                   "twice over — as they must, being the same games opposite "
                   "ways._", ""]

    pool = [(l, s) for l, s in cells if len(s) >= MIN_CELL]
    if not pool:
        return "\n".join(md)
    plan = [[(grade.american_profit(x["odds"]), x["p"]) for x in s] for _, s in pool]
    rng = random.Random(6464)
    hi, lo = [], []
    for _ in range(TRIALS):
        vals = [sum(w if rng.random() < p else -1 for w, p in pl) / len(pl)
                for pl in plan]
        hi.append(max(vals) * 100)
        lo.append(min(vals) * 100)
    best_l, best_s = max(pool, key=lambda c: _roi(c[1]))
    worst_l, worst_s = min(pool, key=lambda c: _roi(c[1]))
    obs_hi, obs_lo = _roi(best_s) * 100, _roi(worst_s) * 100
    p_hi = (sum(1 for x in hi if x >= obs_hi) + 1) / (TRIALS + 1)
    p_lo = (sum(1 for x in lo if x <= obs_lo) + 1) / (TRIALS + 1)
    md += [f"## Corrected across {len(pool)} cells, both tails", "",
           f"- best: **{best_l}** at {obs_hi:+.1f}% (n={len(best_s)}) · redraws "
           f"reach {st.median(hi):+.1f}% median, "
           f"{sorted(hi)[int(.95*TRIALS)]:+.1f}% at the 95th · "
           f"**corrected p = {p_hi:.3f}**",
           f"- worst: **{worst_l}** at {obs_lo:+.1f}% (n={len(worst_s)}) · "
           f"redraws reach {st.median(lo):+.1f}% median, "
           f"{sorted(lo)[int(.05*TRIALS)]:+.1f}% at the 5th · "
           f"**corrected p = {p_lo:.3f}**", ""]
    rh = random.Random(7575)
    for lab, cell in ((best_l, best_s), (worst_l, worst_s)):
        tag = [rh.random() < 0.5 for _ in cell]
        a = [x for x, t in zip(cell, tag) if t]
        b = [x for x, t in zip(cell, tag) if not t]
        if min(len(a), len(b)) >= 25:
            md.append(f"- split-half of **{lab}**: {_fmt(a)} (n={len(a)}) "
                      f"against {_fmt(b)} (n={len(b)})")
    md += ["", "## Reading it", "",
           "- a cell is worth something only if BACK beats the vig, it survives "
           "the correction, and both halves agree in sign",
           "- the two \"they split\" rows are one fact stated twice; their sum "
           "being the double hold is a check that the arithmetic is right, not a "
           "finding",
           "- **agreement cells shrink the sample.** Both venues pointing the "
           "same way is a smaller, easier population, so compare their n before "
           "their ROI", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "venue_cross.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
