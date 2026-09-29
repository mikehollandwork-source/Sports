"""
Line movement when the money disagrees.

THE IDEA
A line that moves TOWARD a side the money is not on is the classic "someone knows
something" tell: the book is repricing against its own visible action. This asks
whether any configuration of (line direction, handle side, ticket side, real
Polymarket money) is actually profitable - and it tests both directions of every
configuration, because a tell only means something if backing it beats backing
its opposite.

THE FOUR SIGNALS, all already in the snapshots
    shift        pick_criteria.line_check.implied_shift, signed TOWARD the
                 advantage side (so >0 = line moved to adv, <0 = moved to opp)
    handle       public_check.money_side - where the DOLLARS are
    tickets      public_majority.team - where the BET COUNT is
    PM money     pre-game Polymarket drift / resting-size imbalance

"The money disagrees" is deliberately tested in three distinct senses, because
they are different things and get conflated constantly:
    line vs handle    the price moved away from the dollars
    line vs tickets   the classic reverse line move (price moved away from the crowd)
    handle vs tickets sharp/square split, with the line as tiebreaker

Every row: bet the line side AND bet its opposite, in-sample vs holdout. The
strongest cut gets a day-block bootstrap CI and a market-calibrated null p-value,
because scanning this many configurations manufactures winners on its own.

Writes output/line_vs_money.md.
"""

from __future__ import annotations

import glob
import json
import random
import statistics as st
from pathlib import Path

from . import grade, mlb_api
from .consensus import book_metrics

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
HOLDOUT_FROM = "2026-07-23"
MOVE_MIN = 0.01          # what counts as the line actually moving (implied prob)
BOOTSTRAP = 2000
NULL_SIMS = 1500
SEED = 20260729


def _implied(ml: int) -> float:
    return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)


def collect() -> list[dict]:
    recs = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        day = json.loads(Path(f).read_text())
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        pmm = book_metrics(date)
        for g in day.get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            if " @ " not in g.get("matchup", ""):
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            away, home = g["matchup"].split(" @ ")
            opp = home if adv == away else away
            lc = pc.get("line_check") or {}
            shift = lc.get("implied_shift")
            if not isinstance(shift, (int, float)):
                continue

            chk = g.get("public_check") or {}
            ms = chk.get("money_side")
            handle = home if ms == "home" else away if ms == "away" else None
            tickets = (g.get("public_majority") or {}).get("team")

            m = pmm.get(g.get("game_pk"))
            pm_team = None
            if m:
                toward_adv = m["drift"] > 0 or m["imbalance"] > 0.2
                pm_team = adv if toward_adv else opp

            # which side did the line move toward?
            line_team = None
            if shift >= MOVE_MIN:
                line_team = adv
            elif shift <= -MOVE_MIN:
                line_team = opp

            recs.append({
                "date": date, "winner": res["winner"],
                "price": {adv: a_ml, opp: o_ml},
                "adv": adv, "opp": opp,
                "line_team": line_team, "shift": shift,
                "timing": lc.get("timing"),
                "handle": handle, "tickets": tickets, "pm_team": pm_team,
                "holdout": date >= HOLDOUT_FROM,
            })
    return recs


def _other(r, team):
    return r["opp"] if team == r["adv"] else r["adv"]


def _rows(recs, chooser):
    out = []
    for r in recs:
        t = chooser(r)
        if not t or t not in r["price"]:
            continue
        out.append({"won": r["winner"] == t, "odds": r["price"][t],
                    "date": r["date"], "holdout": r["holdout"]})
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


def _pair_row(label, sub):
    """Bet the LINE side vs bet its opposite, all / holdout."""
    ln = lambda r: r["line_team"]
    op = lambda r: _other(r, r["line_team"]) if r["line_team"] else None
    h = [r for r in sub if r["holdout"]]
    return (f"| {label} | {_fmt(_rows(sub, ln))} | {_fmt(_rows(h, ln))} "
            f"| {_fmt(_rows(sub, op))} | {_fmt(_rows(h, op))} |")


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


def _null_p(sub, chooser, observed):
    rnd = random.Random(SEED)
    prep = []
    for r in sub:
        teams = list(r["price"])
        if len(teams) != 2:
            continue
        p = [_implied(r["price"][t]) for t in teams]
        tot = sum(p) or 1.0
        prep.append((r, teams, p[0] / tot))
    beat = 0
    for _ in range(NULL_SIMS):
        sim = [{**r, "winner": teams[0] if rnd.random() < p0 else teams[1]}
               for r, teams, p0 in prep]
        v = _roi(_rows(sim, chooser))
        if v is not None and v >= observed:
            beat += 1
    return beat / NULL_SIMS


def build() -> str:
    recs = collect()
    if not recs:
        return "# Line vs money\n\n_No graded games with a line read._"
    moved = [r for r in recs if r["line_team"]]
    H = ("| slice | BET line side (all) | BET line side (holdout) | "
         "BET opposite (all) | BET opposite (holdout) |\n|---|---|---|---|---|")

    md = [f"# Line movement when the money disagrees — {len(recs)} games "
          f"({len(moved)} where the line actually moved ≥{MOVE_MIN:.0%})", "",
          "_'BET line side' backs whichever team the price moved toward; 'BET "
          "opposite' backs the other one. A tell is only real if one side clearly "
          "beats the other._", ""]

    # 1. does line movement alone mean anything?
    md += ["## 1. Line movement on its own", "", H,
           _pair_row("line moved at all", moved)]
    for lo, hi, lab in ((0.01, 0.02, "small move (1–2%)"), (0.02, 0.04, "solid (2–4%)"),
                        (0.04, 9, "big move (4%+)")):
        md.append(_pair_row(lab, [r for r in moved if lo <= abs(r["shift"]) < hi]))
    md.append("")

    # 2. line vs HANDLE (the dollars)
    md += ["## 2. Line vs HANDLE — price moved away from the dollars", "", H]
    hh = [r for r in moved if r["handle"]]
    md.append(_pair_row("line AGREES with handle", [r for r in hh if r["line_team"] == r["handle"]]))
    md.append(_pair_row("line DISAGREES with handle", [r for r in hh if r["line_team"] != r["handle"]]))
    md.append("")

    # 3. line vs TICKETS (classic reverse line move)
    md += ["## 3. Line vs TICKETS — the classic reverse line move", "", H]
    tt = [r for r in moved if r["tickets"]]
    md.append(_pair_row("line AGREES with tickets", [r for r in tt if r["line_team"] == r["tickets"]]))
    md.append(_pair_row("REVERSE line move (line ≠ tickets)",
                        [r for r in tt if r["line_team"] != r["tickets"]]))
    md.append("")

    # 4. handle vs tickets, with the line as tiebreaker
    md += ["## 4. When HANDLE and TICKETS disagree, who does the line side with?", "", H]
    split = [r for r in moved if r["handle"] and r["tickets"] and r["handle"] != r["tickets"]]
    md.append(_pair_row("handle ≠ tickets (any line move)", split))
    md.append(_pair_row("  ...line sided with the HANDLE",
                        [r for r in split if r["line_team"] == r["handle"]]))
    md.append(_pair_row("  ...line sided with the TICKETS",
                        [r for r in split if r["line_team"] == r["tickets"]]))
    md.append(_pair_row("handle = tickets (aligned)",
                        [r for r in moved if r["handle"] and r["tickets"]
                         and r["handle"] == r["tickets"]]))
    md.append("")

    # 5. line vs POLYMARKET money
    md += ["## 5. Line vs POLYMARKET money", "", H]
    pp = [r for r in moved if r["pm_team"]]
    md.append(_pair_row("line AGREES with PM money",
                        [r for r in pp if r["line_team"] == r["pm_team"]]))
    md.append(_pair_row("line DISAGREES with PM money",
                        [r for r in pp if r["line_team"] != r["pm_team"]]))
    md.append("")

    # 6. when did the move happen?
    md += ["## 6. By when the move happened", "", H]
    for t, lab in (("early", "sharp window (overnight)"), ("late", "public window (daytime)"),
                   ("both", "both windows")):
        md.append(_pair_row(lab, [r for r in moved if r["timing"] == t]))
    md.append("")

    # 7. rigour on the best cut with a usable sample
    cands = [
        ("line DISAGREES with handle", [r for r in hh if r["line_team"] != r["handle"]]),
        ("REVERSE line move (line ≠ tickets)", [r for r in tt if r["line_team"] != r["tickets"]]),
        ("line sided with the HANDLE on a split", [r for r in split if r["line_team"] == r["handle"]]),
        ("line DISAGREES with PM money", [r for r in pp if r["line_team"] != r["pm_team"]]),
        ("line AGREES with handle", [r for r in hh if r["line_team"] == r["handle"]]),
    ]
    best = None
    for lab, sub in cands:
        for dirn, ch in (("line side", lambda r: r["line_team"]),
                         ("opposite", lambda r: _other(r, r["line_team"]) if r["line_team"] else None)):
            rr = _rows(sub, ch)
            v = _roi(rr)
            if v is not None and len(rr) >= 30 and (best is None or v > best[0]):
                best = (v, lab, dirn, sub, ch, rr)
    md += ["## 7. Rigour on the strongest cut (n≥30)", ""]
    if best:
        v, lab, dirn, sub, ch, rr = best
        md += [f"**{lab} — bet the {dirn}** — {_fmt(rr)}", ""]
        ci = _bootstrap(rr)
        if ci:
            lo, hi, med = ci
            md += [f"- Day-block bootstrap 95% CI: **{lo:+.1%} to {hi:+.1%}** "
                   f"(median {med:+.1%}) — "
                   + ("cannot rule out zero." if lo <= 0 else "**excludes zero**."), ""]
        p = _null_p(sub, ch, v)
        md += [f"- Market-calibrated null p-value: **{p:.3f}** — this good or better "
               f"happens {p:.1%} of the time with realistic prices and no edge."
               + ("  Not significant." if p > 0.05 else "  Significant at 5%."), ""]
    else:
        md += ["_No cut reached n≥30._", ""]

    md.append("_Roughly 20 configurations are scanned here. Expect one or two to look "
              "great by chance - the holdout column and the p-value are what separate "
              "a tell from a coincidence._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "line_vs_money.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
