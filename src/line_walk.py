"""
Walk-forward on the line-movement threshold - the only gate that earns its keep.

WHY THIS IS THE ONE WORTH TESTING
`gate_sweep` stood every gate alone on the whole pool. Two of three did nothing:
handle=tickets was worth -3.6 points and book-confirm +1.3. The line gate was
worth +5.8 at the live 1.0% bar and +10.1 at "moved against at all", and those
are nested subsets, so the band between them is exact arithmetic: the 185 games
that moved 0-1% against went 116-69, +10.3%, better than the 316 that moved 1%
or more. Direction carries the information; the magnitude filter discards games.

WHY NOT JUST LOWER THE THRESHOLD
Because that is how this session produced a +10.5% signal that was reading
finished games. Picking the best of four thresholds on all the data and then
quoting its return is the same error in a smaller coat. A threshold chosen on
the data it is scored against is not a finding.

THE METHOD
Rolling walk-forward. Fit on everything up to a cut date, pick the threshold
with the best ROI in that window only, apply it to the NEXT block, record what
it actually returned, roll the window forward, repeat. The reported number is
the sum of those out-of-sample blocks - a return the chooser never saw.

Reported against three baselines, because a walk-forward number alone is
unreadable:

    every fixed threshold, scored out-of-sample over the same blocks
    the live 1.0% bar, which is what we run today
    backing the majority side with no line gate at all

If the walk-forward beats the live bar out of sample, the threshold is worth
changing. If a FIXED lower bar beats the walk-forward, the honest answer is to
set it once and not adapt, because adapting cost more than it earned.

Writes output/line_walk.md.
"""

from __future__ import annotations

import glob
import json
import logging
import statistics as st
from pathlib import Path

from . import grade, mlb_api

log = logging.getLogger("line_walk")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
THRESHOLDS = [0.0, 0.0025, 0.005, 0.01, 0.02]
BLOCK = 10          # board days per out-of-sample block
MIN_TRAIN = 25      # board days before the first decision


def collect() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
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
            shift = (pc.get("line_check") or {}).get("implied_shift")
            if not isinstance(odds, int) or not isinstance(shift, (int, float)):
                continue
            toward = shift if maj == adv else -shift
            rows.append({"date": date, "odds": odds, "won": res["winner"] == maj,
                         "against": -toward,
                         "money_ok": chk.get("money") == "with public"})
    return rows


def _roi(rs) -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r["odds"]) if r["won"] else -1
               for r in rs) / len(rs)


def _sel(rs, thr):
    return [r for r in rs if r["against"] >= thr and (thr > 0 or r["against"] > 0)]


def _fmt(rs) -> str:
    if not rs:
        return "— (0)"
    w = sum(1 for r in rs if r["won"])
    return f"{w}-{len(rs)-w} · **{_roi(rs):+.1%}** (n={len(rs)})"


def build() -> str:
    rows = collect()
    md = ["# Walk-forward on the line-movement threshold", "",
          "_The only gate that earns its keep. `gate_sweep` had handle=tickets at "
          "−3.6 points and book-confirm at +1.3; the line gate was +5.8 at the "
          "live 1.0% bar and +10.1 at \"moved against at all\". Those are nested, "
          "so the band between is exact: the 185 games moving 0–1% against went "
          "116-69, +10.3% — better than the 316 moving 1%+._", "",
          "_Which is exactly why it cannot just be lowered. Choosing the best of "
          "four thresholds on all the data and quoting its return is how this "
          "session produced a +10.5% signal that was reading finished games. So "
          "the threshold is chosen on past days only and scored on days the "
          "chooser never saw._", "",
          f"- graded games with a majority side and a line reading: **{len(rows)}**", ""]
    if len(rows) < 300:
        return "\n".join(md + ["Not enough games.", ""])

    for label, pool in (("every game with a majority side", rows),
                        ("games that also pass handle=tickets",
                         [r for r in rows if r["money_ok"]])):
        days = sorted({r["date"] for r in pool})
        if len(days) < MIN_TRAIN + BLOCK:
            continue
        md += [f"## {label}", "",
               "### Fixed thresholds, whole sample (what NOT to choose from)", "",
               "| threshold | record |", "|---|---|"]
        for t in THRESHOLDS:
            md.append(f"| {'moved against at all' if t == 0 else f'≥{t:.2%}'} | "
                      f"{_fmt(_sel(pool, t))} |")
        md.append("")

        # rolling walk-forward
        picked, oos, blocks = [], [], []
        i = MIN_TRAIN
        while i < len(days):
            train_days = set(days[:i])
            test_days = set(days[i:i + BLOCK])
            train = [r for r in pool if r["date"] in train_days]
            test = [r for r in pool if r["date"] in test_days]
            best = max(THRESHOLDS, key=lambda t: _roi(_sel(train, t)))
            chosen = _sel(test, best)
            picked.append(best)
            oos += chosen
            if chosen:
                blocks.append((days[i], best, _roi(chosen), len(chosen)))
            i += BLOCK

        md += ["### Rolling walk-forward", "",
               f"- retrained every **{BLOCK}** board days after a "
               f"**{MIN_TRAIN}**-day burn-in · **{len(blocks)}** scored blocks",
               "- thresholds it chose: " + ", ".join(
                   f"{'any' if t == 0 else f'{t:.2%}'}×{picked.count(t)}"
                   for t in THRESHOLDS if picked.count(t)),
               f"- **out-of-sample: {_fmt(oos)}**", ""]

        # the same blocks, each fixed threshold, so the comparison is fair
        md += ["### The same out-of-sample days, each threshold held fixed", "",
               "_The walk-forward is only worth its complexity if it beats every "
               "fixed bar over the identical days._", "",
               "| threshold | over those blocks |", "|---|---|"]
        scored = set()
        i = MIN_TRAIN
        while i < len(days):
            scored |= set(days[i:i + BLOCK])
            i += BLOCK
        oos_pool = [r for r in pool if r["date"] in scored]
        for t in THRESHOLDS:
            md.append(f"| {'moved against at all' if t == 0 else f'≥{t:.2%}'} | "
                      f"{_fmt(_sel(oos_pool, t))} |")
        md.append(f"| _no line gate at all_ | {_fmt(oos_pool)} |")
        md.append("")

        live = _roi(_sel(oos_pool, 0.01))
        wf = _roi(oos)
        best_fixed = max(THRESHOLDS, key=lambda t: _roi(_sel(oos_pool, t)))
        md += [f"- walk-forward **{wf:+.1%}** against the live 1.0% bar "
               f"**{live:+.1%}** over the same days → "
               + ("**the adaptive threshold earns its keep**" if wf > live
                  else "**adapting did not pay** — it chose worse than the "
                       "bar we already run"),
               f"- best fixed bar out of sample was "
               f"**{'any adverse move' if best_fixed == 0 else f'{best_fixed:.2%}'}** "
               f"at {_roi(_sel(oos_pool, best_fixed)):+.1%} → "
               + ("**set it once, do not adapt** — a fixed bar beat the "
                  "walk-forward, so the adaptation was noise-chasing"
                  if _roi(_sel(oos_pool, best_fixed)) > wf else
                  "the walk-forward held up against every fixed bar"), ""]
        if blocks:
            md += ["### Block by block", "",
                   "| block starts | threshold chosen | ROI | n |", "|---|---|---|---|"]
            for d, t, r, n in blocks:
                md.append(f"| {d} | {'any' if t == 0 else f'{t:.2%}'} | "
                          f"{r:+.1%} | {n} |")
            md += ["",
                   f"- blocks profitable: **{sum(1 for b in blocks if b[2] > 0)}"
                   f"/{len(blocks)}** · median block "
                   f"**{st.median([b[2] for b in blocks]):+.1%}**", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "line_walk.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
