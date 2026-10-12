"""
Which MARKET on our hitters is best priced: 1+ hit, 2+ total bases, or 2+ H+R+RBI?

WHY THIS IS THE RIGHT QUESTION
`prop_grade` says the posted 1+ hit prop hits 62.8% and loses 5.8%, because at
-200 the break-even is 66.7%. The hit rate was never the problem; paying through
it was. So the question is not whether we can pick hitters - we can, within a
couple of points - but whether some OTHER market on the same hitter is sold at a
price his real rate clears.

WHAT CAN AND CANNOT BE BACK-TESTED, precisely
Every OUTCOME can. A boxscore gives hits, total bases, runs and RBIs for every
hitter in every game, all season. `hrr_shadow` says H+R+RBI "cannot be
back-tested" and that is true only of its PRICE - the outcome has been sitting
in the boxscores the whole time, and the outcome is the half that decides
whether the read transfers.

Prices are partial, and this uses what exists rather than assuming:
  1+ hit ......... real, from the cached `batter_hits` boards
  2+ H+R+RBI ..... real, from the cached `batter_hits_runs_rbis` boards
  2+ total bases . NONE ever captured, so only a FAIR price is reported

THE SELECTOR PICKS THE PLAYER, THIS PICKS THE MARKET
Quality is defined once, on the HIT rate, because that is what the board's
selector actually estimates. The same hitters are then measured in all three
markets. That mirrors the real decision: having chosen a hitter, which of his
markets is worth taking?

ESTIMATOR DISCIPLINE, carried over from `parlay_structure`
Rates come from a HELD-OUT half of each hitter's games and are only applied to
the other half, and every correlation lift is read RELATIVE TO A PERMUTATION
NULL that carries the same selection bias. Both were learned the hard way there:
selecting on a rate and then using it as the expectation manufactured a 19%
anti-correlation out of nothing.

Read-only. Stakes nothing, enters no ledger. Writes output/leg_markets.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
from itertools import combinations
from pathlib import Path

from . import mlb_api, totals_signal

log = logging.getLogger("leg_markets")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPORT = OUTPUT_DIR / "leg_markets.md"
CACHE = OUTPUT_DIR / "leg_markets_cache.json"

QUALITY = 0.60        # hit-rate bar, the population the selector posts from
MIN_HALF = 6
PERM_RUNS = 80
SEED = 20261012

# market -> (label, how to score one hitter-game from [PA, H, TB, HRR])
MARKETS = {
    "hit": ("1+ hit", lambda r: r[1] >= 1),
    "tb2": ("2+ total bases", lambda r: r[2] >= 2),
    "hrr2": ("2+ hits+runs+RBIs", lambda r: r[3] >= 2),
}


def _dec(american: int) -> float:
    return american / 100 + 1 if american > 0 else 100 / abs(american) + 1


def _american(dec: float) -> int:
    return round((dec - 1) * 100) if dec >= 2 else -round(100 / (dec - 1))


def _be(american: int) -> float:
    return (abs(american) / (abs(american) + 100) if american < 0
            else 100 / (american + 100))


def _box(pk: int, cache: dict) -> dict:
    """{player_id: [PA, hits, total_bases, H+R+RBI, side]} for one game, cached.

    The SIDE is stored here rather than recovered later, so one fetch answers
    both "what did he do" and "who was he batting for" - an earlier version
    re-fetched the same boxscore to tag the side.

    Total bases is reconstructed (MLB serves no totalBases on the batting
    line): singles are hits minus extra-base hits, TB = 1B + 2*2B + 3*3B +
    4*HR.
    """
    key = str(pk)
    if key in cache:
        return cache[key]
    try:
        box = mlb_api._get(f"game/{pk}/boxscore")
    except Exception as exc:
        log.warning("boxscore %s failed: %s", pk, exc)
        return {}
    out: dict = {}
    for side in ("home", "away"):
        players = ((box.get("teams") or {}).get(side, {}).get("players") or {})
        for pid, p in players.items():
            bat = ((p.get("stats") or {}).get("batting") or {})
            pa = int(bat.get("plateAppearances", 0) or 0)
            if pa < 1:
                continue
            h = int(bat.get("hits", 0) or 0)
            d = int(bat.get("doubles", 0) or 0)
            t = int(bat.get("triples", 0) or 0)
            hr = int(bat.get("homeRuns", 0) or 0)
            runs = int(bat.get("runs", 0) or 0)
            rbi = int(bat.get("rbi", 0) or 0)
            tb = max(0, h - d - t - hr) + 2 * d + 3 * t + 4 * hr
            out[pid.replace("ID", "")] = [pa, h, tb, h + runs + rbi, side]
    cache[key] = out
    return out


def collect() -> list[dict]:
    """One row per hitter-game on every FINAL board game."""
    try:
        cache = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        cache = {}
    try:
        scores = json.loads(totals_signal.SCORES.read_text())
    except (OSError, ValueError):
        scores = {}
    rows, dirty = [], False
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        day_scores = scores.get(date) or {}
        try:
            day = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        for g in day.get("games", []):
            pk = str(g.get("game_pk"))
            if pk not in day_scores:
                continue                      # not final
            before = pk in cache
            lines = _box(int(pk), cache)
            dirty = dirty or not before
            if not lines:
                continue
            away, home = (g.get("matchup") or " @ ").split(" @ ")
            for pid, rec in lines.items():
                if len(rec) < 5:
                    continue                  # pre-side cache entry
                rows.append({"pk": pk, "date": date, "pid": pid,
                             "team": home if rec[4] == "home" else away,
                             "rec": rec})
    if dirty:
        try:
            OUTPUT_DIR.mkdir(exist_ok=True)
            CACHE.write_text(json.dumps(cache))
        except OSError as exc:
            log.warning("cache not written (%s)", exc)
    return rows


# --- the real prices we actually captured -------------------------------------

def captured_prices() -> dict:
    """{market: [american over-prices]} from the per-day odds caches.

    Only two of the three markets were ever cached. 2+ total bases has none,
    which is why it gets a fair price and no edge column.
    """
    out: dict = {"hit": [], "hrr2": []}
    for f in glob.glob(str(OUTPUT_DIR / "prop_odds_2026-*.json")):
        try:
            d = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        for game in d.values():
            if not isinstance(game, dict):
                continue
            for v in game.values():
                o = v.get("over") if isinstance(v, dict) else v
                if isinstance(o, int):
                    out["hit"].append(o)
    for f in glob.glob(str(OUTPUT_DIR / "prop_odds_hrr_2026-*.json")):
        try:
            d = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        for game in d.values():
            if not isinstance(game, dict):
                continue
            for v in game.values():
                o = v.get("over") if isinstance(v, dict) else None
                if isinstance(o, int):
                    out["hrr2"].append(o)
    return out


# --- rates, with the held-out-half discipline ---------------------------------

def split_rates(rows: list) -> tuple[dict, list]:
    """({hitter: {market: rate from his EVEN games}}, the ODD rows to measure).

    Nothing measured shares a game with the rate that judges it.
    """
    by_hitter: dict = {}
    for r in rows:
        by_hitter.setdefault(r["pid"], []).append(r)
    rates, measure = {}, []
    for pid, items in by_hitter.items():
        items.sort(key=lambda r: (r["date"], r["pk"]))
        even, odd = items[0::2], items[1::2]
        if len(even) < MIN_HALF or not odd:
            continue
        rates[pid] = {m: sum(1 for x in even if fn(x["rec"])) / len(even)
                      for m, (_lab, fn) in MARKETS.items()}
        measure += odd
    return rates, measure


def single_legs(measure: list, rates: dict, prices: dict) -> list[str]:
    """Each market's real rate for our kind of hitter, against its real price."""
    qual = [r for r in measure if rates.get(r["pid"], {}).get("hit", 0)
            >= QUALITY]
    md = ["## One leg at a time — the rate, and the price it is sold at", "",
          f"_Hitters are filtered ONCE on the held-out HIT rate at "
          f"{QUALITY:.0%}, the population the board's selector posts from, and "
          "then measured in all three markets. "
          f"**{len({r['pid'] for r in qual})}** hitters, "
          f"**{len(qual)}** hitter-games._", "",
          "| market | rate | fair price | real median price | it needs | "
          "edge |", "|---|---|---|---|---|---|"]
    for m, (label, fn) in MARKETS.items():
        if not qual:
            continue
        rate = sum(1 for r in qual if fn(r["rec"])) / len(qual)
        fair = _american(1 / rate) if rate > 0 else None
        got = prices.get(m) or []
        if got:
            med = int(st.median(got))
            need = _be(med)
            md.append(f"| {label} | **{rate:.1%}** | {fair:+d} | "
                      f"{med:+d} _(n={len(got)})_ | {need:.1%} | "
                      f"**{rate - need:+.1f} pts** |")
        else:
            md.append(f"| {label} | **{rate:.1%}** | {fair:+d} | "
                      "_never captured_ | — | — |")
    md += ["", "_`edge` is percentage POINTS of hit rate over the break-even "
           "the price demands. Multiply by roughly 1.5 to read it as ROI at a "
           "short price, or 2 at plus money._", ""]
    return md


# --- correlation, calibrated against the permutation null --------------------

def _lift(measure: list, rates: dict, market: str, k: int, same_team: bool,
          outcomes: dict | None = None) -> tuple:
    fn = MARKETS[market][1]
    by_game: dict = {}
    for r in measure:
        if rates.get(r["pid"], {}).get("hit", 0) < QUALITY:
            continue
        by_game.setdefault(r["pk"], {}).setdefault(r["team"], []).append(r)
    obs = exp = 0.0
    n = 0
    for pk, teams in by_game.items():
        if same_team:
            groups = [[(t, r) for r in members] for t, members in teams.items()]
        else:
            if len(teams) != 2:
                continue
            groups = [[(t, r) for t, members in teams.items()
                       for r in members]]
        for g in groups:
            if len(g) < k:
                continue
            for combo in combinations(g, k):
                if not same_team and len({c[0] for c in combo}) < 2:
                    continue
                got = [outcomes.get((pk, c[1]["pid"]), fn(c[1]["rec"]))
                       if outcomes else fn(c[1]["rec"]) for c in combo]
                obs += 1.0 if all(got) else 0.0
                p = 1.0
                for c in combo:
                    p *= rates[c[1]["pid"]][market]
                exp += p
                n += 1
    return (obs / n if n else None, exp / n if n else None, n)


def _permute(measure: list, market: str, rnd: random.Random) -> dict:
    """Each hitter keeps his own outcomes; only the GAME they came from moves."""
    fn = MARKETS[market][1]
    by_hitter: dict = {}
    for r in measure:
        by_hitter.setdefault(r["pid"], []).append(r)
    out = {}
    for pid, items in by_hitter.items():
        got = [fn(r["rec"]) for r in items]
        rnd.shuffle(got)
        for r, new in zip(items, got):
            out[(r["pk"], pid)] = new
    return out


def correlation(measure: list, rates: dict) -> list[str]:
    md = ["## Do two of them on the same team co-move?", "",
          "_A parlay is priced as if its legs are independent, so a positive "
          "lift is the only thing that makes one better than its legs. Read "
          "**vs null**: the raw ratio carries the quality filter's winner's "
          "curse, the permutation null carries the identical bias and differs "
          "only in which game each outcome came from, so the ratio of the two "
          "is the part that is actually correlation._", "",
          "| market | legs | pairing | combos | observed | independent | "
          "vs null |", "|---|---|---|---|---|---|---|"]
    rnd = random.Random(SEED)
    for market, (label, _fn) in MARKETS.items():
        perms = [_permute(measure, market, rnd) for _ in range(PERM_RUNS)]
        for k in (2, 3):
            for same in (True, False):
                o, e, n = _lift(measure, rates, market, k, same)
                if o is None or not e or n < 50:
                    continue
                null = []
                for pm in perms:
                    po, pe, _n = _lift(measure, rates, market, k, same,
                                       outcomes=pm)
                    if po is not None and pe:
                        null.append(po / pe)
                if not null:
                    continue
                vs = (o / e) / st.mean(null)
                md.append(f"| {label} | {k} | "
                          + ("same team" if same else "opposite") +
                          f" | {n} | {o:.2%} | {e:.2%} | **×{vs:.3f}** |")
    return md + [""]


def parlays(measure: list, rates: dict, prices: dict) -> list[str]:
    """Each market as a 2- and 3-leg same-team parlay, against its real price."""
    md = ["## The same-team parlay, market by market", "",
          "_True joint probability from the observed rate, against what the "
          "real median price demands once it is multiplied. The total-bases "
          "row has no real price, so it is omitted rather than guessed._", "",
          "| market | legs | true P(all) | price | needs | ROI |",
          "|---|---|---|---|---|---|"]
    rnd = random.Random(SEED + 7)
    for market, (label, _fn) in MARKETS.items():
        got = prices.get(market) or []
        if not got:
            continue
        med = int(st.median(got))
        perms = [_permute(measure, market, rnd) for _ in range(PERM_RUNS)]
        for k in (2, 3):
            o, e, n = _lift(measure, rates, market, k, True)
            if o is None or not e or n < 50:
                continue
            null = [po / pe for po, pe, _ in
                    (_lift(measure, rates, market, k, True, outcomes=pm)
                     for pm in perms) if po is not None and pe]
            if not null:
                continue
            cal = (o / e) / st.mean(null)
            base = sum(1 for r in measure
                       if rates.get(r["pid"], {}).get("hit", 0) >= QUALITY
                       and MARKETS[market][1](r["rec"]))
            tot = sum(1 for r in measure
                      if rates.get(r["pid"], {}).get("hit", 0) >= QUALITY)
            rate = base / tot if tot else 0
            p_all = rate ** k * cal
            dec = _dec(med) ** k
            md.append(f"| {label} | {k} | {p_all:.2%} | "
                      f"{_american(dec):+d} | {1 / dec:.2%} | "
                      f"**{p_all * dec - 1:+.1%}** |")
    return md + [""]


def price_matched(rows: list, rates: dict) -> list[str]:
    """The decisive check on H+R+RBI: each CAPTURED price against the rate of
    the hitter it was actually quoted for.

    The table above pairs a rate measured on QUALITY hitters with a median
    price taken over EVERY hitter the book listed, weak ones included. Good
    hitters are priced shorter, so that mismatch alone would manufacture an
    edge. This removes it by resolving each quoted name to the player and
    using his own held-out rate against his own price.
    """
    md = ["## The decisive check: each captured price against ITS OWN hitter",
          "",
          "_The table above pairs a rate measured on QUALITY hitters with a "
          "median price taken over EVERY hitter the book listed. Good hitters "
          "are priced shorter, so that mismatch alone could manufacture the "
          "edge. Here each quoted name is resolved to the player and scored "
          "against his own held-out rate._", ""]
    # name -> pid, from the boxscores of the dates that have captured prices
    dates = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "prop_odds_hrr_2026-*.json"))):
        dates.append(Path(f).stem.split("prop_odds_hrr_")[1])
    name_to_pid: dict = {}
    pks_by_date: dict = {}
    for r in rows:
        pks_by_date.setdefault(r["date"], set()).add(r["pk"])
    for date in dates:
        for pk in pks_by_date.get(date, ()):
            try:
                box = mlb_api._get(f"game/{pk}/boxscore")
            except Exception:
                continue
            for side in ("home", "away"):
                for pid, pl in (((box.get("teams") or {}).get(side, {})
                                 .get("players")) or {}).items():
                    nm = ((pl.get("person") or {}).get("fullName") or "")
                    if nm:
                        name_to_pid[totals_signal._norm(nm)] = \
                            pid.replace("ID", "")
    matched, unmatched = [], 0
    for date in dates:
        try:
            d = json.loads((OUTPUT_DIR
                            / f"prop_odds_hrr_{date}.json").read_text())
        except (OSError, ValueError):
            continue
        for game in d.values():
            if not isinstance(game, dict):
                continue
            for nm, v in game.items():
                o = v.get("over") if isinstance(v, dict) else None
                if not isinstance(o, int):
                    continue
                pid = name_to_pid.get(totals_signal._norm(nm))
                rate = (rates.get(pid) or {}).get("hrr2") if pid else None
                if rate is None:
                    unmatched += 1
                    continue
                matched.append({"name": nm, "price": o, "rate": rate,
                                "need": _be(o)})
    if len(matched) < 10:
        return md + [f"- only {len(matched)} prices resolved to a measured "
                     f"hitter ({unmatched} unresolved); not decidable.", ""]
    edges = [m["rate"] - m["need"] for m in matched]
    beat = sum(1 for e in edges if e > 0)
    md += [f"- captured prices resolved to a measured hitter: "
           f"**{len(matched)}** ({unmatched} unresolved)",
           f"- median price **{int(st.median(m['price'] for m in matched)):+d}**, "
           f"median rate **{st.median(m['rate'] for m in matched):.1%}**",
           f"- **mean edge: {st.mean(edges):+.1f} points** "
           f"(median {st.median(edges):+.1f})",
           f"- prices the hitter's own rate beat: **{beat}/{len(matched)}**",
           ""]
    md += ["| hitter | price | needs | his rate | edge |",
           "|---|---|---|---|---|"]
    for m in sorted(matched, key=lambda x: -(x["rate"] - x["need"]))[:12]:
        md.append(f"| {m['name'].title()} | {m['price']:+d} | "
                  f"{m['need']:.1%} | {m['rate']:.1%} | "
                  f"**{m['rate'] - m['need']:+.1f} pts** |")
    md.append("")
    md.append("- " + ("**the edge survives price-matching**, so the market "
                      "table above is not a population artifact"
                      if st.mean(edges) > 0.02 else
                      "**the edge does NOT survive price-matching** — the "
                      "apparent H+R+RBI edge was the mismatch between a "
                      "quality-filtered rate and an all-hitters median price"
                      if st.mean(edges) < 0 else
                      "**inconclusive at this sample** — the mean edge is "
                      "inside noise, and 42 captured prices from four October "
                      "dates cannot settle it"))
    return md + [""]


def build() -> str:
    rows = collect()
    md = ["# Which market on our hitters is actually worth taking?", "",
          "_Read-only. Stakes nothing, enters no ledger. Every OUTCOME is "
          "graded from a boxscore; prices are the ones actually captured, and "
          "the market with no captured price says so._", ""]
    if len(rows) < 500:
        return "\n".join(md + [f"- only {len(rows)} hitter-games; not "
                               "measurable.", ""])
    rates, measure = split_rates(rows)
    md += [f"- hitter-games on final board games: **{len(rows)}** across "
           f"**{len({r['pk'] for r in rows})}** games",
           f"- hitters with both halves usable: **{len(rates)}**; measured on "
           f"**{len(measure)}** held-out hitter-games", ""]
    prices = captured_prices()
    md += single_legs(measure, rates, prices)
    md += correlation(measure, rates)
    md += parlays(measure, rates, prices)
    md += price_matched(rows, rates)
    md += ["## Caveats", "",
           "1. Prices are the MEDIAN of what was captured, not what was "
           "available on each individual night, so a single leg's real edge "
           "varies around the number shown.",
           "2. 2+ total bases has no captured price anywhere in the repo. Its "
           "rate is real; whether it is sold near fair is unknown, and that "
           "is the one thing worth capturing next.",
           "3. Hitters are filtered on their HIT rate for every market, "
           "because that is what the selector estimates. A selector built for "
           "total bases or H+R+RBI would pick different hitters and could do "
           "better than these numbers.", ""]
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
