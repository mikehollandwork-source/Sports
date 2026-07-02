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

from . import covers, espn, grade, notify, public_sources, reddit, tune, wiki
from .analysis import (LEAN_STRONG_MARGIN, LINE_CONFIRM_MIN, _canon_abbr, _implied,
                       evaluate_game, find_slate_line, line_confirms)
from .mlb_api import enrich_with_stats, results_for, schedule_for, team_home_away_split

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
    try:
        extra_public = public_sources.all_sources()  # 2 more public-% sources to cross-check
    except Exception as exc:
        log.warning("extra public sources failed: %s", exc)
        extra_public = {}
    try:
        reddit_counts = reddit.reddit_majority(teams, date)  # second forum to cross-check
    except Exception as exc:
        log.warning("reddit tally failed: %s", exc)
        reddit_counts = {}
    try:
        wiki_counts = wiki.team_attention_counts(teams, date)  # public-attention proxy
    except Exception as exc:
        log.warning("wiki attention failed: %s", exc)
        wiki_counts = {}

    results = []
    for g in games:
        try:
            enrich_with_stats(g, date)
        except Exception as exc:
            log.warning("stats enrichment failed for %s: %s", g.game_pk, exc)
        r = evaluate_game(g, consensus, forum_counts, extra_public, reddit_counts, wiki_counts)
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
        _attach_situational(g, r, date)

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


def _attach_situational(g, r: dict, date: str) -> None:
    """This-season straight-up situational record, display-only context (no effect
    on the pick). Home team's home record + away team's road record, point-in-time
    (only games before today) — the one situational split calibration showed is
    real (home field, ~53%). Fails soft: on any error the board just omits it."""
    try:
        season = int(date[:4])
        hs = team_home_away_split(g.home.team_id, season, as_of=date)["home"]
        aw = team_home_away_split(g.away.team_id, season, as_of=date)["away"]
    except Exception as exc:
        log.warning("situational record failed for %s: %s", g.game_pk, exc)
        return
    r["situational"] = {
        "home": {"abbr": g.home.abbreviation or g.home.name,
                 "wins": hs["wins"], "losses": hs["losses"]},
        "away": {"abbr": g.away.abbreviation or g.away.name,
                 "wins": aw["wins"], "losses": aw["losses"]},
    }


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

    # Cross-check the public read against the money: did the line move WITH the
    # stated public side (public money real) or AGAINST it (reverse line move — the
    # % doesn't match where the money is, and a tailwind for our fade)?
    cc = result.get("public_check")
    if cc and cc.get("majority_side") and e:
        ps = cc["majority_side"]
        po, pcur = e.get(f"{ps}_open"), e.get(f"{ps}_current")
        if po is not None and pcur is not None:
            shift = round(_implied(pcur) - _implied(po), 3)
            cc["line"] = ("with public" if shift >= LINE_CONFIRM_MIN
                          else "against public" if shift <= -LINE_CONFIRM_MIN else "flat")
            if cc["line"] == "against public":
                cc["flags"].append("reverse line move — money went against the public %")

    if result["flagged"] and confirms is not True:
        result["flagged"] = False
        result["pick"] = None
        pc["status"] = "lean"
        pc["reason"] = (f"line did not confirm the fade — {info['reason']}"
                        if info["status"] != "unknown"
                        else "line movement unavailable — can't confirm the fade")

    # Lean bar (non-picks): a game is only a LEAN at all if it clears the strong
    # criteria - real margin + favorite's price + line not leaning away (from the
    # graded-lean autopsy; see analysis.LEAN_STRONG_MARGIN). Below the bar the game
    # is a PASS: shown as a one-liner, never booked in the Leans ledger.
    if not result["flagged"]:
        ml = pc.get("advantage_moneyline")
        margin = pc["components"]["stat_edge"]["margin"]
        fails = []
        if margin < LEAN_STRONG_MARGIN:
            fails.append(f"margin {margin} < {LEAN_STRONG_MARGIN}")
        if ml is None:
            fails.append("no captured price")
        elif ml >= 0:
            fails.append("underdog")
        if info.get("status") in ("contradicts", "flat"):
            fails.append(f"line {info['status']}")
        if fails:
            pc["lean_tier"] = "standard"
            pc["status"] = "pass"
            pc["reason"] = "below the lean bar: " + ", ".join(fails)
        else:
            pc["lean_tier"] = "strong"


def _is_play(g: dict) -> bool:
    """A game that gets a full board block: a pick, or a lean that cleared the bar.
    Old frozen snapshots (no lean_tier) keep their lean status."""
    pc = g.get("pick_criteria", {})
    if g.get("flagged"):
        return True
    if "lean_tier" in pc:
        return pc["lean_tier"] == "strong"
    return pc.get("status") == "lean"


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


def _kfmt(n: int) -> str:
    """Compact pageview count: 12450 -> '12k', 980 -> '980'."""
    return f"{round(n / 1000)}k" if n >= 1000 else str(int(n))


def _abbrs(g: dict) -> tuple[str, str]:
    """(away, home) short labels: abbreviations when the payload has them, else the
    full names from the matchup (older locked snapshots lack abbr fields)."""
    aa, ha = g.get("away_abbr"), g.get("home_abbr")
    if aa and ha:
        return aa, ha
    away, home = g["matchup"].split(" @ ")
    return away, home


def _short(g: dict, name: str | None) -> str:
    """A team's short label given its full name."""
    if not name:
        return "?"
    away, home = g["matchup"].split(" @ ")
    aa, ha = _abbrs(g)
    return aa if name == away else ha if name == home else name


def _cons_pair(g: dict) -> str:
    """Both teams' consistency, labeled: 'CIN 2/5 · MIL 3/5' (away first, matching
    the matchup order). Falls back to the advantage team's single number on old
    snapshots that didn't store both."""
    aa, ha = _abbrs(g)

    def hits(side: str):
        try:
            return g["consistency"][side]["back_test"]["complete_win_condition"]
        except (KeyError, TypeError):
            return None

    ah, hh = hits("away"), hits("home")
    if ah is None or hh is None:
        return f"{g['pick_criteria']['components']['consistency']['hits']}/5"
    return f"{aa} {ah}/5 · {ha} {hh}/5"


def _public_evidence(g: dict) -> str:
    """Who the public is on + each source's numbers, compact. All pairs are
    away/home, labeled once at the end with the team abbreviations."""
    det = g["public_majority"]["detail"]
    team = g["public_majority"]["team"]
    if not team:
        return "no public read"
    aa, ha = _abbrs(g)
    bits = []
    co = det.get("consensus")
    if co:
        p = [int(round(v)) for v in co["pcts"].values()]
        if len(p) >= 2:
            bits.append(f"covers {p[0]}/{p[1]}%")
    labels = {"scoresodds_bets": "S&O", "vsin_bets": "VSiN", "oddsshark_bets": "Shark"}
    books = det.get("books") or {}
    for name, bk in books.items():
        bits.append(f"{labels.get(name, name)} {int(bk['away'])}/{int(bk['home'])}%")
    so = det.get("sobets")            # pre-books schema (older locked snapshots)
    if so and not books:
        bits.append(f"S&O {int(so['away'])}/{int(so['home'])}%")
    fo = det.get("forum")
    if fo:
        bits.append(f"forum {fo['away']}/{fo['home']}")
    rd = det.get("reddit")
    if rd:
        bits.append(f"reddit {rd['away']}/{rd['home']}")
    wk = det.get("wiki")
    if wk:
        bits.append(f"wiki {_kfmt(wk['away'])}/{_kfmt(wk['home'])}")
    ev = f" — {' · '.join(bits)} ({aa}/{ha})" if bits else ""
    return f"on {_short(g, team)}{ev}"


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


def _public_check_phrase(g: dict) -> str | None:
    """One-line public-consensus cross-check: the verdict, how many sources agree,
    whether the money moved with or against the public, and any anomaly flags.
    None when there's no public read to check."""
    cc = g.get("public_check")
    if not cc or not cc.get("majority_side"):
        return None
    parts = [cc.get("verdict", "unconfirmed")]
    n = len(cc.get("sources", []))
    if n:
        parts.append(f"{cc.get('agree', 0)}/{n} sources")
    line = cc.get("line", "unknown")
    if line == "with public":
        parts.append("line with public")
    elif line == "against public":
        parts.append("line AGAINST public (RLM)")
    money = cc.get("money", "unknown")
    if money == "with public":
        parts.append("$ with public")
    elif money == "against public":
        parts.append("$ AGAINST public")
    s = " · ".join(parts)
    if cc.get("flags"):
        s += " · ⚠️ " + "; ".join(cc["flags"])
    return s


def _bvp_phrase(g: dict) -> str | None:
    """Batter-vs-pitcher, one short line, and ONLY when the blended-OPS gap is
    meaningful (>= BVP_FLOOR - the same bar at which it nudges the edge). Below
    that it's noise and the board stays quiet. None also on old-schema snapshots."""
    b = g.get("bvp")
    if not b or "away_eff" not in b or not b.get("meaningful") or not b.get("edge_team"):
        return None
    aa, ha = _abbrs(g)
    return (f"edge {_short(g, b['edge_team'])} — "
            f"{aa} {b['away_eff']:.3f} v {ha} {b['home_eff']:.3f}")


def _situational_phrase(g: dict) -> str | None:
    """'NYY 24-15 home · BOS 18-21 road' — this-season straight-up situational
    records (display-only context). None when unavailable."""
    s = g.get("situational")
    if not s:
        return None
    h, a = s["home"], s["away"]
    return (f"{h['abbr']} {h['wins']}-{h['losses']} home · "
            f"{a['abbr']} {a['wins']}-{a['losses']} road")


def _game_lines(g: dict) -> list[str]:
    """Readable lines breaking down one matchup for the board. Games below the lean
    bar collapse to a one-liner."""
    pc = g["pick_criteria"]
    if not _is_play(g):
        why = pc.get("reason", "").replace("below the lean bar: ", "")
        return [f"▫️ {_state_tag(g)}{g['matchup']} — {why}"]
    c = pc["components"]
    adv, conf = pc["advantage_team"], pc["confidence"]
    e = c["stat_edge"]
    edge = f"{adv} ({_edge_word(e['strength'])}, margin {e['margin']})"
    cons = _cons_pair(g)
    pub = _public_evidence(g)
    tag = _state_tag(g)
    if g.get("flagged"):
        bl = g.get("betting_lines")
        ml = f" · bet {bl['non_majority']['moneyline']}" if bl else ""
        lines = [
            f"✅ **{adv}** — {tag}{g['matchup']} · all 3 gates ✓ · confidence {_c10(conf)}{ml}",
            f"   • stat edge: {edge} ✓",
            f"   • public: {pub} → **we fade them** ✓",
            f"   • consistency: {cons} _(context)_",
        ]
    else:
        lines = [
            f"⭐ **{adv}** (lean) — {tag}{g['matchup']} · confidence {_c10(conf)}",
            f"   • stat edge: {edge}",
            f"   • public: {pub}",
            f"   • consistency: {cons} _(context)_",
            f"   • why not a pick: {pc['reason']}",
        ]
    pcheck = _public_check_phrase(g)
    if pcheck:
        lines.append(f"   • public check: {pcheck}")
    bvp = _bvp_phrase(g)
    if bvp:
        lines.append(f"   • BvP: {bvp} _(context)_")
    sit = _situational_phrase(g)
    if sit:
        lines.append(f"   • this season: {sit} _(context)_")
    lb = _line_bullet(pc)
    if lb:
        lines.append(lb + (" — frozen at first pitch" if g.get("state") == "live" else ""))
    return lines


def build_summary(payload: dict) -> str:
    """Markdown board for the daily issue: every matchup broken down — advantage
    team, the public read + evidence, consistency, and a check (pick) or the
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

    plays = [g for g in board if _is_play(g)]
    passes = [g for g in board if not _is_play(g)]

    L = [f"⚾ MLB BOARD — {date}",
         f"{len(picks)} pick(s) · {len(plays) - len(picks)} lean(s)"
         + (f" · {len(passes)} below the bar" if passes else "")]
    if picks:
        L.append(f"picks: {', '.join(picks)}")
    if finals:
        L.append(f"({len(finals)} final → moved to the record)")

    for g in plays:
        pc = g["pick_criteria"]
        aa, ha = _abbrs(g)
        adv = _short(g, pc["advantage_team"])
        edge = _edge_word(pc["components"]["stat_edge"]["strength"])
        emargin = pc["components"]["stat_edge"]["margin"]
        tag = "🔴 LIVE · " if g.get("state") == "live" else ""
        head = (f"✅ {tag}PICK {adv}{_ml_str(pc)}" if g.get("flagged")
                else f"⭐ {tag}{aa} @ {ha} → lean {adv}{_ml_str(pc)}")
        frozen = " [frozen]" if g.get("state") == "live" else ""
        L += ["",
              f"{head} · conf {_c10(pc['confidence'])}"]
        if g.get("flagged"):
            L.append(f"   {aa} @ {ha}")
        L += [f"   edge: {edge} ({emargin}) · consistency {_cons_pair(g)}",
              f"   👥 public {_public_evidence(g)}",
              f"   🦈 line: {_line_phrase(pc.get('line_check'))}{frozen}"]
        pcheck = _public_check_phrase(g)
        if pcheck:
            L.append(f"   🔍 check: {pcheck}")
        bvp = _bvp_phrase(g)
        if bvp:
            L.append(f"   🥊 BvP {bvp}")
        sit = _situational_phrase(g)
        if sit:
            L.append(f"   📅 {sit}")
        L.append("   ✅ all 3 gates — WE FADE" if g.get("flagged")
                 else f"   → lean (not a pick): {pc['reason']}")
    if not plays:
        L += ["", "No picks or qualified leans on the slate."]

    if passes:
        L += ["", "— below the lean bar —"]
        for g in passes:
            aa, ha = _abbrs(g)
            pc = g["pick_criteria"]
            tag = "🔴 " if g.get("state") == "live" else ""
            why = pc.get("reason", "").replace("below the lean bar: ", "")
            L.append(f"▫️ {tag}{aa} @ {ha} — {why}")
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
