"""
Entry point: build the daily edge list.

For each MLB game today:
  1. pull schedule + probable pitchers (MLB API)
  2. pull last-5-game hitting/pitching stats (MLB API)
  3. pull public majority from covers consensus + forum (covers.com)
  4. flag games where the statistically-advantaged team is NOT the public side

Writes output/picks_<date>.json. Date defaults to today (US/Eastern) and can be
overridden with --date YYYY-MM-DD or the PICKS_DATE env var.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import zoneinfo
from pathlib import Path

from . import covers, espn, grade, notify, tune
from .analysis import _canon_abbr, evaluate_game, find_slate_line, line_confirms
from .mlb_api import enrich_with_stats, results_for, schedule_for

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("main")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")


def today_eastern() -> str:
    return dt.datetime.now(EASTERN).date().isoformat()


def run(date: str) -> dict:
    log.info("Building edge list for %s", date)

    games = schedule_for(date)
    log.info("Found %d games", len(games))
    if not games:
        return {"date": date, "games": [], "picks": [], "note": "no games scheduled"}

    # Public sentiment (fetched once, shared across games).
    consensus = covers.consensus()
    teams = [(t.name, t.abbreviation) for g in games for t in (g.home, g.away)]
    forum_counts = covers.forum_majority(teams, date)

    results = []
    for g in games:
        try:
            enrich_with_stats(g, date)
        except Exception as exc:
            log.warning("stats enrichment failed for %s: %s", g.game_pk, exc)
        r = evaluate_game(g, consensus, forum_counts)
        r["game_datetime"] = g.start_time
        results.append(r)

    # Line source = ESPN (true open + current moneyline for every game). For any
    # game ESPN hasn't posted a line for yet, fill the gap from covers' odds page.
    try:
        slate = espn.lines(date)
    except Exception as exc:
        log.warning("espn odds failed: %s", exc)
        slate = []
    if sum(1 for g in games if find_slate_line(g, slate)) < len(games):
        try:
            slate = _merge_slates(slate, covers.slate_lines())
        except Exception as exc:
            log.warning("covers gap-fill failed: %s", exc)

    if os.environ.get("COVERS_DEBUG") == "1":   # capture raw ESPN JSON for debugging
        try:
            espn.dump_debug(date)
        except Exception as exc:
            log.warning("espn debug dump failed: %s", exc)

    for g, r in zip(games, results):
        _attach_line(g, r, slate)

    # Lock games that have already started: a started game keeps the pick/lean
    # status and the odds it had at first pitch (the closing line), so later polls
    # can't flip a pick to a lean or move the price after the game is underway.
    results = _lock_started_games(date, results)

    # Tag each game's live state (upcoming / live / final) for the board.
    try:
        states = results_for(date)
    except Exception as exc:
        log.warning("game-state fetch failed: %s", exc)
        states = {}
    for r in results:
        r["state"] = states.get(r.get("game_pk"), {}).get("state", "upcoming")

    picks = [r["pick"] for r in results if r["flagged"]]
    log.info("Flagged %d edge game(s)", len(picks))

    return {
        "date": date,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "games": results,
        "picks": picks,
    }


def _parse_iso(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _lock_started_games(date: str, results: list) -> list:
    """Freeze any game whose first pitch has passed: replace the fresh computation
    with the previously committed snapshot so a started pick stays a pick (and is
    graded as one) and its captured line is the closing price, not a live one.
    Games not yet underway keep the fresh computation. First-ever capture of an
    already-started game has no snapshot to fall back to, so it stays fresh."""
    prev_path = OUTPUT_DIR / f"picks_{date}.json"
    if not prev_path.exists():
        return results
    try:
        prev = {g["game_pk"]: g for g in json.loads(prev_path.read_text()).get("games", [])}
    except (ValueError, KeyError):
        return results

    now = dt.datetime.now(dt.timezone.utc)
    out, locked = [], 0
    for r in results:
        start = _parse_iso(r.get("game_datetime"))
        snap = prev.get(r.get("game_pk"))
        if snap is not None and start is not None and now >= start:
            out.append(snap)   # underway -> keep the frozen pre-game snapshot
            locked += 1
        else:
            out.append(r)
    if locked:
        log.info("locked %d already-started game(s) to their pre-game snapshot", locked)
    return out


def _merge_slates(primary: list, secondary: list) -> list:
    """ESPN (primary) preferred; append covers (secondary) rows for any game-pair
    the primary doesn't already cover, matched on canonical abbreviations."""
    have = {(_canon_abbr(e["away_abbr"]), _canon_abbr(e["home_abbr"])) for e in primary}
    merged = list(primary)
    for e in secondary:
        key = (_canon_abbr(e["away_abbr"]), _canon_abbr(e["home_abbr"]))
        if key not in have:
            merged.append(e)
            have.add(key)
    return merged


def _attach_line(game, result: dict, slate: list) -> None:
    """Capture the advantage team's current pre-game moneyline (for the tracker,
    picks AND leans) and the open->current line movement toward our side, straight
    from ESPN's open/current. Also applies the sharp-money pick filter."""
    pc = result["pick_criteria"]
    adv = pc["advantage_team"]
    side = "home" if adv == game.home.name else "away"
    opp = "away" if side == "home" else "home"

    # Stop tracking the line the moment the game starts: we only want pre-game
    # movement, never live in-game odds. A started game is restored from its locked
    # snapshot just after this, so we simply don't recompute its line here.
    start = _parse_iso(getattr(game, "start_time", ""))
    if start is not None and dt.datetime.now(dt.timezone.utc) >= start:
        return

    e = find_slate_line(game, slate)
    pc["advantage_moneyline"] = e.get(f"{side}_current") if e else None
    pc["opponent_moneyline"] = e.get(f"{opp}_current") if e else None  # for the faded-leans book

    # line movement toward our side (the advantage team) for EVERY game, pick or lean
    confirms, info = line_confirms(side, e)  # e has {away/home}_open/_current from ESPN
    pc["line_check"] = info

    if not result["flagged"]:
        return
    if confirms is not True:
        result["flagged"] = False
        result["pick"] = None
        pc["status"] = "lean"
        pc["reason"] = (f"line did not confirm the fade — {info['reason']}"
                        if info["status"] != "unknown"
                        else "line movement unavailable — can't confirm the fade")


def _ranked(games: list) -> list:
    """All games, strongest decision first (confidence desc)."""
    return sorted(games, key=lambda g: g.get("pick_criteria", {}).get("confidence", 0.0),
                  reverse=True)


def _board_games(games: list) -> list:
    """Games to show on the live board: upcoming + live only (finals drop off into
    the record), ordered by first pitch with live games pinned to the top."""
    shown = [g for g in games if g.get("state") != "final"]
    return sorted(shown, key=lambda g: (0 if g.get("state") == "live" else 1,
                                        g.get("game_datetime") or ""))


def _finals(games: list) -> list:
    return [g for g in games if g.get("state") == "final"]


def _state_tag(g: dict) -> str:
    return "🔴 LIVE NOW · " if g.get("state") == "live" else ""


def _edge_word(strength: float) -> str:
    return "strong" if strength >= 0.66 else "moderate" if strength >= 0.33 else "slight"


def _c10(conf: float) -> str:
    """Confidence on an intuitive /10 scale, e.g. 0.536 -> '5.4/10'."""
    return f"{round((conf or 0.0) * 10, 1)}/10"


def _public_evidence(g: dict) -> str:
    """Plain description of who the public is on and the evidence behind it,
    in away–home order to match the matchup."""
    det = g["public_majority"]["detail"]
    team = g["public_majority"]["team"]
    if not team:
        return "no public read (forum + consensus both empty)"
    bits = []
    fo = det.get("forum")
    if fo:
        bits.append(f"forum {fo['away']}–{fo['home']} (away–home)")
    co = det.get("consensus")
    if co:
        bits.append("consensus " + "–".join(f"{int(round(v))}%" for v in co["pcts"].values()))
    return f"{team}" + (f" [{', '.join(bits)}]" if bits else "")


def _line_phrase(lc: dict | None) -> str:
    """Line movement boiled down to what matters for the pick: in our favor,
    against us, too much (likely news), or no real movement."""
    if not lc or lc.get("status") == "unknown":
        return "unavailable"
    arrow = f"{lc['open']:+d}→{lc['current']:+d}"
    status = lc["status"]
    if status == "caution":            # big move our way -> usually a pitcher change/news
        return f"⚠️ TOO MUCH ({arrow}) — likely news, verify"
    if status == "confirms":           # a real move toward our side
        return f"IN OUR FAVOR ✓ ({arrow})"
    if status == "contradicts":        # moved toward the other side
        return f"AGAINST us ✗ ({arrow})"
    return f"no real movement ({arrow})"   # flat, or a sub-signal wiggle (soft)


def _line_bullet(pc: dict) -> str | None:
    lc = pc.get("line_check")
    return None if lc is None else f"   • line: {_line_phrase(lc)}"


def _game_lines(g: dict) -> list[str]:
    """Readable lines breaking down one matchup for the board."""
    pc = g["pick_criteria"]
    c = pc["components"]
    adv, conf = pc["advantage_team"], pc["confidence"]
    e = c["stat_edge"]
    edge = f"{adv} ({_edge_word(e['strength'])}, margin {e['margin']})"
    wc = c["win_condition"]["hits"]
    pub = _public_evidence(g)
    tag = _state_tag(g)
    if g.get("flagged"):
        bl = g.get("betting_lines")
        ml = f" · bet {bl['non_majority']['moneyline']}" if bl else ""
        lines = [
            f"✅ **{adv}** — {tag}{g['matchup']} · **confidence {_c10(conf)}** ✓ "
            f"(need {_c10(pc['threshold'])}){ml}",
            f"   • stat edge: {edge}",
            f"   • public is on: {pub} → **we fade them**",
            f"   • win condition: {wc}/5 games",
        ]
    else:
        lines = [
            f"🔸 **{adv}** (lean) — {tag}{g['matchup']} · confidence {_c10(conf)}",
            f"   • stat edge: {edge}",
            f"   • public is on: {pub}",
            f"   • win condition: {wc}/5 games",
            f"   • why not a pick: {pc['reason']}",
        ]
    lb = _line_bullet(pc)
    if lb:
        lines.append(lb + (" — frozen at first pitch" if g.get("state") == "live" else ""))
    return lines


def build_summary(payload: dict) -> str:
    """Markdown board for the daily issue: every matchup broken down — advantage
    team, the public read + evidence, win condition, and a check (pick) or the
    specific reason it's only a lean."""
    date = payload["date"]
    picks = payload.get("picks", [])
    games = payload.get("games", [])
    board, finals = _board_games(games), _finals(games)
    out = [f"# MLB Board — {date}", ""]
    out.append(f"**{len(picks)} pick(s)"
               + (f": {', '.join(picks)}**" if picks else " — no game cleared the bar today.**"))
    if finals:
        out.append(f"\n_{len(finals)} game(s) final — moved into the record below._")
    out.append("")

    if board:
        for g in board:
            out.extend(_game_lines(g))
            out.append("")
    else:
        out.append("_No upcoming or live games — full slate is final (see the record below)._")
        out.append("")

    out.append("_✅ = pick (the public is fading the stat favorite and confidence ≥ threshold). "
               "🔸 = lean: the advantage team is shown, but it's not a play — usually because the "
               "public agrees with the stats (no one to fade) or confidence fell short. "
               "🔴 = live; final games drop off into the record._")

    out.append("")
    out.append(grade.records_block())
    rev = grade.review_line()
    if rev:
        out.append("")
        out.append(rev)
    tune_status = tune.status_line()
    if tune_status:
        out.append("")
        out.append(tune_status)
    out.append(f"\n_Full per-game detail: `output/picks_{date}.json`_")
    return "\n".join(out)


def write_outputs(payload: dict, date: str) -> None:
    """Persist the picks JSON + the daily-issue artifacts (used by main and the
    pre-game refresh)."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / f"picks_{date}.json").write_text(json.dumps(payload, indent=2))
    (OUTPUT_DIR / "latest_summary.md").write_text(build_summary(payload))  # gitignored
    (OUTPUT_DIR / "latest_date.txt").write_text(date)                      # gitignored
    log.info("Wrote picks for %s (%d pick(s))", date, len(payload.get("picks", [])))


def _ml_str(pc: dict) -> str:
    ml = pc.get("advantage_moneyline")
    return f" ({ml:+d})" if isinstance(ml, int) else ""


def _tg_line(g: dict) -> str:
    s = _line_phrase(g["pick_criteria"].get("line_check"))
    if g.get("state") == "live":
        s += " (frozen at first pitch)"
    return f"   line: {s}"


def _telegram_records_lines() -> list[str]:
    """Day/Week/Month/YTD records for both books, laid out one window per line."""
    ledger = grade.load_ledger()
    today = dt.datetime.now(EASTERN).date()
    out: list[str] = []
    for name, key, hyp in (("Picks", "picks", False), ("Leans", "leans", True),
                           ("Leans faded", "leans_faded", True)):
        tag = " (hypothetical)" if hyp else ""
        rec = grade.windowed_records(ledger[key], today)
        if not rec:
            out.append(f"{name}{tag}: no settled bets yet")
            continue
        out.append(f"{name}{tag}:")
        for label, (w, l, u) in rec:
            out.append(f"   • {label}: {w}-{l} ({u:+.2f}u)")
    return out


def telegram_text(payload: dict) -> str:
    """Readable phone layout for Telegram: the pick(s) up top, then leans, then
    the Day/Week/Month/YTD records — sectioned with blank lines and dividers."""
    date = payload["date"]
    games = payload.get("games", [])
    board, finals = _board_games(games), _finals(games)
    picks = payload.get("picks", [])

    L = [f"⚾ MLB BOARD — {date}",
         f"{len(picks)} pick(s)" + (f": {', '.join(picks)}" if picks else " today")]
    if finals:
        L.append(f"({len(finals)} final → moved to the record)")

    for g in board:
        pc = g["pick_criteria"]
        wc = pc["components"]["win_condition"]["hits"]
        tag = "🔴 LIVE · " if g.get("state") == "live" else ""
        if g.get("flagged"):
            edge = _edge_word(pc["components"]["stat_edge"]["strength"])
            L += ["",
                  f"✅ {tag}PICK: {pc['advantage_team']}{_ml_str(pc)}",
                  f"   {g['matchup']}",
                  f"   conf {_c10(pc['confidence'])} · edge {edge} · win-cond {wc}/5",
                  f"   public on {_public_evidence(g)} → we fade",
                  _tg_line(g)]
        else:
            L += ["",
                  f"🔸 {tag}{pc['advantage_team']} · {_c10(pc['confidence'])} · win-cond {wc}/5",
                  f"   {g['matchup']} — {pc['reason']}",
                  _tg_line(g)]
    if not board:
        L += ["", "No upcoming or live games — slate is final (see record)."]

    L += ["", "📊 RECORDS ($1/bet · pre-game ML)"] + _telegram_records_lines()
    ts = tune.status_line().replace("**", "")
    if ts:
        L += ["", ts]
    return "\n".join(L)


def main() -> None:
    parser = argparse.ArgumentParser(description="MLB public-vs-stats edge finder")
    parser.add_argument("--date", default=os.environ.get("PICKS_DATE") or today_eastern())
    args = parser.parse_args()

    payload = run(args.date)
    write_outputs(payload, args.date)
    grade.update_ledger(args.date)  # record any games that just went final (idempotent)
    notify.send_telegram(telegram_text(payload))
    print(json.dumps(payload.get("picks", []), indent=2))


if __name__ == "__main__":
    main()
