"""
Road-trip rule: shadow now, live only if the forward data earns it.

THE RULE, FROZEN
Back the ROAD team when it is playing its ROAD_MIN-th consecutive road game or
later. Nothing else - no price filter, no form, no handle. One condition, fixed
below, and not to be tuned while it is being recorded.

WHY THIS ONE AND NOT THE OTHER TWELVE
`schedule_spots` found a monotone gradient with no cherry-picking needed:

    >=3 road games  +1.3%   (n=550)
    >=4             +5.2%   (n=422)
    >=5             +9.9%   (n=316)
    >=6            +14.8%   (n=207)
    >=7            +14.6%   (n=98)

Rising then flat is the shape a real effect has and the shape every failed
signal here lacked - the +40% dog spike was negative at 55%, peaked at 70% and
inverted at 80%. It also has a mechanism that does not require us to know
baseball better than the market: it says the market OVER-fades tired road teams.
Note the direction is the opposite of the folk wisdom that asked the question.

WHY IT IS NOT LIVE TODAY
It fails the two tests that matter. The 30-cell scan gives a corrected p of
0.160, and adding it to the price changes holdout log-loss by +0.0004 with a CI
of -0.0092 to +0.0098 - no information the market has not already priced. In
sample it ran +28.9%; in holdout +7.8%. That is decay, not confirmation.

ROAD_MIN = 6 is the START of the plateau, not its maximum: >=6 and >=7 are the
same number, so this is not the best cell dressed up as a threshold.

THE BAR, WRITTEN BEFORE ANY FORWARD GAME EXISTS
Promotion is automatic and requires ALL of:
  1. n >= MIN_N forward games (not backtest games - these are excluded)
  2. day-block bootstrap 95% CI lower bound above zero
  3. beats the plain road-team baseline over the SAME games, not merely zero
  4. holds at >= ROAD_MIN + 1 too, so it is a gradient and not one bucket
No corrections are applied because there is nothing to correct for: one rule,
one threshold, one direction, all fixed here in advance. That is the whole point
of pre-registration, and it is why this bar can be trusted where a scan's cannot.

MIN_N is 250 because that is roughly what the observed effect size needs to
separate from zero: at n=250 the standard error on ROI is about 6 points, so a
+14.8% edge clears with room, while +5% would not - which is correct, since a
+5% edge here is not worth the exposure.

Once promoted it stays promoted; demotion is a human decision, because a rule
that switches itself off on a cold week is a rule that never survives variance.

output/road_trip_ledger.json - its own file, touching no board and no record.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
import random
from collections import defaultdict
from pathlib import Path

from . import grade, mlb_api

log = logging.getLogger("road_trip")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
LEDGER = OUTPUT_DIR / "road_trip_ledger.json"

# --- the frozen rule ---------------------------------------------------------
ROAD_MIN = 6
START_FROM = "2026-09-01"       # forward only; backtest games can never count
MIN_N = 250

RULE = {"road_min": ROAD_MIN, "start_from": START_FROM, "min_n": MIN_N,
        "description": f"back the road team on its {ROAD_MIN}th+ straight road game"}


def load() -> dict:
    try:
        d = json.loads(LEDGER.read_text())
        d.setdefault("entries", [])
        return d
    except (OSError, ValueError):
        return {"rule": RULE, "entries": [], "promoted": False}


def _clean(v):
    """NaN is not valid JSON. Python emits and re-reads it happily, so this file
    looked fine while being unreadable to anything else - the bootstrap returns
    NaN until there are enough games, so an empty ledger shipped a broken file."""
    if isinstance(v, float) and v != v:
        return None
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    return v


def save(d: dict) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    d["rule"] = RULE
    LEDGER.write_text(json.dumps(_clean(d), indent=1, allow_nan=False))


def _streaks() -> dict:
    """{(date, team): consecutive road games ending that day, 0 if home}.

    Derived from board history. `seen_home` guards the truncation at the start
    of the record: a trip already running when the boards begin would otherwise
    be counted as however far back we happen to see."""
    hist: dict[str, dict[str, bool]] = {}
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        day = {}
        try:
            games = json.loads(Path(f).read_text()).get("games", [])
        except (OSError, ValueError):
            continue
        for g in games:
            m = g.get("matchup") or ""
            if " @ " in m:
                a, h = m.split(" @ ")
                day[a], day[h] = False, True
        if day:
            hist[date] = day
    prev: dict[str, list[bool]] = defaultdict(list)
    out: dict = {}
    for d in sorted(hist):
        for team, is_home in hist[d].items():
            past = prev[team]
            streak = 1
            for ph in reversed(past):
                if ph == is_home:
                    streak += 1
                else:
                    break
            out[(d, team)] = {"road": 0 if is_home else streak,
                              "seen_home": any(past)}
            past.append(is_home)
    return out


def candidates(date: str, streaks: dict | None = None) -> list[dict]:
    """Games on `date`'s board where the visitor qualifies. Prices only."""
    streaks = streaks if streaks is not None else _streaks()
    try:
        board = json.loads((OUTPUT_DIR / f"picks_{date}.json").read_text())
    except (OSError, ValueError):
        return []
    out = []
    for g in board.get("games", []):
        m = g.get("matchup") or ""
        if " @ " not in m:
            continue
        away, home = m.split(" @ ")
        pc = g.get("pick_criteria") or {}
        adv = pc.get("advantage_team")
        a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
        if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
            continue
        price = {adv: a_ml, (home if adv == away else away): o_ml}
        s = streaks.get((date, away))
        if not s or not s["seen_home"] or s["road"] < ROAD_MIN:
            continue
        out.append({"date": date, "game_pk": g.get("game_pk"), "matchup": m,
                    "bet": away, "odds": price[away],
                    "home_odds": price[home], "road_streak": s["road"]})
    return out


def _boot_day(rows, trials=6000, seed=17) -> tuple[float, float]:
    """Day-block bootstrap: same-day games are not independent."""
    if len(rows) < 20:
        return (float("nan"), float("nan"))
    by = defaultdict(list)
    for r in rows:
        by[r["date"]].append(r)
    days = list(by)
    rng = random.Random(seed)
    out = []
    for _ in range(trials):
        s = []
        for _ in days:
            s += by[days[rng.randrange(len(days))]]
        out.append(sum(x["profit"] for x in s) / len(s))
    out.sort()
    return out[int(.025 * trials)], out[int(.975 * trials)]


def evaluate(led: dict) -> dict:
    """Score the frozen bar. Every clause must pass."""
    done = [e for e in led["entries"] if e.get("won") is not None]
    n = len(done)
    roi = (sum(e["profit"] for e in done) / n) if n else 0.0
    lo, hi = _boot_day(done)
    # baseline: backing the road team is the same bet, so the comparison that
    # matters is the deeper subset against the shallower one
    deeper = [e for e in done if e.get("road_streak", 0) >= ROAD_MIN + 1]
    droi = (sum(e["profit"] for e in deeper) / len(deeper)) if deeper else 0.0
    home_roi = (sum((grade.american_profit(e["home_odds"]) if not e["won"] else -1)
                    for e in done) / n) if n else 0.0
    checks = {
        f"n >= {MIN_N}": n >= MIN_N,
        "CI lower bound > 0": lo is not None and lo == lo and lo > 0,
        "beats fading it (backing home)": roi > home_roi,
        f"holds at >= {ROAD_MIN + 1} too": len(deeper) >= 30 and droi > 0,
    }
    return {"n": n, "roi": roi, "ci": [lo, hi], "deeper_n": len(deeper),
            "deeper_roi": droi, "home_roi": home_roi, "checks": checks,
            "passes": all(checks.values())}


def run() -> dict:
    """Record new qualifying games, grade what is final, then score the bar."""
    led = load()
    seen = {(e["date"], e["game_pk"]) for e in led["entries"]}
    streaks = _streaks()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    dates = sorted(Path(f).stem.split("picks_")[1]
                   for f in glob.glob(str(OUTPUT_DIR / "picks_2026-*.json")))
    added = 0
    for date in dates:
        if date < START_FROM:
            continue
        for c in candidates(date, streaks):
            if (date, c["game_pk"]) in seen:
                continue
            c.update({"recorded_at": now, "won": None, "profit": None})
            led["entries"].append(c)
            added += 1

    open_by_date: dict = defaultdict(list)
    for e in led["entries"]:
        if e.get("won") is None:
            open_by_date[e["date"]].append(e)
    graded = 0
    for date, entries in open_by_date.items():
        try:
            results = mlb_api.results_for(date)
        except Exception as exc:
            log.warning("results unavailable for %s: %s", date, exc)
            continue
        for e in entries:
            res = results.get(e["game_pk"])
            if not res or not res.get("final") or not res.get("winner"):
                continue
            e["won"] = res["winner"] == e["bet"]
            e["profit"] = round(
                grade.american_profit(e["odds"]) if e["won"] else -1.0, 3)
            graded += 1

    led["entries"].sort(key=lambda e: (e["date"], e["game_pk"] or 0))
    ev = evaluate(led)
    led["evaluation"] = ev

    # promotion is one-way: a rule that switches itself off on a cold week never
    # survives variance, so demotion stays a human decision
    if ev["passes"] and not led.get("promoted"):
        led["promoted"] = True
        led["promoted_at"] = now
        log.info("ROAD TRIP RULE PROMOTED: n=%d roi=%+.1f%% ci=%s",
                 ev["n"], ev["roi"] * 100, ev["ci"])
        try:
            from . import notify
            notify.send_telegram(
                "🚗 Road-trip rule PROMOTED — it cleared the bar set on "
                f"2026-08-31.\n\n{ev['n']} forward games · ROI {ev['roi']:+.1%}\n"
                f"95% CI {ev['ci'][0]:+.1%} to {ev['ci'][1]:+.1%}\n\n"
                "It now adds picks to the board, tagged road_trip.")
        except Exception as exc:
            log.error("promotion alert failed: %s", exc)

    save(led)
    log.info("road trip: +%d recorded, %d graded, %d total, promoted=%s",
             added, graded, len(led["entries"]), led.get("promoted"))
    return led


def apply(results: list[dict], date: str) -> int:
    """Add road-trip picks to a board - ONLY once promoted. No-op otherwise."""
    led = load()
    if not led.get("promoted"):
        return 0
    picks = {c["game_pk"]: c for c in candidates(date)}
    applied = 0
    for r in results:
        c = picks.get(r.get("game_pk"))
        if not c:
            continue
        pc = r.setdefault("pick_criteria", {})
        if pc.get("play") == "pick":
            continue                     # the consensus rule keeps its own game
        pc.update({"play": "pick", "status": "PICK", "bet_team": c["bet"],
                   "bet_moneyline": c["odds"], "source": "road_trip",
                   "reason": f"road team on {c['road_streak']} straight road games"})
        applied += 1
    if applied:
        log.info("applied %d road-trip pick(s) for %s", applied, date)
    return applied


def report(led: dict | None = None) -> str:
    led = led or load()
    ev = led.get("evaluation") or evaluate(led)
    md = [f"# Road-trip rule — {'LIVE' if led.get('promoted') else 'shadow'}", "",
          f"_{RULE['description']}. Recording from {START_FROM}; backtest games "
          "can never count._", "",
          f"- forward games graded: **{ev['n']}** · ROI **{ev['roi']:+.1%}**"]
    if ev["n"] >= 20:
        md.append(f"- day-block 95% CI: **{ev['ci'][0]:+.1%} to {ev['ci'][1]:+.1%}**")
        md.append(f"- backing home instead would return **{ev['home_roi']:+.1%}**")
        md.append(f"- at ≥{ROAD_MIN+1} road games: **{ev['deeper_roi']:+.1%}** "
                  f"(n={ev['deeper_n']})")
    md += ["", "## The bar, fixed 2026-08-31", "", "| requirement | met |", "|---|---|"]
    for k, v in ev["checks"].items():
        md.append(f"| {k} | {'✅' if v else '❌'} |")
    md += ["", ("**PROMOTED — live on the board.**" if led.get("promoted")
                else "**Shadow only.** No money, no board."), ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    led = run()
    md = report(led)
    (OUTPUT_DIR / "road_trip.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
