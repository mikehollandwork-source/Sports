"""
Book-fade test: before first pitch, back the side the Polymarket order book has
LESS money resting on - restricted to reasonable prices (no worse than -150).

THE IDEA (user's)
The order book shows where money is queued. If the crowd's money piles onto one
side, the other side is the one nobody wants - and in a market where the favourite
is usually over-backed, the unloved side may be the value. This is the contrarian
read of the same depth data the consensus rule uses in the confirming direction,
so testing it is a genuine fork, not a re-run.

HOW "LESS MONEY" IS MEASURED
The log stores top-of-book for the ADVANTAGE side's token: `bid_sz` is money
queued to BUY that side, `ask_sz` is money queued to sell it (which is money
backing the OTHER team). So at the last clean pre-game reading:
    money on advantage side = bid_sz
    money on opponent side  = ask_sz
and the less-money side is whichever is smaller. We bet it only if its own price
is no worse than MAX_LAY (default -150).

RIGOUR
Every number is reported in-sample vs holdout, plus:
  * a day-block bootstrap 95% CI on ROI (slates resampled whole - same-day games
    are not independent)
  * a MARKET-CALIBRATED null: outcomes redrawn from each game's own price-implied
    probability, giving an empirical p-value for "could this ROI happen with no
    edge at all?"
  * the exact mirror strategy (back the MORE-money side) - if the effect is real,
    the mirror should be symmetrically bad, not also positive
  * sweeps over the imbalance threshold and the price cap, to see a plateau
    rather than a lucky point

Writes output/book_fade.md.
"""

from __future__ import annotations

import glob
import json
import random
import statistics as st
from pathlib import Path

from . import grade, mlb_api

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
HOLDOUT_FROM = "2026-07-23"
MAX_SPREAD = 0.15      # ignore readings with no real two-sided market
MAX_LAY = -150         # never lay worse than this on the side we back
BOOTSTRAP = 2000
NULL_SIMS = 2000
SEED = 20260729


def _implied(ml: int) -> float:
    return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)


def collect() -> list[dict]:
    """One rec per game that has a clean pre-game book reading and both prices."""
    recs = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "pm_books_*.json"))):
        date = Path(f).stem.split("pm_books_")[1]
        picks_path = OUTPUT_DIR / f"picks_{date}.json"
        if not picks_path.exists():
            continue
        book = json.loads(Path(f).read_text())
        snap = {g.get("game_pk"): g for g in
                json.loads(picks_path.read_text()).get("games", [])}
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        for pk_s, g in (book.get("games") or {}).items():
            try:
                pk = int(pk_s)
            except (TypeError, ValueError):
                continue
            sg, res = snap.get(pk), results.get(pk)
            if not sg or not res or not res.get("final") or not res.get("winner"):
                continue
            if " @ " not in sg.get("matchup", ""):
                continue
            pc = sg.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            away, home = sg["matchup"].split(" @ ")
            opp = home if adv == away else away

            reads = [r for r in (g.get("readings") or [])
                     if not r.get("empty")
                     and isinstance(r.get("bid"), (int, float))
                     and isinstance(r.get("ask"), (int, float))
                     and r["ask"] > r["bid"] and (r["ask"] - r["bid"]) <= MAX_SPREAD]
            if not reads:
                continue
            reads.sort(key=lambda r: r.get("t", 0))
            last = reads[-1]
            m_adv = float(last.get("bid_sz") or 0)    # money queued to back adv
            m_opp = float(last.get("ask_sz") or 0)    # money queued to back opp
            if m_adv + m_opp <= 0:
                continue
            recs.append({
                "date": date, "winner": res["winner"],
                "adv": adv, "opp": opp,
                "price": {adv: a_ml, opp: o_ml},
                "m_adv": m_adv, "m_opp": m_opp,
                "imb": (m_adv - m_opp) / (m_adv + m_opp),
                "holdout": date >= HOLDOUT_FROM,
            })
    return recs


def _pick_less(r, min_gap=0.0):
    """The side with LESS resting money, if the lean is at least min_gap."""
    if abs(r["imb"]) < min_gap:
        return None
    return r["opp"] if r["imb"] > 0 else r["adv"]


def _pick_more(r, min_gap=0.0):
    if abs(r["imb"]) < min_gap:
        return None
    return r["adv"] if r["imb"] > 0 else r["opp"]


def _rows(recs, chooser, max_lay=MAX_LAY, min_gap=0.0):
    out = []
    for r in recs:
        t = chooser(r, min_gap)
        if not t:
            continue
        ml = r["price"].get(t)
        if ml is None or ml < max_lay:      # never lay worse than the cap
            continue
        out.append({"won": r["winner"] == t, "odds": ml,
                    "date": r["date"], "holdout": r["holdout"], "team": t})
    return out


def _roi(rows):
    if not rows:
        return None
    return sum(grade.american_profit(x["odds"]) if x["won"] else -1
               for x in rows) / len(rows)


def _fmt(rows):
    if not rows:
        return "—"
    w = sum(1 for x in rows if x["won"])
    u = sum(grade.american_profit(x["odds"]) if x["won"] else -1 for x in rows)
    return f"{w}-{len(rows)-w} ({w/len(rows):.0%}) · {u:+.1f}u · **{_roi(rows):+.1%}** (n={len(rows)})"


def _bootstrap(rows):
    by_day: dict = {}
    for x in rows:
        by_day.setdefault(x["date"], []).append(x)
    days = list(by_day)
    if len(days) < 4:
        return None
    rnd = random.Random(SEED)
    out = []
    for _ in range(BOOTSTRAP):
        pool = []
        for _ in range(len(days)):
            pool.extend(by_day[rnd.choice(days)])
        if pool:
            out.append(_roi(pool))
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))], st.median(out)


def _null_p(recs, rows_roi, chooser, max_lay=MAX_LAY, min_gap=0.0):
    """Empirical p-value: redraw winners from each game's price-implied odds
    (realistic prices, zero edge) and see how often the strategy does this well."""
    rnd = random.Random(SEED)
    sides = []
    for r in recs:
        a, o = r["adv"], r["opp"]
        pa, po = _implied(r["price"][a]), _implied(r["price"][o])
        tot = pa + po or 1.0
        sides.append((a, o, pa / tot))
    beat = 0
    for _ in range(NULL_SIMS):
        sim = []
        for i, r in enumerate(recs):
            a, o, pa = sides[i]
            sim.append({**r, "winner": a if rnd.random() < pa else o})
        rr = _rows(sim, chooser, max_lay, min_gap)
        v = _roi(rr)
        if v is not None and v >= rows_roi:
            beat += 1
    return beat / NULL_SIMS


def build() -> str:
    recs = collect()
    if not recs:
        return "# Book fade\n\n_No order-book games available._"

    main_rows = _rows(recs, _pick_less)
    md = [f"# Book fade — back the side with LESS money in the Polymarket book", "",
          f"_{len(recs)} games with a clean pre-game order-book reading. We back "
          f"whichever side has less resting money, and only if that side's own "
          f"price is no worse than {MAX_LAY}. $1/bet at the real moneyline._", "",
          "## Headline", "",
          f"- **All:** {_fmt(main_rows)}",
          f"- **In-sample:** {_fmt([x for x in main_rows if not x['holdout']])}",
          f"- **Holdout:** {_fmt([x for x in main_rows if x['holdout']])}", ""]

    roi = _roi(main_rows)
    if roi is not None:
        ci = _bootstrap(main_rows)
        if ci:
            lo, hi, med = ci
            md += [f"**Day-block bootstrap 95% CI on ROI: {lo:+.1%} to {hi:+.1%}** "
                   f"(median {med:+.1%}) — "
                   + ("**cannot rule out zero**." if lo <= 0 else
                      "**excludes zero** at 95%."), ""]
        p = _null_p(recs, roi, _pick_less)
        md += [f"**Market-calibrated null p-value: {p:.3f}** — with realistic prices "
               f"and no edge at all, a result this good happens {p:.1%} of the time."
               + ("  That is not significant." if p > 0.05 else
                  "  That is significant at the usual 5% bar."), ""]
        exp = st.mean(_implied(x["odds"]) for x in main_rows)
        act = sum(1 for x in main_rows if x["won"]) / len(main_rows)
        md += [f"Market-implied win rate for these exact bets: **{exp:.1%}**; "
               f"actual **{act:.1%}** (**{(act-exp)*100:+.1f} pts**).", ""]

    # the mirror - if the effect is real this should be symmetrically bad
    mirror = _rows(recs, _pick_more)
    md += ["## Mirror check — back the side with MORE money", "",
           "_If backing the unloved side is a real edge, its exact opposite should "
           "lose. If BOTH look positive, the split is noise._", "",
           f"- **All:** {_fmt(mirror)}",
           f"- **Holdout:** {_fmt([x for x in mirror if x['holdout']])}", ""]

    # how clear does the money lean have to be?
    md += ["## Sweep — minimum money lean required", "",
           "| min imbalance | ALL | in-sample | HOLDOUT |", "|---|---|---|---|"]
    for gap in (0.0, 0.1, 0.2, 0.4, 0.6):
        rr = _rows(recs, _pick_less, min_gap=gap)
        md.append(f"| ≥ {gap:.1f} | {_fmt(rr)} | "
                  f"{_fmt([x for x in rr if not x['holdout']])} | "
                  f"{_fmt([x for x in rr if x['holdout']])} |")
    md.append("")

    # price cap sweep
    md += ["## Sweep — how much are we willing to lay?", "",
           "| price cap | ALL | in-sample | HOLDOUT |", "|---|---|---|---|"]
    for cap, lab in ((-100000, "any price"), (-250, "≥ −250"), (-180, "≥ −180"),
                     (-150, "≥ −150 (default)"), (-130, "≥ −130"), (100, "plus money only")):
        rr = _rows(recs, _pick_less, max_lay=cap)
        md.append(f"| {lab} | {_fmt(rr)} | "
                  f"{_fmt([x for x in rr if not x['holdout']])} | "
                  f"{_fmt([x for x in rr if x['holdout']])} |")
    md.append("")

    # is the less-money side simply the underdog? (sanity: what are we really betting)
    dogs = sum(1 for x in main_rows if x["odds"] > 0)
    md += [f"_Composition: {dogs} of {len(main_rows)} bets are plus-money "
           f"({dogs/len(main_rows):.0%}) — if this is ~100%, the strategy is really "
           "just 'bet underdogs' wearing an order-book costume._", ""]

    md.append("_The p-value and the mirror are the honest tests: a real effect is "
              "significant against realistic prices AND has a losing opposite._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "book_fade.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
