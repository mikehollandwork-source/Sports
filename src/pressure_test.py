"""
Pressure test: does ANY version of this system beat a dumb baseline out-of-sample?

The signal backtest is in-sample - the gate rules (fade-only, core=margin/consistency,
mild-public veto) were DERIVED by looking at that same history, so its +ROI numbers
are curve-fits. This module answers the harder questions:

  1. BASELINES - what do brainless strategies return on the same games? If betting
     every favorite loses -5% and we lose -6%, the system ADDS NOTHING. Without this
     column every other number is meaningless.
  2. HOLDOUT - rules were set through 2026-07-22, so games from 07-23 forward are
     genuinely out-of-sample. Every variant is reported IN-SAMPLE vs HOLDOUT. A rule
     that only works in-sample is a curve-fit, full stop.
  3. ABLATIONS - re-test every gate piece and every feature we retired or trialed
     (line-as-core, underdog discipline, coin flips, pitching dog, mild-public veto,
     star rule, price caps, fade-everything, value sizing) against those baselines.
  4. REVERSAL - the bvp+form promotion went live 07-24, inside the losing streak.
     Isolate its real contribution.

Everything bets $1 at the frozen pre-game price. Runs on GitHub Actions (the MLB API
is firewalled in the dev sandbox). Writes output/pressure_test.md.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

from . import grade, mlb_api
from .main import _book_needs, _public_pairs
from .analysis import PUBLIC_HEAVY
from .signal_backtest import signals, SIGNALS

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# Rules were derived from data through this date; later games are a true holdout.
HOLDOUT_FROM = "2026-07-23"


def _mild_public(g: dict, adv: str, sharp_hit: bool) -> bool:
    """Replicate main's mild-public veto: the public leans on the OTHER side but
    under PUBLIC_HEAVY%. Sharp money on us stands the veto down."""
    maj = (g.get("public_majority") or {}).get("team")
    if not maj or maj == adv or " @ " not in g.get("matchup", ""):
        return False
    pairs = _public_pairs((g.get("public_majority") or {}).get("detail") or {})
    if not pairs:
        return False
    away, home = g["matchup"].split(" @ ")
    ap = sum(p[0] for p in pairs) / len(pairs)
    hp = sum(p[1] for p in pairs) / len(pairs)
    pct = round(hp if maj == home else ap)
    return bool(pct < PUBLIC_HEAVY and not sharp_hit)


def collect() -> list[dict]:
    """One rec per graded game with everything needed to replay any gate."""
    recs: list[dict] = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        day = json.loads(Path(f).read_text())
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        for g in day.get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            sig = signals(g)
            if not sig:
                continue
            pc = g.get("pick_criteria") or {}
            adv, ml = sig["_adv"], sig["_ml"]
            opp_ml = pc.get("opponent_moneyline")
            if " @ " not in g.get("matchup", ""):
                continue
            away, home = g["matchup"].split(" @ ")
            opp = home if adv == away else away
            book = _book_needs(g)
            recs.append({
                "date": date, "sig": sig, "adv": adv, "opp": opp,
                "ml": ml, "opp_ml": opp_ml,
                "won": res["winner"] == adv,                 # our stat side won
                "home_won": res["winner"] == home,
                "is_tail": bool(book and adv == book["bet"]),
                "has_book": bool(book),
                "mild_public": _mild_public(g, adv, sig.get("sharp") is True),
                "reversal": pc.get("reversal"),
                "frozen_play": pc.get("play"),
                "home_ml": (ml if adv == home else opp_ml),
                "away_ml": (ml if adv == away else opp_ml),
            })
    return recs


def _roi(rows: list[dict]) -> tuple[int, int, float, float]:
    """rows: [{won, odds}] -> (w, l, units, roi)."""
    rows = [r for r in rows if r.get("odds") is not None]
    if not rows:
        return 0, 0, 0.0, 0.0
    w = sum(1 for r in rows if r["won"])
    u = sum(grade.american_profit(r["odds"]) if r["won"] else -1 for r in rows)
    return w, len(rows) - w, round(u, 2), u / len(rows)


def _cell(rows: list[dict]) -> str:
    rows = [r for r in rows if r.get("odds") is not None]
    if not rows:
        return "—"
    w, l, u, roi = _roi(rows)
    return f"{w}-{l} · {u:+.1f}u · **{roi:+.1%}** (n={len(rows)})"


def _split_row(label: str, recs: list[dict], bet) -> str:
    """One table row: label | ALL | in-sample | holdout. `bet` maps rec -> {won,odds}|None."""
    def rows(sub):
        out = []
        for r in sub:
            b = bet(r)
            if b and b.get("odds") is not None:
                out.append(b)
        return out
    ins = [r for r in recs if r["date"] < HOLDOUT_FROM]
    hold = [r for r in recs if r["date"] >= HOLDOUT_FROM]
    return f"| {label} | {_cell(rows(recs))} | {_cell(rows(ins))} | {_cell(rows(hold))} |"


# --- bet builders -------------------------------------------------------------
def bet_adv(r):
    return {"won": r["won"], "odds": r["ml"]}


def bet_opp(r):
    return {"won": not r["won"], "odds": r["opp_ml"]}


def bet_fav(r):
    """Bet whichever side is the favorite (more negative price)."""
    h, a = r["home_ml"], r["away_ml"]
    if h is None or a is None:
        return None
    if h <= a:
        return {"won": r["home_won"], "odds": h}
    return {"won": not r["home_won"], "odds": a}


def bet_dog(r):
    h, a = r["home_ml"], r["away_ml"]
    if h is None or a is None:
        return None
    if h > a:
        return {"won": r["home_won"], "odds": h}
    return {"won": not r["home_won"], "odds": a}


def bet_home(r):
    return {"won": r["home_won"], "odds": r["home_ml"]}


def build() -> str:
    recs = collect()
    if not recs:
        return "# Pressure test\n\n_No graded games available._"
    ins = [r for r in recs if r["date"] < HOLDOUT_FROM]
    hold = [r for r in recs if r["date"] >= HOLDOUT_FROM]
    md = [f"# Pressure test — {len(recs)} graded games "
          f"({len(ins)} in-sample, {len(hold)} holdout)", "",
          f"_Rules were derived from data through {HOLDOUT_FROM} (exclusive), so the "
          "**holdout** column is the only honest read. $1/bet at the frozen price. "
          "A strategy is only real if it beats the BASELINES below in the holdout._", ""]

    H = "| strategy | ALL | in-sample | HOLDOUT |\n|---|---|---|---|"

    # 1. BASELINES - the context that makes every other number meaningful.
    md += ["## 1. Baselines (dumb strategies, same games)", "", H,
           _split_row("bet every FAVORITE", recs, bet_fav),
           _split_row("bet every UNDERDOG", recs, bet_dog),
           _split_row("bet every HOME team", recs, bet_home),
           _split_row("bet our STAT SIDE, every game (no gate)", recs, bet_adv), ""]

    # 2. The live gate and its pieces.
    core = lambda r: (r["sig"].get("margin") is True or r["sig"].get("consistency") is True)
    core_line = lambda r: (core(r) or r["sig"].get("line") is True)
    pdog = lambda r: r["sig"].get("pitching_dog") is True

    def gate_live(r):
        q = (core(r) and not r["is_tail"]) if r["has_book"] else core(r)
        return (q or pdog(r)) and (not r["mild_public"] or pdog(r))

    def sub(pred):
        return [r for r in recs if pred(r)]

    md += ["## 2. The LIVE gate (what the board bets today)", "", H,
           _split_row("LIVE GATE (fade + core[margin|consistency] + mild-public veto)",
                      sub(gate_live), bet_adv), ""]

    # 3. Ablations: turn each piece on/off. Does any piece earn its place in the holdout?
    def gate_core_only(r):
        return core(r)

    def gate_with_line(r):
        q = (core_line(r) and not r["is_tail"]) if r["has_book"] else core_line(r)
        return (q or pdog(r)) and (not r["mild_public"] or pdog(r))

    def gate_no_mild(r):
        q = (core(r) and not r["is_tail"]) if r["has_book"] else core(r)
        return q or pdog(r)

    def gate_no_pdog(r):
        q = (core(r) and not r["is_tail"]) if r["has_book"] else core(r)
        return q and not r["mild_public"]

    def gate_fade_only(r):
        return (not r["is_tail"]) if r["has_book"] else True

    def gate_margin_only(r):
        q = (r["sig"].get("margin") is True and not r["is_tail"]) if r["has_book"] \
            else r["sig"].get("margin") is True
        return q and (not r["mild_public"])

    def gate_cons_only(r):
        q = (r["sig"].get("consistency") is True and not r["is_tail"]) if r["has_book"] \
            else r["sig"].get("consistency") is True
        return q and (not r["mild_public"])

    def gate_dogdisc(r):
        """The reverted underdog discipline: a dog needs margin or pitching edge."""
        if not gate_live(r):
            return False
        is_dog = isinstance(r["ml"], int) and r["ml"] > 0
        return (not is_dog) or r["sig"].get("margin") is True or pdog(r)

    md += ["## 3. Ablations — does each gate piece earn its place?", "", H,
           _split_row("core only (NO fade gate)", sub(gate_core_only), bet_adv),
           _split_row("fade gate only (NO core requirement)", sub(gate_fade_only), bet_adv),
           _split_row("live gate, NO mild-public veto", sub(gate_no_mild), bet_adv),
           _split_row("live gate, NO pitching-dog bypass", sub(gate_no_pdog), bet_adv),
           _split_row("core = margin ONLY", sub(gate_margin_only), bet_adv),
           _split_row("core = consistency ONLY", sub(gate_cons_only), bet_adv), ""]

    # 4. Things we removed or trialed - re-tested honestly.
    md += ["## 4. Removed / trialed features, re-tested", "", H,
           _split_row("PUT LINE BACK in core (removed this session)",
                      sub(gate_with_line), bet_adv),
           _split_row("underdog discipline (reverted rule)", sub(gate_dogdisc), bet_adv),
           _split_row("FADE our own picks (bet opponent of live gate)",
                      sub(gate_live), bet_opp),
           _split_row("pitching dogs alone", sub(pdog), bet_adv),
           _split_row("STARRED plays only (margin+fav+line or 4+ proven)",
                      sub(lambda r: gate_live(r) and (
                          (r["sig"].get("margin") and r["sig"].get("favorite")
                           and r["sig"].get("line"))
                          or sum(1 for k in ("margin", "favorite", "line",
                                             "consistency", "bvp")
                                 if r["sig"].get(k) is True) >= 4)), bet_adv), ""]

    # price caps on the live gate
    md += ["### Price caps on the live gate", "", H]
    for cap in (-250, -180, -150, -130):
        md.append(_split_row(f"live gate, lay no worse than {cap}",
                             sub(lambda r, c=cap: gate_live(r)
                                 and isinstance(r["ml"], int) and r["ml"] >= c), bet_adv))
    md.append(_split_row("live gate, PLUS MONEY only",
                         sub(lambda r: gate_live(r) and isinstance(r["ml"], int)
                             and r["ml"] > 0), bet_adv))
    md.append("")

    # 5. Reversal promotion - live since 07-24, inside the losing streak.
    md += ["## 5. Reversal promotion (bvp+form → bet opponent), live since 07-24", "", H,
           _split_row("reversal picks as booked (bet the opponent)",
                      sub(lambda r: bool(r["reversal"])),
                      lambda r: {"won": not r["won"], "odds": (r["reversal"] or {}).get("odds")}),
           _split_row("...the same games if we'd bet our STAT side instead",
                      sub(lambda r: bool(r["reversal"])), bet_adv),
           _split_row("bvp+form profile anywhere (fade opp)",
                      sub(lambda r: r["sig"].get("bvp") is True
                          and r["sig"].get("form") is True), bet_opp), ""]

    # 6. Every signal alone, holdout-checked.
    md += ["## 6. Each signal alone (bet our stat side when it fires)", "", H]
    for s in SIGNALS:
        md.append(_split_row(s, sub(lambda r, k=s: r["sig"].get(k) is True), bet_adv))
    md.append("")

    md.append("_Point-in-time: signals recomputed from each frozen pre-game snapshot; "
              "winners from the MLB Stats API. The HOLDOUT column is the only "
              "out-of-sample evidence - treat in-sample numbers as curve-fits._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "pressure_test.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
