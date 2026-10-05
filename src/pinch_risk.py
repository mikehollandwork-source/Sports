"""
How often is this hitter pulled out of a game he started?

THE HARM
A hits prop needs plate appearances. A hitter lifted in the sixth got two, and
the prop was dead before first pitch. On 2026-10-04 the Braves did it twice in
one game: Murphy out after 2 PA, Thomas out after 2.

WHY THE EXISTING GATE MISSES IT
`props.MIN_AVG_PA` is a MEAN - 3.2 PA across the team wins he played in. A mean
cannot express "ever pinch-hit for": a hitter who finishes 85% of his starts and
is lifted in the other 15% averages about 4.0 and sails through, while being
exactly the risk worth avoiding. What matters is the SHARE of starts that end
early, not the average length of one.

HOW IT IS DETECTED
From the boxscore, not inferred from plate appearances. Every batter carries a
`battingOrder`: a starter's ends in "00" (100, 200 ... 900) and anyone who
replaces him in that slot gets the next number up with `isSubstitute` true. So
slot 7 reading 700 / 701 / 702 means the starter was replaced, and no guessing
from a short line is needed. A first attempt tried to infer it from PA and
returned 0.0% for all 414 hitters - including Murphy, who had been pulled the
day before - because it skipped games under 3 PA and then looked for games of 2
PA or fewer among what was left.

This counts ANY replacement in the slot, not only a pinch hitter: a pinch
runner or a defensive sub ends the starter's night just as finally, and kills a
hits prop just as completely.

COST
One request per game, so the tally is cached by gamePk and refreshed
incrementally - a full season once, then roughly fifteen boxscores a day. The
board calls `refresh()` before building props.

`risk()` returns None under MIN_STARTS, and the gate LETS THOSE THROUGH:
unknown is not risky, and a feed outage must not silently empty the board.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from . import mlb_api

log = logging.getLogger("pinch_risk")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
CACHE = OUTPUT_DIR / "pinch_risk_cache_v2.json"   # v2 stores per-start rows
REPORT = OUTPUT_DIR / "pinch_risk.md"

MIN_STARTS = 20        # starts before a rate is worth acting on
SEASON_START = "03/01"


def _load() -> dict:
    try:
        d = json.loads(CACHE.read_text())
        d.setdefault("games", [])
        d.setdefault("starts", {})
        return d
    except (OSError, ValueError):
        return {"games": [], "starts": {}}


def _save(cache: dict) -> None:
    try:
        CACHE.write_text(json.dumps(cache))
    except OSError as exc:
        log.warning("pinch-risk cache not written (%s)", exc)


def _scan(game_pk: int, starts: dict, date: str = "") -> bool:
    """Record one final game's starters. False if it could not be read.

    A starter is battingOrder ending "00" with isSubstitute false; he was pulled
    if any other entry shares his slot (the same leading digit).

    Stores PER START - [date, PA, pulled, opposing starter hand] - rather than a
    running count, because a count cannot tell a costly pull from a harmless
    one. A defensive sub in the ninth, after the starter has had four plate
    appearances, scores the same as a pinch hitter in the fifth, and only the
    second one costs the prop anything.
    """
    try:
        bs = mlb_api._get(f"game/{game_pk}/boxscore")
    except Exception as exc:
        log.warning("boxscore %s unavailable (%s)", game_pk, exc)
        return False
    opp_sp = {}
    for side in ("away", "home"):
        team = ((bs.get("teams") or {}).get(side) or {})
        pitchers = team.get("pitchers") or []
        opp_sp["home" if side == "away" else "away"] = (
            pitchers[0] if pitchers else None)
    for side in ("away", "home"):
        players = ((bs.get("teams") or {}).get(side) or {}).get("players") or {}
        slots: dict[str, list[tuple[int, int, bool, float]]] = {}
        for p in players.values():
            bo = p.get("battingOrder")
            pid = (p.get("person") or {}).get("id")
            if not bo or not pid:
                continue
            try:
                n = int(bo)
            except (TypeError, ValueError):
                continue
            sub = bool((p.get("gameStatus") or {}).get("isSubstitute"))
            try:
                pa = float(((p.get("stats") or {}).get("batting")
                            or {}).get("plateAppearances", 0) or 0)
            except (TypeError, ValueError):
                pa = 0.0
            slots.setdefault(str(n // 100), []).append((n, pid, sub, pa))
        for entries in slots.values():
            entries.sort()
            n, pid, sub, pa = entries[0]
            if n % 100 != 0 or sub:
                continue                    # not a starter; skip the slot
            starts.setdefault(str(pid), []).append(
                [date, pa, 1 if len(entries) > 1 else 0, opp_sp.get(side)])
    return True


def refresh(through: str, limit: int | None = None) -> dict:
    """Bring the cache up to the day before `through` (YYYY-MM-DD).

    Only FINAL games are scanned, and each gamePk is scanned once, so calling
    this on every board build costs one request per newly finished game.
    """
    cache = _load()
    done = set(cache["games"])
    season = through[:4]
    try:
        sched = mlb_api._get("schedule", sportId=1, gameType="R,P",
                             startDate=f"{SEASON_START}/{season}",
                             endDate=f"{through[5:7]}/{through[8:10]}/{season}")
    except Exception as exc:
        log.warning("schedule for pinch risk unavailable (%s)", exc)
        return cache
    pks = []
    for d in sched.get("dates", []):
        day = d.get("date") or ""
        if day >= through:
            continue                      # never let today inform today
        for g in d.get("games", []):
            state = ((g.get("status") or {}).get("abstractGameState") or "")
            if state == "Final" and g.get("gamePk") not in done:
                pks.append((g["gamePk"], day))
    if limit:
        pks = pks[:limit]
    added = 0
    for pk, day in pks:
        if _scan(pk, cache["starts"], day):
            cache["games"].append(pk)
            added += 1
    if added:
        log.info("pinch risk: scanned %d new boxscore(s)", added)
        _save(cache)
    return cache


def risk(pid: int, cache: dict | None = None) -> dict | None:
    """Short-night risk for one hitter, or None when the sample is too thin.

    `rate` is the measure the gate reads. Which measure that should BE was
    settled by `compare()` below rather than assumed - see MEASURE.
    """
    cache = _load() if cache is None else cache
    rows = (cache.get("starts") or {}).get(str(pid)) or []
    if len(rows) < MIN_STARTS:
        return None
    return summarise(rows)


SHORT_PA = 3          # a start this short cannot carry a hits prop


def summarise(rows: list) -> dict:
    """Every candidate measure over one hitter's starts, so they can be
    compared on the same rows instead of argued about."""
    n = len(rows)
    pulled = sum(1 for r in rows if r[2])
    short = sum(1 for r in rows if r[1] <= SHORT_PA)
    costly = sum(1 for r in rows if r[2] and r[1] <= SHORT_PA)
    recent = rows[-30:]
    rshort = sum(1 for r in recent if r[1] <= SHORT_PA)
    return {
        "starts": n,
        "pulled": pulled,
        "rate": short / n,                 # MEASURE: the one the gate reads
        "pull_rate": pulled / n,
        "short_rate": short / n,
        "costly_rate": costly / n,
        "mean_pa": sum(r[1] for r in rows) / n,
        "recent_short_rate": (rshort / len(recent)) if recent else None,
    }


# --- which measure is actually best? ------------------------------------------
MEASURES = {
    "short_rate (PA<=3)": lambda m: m["short_rate"],
    "pull_rate (any replacement)": lambda m: m["pull_rate"],
    "costly_rate (pulled AND short)": lambda m: m["costly_rate"],
    "mean PA per start (negated)": lambda m: -m["mean_pa"],
    "recent 30 short_rate": lambda m: (m["recent_short_rate"]
                                       if m["recent_short_rate"] is not None
                                       else m["short_rate"]),
}


def _auc(pairs: list[tuple[float, int]]) -> float | None:
    """P(a short night scores higher than a full one), ties counted half.

    Rank-based, so it is the Mann-Whitney statistic and needs no binning or
    threshold - which is the point, since the threshold is what comes after.
    """
    pos = [s for s, y in pairs if y]
    neg = [s for s, y in pairs if not y]
    if not pos or not neg:
        return None
    ordered = sorted(pairs, key=lambda t: t[0])
    ranks, i = {}, 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1][0] == ordered[i][0]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = r
        i = j + 1
    rank_pos = sum(r for k, r in ranks.items() if ordered[k][1])
    n1, n2 = len(pos), len(neg)
    return (rank_pos - n1 * (n1 + 1) / 2) / (n1 * n2)


def compare(cache: dict) -> list[str]:
    """Forward test: which measure best predicts a SHORT NIGHT tonight?

    For every start with at least MIN_STARTS prior ones, each measure is built
    from the PRIOR starts only and scored against what actually happened in
    that game. Strictly out of sample, and the same rows for every measure, so
    the comparison is like for like.
    """
    rows_by_measure: dict[str, list[tuple[float, int]]] = {k: [] for k in MEASURES}
    games = 0
    for _pid, starts in (cache.get("starts") or {}).items():
        starts = sorted(starts, key=lambda r: r[0])
        for i in range(MIN_STARTS, len(starts)):
            prior = starts[:i]
            m = summarise(prior)
            y = 1 if starts[i][1] <= SHORT_PA else 0
            games += 1
            for name, fn in MEASURES.items():
                rows_by_measure[name].append((fn(m), y))
    out = ["| measure | AUC |", "|---|---|"]
    scored = []
    for name, pairs in rows_by_measure.items():
        a = _auc(pairs)
        scored.append((a or 0.0, name))
        out.append(f"| {name} | {a:.4f} |" if a else f"| {name} | — |")
    scored.sort(reverse=True)
    base = games and sum(y for _, y in rows_by_measure[next(iter(MEASURES))]
                         ) / games
    return ([f"**{games} starts** judged, "
             f"{base:.1%} of them short (PA <= {SHORT_PA}).", "",
             "_AUC is the chance a short night scores above a full one. "
             "0.50 is a coin flip._", ""]
            + out
            + ["", f"**Best: {scored[0][1]} at AUC {scored[0][0]:.4f}.**", ""])


# --- the report the threshold is set from -------------------------------------
def build(through: str) -> str:
    cache = refresh(through)
    names = {}
    tally = cache.get("tally") or {}
    ids = [int(p) for p, c in tally.items() if c[1] >= MIN_STARTS]
    for i in range(0, len(ids), 100):
        try:
            for pe in mlb_api._get("people", personIds=",".join(
                    str(x) for x in ids[i:i + 100])).get("people", []):
                names[pe["id"]] = pe.get("fullName")
        except Exception as exc:
            log.warning("name lookup failed (%s)", exc)
    rows = [(names.get(i, str(i)), risk(i, cache)) for i in ids]
    rows = [(n, r) for n, r in rows if r]
    md = [f"# How often is a hitter pulled from a game he started? — {through[:4]}",
          "",
          "_From the boxscore: a starter's `battingOrder` ends in 00, and "
          "anyone replacing him in that slot gets the next number up. Counts "
          "any replacement - pinch hitter, pinch runner or defensive sub - "
          "since each ends his night and kills a hits prop equally._", "",
          f"Games scanned: **{len(cache.get('games') or [])}** · "
          f"hitters with {MIN_STARTS}+ starts: **{len(rows)}**", ""]
    if not rows:
        return "\n".join(md + ["_No usable rows yet._"])
    rates = sorted(r["rate"] for _, r in rows)
    def q(p):
        return rates[int(p * (len(rates) - 1))]
    md += ["| percentile | pulled-from-start rate |", "|---|---|"]
    for p in (0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99):
        md.append(f"| p{int(p*100)} | {q(p):.1%} |")
    md += ["", "## Worst 25 — what the gate has to catch", "",
           "| hitter | pulled | starts | rate |", "|---|---|---|---|"]
    for n, r in sorted(rows, key=lambda x: -x[1]["rate"])[:25]:
        md.append(f"| {n} | {r['pulled']} | {r['starts']} | **{r['rate']:.1%}** |")
    md += ["", "## The two from 2026-10-04", ""]
    for want in ("Sean Murphy", "Lane Thomas", "Ozzie Albies",
                 "Matt Olson", "Ronald Acu"):
        for n, r in rows:
            if want in (n or ""):
                md.append(f"- {n}: {r['pulled']}/{r['starts']} "
                          f"= **{r['rate']:.1%}**")
    md += ["", "## Which measure is best?", "",
           "_Decided by forward test, not by argument: every measure built "
           "from PRIOR starts only, scored against what happened that night._",
           ""]
    md += compare(cache)
    md += ["", "## Reading it", "",
           "- set the gate against the median, not a round number: it has to "
           "catch the pulled bats without condemning ordinary hitters",
           "- Albies, Olson and Acuña are printed as controls — they are the "
           "everyday bats the gate must NOT touch",
           "- a hitter under MIN_STARTS returns None and is let through",
           ""]
    return "\n".join(md)


def main() -> None:
    import datetime as dt
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    OUTPUT_DIR.mkdir(exist_ok=True)
    text = build(dt.date.today().isoformat())
    REPORT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
