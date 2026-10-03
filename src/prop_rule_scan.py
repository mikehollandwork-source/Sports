"""
Is there ANY mechanical prop rule, on the teams the board picks, that profits?

READ-ONLY. Changes no pick, writes no ledger entry.

WHAT IS SEARCHABLE, AND WHAT IS NOT
The cached odds only ever held `batter_hits` 0.5, so every rule here is in the
1+ HIT market. Total bases and hits+runs+RBIs cannot be tested retroactively at
all - those prices were never captured. The richer per-hitter fields the selector
now uses (all_rate, form, BvP, platoon, fit) exist on 7 props, so they are not
searchable either.

What IS available for every quoted hitter on a picked team: his real over price,
his batting-order slot, and whether he got a hit. So the space searched is
mechanical price-and-slot rules, which is narrow but real.

THE CORRECTION IS THE WHOLE POINT
Thirteen rules scanned over the same games is thirteen chances to find a winner,
and at these sample sizes the best of thirteen on pure noise is comfortably
positive. Every rule is scored against a MAX-STATISTIC permutation: outcomes are
shuffled and the BEST ROI across all thirteen is recorded, so the real best is
judged against the best of thirteen on noise. A rule that cannot clear that has
not been found, it has been dredged.

UNDER-BASED RULES
The under price was only captured from 2026-10-03, so under rules cannot be
priced historically. Rather than invent a price, they report the no-hit rate and
the price that rate WOULD need, which is a fact rather than an assumption.

Writes output/prop_rule_scan.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
from pathlib import Path

import requests

from . import apitime, grade

log = logging.getLogger("prop_rule_scan")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 5000
TIMEOUT = 20
MIN_BETS = 25


def _box(game_pk: int) -> dict:
    """{name lower: {"hits", "order", "side"}} for batters with a PA."""
    out: dict = {}
    try:
        with apitime.timed("mlb", f"box/{game_pk}"):
            box = requests.get(
                f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore",
                timeout=TIMEOUT).json()
    except Exception as exc:
        log.warning("boxscore %s failed: %s", game_pk, exc)
        return out
    for side in ("home", "away"):
        team = ((box.get("teams", {}).get(side, {}) or {}).get("team") or {})
        for p in ((box["teams"][side].get("players")) or {}).values():
            bat = (p.get("stats", {}) or {}).get("batting", {}) or {}
            try:
                pa = int(bat.get("plateAppearances", 0) or 0)
            except (TypeError, ValueError):
                pa = 0
            if pa < 1:
                continue
            name = ((p.get("person") or {}).get("fullName") or "").strip().lower()
            try:
                order = int(str(p.get("battingOrder") or "0")) // 100
            except (TypeError, ValueError):
                order = 0
            if name:
                out[name] = {"hits": int(bat.get("hits", 0) or 0),
                             "order": order, "team": team.get("name", "")}
    return out


def collect() -> list[dict]:
    """Quoted hitters ON THE PICKED TEAM, for games the board actually played."""
    picked: dict = {}
    for f in glob.glob(str(OUTPUT_DIR / "picks_2026-*.json")):
        date = Path(f).stem.split("picks_")[1]
        try:
            board = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        for g in board.get("games", []):
            pc = g.get("pick_criteria") or {}
            m = g.get("matchup") or ""
            if pc.get("play") != "pick" or " @ " not in m or not g.get("game_pk"):
                continue
            bet = pc.get("bet_team") or pc.get("advantage_team")
            if bet:
                picked[(date, m.replace(" @ ", "@"))] = (g["game_pk"], bet)

    quotes = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "prop_odds_*.json"))):
        date = Path(f).stem.split("prop_odds_")[1]
        try:
            day = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        for gk, players in (day or {}).items():
            got = picked.get((date, gk))
            if not got:
                continue
            pk, bet = got
            for name, v in (players or {}).items():
                over = v.get("over") if isinstance(v, dict) else v
                under = v.get("under") if isinstance(v, dict) else None
                if isinstance(over, int):
                    quotes.append({"date": date, "pk": pk, "bet_team": bet,
                                   "name": name, "over": over, "under": under})
    boxes = {pk: _box(pk) for pk in sorted({q["pk"] for q in quotes})}
    rows = []
    for q in quotes:
        b = boxes.get(q["pk"], {}).get(q["name"])
        if not b or b["team"] != q["bet_team"]:
            continue                      # not on the picked team, or did not bat
        rows.append({**q, "hit": b["hits"] >= 1, "order": b["order"]})
    return rows


def _by_game(rows):
    g: dict = {}
    for r in rows:
        g.setdefault((r["date"], r["pk"]), []).append(r)
    return g


def rules(rows) -> dict:
    """{name: [selected rows]} - every rule pre-declared, none tuned."""
    games = _by_game(rows)
    out: dict = {"every hitter on the picked team": rows}
    for label, keyf, rev in (("cheapest over price", lambda r: r["over"], False),
                             ("dearest over price", lambda r: r["over"], True)):
        sel = []
        for _, rs in games.items():
            sel.append(sorted(rs, key=keyf, reverse=rev)[0])
        out[label] = sel
    sel = []
    for _, rs in games.items():
        s = sorted(rs, key=lambda r: r["over"])
        if len(s) > 1:
            sel.append(s[1])
    out["second cheapest over price"] = sel
    for lab, lo, hi in (("batting order 1", 1, 1), ("order 1-3", 1, 3),
                        ("order 4-6", 4, 6), ("order 7-9", 7, 9)):
        out[lab] = [r for r in rows if lo <= r["order"] <= hi]
    out["over only at -150 or better"] = [r for r in rows if r["over"] >= -150]
    out["over only at -250 or worse"] = [r for r in rows if r["over"] <= -250]
    out["over only at -151 to -249"] = [r for r in rows
                                        if -249 <= r["over"] <= -151]
    return out


def _roi(rs) -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r["over"]) if r["hit"] else -1.0
               for r in rs) / len(rs)


def build() -> str:
    rows = collect()
    md = ["# Any mechanical prop rule on the picked teams that profits?", "",
          "_All rules are in the 1+ HIT market: the cached odds only ever held "
          "`batter_hits`, so total bases and hits+runs+RBIs cannot be tested "
          "retroactively at all._", ""]
    if len(rows) < 200:
        return "\n".join(md + [f"Only {len(rows)} quoted hitters on picked "
                               "teams; too few.", ""])
    md += [f"- quoted hitters on a picked team who batted: **{len(rows)}** "
           f"across {len(_by_game(rows))} picked games", ""]
    rs = rules(rows)
    md += ["| rule | bets | hit rate | ROI |", "|---|---|---|---|"]
    scored = {}
    for name, sel in rs.items():
        if len(sel) < MIN_BETS:
            md.append(f"| {name} | {len(sel)} | _too few_ | — |")
            continue
        hr = sum(1 for r in sel if r["hit"]) / len(sel)
        roi = _roi(sel)
        scored[name] = (roi, len(sel))
        md.append(f"| {name} | {len(sel)} | {hr:.1%} | **{roi:+.1%}** |")
    md.append("")
    if not scored:
        return "\n".join(md + ["No rule has enough bets.", ""])

    best_name = max(scored, key=lambda k: scored[k][0])
    best_roi = scored[best_name][0]
    md += [f"- best rule: **{best_name}** at **{best_roi:+.1%}** "
           f"on {scored[best_name][1]} bets", ""]

    # max-statistic permutation across every scored rule
    idx = {id(r): i for i, r in enumerate(rows)}
    hits = [1 if r["hit"] else 0 for r in rows]
    profit_if_hit = [grade.american_profit(r["over"]) for r in rows]
    rng = random.Random(4242)
    sel_idx = {n: [idx[id(r)] for r in s] for n, s in rs.items() if n in scored}
    null = []
    for _ in range(TRIALS):
        sh = hits[:]
        rng.shuffle(sh)
        best = None
        for n, ii in sel_idx.items():
            roi = sum(profit_if_hit[i] if sh[i] else -1.0 for i in ii) / len(ii)
            best = roi if best is None else max(best, roi)
        if best is not None:
            null.append(best)
    null.sort()
    p = sum(1 for x in null if x >= best_roi) / len(null)
    md += ["## Corrected for scanning every rule at once", "",
           f"- shuffling outcomes, the BEST of {len(scored)} rules returns "
           f"**{st.median(null):+.1%}** as a median and reaches "
           f"{best_roi:+.1%} **{p:.1%}** of the time",
           f"- **corrected p = {p:.4f}**", "",
           ("- **no rule here is distinguishable from dredging.** A scan this "
            "wide produces the best number by itself."
            if p > 0.05 else
            "- this clears the correction; it still needs forward games before "
            "a bet, because the rule was chosen on these same games"), ""]

    # the under, honestly: outcome is known, price is not
    md += ["## The under side", "",
           "_Under prices were only captured from 2026-10-03, so these cannot be "
           "priced historically. The no-hit rate is a fact; the price it would "
           "need is arithmetic; whether the book offered that is unknown._", "",
           "| rule | bets | no-hit rate | under price it would need |",
           "|---|---|---|---|"]
    for name in ("every hitter on the picked team", "dearest over price",
                 "cheapest over price", "order 7-9"):
        sel = rs.get(name) or []
        if len(sel) < MIN_BETS:
            continue
        nh = sum(1 for r in sel if not r["hit"]) / len(sel)
        need = round(100 * (1 - nh) / nh) if nh > 0 else 0
        md.append(f"| {name} | {len(sel)} | {nh:.1%} | **{need:+d}** or better |")
    real = [r for r in rows if isinstance(r.get("under"), int)]
    md += ["", f"- player-days with a REAL captured under price so far: "
           f"**{len(real)}**"
           + ("" if not real else
              f" (median {st.median([r['under'] for r in real]):+.0f})"), ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "prop_rule_scan.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
