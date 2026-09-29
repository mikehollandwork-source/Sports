"""
Do all our sources point the same way - and is disagreement itself a signal?

THE QUESTION
We collect side-reads from a lot of places: covers.com tickets, the covers
forum, VSiN bets, Polymarket bets, Vegas handle, sportsbook line movement, the
Polymarket order book, and now Kalshi pre-game money. Most days they broadly
agree. The interesting games are the ones where they DON'T - somebody is wrong,
and if a particular source is systematically right when it stands alone, that is
tradeable.

WHAT IS TESTED
  1. coverage - how many sources each game actually has
  2. UNANIMOUS games: back the agreed side, and fade it
  3. SPLIT games: back the majority, fade the majority, and back each individual
     source when it dissents from the rest
  4. specifically Kalshi money vs everyone else, since that is the newest and
     the only one backed by settled cash rather than ticket counts

Every side is normalised to "away"/"home" so sources are directly comparable.
Results run through pregame_money's controls, so the favourite control, the
market-calibrated null, the holdout split and the day-block bootstrap all apply.

Writes output/source_agreement.md. Reporting only - nothing here feeds the board.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
import time
from collections import Counter
from pathlib import Path

from . import kalshi, mlb_api, pm_books
from .analysis import _canon_abbr
from .pregame_money import (HOLDOUT_FROM, LOOKBACK, MIN_N, PACE, _candles,
                            _implied, _start_ts, _vol, settled_index)
from . import grade

log = logging.getLogger("source_agreement")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MAX_SPREAD = 0.15
MIN_LEAN = 0.20

# the sources we can read a side from, in report order
SOURCES = ["covers", "forum", "vsin_bets", "polymarket_bets",
           "vegas", "line", "pm_book", "kalshi_money"]


def _side_of(team: str | None, away: str, home: str) -> str | None:
    if not team:
        return None
    if team == away:
        return "away"
    if team == home:
        return "home"
    return None


def _pm_lean(readings, adv_side: str | None) -> str | None:
    """pm_books stores the ADVANTAGE side's contract: bid = money on that side."""
    best = None
    for r in readings or []:
        if r.get("empty"):
            continue
        b, a = r.get("bid"), r.get("ask")
        if not (isinstance(b, (int, float)) and isinstance(a, (int, float))):
            continue
        if a <= b or (a - b) > MAX_SPREAD:
            continue
        if best is None or r.get("t", 0) > best.get("t", 0):
            best = r
    if not best or not adv_side:
        return None
    bs, as_ = float(best.get("bid_sz") or 0), float(best.get("ask_sz") or 0)
    if bs + as_ <= 0:
        return None
    v = (bs - as_) / (bs + as_)
    other = "home" if adv_side == "away" else "away"
    return adv_side if v > MIN_LEAN else other if v < -MIN_LEAN else None


def collect() -> tuple[list, dict]:
    kmap = settled_index()
    recs, diag = [], Counter()

    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        pb = pm_books.load_day(date) or {}
        day = json.loads(Path(f).read_text())
        for g in day.get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            if " @ " not in (g.get("matchup") or ""):
                continue
            away, home = g["matchup"].split(" @ ")
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            adv_side = _side_of(adv, away, home)
            if not adv_side:
                continue
            opp_side = "home" if adv_side == "away" else "away"

            sides: dict = {}
            # 1-4: the public/consensus sources, already normalised upstream
            for s in (g.get("public_check") or {}).get("sources") or []:
                if s.get("side") in ("away", "home") and s.get("name") in SOURCES:
                    sides[s["name"]] = s["side"]
            # 5: Vegas handle
            sides["vegas"] = _side_of((pc.get("vegas") or {}).get("bet"), away, home)
            # 6: sportsbook line movement, toward whichever side it moved
            shift = (pc.get("line_check") or {}).get("implied_shift")
            if isinstance(shift, (int, float)) and abs(shift) >= 0.01:
                sides["line"] = adv_side if shift > 0 else opp_side
            # 7: Polymarket resting depth
            sides["pm_book"] = _pm_lean(
                (pb.get("games", {}).get(str(g.get("game_pk"))) or {}).get("readings"),
                adv_side)
            # 8: Kalshi pre-game traded volume
            aa, ha = _canon_abbr(g.get("away_abbr") or ""), _canon_abbr(g.get("home_abbr") or "")
            teams = kmap.get((date, frozenset({aa, ha}))) if aa and ha else None
            start = _start_ts(g.get("game_datetime"))
            if teams and start and len(teams) == 2:
                vols = {}
                for ab, info in teams.items():
                    cs = _candles(info["ticker"], start - LOOKBACK, start)
                    if cs:
                        vols[ab] = sum(_vol(c) for c in cs)
                    time.sleep(PACE)
                if len(vols) == 2 and vols[aa] != vols[ha]:
                    sides["kalshi_money"] = "away" if vols[aa] > vols[ha] else "home"

            sides = {k: v for k, v in sides.items() if v in ("away", "home")}
            if len(sides) < 3:
                diag["too_few_sources"] += 1
                continue
            diag[f"n_sources_{len(sides)}"] += 1

            win_side = "away" if res["winner"] == away else "home"
            recs.append({
                "date": date, "win_side": win_side,
                "adv": adv_side, "opp": opp_side,
                "price": {adv_side: a_ml, opp_side: o_ml},
                "sides": sides,
            })
    return recs, diag


# ---------------------------------------------------------------- analysis

def _rows(recs, chooser) -> list:
    out = []
    for r in recs:
        s = chooser(r)
        if s not in ("away", "home"):
            continue
        out.append({"won": r["win_side"] == s, "odds": r["price"][s]})
    return out


def _fmt(rows) -> str:
    if not rows:
        return "—"
    w = sum(1 for x in rows if x["won"])
    if len(rows) < MIN_N:
        return f"{w}-{len(rows)-w} · _n={len(rows)}, too few_"
    u = sum(grade.american_profit(x["odds"]) if x["won"] else -1 for x in rows)
    return f"{w}-{len(rows)-w} ({w/len(rows):.0%}) · {u:+.1f}u · **{u/len(rows):+.1%}** (n={len(rows)})"


def _majority(r: dict, exclude: str | None = None) -> str | None:
    c = Counter(v for k, v in r["sides"].items() if k != exclude)
    if not c:
        return None
    top = c.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return None
    return top[0][0]


def _flip(s: str | None) -> str | None:
    return None if s not in ("away", "home") else ("home" if s == "away" else "away")


def build() -> str:
    recs, diag = collect()
    md = ["# Do our sources agree — and does disagreement pay?", "",
          "_Every source's pick normalised to away/home so they are directly "
          "comparable: covers tickets, covers forum, VSiN bets, Polymarket bets, "
          "Vegas handle, sportsbook line movement, the Polymarket order book, and "
          "Kalshi pre-game traded volume._", "",
          f"## Coverage", "",
          f"- games with at least 3 sources: **{len(recs)}**",
          "- sources per game: " + (", ".join(
              f"{k.split('_')[-1]}→{v}" for k, v in sorted(diag.items())
              if k.startswith("n_sources")) or "none"), ""]
    if len(recs) < MIN_N:
        return "\n".join(md + ["## Verdict", "", "Too few games to read.", ""])

    have = Counter()
    for r in recs:
        for k in r["sides"]:
            have[k] += 1
    md += ["| source | games with a read |", "|---|---|"]
    md += [f"| `{k}` | {have.get(k, 0)} |" for k in SOURCES]
    md.append("")

    unanimous = [r for r in recs if len(set(r["sides"].values())) == 1]
    split = [r for r in recs if len(set(r["sides"].values())) > 1]
    md += ["## 1. Unanimous vs split", "",
           f"- all sources agree: **{len(unanimous)}**",
           f"- sources disagree: **{len(split)}**", "",
           "| strategy | result |", "|---|---|",
           f"| UNANIMOUS — back the agreed side | {_fmt(_rows(unanimous, lambda r: next(iter(r['sides'].values()))))} |",
           f"| UNANIMOUS — fade the agreed side | {_fmt(_rows(unanimous, lambda r: _flip(next(iter(r['sides'].values())))))} |",
           f"| SPLIT — back the majority | {_fmt(_rows(split, _majority))} |",
           f"| SPLIT — fade the majority | {_fmt(_rows(split, lambda r: _flip(_majority(r))))} |", ""]

    md += ["## 2. When one source stands against the rest", "",
           "_Only games where this source disagrees with the majority of the "
           "others. `back` follows the lone dissenter, `fade` follows the crowd._",
           "", "| source | n | back the dissenter | fade it |", "|---|---|---|---|"]
    for s in SOURCES:
        sub = [r for r in recs
               if s in r["sides"] and _majority(r, exclude=s)
               and r["sides"][s] != _majority(r, exclude=s)]
        md.append(f"| `{s}` | {len(sub)} | "
                  f"{_fmt(_rows(sub, lambda r, s=s: r['sides'][s]))} | "
                  f"{_fmt(_rows(sub, lambda r, s=s: _majority(r, exclude=s)))} |")
    md.append("")

    md += ["## 3. Kalshi money vs everyone else", "",
           "_Kalshi is the only source backed by settled cash rather than ticket "
           "counts, so it gets its own head-to-head._", "",
           "| case | n | back Kalshi's side | back the others' side |",
           "|---|---|---|---|"]
    agree, disagree = [], []
    for r in recs:
        km, other = r["sides"].get("kalshi_money"), _majority(r, exclude="kalshi_money")
        if not km or not other:
            continue
        (agree if km == other else disagree).append(r)
    for label, sub in (("agree", agree), ("DISAGREE", disagree)):
        md.append(f"| {label} | {len(sub)} | "
                  f"{_fmt(_rows(sub, lambda r: r['sides']['kalshi_money']))} | "
                  f"{_fmt(_rows(sub, lambda r: _majority(r, exclude='kalshi_money')))} |")
    md.append("")

    md += ["## 4. Holdout split on the headline cases", "",
           "| case | in-sample | holdout |", "|---|---|---|"]
    for label, sub, ch in (
            ("unanimous, back it", unanimous, lambda r: next(iter(r["sides"].values()))),
            ("split, back majority", split, _majority),
            ("kalshi disagrees, back kalshi", disagree, lambda r: r["sides"]["kalshi_money"]),
            ("kalshi disagrees, back others", disagree,
             lambda r: _majority(r, exclude="kalshi_money"))):
        pre = [r for r in sub if r["date"] < HOLDOUT_FROM]
        post = [r for r in sub if r["date"] >= HOLDOUT_FROM]
        md.append(f"| {label} | {_fmt(_rows(pre, ch))} | {_fmt(_rows(post, ch))} |")
    md.append("")

    md.append("_Rows under n=%d are shown as counts only. A source that looks "
              "brilliant as a lone dissenter on a handful of games is the single "
              "easiest way to fool yourself here._" % MIN_N)
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "source_agreement.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
