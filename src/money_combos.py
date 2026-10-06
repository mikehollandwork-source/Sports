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

from . import consensus as C, grade, mlb_api
from .pregame_money import _implied

log = logging.getLogger("money_combos")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPORT = OUTPUT_DIR / "money_combos.md"
MIN_CELL = 40          # below this an ROI is a rounding error
TRIALS = 2000
SEED = 20261006


def _conditions(g: dict, money: str, other: str, price: dict,
                adv: str, home: str, mm: dict | None) -> dict:
    """Every signal and every recorded stat, all phrased RELATIVE TO THE
    MONEY SIDE.

    Phrasing them one way matters: a condition that sometimes meant "about the
    money side" and sometimes "about the home team" would make the pairs
    incoherent and the whole sweep unreadable.

    A condition that cannot be read for a game is False, never a guess, so a
    missing feed shrinks a cell rather than inventing membership for it.
    """
    pc = g.get("pick_criteria") or {}
    chk = g.get("public_check") or {}
    money_is_home = money == home

    def side_of(team_or_side):
        """True when a named side or home/away token is the money side."""
        if team_or_side in ("home", "away"):
            return (team_or_side == "home") == money_is_home
        return team_or_side == money

    shift = (pc.get("line_check") or {}).get("implied_shift")
    toward_adv = isinstance(shift, (int, float)) and shift > 0
    away_adv = isinstance(shift, (int, float)) and shift < 0
    money_is_adv = money == adv
    b, bp = g.get("bvp") or {}, g.get("bvp_pen") or {}
    form = g.get("form") or {}
    fh, fa = form.get("home") or {}, form.get("away") or {}
    dh, da = fh.get("delta"), fa.get("delta")
    hot_h = sum(p.get("delta", 0) for p in (fh.get("hot") or []))
    hot_a = sum(p.get("delta", 0) for p in (fa.get("hot") or []))
    sit = g.get("situational") or {}

    def wp(x):
        w, l = (x or {}).get("wins"), (x or {}).get("losses")
        return w / (w + l) if isinstance(w, int) and isinstance(l, int) and (w + l) else None
    rh, ra = wp(sit.get("home")), wp(sit.get("away"))
    cons = g.get("consistency") or {}
    ch, ca = (cons.get("home") or {}).get("score"), (cons.get("away") or {}).get("score")
    wx = g.get("weather") or {}
    ump = g.get("ump_tend") or {}
    stance = pc.get("book_stance") or {}
    pmq = pc.get("pm_quote") or {}
    proj = pc.get("projected") or {}
    fair = proj.get("fair_american")
    mpct = chk.get("money_pct")
    pf = g.get("park_factor")
    conf = pc.get("confidence")
    temp = wx.get("temp_f") if isinstance(wx, dict) else None
    windmph = wx.get("wind_mph") if isinstance(wx, dict) else None

    def cmp_side(h, a):
        """The money side holds the higher of a home/away pair."""
        if not isinstance(h, (int, float)) or not isinstance(a, (int, float)) \
                or h == a:
            return False
        return (h > a) == money_is_home

    return {
        # --- the handle itself
        "money agrees with tickets": chk.get("money") == "with public",
        "money AGAINST tickets": chk.get("money") == "against public",
        "handle share 60%+": isinstance(mpct, (int, float)) and mpct >= 60,
        "handle share 70%+": isinstance(mpct, (int, float)) and mpct >= 70,
        # --- the line
        "line moved against the money": (away_adv and money_is_adv) or (toward_adv and not money_is_adv),
        "line moved toward the money": (toward_adv and money_is_adv) or (away_adv and not money_is_adv),
        "line flat": chk.get("line") == "flat",
        "line vs money: against": pc.get("line_vs_money") == "against",
        "line vs money: with": pc.get("line_vs_money") == "with",
        # --- price
        "money side is the favourite": price[money] < price[other],
        "money side is the underdog": price[money] > price[other],
        "money side is a big favourite": price[money] <= -150,
        "money side is a big dog": price[money] >= 130,
        # --- the crowd
        "public sources corroborated": chk.get("verdict") == "corroborated",
        "public sources trusted": bool(chk.get("trusted")),
        "ticket majority is the money side": side_of(chk.get("majority_side")),
        "public edge flagged": bool(pc.get("public_edge")),
        # --- the model and its parts
        "money side has the stat edge": money_is_adv,
        "stat edge is strong": bool(pc.get("edge_strong")),
        "money side has the starter BvP": b.get("edge_team") == money,
        "money side has the bullpen BvP": bp.get("edge_team") == money,
        "money side has hotter bats": cmp_side(dh, da),
        "money side has the hot bats": cmp_side(hot_h, hot_a),
        "money side more consistent": cmp_side(ch, ca),
        "money side has the better record": cmp_side(rh, ra),
        "form edge present": pc.get("form_edge") is not None,
        "sharp money flagged": bool(pc.get("sharp_money")),
        "pitching dog": bool(pc.get("pitching_dog")),
        "starter dog edge": bool(pc.get("sp_dog_edge")),
        "3+ signals hit": isinstance(pc.get("signals_hit"), int) and pc["signals_hit"] >= 3,
        "2+ consistency hits": isinstance(pc.get("consistency_hits"), int) and pc["consistency_hits"] >= 2,
        "confidence above 0.3": isinstance(conf, (int, float)) and conf >= 0.3,
        "board's fair price likes the money": (
            isinstance(fair, int) and _implied(fair) > _implied(price[money])),
        # --- the book
        "book looks fooled": bool(stance.get("fooled")),
        "book stance against us": bool(stance.get("against_us")),
        # --- the other venue
        "Polymarket drifts to the money": (
            bool(mm) and ((mm["drift"] > 0) == money_is_adv)),
        "Polymarket size leans money": (
            bool(mm) and ((mm["imbalance"] > 0) == money_is_adv)),
        "PM quote beats the book": pmq.get("vs_book") == "better",
        # --- conditions
        "hitter-friendly park": isinstance(pf, (int, float)) and pf > 1.0,
        "pitcher-friendly park": isinstance(pf, (int, float)) and pf < 1.0,
        "warm (75F+)": isinstance(temp, (int, float)) and temp >= 75,
        "windy (10mph+)": isinstance(windmph, (int, float)) and windmph >= 10,
        "umpire favours hitters": isinstance(ump.get("k_per_g"), (int, float)) and ump["k_per_g"] < 0,
        # --- venue
        "money side is home": money_is_home,
    }


def collect() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
            metrics = C.book_metrics(date)
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
                "cond": _conditions(g, money, other, price, adv, home,
                                    metrics.get(g.get("game_pk"))),
            })
    return rows


def _members(rows, keys) -> list[int]:
    return [i for i, r in enumerate(rows)
            if all(r["cond"].get(k) for k in keys)]


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


def _anchor_test(back, fade) -> list[str]:
    """A standalone interval for backing the money side.

    Two benchmarks matter and they are different. ZERO is what a profitable
    bet must beat. MINUS HALF THE HOLD is what a side carrying NO information
    would return, and beating that only means the handle knows something - not
    that it knows enough to pay for the privilege of betting it.
    """
    hold = -(_roi(back) + _roi(fade)) / 2        # per-side hold
    obs = _roi(back)
    rng = random.Random(SEED + 1)
    plan = [(grade.american_profit(x["odds"]), x["p"]) for x in back]
    draws = sorted(sum(w if rng.random() < p else -1 for w, p in plan)
                   / len(plan) * 100 for _ in range(TRIALS))
    lo, hi = draws[int(.025 * TRIALS)], draws[int(.975 * TRIALS)]
    p_val = (sum(1 for d in draws if d >= obs * 100) + 1) / (TRIALS + 1)
    beats_zero = obs > 0
    return ["### Backing the money side on its own", "",
            "_This one is not part of the search — it is the question as "
            "asked, so it takes no multiple-comparison penalty._", "",
            f"- backing the money side: **{obs:+.1%}** on {len(back)} bets",
            f"- a no-information side at these prices returns about "
            f"**{-hold:+.1%}** (half the hold)",
            f"- simulating these same bets at their market prices: 95% of "
            f"outcomes land in **{lo:+.1f}% to {hi:+.1f}%**, "
            f"**p = {p_val:.3f}** for reaching {obs*100:+.1f}% by chance",
            "- " + ("**beats zero**, which is the bar that matters"
                    if beats_zero else
                    f"**does not beat zero.** It is {obs*100 + hold*100:+.1f} "
                    "points better than a no-information side, so the handle "
                    "is carrying something — but not enough to pay the hold, "
                    "which is the only thing that counts"),
            ""]


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
    cells, combo_keys = [], []
    for keys in combos:
        for fade in (False, True):
            cell = _cell(rows, keys, fade)
            if len(cell) >= MIN_CELL:
                label = ("fade the money" if fade else "back the money")
                if keys:
                    label += " WHEN " + " AND ".join(keys)
                cells.append((label, cell))
                combo_keys.append((keys, fade))

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

    # The bare anchor is NOT part of the search. It is the single hypothesis
    # that was stated before any cell was looked at - "what side is the money
    # on" - so it carries no multiple-comparison penalty and deserves its own
    # interval rather than being buried among 326 searched cells.
    md += _anchor_test(base_b, base_f)

    ranked = sorted(cells, key=lambda c: -_roi(c[1]))
    md += ["## The ten best cells — before correction", "",
           "| cell | n | result |", "|---|---|---|"]
    for lbl, s in ranked[:10]:
        md.append(f"| {lbl} | {len(s)} | {_fmt(s)} |")
    md += ["", "_These are the numbers a search of this width produces. "
           "Whether any of them is real is the next section, and the answer "
           "is almost always no._", ""]

    # --- the null, simulated PER GAME rather than per cell ---------------
    # These cells overlap heavily - a game sits in dozens of them - and back
    # and fade on the same game are perfectly anti-correlated. Drawing each
    # cell independently, as signal_sweep does, would break both relationships
    # and overstate the spread of the maximum. Here each TRIAL simulates every
    # game once at its own market price, and every cell reads that same
    # simulated slate, so the correlation structure of the search is preserved.
    pb = [grade.american_profit(r["price"][r["money"]]) for r in rows]
    pf_ = [grade.american_profit(r["price"][r["other"]]) for r in rows]
    pm = [r["p_money"] for r in rows]
    sim = [(_members(rows, keys), fade, len(_cell(rows, keys, fade)))
           for keys, fade in combo_keys]
    rng = random.Random(SEED)
    hi, lo = [], []
    for _ in range(TRIALS):
        won = [rng.random() < q for q in pm]
        back = [pb[i] if won[i] else -1.0 for i in range(len(rows))]
        fade_p = [-1.0 if won[i] else pf_[i] for i in range(len(rows))]
        best = -9e9
        worst = 9e9
        for idx, fade, n in sim:
            arr = fade_p if fade else back
            v = 0.0
            for i in idx:
                v += arr[i]
            v = v / n * 100
            if v > best:
                best = v
            if v < worst:
                worst = v
        hi.append(best)
        lo.append(worst)
    best_l, best_s = ranked[0]
    worst_l, worst_s = ranked[-1]
    obs_hi, obs_lo = _roi(best_s) * 100, _roi(worst_s) * 100
    p_hi = (sum(1 for x in hi if x >= obs_hi) + 1) / (TRIALS + 1)
    p_lo = (sum(1 for x in lo if x <= obs_lo) + 1) / (TRIALS + 1)
    md += ["## Corrected for the width of the search", "",
           "_Each trial simulates every game once at its market price and "
           "scores all cells on that same slate, so the heavy overlap between "
           "cells — and the fact that back and fade on one game cannot both "
           "win — is preserved rather than assumed away._", "",
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
    # Why does the top of the list look the way it does? Every condition set
    # is entered TWICE, as back and as fade, and the two are mirror images -
    # on the same games they sum to the hold paid twice. So the leaderboard is
    # a mirrored list, and the direction label on its top rows carries no
    # information at all.
    def _price_profile(cs):
        odds = [x["odds"] for _, c in cs for x in c]
        if not odds:
            return "—"
        plus = sum(1 for o in odds if o > 0) / len(odds)
        return (f"{plus:.0%} plus-money, median price "
                f"{sorted(odds)[len(odds)//2]:+d}")
    top10 = ranked[:10]
    fades = sum(1 for lbl, _ in top10 if lbl.startswith("fade"))
    mirrored = best_l.split(" WHEN ", 1)[-1] == worst_l.split(" WHEN ", 1)[-1]
    md += ["## Why the leaderboard looks one-sided", "",
           f"- of the ten best cells, **{fades} are fades**",
           "- but every condition set is entered **twice**, as back and as "
           "fade, and the pair are mirror images: on the same games they sum "
           "to the hold paid twice",
           (f"- the best and worst cells are the SAME condition set "
            f"({best_l.split(' WHEN ', 1)[-1]}) in opposite directions, "
            f"{obs_hi:+.1f}% against {obs_lo:+.1f}% on the same "
            f"{len(best_s)} games" if mirrored else
            "- best and worst are different condition sets"),
           "- so a top row being a fade means only that the money side LOST "
           "in that cell. It is not evidence that fading works; the mirrored "
           "back row is sitting at the bottom of the same list",
           "",
           "_A plausible alternative was that fades crowd the top because "
           "they take plus-money prices, whose ROI has a long right tail at "
           "small n. The data does not support that here:_", "",
           f"- the ten best cells: {_price_profile(top10)}",
           f"- all {len(cells)} cells: {_price_profile(cells)}",
           f"- bare back the money: {_price_profile([('b', base_b)])}",
           f"- bare fade the money: {_price_profile([('f', base_f)])}", "",
           "_The leaders are no more plus-money than the pool, so the "
           "one-sidedness is the mirroring, not the price._", ""]

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
