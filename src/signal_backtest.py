"""
Snapshot backtest: grade the CURRENT system's signals against actual results using
the FROZEN boards (output/picks_*.json) as the point-in-time truth - the snapshots
already captured the pre-game money/public/stat state that can't be reconstructed
after the fact (unlike src/backtest.py, which re-derives and hits the forum-history
limit). Recomputes the 7 signals + the Vegas-needed side from each snapshot and
grades vs the MLB Stats API winner. $1/bet at the frozen moneyline.

Reports: each signal alone, signal-count buckets, the best 2-3 signal COMBOS, and
whether tailing the side VEGAS needed would be up or down units.

Runs on GitHub Actions (the MLB API is firewalled in the dev sandbox). Writes
output/signal_backtest.md.
"""

from __future__ import annotations

import glob
import itertools
import json
from pathlib import Path

from . import grade, mlb_api
from .main import _book_needs, _book_stance
from .analysis import LEAN_STRONG_MARGIN, LEAN_MIN_CONSISTENCY

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
SIGNALS = ("margin", "favorite", "line", "consistency", "bvp", "sharp", "form")


def _adv_side(g: dict) -> str | None:
    pc = g.get("pick_criteria") or {}
    adv = pc.get("advantage_team")
    if not adv or " @ " not in g.get("matchup", ""):
        return None
    away, home = g["matchup"].split(" @ ")
    return "home" if adv == home else "away" if adv == away else None


def signals(g: dict) -> dict | None:
    """The 7 signals for the advantage team, recomputed from the frozen snapshot.
    None when an input wasn't recorded (older board) - excluded from that signal's
    row so coverage stays honest."""
    pc = g.get("pick_criteria") or {}
    adv = pc.get("advantage_team")
    side = _adv_side(g)
    if not adv or side is None:
        return None
    ml = pc.get("advantage_moneyline")
    margin = (pc.get("components") or {}).get("stat_edge", {}).get("margin")
    lc = pc.get("line_check") or {}
    bt = (g.get("back_test") or {}).get(side) or {}
    out_hit = bt.get("out_hit")
    cons_hits = (pc.get("components") or {}).get("consistency", {}).get("hits")
    cons = out_hit if out_hit is not None else cons_hits
    b = g.get("bvp") or {}
    cc = g.get("public_check") or {}
    maj = (g.get("public_majority") or {}).get("team")
    fm = g.get("form") or {}
    fa = (fm.get(side) or {}).get("delta")
    fo = (fm.get("away" if side == "home" else "home") or {}).get("delta")
    return {
        "margin": None if margin is None else margin >= LEAN_STRONG_MARGIN,
        "favorite": None if ml is None else ml < 0,
        "line": None if not lc.get("status") else lc.get("status") == "confirms",
        "consistency": None if cons is None else cons >= LEAN_MIN_CONSISTENCY,
        "bvp": None if not b else not (b.get("edge_team") and b.get("meaningful", True)
                                       and b["edge_team"] != adv),
        "sharp": (None if not cc.get("money_side") or not maj
                  else cc.get("money_side") == side and maj != adv),
        "form": (None if fa is None or fo is None or abs(fa - fo) < 0.015 else fa > fo),
        "_ml": ml, "_adv": adv,
    }


def _units(rows: list[dict]) -> tuple[int, int, float]:
    w = sum(1 for r in rows if r["won"])
    u = sum((grade.american_profit(r["odds"]) if r["won"] else -1)
            for r in rows if r.get("odds"))
    return w, len(rows) - w, round(u, 2)


def _row(label: str, rows: list[dict]) -> str:
    if not rows:
        return f"| {label} | 0 | — |"
    w, l, u = _units(rows)
    return f"| {label} | {w}-{l} ({w / len(rows):.0%}) | {u:+.2f}u |"


def build() -> str:
    games: list[dict] = []
    total = graded = 0
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        day = json.loads(Path(f).read_text())
        try:
            results = mlb_api.results_for(date)
        except Exception:
            results = {}
        for g in day.get("games", []):
            total += 1
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            sig = signals(g)
            if not sig:
                continue
            graded += 1
            adv = sig["_adv"]
            rec = {"won": res["winner"] == adv, "odds": sig["_ml"], "sig": sig,
                   "stance_against": bool((_book_stance(g) or {}).get("against_us"))}
            bn = _book_needs(g)
            if bn:
                rec.update(veg_won=res["winner"] == bn["bet"], veg_odds=bn["odds"],
                           veg_basis=bn["basis"])
            games.append(rec)

    md = [f"# Signal backtest — {graded} graded of {total} game snapshots", ""]

    md += ["## Each signal alone (bet the advantage team when it fires)", "",
           "| signal | record | units |", "|---|---|---|"]
    for s in SIGNALS:
        md.append(_row(f"{s} (n={sum(1 for g in games if g['sig'].get(s) is True)})",
                       [g for g in games if g["sig"].get(s) is True]))
    md.append("")

    def count(g):
        return sum(1 for s in SIGNALS if g["sig"].get(s) is True)
    md += ["## By number of signals hit", "", "| signals hit | record | units |", "|---|---|---|"]
    for n in range(7, -1, -1):
        b = [g for g in games if count(g) == n]
        if b:
            md.append(_row(f"{n}/7", b))
    md.append("")

    core = ("margin", "favorite", "line", "consistency", "bvp", "sharp")
    combos = []
    for k in (2, 3):
        for cmb in itertools.combinations(core, k):
            b = [g for g in games if all(g["sig"].get(s) is True for s in cmb)]
            if len(b) >= 10:
                w, _, u = _units(b)
                combos.append((w / len(b), u, " + ".join(cmb), b))
    md += ["## Best signal combos (all present together, n≥10, by win%)", "",
           "| combo | record | units |", "|---|---|---|"]
    for wr, u, name, b in sorted(combos, reverse=True)[:12]:
        md.append(_row(name, b))
    md.append("")

    veg = [g for g in games if "veg_won" in g]
    md += ["## Tailing the side VEGAS needed (book_needs) vs outcome", "",
           "| slice | record | units |", "|---|---|---|",
           _row(f"all games with a book read (n={len(veg)})",
                [{"won": g["veg_won"], "odds": g["veg_odds"]} for g in veg])]
    for basis in ("money %", "ticket %"):
        sub = [{"won": g["veg_won"], "odds": g["veg_odds"]} for g in veg
               if g.get("veg_basis") == basis]
        md.append(_row(f"  ...{basis} (n={len(sub)})", sub))
    md.append(_row("(vs our advantage side, same games)",
                   [{"won": g["won"], "odds": g["odds"]} for g in veg]))
    md.append("")

    ag = [{"won": g["won"], "odds": g["odds"]} for g in games if g["stance_against"]]
    md += ["## Our pick when the book's informed money was AGAINST us (⚠️ bucket)", "",
           "| slice | record | units |", "|---|---|---|",
           _row(f"stance-against plays (n={len(ag)})", ag), ""]

    md.append("_Point-in-time: signals recomputed from the frozen pre-game snapshot; "
              "winners from the MLB Stats API; $1/bet at the frozen moneyline. A "
              "signal with no recorded input on an older board is excluded from that "
              "row only (see n=)._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "signal_backtest.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
