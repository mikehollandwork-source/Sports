"""
Every gate, isolated, on the whole pool - pass against fail.

WHY THIS IS NOT gate_audit
`gate_audit` does ablation: for each gate, the games it UNIQUELY rejects, out of
those passing every other gate. That answers "at the margin of the finished
rule, does this gate help?" It cannot answer "does this gate carry any edge at
all?", because it only ever looks at a sliver that has already survived
everything else. When `quality_gate` returned +23.8% on our 104 picks and
+0.1% on all 819 qualifying games, that gap was this mistake.

So: each gate ALONE, on the whole pool, with no other gate applied.

WHAT A GATE IS, AND WHAT THEREFORE GETS MEASURED
A gate does not name a side - the side is already chosen. A gate only decides
bet or don't. So the side is held fixed at the public-majority team for every
row, and each gate splits that same pool in two:

    PASS   bet the majority side on the games the gate lets through
    FAIL   bet the majority side on the games it rejects

The gate is worth PASS minus FAIL. Not PASS on its own - a gate that only
selects short favourites will show a high win rate and no edge, and its FAIL
column is the control that exposes that. The difference is the number, and it
gets a day-block bootstrap interval as a difference rather than an interval
read off PASS alone.

WHAT IS TESTED
The live rule's own gates, decomposed further than the rule states them
(drift and size separately, then their OR and their AND; the line bar at both
1.0% and 0.5%), plus every board flag that has never been a gate at all -
trusted, corroborated, edge_strong, starred, consistency hits, BvP meaningful,
sharp money, pitching dog, book_stance, line-vs-money, PM quote, flagged.

CORRECTION
Roughly twenty gates, so the best difference is selected out of twenty. The
permutation redraws winners ONCE per trial from de-vigged prices and then
recomputes every gate's difference from that same redraw, because the gates
overlap heavily on the same games and independent redraws would understate how
easily the best one drifts up. Max and min statistic, then split-half.

Writes output/gate_sweep.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import consensus as C, grade, mlb_api
from .pregame_money import _implied

log = logging.getLogger("gate_sweep")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 3000
MIN_CELL = 40


def _shift_against(g: dict, side: str) -> float | None:
    """How far the line moved AGAINST `side`, in implied points. Positive means
    the price got better for us, which is what the live gate wants."""
    pc = g.get("pick_criteria") or {}
    shift = (pc.get("line_check") or {}).get("implied_shift")
    adv = pc.get("advantage_team")
    if not isinstance(shift, (int, float)) or not adv:
        return None
    toward = shift if side == adv else -shift
    return -toward


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
            chk = g.get("public_check") or {}
            maj = (g.get("public_majority") or {}).get("team")
            adv = pc.get("advantage_team")
            away, home = m.split(" @ ")
            if maj not in (away, home) or not adv:
                continue
            odds = (pc.get("advantage_moneyline") if maj == adv
                    else pc.get("opponent_moneyline"))
            other = (pc.get("opponent_moneyline") if maj == adv
                     else pc.get("advantage_moneyline"))
            if not isinstance(odds, int) or not isinstance(other, int):
                continue
            tot = _implied(odds) + _implied(other)
            if tot <= 0:
                continue

            mm = metrics.get(g.get("game_pk"))
            # book_metrics is signed to the ADVANTAGE side; flip for the other
            flip = 1 if maj == adv else -1
            drift = (mm["drift"] * flip) if mm else None
            imb = (mm["imbalance"] * flip) if mm else None
            ag = _shift_against(g, maj)
            bs = pc.get("book_stance") or {}
            pmq = pc.get("pm_quote") or {}
            conf, thr = pc.get("confidence"), pc.get("edge_threshold")
            hits = pc.get("consistency_hits")
            starred = pc.get("starred")

            gates = {
                # ---- the live rule, decomposed -------------------------------
                "handle agrees with tickets": chk.get("money") == "with public",
                "an order-book read exists": mm is not None,
                "book DRIFT confirms": (drift > 0) if drift is not None else None,
                "book SIZE confirms": ((imb > C.IMBALANCE_MIN)
                                       if imb is not None else None),
                "book confirms — EITHER (live)": (
                    (drift > 0 or imb > C.IMBALANCE_MIN)
                    if drift is not None and imb is not None else None),
                "book confirms — BOTH (reverted)": (
                    (drift > 0 and imb > C.IMBALANCE_MIN)
                    if drift is not None and imb is not None else None),
                "line moved against ≥1.0% (live)": (
                    (ag >= 0.01) if ag is not None else None),
                "line moved against ≥0.5%": ((ag >= 0.005) if ag is not None else None),
                "line moved against at all": ((ag > 0) if ag is not None else None),

                # ---- board flags that have never been gates ------------------
                "public sources trusted": chk.get("trusted") if isinstance(
                    chk.get("trusted"), bool) else None,
                "public verdict corroborated": (
                    (chk.get("verdict") == "corroborated") if chk.get("verdict") else None),
                "stat edge is strong": pc.get("edge_strong") if isinstance(
                    pc.get("edge_strong"), bool) else None,
                "public edge flag": pc.get("public_edge") if isinstance(
                    pc.get("public_edge"), bool) else None,
                "confidence ≥ threshold": (
                    (conf >= thr) if isinstance(conf, (int, float))
                    and isinstance(thr, (int, float)) else None),
                "starred (any tag)": ((len(starred) > 0)
                                      if isinstance(starred, list) else None),
                "win-condition hits ≥3": ((hits >= 3) if isinstance(hits, int) else None),
                "BvP sample meaningful": (g.get("bvp") or {}).get("meaningful") \
                    if isinstance((g.get("bvp") or {}).get("meaningful"), bool) else None,
                "sharp money flag": pc.get("sharp_money") if isinstance(
                    pc.get("sharp_money"), bool) else None,
                "pitching dog": pc.get("pitching_dog") if isinstance(
                    pc.get("pitching_dog"), bool) else None,
                "book stance against us": bs.get("against_us") if isinstance(
                    bs.get("against_us"), bool) else None,
                "book looks fooled": bs.get("fooled") if isinstance(
                    bs.get("fooled"), bool) else None,
                "line vs money 'against'": (
                    (pc.get("line_vs_money") == "against")
                    if pc.get("line_vs_money") else None),
                "PM quote better than book": (
                    (pmq.get("vs_book") == "better") if pmq.get("vs_book") else None),
                "board flagged it": g.get("flagged") if isinstance(
                    g.get("flagged"), bool) else None,
            }
            rows.append({"date": date, "odds": odds, "won": res["winner"] == maj,
                         "p": _implied(odds) / tot, "gates": gates})
    return rows


GATES = ["handle agrees with tickets", "an order-book read exists",
         "book DRIFT confirms", "book SIZE confirms",
         "book confirms — EITHER (live)", "book confirms — BOTH (reverted)",
         "line moved against ≥1.0% (live)", "line moved against ≥0.5%",
         "line moved against at all",
         "public sources trusted", "public verdict corroborated",
         "stat edge is strong", "public edge flag", "confidence ≥ threshold",
         "starred (any tag)", "win-condition hits ≥3", "BvP sample meaningful",
         "sharp money flag", "pitching dog", "book stance against us",
         "book looks fooled", "line vs money 'against'",
         "PM quote better than book", "board flagged it"]

LIVE = set(GATES[:9])


def _split(rows, gate):
    p = [r for r in rows if r["gates"].get(gate) is True]
    f = [r for r in rows if r["gates"].get(gate) is False]
    return p, f


def _roi(rs) -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r["odds"]) if r["won"] else -1
               for r in rs) / len(rs)


def _fmt(rs) -> str:
    if not rs:
        return "—"
    w = sum(1 for r in rs if r["won"])
    return f"{w}-{len(rs)-w} · **{_roi(rs):+.1%}**"


def _boot_diff(p, f) -> tuple[float, float]:
    """Day-block bootstrap on roi(pass) - roi(fail), days resampled jointly so
    the two populations stay paired within a day."""
    gp, gf = defaultdict(list), defaultdict(list)
    for r in p:
        gp[r["date"]].append(grade.american_profit(r["odds"]) if r["won"] else -1)
    for r in f:
        gf[r["date"]].append(grade.american_profit(r["odds"]) if r["won"] else -1)
    days = sorted(set(gp) | set(gf))
    if len(days) < 5:
        return (float("nan"), float("nan"))
    rng = random.Random(451)
    out = []
    for _ in range(TRIALS):
        va, vb = [], []
        for _ in days:
            d = days[rng.randrange(len(days))]
            va += gp.get(d, [])
            vb += gf.get(d, [])
        if va and vb:
            out.append((st.mean(va) - st.mean(vb)) * 100)
    if not out:
        return (float("nan"), float("nan"))
    out.sort()
    return out[int(.025 * len(out))], out[int(.975 * len(out))]


def build() -> str:
    rows = collect()
    md = ["# Every gate, isolated, on the whole pool", "",
          "_`gate_audit` does ablation — each gate judged on the sliver of games "
          "that already passed every OTHER gate. That answers whether a gate helps "
          "at the margin of the finished rule; it cannot say whether the gate "
          "carries any edge at all. `quality_gate` returning +23.8% on our own 104 "
          "picks and +0.1% on all 819 qualifying games was that mistake._", "",
          "_So each gate stands alone here, on the whole pool, no other gate "
          "applied. A gate does not pick a side — the side is held fixed at the "
          "public-majority team — it only decides bet or don't. So the number that "
          "matters is **PASS minus FAIL**, not PASS on its own: a gate that merely "
          "selects short favourites shows a fat win rate and no edge, and its FAIL "
          "column is the control that catches it._", "",
          f"- graded games with a nameable majority side: **{len(rows)}**", ""]
    if len(rows) < 300:
        return "\n".join(md + ["Not enough graded games.", ""])

    live_rows, other_rows, diffs = [], [], {}
    for gate in GATES:
        p, f = _split(rows, gate)
        if min(len(p), len(f)) < MIN_CELL:
            line = (f"| {gate} | {len(p)} / {len(f)} | _one side too thin_ | | |")
            (live_rows if gate in LIVE else other_rows).append(line)
            continue
        d = (_roi(p) - _roi(f)) * 100
        diffs[gate] = (d, p, f)
        lo, hi = _boot_diff(p, f)
        ci = "—" if lo != lo else f"{lo:+.1f} to {hi:+.1f}"
        line = (f"| {gate} | {len(p)} / {len(f)} | {_fmt(p)} | {_fmt(f)} | "
                f"**{d:+.1f} pts** | {ci} |")
        (live_rows if gate in LIVE else other_rows).append(line)

    hdr = ["| gate | pass / fail | PASS | FAIL | worth | 95% CI on worth |",
           "|---|---|---|---|---|---|"]
    md += ["## The live rule's own gates", ""] + hdr + live_rows + [""]
    md += ["## Board flags that have never been gates", ""] + hdr + other_rows + [""]

    if not diffs:
        return "\n".join(md)

    # one redraw of the whole pool per trial, then every gate's difference from
    # that same redraw - the gates overlap on the same games, so independent
    # redraws would understate how far the best one drifts on noise alone.
    order = list(diffs)
    idx = {g: ([i for i, r in enumerate(rows) if r["gates"].get(g) is True],
               [i for i, r in enumerate(rows) if r["gates"].get(g) is False])
           for g in order}
    prof = [grade.american_profit(r["odds"]) for r in rows]
    prob = [r["p"] for r in rows]
    rng = random.Random(77)
    hi_d, lo_d = [], []
    for _ in range(TRIALS):
        draw = [prof[i] if rng.random() < prob[i] else -1 for i in range(len(rows))]
        vals = []
        for g in order:
            pi, fi = idx[g]
            vals.append((sum(draw[i] for i in pi) / len(pi)
                         - sum(draw[i] for i in fi) / len(fi)) * 100)
        hi_d.append(max(vals))
        lo_d.append(min(vals))

    best = max(diffs, key=lambda g: diffs[g][0])
    worst = min(diffs, key=lambda g: diffs[g][0])
    obs_hi, obs_lo = diffs[best][0], diffs[worst][0]
    p_hi = (sum(1 for x in hi_d if x >= obs_hi) + 1) / (TRIALS + 1)
    p_lo = (sum(1 for x in lo_d if x <= obs_lo) + 1) / (TRIALS + 1)

    md += [f"## Corrected across {len(diffs)} gates, both tails", "",
           f"- best gate: **{best}** worth {obs_hi:+.1f} pts · a redraw's best "
           f"gate reaches {st.median(hi_d):+.1f} median, "
           f"{sorted(hi_d)[int(.95*TRIALS)]:+.1f} at the 95th · "
           f"**corrected p = {p_hi:.3f}**",
           f"- most harmful: **{worst}** worth {obs_lo:+.1f} pts · a redraw's "
           f"worst reaches {st.median(lo_d):+.1f} median, "
           f"{sorted(lo_d)[int(.05*TRIALS)]:+.1f} at the 5th · "
           f"**corrected p = {p_lo:.3f}**", ""]

    rh = random.Random(88)
    for lab in (best, worst):
        _, p, f = diffs[lab]
        tp = [rh.random() < 0.5 for _ in p]
        tf = [rh.random() < 0.5 for _ in f]
        pa = [x for x, t in zip(p, tp) if t]; pb = [x for x, t in zip(p, tp) if not t]
        fa = [x for x, t in zip(f, tf) if t]; fb = [x for x, t in zip(f, tf) if not t]
        if min(len(pa), len(pb), len(fa), len(fb)) >= 20:
            md.append(f"- split-half of **{lab}**: worth "
                      f"{(_roi(pa)-_roi(fa))*100:+.1f} pts on one half, "
                      f"{(_roi(pb)-_roi(fb))*100:+.1f} pts on the other")
    md += ["", "## Reading it", "",
           "- **worth** is the gate's whole case. A gate earns its place only if "
           "its PASS beats its FAIL by more than the correction allows, and by "
           "the same sign in both halves",
           "- a CI on **worth** that straddles zero means the gate is not doing "
           "anything measurable, whatever its PASS column says",
           "- `book confirms — EITHER` and `BOTH` are the live and reverted "
           "settings side by side, on the whole pool rather than on our picks", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "gate_sweep.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
