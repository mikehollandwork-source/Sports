"""
What separates the winning props from the losing ones?

READ-ONLY. Changes no pick, writes no ledger entry.

WHAT CAN AND CANNOT BE TESTED
Historical prop entries stored only `hit_rate` (in wins), `wins_played`, `avg_pa`
and, for 93 of 142, the real `odds`. The richer fields the selector now uses -
all_rate, form, BvP, platoon, fit - were added days ago and exist on 7 props, so
they CANNOT be tested here. Anything claiming otherwise would be reading three
games as evidence.

What IS on every board is the game context, so that is what this tests: park,
temperature, wind, the opposing starter's K/9, the umpire's strikeout lean,
home/away, whether the game was a play, and the price.

THE CORRECTION IS THE POINT
Twelve features at a median split is twelve chances to find a difference, and at
142 games noise alone produces a convincing-looking one. Every feature is scored
against a MAX-STATISTIC permutation null: outcomes are shuffled and the BEST
difference across all twelve is recorded, so the real best is judged against the
best of twelve on noise rather than against a single-comparison p-value. This is
the test that has killed every other candidate in this project, and it is applied
before any of this is believed.

Writes output/prop_audit.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
from pathlib import Path

log = logging.getLogger("prop_audit")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 10000
MIN_SIDE = 20          # a split smaller than this says nothing either way


def collect() -> list[dict]:
    """Each graded prop single, joined to its board game's features."""
    try:
        led = json.loads((OUTPUT_DIR / "prop_ledger.json").read_text())
        entries = led["singles"]["entries"]
    except (OSError, ValueError, KeyError):
        return []
    boards: dict = {}
    for f in glob.glob(str(OUTPUT_DIR / "picks_2026-*.json")):
        date = Path(f).stem.split("picks_")[1]
        try:
            boards[date] = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
    rows = []
    for e in entries:
        date, pk = e["key"].split("#")
        board = boards.get(date)
        if not board:
            continue
        g = next((x for x in board.get("games", [])
                  if str(x.get("game_pk")) == pk), None)
        if not g:
            continue
        pc = g.get("pick_criteria") or {}
        prop = pc.get("prop") or {}
        w = g.get("weather") or {}
        sa = g.get("statistical_advantage") or {}
        tend = g.get("ump_tend") or {}
        away, home = (g.get("matchup") or " @ ").split(" @ ")
        adv = pc.get("advantage_team")
        is_home = adv == home
        opp_side = "away" if is_home else "home"
        rows.append({
            "date": date, "won": e["result"] == "W",
            "profit": e.get("profit", 0.0), "odds": e.get("odds"),
            "real_line": bool(e.get("real_line")),
            # prop features that actually exist historically
            "hit_rate": prop.get("hit_rate"),
            "wins_played": prop.get("wins_played"),
            "avg_pa": prop.get("avg_pa"),
            # game context, on every board
            "park": g.get("park_factor"),
            "temp": w.get("temp_f"),
            "wind": w.get("wind_mph"),
            "opp_k9": (sa.get(opp_side) or {}).get("starter_k9"),
            "ump_k": tend.get("k_extra"),
            "home": 1 if is_home else 0,
            "was_pick": 1 if pc.get("play") == "pick" else 0,
            "adv_ml": pc.get("advantage_moneyline"),
        })
    return rows


FEATURES = ["hit_rate", "wins_played", "avg_pa", "odds", "park", "temp",
            "wind", "opp_k9", "ump_k", "home", "was_pick", "adv_ml"]


def _split(rows: list[dict], key: str):
    """(low side, high side, cut) at the feature's median."""
    vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
    if len(vals) < 2 * MIN_SIDE:
        return None, None, None
    cut = st.median(vals)
    lo = [r for r in rows if isinstance(r.get(key), (int, float)) and r[key] <= cut]
    hi = [r for r in rows if isinstance(r.get(key), (int, float)) and r[key] > cut]
    if len(lo) < MIN_SIDE or len(hi) < MIN_SIDE:
        return None, None, None
    return lo, hi, cut


def _rate(rs):
    return sum(1 for r in rs if r["won"]) / len(rs) if rs else 0.0


def _roi(rs):
    return sum(r["profit"] for r in rs) / len(rs) if rs else 0.0


def _stat(rows, key, wins) -> float | None:
    """|hit-rate difference| across the split, using the supplied win vector."""
    lo, hi, _ = _split(rows, key)
    if lo is None:
        return None
    idx = {id(r): i for i, r in enumerate(rows)}
    lr = sum(wins[idx[id(r)]] for r in lo) / len(lo)
    hr = sum(wins[idx[id(r)]] for r in hi) / len(hi)
    return abs(hr - lr)


def build() -> str:
    rows = collect()
    md = ["# Props — what separates the winners from the losers", "",
          "_Read-only. Every feature is corrected together by a max-statistic "
          "permutation, so the best of twelve is judged against the best of "
          "twelve on noise._", ""]
    if len(rows) < 60:
        return "\n".join(md + [f"Only {len(rows)} graded props joined to a "
                               "board; too few.", ""])
    w = sum(1 for r in rows if r["won"])
    md += [f"- graded props joined to their board: **{len(rows)}**",
           f"- overall: **{w}-{len(rows)-w}** = {_rate(rows):.1%} · "
           f"{sum(r['profit'] for r in rows):+.2f}u · ROI {_roi(rows):+.1%}", "",
           "_Fields the CURRENT selector uses - all_rate, form, BvP, platoon, fit "
           "- were added days ago and exist on 7 props. They are NOT tested here; "
           "three games is not evidence._", "",
           "## Every feature, split at its median", "",
           "| feature | cut | low side | high side | hit-rate gap | ROI gap |",
           "|---|---|---|---|---|---|"]
    obs: dict = {}
    for key in FEATURES:
        lo, hi, cut = _split(rows, key)
        if lo is None:
            md.append(f"| {key} | — | _too lopsided to split_ | | | |")
            continue
        gap = _rate(hi) - _rate(lo)
        rgap = _roi(hi) - _roi(lo)
        obs[key] = abs(gap)
        md.append(f"| `{key}` | {cut:g} | {_rate(lo):.1%} ({len(lo)}) "
                  f"| {_rate(hi):.1%} ({len(hi)}) | **{gap:+.1%}** "
                  f"| {rgap:+.1%} |")
    md.append("")
    if not obs:
        return "\n".join(md + ["No feature splits cleanly.", ""])

    best_key = max(obs, key=obs.get)
    best = obs[best_key]
    wins = [1 if r["won"] else 0 for r in rows]
    rng = random.Random(31337)
    null = []
    for _ in range(TRIALS):
        sh = wins[:]
        rng.shuffle(sh)
        vals = [v for v in (_stat(rows, k, sh) for k in obs) if v is not None]
        if vals:
            null.append(max(vals))
    null.sort()
    p = sum(1 for x in null if x >= best) / len(null)
    md += ["## Corrected for looking twelve times", "",
           f"- biggest gap found: **`{best_key}` at {best:.1%}**",
           f"- shuffling outcomes, the BEST of twelve gaps is typically "
           f"**{st.median(null):.1%}**, and clears {best:.1%} "
           f"**{p:.1%}** of the time",
           f"- **corrected p = {p:.4f}**", "",
           ("- **nothing here is distinguishable from noise.** At 142 props, "
            "twelve looks produce a gap this size routinely."
            if p > 0.05 else
            "- this survives the correction and is worth a second look on new "
            "games before it is acted on"), ""]

    md += ["## Price, which is arithmetic rather than a discovery", "",
           "_Break-even rises with the price, so this needs no significance "
           "test - it is what the numbers mean._", "",
           "| price band | n | hit rate | needs | ROI |", "|---|---|---|---|---|"]
    bands = [(-1000, -250, "−250 or worse"), (-249, -200, "−249 to −200"),
             (-199, -150, "−199 to −150"), (-149, 1000, "−149 or better")]
    for lo_o, hi_o, label in bands:
        sub = [r for r in rows
               if isinstance(r.get("odds"), int) and lo_o <= r["odds"] <= hi_o]
        if not sub:
            md.append(f"| {label} | 0 | — | — | — |")
            continue
        med = st.median([r["odds"] for r in sub])
        need = abs(med) / (abs(med) + 100) if med < 0 else 100 / (med + 100)
        md.append(f"| {label} | {len(sub)} | {_rate(sub):.1%} | {need:.1%} "
                  f"| **{_roi(sub):+.1%}** |")
    return "\n".join(md + [""])


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "prop_audit.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
