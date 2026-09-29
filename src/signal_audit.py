"""
Signal audit: every signal and every stat tested INDIVIDUALLY against the game
outcome - both as a bet and as a fade.

Two things the existing backtests never did cleanly:
  * test each input on ALL games (not just the ones that made the board), so a
    signal's real hit rate isn't confounded by the gate that selected around it
  * report the FADE of each one next to it, since a reliably losing input is a
    winning input backwards (the vig is paid either way, so a fade only profits
    if the straight side loses by MORE than the juice)

Continuous stats are bucketed into terciles and read for MONOTONICITY: a stat
that matters should show win rate climbing from the low to the high bucket. A
stat whose middle bucket is best is noise.

Every row carries a HOLDOUT column (rules were derived through 2026-07-23), and
many inputs are scanned, so treat isolated green cells as hypotheses.
Writes output/signal_audit.md.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

from . import grade, mlb_api
from .signal_backtest import signals, profile, SIGNALS

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
HOLDOUT_FROM = "2026-07-23"

STATS = [("margin", "edge margin"), ("team_score_gap", "team-score gap"),
         ("offense_index_gap", "offense-index gap"),
         ("pitching_index_gap", "pitching-index gap"),
         ("fip_gap", "FIP gap (opp−ours)"), ("woba_neutral_gap", "wOBA gap"),
         ("iso_neutral_gap", "ISO gap"), ("k_pct_gap", "K% gap"),
         ("bvp_gap", "BvP gap"), ("form_gap", "form gap")]


def collect() -> list[dict]:
    recs = []
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
            if not sig or sig.get("_ml") is None:
                continue
            pc = g.get("pick_criteria") or {}
            prof = profile(g) or {}
            prof["margin"] = sig.get("_margin")
            recs.append({"date": date, "won": res["winner"] == sig["_adv"],
                         "ml": sig["_ml"], "opp_ml": pc.get("opponent_moneyline"),
                         "sig": sig, "prof": prof,
                         "holdout": date >= HOLDOUT_FROM})
    return recs


def _roi(rows, side="adv"):
    """rows -> (w,l,units,roi) betting the advantage side or its opponent."""
    out = []
    for r in rows:
        ml = r["ml"] if side == "adv" else r["opp_ml"]
        if ml is None:
            continue
        won = r["won"] if side == "adv" else (not r["won"])
        out.append((won, ml))
    if not out:
        return None
    w = sum(1 for won, _ in out if won)
    u = sum(grade.american_profit(ml) if won else -1 for won, ml in out)
    return w, len(out) - w, round(u, 2), u / len(out)


def _cell(rows, side="adv"):
    r = _roi(rows, side)
    if not r:
        return "—"
    w, l, u, roi = r
    return f"{w}-{l} ({w/(w+l):.0%}) · **{roi:+.1%}** (n={w+l})"


def build() -> str:
    recs = collect()
    if not recs:
        return "# Signal audit\n\n_No graded games._"
    hold = [r for r in recs if r["holdout"]]
    md = [f"# Signal audit — {len(recs)} games ({len(hold)} holdout)", "",
          "_Each input tested alone on EVERY graded game. 'bet' = back the "
          "advantage side when the input fires; 'fade' = back its opponent. "
          "A fade only profits if the straight side loses by more than the vig._", ""]

    # --- boolean signals: bet vs fade, all + holdout
    md += ["## 1. Each signal alone — bet it, and fade it", "",
           "| signal | BET (all) | BET (holdout) | FADE (all) | FADE (holdout) |",
           "|---|---|---|---|---|"]
    for s in SIGNALS:
        sub = [r for r in recs if r["sig"].get(s) is True]
        sh = [r for r in sub if r["holdout"]]
        md.append(f"| {s} | {_cell(sub)} | {_cell(sh)} | {_cell(sub,'opp')} | "
                  f"{_cell(sh,'opp')} |")
    md.append("")

    # signal ABSENT (the negative case) - sometimes the absence is the signal
    md += ["## 2. Each signal when it does NOT fire", "",
           "| signal absent | BET (all) | BET (holdout) |", "|---|---|---|"]
    for s in SIGNALS:
        sub = [r for r in recs if r["sig"].get(s) is False]
        sh = [r for r in sub if r["holdout"]]
        md.append(f"| {s} = False | {_cell(sub)} | {_cell(sh)} |")
    md.append("")

    # --- continuous stats: terciles, read for monotonicity
    md += ["## 3. Each stat by tercile (bet the advantage side)", "",
           "_Stats are signed so positive = our edge. A real stat climbs low→high. "
           "If the MIDDLE bucket is best, it's noise._", "",
           "| stat | low third | mid third | high third | high−low |",
           "|---|---|---|---|---|"]
    for key, lab in STATS:
        vals = sorted(r["prof"][key] for r in recs
                      if isinstance(r["prof"].get(key), (int, float)))
        if len(vals) < 30:
            md.append(f"| {lab} | — | — | — | — |")
            continue
        q1, q2 = vals[len(vals) // 3], vals[2 * len(vals) // 3]
        def band(lo, hi):
            return [r for r in recs
                    if isinstance(r["prof"].get(key), (int, float))
                    and (lo is None or r["prof"][key] >= lo)
                    and (hi is None or r["prof"][key] < hi)]
        lo_b, mid_b, hi_b = band(None, q1), band(q1, q2), band(q2, None)
        def wr(rows):
            return (sum(1 for r in rows if r["won"]) / len(rows)) if rows else None
        wl, wh = wr(lo_b), wr(hi_b)
        delta = f"{(wh-wl)*100:+.1f} pts" if (wl is not None and wh is not None) else "—"
        md.append(f"| {lab} | {_cell(lo_b)} | {_cell(mid_b)} | {_cell(hi_b)} | "
                  f"**{delta}** |")
    md.append("")

    md.append("_Multiple inputs are scanned; a single green cell is a hypothesis, "
              "not a rule. The holdout column is the only out-of-sample evidence._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "signal_audit.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
