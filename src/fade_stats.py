"""
Do the STAT signals separate winning fades from losing ones?

WHY ASK AGAIN WHEN ev_model SAID NO
`ev_model` showed margin, BvP, bullpen BvP, form and public lean add nothing on
top of the price - across ALL games. The fade is a different population: games
where the rule itself changed its mind mid-afternoon. It is at least arguable
that fundamentals break the tie there when they do not in general, and
`near_miss` already proved a prior of mine wrong this week, so it is worth the
test rather than the assumption.

HOW IT IS TESTED
Two ways, deliberately.

  1. PER FEATURE, the table you would expect: split each stat at its median and
     compare fade ROI either side. Corrected with a max-statistic over every
     split examined, because this repo has produced a great-looking cell from
     seventeen consecutive scans.

  2. LOG-LOSS, the powered version: a logistic fit of fade outcome on the
     market's own de-vigged price plus the stat features, trained before the
     holdout and scored after. ROI on a subset is dominated by which coin flips
     landed - which is why every power calculation here came back at 600+ games
     per test. Log-loss scores the probability assigned to what actually
     happened on EVERY fade, so it is informative at the sample we have.

Every feature is signed TOWARD the side the fade backs, so a positive weight
means "this raises the fade's chance" and the sign is readable.

Writes output/fade_stats.md.
"""

from __future__ import annotations

import glob
import json
import logging
import math
import random
import statistics as st
import subprocess
from collections import defaultdict
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import HOLDOUT_FROM, _implied

log = logging.getLogger("fade_stats")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPO = Path(__file__).resolve().parent.parent
MIN_CELL = 25
EPS = 1e-6

FEATURES = ["bvp", "pen", "margin", "form", "consistency", "park", "record"]


def _shas(rel):
    try:
        o = subprocess.run(["git", "log", "--format=%H", "--all", "--reverse",
                            "--", rel], cwd=REPO, capture_output=True,
                           text=True, timeout=120)
        return [x for x in o.stdout.split() if x]
    except Exception:
        return []


def _at(sha, rel):
    try:
        o = subprocess.run(["git", "show", f"{sha}:{rel}"], cwd=REPO,
                           capture_output=True, text=True, timeout=60)
        return json.loads(o.stdout) if o.returncode == 0 else None
    except Exception:
        return None


def collect() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        rel = f"output/picks_{date}.json"
        shas = _shas(rel)
        if len(shas) < 2:
            continue
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        seq: dict = defaultdict(list)
        snap: dict = {}
        for sha in shas:
            day = _at(sha, rel)
            if not day:
                continue
            for g in day.get("games", []):
                pk = g.get("game_pk")
                pc = g.get("pick_criteria") or {}
                seq[pk].append((pc.get("play") == "pick", pc.get("bet_team")))
                snap[pk] = g              # last version wins: the settled board
        for pk, hist in seq.items():
            picked = [i for i, x in enumerate(hist) if x[0]]
            if not picked or picked[-1] == len(hist) - 1:
                continue                  # never picked, or survived
            g = snap.get(pk)
            res = results.get(pk)
            if not g or not res or not res.get("final") or not res.get("winner"):
                continue
            m = g.get("matchup") or ""
            bet = hist[picked[-1]][1]
            if " @ " not in m or not bet:
                continue
            away, home = m.split(" @ ")
            fade = home if bet == away else away
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not isinstance(a_ml, int) or not isinstance(o_ml, int) or not adv:
                continue
            odds = a_ml if fade == adv else o_ml

            def toward(val, team):
                """A signal naming a team, signed toward the FADE side."""
                if not isinstance(val, (int, float)) or not team:
                    return 0.0
                return float(val) if team == fade else -float(val)

            b, bp = g.get("bvp") or {}, g.get("bvp_pen") or {}
            form = g.get("form") or {}
            fh = (form.get("home") or {}).get("delta")
            fa = (form.get("away") or {}).get("delta")
            cons = g.get("consistency") or {}
            sit = g.get("situational") or {}

            def wpct(side):
                s = sit.get(side) or {}
                w, l = s.get("wins"), s.get("losses")
                return (w / (w + l)) if isinstance(w, int) and isinstance(l, int) and (w + l) else 0.5

            margin = ((pc.get("components") or {}).get("stat_edge") or {}).get("margin")
            ch = (cons.get("home") or {}).get("back_test", {}).get("complete_win_condition")
            ca = (cons.get("away") or {}).get("back_test", {}).get("complete_win_condition")
            tot = _implied(a_ml) + _implied(o_ml)
            rows.append({
                "date": date, "pk": pk, "matchup": m, "fade": fade, "odds": odds,
                "won": res["winner"] == fade,
                "p": (_implied(odds) / tot) if tot > 0 else 0.5,
                "x": {
                    "bvp": toward(b.get("gap"), b.get("edge_team")),
                    "pen": toward(bp.get("gap"), bp.get("edge_team")),
                    "margin": toward(margin, adv),
                    "form": ((fh - fa) if fade == home else (fa - fh))
                    if isinstance(fh, (int, float)) and isinstance(fa, (int, float)) else 0.0,
                    "consistency": float((ch - ca) if fade == home else (ca - ch))
                    if isinstance(ch, int) and isinstance(ca, int) else 0.0,
                    "park": float(g.get("park_factor") or 1.0) - 1.0,
                    "record": (wpct("home") - wpct("away")) if fade == home
                    else (wpct("away") - wpct("home")),
                },
            })
    return rows


def _roi(rs) -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r["odds"]) if r["won"] else -1
               for r in rs) / len(rs)


def _fmt(rs) -> str:
    if not rs:
        return "—"
    w = sum(1 for r in rs if r["won"])
    tag = "" if len(rs) >= MIN_CELL else "_"
    return f"{tag}{w}-{len(rs)-w} · {_roi(rs):+.1%} (n={len(rs)}){tag}"


def _sig(z):
    if z >= 0:
        return 1 / (1 + math.exp(-z))
    e = math.exp(z)
    return e / (1 + e)


def _fit(train, feats, iters=4000, lr=0.15, l2=1.0):
    w = {k: 0.0 for k in feats}
    b = 0.0
    n = len(train)
    for _ in range(iters):
        gw = {k: 0.0 for k in feats}
        gb = 0.0
        for r in train:
            z = b + sum(w[k] * r["z"][k] for k in feats)
            e = _sig(z) - (1.0 if r["won"] else 0.0)
            gb += e
            for k in feats:
                gw[k] += e * r["z"][k]
        b -= lr * gb / n
        for k in feats:
            w[k] -= lr * (gw[k] / n + l2 * w[k] / n)
    return {"w": w, "b": b, "feats": feats}


def _pred(mdl, r):
    z = mdl["b"] + sum(mdl["w"][k] * r["z"][k] for k in mdl["feats"])
    return min(max(_sig(z), EPS), 1 - EPS)


def _ll(rs, ps):
    return -sum(math.log(p if r["won"] else 1 - p) for r, p in zip(rs, ps)) / len(rs)


def build() -> str:
    rows = collect()
    md = ["# Do the stat signals separate winning fades from losing ones?", "",
          "_ev_model showed these add nothing on top of the price across all "
          "games. The fade is a different population - games where the rule "
          "changed its mind - so it is worth testing rather than assuming._", "",
          f"- fades reconstructed with an outcome: **{len(rows)}**",
          f"- pooled: **{_fmt(rows)}**", ""]
    if len(rows) < 80:
        return "\n".join(md + ["Too few fades to test.", ""])

    cells: dict = {}
    md += ["## Each stat, split at its median", "",
           "_Every feature is signed TOWARD the side the fade backs, so "
           "\"favours the fade\" means the stat likes the team we are buying._",
           "", "| stat | favours the fade | favours the other side |",
           "|---|---|---|"]
    for k in FEATURES:
        vals = sorted(r["x"][k] for r in rows)
        med = vals[len(vals) // 2]
        hi = [r for r in rows if r["x"][k] > med]
        lo = [r for r in rows if r["x"][k] <= med]
        for lbl, sub in ((f"{k} high", hi), (f"{k} low", lo)):
            if len(sub) >= MIN_CELL:
                cells[lbl] = sub
        md.append(f"| `{k}` | {_fmt(hi)} | {_fmt(lo)} |")
    md.append("")

    best = max(cells, key=lambda k: _roi(cells[k]))
    bv = _roi(cells[best])
    rng = random.Random(1361)
    null = []
    for _ in range(3000):
        wins = {r["pk"]: rng.random() < r["p"] for r in rows}
        sc = []
        for v in cells.values():
            u = sum(grade.american_profit(r["odds"]) if wins[r["pk"]] else -1 for r in v)
            sc.append(u / len(v))
        null.append(max(sc))
    pv = sum(1 for x in null if x >= bv) / len(null)
    null.sort()
    md += ["## Does the best split beat the search?", "",
           f"- splits at n≥{MIN_CELL}: **{len(cells)}**",
           f"- best: `{best}` at **{bv:+.1%}** (n={len(cells[best])})",
           f"- median best-in-noise: **{st.median(null):+.1%}**",
           f"- **corrected p = {pv:.3f}**", ""]
    md += (["**Clears.**", ""] if pv <= 0.05 else ["**Does not clear.**", ""])

    # ---- the powered version ----
    # HOLDOUT_FROM is 2026-07-23 but the consensus rule only went live on 07-28,
    # so every fade postdates it and that split leaves an empty training set -
    # the fit silently did not run the first time. The fade population is
    # out-of-sample by construction, so it is split on its own median date.
    dates = sorted({r["date"] for r in rows})
    mid = dates[len(dates) // 2]
    train = [r for r in rows if r["date"] < mid]
    hold = [r for r in rows if r["date"] >= mid]
    md += ["## The powered version — log-loss on every fade", "",
           "_ROI on a subset is dominated by which coin flips landed. Log-loss "
           "scores the probability assigned to what actually happened on every "
           "fade, so it is informative at this sample._", "",
           f"- trained on fades before **{mid}** (**{len(train)}**), scored on "
           f"**{len(hold)}** after", "",
           "_Every fade postdates the MLB holdout date, since the consensus rule "
           "went live after it. So this splits the fade population on its own "
           "median date instead._", ""]
    if len(train) < 30 or len(hold) < 30:
        md += ["Split too small to fit.", ""]
        return "\n".join(md)
    stats = {}
    for k in FEATURES:
        v = [r["x"][k] for r in train]
        m0 = sum(v) / len(v)
        sd = (sum((x - m0) ** 2 for x in v) / len(v)) ** 0.5 or 1.0
        stats[k] = (m0, sd)
    for r in rows:
        r["z"] = {k: (r["x"][k] - stats[k][0]) / stats[k][1] for k in FEATURES}
        r["z"]["mkt"] = math.log(min(max(r["p"], EPS), 1 - EPS)
                                 / (1 - min(max(r["p"], EPS), 1 - EPS)))
    v = [r["z"]["mkt"] for r in train]
    m0 = sum(v) / len(v)
    sd = (sum((x - m0) ** 2 for x in v) / len(v)) ** 0.5 or 1.0
    for r in rows:
        r["z"]["mkt"] = (r["z"]["mkt"] - m0) / sd

    mkt = _fit(train, ["mkt"])
    full = _fit(train, ["mkt"] + FEATURES)
    p_m = [_pred(mkt, r) for r in hold]
    p_f = [_pred(full, r) for r in hold]
    gain = _ll(hold, p_m) - _ll(hold, p_f)
    d = [(-math.log(a if r["won"] else 1 - a)) - (-math.log(b if r["won"] else 1 - b))
         for r, a, b in zip(hold, p_m, p_f)]
    rg = random.Random(1409)
    bs = sorted(sum(x) / len(x) for x in
                ([d[rg.randrange(len(d))] for _ in d] for _ in range(4000)))
    md += ["| model | holdout log-loss |", "|---|---|",
           f"| price only | {_ll(hold, p_m):.4f} |",
           f"| price + all stats | **{_ll(hold, p_f):.4f}** |", "",
           f"- stats change holdout log-loss by **{gain:+.4f}**",
           f"- 95% CI: **{bs[100]:+.4f} to {bs[3899]:+.4f}**",
           "- weights: " + ", ".join(f"`{k}` {full['w'][k]:+.3f}" for k in FEATURES),
           ""]
    md += (["**The stats carry information about fade outcomes.**", ""]
           if bs[100] > 0 else
           ["**No information beyond the price.** On the fade population too, "
            "everything we track is already in the number.", ""])
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "fade_stats.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
