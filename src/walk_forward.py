"""
Does retuning the gates ever pay, or does it only ever look like it does?

THE QUESTION BEHIND THE QUESTION
"Should I change the parameters after a good month?" is really two questions.
The first - does THIS change survive the good month's removal - is answered by
`change_check`. The second is more useful and nobody has asked it yet: across
this whole season, has picking the best-looking configuration from the data so
far EVER beaten simply leaving the rule alone?

That is testable without hindsight. Walk the season forward one day at a time.
On each day, look only at games that finished BEFORE that day, pick whichever
configuration has the best ROI on that history, and bet the day with it. Then
move to the next day. No future data is ever used, and the answer is a single
number: what the retuning habit itself earned, against what standing pat earned.

WHY THIS IS THE HONEST TEST
Every backtest in this repo picks a winner from a grid and then reports the
winner's number. That number is optimistic by construction - the grid search is
part of the strategy, so it belongs inside the measurement. Walk-forward puts it
there. If adaptive tuning beats the frozen rules, retuning is a skill. If it
loses to them - which is the usual result when the grid's cells differ by noise -
then every retune, including the one just shipped, is expected to cost money and
the right policy is to stop changing things.

Also reports how often the adaptive policy CHANGED its mind. A rule that flips
configuration every few days is not discovering a parameter; it is chasing the
last two weeks.

Writes output/walk_forward.md.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from . import grade
from .change_check import collect

log = logging.getLogger("walk_forward")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# the configuration grid the adaptive policy is allowed to choose from
MOVES = [0.0, 0.005, 0.01, 0.015, 0.02]
GRID = [{"both": b, "move": m} for b in (False, True) for m in MOVES]

OLD = {"both": False, "move": 0.01}     # the rule before 2026-09-21
NEW = {"both": True, "move": 0.005}     # the rule now live

MIN_TRAIN = 60          # games of history before the policy is allowed to tune


def _name(cfg: dict) -> str:
    return f"{'BOTH' if cfg['both'] else 'EITHER'} / ≥{cfg['move']:.1%}"


def _passes(r: dict, cfg: dict) -> bool:
    toward_adv = ((r["drift_ok"] and r["size_ok"]) if cfg["both"]
                  else (r["drift_ok"] or r["size_ok"]))
    if not (toward_adv if r["is_adv"] else not toward_adv):
        return False
    return r["toward"] <= -cfg["move"]


def _sel(rows, cfg):
    return [r for r in rows if _passes(r, cfg)]


def _units(rs) -> float:
    return sum(grade.american_profit(r["odds"]) if r["won"] else -1 for r in rs)


def _line(rs) -> str:
    if not rs:
        return "— (n=0)"
    w, u = sum(1 for r in rs if r["won"]), _units(rs)
    return f"{w}-{len(rs)-w} · {u:+.2f}u · **{u/len(rs):+.1%}** (n={len(rs)})"


def build() -> str:
    rows = sorted(collect(), key=lambda r: r["date"])
    md = ["# Does retuning the gates ever pay?", "",
          "_Walk the season forward one day at a time. On each day pick the "
          "configuration with the best ROI on games that finished BEFORE that "
          "day, and bet the day with it. No future data is used anywhere. The "
          "grid search is part of the strategy, so it is measured as part of "
          "the strategy._", "",
          f"- games reaching the book gate: **{len(rows)}**",
          f"- configurations available: **{len(GRID)}** "
          f"(EITHER/BOTH × line move {MOVES[0]:.1%}–{MOVES[-1]:.1%})",
          f"- history required before tuning is allowed: **{MIN_TRAIN}** games", ""]
    if len(rows) < MIN_TRAIN * 2:
        return "\n".join(md + ["Not enough settled games to walk forward.", ""])

    by_date = defaultdict(list)
    for r in rows:
        by_date[r["date"]].append(r)
    dates = sorted(by_date)

    # --- the walk -----------------------------------------------------------
    hist: list[dict] = []
    picked: list[dict] = []          # bets the adaptive policy actually made
    choices: list[tuple[str, str]] = []
    for d in dates:
        if len(hist) >= MIN_TRAIN:
            best, best_roi = None, None
            for cfg in GRID:
                s = _sel(hist, cfg)
                if len(s) < 10:
                    continue
                roi = _units(s) / len(s)
                if best_roi is None or roi > best_roi:
                    best, best_roi = cfg, roi
            if best is not None:
                choices.append((d, _name(best)))
                picked += _sel(by_date[d], best)
        hist += by_date[d]

    live = [r for r in rows if r["date"] >= dates[0]]
    start = choices[0][0] if choices else dates[0]
    # the frozen rules are scored over the SAME days the adaptive policy bet,
    # or the comparison is between different seasons
    same = [r for r in live if r["date"] >= start]

    md += ["## The whole season, over the days the adaptive policy was live", "",
           f"_from **{start}** onward_", "",
           "| policy | record |", "|---|---|",
           f"| **adaptive** (retune daily on all prior games) | {_line(picked)} |",
           f"| frozen old rule ({_name(OLD)}) | {_line(_sel(same, OLD))} |",
           f"| frozen new rule ({_name(NEW)}) | {_line(_sel(same, NEW))} |", ""]

    a_roi = _units(picked) / len(picked) if picked else 0.0
    o_roi = (_units(_sel(same, OLD)) / len(_sel(same, OLD))
             if _sel(same, OLD) else 0.0)
    n_roi = (_units(_sel(same, NEW)) / len(_sel(same, NEW))
             if _sel(same, NEW) else 0.0)
    better = a_roi > max(o_roi, n_roi)
    md += [("**Retuning beat standing pat.** On this data the habit of picking "
            f"the best-so-far configuration earned {(a_roi-max(o_roi,n_roi))*100:+.1f} "
            "points over the better frozen rule. That is weak evidence that the "
            "grid's cells differ by something real - weak because it is one "
            "season and one walk.")
           if better else
           ("**Retuning lost to standing pat.** Picking the best-so-far "
            f"configuration earned {(a_roi-max(o_roi,n_roi))*100:+.1f} points "
            "against the better frozen rule, which is what happens when the "
            "grid's cells differ by noise: you chase whichever cell got lucky "
            "and it reverts. This is the measurement that applies to the change "
            "just shipped, because that change was produced by exactly this "
            "procedure."), ""]

    # --- how stable was the choice? ----------------------------------------
    flips = sum(1 for i in range(1, len(choices)) if choices[i][1] != choices[i-1][1])
    tally: dict = defaultdict(int)
    for _, nm in choices:
        tally[nm] += 1
    md += ["## How often did it change its mind?", "",
           f"- days tuned: **{len(choices)}** · configuration changed on "
           f"**{flips}** of them ({flips/max(len(choices)-1,1):.0%})", "",
           "| configuration | days it was the best-so-far |", "|---|---|"]
    for nm, c in sorted(tally.items(), key=lambda kv: -kv[1]):
        md.append(f"| {nm} | {c} |")
    md += ["", "_A parameter that is real stays selected. One that flips every "
           "few days is the last two weeks talking._", ""]

    # --- what the grid looks like in hindsight, for contrast ---------------
    md += ["## The same grid scored with hindsight (for contrast only)", "",
           "_Every cell over all games. This is the view that produced the "
           "change, and the spread here is the size of the temptation._", "",
           "| configuration | record |", "|---|---|"]
    ranked = sorted(GRID, key=lambda c: -( _units(_sel(rows, c)) / len(_sel(rows, c))
                                           if _sel(rows, c) else -9))
    for cfg in ranked:
        s = _sel(rows, cfg)
        mark = ""
        if cfg == OLD:
            mark = " ← old"
        if cfg == NEW:
            mark = " ← **live now**"
        md.append(f"| {_name(cfg)}{mark} | {_line(s)} |")
    md += ["", "_The best cell in hindsight is not a forecast. The walk-forward "
           "number above is the one that includes the cost of having chosen "
           "it._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "walk_forward.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
