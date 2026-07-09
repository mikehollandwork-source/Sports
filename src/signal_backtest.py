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
        "_ml": ml, "_adv": adv, "_margin": margin, "_cons": cons,
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
                # the ANTI-Vegas side = the team the book is EXPOSED to (opposite of
                # book_needs) and its frozen price; whether our stat side agrees.
                away, home = g["matchup"].split(" @ ")
                pc = g.get("pick_criteria") or {}
                mls = {adv: pc.get("advantage_moneyline"),
                       (home if adv == away else away): pc.get("opponent_moneyline")}
                anti = home if bn["bet"] == away else away
                rec.update(anti_team=anti, anti_won=res["winner"] == anti,
                           anti_odds=mls.get(anti), anti_is_adv=(anti == adv))
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

    # TAIL Vegas: bet the side the book NEEDS, then pour in one of our signals. A
    # signal counts only when our stat side IS the Vegas-needed team (not anti_is_adv)
    # - our signals are computed for the advantage side, so they can only "confirm"
    # the tail when the advantage side and the book_needs side are the same team.
    tail_ok = [g for g in veg if g.get("veg_odds") is not None]
    md += ["## Tailing Vegas (bet the side book_needs) + one of our signals", "",
           "| slice | record | units |", "|---|---|---|",
           _row(f"tail Vegas, all games (n={len(tail_ok)})",
                [{"won": g["veg_won"], "odds": g["veg_odds"]} for g in tail_ok])]
    tagree = [g for g in tail_ok if not g["anti_is_adv"]]   # book_needs side == our adv
    md.append(_row(f"  + our stat side agrees (n={len(tagree)})",
                   [{"won": g["veg_won"], "odds": g["veg_odds"]} for g in tagree]))
    for s in SIGNALS:
        sub = [g for g in tagree if g["sig"].get(s) is True]
        md.append(_row(f"  + agrees & {s} (n={len(sub)})",
                       [{"won": g["veg_won"], "odds": g["veg_odds"]} for g in sub]))
    md.append("")

    def ncore_t(g):
        return sum(1 for s in core if g["sig"].get(s) is True)
    md += ["## Tail Vegas (stat side agrees) by NUMBER of signals stacked", "",
           "| signals stacked | record | units | ROI/bet |", "|---|---|---|---|"]
    for lo, lab in ((1, "≥1"), (2, "≥2"), (3, "≥3"), (4, "≥4")):
        sub = [g for g in tagree if ncore_t(g) >= lo]
        rows = [{"won": g["veg_won"], "odds": g["veg_odds"]} for g in sub]
        if rows:
            w, l, u = _units(rows)
            md.append(f"| {lab} signals (n={len(rows)}) | {w}-{l} ({w/len(rows):.0%}) "
                      f"| {u:+.2f}u | {u/len(rows):+.1%} |")
    md.append("")

    # FADE Vegas: bet the OPPOSITE side of what the book needs (the team it's
    # exposed to), then pour in one of our signals. A signal only counts when our
    # stat side IS that anti-Vegas team (anti_is_adv) - otherwise our signal points
    # the other way and can't "confirm" the fade.
    anti = [g for g in veg if g.get("anti_odds") is not None]
    md += ["## Fading Vegas (bet the OPPOSITE of book_needs) + one of our signals", "",
           "| slice | record | units |", "|---|---|---|",
           _row(f"fade Vegas, all games (n={len(anti)})",
                [{"won": g["anti_won"], "odds": g["anti_odds"]} for g in anti])]
    agree = [g for g in anti if g["anti_is_adv"]]
    md.append(_row(f"  + our stat side agrees (n={len(agree)})",
                   [{"won": g["anti_won"], "odds": g["anti_odds"]} for g in agree]))
    for s in SIGNALS:
        sub = [g for g in agree if g["sig"].get(s) is True]
        md.append(_row(f"  + agrees & {s} (n={len(sub)})",
                       [{"won": g["anti_won"], "odds": g["anti_odds"]} for g in sub]))
    md.append("")

    # Does STACKING more than one signal on the fade raise ROI? Count buckets over
    # the six core signals, then the best 2- and 3-signal combos on the fade.
    def ncore(g):
        return sum(1 for s in core if g["sig"].get(s) is True)
    md += ["## Fade Vegas (stat side agrees) by NUMBER of signals stacked", "",
           "| signals stacked | record | units | ROI/bet |", "|---|---|---|---|"]
    for lo, lab in ((1, "≥1"), (2, "≥2"), (3, "≥3"), (4, "≥4")):
        sub = [g for g in agree if ncore(g) >= lo]
        rows = [{"won": g["anti_won"], "odds": g["anti_odds"]} for g in sub]
        if rows:
            w, l, u = _units(rows)
            roi = u / len(rows)
            md.append(f"| {lab} signals (n={len(rows)}) | {w}-{l} ({w/len(rows):.0%}) "
                      f"| {u:+.2f}u | {roi:+.1%} |")
    md.append("")
    md += ["## Best MULTI-signal fade combos (stat side agrees, n≥10)", "",
           "| combo | record | units |", "|---|---|---|"]
    fcombos = []
    for k in (2, 3):
        for cmb in itertools.combinations(core, k):
            sub = [g for g in agree if all(g["sig"].get(s) is True for s in cmb)]
            if len(sub) >= 10:
                rows = [{"won": g["anti_won"], "odds": g["anti_odds"]} for g in sub]
                w, _, u = _units(rows)
                fcombos.append((u / len(rows), u, " + ".join(cmb), rows))
    for roi, u, name, rows in sorted(fcombos, reverse=True)[:10]:
        md.append(_row(name, rows))
    md.append("")

    ag = [{"won": g["won"], "odds": g["odds"]} for g in games if g["stance_against"]]
    md += ["## Our pick when the book's informed money was AGAINST us (⚠️ bucket)", "",
           "| slice | record | units |", "|---|---|---|",
           _row(f"stance-against plays (n={len(ag)})", ag), ""]

    # NEW BOARD GATE (live rule): a pick must be a FADE (our stat side is the team
    # Vegas does NOT need) carrying a CORE signal (margin/line/consistency). This is
    # what actually makes the board now - validate it's +EV and see what it drops.
    def is_core(g):
        return any(g["sig"].get(s) is True for s in ("margin", "line", "consistency"))
    gate = [g for g in agree if is_core(g)]                     # fade + core
    dropped_tail = [g for g in veg if not g["anti_is_adv"] and is_core(g)]  # tail + core (now cut)
    md += ["## NEW BOARD GATE — fade + core signal (what makes the board now)", "",
           "| slice | record | units |", "|---|---|---|",
           _row(f"BOARD: fade + core signal (n={len(gate)})",
                [{"won": g["anti_won"], "odds": g["anti_odds"]} for g in gate]),
           _row(f"DROPPED: tail + core signal (was played, now cut) (n={len(dropped_tail)})",
                [{"won": g["veg_won"], "odds": g["veg_odds"]} for g in dropped_tail]), ""]

    # #5 - do tighter numeric thresholds sharpen a signal? Sweep the margin and
    # consistency cutoffs on the fade side (bet the anti-Vegas team).
    md += ["## Threshold sweeps on the fade side (does a tighter bar help?)", "",
           "| margin ≥ | record | units |", "|---|---|---|"]
    for thr in (0.30, 0.40, 0.50, 0.60, 0.70):
        sub = [g for g in agree if (g["sig"].get("_margin") or -9) >= thr]
        md.append(_row(f"{thr:.2f}", [{"won": g["anti_won"], "odds": g["anti_odds"]} for g in sub]))
    md += ["", "| consistency (out-hit) ≥ | record | units |", "|---|---|---|"]
    for thr in (3, 4, 5):
        sub = [g for g in agree if (g["sig"].get("_cons") or -9) >= thr]
        md.append(_row(f"{thr}/5", [{"won": g["anti_won"], "odds": g["anti_odds"]} for g in sub]))
    md.append("")

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
