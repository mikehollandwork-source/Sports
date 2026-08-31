"""
Benter's actual method: estimate p, then bet only when p beats the price.

THE PART OF THE BENTER STORY THAT MATTERS
The popular version is "he built a model of the true win probability and bet
when it beat the odds". That is the second half. The first half, which Benter
wrote about himself, is that his fundamental model ALONE was not profitable. The
breakthrough was feeding the public odds INTO his model as a variable: the
market already contains information no fundamental model has, so the only thing
worth asking is whether your model adds anything ON TOP of the market.

That is exactly our situation, and it is measurable. Backing `advantage_team`
returned -5.9% over 581 games, so our model alone is WORSE than the market. The
question is not "does our model beat the market" - it demonstrably does not - it
is "does our model know one thing the market has not already priced".

WHY THIS TEST IS WORTH MORE THAN THE ELEVEN BEFORE IT
Every previous test measured ROI on a subset. ROI is a terrible measuring
instrument: it is dominated by which coin flips landed, which is why the power
calculations kept coming back at 600-800 games PER TEST and why the max-statistic
nulls kept swallowing every result.

Log-loss does not have that problem. It scores the probability assigned to what
actually happened, on every game, so it uses the whole sample instead of a cell
of it. At n=581 it is already informative TODAY. This is the same reason CLV was
the one useful number in `execution_edge.md` - low-variance beats high-variance
when the effect is small.

WHAT IS FITTED, AND HOW LEAKAGE IS AVOIDED
A logistic regression on the market's own de-vigged logit plus our signals, all
signed toward the home team. Fitted on games before HOLDOUT_FROM, scored on
games after. Feature standardisation uses TRAIN statistics only - computing the
mean over the whole set and then "holding out" leaks the holdout into the fit.

Two baselines, because beating the raw market could just mean the market is
poorly calibrated:
    market raw    the de-vigged price, used as-is
    market only   a logistic refit on the market logit alone, which absorbs any
                  pure recalibration. Our signals have to beat THIS one.

THE BAR, AND WHY LOG-LOSS ALONE IS NOT ENOUGH
Beating the market on log-loss is necessary but not sufficient. A model can be
better calibrated and still not clear the vig. So the report ends with the
actual bet: EV = p*b - (1-p) at the real price, Kelly-staked, on holdout games
only. Both numbers have to work.

Writes output/ev_model.md.
"""

from __future__ import annotations

import glob
import json
import logging
import math
import random
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import HOLDOUT_FROM, _implied

log = logging.getLogger("ev_model")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EPS = 1e-6
L2 = 1.0
ITERS = 4000
LR = 0.15

# every feature is signed toward the HOME team so one coefficient sign is
# readable: positive means "this raises the home team's chance"
FEATURES = ["mkt", "margin", "bvp", "pen", "form", "line", "lean"]

# Schedule/travel, tested SEPARATELY from the signals above. `schedule_spots`
# found a monotone gradient - backing the road team pays more the longer its
# trip - which is the plateau shape every failed signal lacked. But that came
# from a 30-cell scan whose max-statistic test does not credit monotonicity
# (corrected p = 0.160). This is the decisive version: ONE pre-specified test,
# scored by log-loss, asking whether fatigue adds anything the price has not
# already absorbed.
SCHED = ["road_trip", "homestand", "rest_edge"]


def _logit(p: float) -> float:
    p = min(max(p, EPS), 1 - EPS)
    return math.log(p / (1 - p))


def _sig(z: float) -> float:
    if z >= 0:
        return 1 / (1 + math.exp(-z))
    e = math.exp(z)
    return e / (1 + e)


def collect() -> list[dict]:
    from . import schedule_spots
    hist, dates = schedule_spots._history()
    global _sched
    _sched = schedule_spots._team_spots(hist, dates)
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
            matchup = g.get("matchup") or ""
            if " @ " not in matchup:
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            away, home = matchup.split(" @ ")
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            ia, io = _implied(price[home]), _implied(price[away])
            if ia + io <= 0:
                continue
            p_home = ia / (ia + io)            # de-vigged market probability

            def toward_home(val, team):
                """A signal naming a team becomes a number signed toward home."""
                if not isinstance(val, (int, float)) or not team:
                    return 0.0
                return float(val) if team == home else -float(val)

            margin = ((pc.get("components") or {}).get("stat_edge") or {}).get("margin")
            b, bp = g.get("bvp") or {}, g.get("bvp_pen") or {}
            form = g.get("form") or {}
            fh = (form.get("home") or {}).get("delta")
            fa = (form.get("away") or {}).get("delta")
            shift = (pc.get("line_check") or {}).get("implied_shift")
            lean = ((pc.get("components") or {}).get("public_fade") or {}).get("blended_lean")

            sp = _sched.get((date, away)), _sched.get((date, home))
            if not sp[0] or not sp[1] or not sp[0]["seen_home"] or not sp[1]["seen_home"]:
                continue
            sa, sh = sp
            recs.append({
                "date": date, "matchup": matchup, "home": home, "away": away,
                "home_won": res["winner"] == home,
                "p_mkt": p_home,
                "home_ml": price[home], "away_ml": price[away],
                "x": {
                    "mkt": _logit(p_home),
                    "margin": toward_home(margin, adv),
                    "bvp": toward_home(b.get("gap"), b.get("edge_team")),
                    "pen": toward_home(bp.get("gap"), bp.get("edge_team")),
                    "form": ((fh - fa) if isinstance(fh, (int, float))
                             and isinstance(fa, (int, float)) else 0.0),
                    "line": toward_home(shift, adv),
                    "lean": toward_home(lean, adv),
                    # signed toward home: a tired visitor should help the home side
                    "road_trip": float(sa["road_streak"]),
                    "homestand": float(sh["home_streak"]),
                    "rest_edge": float((sh["days_rest"] or 0) - (sa["days_rest"] or 0)),
                },
            })
    return recs


def _standardise(train, allrows, feats):
    """Mean/sd from TRAIN only. Using the full set leaks the holdout into the fit."""
    stats = {}
    for k in feats:
        vals = [r["x"][k] for r in train]
        m = sum(vals) / len(vals)
        sd = (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5 or 1.0
        stats[k] = (m, sd)
    for r in allrows:
        r["z"] = {k: (r["x"][k] - stats[k][0]) / stats[k][1] for k in feats}
    return stats


def fit(train, feats) -> dict:
    """Batch gradient descent with L2. No dependency worth adding for 600x7."""
    w = {k: 0.0 for k in feats}
    b = 0.0
    n = len(train)
    for _ in range(ITERS):
        gw = {k: 0.0 for k in feats}
        gb = 0.0
        for r in train:
            z = b + sum(w[k] * r["z"][k] for k in feats)
            err = _sig(z) - (1.0 if r["home_won"] else 0.0)
            gb += err
            for k in feats:
                gw[k] += err * r["z"][k]
        b -= LR * gb / n
        for k in feats:
            w[k] -= LR * (gw[k] / n + L2 * w[k] / n)
    return {"w": w, "b": b, "feats": feats}


def predict(model, r) -> float:
    z = model["b"] + sum(model["w"][k] * r["z"][k] for k in model["feats"])
    return min(max(_sig(z), EPS), 1 - EPS)


def logloss(rows, ps) -> float:
    return -sum(math.log(p if r["home_won"] else 1 - p)
                for r, p in zip(rows, ps)) / len(rows)


def brier(rows, ps) -> float:
    return sum((p - (1.0 if r["home_won"] else 0.0)) ** 2
               for r, p in zip(rows, ps)) / len(rows)


def _kelly(p: float, ml: int) -> float:
    b = grade.american_profit(ml)          # profit per 1 unit staked
    if b <= 0:
        return 0.0
    f = (p * b - (1 - p)) / b
    return max(0.0, f)


def build() -> str:
    recs = collect()
    md = ["# EV model — does anything we track beat the market's own price?", "",
          "_Benter's fundamental model alone was not profitable; the change that "
          "made it work was feeding the public odds into the model, because the "
          "market already prices what a fundamental model knows. So the question "
          "is not whether our model beats the market - it does not, backing "
          "`advantage_team` returns -5.9% over 581 games - but whether it adds "
          "anything on top of it._", "",
          f"- graded games: **{len(recs)}**", ""]
    if len(recs) < 100:
        return "\n".join(md + ["Too few games to fit.", ""])

    train = [r for r in recs if r["date"] < HOLDOUT_FROM]
    hold = [r for r in recs if r["date"] >= HOLDOUT_FROM]
    md += [f"- train (< {HOLDOUT_FROM}): **{len(train)}** · "
           f"holdout: **{len(hold)}**", ""]
    if len(train) < 80 or len(hold) < 40:
        return "\n".join(md + ["Split too small to be worth fitting.", ""])

    _standardise(train, recs, FEATURES + SCHED)
    full = fit(train, FEATURES)
    mkt_only = fit(train, ["mkt"])
    sched = fit(train, ["mkt"] + SCHED)

    p_raw = [r["p_mkt"] for r in hold]
    p_mkt = [predict(mkt_only, r) for r in hold]
    p_full = [predict(full, r) for r in hold]
    p_sch = [predict(sched, r) for r in hold]

    md += ["## Holdout scoring — lower is better", "",
           "| model | log-loss | Brier |", "|---|---|---|",
           f"| market raw (de-vigged price) | {logloss(hold, p_raw):.4f} | "
           f"{brier(hold, p_raw):.4f} |",
           f"| market only, refit | {logloss(hold, p_mkt):.4f} | "
           f"{brier(hold, p_mkt):.4f} |",
           f"| **market + our signals** | **{logloss(hold, p_full):.4f}** | "
           f"**{brier(hold, p_full):.4f}** |",
           f"| **market + schedule/travel** | **{logloss(hold, p_sch):.4f}** | "
           f"**{brier(hold, p_sch):.4f}** |", ""]
    sg = logloss(hold, p_mkt) - logloss(hold, p_sch)
    sdiffs = [(-math.log(a if r["home_won"] else 1 - a))
              - (-math.log(c if r["home_won"] else 1 - c))
              for r, a, c in zip(hold, p_mkt, p_sch)]
    rs = random.Random(211)
    sb = sorted(sum(x) / len(x) for x in
                ([sdiffs[rs.randrange(len(sdiffs))] for _ in sdiffs]
                 for _ in range(4000)))
    md += ["### Schedule/travel, tested on its own", "",
           f"- schedule features change holdout log-loss by **{sg:+.4f}**",
           f"- 95% CI: **{sb[100]:+.4f} to {sb[3899]:+.4f}**",
           f"- fitted weights: " + ", ".join(f"`{k}` {sched['w'][k]:+.3f}"
                                             for k in SCHED), ""]
    md += (["**Fatigue carries information the price has not absorbed.**", ""]
           if sb[100] > 0 else
           ["**No information beyond the price.** The road-trip gradient in "
            "`schedule_spots` does not survive being asked whether it adds "
            "anything the market has not already priced.", ""])
    gain = logloss(hold, p_mkt) - logloss(hold, p_full)
    md += [f"- our signals change holdout log-loss by **{gain:+.4f}** "
           f"({'better' if gain > 0 else 'worse'} than market alone)", ""]

    # a paired bootstrap on the per-game difference: is the gain real?
    diffs = [(-math.log(a if r["home_won"] else 1 - a))
             - (-math.log(bb if r["home_won"] else 1 - bb))
             for r, a, bb in zip(hold, p_mkt, p_full)]
    rng = random.Random(131)
    boots = []
    for _ in range(4000):
        s = [diffs[rng.randrange(len(diffs))] for _ in diffs]
        boots.append(sum(s) / len(s))
    boots.sort()
    lo, hi = boots[100], boots[3899]
    md += [f"- 95% CI on that gain: **{lo:+.4f} to {hi:+.4f}**", ""]
    md += (["**Our signals add real information.** The interval excludes zero, "
            "so the market has not already priced everything we track.", ""]
           if lo > 0 else
           ["**No information beyond the price.** The interval includes zero: "
            "on this evidence everything we track is already in the market's "
            "number, which is exactly what eleven failed selection tests and a "
            "-5.9% model baseline have been saying.", ""])

    md += ["## What the fit learned", "",
           "| feature | weight | reading |", "|---|---|---|"]
    for k in FEATURES:
        w = full["w"][k]
        note = ("the market's own price" if k == "mkt" else
                "adds nothing" if abs(w) < 0.02 else
                "pushes toward the side it names" if w > 0 else
                "pushes AGAINST the side it names")
        md.append(f"| `{k}` | {w:+.3f} | {note} |")
    md.append("")

    # the actual bet, on holdout only
    md += ["## The Benter filter, applied for real", "",
           "_EV = p·b − (1−p) at the real price, quarter-Kelly staked, holdout "
           "games only. Beating log-loss is necessary but not sufficient - a "
           "better-calibrated model still has to clear the vig._", ""]
    rows = []
    for r, p in zip(hold, p_full):
        for side, ml, pw in ((r["home"], r["home_ml"], p),
                             (r["away"], r["away_ml"], 1 - p)):
            b = grade.american_profit(ml)
            ev = pw * b - (1 - pw)
            if ev > 0:
                f = 0.25 * _kelly(pw, ml)
                won = (r["home_won"] if side == r["home"] else not r["home_won"])
                rows.append({"stake": f, "pnl": f * b if won else -f, "won": won,
                             "ev": ev})
    if not rows:
        md += ["No EV-positive bets found on the holdout. The model never "
               "disagrees with the price by enough to clear the vig.", ""]
    else:
        staked = sum(x["stake"] for x in rows)
        pnl = sum(x["pnl"] for x in rows)
        w = sum(1 for x in rows if x["won"])
        md += [f"- EV-positive bets: **{len(rows)}** of {len(hold)*2} sides "
               f"({len(rows)/(len(hold)*2):.0%})",
               f"- record: **{w}-{len(rows)-w}**",
               f"- staked {staked:.2f}u, P&L **{pnl:+.2f}u**, "
               f"return on stake **{(pnl/staked if staked else 0):+.1%}**",
               f"- mean EV claimed per bet: {sum(x['ev'] for x in rows)/len(rows):+.3f}",
               ""]
        md += ["_If the model had no edge, the EV it claims is fictional and "
               "this return is the vig showing up as a loss._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "ev_model.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
