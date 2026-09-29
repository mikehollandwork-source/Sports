"""
Is the book-confirm gate worthless, or are we just reading the wrong venue?

WHAT PROMPTED THIS
`gate_sweep` put the book-confirm gate at +1.3 points standing alone on 958
games - nothing. The natural conclusion is that order-book confirmation carries
no information. But the gate reads Polymarket, and Polymarket turns out to be
the worse of the two venues we log, measured against the sportsbook's own
de-vigged price:

    venues agree (607 games)      Polymarket off by 0.038   Kalshi off by 0.007
    venues diverge (163 games)    Polymarket off by 0.206   Kalshi off by 0.018

Kalshi tracks the book to under two cents. Polymarket misses by twenty in a
fifth of games. A gate fed by a price that noisy would measure nothing even if
order-book confirmation were real - so "the gate is worthless" and "the gate is
fed garbage" predict the same +1.3 points, and only swapping the venue
separates them.

THE TEST
The same gate, three ways, on the same pool, with the side held fixed at the
public-majority team so the gates only decide bet-or-don't:

    Polymarket   what the rule does now
    Kalshi       same arithmetic, better prices
    both agree   the subset where the two venues point the same way

PASS minus FAIL is the statistic, as in gate_sweep - a gate that merely selects
short favourites shows a fat win rate and no edge, and the FAIL column is what
catches that. Day-block bootstrap on the difference, and a shared-redraw
permutation across the variants, since picking the best of several venues is
itself a scan.

Everything is cut at first pitch minus LOCK_LEAD. Kalshi's log runs through
settlement exactly like Polymarket's, and that is what made the drift signal
look like +10.5% this morning.

Writes output/venue_swap.md.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import consensus as C, grade, mlb_api, pm_books
from .pregame_money import _implied

log = logging.getLogger("venue_swap")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 10000
MIN_CELL = 40


def _metrics(readings: list, cutoff: float) -> dict | None:
    """book_metrics' arithmetic on any venue's log, cut at the freeze."""
    ok = []
    for r in readings or []:
        if r.get("empty"):
            continue
        b, a, t = r.get("bid"), r.get("ask"), r.get("t")
        if not (isinstance(b, (int, float)) and isinstance(a, (int, float))
                and isinstance(t, (int, float))):
            continue
        if t > cutoff or a <= b or (a - b) > C.MAX_SPREAD:
            continue
        ok.append(r)
    if len(ok) < C.MIN_READINGS:
        return None
    ok.sort(key=lambda r: r["t"])
    f, l = ok[0], ok[-1]
    bs, as_ = l.get("bid_sz") or 0, l.get("ask_sz") or 0
    return {"drift": (l["bid"] + l["ask"]) / 2 - (f["bid"] + f["ask"]) / 2,
            "imbalance": (bs - as_) / (bs + as_) if (bs + as_) else 0.0}


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
            # both logs are written from `side`; orient them to the bet side
            flip = 1 if side == maj else -1
            pm = _metrics(gb.get("readings"), cut)
            ka = _metrics(gb.get("k_readings"), cut)
            rows.append({
                "date": date, "odds": odds, "won": res["winner"] == maj,
                "p": _implied(odds) / tot,
                "money_ok": chk.get("money") == "with public",
                "pm": ({"drift": pm["drift"] * flip,
                        "imbalance": pm["imbalance"] * flip} if pm else None),
                "ka": ({"drift": ka["drift"] * flip,
                        "imbalance": ka["imbalance"] * flip} if ka else None),
            })
    return rows


def _confirms(m: dict | None) -> bool | None:
    if m is None:
        return None
    return m["drift"] > 0 or m["imbalance"] > C.IMBALANCE_MIN


VARIANTS = ["Polymarket (what the rule reads now)", "Kalshi (the better prices)",
            "both venues confirm", "Polymarket drift only", "Kalshi drift only"]


def _gate(r: dict, v: str) -> bool | None:
    pm, ka = r["pm"], r["ka"]
    if v.startswith("Polymarket (") :
        return _confirms(pm)
    if v.startswith("Kalshi ("):
        return _confirms(ka)
    if v == "both venues confirm":
        a, b = _confirms(pm), _confirms(ka)
        return None if a is None or b is None else (a and b)
    if v == "Polymarket drift only":
        return None if pm is None else pm["drift"] > 0
    if v == "Kalshi drift only":
        return None if ka is None else ka["drift"] > 0
    return None


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


def _boot(p, f) -> tuple[float, float]:
    gp, gf = defaultdict(list), defaultdict(list)
    for r in p:
        gp[r["date"]].append(grade.american_profit(r["odds"]) if r["won"] else -1)
    for r in f:
        gf[r["date"]].append(grade.american_profit(r["odds"]) if r["won"] else -1)
    days = sorted(set(gp) | set(gf))
    if len(days) < 5:
        return (float("nan"), float("nan"))
    rng = random.Random(919)
    out = []
    for _ in range(TRIALS):
        va, vb = [], []
        for _ in days:
            d = days[rng.randrange(len(days))]
            va += gp.get(d, [])
            vb += gf.get(d, [])
        if va and vb:
            out.append((st.mean(va) - st.mean(vb)) * 100)
    out.sort()
    return out[int(.025 * len(out))], out[int(.975 * len(out))]


def build() -> str:
    rows = collect()
    md = ["# Is the book-confirm gate worthless, or are we reading the wrong "
          "venue?", "",
          "_`gate_sweep` put the gate at +1.3 points on 958 games — nothing. But "
          "the gate reads Polymarket, and against the sportsbook's own de-vigged "
          "price Polymarket is off by 0.038 where the venues agree and 0.206 "
          "where they diverge, against Kalshi's 0.007 and 0.018. A gate fed by a "
          "price that noisy would measure nothing even if confirmation were "
          "real — so \"worthless\" and \"fed garbage\" predict the same +1.3, and "
          "only swapping the venue tells them apart._", "",
          f"- graded games with a majority side: **{len(rows)}**",
          f"- with a usable Polymarket read: "
          f"**{sum(1 for r in rows if r['pm'])}**",
          f"- with a usable Kalshi read: **{sum(1 for r in rows if r['ka'])}**",
          f"- Kalshi usable where Polymarket is NOT: "
          f"**{sum(1 for r in rows if r['ka'] and not r['pm'])}**", ""]
    if len(rows) < 300:
        return "\n".join(md + ["Not enough games.", ""])

    md += ["## The same gate, different venue", "",
           "| gate | pass / fail | PASS | FAIL | worth | 95% CI on worth |",
           "|---|---|---|---|---|---|"]
    cells = {}
    for v in VARIANTS:
        p = [r for r in rows if _gate(r, v) is True]
        f = [r for r in rows if _gate(r, v) is False]
        if min(len(p), len(f)) < MIN_CELL:
            md.append(f"| {v} | {len(p)} / {len(f)} | _too thin_ | | | |")
            continue
        d = (_roi(p) - _roi(f)) * 100
        cells[v] = (d, p, f)
        lo, hi = _boot(p, f)
        ci = "—" if lo != lo else f"{lo:+.1f} to {hi:+.1f}"
        md.append(f"| {v} | {len(p)} / {len(f)} | {_fmt(p)} | {_fmt(f)} | "
                  f"**{d:+.1f} pts** | {ci} |")
    md.append("")

    # the live rule's first gate applied, since that is where it would live
    md += ["## Among games that already pass handle=tickets", "",
           "_Where the gate actually sits in the rule._", "",
           "| gate | pass / fail | PASS | FAIL | worth |", "|---|---|---|---|---|"]
    mo = [r for r in rows if r["money_ok"]]
    for v in VARIANTS:
        p = [r for r in mo if _gate(r, v) is True]
        f = [r for r in mo if _gate(r, v) is False]
        if min(len(p), len(f)) < 25:
            md.append(f"| {v} | {len(p)} / {len(f)} | _too thin_ | | |")
            continue
        md.append(f"| {v} | {len(p)} / {len(f)} | {_fmt(p)} | {_fmt(f)} | "
                  f"**{(_roi(p)-_roi(f))*100:+.1f} pts** |")
    md.append("")

    if cells:
        order = list(cells)
        idx = {v: ([i for i, r in enumerate(rows) if _gate(r, v) is True],
                   [i for i, r in enumerate(rows) if _gate(r, v) is False])
               for v in order}
        prof = [grade.american_profit(r["odds"]) for r in rows]
        prob = [r["p"] for r in rows]
        rng = random.Random(1212)
        hi_d = []
        for _ in range(TRIALS):
            draw = [prof[i] if rng.random() < prob[i] else -1 for i in range(len(rows))]
            hi_d.append(max((sum(draw[i] for i in pi) / len(pi)
                             - sum(draw[i] for i in fi) / len(fi)) * 100
                            for pi, fi in idx.values()))
        best = max(cells, key=lambda v: cells[v][0])
        obs = cells[best][0]
        pv = (sum(1 for x in hi_d if x >= obs) + 1) / (TRIALS + 1)
        md += [f"## Corrected for trying {len(cells)} venue variants", "",
               f"- best: **{best}** at {obs:+.1f} pts · the best of "
               f"{len(cells)} reaches {st.median(hi_d):+.1f} median, "
               f"{sorted(hi_d)[int(.95*TRIALS)]:+.1f} at the 95th · "
               f"**corrected p = {pv:.3f}**", ""]
        rh = random.Random(1313)
        _, p, f = cells[best]
        tp = [rh.random() < 0.5 for _ in p]
        tf = [rh.random() < 0.5 for _ in f]
        pa = [x for x, t in zip(p, tp) if t]; pb = [x for x, t in zip(p, tp) if not t]
        fa = [x for x, t in zip(f, tf) if t]; fb = [x for x, t in zip(f, tf) if not t]
        if min(len(pa), len(pb), len(fa), len(fb)) >= 20:
            md.append(f"- split-half of **{best}**: "
                      f"{(_roi(pa)-_roi(fa))*100:+.1f} pts on one half, "
                      f"{(_roi(pb)-_roi(fb))*100:+.1f} pts on the other")
        md.append("")

    md += ["## What follows", "",
           "- if the **Kalshi** row is worth materially more than the "
           "Polymarket row, the gate was never worthless — it was mis-fed, and "
           "the fix is to read the other venue",
           "- if both rows are near zero, order-book confirmation really does "
           "carry nothing and the gate should come out of the rule",
           "- the **Kalshi usable where Polymarket is not** count is free "
           "sample either way: games like today's Atlanta, discarded for a "
           "20-cent Polymarket spread while Kalshi quoted one cent", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "venue_swap.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
