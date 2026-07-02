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

from . import covers, espn, grade, notify, public_sources, reddit, tune, weather, wiki
from .analysis import (LEAN_MIN_CONSISTENCY, LEAN_STRONG_MARGIN, LINE_CONFIRM_MIN,
                       PICK_MIN_SIGNALS, _canon_abbr, _implied, evaluate_game,
                       find_slate_line, line_confirms)
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
        try:
            r["weather"] = weather.forecast_for(r.get("venue", ""), r.get("game_datetime"))
        except Exception as exc:
            log.warning("weather failed for %s: %s", g.game_pk, exc)

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

    picks = [r["pick_criteria"]["advantage_team"] for r in results if _play(r) == "pick"]
    leans = [r["pick_criteria"]["advantage_team"] for r in results if _play(r) == "lean"]
    fades = sum(1 for r in results if _play(r) == "fade")
    log.info("Board: %d pick(s), %d lean(s), %d fade(s)", len(picks), len(leans), fades)

    return {
        "date": date,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "games": results,
        "picks": picks,
        "leans": leans,
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

    # line movement toward our side (the advantage team) for EVERY game
    _, info = line_confirms(side, e)  # e has {away/home}_open/_current from ESPN
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

    # THE decision (no pick/lean separation): count the five autopsy signals -
    # real margin, favorite's price, line moved TOWARD the lean, consistency
    # >= 3/5, BvP not pointing the other way. At least LEAN_MIN_SIGNALS hits =
    # LEAN; fewer = FADE: bet AGAINST the stat favorite at the opponent's price.
    result["flagged"] = False
    result["pick"] = None
    ml = pc.get("advantage_moneyline")
    margin = pc["components"]["stat_edge"]["margin"]
    cons = pc["components"]["consistency"]["hits"]
    bvp = result.get("bvp") or {}
    m_hit = margin >= LEAN_STRONG_MARGIN
    f_hit = ml is not None and ml < 0
    l_hit = info.get("status") == "confirms"
    c_hit = cons >= LEAN_MIN_CONSISTENCY
    # BvP counts as a hit unless it exists AND points the other way (same
    # semantics the >=2-of-5 backtest was measured with).
    b_hit = not (bvp.get("edge_team") and bvp["edge_team"] != adv)
    hits, misses = [], []
    for ok, label in ((m_hit, f"margin {margin}"),
                      (f_hit, "favorite" if ml is not None else "no price"),
                      (l_hit, "line toward"),
                      (c_hit, f"consistency {cons}/5"),
                      (b_hit, "BvP")):
        (hits if ok else misses).append(label)
    pc["signals_hit"] = len(hits)
    # the opponent's mirrored 9-1 profile: line moved TOWARD them and the public
    # is on them or silent (in the graded record, no-fade + line-confirmed went 9-1)
    away, home = result["matchup"].split(" @ ")
    opp_name = home if adv == away else away
    shift = info.get("implied_shift")
    maj = (result.get("public_majority") or {}).get("team")
    opp_profile = (shift is not None and shift <= -LINE_CONFIRM_MIN
                   and (maj is None or maj == opp_name))
    if len(hits) >= PICK_MIN_SIGNALS:
        pc["play"] = "pick"
        pc["status"] = "pick"
        pc["reason"] = f"{len(hits)}/5 signals — {', '.join(hits)}"
        # ⭐ = the proven-hot combos from the graded record: margin + favorite +
        # line toward (that cell went 10-2), or the 4+-signal sweet spot (8-1).
        star = []
        if m_hit and f_hit and l_hit:
            star.append("margin+favorite+line")
        if len(hits) >= 4:
            star.append(f"{len(hits)}/5 signals")
        pc["starred"] = star
    elif opp_profile:
        pc["play"] = "fade"
        pc["status"] = "fade"
        pc["reason"] = (f"line moved toward {opp_name} and the public isn't against "
                        f"them (9-1 profile); our side hit {len(hits)}/5")
    elif len(hits) >= 1:
        pc["play"] = "lean"
        pc["status"] = "lean"
        pc["reason"] = f"1/5 signals — {', '.join(hits)}"
    else:
        pc["play"] = "pass"
        pc["status"] = "pass"
        pc["reason"] = f"0/5 signals, no fade profile — missed: {', '.join(misses)}"


def _play(g: dict) -> str:
    """The game's play type: 'pick' / 'lean' / 'fade' / 'pass'. Older frozen
    snapshots map: flagged or strong-tier -> pick-era leans stay what they were."""
    pc = g.get("pick_criteria", {})
    if pc.get("play") in ("pick", "lean", "fade", "pass"):
        return pc["play"]
    if g.get("flagged") or pc.get("lean_tier") == "strong":
        return "lean"
    return "pass"


def _is_play(g: dict) -> bool:
    """Full board block = pick or lean (the sides we bet ON)."""
    return _play(g) in ("pick", "lean")


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
    plain = {"corroborated": "all sources agree", "mostly agrees": "most sources agree",
             "sources split": "sources disagree", "unconfirmed": "only 1 source"}
    v = cc.get("verdict", "unconfirmed")
    parts = [plain.get(v, v)]
    n = len(cc.get("sources", []))
    if n > 1:
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


def _weather_phrase(g: dict) -> str | None:
    """'82°F · wind 12mph SSE · rain 20%' at first pitch; roofed parks say so."""
    w = g.get("weather")
    if not w:
        return None
    if w.get("roof") == "dome":
        return "dome (no weather factor)"
    base = f"{w['temp_f']}°F · wind {w['wind_mph']}mph {w['wind_dir']} · rain {w['precip_pct']}%"
    return base + (" · retractable roof" if w.get("roof") == "retract" else "")


def _pen_bvp_phrase(g: dict) -> str | None:
    """Bullpen BvP one-liner, only when the gap is meaningful on a real sample."""
    b = g.get("bvp_pen")
    if not b or not b.get("meaningful") or not b.get("edge_team"):
        return None
    aa, ha = _abbrs(g)
    return (f"edge {_short(g, b['edge_team'])} — "
            f"{aa} {b['away_ops']:.3f} v {ha} {b['home_ops']:.3f} ({b['total_pa']} PA)")


def _situational_phrase(g: dict) -> str | None:
    """'NYY 24-15 home · BOS 18-21 road' — this-season straight-up situational
    records (display-only context). None when unavailable."""
    s = g.get("situational")
    if not s:
        return None
    h, a = s["home"], s["away"]
    return (f"{h['abbr']} {h['wins']}-{h['losses']} home · "
            f"{a['abbr']} {a['wins']}-{a['losses']} road")


def _fade_line(g: dict) -> str:
    """One-liner for a FADE: the side to bet (against the stat favorite), its price,
    and which lean signals failed."""
    pc = g["pick_criteria"]
    adv = pc["advantage_team"]
    away, home = g["matchup"].split(" @ ")
    opp = _short(g, home if adv == away else away)
    oml = pc.get("opponent_moneyline")
    oml_s = f" ({oml:+d})" if isinstance(oml, int) else ""
    return f"🔄 {_state_tag(g)}{g['matchup']} → bet {opp}{oml_s} — {pc.get('reason', '')}"


def _star(pc: dict) -> list[str]:
    """Star reasons for a lean: the proven-hot combos (margin+favorite+line, or 4+
    signals). Falls back to the short-lived 'elevated' schema on older snapshots."""
    st = pc.get("starred")
    if st is not None:
        return st
    ev = pc.get("elevated") or []
    return ev if len(ev) >= 2 else []


def _game_lines(g: dict) -> list[str]:
    """Readable lines breaking down one matchup for the board. Fades collapse to a
    one-liner naming the side to bet; passes to a plain one-liner."""
    pc = g["pick_criteria"]
    if _play(g) == "fade":
        return [_fade_line(g)]
    if _play(g) == "pass":
        return [f"▫️ {_state_tag(g)}{g['matchup']} — {pc.get('reason', '')}"]
    c = pc["components"]
    adv = pc["advantage_team"]
    e = c["stat_edge"]
    edge = f"{adv} ({_edge_word(e['strength'])}, margin {e['margin']})"
    cons = _cons_pair(g)
    pub = _public_evidence(g)
    tag = _state_tag(g)
    star = _star(pc)
    kind = _play(g).upper()
    mark = "⭐" if star else ("✅" if kind == "PICK" else "🔸")
    lines = [
        f"{mark} **{kind} {adv}**{_ml_str(pc)} — {tag}{g['matchup']}"
        + (f" · ⭐ {', '.join(star)}" if star else ""),
        f"   • stat edge: {edge}",
        f"   • public: {pub}",
        f"   • consistency: {cons}",
    ]
    pcheck = _public_check_phrase(g)
    if pcheck:
        lines.append(f"   • public check: {pcheck}")
    bvp = _bvp_phrase(g)
    if bvp:
        lines.append(f"   • BvP: {bvp} _(context)_")
    pen = _pen_bvp_phrase(g)
    if pen:
        lines.append(f"   • pen BvP: {pen} _(context)_")
    wx = _weather_phrase(g)
    if wx:
        lines.append(f"   • weather: {wx} _(context)_")
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
    games = payload.get("games", [])
    board, finals = _board_games(games), _finals(games)
    picks = [g for g in board if _play(g) == "pick"]
    leans = [g for g in board if _play(g) == "lean"]
    fades = [g for g in board if _play(g) == "fade"]
    out = [f"# MLB Board — {date}", ""]
    out.append(f"**{len(picks)} pick(s) · {len(leans)} lean(s) · {len(fades)} fade(s)**"
               + (f" — picks: {', '.join(g['pick_criteria']['advantage_team'] for g in picks)}"
                  if picks else ""))
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

    out.append("_✅ = PICK (2+ signals). ⭐ = pick on a proven-hot combo (margin+favorite+line, or "
               "4+ signals). 🔸 = LEAN (1 signal). 🔄 = FADE: bet against the stat side (their "
               "line+public profile went 9-1). ▫️ = no play. 🔴 = live._")

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
    log.info("Wrote board for %s (%d lean(s))", date, len(payload.get("leans", [])))


def _ml_str(pc: dict) -> str:
    ml = pc.get("advantage_moneyline")
    return f" ({ml:+d})" if isinstance(ml, int) else ""


def _telegram_records_lines() -> list[str]:
    """Day/Week/Month/YTD records for both books, laid out one window per line."""
    ledger = grade.load_ledger()
    today = dt.datetime.now(EASTERN).date()
    out: list[str] = []
    for name, key, hyp in (("Picks", "picks", False), ("Leans", "leans", False),
                           ("Fades", "fades", False)):
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

    picks = [g for g in board if _play(g) == "pick"]
    leans = [g for g in board if _play(g) == "lean"]
    fades = [g for g in board if _play(g) == "fade"]
    passes = [g for g in board if _play(g) == "pass"]

    L = [f"⚾ MLB BOARD — {date}",
         f"{len(picks)} pick(s) · {len(leans)} lean(s) · {len(fades)} fade(s)"
         + (f" · {len(passes)} pass" if passes else "")]
    if finals:
        L.append(f"({len(finals)} final → moved to the record)")

    for g in picks + leans:
        pc = g["pick_criteria"]
        aa, ha = _abbrs(g)
        adv = _short(g, pc["advantage_team"])
        edge = _edge_word(pc["components"]["stat_edge"]["strength"])
        emargin = pc["components"]["stat_edge"]["margin"]
        tag = "🔴 LIVE · " if g.get("state") == "live" else ""
        frozen = " [frozen]" if g.get("state") == "live" else ""
        star = _star(pc)
        kind = _play(g).upper()
        mark = "⭐" if star else ("✅" if kind == "PICK" else "🔸")
        L += ["",
              f"{mark} {tag}{kind} {adv}{_ml_str(pc)}",
              f"   {aa} @ {ha}",
              f"   edge: {edge} ({emargin}) · consistency {_cons_pair(g)}",
              f"   👥 public {_public_evidence(g)}",
              f"   🦈 line: {_line_phrase(pc.get('line_check'))}{frozen}"]
        pcheck = _public_check_phrase(g)
        if pcheck:
            L.append(f"   🔍 check: {pcheck}")
        bvp = _bvp_phrase(g)
        if bvp:
            L.append(f"   🥊 BvP {bvp}")
        pen = _pen_bvp_phrase(g)
        if pen:
            L.append(f"   🧯 pen BvP {pen}")
        wx = _weather_phrase(g)
        if wx:
            L.append(f"   🌤 {wx}")
        sit = _situational_phrase(g)
        if sit:
            L.append(f"   📅 {sit}")
        L.append(f"   ✅ {pc['reason']}"
                 + (f" · ⭐ {', '.join(star)}" if star else ""))
    if not picks and not leans:
        L += ["", "No picks or leans on the slate."]

    if fades:
        L += ["", "— FADES (bet against the stat side) —"]
        for g in fades:
            aa, ha = _abbrs(g)
            pc = g["pick_criteria"]
            adv_name = pc["advantage_team"]
            away, home = g["matchup"].split(" @ ")
            opp = _short(g, home if adv_name == away else away)
            oml = pc.get("opponent_moneyline")
            oml_s = f" ({oml:+d})" if isinstance(oml, int) else ""
            tag = "🔴 " if g.get("state") == "live" else ""
            L.append(f"🔄 {tag}{aa} @ {ha} → bet {opp}{oml_s} — {pc.get('reason', '')}")
    if passes:
        L += ["", "— no play —"]
        for g in passes:
            aa, ha = _abbrs(g)
            tag = "🔴 " if g.get("state") == "live" else ""
            L.append(f"▫️ {tag}{aa} @ {ha} — {g['pick_criteria'].get('reason', '')}")
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
    print(json.dumps(payload.get("leans", []), indent=2))


if __name__ == "__main__":
    main()
