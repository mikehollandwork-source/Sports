"""
When everything says blowout and the price says close, who is right?

THE QUESTION
A team that is better on paper - better record, the stat model likes them,
the hotter bats - priced only -160 against a poor opponent. The price looks
short for the mismatch. Is that the market knowing something the mismatch
does not?

WHY THIS IS NOT `divergence` AGAIN
`divergence` compared the market to OUR stat model and found the model's
deviation anti-informative. This compares the market to the two teams'
RECORDS, which are not our model and not our opinion - they are the plainest
fact available about who is better, and they sit on 97% of games in
`situational`, never used as a signal.

So the statistic is a residual: how much more or less confident the price is
than the quality gap alone would suggest.

    quality gap   favourite's win% minus underdog's win%
    price         de-vigged probability of the favourite
    residual      percentile(price) - percentile(quality gap)

A negative residual is the user's scenario: the records say mismatch, the
price says close. A positive one is the opposite - the price more certain
than the records justify.

WHAT WOULD MAKE IT A TELL
If the market prices a mismatch short because it knows something (an injury,
a bullpen state, a spot start), the underdog should beat its price in those
games. If the short price is just noise, both sides land on their price and
the residual predicts nothing.

THE SCENARIO EXACTLY AS ASKED IS ALSO A CELL
Big quality gap, stat model agreeing, hotter bats agreeing, and a price no
shorter than -180 - reported on its own rather than buried in a grid, since
that is the game actually being described.

Corrections as ever: the best of the grid against a max-statistic permutation
with outcomes redrawn from de-vigged prices, then split-half. Nothing this
season has passed both.

Writes output/price_vs_quality.md.
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

log = logging.getLogger("price_vs_quality")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 3000
MIN_CELL = 40
MIN_HALF = 15


def _pct_rank(vals: list[float]) -> list[float]:
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    out = [0.0] * len(vals)
    n = len(vals)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        share = ((i + j) / 2) / max(n - 1, 1)
        for k in range(i, j + 1):
            out[order[k]] = share
        i = j + 1
    return out


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
            sit = g.get("situational") or {}
            sh, sa = sit.get("home") or {}, sit.get("away") or {}
            if (not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int)
                    or not all(isinstance(x.get(k), int) for x in (sh, sa)
                               for k in ("wins", "losses"))):
                continue
            away, home = m.split(" @ ")
            if adv not in (away, home):
                continue
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            def wpct(s):
                t = s["wins"] + s["losses"]
                return s["wins"] / t if t else 0.5
            rec = {home: wpct(sh), away: wpct(sa)}

            fav = min(price, key=lambda t: price[t])     # lower number = favourite
            dog = home if fav == away else away
            if price[fav] >= 0:                          # pick'em, no clear favourite
                continue
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0:
                continue
            p_fav = _implied(price[fav]) / tot

            form = g.get("form") or {}
            dh = (form.get("home") or {}).get("delta")
            da = (form.get("away") or {}).get("delta")
            hotter = None
            if isinstance(dh, (int, float)) and isinstance(da, (int, float)) and dh != da:
                hotter = home if dh > da else away

            rows.append({
                "date": date, "fav": fav, "dog": dog,
                "fav_odds": price[fav], "dog_odds": price[dog],
                "fav_won": res["winner"] == fav, "p_fav": p_fav,
                "gap": rec[fav] - rec[dog],
                "dog_wpct": rec[dog],
                "stat_agrees": adv == fav,
                "form_agrees": hotter == fav if hotter else None,
            })
    gaps = _pct_rank([r["gap"] for r in rows])
    prices = _pct_rank([r["p_fav"] for r in rows])
    for r, gp, pp in zip(rows, gaps, prices):
        r["residual"] = pp - gp
    return rows


def _bets(rs, side):
    if side == "fav":
        return [(r["fav_odds"], r["fav_won"]) for r in rs]
    return [(r["dog_odds"], not r["fav_won"]) for r in rs]


def _roi(b) -> float:
    if not b:
        return 0.0
    return sum(grade.american_profit(o) if w else -1 for o, w in b) / len(b)


def _fmt(rs, side) -> str:
    b = _bets(rs, side)
    if not b:
        return "—"
    w = sum(1 for _, won in b if won)
    return f"{w}-{len(b)-w} · **{_roi(b):+.1%}** (n={len(b)})"


def build() -> str:
    rows = collect()
    md = ["# Price against quality: when the mismatch is bigger than the line",
          "", "_The residual is how much more (or less) confident the price "
          "is than the two teams' RECORDS alone would suggest. Records are "
          "not our model — they are the plainest fact about who is better, "
          "and they sit on 97% of games unused._", "",
          f"- games with both records and a clear favourite: **{len(rows)}**", ""]
    if len(rows) < 300:
        return "\n".join(md + ["Not enough games.", ""])

    md += [f"- baseline, backing every favourite: {_fmt(rows, 'fav')}",
           f"- baseline, backing every underdog: {_fmt(rows, 'dog')}", ""]

    cells = []
    md += ["## By residual — price against what the records imply", "",
           "_Negative means the records say mismatch and the price says "
           "close: the scenario asked about._", "",
           "| residual | backing the favourite | backing the underdog |",
           "|---|---|---|"]
    bands = [("price much SHORTER than records (< -0.25)", lambda v: v < -0.25),
             ("shorter (-0.25 to -0.10)", lambda v: -0.25 <= v < -0.10),
             ("price matches records (-0.10 to +0.10)", lambda v: -0.10 <= v <= 0.10),
             ("longer (+0.10 to +0.25)", lambda v: 0.10 < v <= 0.25),
             ("price much LONGER than records (> +0.25)", lambda v: v > 0.25)]
    for label, test in bands:
        sub = [r for r in rows if test(r["residual"])]
        cells += [(f"fav · {label}", sub, "fav"), (f"dog · {label}", sub, "dog")]
        md.append(f"| {label} | {_fmt(sub, 'fav')} | {_fmt(sub, 'dog')} |")
    md.append("")

    # --- the scenario exactly as described --------------------------------
    md += ["## The scenario as asked", "",
           "_Better on paper by record, the stat model agrees, the hotter "
           "bats agree — and the price is no shorter than -180._", "",
           "| condition | backing the favourite | backing the underdog |",
           "|---|---|---|"]
    gap_hi = st.median([r["gap"] for r in rows if r["gap"] > 0]) if rows else 0
    scen = [r for r in rows
            if r["gap"] >= gap_hi and r["stat_agrees"]
            and r["form_agrees"] is True and r["fav_odds"] >= -180]
    cells += [("fav · scenario", scen, "fav"), ("dog · scenario", scen, "dog")]
    md += [f"| big gap + stat + form, price ≥ -180 | {_fmt(scen, 'fav')} "
           f"| {_fmt(scen, 'dog')} |", ""]
    md += [f"_`big gap` is a win% gap of at least {gap_hi:.3f}, the median "
           "among favourites._", ""]

    # --- worst-opponent version -------------------------------------------
    md += ["## Against genuinely poor opponents", "",
           "_Underdog win% under .400, which is the 'league's worst' the "
           "question describes._", "",
           "| condition | backing the favourite | backing the underdog |",
           "|---|---|---|"]
    for label, test in (("dog under .400, price ≥ -180",
                         lambda r: r["dog_wpct"] < 0.400 and r["fav_odds"] >= -180),
                        ("dog under .400, price < -180",
                         lambda r: r["dog_wpct"] < 0.400 and r["fav_odds"] < -180)):
        sub = [r for r in rows if test(r)]
        cells += [(f"fav · {label}", sub, "fav"), (f"dog · {label}", sub, "dog")]
        md.append(f"| {label} | {_fmt(sub, 'fav')} | {_fmt(sub, 'dog')} |")
    md.append("")

    # --- pay for the grid --------------------------------------------------
    pool = [(l, s, side) for l, s, side in cells if len(s) >= MIN_CELL]
    if not pool:
        return "\n".join(md + [f"No cell reaches n={MIN_CELL}.", ""])
    bl, bs, bside = max(pool, key=lambda c: _roi(_bets(c[1], c[2])))
    obs = _roi(_bets(bs, bside)) * 100
    plan = [[(grade.american_profit(r["fav_odds"] if side == "fav" else r["dog_odds"]),
              r["p_fav"] if side == "fav" else 1 - r["p_fav"]) for r in s]
            for _, s, side in pool]
    rng = random.Random(31)
    null = [max(sum(w if rng.random() < p else -1 for w, p in pl) / len(pl)
                for pl in plan) * 100 for _ in range(TRIALS)]
    pv = (sum(1 for x in null if x >= obs) + 1) / (len(null) + 1)
    md += ["## Does the best cell beat the grid?", "",
           f"- cells at n≥{MIN_CELL}: **{len(pool)}** (both sides of every "
           "cell, so picking the direction afterwards is paid for)",
           f"- best: **{bl}** at {obs:+.1f}%",
           f"- biggest a price-redraw manufactures: median "
           f"**{st.median(null):+.1f}%**, 95th pct "
           f"**{sorted(null)[int(.95*len(null))]:+.1f}%**",
           f"- **corrected p = {pv:.3f}**", "",
           ("**Clears the grid.**" if pv < 0.05 else "**Does not clear.**"), ""]

    rh = random.Random(7)
    tag = [rh.random() < 0.5 for _ in bs]
    a = [r for r, t in zip(bs, tag) if t]
    b = [r for r, t in zip(bs, tag) if not t]
    if min(len(a), len(b)) >= MIN_HALF:
        md += [f"- split-half of **{bl}**: {_fmt(a, bside)} against "
               f"{_fmt(b, bside)}", ""]

    md += ["## How to read this", "",
           "- a short price on a big mismatch is a TELL only if the underdog "
           "beats its price in those games; if both sides land on their "
           "price, the residual is describing the schedule, not information",
           "- records are a cruder measure of quality than a full model, but "
           "that is the point here: they are not OUR model, so this is not "
           "`divergence` restated",
           "- nothing here changes the board.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "price_vs_quality.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
