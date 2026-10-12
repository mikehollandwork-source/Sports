"""
Settle the logged totals, first-five and strikeout lines against what happened.

WHY THIS EXISTS
`market_log` records what the book charges and `projections` records what we
think, and until now the two sat in different files with the outcome in neither.
"Tracking" a market means knowing how it turned out, so this joins the three and
keeps a running record.

NOTHING IS STAKED AND THERE IS NO ROI. These are not bets and no price is
compared to a payout. The record answers two narrower questions:

  1. how often the OVER hit, which is the market's own calibration and the
     baseline anything else has to beat;
  2. when we had a projection, which side of the line it took and whether that
     side was right - a hit rate, not a return.

A hit rate is NOT an edge. A 55% side at -115 is break-even, and the vig on a
two-sided total is around 4.5%, so nothing here becomes bettable until the hit
rate clears the price by more than its own interval. That test needs a season,
not a week.

THE READING IS CUT BEFORE FIRST PITCH, for the same reason CLAUDE.md requires it
of `pm_books`: the poller runs three times a day and a 1pm game is in progress by
the afternoon poll, where the line has already seen the score. Only the last poll
strictly before first pitch minus `consensus.LOCK_LEAD` is used.

Idempotent: keyed per date/game/market/pitcher, so re-running a date re-settles
rather than duplicating. Writes output/market_track.json and .md.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
import math
import statistics as st
import unicodedata
from pathlib import Path

from . import consensus, totals_model

log = logging.getLogger("market_track")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
RECORD = OUTPUT_DIR / "market_track.json"
REPORT = OUTPUT_DIR / "market_track.md"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s.lower() if c.isalnum())


def _first_pitch(g: dict) -> dt.datetime | None:
    v = g.get("game_datetime")
    if not isinstance(v, str):
        return None
    try:
        return dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None


def _last_poll_before(polls: list, cutoff: dt.datetime | None) -> dict | None:
    """The latest poll strictly before the cutoff, or None.

    No cutoff means no usable reading rather than "use the last one" - a line
    read after first pitch is a different quantity, and defaulting to it is
    exactly the mistake that turned a -5.0% backtest into +9.9%.
    """
    if cutoff is None:
        return None
    best = None
    for p in polls:
        try:
            at = dt.datetime.fromisoformat((p.get("at") or "").replace("Z",
                                                                       "+00:00"))
        except ValueError:
            continue
        if at < cutoff and (best is None or at > best[0]):
            best = (at, p)
    return best[1] if best else None


MATCH_TOLERANCE = dt.timedelta(minutes=90)


def _parse(v) -> dt.datetime | None:
    if not isinstance(v, str):
        return None
    try:
        return dt.datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None


def _find(logged: dict, away: str, home: str,
          fp: dt.datetime | None) -> tuple:
    """(entry, legacy_skipped) - the logged line for THIS GAME.

    Keys are `away@home|commence` since 2026-10-12. A bare pair key cannot be
    tied to a game: the same pair plays on consecutive days and `/events` lists
    several at once, so the earlier logs may hold either day's line. Those are
    REFUSED rather than guessed at, exactly as CLAUDE.md requires of the 97
    mis-keyed Kalshi entries - a reading that might belong to another game is
    not a reading.
    """
    pair = f"{away}@{home}"
    best, legacy = None, 0
    for k, v in (logged or {}).items():
        if "|" not in k:
            if k == pair:
                legacy += 1
            continue
        p, _, c = k.partition("|")
        if p != pair:
            continue
        at = _parse((v or {}).get("commence") or c)
        if at is None or fp is None:
            continue
        gap = abs(at - fp)
        if gap <= MATCH_TOLERANCE and (best is None or gap < best[0]):
            best = (gap, v)
    return (best[1] if best else None), legacy


def _side(point, actual) -> str | None:
    if not isinstance(point, (int, float)) or actual is None:
        return None
    if actual > point:
        return "over"
    if actual < point:
        return "under"
    return "push"


def collect() -> tuple[dict, dict]:
    """({key: row} for every settled logged market, {counts}).

    The counts stay OUT of the row dict - a meta entry living among the rows
    would be iterated as one and read for a `market` it does not have.
    """
    try:
        scores = json.loads(totals_model.totals_signal.SCORES.read_text())
    except (OSError, ValueError):
        scores = {}
    try:
        box = json.loads(totals_model.CACHE.read_text())
    except (OSError, ValueError):
        box = {}
    rows: dict = {}
    legacy = 0
    unmatched: list = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "market_log_*.json"))):
        date = Path(f).stem.split("market_log_")[1]
        try:
            logged = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        board_path = OUTPUT_DIR / f"picks_{date}.json"
        if not board_path.exists():
            continue
        try:
            board = json.loads(board_path.read_text())
        except (OSError, ValueError):
            continue
        polls = logged.get("polls") or []
        day_scores = scores.get(date) or {}
        for g in board.get("games", []):
            pk = str(g.get("game_pk"))
            got = day_scores.get(pk)
            if not got:
                continue                     # not final yet
            fp = _first_pitch(g)
            cutoff = fp - consensus.LOCK_LEAD if fp else None
            poll = _last_poll_before(polls, cutoff)
            if not poll:
                continue                     # no pre-game reading
            away, home = (g.get("matchup") or " @ ").split(" @ ")
            pj = (g.get("pick_criteria") or {}).get("projections") or {}
            base = {"date": date, "game_pk": pk, "matchup": g.get("matchup"),
                    "poll_at": poll.get("at")}

            # full-game total (bulk endpoint, so it is on every game)
            t, lg = _find(poll.get("totals") or {}, away, home, fp)
            legacy += lg
            if t and isinstance(t.get("point"), (int, float)):
                rows[f"{date}#{pk}#total"] = {
                    **base, "market": "total", "point": t["point"],
                    "over": t.get("over"), "under": t.get("under"),
                    "book": t.get("book"), "actual": got["total"],
                    "result": _side(t["point"], got["total"]),
                    "proj": (pj.get("runs") or {}).get("full")}

            ev, lg = _find(poll.get("events") or {}, away, home, fp)
            legacy += lg
            ev = ev or {}
            f5 = ev.get("f5_total")
            if f5 and isinstance(f5.get("point"), (int, float)):
                rows[f"{date}#{pk}#f5_total"] = {
                    **base, "market": "f5_total", "point": f5["point"],
                    "over": f5.get("over"), "under": f5.get("under"),
                    "actual": got["f5"],
                    "result": _side(f5["point"], got["f5"]),
                    "proj": (pj.get("runs") or {}).get("f5")}

            # strikeouts: the line is per pitcher, the actual is per starter
            actual_k = {_norm(s.get("name")): s.get("k")
                        for s in (box.get(pk) or {}).get("starters", [])}
            proj_k = {_norm(k.get("pitcher")): k.get("proj")
                      for k in (pj.get("strikeouts") or [])}
            for name, line in (ev.get("strikeouts") or {}).items():
                pt = ((line.get("over") or {}).get("point")
                      if isinstance(line.get("over"), dict) else None)
                k = actual_k.get(_norm(name))
                if isinstance(pt, (int, float)) and k is None:
                    # The book priced someone the boxscore does not list as a
                    # starter. Usually a late scratch, but it is ALSO what a
                    # name-matching failure looks like - a suffix or an accent
                    # the normaliser misses - so it is counted and named rather
                    # than dropped silently.
                    unmatched.append(f"{date} {name}")
                if not isinstance(pt, (int, float)) or k is None:
                    continue
                rows[f"{date}#{pk}#k#{_norm(name)}"] = {
                    **base, "market": "strikeouts", "pitcher": name,
                    "point": pt,
                    "over": (line.get("over") or {}).get("price"),
                    "under": (line.get("under") or {}).get("price"),
                    "actual": k, "result": _side(pt, k),
                    "proj": proj_k.get(_norm(name))}
    if legacy:
        log.info("market_track: refused %d pair-keyed reading(s) from logs "
                 "written before the per-game key", legacy)
    return rows, {"legacy_refused": legacy, "unmatched_pitchers": unmatched}


def _our_side(row: dict) -> str | None:
    """Which side our own projection takes, or None (no projection, or it sits
    exactly on the number)."""
    p, pt = row.get("proj"), row.get("point")
    if not isinstance(p, (int, float)) or not isinstance(pt, (int, float)):
        return None
    if p > pt:
        return "over"
    if p < pt:
        return "under"
    return None


def _break_even(odds) -> float | None:
    if not isinstance(odds, (int, float)):
        return None
    return (abs(odds) / (abs(odds) + 100) if odds < 0
            else 100 / (odds + 100))


def _market_block(name: str, rows: list) -> list[str]:
    settled = [r for r in rows if r.get("result") in ("over", "under")]
    pushes = sum(1 for r in rows if r.get("result") == "push")
    if not settled:
        return [f"### {name}", "", f"- logged: **{len(rows)}**, settled: 0"
                + (f", pushes: {pushes}" if pushes else ""), ""]
    overs = sum(1 for r in settled if r["result"] == "over")
    out = [f"### {name}", "",
           f"- settled: **{len(settled)}**"
           + (f" (plus {pushes} push)" if pushes else ""),
           f"- the OVER hit **{overs}/{len(settled)}** "
           f"({overs / len(settled):.0%}) — the market's own calibration, and "
           "the baseline to beat"]
    # the line's accuracy as a predictor, which is what we are up against
    pts = [r["point"] for r in settled]
    acts = [r["actual"] for r in settled]
    out.append(f"- the line's mean absolute miss: **"
               f"{st.mean(abs(p - a) for p, a in zip(pts, acts)):.2f}**"
               f" (line mean {st.mean(pts):.2f}, actual mean "
               f"{st.mean(acts):.2f})")
    ours = [r for r in settled if _our_side(r)]
    if not ours:
        out += ["- _no projection on any settled row yet, so there is no side "
                "of ours to score. `projections` shipped after the first "
                "logged date._", ""]
        return out
    hit = sum(1 for r in ours if _our_side(r) == r["result"])
    rate = hit / len(ours)
    se = math.sqrt(rate * (1 - rate) / len(ours)) if len(ours) else 0
    out.append(f"- OUR projection's side: **{hit}/{len(ours)}** "
               f"({rate:.0%} ± {1.96 * se:.0%})")
    prices = [_break_even(r["over"] if _our_side(r) == "over" else r["under"])
              for r in ours]
    prices = [p for p in prices if p is not None]
    if prices:
        out.append(f"- the price those sides needed: **{st.mean(prices):.1%}** "
                   "on average")
    mae = st.mean(abs(r["proj"] - r["actual"]) for r in ours)
    lmae = st.mean(abs(r["point"] - r["actual"]) for r in ours)
    out.append(f"- on the same rows, our projection misses by **{mae:.2f}** "
               f"against the line's **{lmae:.2f}**"
               + ("  ← we are closer" if mae < lmae else
                  "  ← the line is closer"))
    out.append("")
    return out


def build(rows: dict, meta: dict) -> str:
    md = ["# Tracking the totals, first five and strikeout lines", "",
          "_LOGGING AND SETTLEMENT ONLY. Nothing is staked, no price is "
          "compared to a payout, and no pick changes. A hit rate is not an "
          "edge: a 55% side at -115 is break-even and the vig on a two-sided "
          "total is around 4.5%, so nothing here is bettable until a side "
          "clears its price by more than its own interval._", "",
          "_Every reading is the last poll strictly before first pitch minus "
          f"`consensus.LOCK_LEAD` ({int(consensus.LOCK_LEAD.total_seconds() // 60)}"
          " min). The poller runs three times a day, so an afternoon game is "
          "already in progress by the later polls and its line has seen the "
          "score._", ""]
    um = meta.get("unmatched_pitchers") or []
    if um:
        md += [f"- **{len(um)} priced pitcher(s) not found as a starter** in "
               "the boxscore: " + ", ".join(um[:8])
               + ("…" if len(um) > 8 else "")
               + ". Usually a late scratch, but this is also what a "
                 "name-matching failure looks like, so it is named rather "
                 "than dropped silently.", ""]
    if meta.get("legacy_refused"):
        md += [f"- **{meta['legacy_refused']} reading(s) refused** as "
               "pair-keyed: they come from logs written before the per-game "
               "key and could belong to either day of a back-to-back, so "
               "they are not used. The record starts at the per-game key.",
               ""]
    if not rows:
        return "\n".join(md + ["- nothing settled yet.", ""])
    dates = sorted({r["date"] for r in rows.values()})
    md += [f"- settled rows: **{len(rows)}** over "
           f"**{len(dates)}** date(s) ({dates[0]} to {dates[-1]})", ""]
    for key, name in (("total", "Full-game total"),
                      ("f5_total", "First-five total"),
                      ("strikeouts", "Starter strikeouts")):
        md += _market_block(name, [r for r in rows.values()
                                   if r["market"] == key])
    md += ["## Every settled row", "",
           "| date | matchup | market | line | our proj | actual | result | "
           "our side |", "|---|---|---|---|---|---|---|---|"]
    for k in sorted(rows):
        r = rows[k]
        who = f" ({r['pitcher']})" if r.get("pitcher") else ""
        proj = f"{r['proj']:.2f}" if isinstance(r.get("proj"), (int, float)) \
            else "—"
        side = _our_side(r) or "—"
        mark = ("✓" if side == r.get("result") else "✗") if side != "—" else ""
        md.append(f"| {r['date']} | {r['matchup']} | {r['market']}{who} | "
                  f"{r['point']} | {proj} | {r['actual']} | {r['result']} | "
                  f"{side} {mark} |")
    return "\n".join(md + [""])


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    rows, meta = collect()
    OUTPUT_DIR.mkdir(exist_ok=True)
    RECORD.write_text(json.dumps({"meta": meta, "rows": rows}, indent=1,
                                 sort_keys=True))
    text = build(rows, meta)
    REPORT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
