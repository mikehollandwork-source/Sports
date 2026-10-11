"""
Do the prices agree with each other, and with what we have measured?

NOT A PROFIT HUNT
Every search in this repo has asked "where is the edge". This asks a different
and more basic question: are the numbers CONSISTENT? A price that disagrees
with another price on the same game, or with an outcome we recorded ourselves,
is either a stale line, a market joined to the wrong event - which has happened
here before, with Kalshi - or a figure we are reading wrong. All three are data
faults, and none of them shows up in an ROI table.

FOUR CHECKS

1. CALIBRATION of the hit props. Bucket every stored price by the probability
   it implies, then look at how often those hitters actually got a hit. A
   well-calibrated book sits on the diagonal once the vig is allowed for. This
   is the check that explains the prop record: a 63.3% hit rate against a 66.8%
   break-even is exactly what a correctly-priced market looks like, and the
   calibration curve either confirms that or finds the price we can beat.

2. OUR RATE against THEIR PRICE, per hitter. We store all_rate - his hit rate
   across every game. If our number and the market's disagree systematically,
   one of them is wrong, and it matters which.

3. FIRST FIVE against the FULL GAME. The first five innings are roughly 55-60%
   of a game's runs. A pair that does not sit in that band is a stale line or a
   mis-joined event.

4. THE STRIKEOUT LINE against the OPPOSING LINEUP. A starter priced for a lot
   of strikeouts should face hitters priced low to get a hit. If those two move
   together instead of apart, one of them is not about this game.

Checks 3 and 4 need the new market log and will be thin for weeks. Checks 1 and
2 run on 4,447 prices already stored.

Read-only. Writes output/market_coherence.md. Changes no pick.
"""

from __future__ import annotations

import glob
import json
import logging
import math
import statistics as st
import unicodedata
from pathlib import Path

from . import mlb_api, prop_odds
from .pregame_money import _implied

log = logging.getLogger("market_coherence")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPORT = OUTPUT_DIR / "market_coherence.md"
CACHE = OUTPUT_DIR / "coherence_cache.json"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s.lower() if c.isalnum() or c == " ").strip()


def _box_hits(game_pk: int) -> dict[str, list[int]] | None:
    """{normalised name: [hits, PA]} for everyone who batted."""
    try:
        bs = mlb_api._get(f"game/{game_pk}/boxscore")
    except Exception as exc:
        log.warning("boxscore %s failed (%s)", game_pk, exc)
        return None
    out = {}
    for side in ("away", "home"):
        t = ((bs.get("teams") or {}).get(side) or {})
        for p in (t.get("players") or {}).values():
            nm = (p.get("person") or {}).get("fullName")
            bat = ((p.get("stats") or {}).get("batting") or {})
            if not nm or not bat:
                continue
            try:
                out[_norm(nm)] = [int(bat.get("hits", 0) or 0),
                                  int(bat.get("plateAppearances", 0) or 0)]
            except (TypeError, ValueError):
                continue
    return out


def collect() -> list[dict]:
    """One row per priced hitter: implied probability and what he did."""
    try:
        cache = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        cache = {}
    rows = []
    files = [f for f in sorted(glob.glob(str(OUTPUT_DIR / "prop_odds_2026-*.json")))
             if "_hr_" not in f and "_hrr_" not in f]
    for f in files:
        date = Path(f).stem.split("prop_odds_")[1]
        try:
            odds = json.loads(Path(f).read_text())
            board = json.loads((OUTPUT_DIR / f"picks_{date}.json").read_text())
        except (OSError, ValueError):
            continue
        by = {g.get("matchup"): g for g in board.get("games", [])}
        for matchup, hitters in odds.items():
            if not isinstance(hitters, dict) or not hitters:
                continue
            g = by.get(matchup.replace("@", " @ ")) or by.get(matchup)
            if not g:
                continue
            pk = g.get("game_pk")
            ck = str(pk)
            if ck not in cache:
                b = _box_hits(pk)
                if b is None:
                    continue
                cache[ck] = b
            box = cache[ck]
            for nm, v in hitters.items():
                o = prop_odds._as_row(v).get("over")
                if not isinstance(o, int):
                    continue
                stat = box.get(_norm(nm))
                if not stat or stat[1] < 1:
                    continue          # did not bat: the prop would have voided
                rows.append({"date": date, "name": _norm(nm), "odds": o,
                             "implied": _implied(o), "hit": 1 if stat[0] >= 1 else 0,
                             "pa": stat[1]})
    try:
        CACHE.write_text(json.dumps(cache))
    except OSError as exc:
        log.warning("cache not written (%s)", exc)
    return rows


def _wilson(k: int, n: int) -> tuple[float, float]:
    if not n:
        return (0.0, 0.0)
    p, z = k / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def build() -> str:
    rows = collect()
    md = ["# Do the prices agree — with each other, and with us?", "",
          "_Not an edge hunt. A price that disagrees with another price on the "
          "same game, or with an outcome we recorded, is a stale line, a "
          "mis-joined event or a number we are reading wrong — and none of "
          "those shows up in an ROI table._", "",
          f"- priced hitter-games with a result: **{len(rows)}**", ""]
    if len(rows) < 200:
        return "\n".join(md + ["_Too few to judge._", ""])

    # --- 1. calibration
    md += ["## 1. Is the hit market calibrated?", "",
           "_Implied probability still carries the vig, so a correctly-priced "
           "book should land BELOW the diagonal by roughly the hold (~6.5% on "
           "these), not on it._", "",
           "| implied band | n | implied | actual | gap | 95% CI on actual |",
           "|---|---|---|---|---|---|"]
    bands = [(0.0, .55), (.55, .62), (.62, .67), (.67, .72), (.72, 1.0)]
    gaps = []
    for lo, hi in bands:
        sel = [r for r in rows if lo <= r["implied"] < hi]
        if len(sel) < 40:
            continue
        imp = st.mean(r["implied"] for r in sel)
        k = sum(r["hit"] for r in sel)
        act = k / len(sel)
        cl, ch = _wilson(k, len(sel))
        gaps.append(act - imp)
        md.append(f"| {lo:.0%}–{hi:.0%} | {len(sel)} | {imp:.1%} | {act:.1%} "
                  f"| {act-imp:+.1%} | {cl:.1%} – {ch:.1%} |")
    if gaps:
        md += ["", f"_Mean gap **{st.mean(gaps):+.1%}**. A book carrying ~6.5% "
               "hold should read about −6.5% here. Much closer to zero means "
               "the prices are beatable; much more negative means they are "
               "worse than the vig alone._", ""]

    # --- 2. our realised rate against their price, per hitter
    byname = {}
    for r in rows:
        byname.setdefault(r["name"], []).append(r)
    pairs = [(st.mean(v[i]["implied"] for i in range(len(v))),
              sum(x["hit"] for x in v) / len(v), len(v), n)
             for n, v in byname.items() if len(v) >= 10]
    md += ["## 2. Our realised rate against their price, hitter by hitter", "",
           f"_{len(pairs)} hitters with 10+ priced games._", ""]
    if len(pairs) >= 15:
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        mx, my = st.mean(xs), st.mean(ys)
        num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
        den = math.sqrt(sum((a - mx) ** 2 for a in xs)
                        * sum((b - my) ** 2 for b in ys))
        r = num / den if den else 0.0
        md += [f"- correlation between a hitter's mean price and his actual "
               f"rate: **r = {r:+.3f}**",
               f"- mean implied {mx:.1%} · mean actual {my:.1%} · "
               f"gap **{my-mx:+.1%}**", ""]
        worst = sorted(pairs, key=lambda p: p[1] - p[0])
        md += ["| hitter | games | mean price implies | actually hit | gap |",
               "|---|---|---|---|---|"]
        for lbl, grp in (("most overpriced", worst[:4]),
                         ("most underpriced", worst[-4:][::-1])):
            md.append(f"| _{lbl}_ | | | | |")
            for imp, act, n, nm in grp:
                md.append(f"| {nm} | {n} | {imp:.1%} | {act:.1%} | {act-imp:+.1%} |")
        md.append("")

    # --- 3 & 4. the new markets
    md += ["## 3-4. The new markets", ""]
    logs = sorted(glob.glob(str(OUTPUT_DIR / "market_log_*.json")))
    f5s, ks = [], []
    for f in logs:
        try:
            d = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        for poll in d.get("polls", []):
            tot = poll.get("totals") or {}
            for mk, ev in (poll.get("events") or {}).items():
                f5 = ev.get("f5_total")
                full = tot.get(mk)
                if f5 and full and full.get("point"):
                    f5s.append((mk, f5["point"], full["point"],
                                f5["point"] / full["point"]))
                for p, sides in (ev.get("strikeouts") or {}).items():
                    o = (sides.get("over") or {}).get("point")
                    if o:
                        ks.append((mk, p, o))
    if f5s:
        md += ["**First five against the full game** — runs through five "
               "innings are normally 55–60% of a game.", "",
               "| game | F5 | full | ratio |", "|---|---|---|---|"]
        for mk, a, b, rt in f5s[-8:]:
            flag = "" if 0.50 <= rt <= 0.65 else "  ⚠️ outside 50–65%"
            md.append(f"| {mk} | {a} | {b} | **{rt:.0%}**{flag} |")
        md.append("")
    else:
        md += ["_No paired first-five and full-game totals logged yet._", ""]
    if ks:
        md += ["**Strikeout lines logged**", "",
               "| game | pitcher | line |", "|---|---|---|"]
        for mk, p, o in ks[-8:]:
            md.append(f"| {mk} | {p} | o{o} |")
        md += ["", "_Too few games yet to test the K line against the "
               "opposing lineup's hit prices; that check needs a sample._", ""]
    md += ["## What a failure would look like", "",
           "- calibration gap near **zero** → the book is not charging its own "
           "vig and the prices are beatable",
           "- a hitter whose price and realised rate disagree by more than "
           "~15 points over 10+ games → likely a name joined to the wrong "
           "player, not a market view",
           "- an F5/full ratio outside 50–65% → a stale line or a mis-joined "
           "event, the same class of fault as the Kalshi ticker bug", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    OUTPUT_DIR.mkdir(exist_ok=True)
    text = build()
    REPORT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
