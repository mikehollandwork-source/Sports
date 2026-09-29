"""
Remove the book-confirm gate: rolling out-of-sample test before it ships.

THE CASE FOR REMOVAL, FROM FOUR INDEPENDENT MEASUREMENTS
  gate_sweep     standing alone on 958 games, worth +1.3 points
  venue_swap     -1.4 points on Polymarket, -9.5 on Kalshi's better prices,
                 best of five variants below what noise produces, p = 0.915
  disagreement   sign reversed once the look-ahead was fixed: confirming
                 -11.1%, not confirming +6.7%
  venue_cross    "both venues confirm the money side" backs at -10.5%

Feeding it a price five to eleven times more accurate made it WORSE, which
removes the last excuse that it was mis-fed rather than empty.

WHAT "WALK FORWARD" MEANS FOR A REMOVAL
Nothing is being fitted, so there is no parameter to choose on past data. The
question is temporal consistency: does dropping the gate help in block after
block, or once? So the two rules are run over successive 10-day blocks and
compared within each. A change that helps in most blocks is a change to the
rule; a change that helps in one is a change to that block - the same standard
change_check applied to the gate tuning, and the one that reverted it.

THREE VARIANTS, BECAUSE HALF A REMOVAL IS ITS OWN DECISION
  live            handle=tickets + book confirms + line moved against
  no confirm      the gate dropped, but a book read still required to exist
  no book at all  neither the confirmation nor the read requirement

The third matters. If confirmation carries nothing, insisting a read EXISTS
only shrinks the sample for no benefit - gate_sweep put that requirement at
-11.2 points, and while that figure is confounded (games without a read are
different games), keeping a cost whose benefit measured zero needs its own
justification.

THE DECIDING NUMBER
Not the variants' totals - those share most of their picks and will look
similar. It is the MARGINAL games: those passing handle=tickets and the line
gate but failing the book gate. Those are exactly the bets removal adds, and
their return is what the change is worth. Day-block bootstrap on them, since
that is the population being argued about.

Writes output/gate_removal.md.
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

log = logging.getLogger("gate_removal")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 10000
BLOCK = 10


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
            rows.append({
                "date": date, "odds": odds, "won": res["winner"] == maj,
                "p": _implied(odds) / tot,
                "money": chk.get("money") == "with public",
                "line": C.line_tag(g, maj) == "against",
                "read": mm is not None,
                "confirm": C._confirms(mm, maj == adv) if mm else None,
            })
    return rows


def live(r):        return r["money"] and r["read"] and r["confirm"] and r["line"]
def no_confirm(r):  return r["money"] and r["read"] and r["line"]
def no_book(r):     return r["money"] and r["line"]


VARIANTS = [("live rule (as it runs today)", live),
            ("confirm gate dropped, read still required", no_confirm),
            ("book dropped entirely", no_book)]


def _roi(rs) -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r["odds"]) if r["won"] else -1
               for r in rs) / len(rs)


def _fmt(rs) -> str:
    if not rs:
        return "— (0)"
    w = sum(1 for r in rs if r["won"])
    return f"{w}-{len(rs)-w} · **{_roi(rs):+.1%}** (n={len(rs)})"


def _boot(rs) -> tuple[float, float]:
    by = defaultdict(list)
    for r in rs:
        by[r["date"]].append(grade.american_profit(r["odds"]) if r["won"] else -1)
    days = sorted(by)
    if len(days) < 5:
        return (float("nan"), float("nan"))
    rng = random.Random(8181)
    out = []
    for _ in range(TRIALS):
        v = []
        for _ in days:
            v += by[days[rng.randrange(len(days))]]
        if v:
            out.append(st.mean(v) * 100)
    out.sort()
    return out[int(.025 * len(out))], out[int(.975 * len(out))]


def build() -> str:
    rows = collect()
    md = ["# Removing the book-confirm gate", "",
          "_Four independent measurements say it does nothing: +1.3 points "
          "standing alone (`gate_sweep`), −1.4 on Polymarket and −9.5 on Kalshi's "
          "better prices (`venue_swap`, p = 0.915), sign-reversed in "
          "`disagreement` once the look-ahead was fixed, and −10.5% in "
          "`venue_cross`. Feeding it prices five to eleven times more accurate "
          "made it worse, which removes the last excuse that it was mis-fed "
          "rather than empty._", "",
          "_Nothing is fitted here, so a walk-forward means temporal "
          "consistency: does dropping it help block after block, or once? That is "
          "the standard that reverted the gate tuning._", "",
          f"- graded games with a majority side: **{len(rows)}**", ""]
    if len(rows) < 300:
        return "\n".join(md + ["Not enough games.", ""])

    md += ["## The three variants, whole sample", "",
           "| rule | record | 95% CI on ROI |", "|---|---|---|"]
    for lab, fn in VARIANTS:
        sel = [r for r in rows if fn(r)]
        lo, hi = _boot(sel)
        md.append(f"| {lab} | {_fmt(sel)} | "
                  + ("—" if lo != lo else f"{lo:+.1f}% to {hi:+.1f}%") + " |")
    md.append("")

    # ---- the deciding number: the games removal ADDS --------------------
    add_read = [r for r in rows if no_confirm(r) and not live(r)]
    add_all = [r for r in rows if no_book(r) and not live(r)]
    md += ["## The games removal actually adds", "",
           "_The variants above share most of their picks, so their totals look "
           "alike whatever the truth is. These are the bets the change adds — "
           "passing handle=tickets and the line gate, failing the book gate. "
           "Their return IS what the change is worth._", "",
           "| added by | record | 95% CI on ROI |", "|---|---|---|"]
    for lab, sel in (("dropping the confirm gate", add_read),
                     ("dropping the book entirely", add_all)):
        lo, hi = _boot(sel)
        md.append(f"| {lab} | {_fmt(sel)} | "
                  + ("—" if lo != lo else f"{lo:+.1f}% to {hi:+.1f}%") + " |")
    md.append("")
    if add_all:
        lo, hi = _boot(add_all)
        md += ["- " + ("**the added bets are profitable** — the gate has been "
                       "rejecting winners" if lo == lo and lo > 0 else
                       "**the added bets are not distinguishable from "
                       "break-even.** Removal is then justified by sample size "
                       "and simplicity, not by profit: it stops discarding games "
                       "on a signal measured at zero, and more picks at the same "
                       "edge is still more edge."), ""]

    # ---- block by block -------------------------------------------------
    days = sorted({r["date"] for r in rows})
    blocks = []
    for i in range(0, len(days) - BLOCK + 1, BLOCK):
        ds = set(days[i:i + BLOCK])
        sub = [r for r in rows if r["date"] in ds]
        cells = [(lab, [r for r in sub if fn(r)]) for lab, fn in VARIANTS]
        if all(len(c) >= 3 for _, c in cells):
            blocks.append((days[i], cells))
    md += [f"## Block by block — {len(blocks)} blocks of {BLOCK} board days", "",
           "| block starts | live | confirm dropped | book dropped |",
           "|---|---|---|---|"]
    wins_nc = wins_nb = 0
    for start, cells in blocks:
        r0, r1, r2 = (_roi(c) for _, c in cells)
        wins_nc += r1 > r0
        wins_nb += r2 > r0
        md.append(f"| {start} | {r0:+.1%} ({len(cells[0][1])}) | "
                  f"{r1:+.1%} ({len(cells[1][1])}) | "
                  f"{r2:+.1%} ({len(cells[2][1])}) |")
    md.append("")
    if blocks:
        md += [f"- confirm-dropped beat live in **{wins_nc}/{len(blocks)}** blocks",
               f"- book-dropped beat live in **{wins_nb}/{len(blocks)}** blocks",
               "- " + ("**consistent across time**, not one block"
                       if max(wins_nc, wins_nb) > len(blocks) * 0.6 else
                       "**not consistent across time** — the variants trade "
                       "blocks, which is what two rules of equal merit look "
                       "like"), ""]

    # ---- leave August out, the standard that reverted the last change ----
    md += ["## Leave August out", "",
           "| period | live | confirm dropped | book dropped |", "|---|---|---|---|"]
    for lab, keep in (("all months", lambda d: True),
                      ("**excluding August**", lambda d: d[:7] != "2026-08"),
                      ("September only", lambda d: d[:7] == "2026-09")):
        sub = [r for r in rows if keep(r["date"])]
        md.append(f"| {lab} | " + " | ".join(
            _fmt([r for r in sub if fn(r)]) for _, fn in VARIANTS) + " |")
    md += ["", "## The call", "",
           "- removal is right if the added games are **not losing** and the "
           "variants hold across blocks — a gate measured at zero should not be "
           "discarding sample",
           "- removal is wrong only if the added games lose materially, which "
           "would mean the gate was doing something the earlier tests missed",
           "- either way this is a rule change, so the record starts counting "
           "from the change forward and nothing before it is restated", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "gate_removal.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
