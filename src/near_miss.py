"""
The games that ALMOST qualified - the biggest untested pool we have.

THE IDEA
Every board rejects four or five games that clear five of the six gates and die
on one. That is roughly ten times the pick volume, sitting unexamined, and the
question has never been asked directly: is a game that fails exactly ONE gate
still worth backing?

It is not obviously no. Each gate was added because it improved the whole, but
"improves the average" and "every rejection is correctly rejected" are different
claims, and only the first has ever been tested. If one gate is doing the real
work and the others are near-neutral, then games dying on a near-neutral gate
are being thrown away for nothing.

WHAT IS TESTED
  * games failing exactly one gate, split by WHICH gate killed them
  * the same games split by whether the consensus side is also the stat model's
    advantage side - a free split never looked at
  * slate size, because a 15-game night and a 5-game night are different markets
  * same-day clustering, because if picks on one slate move together the effective
    sample is days, not bets

WHY IT MIGHT STILL BE NOTHING
Six gate-groups plus the extra splits is another grid, and this dataset has
produced a great-looking cell from sixteen consecutive grids. So every cell is
scored against a max-statistic null, and the headline is a SPLIT-HALF: if the
good gate-groups in one half are the good ones in the other, this is real. That
test has killed two candidates cleanly and it is the fastest way to a definitive
answer here.

Writes output/near_miss.md.
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
from .pregame_money import HOLDOUT_FROM, _implied

log = logging.getLogger("near_miss")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MIN_CELL = 30
TRIALS = 3000


def collect() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            metrics = C.book_metrics(date)
            results = mlb_api.results_for(date)
        except Exception:
            continue
        day = json.loads(Path(f).read_text())
        slate = len(day.get("games") or [])
        for g in day.get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            pc = g.get("pick_criteria") or {}
            chk = g.get("public_check") or {}
            maj = (g.get("public_majority") or {}).get("team")
            adv = pc.get("advantage_team")
            m = g.get("matchup") or ""
            if not maj or not adv or " @ " not in m:
                continue
            odds = (pc.get("advantage_moneyline") if maj == adv
                    else pc.get("opponent_moneyline"))
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not isinstance(odds, int) or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            mm = metrics.get(g.get("game_pk"))
            shift = (pc.get("line_check") or {}).get("implied_shift")
            toward = (shift if maj == adv else -shift) if isinstance(shift, (int, float)) else None

            gates = {
                "handle=tickets": chk.get("money") == "with public",
                "book read": mm is not None,
                "book confirms": (C._confirms(mm, maj == adv) if mm else False),
                "line against": (toward is not None and toward <= -C.LINE_MOVE_MIN),
            }
            failed = [k for k, v in gates.items() if not v]
            tot = _implied(a_ml) + _implied(o_ml)
            rows.append({
                "date": date, "pk": g.get("game_pk"), "matchup": m,
                "bet": maj, "odds": odds, "won": res["winner"] == maj,
                "failed": failed, "nfail": len(failed),
                "is_adv": maj == adv, "slate": slate,
                "p": (_implied(odds) / tot) if tot > 0 else 0.5,
            })
    return rows


def _roi(rs, wins=None) -> float:
    if not rs:
        return 0.0
    u = 0.0
    for r in rs:
        won = r["won"] if wins is None else wins[r["pk"]]
        u += grade.american_profit(r["odds"]) if won else -1
    return u / len(rs)


def _fmt(rs) -> str:
    if not rs:
        return "—"
    w = sum(1 for r in rs if r["won"])
    tag = "" if len(rs) >= MIN_CELL else "_"
    return f"{tag}{w}-{len(rs)-w} · {_roi(rs):+.1%} (n={len(rs)}){tag}"


def build() -> str:
    rows = collect()
    md = ["# Near-misses — the games that almost qualified", "",
          "_Roughly ten times the pick volume, never examined. Every gate was "
          "added because it improved the average; that is a different claim from "
          "every rejection being correct, and only the first has been tested._",
          "", f"- graded games with a consensus side: **{len(rows)}**", ""]
    if len(rows) < 200:
        return "\n".join(md + ["Too few games.", ""])

    md += ["## By how many gates failed", "",
           "| gates failed | backing the consensus side |", "|---|---|"]
    for k in range(0, 5):
        md.append(f"| {k}{' (these are the picks)' if k == 0 else ''} | "
                  f"{_fmt([r for r in rows if r['nfail'] == k])} |")
    md.append("")

    one = [r for r in rows if r["nfail"] == 1]
    cells: dict = {}
    md += ["## Failing exactly ONE gate — which gate killed it?", "",
           f"_{len(one)} games. If a gate is near-neutral, games dying on it are "
           "being thrown away for nothing._", "",
           "| the one gate it failed | backing the consensus side |", "|---|---|"]
    for gate in ("handle=tickets", "book read", "book confirms", "line against"):
        sub = [r for r in one if r["failed"] == [gate]]
        if len(sub) >= MIN_CELL:
            cells[f"only {gate}"] = sub
        md.append(f"| {gate} | {_fmt(sub)} |")
    md.append("")

    md += ["## Free splits never looked at", "",
           "| split | backing the consensus side |", "|---|---|",
           f"| picks where consensus IS the stat model's side | "
           f"{_fmt([r for r in rows if r['nfail'] == 0 and r['is_adv']])} |",
           f"| picks where consensus is NOT | "
           f"{_fmt([r for r in rows if r['nfail'] == 0 and not r['is_adv']])} |",
           f"| near-miss, consensus IS the stat side | "
           f"{_fmt([r for r in one if r['is_adv']])} |",
           f"| near-miss, consensus is NOT | "
           f"{_fmt([r for r in one if not r['is_adv']])} |", ""]
    for lbl, sub in (("adv picks", [r for r in rows if r["nfail"] == 0 and r["is_adv"]]),
                     ("nonadv picks", [r for r in rows if r["nfail"] == 0 and not r["is_adv"]]),
                     ("adv near-miss", [r for r in one if r["is_adv"]]),
                     ("nonadv near-miss", [r for r in one if not r["is_adv"]])):
        if len(sub) >= MIN_CELL:
            cells[lbl] = sub

    md += ["## Slate size", "",
           "_A 15-game night and a 5-game night are different markets._", "",
           "| slate | picks | near-misses |", "|---|---|---|"]
    for lbl, t in (("≤8 games", lambda r: r["slate"] <= 8),
                   ("9-12", lambda r: 9 <= r["slate"] <= 12),
                   ("13+", lambda r: r["slate"] >= 13)):
        md.append(f"| {lbl} | {_fmt([r for r in rows if r['nfail'] == 0 and t(r)])} | "
                  f"{_fmt([r for r in one if t(r)])} |")
    md.append("")

    # same-day clustering: is the effective sample days rather than bets?
    byd = defaultdict(list)
    for r in rows:
        if r["nfail"] == 0:
            byd[r["date"]].append(r)
    multi = [v for v in byd.values() if len(v) >= 2]
    same = sum(1 for v in multi
               if len({x["won"] for x in v}) == 1)
    md += ["## Do same-day picks move together?", "",
           f"- days with 2+ picks: **{len(multi)}**",
           f"- days where they ALL won or ALL lost: **{same}** "
           f"({same/len(multi):.0%})" if multi else "- too few multi-pick days",
           "", "_If picks on one slate move together the effective sample is "
           "days, not bets, and every confidence interval in this repo is "
           "narrower than it should be._", ""]

    if not cells:
        return "\n".join(md + ["No cell reaches the minimum.", ""])

    # ---- correction + split-half ----
    best = max(cells, key=lambda k: _roi(cells[k]))
    bv = _roi(cells[best])
    rng = random.Random(1229)
    null = []
    for _ in range(TRIALS):
        wins = {r["pk"]: rng.random() < r["p"] for r in rows}
        null.append(max(_roi(v, wins) for v in cells.values()))
    pv = sum(1 for x in null if x >= bv) / TRIALS
    null.sort()
    md += ["## Does the best cell beat the search?", "",
           f"- cells at n≥{MIN_CELL}: **{len(cells)}**",
           f"- best: `{best}` at **{bv:+.1%}** (n={len(cells[best])})",
           f"- median best-in-noise: **{st.median(null):+.1%}**",
           f"- **corrected p = {pv:.3f}**", ""]
    md += (["**Clears.**", ""] if pv <= 0.05 else
           ["**Does not clear.**", ""])

    dates = sorted({r["date"] for r in rows})
    mid = dates[len(dates) // 2]
    pairs = []
    for k, v in cells.items():
        a = [r for r in v if r["date"] < mid]
        b = [r for r in v if r["date"] >= mid]
        if len(a) >= 10 and len(b) >= 10:
            pairs.append((k, _roi(a), _roi(b)))
    md += ["## Split-half — would the good cells have stayed good?", ""]
    if len(pairs) < 3:
        md += ["Too few cells have games in both halves.", ""]
        return "\n".join(md)
    md += ["| cell | first half | second half |", "|---|---|---|"]
    for k, a, b in sorted(pairs, key=lambda x: -x[1]):
        md.append(f"| {k} | {a:+.1%} | {b:+.1%} |")
    xs, ys = [p[1] for p in pairs], [p[2] for p in pairs]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    r = (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (dx * dy)) if dx and dy else float("nan")
    md += ["", f"- correlation between halves: **r = {r:+.2f}**", ""]
    md += (["**The ranking holds.** Worth pursuing.", ""] if r > 0.4 else
           ["**The ranking does not hold.** A cell's first-half record does not "
            "predict its second, which is the same verdict the team scan and the "
            "fade profile reached.", ""])
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "near_miss.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
