"""
Deep dive: is the consensus edge real, and does anything else in the market data
hold up across BOTH windows?

Two jobs.

1) IS IT NOISE? The consensus rule tested at 68% / +12.5% on n=68. That is a small
   sample, so this puts error bars on it:
     * day-block bootstrap - resamples whole SLATES, not individual bets, because
       games on the same day share the same market conditions and are not
       independent. Gives a 95% CI on ROI. If that interval includes 0, the honest
       answer is "not yet proven".
     * a binomial read against the price-implied win rate (what the market says
       those exact bets should hit).
     * a threshold sensitivity sweep - a real effect degrades smoothly; a spike
       with dips either side is a fit.

2) WHAT ELSE IS THERE? An exhaustive scan over line movement x public consensus x
   order-book conditions, keeping only combinations that are positive in BOTH the
   in-sample and holdout windows. Crucially it also runs a PERMUTATION NULL: the
   same scan on shuffled outcomes, repeated, to measure how many "consistent
   winners" pure chance produces. If the real scan finds 6 and the null finds 5,
   the survivors are noise - that comparison is the whole point.

Uses the drift backfill (src/pm_backfill.py) when present to widen the order-book
sample beyond the days the live logger ran. Writes output/deep_dive.md.
"""

from __future__ import annotations

import glob
import itertools
import json
import random
import statistics as st
from pathlib import Path

from . import grade, mlb_api, pm_backfill
from .consensus import book_metrics
from .signal_backtest import signals

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
HOLDOUT_FROM = "2026-07-23"
BOOTSTRAP = 2000
PERMUTATIONS = 200
SEED = 20260728


def _implied(ml: int) -> float:
    return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)


def collect() -> list[dict]:
    """One rec per graded game with every market condition attached."""
    recs = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        day = json.loads(Path(f).read_text())
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        live = book_metrics(date)          # live order-book log (drift + imbalance)
        back = pm_backfill.load(date)      # backfilled drift (wider coverage)
        for g in day.get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            sig = signals(g)
            if not sig or sig.get("_ml") is None or " @ " not in g.get("matchup", ""):
                continue
            pc = g.get("pick_criteria") or {}
            away, home = g["matchup"].split(" @ ")
            adv = sig["_adv"]
            price = {adv: sig["_ml"]}
            opp = home if adv == away else away
            if pc.get("opponent_moneyline") is not None:
                price[opp] = int(pc["opponent_moneyline"])
            chk = g.get("public_check") or {}
            maj = (g.get("public_majority") or {}).get("team")
            pk = g.get("game_pk")

            # order-book drift oriented to the ADVANTAGE side
            drift = imb = None
            m = live.get(pk)
            if m:
                drift, imb = m["drift"], m["imbalance"]
            elif pk in back:
                b = back[pk]
                aab = (g.get("home_abbr") if adv == home else g.get("away_abbr")) or ""
                # backfilled drift is stored for b["abbr"]; flip if that's the other side
                drift = b["drift"] if str(b.get("abbr")) == str(aab) else -b["drift"]

            lc = pc.get("line_check") or {}
            recs.append({
                "date": date, "winner": res["winner"], "price": price,
                "adv": adv, "opp": opp, "maj": maj,
                "money": chk.get("money"),
                "shift": lc.get("implied_shift"), "timing": lc.get("timing"),
                "drift": drift, "imb": imb,
                "holdout": date >= HOLDOUT_FROM,
            })
    return recs


def _rows(recs, team_of):
    out = []
    for r in recs:
        t = team_of(r)
        if not t or t not in r["price"]:
            continue
        out.append({"won": r["winner"] == t, "odds": r["price"][t],
                    "date": r["date"], "holdout": r["holdout"]})
    return out


def _roi(rows):
    if not rows:
        return None
    u = sum(grade.american_profit(r["odds"]) if r["won"] else -1 for r in rows)
    return u / len(rows)


def _fmt(rows):
    if not rows:
        return "—"
    w = sum(1 for r in rows if r["won"])
    return f"{w}-{len(rows)-w} ({w/len(rows):.0%}) · **{_roi(rows):+.1%}** (n={len(rows)})"


def _day_block_bootstrap(rows, n=BOOTSTRAP):
    """95% CI on ROI, resampling whole slates (games in a day aren't independent)."""
    by_day: dict = {}
    for r in rows:
        by_day.setdefault(r["date"], []).append(r)
    days = list(by_day)
    if len(days) < 4:
        return None
    rnd = random.Random(SEED)
    out = []
    for _ in range(n):
        pool = []
        for _ in range(len(days)):
            pool.extend(by_day[rnd.choice(days)])
        if pool:
            out.append(_roi(pool))
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))], st.median(out)


def build() -> str:
    recs = collect()
    if not recs:
        return "# Deep dive\n\n_No graded games._"

    # the live consensus rule, reconstructed
    def consensus_bet(r):
        if r["money"] != "with public" or not r["maj"]:
            return None
        if r["drift"] is None and r["imb"] is None:
            return None
        toward_adv = (r["drift"] or 0) > 0 or (r["imb"] or 0) > 0.2
        confirms = toward_adv if r["maj"] == r["adv"] else (not toward_adv)
        return r["maj"] if confirms else None

    crows = _rows(recs, consensus_bet)
    ins = [r for r in crows if not r["holdout"]]
    hold = [r for r in crows if r["holdout"]]
    n_drift = sum(1 for r in recs if r["drift"] is not None)

    md = [f"# Deep dive — {len(recs)} graded games "
          f"({n_drift} with order-book drift after backfill)", "",
          "## 1. Is the consensus edge real, or noise?", "",
          f"- **All:** {_fmt(crows)}", f"- **In-sample:** {_fmt(ins)}",
          f"- **Holdout:** {_fmt(hold)}", ""]

    ci = _day_block_bootstrap(crows)
    if ci:
        lo, hi, med = ci
        verdict = ("**cannot rule out zero** — not yet proven" if lo <= 0
                   else "**excludes zero** at 95%")
        md += [f"**Day-block bootstrap 95% CI on ROI: {lo:+.1%} to {hi:+.1%}** "
               f"(median {med:+.1%}) — {verdict}.", "",
               "_Resamples whole slates, since games on the same day share market "
               "conditions and are not independent bets._", ""]
    if crows:
        exp = st.mean(_implied(r["odds"]) for r in crows)
        act = sum(1 for r in crows if r["won"]) / len(crows)
        md += [f"Market-implied win rate for these exact bets: **{exp:.1%}**; "
               f"actual **{act:.1%}** (**{(act-exp)*100:+.1f} pts**). The bar to "
               "beat is the price, not 50%.", ""]

    # threshold sensitivity - plateau or spike?
    md += ["### Sensitivity — does the edge survive moving the threshold?", "",
           "| drift/imbalance bar | ALL | in-sample | HOLDOUT |", "|---|---|---|---|"]
    for dmin, imin, lab in ((-0.01, 0.10, "loose"), (0.0, 0.20, "live setting"),
                            (0.01, 0.30, "tighter"), (0.02, 0.40, "tightest")):
        def bet(r, d=dmin, i=imin):
            if r["money"] != "with public" or not r["maj"]:
                return None
            if r["drift"] is None and r["imb"] is None:
                return None
            toward = (r["drift"] or -9) > d or (r["imb"] or -9) > i
            ok = toward if r["maj"] == r["adv"] else (not toward)
            return r["maj"] if ok else None
        rr = _rows(recs, bet)
        md.append(f"| {lab} | {_fmt(rr)} | {_fmt([x for x in rr if not x['holdout']])} "
                  f"| {_fmt([x for x in rr if x['holdout']])} |")
    md.append("")

    # ---- 2. exhaustive scan, both-windows-positive, vs a permutation null ----
    CONDS = {
        "consensus (money with public)": lambda r: r["money"] == "with public",
        "money against public": lambda r: r["money"] == "against public",
        "line toward adv ≥2%": lambda r: (r["shift"] or -9) >= 0.02,
        "line away from adv ≥2%": lambda r: (r["shift"] or 9) <= -0.02,
        "line flat": lambda r: r["shift"] is not None and abs(r["shift"]) < 0.005,
        "sharp-window move": lambda r: r["timing"] in ("early", "both"),
        "public-window move": lambda r: r["timing"] == "late",
        "PM drift up": lambda r: (r["drift"] or 0) > 0,
        "PM drift down": lambda r: (r["drift"] or 0) < 0,
        "PM size toward adv": lambda r: (r["imb"] or 0) > 0.2,
        "PM size against adv": lambda r: (r["imb"] or 0) < -0.2,
    }
    SIDES = {"adv": lambda r: r["adv"], "opp": lambda r: r["opp"],
             "consensus": lambda r: r["maj"],
             "anti-consensus": lambda r: (r["opp"] if r["maj"] == r["adv"] else r["adv"])
             if r["maj"] else None}
    MINN, MINH = 25, 8

    def scan(outcome_map=None):
        """Combos positive in BOTH windows. outcome_map swaps winners (null test)."""
        hits = []
        pool = recs if outcome_map is None else [
            {**r, "winner": outcome_map[i]} for i, r in enumerate(recs)]
        for k in (1, 2):
            for names in itertools.combinations(CONDS, k):
                sub = [r for r in pool
                       if all(CONDS[nm](r) for nm in names)]
                if len(sub) < MINN:
                    continue
                for sname, sfn in SIDES.items():
                    rr = _rows(sub, sfn)
                    i_r = [x for x in rr if not x["holdout"]]
                    h_r = [x for x in rr if x["holdout"]]
                    if len(rr) < MINN or len(h_r) < MINH:
                        continue
                    ri, rh = _roi(i_r), _roi(h_r)
                    if ri is not None and rh is not None and ri > 0 and rh > 0:
                        hits.append((min(ri, rh), " + ".join(names), sname, rr, i_r, h_r))
        return sorted(hits, reverse=True)

    real = scan()
    rnd = random.Random(SEED)
    winners = [r["winner"] for r in recs]
    null_counts = []
    for _ in range(PERMUTATIONS):
        shuffled = winners[:]
        rnd.shuffle(shuffled)
        null_counts.append(len(scan(shuffled)))
    null_mean = st.mean(null_counts) if null_counts else 0
    null_p95 = sorted(null_counts)[int(0.95 * len(null_counts))] if null_counts else 0

    md += ["## 2. Everything that is positive in BOTH windows", "",
           f"_Scanned every 1- and 2-condition combination x 4 bet sides "
           f"(n≥{MINN}, holdout n≥{MINH}), keeping only those profitable in-sample "
           "AND in holdout._", "",
           f"**Real scan found {len(real)}. On randomly shuffled outcomes the same "
           f"scan finds {null_mean:.1f} on average (95th pct {null_p95}).** "
           + ("Chance alone explains this many survivors — treat them as noise."
              if len(real) <= null_p95 else
              "The real scan beats what chance produces, so the survivors are "
              "worth a look."), "",
           "| conditions | bet side | ALL | in-sample | HOLDOUT |",
           "|---|---|---|---|---|"]
    for _, names, sname, rr, i_r, h_r in real[:15]:
        md.append(f"| {names} | {sname} | {_fmt(rr)} | {_fmt(i_r)} | {_fmt(h_r)} |")
    if not real:
        md.append("| _nothing survived both windows_ | — | — | — | — |")
    md.append("")

    md.append("_The permutation null is the honest yardstick: any large scan finds "
              "'consistent winners' in pure noise, so a survivor only means "
              "something if the real count clearly exceeds the null count._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "deep_dive.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
