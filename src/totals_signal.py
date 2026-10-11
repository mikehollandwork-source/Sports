"""
Can our signals predict RUNS? Pre-registered, before the lines exist.

THE SITUATION
Asked to backtest the strikeout, first-five and full-game totals against our
signals. We cannot: those markets began logging on 2026-10-11 and there are two
games. No historical totals exist anywhere - `betting_lines` on the boards
stores moneylines only, and there are no early-line files.

WHAT IS WORTH DOING INSTEAD, AND WHY IT IS BETTER THAN WAITING
Beating a totals line needs two separate things: signals that predict runs, and
a market that has not already priced them. The second cannot be tested yet. The
FIRST can, right now, against actual scores - and it is the half that decides
whether the idea is alive at all. If our inputs cannot predict runs with no vig
and no opponent, they will certainly not beat a line.

So this tests signal against OUTCOME, not signal against market. There is no
betting here and no ROI, because without a line there is no price to beat.

PRE-REGISTERED, WHICH IS THE POINT
Every sweep in this repo has been run after the data was visible, and the
correction for that is what kept killing them. Here the lines do not exist yet,
so the hypotheses below are written while genuinely blind. When the market data
accumulates, the test is honest by construction rather than by correction.

    full-game runs   park, temperature, wind, combined lineup hit rate,
                     combined starter quality (FIP from the board)
    first-five runs  the same, since the starters are who pitch it

Read-only. Writes output/totals_signal.md. Changes no pick.
"""

from __future__ import annotations

import glob
import json
import logging
import math
import statistics as st
import unicodedata
from pathlib import Path

from . import mlb_api

log = logging.getLogger("totals_signal")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPORT = OUTPUT_DIR / "totals_signal.md"
SCORES = OUTPUT_DIR / "totals_scores.json"
BOX = OUTPUT_DIR / "coherence_cache.json"
LINEUPS = OUTPUT_DIR / "lineup_price_cache.json"

LEAGUE_HIT_RATE = 0.63
SHRINK_GAMES = 12


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s.lower() if c.isalnum() or c == " ").strip()


def _scores(date: str, cache: dict) -> dict:
    """{gamePk: {total, f5}} - full-game runs and runs through five innings."""
    if date in cache:
        return cache[date]
    try:
        data = mlb_api._get("schedule", sportId=1, date=date,
                            hydrate="linescore")
    except Exception as exc:
        log.warning("linescore %s failed (%s)", date, exc)
        return {}
    out = {}
    for day in data.get("dates", []):
        for g in day.get("games", []):
            if (g.get("status") or {}).get("abstractGameState") != "Final":
                continue
            ls = g.get("linescore") or {}
            innings = ls.get("innings") or []
            try:
                h = int((ls.get("teams") or {}).get("home", {}).get("runs"))
                a = int((ls.get("teams") or {}).get("away", {}).get("runs"))
            except (TypeError, ValueError):
                continue
            f5 = 0
            ok = len(innings) >= 5
            for inn in innings[:5]:
                for sd in ("home", "away"):
                    v = (inn.get(sd) or {}).get("runs")
                    f5 += int(v) if isinstance(v, int) else 0
            out[str(g["gamePk"])] = {"total": h + a,
                                     "f5": f5 if ok else None}
    cache[date] = out
    return out


def collect() -> list[dict]:
    try:
        cache = json.loads(SCORES.read_text())
    except (OSError, ValueError):
        cache = {}
    box = json.loads(Path(BOX).read_text())
    lineups = json.loads(Path(LINEUPS).read_text())
    hist: dict[str, list[int]] = {}
    rows = []
    dirty = False

    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            day = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        games = [g for g in day.get("games", [])
                 if str(g.get("game_pk")) in lineups]
        if not games:
            continue
        before = date in cache
        sc = _scores(date, cache)
        dirty = dirty or not before
        for g in games:
            pk = str(g.get("game_pk"))
            s = sc.get(pk)
            m = g.get("matchup") or ""
            if not s or " @ " not in m:
                continue
            away, home = m.split(" @ ")
            st_ = lineups[pk]
            if home not in st_ or away not in st_:
                continue

            def rate(nm):
                gm, hh = hist.get(_norm(nm), [0, 0])
                w = gm / (gm + SHRINK_GAMES)
                return (w * (hh / gm if gm else LEAGUE_HIT_RATE)
                        + (1 - w) * LEAGUE_HIT_RATE)

            lineup_rate = st.mean([rate(n) for n in st_[home]]
                                  + [rate(n) for n in st_[away]])
            wx = g.get("weather") or {}
            sa = g.get("statistical_advantage") or {}

            def fip(side):
                v = (sa.get(side) or {}).get("starter_fip")
                return float(v) if isinstance(v, (int, float)) else None
            fh, fa = fip("home"), fip("away")
            rows.append({
                "date": date, "pk": pk,
                "total": s["total"], "f5": s["f5"],
                "park": float(g.get("park_factor") or 1.0),
                "temp": wx.get("temp_f"), "wind": wx.get("wind_mph"),
                "lineup_rate": lineup_rate,
                "fip": (st.mean([x for x in (fh, fa) if x is not None])
                        if (fh is not None or fa is not None) else None),
            })
            for nm, line in (box.get(pk) or {}).items():
                if isinstance(line, list) and len(line) >= 2 and line[1] >= 1:
                    c = hist.setdefault(nm, [0, 0])
                    c[0] += 1
                    c[1] += 1 if line[0] >= 1 else 0
    if dirty:
        try:
            SCORES.write_text(json.dumps(cache))
        except OSError as exc:
            log.warning("scores cache not written (%s)", exc)
    return rows


def _pearson(xs, ys):
    n = len(xs)
    if n < 10:
        return None
    mx, my = st.mean(xs), st.mean(ys)
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else None


SIGNALS = ("park", "temp", "wind", "lineup_rate", "fip")


def build() -> str:
    rows = collect()
    md = ["# Can our signals predict RUNS?", "",
          "_The totals markets began logging on 2026-10-11, so there is no "
          "history to backtest against a line. This tests the half that can "
          "be tested: signal against actual score. No line means no vig and "
          "no ROI — if these cannot predict runs unopposed, they will not "
          "beat a price._", "",
          f"- graded games with a score: **{len(rows)}**", ""]
    if len(rows) < 100:
        return "\n".join(md + ["_Too few games._", ""])
    tot = [r["total"] for r in rows]
    f5s = [r["f5"] for r in rows if isinstance(r["f5"], int)]
    md += [f"- full-game runs: mean **{st.mean(tot):.2f}**, "
           f"median {st.median(tot):.1f}, SD {st.pstdev(tot):.2f}",
           (f"- first-five runs: mean **{st.mean(f5s):.2f}** "
            f"({st.mean(f5s)/st.mean(tot):.0%} of the game), n={len(f5s)}"
            if f5s else "- first-five runs: none parsed"), "",
           "## Each signal against the actual score", "",
           "| signal | n | r vs full game | r vs first five |",
           "|---|---|---|---|"]
    for sig in SIGNALS:
        pair = [(r[sig], r["total"], r["f5"]) for r in rows
                if isinstance(r.get(sig), (int, float))]
        if len(pair) < 50:
            md.append(f"| {sig} | {len(pair)} | _too few_ | |")
            continue
        rt = _pearson([p[0] for p in pair], [p[1] for p in pair])
        sub = [p for p in pair if isinstance(p[2], int)]
        rf = (_pearson([p[0] for p in sub], [p[2] for p in sub])
              if len(sub) >= 50 else None)
        md.append(f"| {sig} | {len(pair)} | {rt:+.3f} |"
                  + (f" {rf:+.3f} |" if rf is not None else " — |"))
    md += ["", "_A correlation inside roughly ±0.10 at this sample is not "
           "distinguishable from nothing._", ""]

    # the bettable shape, against a fixed bar rather than a market line
    bar = st.median(tot)
    md += [f"## Over/under the median ({bar:.1f} runs)", "",
           "_No market line exists, so the bar is our own median. This shows "
           "whether a signal SORTS games, which is necessary before it can "
           "beat a price — not sufficient._", "",
           "| signal | low third | high third | gap |", "|---|---|---|---|"]
    for sig in SIGNALS:
        have = [r for r in rows if isinstance(r.get(sig), (int, float))]
        if len(have) < 90:
            continue
        have.sort(key=lambda r: r[sig])
        k = len(have) // 3
        lo = have[:k]
        hi = have[2 * k:]
        fl = sum(1 for r in lo if r["total"] > bar) / len(lo)
        fh = sum(1 for r in hi if r["total"] > bar) / len(hi)
        md.append(f"| {sig} | {fl:.1%} over | {fh:.1%} over | **{fh-fl:+.1%}** |")
    md += ["", "## Pre-registered, for when the lines arrive", "",
           "_Written while blind — the market data does not exist yet, so "
           "these cannot have been chosen to fit it. When the log has a "
           "season, the test is: does the signal beat the CLOSING line, "
           "corrected for the width of the search, with both tails checked._",
           "",
           "- full game: park, temperature, wind, lineup hit rate, starter FIP",
           "- first five: the same, since the starters pitch it",
           "- strikeout line: the starter's K price against the opposing "
           "lineup's hit prices, which should move opposite",
           "- the bar is the vig, roughly 4.5% on a two-sided total, not zero",
           ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    OUTPUT_DIR.mkdir(exist_ok=True)
    t = build()
    REPORT.write_text(t)
    print(t)


if __name__ == "__main__":
    main()
