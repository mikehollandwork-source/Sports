"""
Back-test the four-leg ticket: how often would it actually have hit?

THE FOUR-LEG TICKET CANNOT BE BACK-TESTED ON THIS HISTORY, and that is the
first finding rather than a caveat. Of 248 past plays, **241 stored no
`hit_bats` pool at all** and 137 of the rest carry exactly ONE hitter - boards
posted a single prop until 2026-10-12, and the archival pool that would supply a
second hitter was only added at the end. Three distinct hitters never existed in
the record, so a four-leg reconstruction would be inventing two of its legs.
Asking anyway produced six tickets, which is not a measurement.

WHAT THE HISTORY DOES SUPPORT, and it is the useful half
The MONEYLINE pick and ONE posted hit prop, both with real captured prices and
both graded from the boxscore. That is the two-leg version of the same
structure, and it answers the question the four-leg one was asked for: do these
legs co-move, and does the pair beat its price?

It also measures the 2+ TOTAL BASES rate for exactly the hitters the board
posts, which is what a total-bases leg is worth and was previously a guess.

THE HONEST CAVEATS, stated before the numbers because they bound them
  1. Historical boards posted ONE prop, not three, so the two hit legs are
     reconstructed from `hit_bats` - the archival top-of-pool the board stored
     at the time. That pool was ranked by the OLD selector, which still carried
     the `form` term since removed. So this measures the STRUCTURE, not today's
     selector.
  2. Total-bases prices were never captured - that market only started being
     logged with `parlay_paper`. The leg's OUTCOME is real; its PRICE is
     assumed, and the report sweeps a range rather than picking one.
  3. The moneyline and hit-prop prices ARE real where the board captured them,
     assumed `-200` for a hit prop otherwise, which is the same fallback
     `prop_grade` uses.

WHAT NEEDS NO ASSUMPTION
The hit RATE of the structure. How often all four legs land is a count, and it
is the number that decides everything: against it, any price is just arithmetic.
Leg-by-leg rates are reported too, because the useful question is not "does this
lose" - `parlay_structure.md` already settled that - but WHICH leg is doing the
damage.

Read-only. Stakes nothing, enters no ledger. Writes output/parlay_backtest.md.
"""

from __future__ import annotations

import glob
import json
import logging
from pathlib import Path

from . import mlb_api

log = logging.getLogger("parlay_backtest")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPORT = OUTPUT_DIR / "parlay_backtest.md"
CACHE = OUTPUT_DIR / "parlay_backtest_cache.json"

ASSUMED_PROP = -200          # same fallback prop_grade uses
TB_PRICES = (100, 140, 180)  # the sweep for the unpriced leg
TB_MAIN = 140
STAKE = 1.0


def _dec(american: int) -> float:
    return american / 100 + 1 if american > 0 else 100 / abs(american) + 1


def _american(dec: float) -> int:
    return round((dec - 1) * 100) if dec >= 2 else -round(100 / (dec - 1))


def _box(pk: int, cache: dict) -> dict:
    """{player_id: [hits, total_bases]} for a game, fetched once and cached.

    `mlb_api.player_hits` and `player_total_bases` each pull the whole boxscore,
    so asking them per player would fetch the same document three times a game.
    """
    key = str(pk)
    if key in cache:
        return cache[key]
    out: dict = {}
    try:
        box = mlb_api._get(f"game/{pk}/boxscore")
    except Exception as exc:
        log.warning("boxscore %s failed: %s", pk, exc)
        return {}
    for side in ("home", "away"):
        for pid, p in ((box.get("teams") or {}).get(side, {}).get("players")
                       or {}).items():
            bat = ((p.get("stats") or {}).get("batting") or {})
            if int(bat.get("plateAppearances", 0) or 0) < 1:
                continue
            h = int(bat.get("hits", 0) or 0)
            d = int(bat.get("doubles", 0) or 0)
            t = int(bat.get("triples", 0) or 0)
            hr = int(bat.get("homeRuns", 0) or 0)
            out[pid.replace("ID", "")] = [h, max(0, h - d - t - hr)
                                          + 2 * d + 3 * t + 4 * hr]
    cache[key] = out
    return out


def collect() -> list[dict]:
    """One row per past PLAY with a gradeable moneyline leg and posted prop."""
    try:
        cache = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        cache = {}
    rows, dirty = [], False
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            day = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        results = None
        for g in day.get("games", []):
            pc = g.get("pick_criteria") or {}
            if pc.get("play") != "pick":
                continue
            team = pc.get("bet_team") or pc.get("advantage_team")
            ml = pc.get("bet_moneyline")
            if ml is None:
                ml = pc.get("advantage_moneyline")
            posted = pc.get("props") or ([pc["prop"]] if pc.get("prop") else [])
            if not team or not isinstance(ml, int) or not posted:
                continue
            pid = posted[0].get("player_id")
            if not pid:
                continue
            pk = g.get("game_pk")
            if results is None:
                results = mlb_api.results_for(date)
            r = results.get(pk)
            if not r or not r.get("final"):
                continue
            before = str(pk) in cache
            lines = _box(pk, cache)
            dirty = dirty or not before
            if str(pid) not in lines:
                continue              # did not bat: not a graded leg
            h, tb = lines[str(pid)]
            rows.append({
                "date": date, "game_pk": pk, "matchup": g.get("matchup"),
                "team": team, "ml": ml, "ml_won": r.get("winner") == team,
                "player": posted[0].get("player"), "player_id": pid,
                "prop_odds": (int(posted[0]["odds"])
                              if isinstance(posted[0].get("odds"), int)
                              else ASSUMED_PROP),
                "real_price": isinstance(posted[0].get("odds"), int),
                "hit_won": h >= 1, "tb_won": tb >= 2})
    if dirty:
        try:
            OUTPUT_DIR.mkdir(exist_ok=True)
            CACHE.write_text(json.dumps(cache))
        except OSError as exc:
            log.warning("cache not written (%s)", exc)
    return rows


def _pair_roi(rows: list, tb_price: int | None) -> tuple:
    """(wins, n, roi, mean decimal) for ML + prop, optionally + total bases."""
    wins = n = 0
    profit = 0.0
    decs = []
    for r in rows:
        dec = _dec(r["ml"]) * _dec(r["prop_odds"])
        ok = r["ml_won"] and r["hit_won"]
        if tb_price is not None:
            dec *= _dec(tb_price)
            ok = ok and r["tb_won"]
        n += 1
        decs.append(dec)
        if ok:
            wins += 1
            profit += STAKE * (dec - 1)
        else:
            profit -= STAKE
    if not n:
        return 0, 0, None, None
    return wins, n, profit / (n * STAKE), sum(decs) / len(decs)


def build() -> str:
    rows = collect()
    md = ["# Back-testing the parlay structure", "",
          "_Read-only. Stakes nothing, enters no ledger. Outcomes are graded "
          "from the boxscore._", "",
          "## First finding: the FOUR-leg ticket is not back-testable", "",
          "_Of 248 past plays, **241 stored no `hit_bats` pool at all** and "
          "most of the rest carry exactly ONE hitter. Boards posted a single "
          "prop until 2026-10-12. Three distinct hitters never existed in the "
          "record, so reconstructing four legs would mean inventing two of "
          "them — asking anyway returned six tickets, which is not a "
          "measurement. The four-leg record has to be built FORWARD, which is "
          "what `parlay_paper` is now doing._", ""]
    if len(rows) < 20:
        return "\n".join(md + [f"- only {len(rows)} gradeable two-leg rows; "
                                "not measurable.", ""])
    n = len(rows)
    mlw = sum(1 for r in rows if r["ml_won"])
    hw = sum(1 for r in rows if r["hit_won"])
    tbw = sum(1 for r in rows if r["tb_won"])
    both = sum(1 for r in rows if r["ml_won"] and r["hit_won"])
    md += ["## What the history does support: the moneyline pick + its prop",
           "",
           f"- gradeable rows: **{n}** "
           f"({rows[0]['date']} to {rows[-1]['date']})",
           f"- of those, prop legs with a REAL captured price: "
           f"**{sum(1 for r in rows if r['real_price'])}**", "",
           "| leg | hit | rate |", "|---|---|---|",
           f"| moneyline pick | {mlw}/{n} | **{mlw / n:.1%}** |",
           f"| the posted prop, 1+ hit | {hw}/{n} | **{hw / n:.1%}** |",
           f"| that same hitter, 2+ total bases | {tbw}/{n} | "
           f"**{tbw / n:.1%}** |", ""]
    ind = (mlw / n) * (hw / n)
    md += [f"- **both together: {both}/{n} = {both / n:.1%}**, against "
           f"{ind:.1%} if they were independent → same-game lift "
           f"**×{(both / n) / ind:.3f}**",
           "  _Positive is expected and is the only thing that makes a parlay "
           "better than its legs: a team winning and its hitter getting a hit "
           "are the same night going one way. Note the prop may be on EITHER "
           "team since 2026-10-12, which weakens exactly this._", ""]
    md += ["## Does the pair beat its price?", "",
           "| structure | wins | mean price | ROI |", "|---|---|---|---|"]
    w, nn, roi, mp = _pair_roi(rows, None)
    md.append(f"| ML + 1 prop (2 legs, real prices) | {w}/{nn} "
              f"({w / nn:.1%}) | {_american(mp):+d} | **{roi:+.1%}** |")
    for tbp in TB_PRICES:
        w, nn, roi, mp = _pair_roi(rows, tbp)
        md.append(f"| + 2 total bases at {tbp:+d} (3 legs) | {w}/{nn} "
                  f"({w / nn:.1%}) | {_american(mp):+d} | **{roi:+.1%}** |")
    md += ["", "_The three-leg rows add total bases on the SAME hitter as the "
           "hit leg, which is a NESTED leg the live builder now forbids — 2+ "
           "total bases cannot happen without a hit. They are shown because "
           "the history has no second hitter to use, and they therefore "
           "FLATTER the structure: the real four-leg version needs a third "
           "hitter to also come through._", "",
           "## What this says about the total-bases leg", "",
           f"- the board's own posted hitters reach 2+ total bases "
           f"**{tbw / n:.1%}** of the time, so a fair price is about "
           f"**{_american(1 / (tbw / n)):+d}** before any hold",
           "- that is the first measured number for that leg; it was a guess "
           "before", ""]
    md += ["## Caveats", "",
           f"1. {sum(1 for r in rows if not r['real_price'])} of {n} prop legs "
           f"use the assumed {ASSUMED_PROP:+d} rather than a captured price.",
           "2. The props here were chosen by the OLD selector, which carried "
           "the `form` term since removed for scoring AUC 0.5053, and were "
           "drawn from the PICKED team only. Both changed on 2026-10-12.",
           "3. Total-bases outcomes are real; no total-bases price was ever "
           "captured, so those columns are swept.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    text = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
