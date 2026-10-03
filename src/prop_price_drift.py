"""
When a hitter's 1+ hit price is unusually LOW for him, does he underperform it?

THE IDEA
A hitter whose prop normally sits at -200 but is quoted -150 tonight has had
something change - lineup spot, a knock, a matchup the market respects. The price
is the market telling us. The question is whether it tells us ENOUGH: is the drop
an accurate repricing, or does the market under-react, leaving the fade profitable?

THE QUESTION THAT MATTERS, AND THE ONE THAT DOES NOT
"Does he hit less often when the price is lower" is trivially yes - that is what
the price means. The real question is whether he hits less often than TONIGHT'S
PRICE implies. So the statistic here is the market's ERROR:

    error = actual hit rate  -  the rate tonight's price implies

An American price includes the vig, so implied overstates the true probability and
the error is negative in every bucket by construction. That bias is CONSTANT
across buckets, so it cancels in the comparison between them. What is being tested
is whether the error is BIGGER when the price is unusually low - that is the only
part the vig does not explain.

DATA
The cached `prop_odds_<date>.json` files hold the whole batter_hits board for every
play-game, not just the posted prop: 4,374 player-day quotes across 499 players,
median 8 per player. Each player's baseline is a LEAVE-ONE-OUT median of his own
other quotes, so the day being judged never contributes to its own baseline.

A quoted player who did not bat is DROPPED, not counted as a no-hit. A scratch is
exactly the suspicious-price case, and scoring it as a loss would manufacture the
signal this is trying to test.

Writes output/prop_price_drift.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

import requests

from . import apitime

log = logging.getLogger("prop_price_drift")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MIN_QUOTES = 8          # quotes a player needs before he has a baseline
TRIALS = 10000
TIMEOUT = 20
# pre-declared deviation buckets, in implied-probability points vs his own median
BUCKETS = [(-1.0, -0.06, "much cheaper (≤ −6 pts)"),
           (-0.06, -0.02, "cheaper (−6 to −2)"),
           (-0.02, 0.02, "about normal (±2)"),
           (0.02, 0.06, "dearer (+2 to +6)"),
           (0.06, 1.0, "much dearer (≥ +6 pts)")]


def _implied(o: int) -> float:
    return abs(o) / (abs(o) + 100.0) if o < 0 else 100.0 / (o + 100.0)


def _box_hits(game_pk: int) -> dict:
    """{player name lower: hits} for every batter WITH a plate appearance."""
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
        for p in ((box.get("teams", {}).get(side, {}).get("players")) or {}).values():
            bat = (p.get("stats", {}) or {}).get("batting", {}) or {}
            try:
                pa = int(bat.get("plateAppearances", 0) or 0)
            except (TypeError, ValueError):
                pa = 0
            if pa < 1:
                continue                       # did not bat: drop, never a loss
            name = ((p.get("person") or {}).get("fullName") or "").strip().lower()
            if name:
                out[name] = int(bat.get("hits", 0) or 0)
    return out


def collect() -> list[dict]:
    """One row per quoted player-day that actually batted."""
    # (date, "Away@Home") -> game_pk, from the boards
    pk_of: dict = {}
    for f in glob.glob(str(OUTPUT_DIR / "picks_2026-*.json")):
        date = Path(f).stem.split("picks_")[1]
        try:
            board = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        for g in board.get("games", []):
            m = g.get("matchup") or ""
            if " @ " in m and g.get("game_pk"):
                pk_of[(date, m.replace(" @ ", "@"))] = g["game_pk"]

    quotes = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "prop_odds_*.json"))):
        date = Path(f).stem.split("prop_odds_")[1]
        try:
            day = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        for game_key, players in (day or {}).items():
            pk = pk_of.get((date, game_key))
            if not pk:
                continue
            for name, v in (players or {}).items():
                over = v.get("over") if isinstance(v, dict) else v
                under = v.get("under") if isinstance(v, dict) else None
                if isinstance(over, int):
                    quotes.append({"date": date, "pk": pk, "name": name,
                                   "over": over, "under": under})
    # one boxscore per game, not per quote
    hits_by_pk: dict = {}
    for pk in sorted({q["pk"] for q in quotes}):
        hits_by_pk[pk] = _box_hits(pk)
    rows = []
    for q in quotes:
        h = hits_by_pk.get(q["pk"], {}).get(q["name"])
        if h is None:
            continue                           # quoted but did not bat
        rows.append({**q, "hit": h >= 1, "imp": _implied(q["over"])})
    return rows


def build() -> str:
    rows = collect()
    md = ["# Is an unusually LOW prop price a fade?", "",
          "_Each hitter's baseline is a leave-one-out median of his OWN other "
          "quotes, so the day judged never feeds its own baseline. A quoted "
          "player who did not bat is dropped, never scored as a no-hit._", ""]
    if len(rows) < 300:
        return "\n".join(md + [f"Only {len(rows)} usable player-days.", ""])

    by_player = defaultdict(list)
    for r in rows:
        by_player[r["name"]].append(r)
    scored = []
    for name, rs in by_player.items():
        if len(rs) < MIN_QUOTES:
            continue
        for i, r in enumerate(rs):
            others = [x["imp"] for j, x in enumerate(rs) if j != i]
            base = st.median(others)
            scored.append({**r, "base": base, "dev": r["imp"] - base})

    md += [f"- quoted player-days that batted: **{len(rows)}**",
           f"- with a baseline (player has ≥ {MIN_QUOTES} quotes): "
           f"**{len(scored)}** across {sum(1 for v in by_player.values() if len(v) >= MIN_QUOTES)} players",
           f"- overall hit rate {sum(1 for r in scored if r['hit'])/len(scored):.1%} "
           f"against a mean implied {st.mean(r['imp'] for r in scored):.1%} "
           f"→ baseline market error "
           f"**{(sum(1 for r in scored if r['hit'])/len(scored) - st.mean(r['imp'] for r in scored))*100:+.1f} pts** "
           "(this is the vig, and it is in every bucket)", "",
           "## By how unusual tonight's price is for him", "",
           "_`error` is actual minus implied. More negative = he underperformed "
           "the price, which is what a fade needs._", "",
           "| tonight's price vs his own median | n | hit rate | implied | error |",
           "|---|---|---|---|---|"]
    cells = {}
    for lo, hi, label in BUCKETS:
        sub = [r for r in scored if lo <= r["dev"] < hi]
        if len(sub) < 25:
            md.append(f"| {label} | {len(sub)} | _too few_ | | |")
            continue
        hr = sum(1 for r in sub if r["hit"]) / len(sub)
        imp = st.mean(r["imp"] for r in sub)
        cells[label] = (hr - imp, len(sub))
        md.append(f"| {label} | {len(sub)} | {hr:.1%} | {imp:.1%} "
                  f"| **{(hr-imp)*100:+.1f} pts** |")
    md.append("")
    if len(cells) < 2:
        return "\n".join(md + ["Too few populated buckets to compare.", ""])

    # is the spread of bucket errors more than chance? permute the outcomes
    worst = min(cells.values())[0]
    best = max(cells.values())[0]
    obs_spread = best - worst
    hits = [1 if r["hit"] else 0 for r in scored]
    devs = [r["dev"] for r in scored]
    imps = [r["imp"] for r in scored]
    rng = random.Random(606)
    null = []
    for _ in range(TRIALS):
        sh = hits[:]
        rng.shuffle(sh)
        errs = []
        for lo, hi, _label in BUCKETS:
            idx = [i for i, d in enumerate(devs) if lo <= d < hi]
            if len(idx) < 25:
                continue
            errs.append(sum(sh[i] for i in idx)/len(idx)
                        - sum(imps[i] for i in idx)/len(idx))
        if len(errs) >= 2:
            null.append(max(errs) - min(errs))
    null.sort()
    p = sum(1 for x in null if x >= obs_spread) / len(null) if null else 1.0
    md += ["## Corrected for comparing five buckets", "",
           f"- observed spread between best and worst bucket error: "
           f"**{obs_spread*100:.1f} pts**",
           f"- shuffling outcomes, that spread is typically "
           f"**{st.median(null)*100:.1f} pts** and reaches "
           f"{obs_spread*100:.1f} **{p:.1%}** of the time",
           f"- **corrected p = {p:.4f}**", "",
           ("- **the market's error does not depend on how unusual the price "
            "is.** An unusually low price is an accurate repricing, not an "
            "under-reaction, so there is nothing to fade."
            if p > 0.05 else
            "- the error DOES vary by bucket; worth re-testing on new games "
            "before anything is acted on"), ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "prop_price_drift.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
