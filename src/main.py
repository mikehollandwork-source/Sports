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

from . import covers, espn, grade, notify, public_sources, reddit, tune, umpire, weather, wiki
from .analysis import (FORM_DIFF_FLOOR, LEAN_MIN_CONSISTENCY, LEAN_STRONG_MARGIN,
                       LINE_CONFIRM_MIN, PDOG_FIP_MIN, PICK_MIN_SIGNALS, PUBLIC_HEAVY,
                       UMP_K_EXTRA, UMP_MIN_GAMES, _canon_abbr, _implied, evaluate_game,
                       find_slate_line, line_confirms)
from .mlb_api import (enrich_with_stats, hp_umpire, results_for, schedule_for,
                      team_home_away_split)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("main")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

# Freeze a game's pick + line this long BEFORE first pitch (not just after), so a
# board firing in the final minutes can't flip a pick to no-action. Covers the
# common case where boards don't land exactly at game time.
LOCK_LEAD = dt.timedelta(minutes=15)


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
        try:   # before evaluation: the weather x power nudge needs it in the margin
            g.weather = weather.forecast_for(g.venue, g.start_time)
        except Exception as exc:
            log.warning("weather failed for %s: %s", g.game_pk, exc)
        # HP umpire before evaluation too: a big-zone ump tilts the margin
        # (umpire.tendency). MLB posts the crew close to first pitch, so the
        # morning run usually gets None and the pre-game refresh fills it in.
        try:
            g.umpire_hp = hp_umpire(g.game_pk)
            g.ump_tend = umpire.tendency(g.umpire_hp, int(date[:4]))
        except Exception as exc:
            log.warning("umpire failed for %s: %s", g.game_pk, exc)
            g.umpire_hp, g.ump_tend = None, None
        r = evaluate_game(g, consensus, forum_counts, extra_public, reddit_counts, wiki_counts)
        r["game_datetime"] = g.start_time
        r["weather"] = g.weather
        r["umpire_hp"] = g.umpire_hp
        r["ump_tend"] = g.ump_tend
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

    picks = [r["pick_criteria"]["advantage_team"] for r in results if _play(r) == "pick"]
    no_action = sum(1 for r in results if _play(r) == "stay_away")
    log.info("Board: %d play(s), %d no-action", len(picks), no_action)

    return {
        "date": date,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "games": results,
        "picks": picks,            # the PLAYS (single tier now)
        "coin_flips": [],          # retired, kept for payload-shape compat
        "leans": [],               # retired tier, kept for payload-shape compat
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
    with the previously committed snapshot so a started PICK stays a pick (and is
    graded as one) and its captured line is the closing price, not a live one.

    Hardened so a started pick can never flip to no-action on a later board:
      - the start time comes from the fresh result OR (fallback) the frozen snapshot,
        so a missing fresh datetime can't skip the lock;
      - once a game is underway we ALWAYS restore its snapshot; and
      - a snapshot that was a PICK is sticky — even the rare case where the fresh
        recompute would down-grade it is overridden back to the pick.
    A game that first appears already-started with no snapshot keeps its fresh
    computation (nothing to fall back to)."""
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
        snap = prev.get(r.get("game_pk"))
        # start from the fresh result, falling back to the frozen snapshot so a
        # missing/empty fresh datetime never bypasses the lock.
        start = _parse_iso(r.get("game_datetime"))
        if start is None and snap is not None:
            start = _parse_iso(snap.get("game_datetime"))
        # lock from LOCK_LEAD before first pitch onward (not just after start)
        locked_window = start is not None and now >= start - LOCK_LEAD
        if snap is not None and locked_window:
            out.append(snap)   # in the lock window -> keep the frozen snapshot
            locked += 1
        else:
            out.append(r)
    if locked:
        log.info("locked %d game(s) at/near first pitch to their pre-game snapshot", locked)
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


# Historical WIN RATES per signal / proven pair, from the fade-gated full-slate
# exhaustive backtest. Used to rank picks by the highest mathematical chance of a
# win, so core (consistency/margin) leads and the pitching-dog (~51%) never tops it.
_SIGNAL_WIN = {"margin": 76, "consistency": 68, "line": 68, "bvp": 62,
               "favorite": 61, "sharp": 60, "form": 57, "pitching_dog": 51}
_PAIR_WIN = {frozenset(("favorite", "consistency", "bvp")): 76,
             frozenset(("consistency", "bvp")): 75,
             frozenset(("margin", "bvp")): 75,
             frozenset(("favorite", "consistency")): 68}


def _win_prob(hits: dict) -> tuple[int, str]:
    """Best mathematical win chance for a pick from the signals it has: the highest
    backtested win rate among its single signals and proven pairs. Returns
    (win_pct, driver_label). A pitching-dog-only pick lands at ~51%, so it always
    sorts below any core (consistency/margin/line) pick."""
    present = [s for s, ok in hits.items() if ok]
    best, driver = 50, "no signal"
    for s in present:
        if _SIGNAL_WIN.get(s, 0) > best:
            best, driver = _SIGNAL_WIN[s], s
    for combo, wr in _PAIR_WIN.items():
        if combo <= set(present) and wr > best:
            best, driver = wr, " + ".join(sorted(combo))
    return best, driver


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
    # BvP counts as a hit unless a MEANINGFUL read points the other way (the
    # book's lens: big-sample platoon data votes, a tiny-gap career OPS doesn't -
    # bvp_read's `meaningful` = gap >= BVP_FLOOR on the shrunk-to-hand numbers).
    b_hit = not (bvp.get("edge_team") and bvp.get("meaningful", True)
                 and bvp["edge_team"] != adv)
    away, home = result["matchup"].split(" @ ")
    # Player-form signal (user call: DIRECT signal): the play side's lineup is
    # hotter - each hitter's last-5 wOBA vs his own season baseline, PA-weighted -
    # than the opponent's by >= FORM_DIFF_FLOOR. Counted like favorite/BvP
    # (supporting: it can't carry a play without a core signal until the audit
    # proves it); form_edge/form_gap are recorded so the audit measures it.
    fm = result.get("form") or {}
    adv_side = "home" if adv == home else "away"
    fa = (fm.get(adv_side) or {}).get("delta")
    fo = (fm.get("away" if adv_side == "home" else "home") or {}).get("delta")
    pc["form_edge"] = (None if fa is None or fo is None or abs(fa - fo) < FORM_DIFF_FLOOR
                       else fa > fo)
    pc["form_gap"] = round(fa - fo, 3) if fa is not None and fo is not None else None
    fh_hit = pc["form_edge"] is True
    maj = (result.get("public_majority") or {}).get("team")
    # Sharp-$ signal (tickets vs HANDLE, the book's own tell): the money sits on
    # OUR side while the ticket majority leans the other way - casual tickets on
    # them, real dollars on us. That divergence is how books themselves profile
    # the action and pick the side they position on. None = no clean money read
    # or no divergence to speak of.
    mcc = result.get("public_check") or {}
    money_ours = mcc.get("money_side") == adv_side
    pc["sharp_money"] = (None if not mcc.get("money_side") or not maj
                         else bool(money_ours and maj != adv))
    s_hit = pc["sharp_money"] is True
    s_label = "sharp $" + (f" ({mcc.get('money_pct')}% of $ on us)"
                           if mcc.get("money_pct") else "")
    # PITCHING-DOG signal (season-scan finding, 186-game stable +11% ROI): an
    # underdog whose starter out-FIPs the favorite's starter by >= PDOG_FIP_MIN
    # (SEASON FIP). It's on the side Vegas needs (a tail), so like the retired
    # live-dog it's an explicit exception to the fade gate - but this one earned it
    # on 186 games with a flat ROI plateau, not a 5-game spike.
    sa = result.get("statistical_advantage") or {}
    a_sfs = (sa.get(adv_side) or {}).get("starter_fip_season")
    o_sfs = (sa.get("away" if adv_side == "home" else "home") or {}).get("starter_fip_season")
    sp_dog_edge = (o_sfs - a_sfs) if isinstance(a_sfs, (int, float)) and isinstance(o_sfs, (int, float)) else None
    pc["sp_dog_edge"] = round(sp_dog_edge, 3) if sp_dog_edge is not None else None
    pd_hit = (ml is not None and ml > 0
              and sp_dog_edge is not None and sp_dog_edge >= PDOG_FIP_MIN)
    pc["pitching_dog"] = pd_hit
    pd_label = (f"pitching dog (SP FIP +{sp_dog_edge:.2f})" if pd_hit else "pitching dog")
    hits, misses = [], []
    for ok, label in ((m_hit, f"margin {margin}"),
                      (f_hit, "favorite" if ml is not None else "no price"),
                      (l_hit, "line toward"),
                      (c_hit, f"consistency {cons}/5"),
                      (b_hit, "BvP"),
                      (fh_hit, f"hot lineup ({pc['form_gap']:+.3f})" if fh_hit else "form"),
                      (s_hit, s_label if s_hit else "sharp $"),
                      (pd_hit, pd_label)):
        (hits if ok else misses).append(label)
    pc["signals_hit"] = len(hits)
    opp_name = home if adv == away else away
    shift = info.get("implied_shift")
    # CORE signals carry a play; favorite + BvP are supporting only. The graded
    # record: bets with a core signal (margin>=.50 / line toward / consistency>=3)
    # went 11-4 (+3.06u), while no-core bets (favorite-only, BvP-only, favorite+BvP)
    # went 7-8 (-1.78u). So ANY play now needs a core signal.
    core_hit = m_hit or l_hit or c_hit
    # Mild-public gate: a public lean UNDER PUBLIC_HEAVY% on the OTHER side has been
    # the sharp side (both the 106-game study and the live record: our side ~38%
    # into it). It's now a NO-ACTION, not a demoted lean - that bucket bled -2.23u.
    mild_public = False
    pub_pct = None
    if maj and maj != adv:
        pairs = _public_pairs((result.get("public_majority") or {}).get("detail") or {})
        if pairs:
            ap = sum(p[0] for p in pairs) / len(pairs)
            hp = sum(p[1] for p in pairs) / len(pairs)
            pub_pct = round(hp if maj == home else ap)
            pc["public_pct_against"] = pub_pct
            mild_public = pub_pct < PUBLIC_HEAVY
    # Tickets-vs-handle override (user call - the book's own playbook): the
    # mild-public fade assumes the sharp side is the OTHER side. When the real
    # dollars sit on US while the tickets lean away, that assumption fails -
    # the sharp profile is ours, so the mild-public gate stands down.
    if mild_public and s_hit:
        mild_public = False
        pc["mild_public_overridden"] = "money on us vs tickets on them"
    # Book-stance read (research playbook): freeze the informed tells the book
    # leaves when it positions against the public. NOT a veto - the graded record
    # shows our 'book-informed-side-against-us' plays are our BEST bucket (27-16),
    # so a hard fade would cut winners. It DOES gate the star: a play where the
    # book's INFORMED money (>=1 tell) is against us can't be a ⭐ (we're the side
    # the house is quietly fading), and it earns a ⚠️ on the board.
    stance = _book_stance(result)
    pc["book_stance"] = stance
    stance_against = bool(stance and stance.get("against_us") and stance.get("tells"))
    # FADE-ONLY board gate (user call, backed by the 186-game backtest): a game
    # makes the board ONLY as a FADE of Vegas (our side is the team the book does
    # NOT need) carrying a CORE signal - the high-ROI zone (fade+margin +29.6%,
    # fade+consistency +15%, fade+line +12.6% ROI/bet). The side VEGAS needs (tail)
    # is dropped no matter how many signals agree: tailing + our signals graded
    # NEGATIVE on the full sample (tail+bvp -5.48u, tail+consistency -2.50u, and
    # -16.2% ROI at >=2 stacked). When there's no clean book read we can't tell
    # fade from tail, so we fall back to the plain core-signal gate.
    book = _book_needs(result)
    pc["vegas"] = book   # frozen book_needs read: drives the fade gate (behind the scenes)
    if book:
        is_tail = adv == book["bet"]          # we're on the side Vegas NEEDS
        qualifies = (core_hit and not is_tail) or pd_hit  # fade+core, OR a pitching dog
    else:
        is_tail = False
        qualifies = core_hit or pd_hit        # no book read -> core, or pitching dog
    # ONE play tier (user call - no more pick/lean split): a game is a PLAY when it
    # clears the fade gate + core signal and isn't a mild-public fade. A PITCHING
    # DOG also bypasses the fade + mild-public gates - it's its own high-conviction
    # path (backtested +11% ROI on 186 dogs). The internal play value stays "pick".
    playable = qualifies and (not mild_public or pd_hit)
    if playable and len(hits) >= 1:
        pc["play"] = "pick"
        pc["status"] = "pick"
        pc["reason"] = f"{len(hits)}/8 signals — {', '.join(hits)}"
        # ⭐ = the proven-hot combos from the graded record: margin + favorite +
        # line toward (10-2), or 4+ of the FIVE PROVEN signals (8-1). Form, sharp-$
        # and pitching-dog are extras kept out of the star (form=no edge; sharp-$
        # and pitching-dog are backtested but not yet forward-proven live).
        proven = len(hits) - (1 if fh_hit else 0) - (1 if s_hit else 0) - (1 if pd_hit else 0)
        star = []
        if m_hit and f_hit and l_hit:
            star.append("margin+favorite+line")
        if proven >= 4:
            star.append(f"{proven}/5 proven signals")
        # never star a play the book's informed money is fading (⚠️ instead)
        pc["starred"] = [] if stance_against else star
        if stance_against:
            pc["stance_warning"] = f"book's informed money is on {stance['side']}"
        # WIN PROBABILITY (user call): the reason we pick a game is the highest
        # mathematical chance of a WIN among its signals - the board is ranked by
        # this, so high-win-rate CORE picks (consistency/margin) always lead and the
        # low-win-rate pitching-dog (~51%, profits on the plus price) never takes
        # priority over core. Rates are the fade-gated backtest win %s.
        wp, driver = _win_prob({"margin": m_hit, "favorite": f_hit, "line": l_hit,
                                "consistency": c_hit, "bvp": b_hit, "sharp": s_hit,
                                "form": fh_hit, "pitching_dog": pd_hit})
        pc["win_prob"] = wp
        pc["win_driver"] = driver
    else:
        # (Coin flips RETIRED per user call - "it's either a pick or not". The
        # old lock profile bet the opponent on a line move toward them, but it
        # graded to no edge (2-4 back-test, 3-2 live), so those games are just
        # no-action now. Legacy frozen locks still display/grade as history.)
        # NO ACTION: no core signal (favorite/BvP alone don't carry a play), or the
        # public is mildly on the other side (the sharp fade). Listed, never booked.
        # (play value stays 'stay_away' so older frozen snapshots classify the same.)
        pc["play"] = "stay_away"
        pc["status"] = "stay_away"
        pc["stay_bet"] = None
        pc["stay_odds"] = None
        if mild_public:
            why = f"public mildly on {maj} ({pub_pct}% < {PUBLIC_HEAVY}) — sharp fade, no play"
        elif book and is_tail and core_hit:
            why = (f"on the side Vegas needs ({_short(result, book['bet'])}) — "
                   f"tailing the book lost even with signals, no play")
        elif not core_hit and hits:
            why = f"only {', '.join(hits)} — no core signal (margin/line/consistency), no play"
        else:
            why = "0/8 signals — no play"
        pc["reason"] = why


def _play(g: dict) -> str:
    """The game's play type: 'pick' (a PLAY) / 'lock' (coin flip) / 'stay_away'.
    The pick/lean split is retired - legacy 'lean' frozen snapshots classify as
    plays; old 'fade' (the 9-1 rule) -> lock; 'pass' -> stay_away."""
    pc = g.get("pick_criteria", {})
    play = pc.get("play")
    if play == "lean":
        return "pick"
    if play in ("lock", "fade", "pass"):   # coin flips retired entirely
        return "stay_away"
    if play in ("pick", "stay_away"):
        return play
    if g.get("flagged") or pc.get("lean_tier") == "strong":
        return "pick"
    return "stay_away"


def _is_play(g: dict) -> bool:
    """Full board block = a PLAY (the side we bet ON)."""
    return _play(g) == "pick"


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


def _by_win(games: list) -> list:
    """Order picks by the highest mathematical chance of a win (live pinned on top),
    so core consistency/margin picks lead and the low-win pitching-dog trails."""
    return sorted(games, key=lambda g: (0 if g.get("state") == "live" else 1,
                                        -((g.get("pick_criteria") or {}).get("win_prob") or 0)))


def _win_phrase(g: dict) -> str | None:
    """'🎯 ~76% win (margin)' - the pick's best mathematical win chance + what drives
    it. None on older snapshots without the field."""
    pc = g.get("pick_criteria") or {}
    wp = pc.get("win_prob")
    if not wp:
        return None
    return f"🎯 ~{wp}% win ({pc.get('win_driver', 'signal')})"


def _finals(games: list) -> list:
    return [g for g in games if g.get("state") == "final"]


def _state_tag(g: dict) -> str:
    return "🔴 LIVE NOW · " if g.get("state") == "live" else ""


def _start_time(g: dict) -> str | None:
    """First pitch in US/Eastern, e.g. '7:05 PM ET'. None if unknown or the game
    is already live/final (the state tag covers those)."""
    if g.get("state") in ("live", "final"):
        return None
    d = _parse_iso(g.get("game_datetime"))
    if not d:
        return None
    et = d.astimezone(EASTERN)
    return et.strftime("%-I:%M %p ET")


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
            return g["consistency"][side]["back_test"]["out_hit"]
        except (KeyError, TypeError):
            return None

    ah, hh = hits("away"), hits("home")
    if ah is None or hh is None:
        return f"{g['pick_criteria']['components']['consistency']['hits']}/5"
    return f"{aa} {ah}/5 · {ha} {hh}/5"


_SRC_LABELS = {"covers": "covers", "forum": "forum", "reddit": "reddit",
               "scoresodds_bets": "S&O", "vsin_bets": "VSiN", "polymarket_bets": "Poly"}


def _public_pairs(det: dict) -> list[tuple[float, float]]:
    """Every public-% source as an (away%, home%) pair: covers consensus, each
    book's bet%, and the forum/reddit tallies converted to shares. Wiki attention
    is NOT a consensus number, so it stays out of the average."""
    pairs: list[tuple[float, float]] = []
    co = det.get("consensus")
    if co:
        p = list(co.get("pcts", {}).values())
        if len(p) >= 2:
            pairs.append((p[0], p[1]))
    books = det.get("books") or {}
    for bk in books.values():
        pairs.append((bk["away"], bk["home"]))
    so = det.get("sobets")            # pre-books schema (older locked snapshots)
    if so and not books:
        pairs.append((so["away"], so["home"]))
    for key in ("forum", "reddit"):
        t = det.get(key)
        if t and (t.get("away", 0) + t.get("home", 0)):
            tot = t["away"] + t["home"]
            pairs.append((100.0 * t["away"] / tot, 100.0 * t["home"] / tot))
    return pairs


def _public_evidence(g: dict) -> str:
    """Who the public is on + ONE combined number: every % source averaged per
    team, labeled with the team abbreviations ('on MIA — MIA 68% v HOU 42%').
    Per-source detail lives in the JSON and only surfaces on the check line
    when sources disagree."""
    det = g["public_majority"]["detail"]
    team = g["public_majority"]["team"]
    if not team:
        return "no public read"
    aa, ha = _abbrs(g)
    pairs = _public_pairs(det)
    if not pairs:
        return f"on {_short(g, team)}"
    ap = round(sum(p[0] for p in pairs) / len(pairs))
    hp = round(sum(p[1] for p in pairs) / len(pairs))
    n = len(pairs)
    return (f"on {_short(g, team)} — {aa} {ap}% v {ha} {hp}% "
            f"(avg of {n} source{'s' if n > 1 else ''})")


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
    """The public-consensus cross-check, shown ONLY when something's off: sources
    disagreeing on the public side (named, with who went which way) or an anomaly
    flag. When every source agrees the check stays behind the scenes (it's in the
    JSON). Historical note: on sources-split games the majority side still won
    59% (19-13), so disagreement is a caution, not a veto."""
    cc = g.get("public_check")
    if not cc or not cc.get("majority_side"):
        return None
    if not cc.get("dissent") and not cc.get("flags"):
        return None
    parts = []
    if cc.get("dissent"):
        ms = cc["majority_side"]
        maj_team = _short(g, g["matchup"].split(" @ ")[1 if ms == "home" else 0])
        other = _short(g, g["matchup"].split(" @ ")[0 if ms == "home" else 1])
        with_names = [_SRC_LABELS.get(s["name"], s["name"])
                      for s in cc.get("sources", []) if s.get("agrees")]
        against = [_SRC_LABELS.get(s["name"], s["name"])
                   for s in cc.get("sources", []) if not s.get("agrees")]
        parts.append(f"sources disagree — {', '.join(against)} on {other}"
                     + (f"; {', '.join(with_names)} on {maj_team}" if with_names else ""))
        # historical read on split games (23-13, 64%): the forum has been right
        # when IT's the dissenter (5-2); any other dissenter, stay with the
        # majority (18-11). Display-only - it doesn't move the play.
        forum_dissents = any(s["name"] == "forum" and not s.get("agrees")
                             for s in cc.get("sources", []))
        parts.append(f"split read: {other if forum_dissents else maj_team} "
                     f"(64% historically)")
    line = cc.get("line", "unknown")
    if line == "against public":
        parts.append("line AGAINST public (RLM)")
    money = cc.get("money", "unknown")
    if money == "against public":
        parts.append("$ AGAINST public")
    s = " · ".join(parts) if parts else ""
    flags = [f for f in cc.get("flags", [])         # drop the two flags the parts above
             if "other side from the public" not in f    # already say ('$ AGAINST' / RLM)
             and "reverse line move" not in f]
    if flags:
        s += (" · " if s else "") + "⚠️ " + "; ".join(flags)
    return s or None


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


def _pen_tax_phrase(g: dict) -> str | None:
    """'🪫 pen tax: STL 2 arm(s) down' - relievers who threw both of the last two
    days (their pen FIP is taxed in the margin). None when both pens are fresh."""
    sa = g.get("statistical_advantage") or {}
    away, home = g["matchup"].split(" @ ")
    parts = []
    for side, name in (("away", away), ("home", home)):
        n = (sa.get(side) or {}).get("pen_arms_down")
        if n:
            parts.append(f"{_short(g, name)} {n} arm(s) down")
    return "🪫 pen tax: " + " · ".join(parts) if parts else None


def _form_phrase(g: dict) -> str | None:
    """Hot/cold lineup form vs each hitter's own season baseline, with the
    standout bat per side: '🔥 SEA +.024 (Rodríguez +.115) · ❄️ TOR -.018
    (Springer -.092)'. Probation signal - display + audit only."""
    fm = g.get("form") or {}
    aa, ha = _abbrs(g)
    bits = []
    for side, ab in (("away", aa), ("home", ha)):
        s = fm.get(side)
        if not s or s.get("delta") is None:
            continue
        d = s["delta"]
        icon = "🔥" if d >= 0.015 else "❄️" if d <= -0.015 else "•"
        standout = (s.get("hot") or [None])[0] if d >= 0 else (s.get("cold") or [None])[-1]
        extra = ""
        if standout:
            last = standout["name"].split()[-1]
            extra = f" ({last} {standout['delta']:+.3f})"
        bits.append(f"{icon} {ab} {d:+.3f}{extra}")
    if not bits:
        return None
    # strength of the hotter lineup's EDGE (the gap between the two sides), labeled
    # strong / moderate / weak off the form-calibration bands.
    pc = g.get("pick_criteria") or {}
    gap = pc.get("form_gap")
    if gap is not None and abs(gap) >= FORM_DIFF_FLOOR:
        mag = abs(gap)
        tier = "strong" if mag >= 0.05 else "moderate" if mag >= 0.03 else "weak"
        adv = pc.get("advantage_team")
        away, home = g["matchup"].split(" @ ")
        opp = home if adv == away else away
        hotter = adv if gap > 0 else opp   # form_gap = advantage delta - opponent delta
        bits.append(f"edge {_short(g, hotter)} ({tier})")
    return " · ".join(bits)


def _ump_phrase(g: dict) -> str | None:
    """'HP ump: John Doe — big zone (K +0.9/gm)' once MLB posts the crew. The
    tendency comes from the committed ump table; a big-zone ump also tilts the
    margin toward the lower-K lineup (see analysis)."""
    u = g.get("umpire_hp")
    if not u:
        return None
    t = g.get("ump_tend")
    if t and t.get("games", 0) >= UMP_MIN_GAMES:
        ke = t.get("k_extra") or 0
        zone = ("big zone" if ke >= UMP_K_EXTRA
                else "tight zone" if ke <= -UMP_K_EXTRA else "neutral zone")
        return f"HP ump: {u} — {zone} (K {ke:+.1f}/gm, {t['games']} gm)"
    return f"HP ump: {u}"


def _situational_phrase(g: dict) -> str | None:
    """'NYY 24-15 home · BOS 18-21 road' — this-season straight-up situational
    records (display-only context). None when unavailable."""
    s = g.get("situational")
    if not s:
        return None
    h, a = s["home"], s["away"]
    return (f"{h['abbr']} {h['wins']}-{h['losses']} home · "
            f"{a['abbr']} {a['wins']}-{a['losses']} road")


def _lock_bet(g: dict) -> tuple[str | None, int | None]:
    """The LOCK's bet side + price. Frozen snapshots from before lock_bet existed
    (old 'fade' schema) fall back to the opponent of the stat side at its captured
    price - the same fallback grading uses, so display and record always match."""
    pc = g["pick_criteria"]
    bet, odds = pc.get("lock_bet"), pc.get("lock_odds")
    if bet is None:
        away, home = g["matchup"].split(" @ ")
        adv = pc.get("advantage_team")
        bet = home if adv == away else away
        oml = pc.get("opponent_moneyline")
        odds = int(oml) if oml is not None else None
    return bet, odds


def _money_phrase(g: dict) -> str | None:
    """'💰 money on ATL 62%' - which side the sportsbook money sits on (avg of
    the *_money sources) for a no-play game. None when there's no clean read."""
    cc = g.get("public_check") or {}
    ms = cc.get("money_side")
    if ms not in ("home", "away"):
        return None
    away, home = g["matchup"].split(" @ ")
    team = _short(g, home if ms == "home" else away)
    pct = cc.get("money_pct")
    return f"💰 money on {team}" + (f" {pct}%" if pct else "")


# Display-only ballpark for the total wagered on an average regular-season MLB
# game across US legal books (annual MLB handle / ~2430 games). A rough constant,
# not per-game data - shown as "(est)" and never used in any decision.
EST_GAME_HANDLE = 7_000_000


def _book_needs(g: dict) -> dict | None:
    """Which team the SPORTSBOOK needs to win, from the dollar split (money % -
    falls back to avg ticket %) and both moneylines on an estimated ~$7M handle.
    Returns {bet (full name), odds (that side's ml), basis, hold_home, hold_away}
    or None with no clean read. Display/Vegas-record only - never a decision."""
    pc = g.get("pick_criteria") or {}
    adv = pc.get("advantage_team")
    ml_a, ml_o = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
    if not adv or ml_a is None or ml_o is None:
        return None
    away, home = g["matchup"].split(" @ ")
    ml_home, ml_away = (ml_a, ml_o) if adv == home else (ml_o, ml_a)
    cc = g.get("public_check") or {}
    if cc.get("money_side") in ("home", "away") and cc.get("money_pct"):
        hp = cc["money_pct"] if cc["money_side"] == "home" else 100 - cc["money_pct"]
        basis = "money %"
    else:
        pairs = _public_pairs((g.get("public_majority") or {}).get("detail") or {})
        if not pairs:
            return None
        hp = sum(p[1] for p in pairs) / len(pairs)
        basis = "ticket %"
    dh, da = hp / 100.0, 1.0 - hp / 100.0

    def net(ml):        # winner's net payout per $1 staked
        return 100 / abs(ml) if ml < 0 else ml / 100

    hold_home = EST_GAME_HANDLE * (da - dh * net(ml_home))   # book P/L if home wins
    hold_away = EST_GAME_HANDLE * (dh - da * net(ml_away))
    need_home = hold_home >= hold_away
    return {"bet": home if need_home else away,
            "odds": int(ml_home if need_home else ml_away),
            "basis": basis,
            "hold_home": round(hold_home), "hold_away": round(hold_away)}


def _book_stance(g: dict) -> dict | None:
    """Read the sportsbook's *informed* stance - the side the SHARP dollars back -
    from the tells a book leaves when it positions against the public (the research
    playbook: money-vs-ticket divergence, reverse line move, a frozen line under
    heavy public). Returns {side, against_us, tells:[...], strength, fooled}:
      - side       = the team the SHARP money is on (money-heavy side when it
                     splits from tickets; else the side the line moved toward)
      - fooled     = True when the public ticket majority is on the OTHER side
                     (the public is being funneled off the sharp number)
      - against_us = the sharp side is NOT our advantage team (we'd be on the
                     side the smart money is fading)
      - strength   = number of confirming tells (0 = no informed signal, None)
    Display + warning only; it does NOT kill a play - the graded record shows our
    plays with the sharp money against us are our BEST bucket (a hard veto would
    cut winners). It gates the ⭐ and prints a ⚠️ so the conflict is visible."""
    cc = g.get("public_check") or {}
    pc = g.get("pick_criteria") or {}
    adv = pc.get("advantage_team")
    away, home = g["matchup"].split(" @ ")
    maj = (g.get("public_majority") or {}).get("team")
    ms = cc.get("money_side")
    money_team = (home if ms == "home" else away) if ms in ("home", "away") else None
    tells = []
    side = None
    # 1) sharp $: dollars concentrated on the side the tickets are NOT on
    if money_team and maj and money_team != maj:
        tells.append("money vs tickets")
        side = money_team
    # 2) reverse line move: line moved toward the non-public side (sharp action)
    if cc.get("line") == "against public":
        tells.append("reverse line move")
        if side is None and maj:
            side = home if maj == away else away
    # 3) heavy public on one side, line didn't confirm to them (book holding firm
    #    against the crowd) - the sharp side is the one the public is NOT on
    if maj:
        pairs = _public_pairs((g.get("public_majority") or {}).get("detail") or {})
        if pairs:
            mp = (sum(p[1] for p in pairs) if maj == home else sum(p[0] for p in pairs)) / len(pairs)
            if mp >= PUBLIC_HEAVY and (pc.get("line_check") or {}).get("status") != "confirms":
                tells.append(f"line frozen under {round(mp)}% public")
                if side is None:
                    side = home if maj == away else away
    if not tells or side is None:
        return {"side": None, "against_us": False, "tells": [], "strength": 0, "fooled": False}
    return {"side": side, "against_us": bool(adv and side != adv),
            "tells": tells, "strength": len(tells),
            "fooled": bool(maj and maj != side)}


def _stance_phrase(g: dict, brief: bool = False) -> str | None:
    """'🕵️ book stance: ON ATH — public being fooled (money vs tickets, RLM)' when
    the book has left informed tells; a plain liability lean (0 tells) says nothing
    and returns None. Adds '⚠️ vs OUR pick' when the informed side isn't ours.
    `brief` = a compact tag for no-play one-liners."""
    st = (g.get("pick_criteria") or {}).get("book_stance") or _book_stance(g)
    if not st or not st.get("tells"):
        return None
    who = _short(g, st["side"])
    if brief:
        return (f"🚨 public fooled → book on {who}" if st["fooled"]
                else f"🕵️ book on {who}")
    tail = f" — 🚨 public being fooled ({', '.join(st['tells'])})" if st["fooled"] \
        else f" ({', '.join(st['tells'])})"
    warn = " · ⚠️ vs OUR pick" if st.get("against_us") else ""
    return f"🕵️ book stance: ON {who}{tail}{warn}"


def _stay_line(g: dict) -> str:
    """One-liner for a NO-ACTION game (nothing the system likes; never booked)."""
    pc = g["pick_criteria"]
    mp = _money_phrase(g)
    stc = _stance_phrase(g, brief=True)
    tm = _start_time(g)
    head = f"▫️ {_state_tag(g)}{g['matchup']}" + (f" ({tm})" if tm else "")
    return (f"{head} — {pc.get('reason', 'no play')}"
            + (f" · {mp}" if mp else "")
            + (f" · {stc}" if stc else ""))


def _star(pc: dict) -> list[str]:
    """Star reasons for a lean: the proven-hot combos (margin+favorite+line, or 4+
    signals). Falls back to the short-lived 'elevated' schema on older snapshots."""
    st = pc.get("starred")
    if st is not None:
        return st
    ev = pc.get("elevated") or []
    return ev if len(ev) >= 2 else []


def _game_lines(g: dict) -> list[str]:
    """Readable lines breaking down one matchup for the board. Coin flips and
    no-action games collapse to a one-liner."""
    pc = g["pick_criteria"]
    if _play(g) == "stay_away":
        return [_stay_line(g)]
    c = pc["components"]
    adv = pc["advantage_team"]
    e = c["stat_edge"]
    edge = f"{adv} ({_edge_word(e['strength'])}, margin {e['margin']})"
    cons = _cons_pair(g)
    pub = _public_evidence(g)
    tag = _state_tag(g)
    star = _star(pc)
    kind = "PLAY"
    warn = pc.get("stance_warning")
    mark = "⚠️" if warn else "⭐" if star else "✅"
    wphr = _win_phrase(g)
    lines = [
        f"{mark} **{kind} {adv}**{_ml_str(pc)} — {tag}{g['matchup']}"
        + (f" · {_start_time(g)}" if _start_time(g) else "")
        + (f" · {wphr}" if wphr else "")
        + (f" · ⭐ {', '.join(star)}" if star else "")
        + (f" · ⚠️ {warn}" if warn else ""),
        f"   • stat edge: {edge}",
        f"   • public: {pub}",
        f"   • consistency: {cons}",
    ]
    mp = _money_phrase(g)
    if mp:
        lines.append(f"   • {mp}")
    stp = _stance_phrase(g)
    if stp:
        lines.append(f"   • {stp}")
    pcheck = _public_check_phrase(g)
    if pcheck:
        lines.append(f"   • public check: {pcheck}")
    bvp = _bvp_phrase(g)
    if bvp:
        lines.append(f"   • BvP: {bvp} _(context)_")
    pen = _pen_bvp_phrase(g)
    if pen:
        lines.append(f"   • pen BvP: {pen} _(context)_")
    pt = _pen_tax_phrase(g)
    if pt:
        lines.append(f"   • {pt}")
    fp = _form_phrase(g)
    if fp:
        lines.append(f"   • form: {fp} _(probation signal)_")
    wx = _weather_phrase(g)
    if wx:
        lines.append(f"   • weather: {wx} _(context)_")
    ump = _ump_phrase(g)
    if ump:
        lines.append(f"   • {ump} _(context)_")
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
    no_action = [g for g in board if _play(g) == "stay_away"]
    out = [f"# MLB Board — {date}", ""]
    out.append(f"**{len(picks)} play(s) · {len(no_action)} no-play**"
               + (f" — picks: {', '.join(g['pick_criteria']['advantage_team'] for g in picks)}"
                  if picks else ""))
    if finals:
        out.append(f"\n_{len(finals)} game(s) final — moved into the record below._")
    out.append("")

    if board:
        for g in _by_win(picks) + no_action:   # picks ranked by win chance, then no-plays
            out.extend(_game_lines(g))
            out.append("")
    else:
        out.append("_No upcoming or live games — full slate is final (see the record below)._")
        out.append("")

    out.append("_✅ = PLAY (core signal + not a mild-public fade, unless the sharp $ is on us). "
               "⭐ = play on a proven-hot combo (margin+favorite+line, or 4+ proven signals). "
               "⚠️ = a PLAY the book's informed money is fading (never a ⭐). ▫️ = no play. "
               "🕵️/🚨 = the book's informed stance / public being fooled. 🔴 = live._")

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
    """Day/Week/Month/YTD records per book plus the all-time combined row, laid
    out one window per line."""
    ledger = grade.load_ledger()
    today = dt.datetime.now(EASTERN).date()
    out: list[str] = []
    books = [("Plays", ledger["plays"])]
    for name, book in books:
        rec = grade.windowed_records(book, today)
        if not rec:
            out.append(f"{name}: no settled bets yet")
            continue
        out.append(f"{name}:")
        for label, (w, l, u) in rec:
            out.append(f"   • {label}: {w}-{l} ({u:+.2f}u)")
        w, l, u = grade._tally(book["entries"])
        out.append(f"   • All-time: {w}-{l} ({u:+.2f}u)")
    return out


def telegram_text(payload: dict) -> str:
    """Readable phone layout for Telegram: the pick(s) up top, then leans, then
    the Day/Week/Month/YTD records — sectioned with blank lines and dividers."""
    date = payload["date"]
    games = payload.get("games", [])
    board, finals = _board_games(games), _finals(games)

    picks = [g for g in board if _play(g) == "pick"]
    no_action = [g for g in board if _play(g) == "stay_away"]

    L = [f"⚾ MLB BOARD — {date}",
         f"{len(picks)} play(s) · {len(no_action)} no-play"]
    if finals:
        L.append(f"({len(finals)} final → moved to the record)")

    def block(g):
        pc = g["pick_criteria"]
        aa, ha = _abbrs(g)
        adv = _short(g, pc["advantage_team"])
        edge = _edge_word(pc["components"]["stat_edge"]["strength"])
        emargin = pc["components"]["stat_edge"]["margin"]
        tag = "🔴 LIVE · " if g.get("state") == "live" else ""
        frozen = " [frozen]" if g.get("state") == "live" else ""
        star = _star(pc)
        kind = "PLAY"
        warn = pc.get("stance_warning")
        mark = "⚠️" if warn else "⭐" if star else "✅"
        st = _start_time(g)
        wphr = _win_phrase(g)
        L.extend(["",
                  f"{mark} {tag}{kind} {adv}{_ml_str(pc)}"
                  + (f"  ⚠️ {warn}" if warn else ""),
                  f"   {aa} @ {ha}" + (f" · {st}" if st else ""),
                  f"   edge: {adv} {edge} ({emargin}) · consistency {_cons_pair(g)}"]
                 + ([f"   {wphr}"] if wphr else [])
                 + [f"   👥 public {_public_evidence(g)}",
                    f"   🦈 line: {_line_phrase(pc.get('line_check'))}{frozen}"])
        mp = _money_phrase(g)
        if mp:
            L.append(f"   {mp}")
        stp = _stance_phrase(g)
        if stp:
            L.append(f"   {stp}")
        pcheck = _public_check_phrase(g)
        if pcheck:
            L.append(f"   🔍 check: {pcheck}")
        bvp = _bvp_phrase(g)
        if bvp:
            L.append(f"   🥊 BvP {bvp}")
        pen = _pen_bvp_phrase(g)
        if pen:
            L.append(f"   🧯 pen BvP {pen}")
        pt = _pen_tax_phrase(g)
        if pt:
            L.append(f"   {pt}")
        fp = _form_phrase(g)
        if fp:
            L.append(f"   📈 form: {fp}")
        wx = _weather_phrase(g)
        if wx:
            L.append(f"   🌤 {wx}")
        ump = _ump_phrase(g)
        if ump:
            L.append(f"   🧑‍⚖️ {ump}")
        sit = _situational_phrase(g)
        if sit:
            L.append(f"   📅 {sit}")
        L.append(f"   ✅ {pc['reason']}"
                 + (f" · ⭐ {', '.join(star)}" if star else ""))

    for g in _by_win(picks):   # ranked by win chance: core leads, pitching-dog trails
        block(g)
    if not picks:
        L += ["", "No plays on the slate."]


    if no_action:
        L += ["", "— NO PLAY —"]
        for g in no_action:
            aa, ha = _abbrs(g)
            pc = g["pick_criteria"]
            tag = "🔴 " if g.get("state") == "live" else ""
            mp = _money_phrase(g)
            stc = _stance_phrase(g, brief=True)
            tm = _start_time(g)
            L.append(f"▫️ {tag}{aa} @ {ha}" + (f" ({tm})" if tm else "")
                     + f" — {pc.get('reason', 'no play')}"
                     + (f" · {mp}" if mp else "")
                     + (f" · {stc}" if stc else ""))
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
