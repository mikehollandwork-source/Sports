"""
Back-test the four-leg ticket: how often would it actually have hit?

WHAT IS RECONSTRUCTED
For every past board game that was a PLAY, the legs the current rules would
pick: the moneyline pick, two DIFFERENT hitters for 1+ hit, and 2+ total bases
for the power model's hitter. Every leg is then graded from the boxscore, so the
OUTCOMES are real.

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
    """One reconstructed ticket per past PLAY whose legs all grade."""
    try:
        cache = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        cache = {}
    tickets, dirty = [], False
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
            if not team or not isinstance(ml, int):
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
            if not lines:
                continue

            # TB leg: the HR pick, reserved before the hits legs
            hp = pc.get("hr_prop") or {}
            tb_id = hp.get("player_id")
            tb_who = hp.get("player")
            reserved = {tb_id} if tb_id else set()

            # hits legs: two distinct hitters from the archival pool
            hits_legs = []
            posted = pc.get("props") or ([pc["prop"]] if pc.get("prop") else [])
            pool = posted + [b for b in (pc.get("hit_bats") or [])
                             if b.get("player_id")
                             not in {x.get("player_id") for x in posted}]
            for b in pool:
                if len(hits_legs) >= 2:
                    break
                pid = b.get("player_id")
                if not pid or pid in reserved or \
                        pid in {x["player_id"] for x in hits_legs}:
                    continue
                if str(pid) not in lines:
                    continue          # did not bat: not a graded leg
                hits_legs.append({
                    "player_id": pid, "player": b.get("player"),
                    "odds": int(b["odds"]) if isinstance(b.get("odds"), int)
                    else ASSUMED_PROP,
                    "real_price": isinstance(b.get("odds"), int),
                    "won": lines[str(pid)][0] >= 1})
            if len(hits_legs) < 2:
                continue
            if not tb_id:
                # no HR pick: the next unused bat, same rule as live
                for b in pool:
                    pid = b.get("player_id")
                    if pid and pid not in {x["player_id"] for x in hits_legs} \
                            and str(pid) in lines:
                        tb_id, tb_who = pid, b.get("player")
                        break
            if not tb_id or str(tb_id) not in lines:
                continue
            tickets.append({
                "date": date, "game_pk": pk, "matchup": g.get("matchup"),
                "ml": {"team": team, "odds": ml,
                       "won": r.get("winner") == team},
                "hits": hits_legs,
                "tb": {"player_id": tb_id, "player": tb_who,
                       "won": lines[str(tb_id)][1] >= 2,
                       "real_price": False}})
    if dirty:
        try:
            OUTPUT_DIR.mkdir(exist_ok=True)
            CACHE.write_text(json.dumps(cache))
        except OSError as exc:
            log.warning("cache not written (%s)", exc)
    return tickets


def _roi(tickets: list, legs: tuple, tb_price: int) -> tuple:
    """(wins, n, roi, mean parlay price) for a structure built from `legs`."""
    wins = n = 0
    profit = 0.0
    prices = []
    for t in tickets:
        dec = 1.0
        ok = True
        if "ml" in legs:
            dec *= _dec(t["ml"]["odds"])
            ok = ok and t["ml"]["won"]
        for i in range(legs.count("hits")):
            dec *= _dec(t["hits"][i]["odds"])
            ok = ok and t["hits"][i]["won"]
        if "tb" in legs:
            dec *= _dec(tb_price)
            ok = ok and t["tb"]["won"]
        n += 1
        prices.append(dec)
        if ok:
            wins += 1
            profit += STAKE * (dec - 1)
        else:
            profit -= STAKE
    if not n:
        return 0, 0, None, None
    return wins, n, profit / (n * STAKE), sum(prices) / len(prices)


def build() -> str:
    tickets = collect()
    md = ["# Back-testing the four-leg ticket", "",
          "_Read-only. Stakes nothing, enters no ledger. Every leg's OUTCOME is "
          "graded from the boxscore; the caveats on PRICES are below the "
          "numbers that depend on them._", ""]
    if len(tickets) < 20:
        return "\n".join(md + [f"- only {len(tickets)} reconstructable "
                               "tickets; not measurable.", ""])
    md += [f"- reconstructed tickets (past PLAYS with four gradeable legs): "
           f"**{len(tickets)}**",
           f"- dates: **{tickets[0]['date']} to {tickets[-1]['date']}**", ""]

    # leg by leg - the part that needs no price at all
    ml_w = sum(1 for t in tickets if t["ml"]["won"])
    h1 = sum(1 for t in tickets if t["hits"][0]["won"])
    h2 = sum(1 for t in tickets if t["hits"][1]["won"])
    tb_w = sum(1 for t in tickets if t["tb"]["won"])
    both_h = sum(1 for t in tickets
                 if t["hits"][0]["won"] and t["hits"][1]["won"])
    allf = sum(1 for t in tickets if t["ml"]["won"] and t["tb"]["won"]
               and t["hits"][0]["won"] and t["hits"][1]["won"])
    n = len(tickets)
    md += ["## Leg by leg — no price needed", "",
           "| leg | hit | rate |", "|---|---|---|",
           f"| moneyline pick | {ml_w}/{n} | **{ml_w / n:.1%}** |",
           f"| 1+ hit, first hitter | {h1}/{n} | **{h1 / n:.1%}** |",
           f"| 1+ hit, second hitter | {h2}/{n} | **{h2 / n:.1%}** |",
           f"| 2+ total bases | {tb_w}/{n} | **{tb_w / n:.1%}** |", "",
           f"- both hit legs together: **{both_h}/{n} = {both_h / n:.1%}** "
           f"(independent would be {h1 / n * h2 / n:.1%}, so the same-game "
           f"lift is **×{(both_h / n) / (h1 / n * h2 / n):.3f}**)",
           f"- **ALL FOUR legs: {allf}/{n} = {allf / n:.1%}**", ""]

    # what any price would have to be
    md += ["## What the structure returns", "",
           "_The total-bases price was never captured, so it is swept. "
           "Moneyline prices are real; hit props are real where the board "
           "captured one and `-200` otherwise._", "",
           "| structure | assumed TB price | wins | mean price | ROI |",
           "|---|---|---|---|---|"]
    rows = [(("ml", "hits", "hits", "tb"), "4 legs — the full ticket"),
            (("ml", "hits", "hits"), "3 legs — drop total bases"),
            (("hits", "hits", "tb"), "3 legs — drop the moneyline"),
            (("ml", "hits"), "2 legs — ML + one hit"),
            (("hits", "hits"), "2 legs — two hits")]
    for legs, label in rows:
        for tbp in (TB_PRICES if "tb" in legs else (TB_MAIN,)):
            w, nn, roi, mp = _roi(tickets, legs, tbp)
            if roi is None:
                continue
            md.append(f"| {label} | "
                      + (f"{tbp:+d}" if "tb" in legs else "—")
                      + f" | {w}/{nn} ({w / nn:.1%}) | "
                      f"{_american(mp):+d} | **{roi:+.1%}** |")
    md += ["", "## Which leg does the damage", ""]
    worst = min((("moneyline", ml_w / n), ("first hit", h1 / n),
                 ("second hit", h2 / n), ("total bases", tb_w / n)),
                key=lambda x: x[1])
    md += [f"- the lowest-rate leg is **{worst[0]}** at {worst[1]:.1%}",
           f"- dropping total bases moves the ticket from "
           f"{_roi(tickets, ('ml', 'hits', 'hits', 'tb'), TB_MAIN)[2]:+.1%} to "
           f"{_roi(tickets, ('ml', 'hits', 'hits'), TB_MAIN)[2]:+.1%}",
           f"- dropping the moneyline instead moves it to "
           f"{_roi(tickets, ('hits', 'hits', 'tb'), TB_MAIN)[2]:+.1%}", "",
           "## Caveats that bound all of the above", "",
           "1. Historical boards posted ONE prop, so the two hit legs are "
           "reconstructed from `hit_bats`, the archival top-of-pool ranked by "
           "the OLD selector - which still carried the `form` term since "
           "removed for scoring AUC 0.5053. This measures the STRUCTURE, not "
           "today's selector.",
           "2. The total-bases price is assumed, not captured. Its OUTCOME is "
           "real.",
           f"3. {sum(1 for t in tickets for h in t['hits'] if h['real_price'])}"
           f" of {2 * n} hit legs carry a real captured price; the rest use "
           f"{ASSUMED_PROP:+d}.", ""]
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
