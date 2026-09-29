"""
Every signal, isolated, both directions, with the vig made visible.

THE REQUEST AND THE CORRECTION IT NEEDS
"Isolate all the signals and test them individually; if one is a clear loser,
test the other side." The first half is right. The second half has a trap in
it worth stating before any number appears.

A losing signal is NOT automatically a winning fade. Both directions pay the
hold. On the same games, backing a side and backing its opponent sum to about
MINUS TWICE THE VIG, not to zero:

    back the signal    -6%
    fade the signal    -3%      <- not +6%

So a fade only pays when the signal is wrong by MORE than the vig. Every row
here prints both directions and their sum, so that bar is visible rather than
assumed - if the two add to roughly -9%, the signal is worthless in both
directions and neither number is an opportunity.

WHAT IS SWEPT
Every side-naming signal the board carries: the stat model, starter and
bullpen batter-vs-pitcher, form (two ways), line movement, tickets, handle,
the two prediction-market venues (drift and resting size), Polymarket's quote
against the book, the board's own fair price, and team record. Plus three
baselines - home teams, favourites, underdogs - because a signal that only
matches "back the favourite" is not a signal.

CORRECTED IN BOTH TAILS
Looking for losers to fade means the MINIMUM matters as much as the maximum,
and picking whichever tail looks better after the fact is the error that
`margin_form` caught. So the permutation records both the best and the worst
cell of each redraw, and the two are corrected separately.

Writes output/signal_sweep.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
from pathlib import Path

from . import consensus as C, grade, mlb_api
from .pregame_money import _implied

log = logging.getLogger("signal_sweep")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 3000
MIN_CELL = 60


def collect() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
            metrics = C.book_metrics(date)
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
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            away, home = m.split(" @ ")
            if adv not in (away, home):
                continue
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0:
                continue

            b, bp = g.get("bvp") or {}, g.get("bvp_pen") or {}
            form = g.get("form") or {}
            fh, fa = form.get("home") or {}, form.get("away") or {}
            dh, da = fh.get("delta"), fa.get("delta")
            hot_h = sum(p.get("delta", 0) for p in (fh.get("hot") or []))
            hot_a = sum(p.get("delta", 0) for p in (fa.get("hot") or []))
            shift = (pc.get("line_check") or {}).get("implied_shift")
            chk = g.get("public_check") or {}
            ms, maj = chk.get("money_side"), chk.get("majority_side")
            sit = g.get("situational") or {}
            sh, sa = sit.get("home") or {}, sit.get("away") or {}
            wp = lambda s: (s["wins"] / (s["wins"] + s["losses"])
                            if isinstance(s.get("wins"), int)
                            and isinstance(s.get("losses"), int)
                            and (s["wins"] + s["losses"]) else None)          # noqa: E731
            rh, ra = wp(sh), wp(sa)
            mm = metrics.get(g.get("game_pk"))
            pmq = pc.get("pm_quote") or {}
            proj = pc.get("projected") or {}
            fair = proj.get("fair_american")

            sides = {
                "stat model (advantage_team)": adv,
                "starter BvP": b.get("edge_team"),
                "bullpen BvP": bp.get("edge_team"),
                "hotter bats (team delta)": (
                    (home if dh > da else away)
                    if isinstance(dh, (int, float)) and isinstance(da, (int, float))
                    and dh != da else None),
                "hot bats (sum of top bats)": (
                    (home if hot_h > hot_a else away) if hot_h != hot_a else None),
                "line moved TOWARD": ((adv if shift > 0 else opp)
                                      if isinstance(shift, (int, float)) and shift else None),
                "ticket majority": ((home if maj == "home" else away)
                                    if maj in ("home", "away") else None),
                "handle majority": ((home if ms == "home" else away)
                                    if ms in ("home", "away") else None),
                "Polymarket drift": ((adv if mm["drift"] > 0 else opp) if mm else None),
                "Polymarket size lean": (
                    (adv if mm["imbalance"] > 0 else opp) if mm else None),
                "PM quote beats book": (adv if pmq.get("vs_book") == "better" else None),
                "board's own fair price": (
                    (adv if _implied(fair) > _implied(a_ml) else opp)
                    if isinstance(fair, int) else None),
                "better record": ((home if rh > ra else away)
                                  if rh is not None and ra is not None and rh != ra else None),
                "— home team": home,
                "— the favourite": min(price, key=lambda t: price[t]),
                "— the underdog": max(price, key=lambda t: price[t]),
            }
            rows.append({"date": date, "winner": res["winner"], "price": price,
                         "adv": adv, "opp": opp, "sides": sides,
                         "p_adv": _implied(a_ml) / tot})
    return rows


def _view(rows, sig, fade=False):
    out = []
    for r in rows:
        s = r["sides"].get(sig)
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


SIGNALS = ["stat model (advantage_team)", "starter BvP", "bullpen BvP",
           "hotter bats (team delta)", "hot bats (sum of top bats)",
           "line moved TOWARD", "ticket majority", "handle majority",
           "Polymarket drift", "Polymarket size lean", "PM quote beats book",
           "board's own fair price", "better record",
           "— home team", "— the favourite", "— the underdog"]


def build() -> str:
    rows = collect()
    md = ["# Every signal, isolated, both directions", "",
          "_**A losing signal is not automatically a winning fade.** Both "
          "directions pay the hold, so on the same games backing a side and "
          "backing its opponent sum to about MINUS TWICE THE VIG, not to "
          "zero. A fade only pays when the signal is wrong by more than the "
          "vig — the `sum` column is that bar, made visible._", "",
          f"- graded games: **{len(rows)}**", ""]
    if len(rows) < 300:
        return "\n".join(md + ["Not enough graded games.", ""])

    md += ["| signal | n | BACK it | FADE it | sum |", "|---|---|---|---|---|"]
    cells = []
    for sig in SIGNALS:
        bk, fd = _view(rows, sig), _view(rows, sig, fade=True)
        if len(bk) < MIN_CELL:
            md.append(f"| {sig} | {len(bk)} | _too few_ | | |")
            continue
        s = (_roi(bk) + _roi(fd)) * 100
        cells += [(f"back {sig}", bk), (f"fade {sig}", fd)]
        md.append(f"| {sig} | {len(bk)} | {_fmt(bk)} | {_fmt(fd)} | "
                  f"{s:+.1f}% |")
    md.append("")

    sums = []
    for sig in SIGNALS:
        bk, fd = _view(rows, sig), _view(rows, sig, fade=True)
        if len(bk) >= MIN_CELL:
            sums.append((_roi(bk) + _roi(fd)) * 100)
    if sums:
        md += [f"_Median `sum` across all signals: **{st.median(sums):+.1f}%**. "
               "That is the hold, paid twice. A signal whose two directions "
               "sum to about that is carrying no information either way, and "
               "neither of its numbers is an opportunity — however bad one of "
               "them looks._", ""]

    # --- corrected in BOTH tails ------------------------------------------
    pool = [(l, s) for l, s in cells if len(s) >= MIN_CELL]
    if pool:
        best_l, best_s = max(pool, key=lambda c: _roi(c[1]))
        worst_l, worst_s = min(pool, key=lambda c: _roi(c[1]))
        plan = [[(grade.american_profit(x["odds"]), x["p"]) for x in s]
                for _, s in pool]
        rng = random.Random(303)
        hi, lo = [], []
        for _ in range(TRIALS):
            vals = [sum(w if rng.random() < p else -1 for w, p in pl) / len(pl)
                    for pl in plan]
            hi.append(max(vals) * 100)
            lo.append(min(vals) * 100)
        obs_hi, obs_lo = _roi(best_s) * 100, _roi(worst_s) * 100
        p_hi = (sum(1 for x in hi if x >= obs_hi) + 1) / (TRIALS + 1)
        p_lo = (sum(1 for x in lo if x <= obs_lo) + 1) / (TRIALS + 1)
        md += ["## Corrected in both tails", "",
               "_Hunting for losers to fade means the MINIMUM matters as much "
               "as the maximum, and choosing whichever tail looks better "
               "afterwards is the error `margin_form` caught. Both are "
               "corrected separately._", "",
               f"- cells at n≥{MIN_CELL}: **{len(pool)}**",
               f"- best: **{best_l}** at {obs_hi:+.1f}% · redraws reach "
               f"{st.median(hi):+.1f}% median · **corrected p = {p_hi:.3f}**",
               f"- worst: **{worst_l}** at {obs_lo:+.1f}% · redraws reach "
               f"{st.median(lo):+.1f}% median · **corrected p = {p_lo:.3f}**", "",
               ("**Something clears.**" if min(p_hi, p_lo) < 0.05 else
                "**Neither tail clears.** The extremes are what a sweep this "
                "wide produces from noise."), ""]

        for lbl, sub in ((best_l, best_s), (worst_l, worst_s)):
            rh2 = random.Random(hash(lbl) % 9999)
            tag = [rh2.random() < 0.5 for _ in sub]
            a = [x for x, t in zip(sub, tag) if t]
            b = [x for x, t in zip(sub, tag) if not t]
            if min(len(a), len(b)) >= 25:
                md.append(f"- split-half of **{lbl}**: {_fmt(a)} (n={len(a)}) "
                          f"against {_fmt(b)} (n={len(b)})")
        md.append("")

    md += ["## How to read this", "",
           "- the three rows beginning `—` are baselines, not signals; a "
           "signal that merely matches 'back the favourite' has found nothing",
           "- the `sum` column is the test of the fade idea: only a signal "
           "summing well BELOW the median is wrong by more than the vig and "
           "worth fading",
           "- nothing here changes the board.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "signal_sweep.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
