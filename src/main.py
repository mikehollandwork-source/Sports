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

from . import consensus as consensus_rule
from .park_factors import bearing_for, hr_factor
from . import batter_look, good_dog, hitter_type, hr_pick, hrr_shadow, line_money, manual_picks, covers, prop_grade, early_lines, espn, fade_rule, grade, notify, pick_watch, prop_odds, props, public_sources, reddit, road_trip, tune, umpire, weather, wiki
from .analysis import (FORM_DIFF_FLOOR, LEAN_MIN_CONSISTENCY, LEAN_STRONG_MARGIN,
                       LINE_CONFIRM_MIN, PDOG_FIP_MIN, PICK_MIN_SIGNALS, PUBLIC_HEAVY,
                       UMP_K_EXTRA, UMP_MIN_GAMES, _canon_abbr, _implied, evaluate_game,
                       find_slate_line, line_confirms,
                       projected_from_margin)
from .mlb_api import (enrich_with_stats, hp_umpire, lineup as mlb_lineup,
                      results_for, schedule_for,
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

    # off-hours snapshots (absent until those crons have run for this date)
    early = early_lines.load(date)              # 6am ET reading
    evening = early_lines.load(date, "evening")  # 11pm-ET-the-night-before reading

    for g, r in zip(games, results):
        _attach_line(g, r, slate, early, evening)
        _attach_pm_quote(g, r, extra_public.get("polymarket_bets") or [])
        _attach_situational(g, r, date)
        # projected fair odds from our stats alone (no market data) - backend
        pc = r.get("pick_criteria") or {}
        margin = (pc.get("components") or {}).get("stat_edge", {}).get("margin")
        proj = projected_from_margin(margin)
        if proj:
            pc["projected"] = proj

    # CONSENSUS DECISION (2026-07-28): the board's pick logic. The old fade gate
    # above still computes every signal (kept as context and for the backtests),
    # but the PLAY is now decided here - back the side handle+tickets agree on,
    # when the line has moved against it. The order-book confirmation that used
    # to be required was removed 2026-09-29 after five independent tests put it
    # at zero; the book is still read, for display only. See src/consensus.py.
    cmetrics = consensus_rule.book_metrics(date)
    for r in results:
        _apply_consensus(r, cmetrics)

    # GOOD DOG TAG: a team the market usually favours, priced as a dog tonight.
    # Reporting only - it changes no pick. The backtest could not close the
    # question (main effects p = 0.154 and 0.277, null width +/-16 points), and
    # settling it needs about 2.5x the data, so the tag exists to accumulate
    # forward evidence while we wait. See src/good_dog.py.
    try:
        dog_rates = good_dog.favourite_rates(date)
        for r in results:
            (r.setdefault("pick_criteria", {}))["good_dog"] = good_dog.tag(r, dog_rates)
    except Exception as exc:                     # never let a tag break a board
        log.warning("good-dog tag failed: %s", exc)

    # LINE-AGAINST-THE-MONEY TAG: the price moved away from where the dollars
    # are. Reporting only - it changes no pick. It is the one candidate with a
    # mechanism that survived a walk-forward (6/8 blocks, median +10.2%), but its
    # 95% CI spans zero and the cell was selected over this same data, so only
    # games played from here on can settle it. See src/line_money.py.
    for r in results:
        try:
            (r.setdefault("pick_criteria", {}))["line_money"] = line_money.tag(r)
        except Exception as exc:                 # never let a tag break a board
            log.warning("line-money tag failed on %s: %s", r.get("game_pk"), exc)

    # Lock games that have already started: a started game keeps the pick/lean
    # status and the odds it had at first pitch (the closing line), so later polls
    # can't flip a pick to a lean or move the price after the game is underway.
    # a feed failure must not delete a posted pick; a started game's freeze
    # still wins, so this runs first
    _hold_on_missing_data(date, results)
    results = _lock_started_games(date, results)

    # Operator-entered picks go AFTER the lock, which is the only place they are
    # genuinely last. Applied before it, _lock_started_games restores the frozen
    # snapshot over the top and silently discards them - which is exactly what
    # happened on 2026-08-09: a pick entered 24 min before first pitch was wiped
    # by the lock window that opens 15 min before it, and never reached any board.
    manual_picks.apply(results, date)

    # Road-trip rule: a no-op until its pre-registered bar is met, at which
    # point it promotes itself and starts adding picks here. Placed after the
    # lock for the same reason manual picks are, and it never overwrites a game
    # the consensus rule already picked. Entries carry source="road_trip" so the
    # two populations stay separable in the ledger.
    try:
        road_trip.apply(results, date)
    except Exception as exc:
        log.warning("road-trip rule failed (board unaffected): %s", exc)

    # Fade: back the other side of any pick the rule has withdrawn. Last, so it
    # only ever touches games nothing else is picking - a game being backed now
    # is not a game that was withdrawn. Tagged source="fade" so the consensus
    # rule's own record stays readable separately.
    try:
        fade_rule.apply(results, date)
    except Exception as exc:
        log.warning("fade rule failed (board unaffected): %s", exc)

    # Last of all: collapse a market that arrived under two game ids, so the
    # board cannot post the same bet twice (see _dedupe_same_market).
    try:
        _dedupe_same_market(results)
    except Exception as exc:
        log.warning("duplicate-market dedupe failed (board unaffected): %s", exc)

    # Tag each game's live state (upcoming / live / final) for the board.
    try:
        states = results_for(date)
    except Exception as exc:
        log.warning("game-state fetch failed: %s", exc)
        states = {}
    for r in results:
        r["state"] = states.get(r.get("game_pk"), {}).get("state", "upcoming")

    # Best 1+ hit prop for each PLAY (the picked team's most-consistent bat in its
    # season wins). Only upcoming/live plays; fails soft so it never blocks the board.
    gbypk = {g.game_pk: g for g in games}
    for r in results:
        if r.get("state") == "final":
            continue
        pc0 = r.get("pick_criteria") or {}
        gd = pc0.get("good_dog") or {}
        # the read is computed for PLAYS and for watch-listed good dogs, since
        # "who gets a hit when they win" is asked of both. For a watch entry the
        # team is the good dog itself, not a bet side.
        adv = (_bet_side(pc0)[0] if _play(r) == "pick" else None) or gd.get("team")
        if not adv:
            continue
        gm = gbypk.get(r.get("game_pk"))
        if gm is None:
            continue
        is_home = adv == gm.home.name
        team = gm.home if is_home else gm.away
        try:
            # one fetch serves both: the prop (top bat) and the board's ranked
            # hit-in-wins line. Calling best_hit_prop separately would re-pull
            # the lineup and every game log.
            opp_sp = (gm.away if is_home else gm.home).probable_pitcher
            ranked = props.hit_in_wins_ranked(
                gm.game_pk, team.team_id, date, is_home,
                opp_pitcher_id=opp_sp.player_id if opp_sp else None)
            if opp_sp:
                r["pick_criteria"]["opp_starter"] = opp_sp.name
            # the conditions term, per hitter, from his batted-ball profile
            fits = _fits_for(r, ranked, team.team_id, date)
            # the platoon term: his AVG against THIS starter's hand, a
            # several-hundred-PA sample, against BvP's handful
            plat = _platoon_for(ranked, getattr(opp_sp, "hand", None), int(date[:4]))
            for b in ranked:
                if b.get("player_id") in plat:
                    b["platoon"] = plat[b["player_id"]]
            scored = sorted(ranked,
                            key=lambda b: _prop_score(b, fits.get(b.get("player_id"), 0)),
                            reverse=True)
            prop = scored[0] if scored else None
            if prop:
                # Only buy a price for a game that has NOT started. An in-game
                # price answers a different question - the market probe proved
                # it, returning Over 0.5 hits at +208 on a game two hours old
                # when that market prices near -200 pre-game - and the per-day
                # cache would then freeze that wrong price for the rest of the
                # day. Skipping it also stops spending credits on games that can
                # no longer be bet.
                upcoming = r.get("state") == "upcoming"
                line = (prop_odds.hit_line(date, prop["player"], gm.away.name,
                                           gm.home.name)
                        if upcoming else None)
                if line is not None:
                    prop["odds"] = line          # real 1+ hit price (else assumed at grade time)
                fit = fits.get(prop.get("player_id"), 0)
                prop["fit"] = fit
                prop["prop_score"] = round(_prop_score(prop, fit), 4)
                # Stamped so the prop ledger stays separable: entries before this
                # were chosen by hit-rate-in-wins, which is a different population.
                prop["selector"] = PROP_SELECTOR
                # The gate applies to a POSTED prop, i.e. a play. A good-dog
                # watch entry's hit block is context, not a bet, so it is left
                # alone - it is already labelled NOT A BET.
                held = _prop_withheld(prop, r) if _play(r) == "pick" else None
                if held:
                    r["pick_criteria"]["prop_withheld"] = held
                    log.info("prop withheld on %s: %s", r.get("game_pk"),
                             held["reason"])
                else:
                    r["pick_criteria"]["prop"] = prop
                # SHADOW ONLY, NEVER BET: the same hitter's hits+runs+RBIs over
                # 1.5. 1+ hit is a ~63% event priced near -200 (66.7% break-even)
                # so the hold eats the edge; H+R+RBI 1.5 was +105 on 2026-10-03,
                # a 48.8% break-even - the same read with 16 points less hold.
                # Whether the read transfers is unknown and cannot be
                # back-tested: those prices were never captured. So it is logged
                # to its own book and left alone, like the watch tags.
                # Plays only - it costs one extra API credit per game per day.
                if _play(r) == "pick" and upcoming:
                    try:
                        hrr = prop_odds.hrr_line(date, prop["player"],
                                                 gm.away.name, gm.home.name)
                        if hrr.get("over") is not None:
                            r["pick_criteria"]["shadow_hrr"] = {
                                "player": prop["player"],
                                "player_id": prop.get("player_id"),
                                "market": "hits+runs+RBIs over 1.5",
                                "over": hrr["over"], "under": hrr.get("under"),
                                "bet": False}
                    except Exception as exc:
                        log.warning("hrr shadow line failed on %s: %s",
                                    r.get("game_pk"), exc)
                for b in scored:
                    b["fit"] = fits.get(b.get("player_id"), 0)
                r["pick_criteria"]["hit_bats"] = scored[:3]
                # HOME RUN PICK, from the WHOLE lineup - see _attach_hr_prop
                # for why the three posted bats are the wrong pool for it.
                if _play(r) == "pick" and upcoming:
                    try:
                        _attach_hr_prop(r, team, gm, is_home, date)
                    except Exception as exc:
                        log.warning("hr prop failed on %s: %s",
                                    r.get("game_pk"), exc)
        except Exception as exc:
            log.warning("prop failed for %s: %s", r.get("game_pk"), exc)

    picks = [_bet_side(r["pick_criteria"])[0] for r in results if _play(r) == "pick"]
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


# HOTFIX 2026-09-25: one market, two game ids.
# Baltimore @ NY Yankees arrived as game_pk 823489 and 823491, five minutes
# apart (4:05 and 4:10 PM). They are not a doubleheader - the order-book log
# shows both tracking OPPOSITE SIDES of a single Polymarket market: identical
# reading timestamps, and bid/ask sizes that are exact mirrors (52.36/2891.84
# against 2891.84/52.36). Because the readings mirror, so does everything
# derived from them (drift -0.055/+0.055, imbalance -0.702/+0.702), and the
# rule resolved both ids to the same bet. The board posted "BET New York
# Yankees -115" twice, which is two units of exposure to one outcome and would
# have booked into the ledger twice.
#
# A real doubleheader is hours apart (Cubs @ Boston, 1:05 and 5:35 PM), so a
# 30-minute window separates the two cases without touching legitimate ones.
# This is the narrow fix; deduping on market identity belongs in the schedule
# layer where the ids are read, not here.
DUP_WINDOW = dt.timedelta(minutes=30)


def _dedupe_same_market(results: list) -> int:
    """Drop a pick that repeats another pick's matchup within DUP_WINDOW."""
    by_matchup: dict = {}
    for r in results:
        if (r.get("pick_criteria") or {}).get("play") != "pick":
            continue
        by_matchup.setdefault(r.get("matchup") or "", []).append(r)

    dropped = 0
    for games in by_matchup.values():
        if len(games) < 2:
            continue
        games.sort(key=lambda g: (g.get("game_datetime") or "", g.get("game_pk") or 0))
        kept, kept_start = games[0], _parse_iso(games[0].get("game_datetime"))
        for g in games[1:]:
            st = _parse_iso(g.get("game_datetime"))
            if (kept_start and st
                    and abs(st - kept_start) <= DUP_WINDOW):
                pc = g["pick_criteria"]
                pc["play"] = "stay_away"
                pc["status"] = "NO PLAY"
                pc["reason"] = (
                    f"duplicate market — same matchup as game "
                    f"{kept.get('game_pk')} starting within 30 minutes; one "
                    "market listed under two game ids, so this would double "
                    "the same bet")
                dropped += 1
            else:
                kept, kept_start = g, st        # a real doubleheader
    if dropped:
        log.warning("dropped %d duplicate-market pick(s)", dropped)
    return dropped


def _hold_on_missing_data(date: str, results: list) -> int:
    """Keep an announced pick alive when a FEED failed, not when a gate failed.

    Changes nothing about what qualifies. A game the rule never picked stays a
    no-play, and a pick whose gate genuinely stopped passing - the money split,
    the line moved the wrong way - is still withdrawn exactly as before. The
    only case touched is the one where this board cannot evaluate the game at
    all because data is missing, and the previous committed board had it as a
    pick. Then the last good evaluation stands instead of the pick vanishing.

    This is the other half of the 2026-09-29 bug. Not substituting the opening
    price stopped a feed failure from looking like a flat line; this stops it
    from silently removing a bet that was already posted to Telegram.

    Reuses the committed board as the snapshot, the same source
    _lock_started_games uses, and runs BEFORE it so a started game's freeze
    still wins.
    """
    prev_path = OUTPUT_DIR / f"picks_{date}.json"
    if not prev_path.exists():
        return 0
    try:
        prev = {g["game_pk"]: g
                for g in json.loads(prev_path.read_text()).get("games", [])}
    except (OSError, ValueError):
        return 0
    held = 0
    for r in results:
        pc = r.get("pick_criteria") or {}
        if pc.get("play") == "pick":
            continue                       # still qualifying; nothing to hold
        if "unavailable" not in (pc.get("reason") or "").lower():
            continue                       # a real gate failure, not a feed one
        snap = prev.get(r.get("game_pk")) or {}
        spc = snap.get("pick_criteria") or {}
        if spc.get("play") != "pick":
            continue                       # was never a pick; nothing to hold
        r["pick_criteria"] = {**spc, "held_stale": True}
        held += 1
    if held:
        log.info("held %d pick(s) at their last good reading (feed unavailable)", held)
    return held


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


def _line_windows(o, evening, morning, c) -> dict:
    """Split an open->current move by WHEN it happened, from the snapshot files:
    strike (open->11pm the night before), overnight (11pm->6am), early (open->6am,
    the whole sharp window) and late (6am->current, the public window) - all as
    implied-probability shifts toward our side. `timing` = which side of the 6am
    cut carried a real move (>= LINE_CONFIRM_MIN). Only windows whose snapshot
    exists are emitted; empty dict when open/current are missing."""
    if o is None or c is None:
        return {}
    out: dict = {}
    if morning is not None:
        es, ls = round(_implied(morning) - _implied(o), 3), round(_implied(c) - _implied(morning), 3)
        eh, lh = es >= LINE_CONFIRM_MIN, ls >= LINE_CONFIRM_MIN
        out.update(morning=morning, early_shift=es, late_shift=ls,
                   timing="early" if eh and not lh else "late" if lh and not eh
                          else "both" if eh and lh else None)
    if evening is not None:
        out["evening"] = evening
        out["strike_shift"] = round(_implied(evening) - _implied(o), 3)
        if morning is not None:
            out["overnight_shift"] = round(_implied(morning) - _implied(evening), 3)
    return out


def _prob_to_american(p: float) -> int:
    """Implied win probability -> the equivalent American moneyline."""
    return -int(round(100 * p / (1 - p))) if p >= 0.5 else int(round(100 * (1 - p) / p))


def _attach_pm_quote(game, result: dict, pm_rows: list) -> None:
    """Polymarket quote for the advantage side (STAGE 1 of auto-betting: read-only).
    A Polymarket price in cents IS the breakeven win probability, so comparing it
    to the book moneyline's implied probability says which venue sells our side
    cheaper. Recorded in the snapshot (pick_criteria.pm_quote) so PM's value vs
    the book can be graded over time before any real order is ever placed."""
    pc = result.get("pick_criteria") or {}
    adv = pc.get("advantage_team")
    if not adv or not pm_rows:
        return
    a, h = _canon_abbr(game.away.abbreviation), _canon_abbr(game.home.abbreviation)
    row = next((x for x in pm_rows if _canon_abbr(x["away_abbr"]) == a
                and _canon_abbr(x["home_abbr"]) == h), None)
    if not row:
        return
    side = "home" if adv == game.home.name else "away"
    pct = row.get(f"{side}_pct")
    if not isinstance(pct, (int, float)) or not 1 <= pct <= 99:
        return
    q = {"pm_pct": int(pct), "pm_american": _prob_to_american(pct / 100)}
    ml = pc.get("advantage_moneyline")
    if ml is not None:
        diff = round((_implied(int(ml)) - pct / 100) * 100, 1)  # +ve = PM cheaper
        q["edge_pts"] = diff
        q["vs_book"] = "better" if diff >= 1 else "worse" if diff <= -1 else "same"
    pc["pm_quote"] = q


def _attach_line(game, result: dict, slate: list, early: dict | None = None,
                 evening: dict | None = None) -> None:
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

    # With the off-hours snapshots (early_lines), split that move by WHEN it
    # happened - 11pm strike / overnight / daytime windows - plus the sharp-book
    # (Pinnacle) morning price for our side. Recording + display only - the
    # confirms status above stays the pure open->current signal.
    em = find_slate_line(game, (early or {}).get("espn") or [])
    ev = find_slate_line(game, (evening or {}).get("espn") or [])
    info.update(_line_windows((e or {}).get(f"{side}_open"),
                              (ev or {}).get(f"{side}_current"),
                              (em or {}).get(f"{side}_current"),
                              (e or {}).get(f"{side}_current")))
    for p in (early or {}).get("pinnacle") or []:
        if (p.get("away_name", "").casefold() == game.away.name.casefold()
                and p.get("home_name", "").casefold() == game.home.name.casefold()):
            info["pinny_morning"] = p.get(f"{side}_ml")
            break

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
    shift = info.get("implied_shift")
    # CORE signals carry a play; favorite, BvP AND now LINE are supporting only.
    # The 335-game leak-finder: line as a standalone core bled (line-only -9.3%
    # ROI, line+consistency-no-margin -20%), because our line signal can't tell a
    # sharp move from a public one and public-window moves grade -17%. Dropping it
    # from core lifts the board 62%->65% / +8.9%->+13.4% ROI. margin (+34.6%) and
    # consistency (+8.1%) are the only edges that carry a play alone; line still
    # counts toward signals_hit / star / win-prob.
    core_hit = m_hit or c_hit
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
    # the house is quietly fading). Backend-only now: it gates the star but is not
    # shown on the board (stored in pc["book_stance"]/["stance_warning"]).
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
        qualifies = core_hit and not is_tail  # fade + core
    else:
        is_tail = False
        qualifies = core_hit                  # no book read -> core alone
    # ONE play tier (user call - no more pick/lean split): a game is a PLAY when it
    # clears the fade gate + core signal and isn't a mild-public fade.
    # PITCHING-DOG BYPASS — REMOVED (2026-07-28). It let a game skip BOTH the fade
    # and mild-public gates on the strength of a 186-game backtest, and has since
    # gone 0-5 (-100% ROI) - it has never once won, in-sample or holdout. A bypass
    # that overrides safety gates has to earn it; this never did. pitching_dog is
    # still computed and shown as a signal, it just can't carry a play by itself.
    # (Also tried an extra underdog gate — dogs need margin/pitching — but the fade
    # gate already cuts the losing dogs; the survivors went 4-3 +21%, so it dropped
    # winners and LOWERED ROI. Reverted, kept as a note.)
    playable = qualifies and not mild_public
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
            why = "core signal but not a fade setup — no play"
        elif not core_hit and hits:
            why = f"only {', '.join(hits)} — no core signal (margin/consistency), no play"
        else:
            why = "0/8 signals — no play"
        pc["reason"] = why
        # REVERSAL PROMOTION — REMOVED (2026-07-28). Mined from the backtest at
        # 24-12/+25% on the no-play subset, it collapsed the moment it went live:
        # 5-11 (31%), -6.56u, -41% ROI on the real ledger - 59% of the system's
        # entire all-time deficit from 10% of its bets. The holdout says it is
        # exactly BACKWARDS: those same games bet on our STAT side returned +25.6%
        # while fading them returned -31.7%. Textbook curve-fit; do not resurrect
        # without out-of-sample evidence. Past entries stay in the record untouched.


def _bet_side(pc: dict) -> tuple:
    """(team, moneyline) actually being bet. Consensus picks carry bet_team /
    bet_moneyline; older frozen snapshots fall back to the advantage side so
    history renders and grades exactly as it did."""
    if pc.get("bet_team"):
        return pc.get("bet_team"), pc.get("bet_moneyline")
    return pc.get("advantage_team"), pc.get("advantage_moneyline")


def _apply_consensus(r: dict, metrics: dict) -> None:
    """Decide the play with the consensus rule, overriding the legacy fade gate."""
    pc = r.setdefault("pick_criteria", {})
    play = consensus_rule.evaluate(r, metrics)
    # Record how the line moved relative to the consensus side even when the game
    # is filtered out, so the counterfactual bucket stays gradeable from snapshots.
    maj = (r.get("public_majority") or {}).get("team")
    if maj:
        pc["line_vs_money"] = consensus_rule.line_tag(r, maj)
    if play:
        pc.update(play="pick", status="pick",
                  bet_team=play["bet"], bet_moneyline=play["odds"],
                  reason=play["reason"], starred=[],
                  consensus={"drift": play["drift"], "imbalance": play["imbalance"],
                             "line": play.get("line")},
                  win_prob=68, win_driver="consensus")
        return
    pc.update(play="stay_away", status="stay_away",
              bet_team=None, bet_moneyline=None, starred=[],
              reason=consensus_rule.reject_reason(r, metrics))


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
        tag = {"early": " · moved overnight (sharp window)",
               "late": " · moved today (public window)",
               "both": " · moved in both windows"}.get(lc.get("timing"), "")
        if (lc.get("strike_shift") or 0) >= LINE_CONFIRM_MIN and lc.get("timing") in ("early", "both"):
            tag = " · sharps struck the fresh opener"   # moved within hours of posting
        return f"IN OUR FAVOR ✓ ({arrow}){tag}"
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


def _stay_line(g: dict) -> str:
    """One-liner for a NO-ACTION game (nothing the system likes; never booked)."""
    pc = g["pick_criteria"]
    mp = _money_phrase(g)
    tm = _start_time(g)
    head = f"▫️ {_state_tag(g)}{g['matchup']}" + (f" ({tm})" if tm else "")
    return (f"{head} — {pc.get('reason', 'no play')}"
            + (f" · {mp}" if mp else ""))


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
    mark = "⭐" if star else "✅"
    wphr = _win_phrase(g)
    lines = [
        f"{mark} **{kind} {adv}**{_ml_str(pc)} — {tag}{g['matchup']}"
        + (f" · {_start_time(g)}" if _start_time(g) else "")
        + (f" · {wphr}" if wphr else "")
        + (f" · ⭐ {', '.join(star)}" if star else ""),
        f"   • stat edge: {edge}",
        f"   • public: {pub}",
        f"   • consistency: {cons}",
    ]
    mp = _money_phrase(g)
    if mp:
        lines.append(f"   • {mp}")
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
    board = _board_games(games)
    picks = _by_win([g for g in board if _play(g) == "pick"])
    # Minimal board: only the plays, one clean line each, ranked by win chance.
    # No-plays are still recorded in the picks JSON (backend), just not shown.
    out = [f"# MLB Board — {date}", ""]
    if picks:
        out += [_pick_line(g, _splits_or_empty(board)) for g in picks]
    else:
        out.append("_No plays on the board._")
    dogs = _good_dog_lines(board, picks)
    if dogs:
        out += ["", "## Watching — good dogs (NOT bets)", "",
                "_Usually-favoured teams priced as dogs tonight. Labelled to "
                "gather forward evidence; the backtest could not settle them. "
                "**Do not bet these.**_", ""] + dogs
    out += ["", grade.records_block()]
    # props stay backend-only for now (still computed + tracked in prop_ledger.json,
    # just not shown on the board)
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


# Scan markers on a team's own when-picked record. The BAR IS NOT FITTED to our
# results: +/-10% is about two units of bookmaker hold, i.e. the margin at which a
# record is doing something other than paying the vig. Picking the cut by eye off
# our own table is how this project produced three thresholds that flattered a
# candidate, so it is derived from market structure instead.
#
# These mark HISTORY, not skill. A permutation test shuffling which team each
# settled bet belonged to puts the spread of per-team ROI at p = 0.10 (n >= 8),
# 0.20 (n >= 10) and 0.015 (n >= 5) - significant at exactly one of three cuts,
# which is noise with a threshold attached. So a star does not mean the team is a
# better bet; it means we have won money on it so far.
PICK_REC_MIN = 8          # same bar good_dog uses before it will show a split
PICK_REC_HOT = 0.10
PICK_REC_COLD = -0.10


def _when_picked(team: str | None) -> str:
    """'20-3 · +59.7% ⭐', or '' when we never have. Callers add the label.

    History, not a signal. It is on the board so a pick arrives with its own
    track record rather than looking like a fresh idea, and so a team we have
    been repeatedly wrong about is visible at the moment of betting it.

    The star/ice is a scan aid on that same number, shown only once there are
    PICK_REC_MIN picks. Below that the record still prints unmarked - a thin
    sample is worth reading, just not worth flagging.
    """
    if not team:
        return ""
    rec = grade.record_when_picked(team)
    if not rec:
        return ""
    w, l, roi = rec
    mark = ""
    if w + l >= PICK_REC_MIN:
        mark = (" ⭐" if roi >= PICK_REC_HOT else
                " 🧊" if roi <= PICK_REC_COLD else "")
    return f"{w}-{l} · {roi:+.1%}{mark}"


def _pick_line(g: dict, sp: dict | None = None) -> str:
    """One board entry, written as an instruction rather than a notation.

    'BET Texas Rangers -125' leaves nothing to work out; the old
    '✅ TEX -125 vs NYM' made the reader decode an abbreviation and a tick to
    find the team. The opponent, venue and first pitch go on a second,
    indented line so the team and the price are never competing for attention.

    Fades are tagged in words - they count in the record like anything else, so
    the tag says where the pick came from and nothing more."""
    pc = g["pick_criteria"]
    aa, ha = _abbrs(g)
    away, home = g["matchup"].split(" @ ")
    bet_team, ml = _bet_side(pc)
    at_home = bet_team == home
    opp_ab = aa if at_home else ha
    mls = f" {ml:+d}" if isinstance(ml, int) else ""
    star = " ⭐" if _star(pc) else ""
    tag = "  ·  fade" if pc.get("source") == "fade" else ""
    gd = pc.get("good_dog") or {}
    # only label it when the team we are BACKING is the good dog
    if gd.get("team") == bet_team:
        tag += "  ·  good dog"
    if pc.get("held_stale"):
        tag += "  ·  ⚠ held (line feed down)"
    head = f"✅ BET {bet_team}{mls}{star}{tag}"
    where = f"{'vs' if at_home else 'at'} {opp_ab}"
    live = "🔴 LIVE · " if g.get("state") == "live" else ""
    st = _start_time(g)
    sub = f"     {live}{where}" + (f" · {st}" if st else "")
    lines = [head, sub]
    wp = _when_picked(bet_team)
    if wp:
        lines.append(f"     when we pick {ha if at_home else aa}: {wp}")
    # how often this team wins at this kind of price - the same trust check the
    # watch list carries, on the bet itself. `applies` marks which of the two
    # numbers tonight's price puts in play.
    if sp:
        # both sides, same as the watch list: the bet team's record only reads
        # against the side it is facing
        applies = "fav" if isinstance(ml, int) and ml < 0 else "dog"
        opp = home if bet_team == away else away
        for team, ab, mark in ((bet_team, ha if at_home else aa, applies),
                               (opp, aa if at_home else ha, None)):
            txt = good_dog.split_text(team, sp, mark)
            if txt:
                lines.append(f"     {ab}  {txt}")
    lines += _hit_lines(g)
    return "\n".join(lines)


# Ranking the hit read. Form and BvP decide the order; hit-in-wins is context.
#
# BvP CANNOT be used raw. Career samples against one pitcher are tiny - tonight's
# board carries a 1.333 OPS on 6 PA and a .083 on 12 - so a raw sort puts the
# smallest samples on top, which is the error this project keeps catching
# elsewhere. Each line is shrunk toward league-average OPS by its own sample:
#
#     weight = pa / (pa + BVP_PRIOR)
#
# so 6 PA keeps under a quarter of its deviation and 24 PA keeps over half. A
# hitter who has never faced the starter contributes exactly zero rather than
# being dropped - no information is not bad information.
LEAGUE_OPS = 0.710     # roughly league-average OPS; the point BvP shrinks toward
BVP_PRIOR = 20         # PA of imaginary league-average history added to each line


# PROP SELECTION. The posted prop used to be ranked[0] - the top hit rate in the
# team's season WINS. That is the wrong statistic for a prop bet, and measurably
# so: the posted props have hit 62.7% (89-53) against a 66.7% break-even at their
# median -200 price, for -8.63u. A rate computed INSIDE wins is conditioned on the
# outcome, so it partly measures "the team wins when he hits" rather than "he
# hits", and it is inflated for every regular.
#
# A prop asks P(he gets a hit tonight). The honest base for that is his ALL-GAMES
# rate, then adjusted by what we know about tonight:
#   all_rate  how often he actually gets a hit, unconditioned
#   form      his last-5 rate against his OWN season rate
#   bvp       shrunk by sample against the opposing starter
#   fit       his batted-ball profile against tonight's air and starter
#
# Everything is kept on a hit-probability scale and ADDED UNWEIGHTED: with no
# evidence that one of these predicts a hit better than another, a weighting would
# be a free parameter tuned on nothing. (This replaces `_hit_score`, which ordered
# the DISPLAY by form + BvP only; it had no other caller and is removed.)
# The one scaling judgement is fit/100, which caps conditions at about +/-5
# points of hit probability - stated as a judgement, not a fit.
PROP_FIT_SCALE = 100.0
# Individual platoon splits are noisy and regress hard - far harder than their
# sample size alone suggests - so a hitter's own vs-hand delta is shrunk toward
# ZERO, i.e. toward "he is the same against both hands". Half weight at 300 PA is
# a conservative stated judgement, NOT fitted to our results; the alternative, no
# shrinkage at all, would let a 60-PA split swing the pick.
#
# The delta is on BATTING AVERAGE, not OPS, because the prop asks for a HIT.
# (The older BvP term is still an OPS delta. It is pre-existing and feeds the
# display, so it is left alone, but the two matchup terms are not on the same
# scale and that is worth knowing.)
PLATOON_PRIOR_PA = 300
PROP_SELECTOR = "all_rate+form+bvp+fit+platoon"   # stamped so the ledger stays separable


def _prop_score(b: dict, fit: int = 0) -> float:
    """Estimated hit likelihood for tonight, on a probability-ish scale.

    FORM IS SHRUNK, for the same reason BvP is. `form` is computed over
    props.RECENT_GAMES games, so a +39% reading is five games of evidence, and
    taking it at face value would say a hitter is 39 points more likely to get a
    hit tonight than his own season rate. It gets the same sample-size treatment
    BvP gets, with the prior set EQUAL TO the window - so at exactly the window
    length form carries half its face value. The prior is the window rather than
    a number picked to produce an answer.
    """
    base = (b.get("all_rate") or 0) / 100.0
    n = props.RECENT_GAMES
    form = ((b.get("form") or 0) / 100.0) * (n / (n + n))
    bvp = b.get("bvp") or {}
    pa, ops = bvp.get("pa") or 0, bvp.get("ops") or 0.0
    edge = ((ops - LEAGUE_OPS) * (pa / (pa + BVP_PRIOR))) if pa > 0 else 0.0
    platoon = (b.get("platoon") or {}).get("shrunk") or 0.0
    return base + form + edge + platoon + (fit / PROP_FIT_SCALE)


def _fits_for(game: dict, bats: list, team_id: int, date: str) -> dict:
    """{player_id: fit score} from each hitter's batted-ball profile against
    tonight's conditions. Fails soft to {} - a missing profile costs the
    conditions term, and must never cost the board."""
    out: dict = {}
    cold_or_in = _conditions_against(game)
    if not cold_or_in:
        return out                       # nothing to adjust for
    try:
        season = int(date[:4])
        for b in bats:
            pid = b.get("player_id")
            if not pid:
                continue
            st = hitter_type.season_line(pid, season)
            if st:
                out[pid] = hitter_type.fit(hitter_type.profile(st))[0]
    except Exception as exc:
        log.warning("conditions fit unavailable: %s", exc)
        return {}
    return out


def _hr_side(r: dict, bat_team, opp_team, gm, is_home: bool, date: str,
             shared: dict) -> list[dict]:
    """Scored HR candidates for ONE lineup, against ITS OWN opposing pitching.

    Each side faces a different starter and bullpen and has its own win
    probability, so the two lineups cannot share those terms - only the park,
    wind and temperature, which are the game's.
    """
    try:
        hitters = mlb_lineup(gm.game_pk, bat_team.team_id, date, is_home)
    except Exception as exc:
        log.warning("hr lineup unavailable for %s: %s", bat_team.name, exc)
        return []
    names = {h.player_id: h.name for h in hitters if getattr(h, "player_id", None)}
    if not names:
        return []
    season = int(date[:4])
    opp_sp = opp_team.probable_pitcher
    sa = (r.get("statistical_advantage") or {}).get(
        "away" if is_home else "home") or {}
    pen, pen_ip = hr_pick.pen_hr9(opp_team.team_id, date,
                                  getattr(opp_sp, "player_id", None), season)
    oppf, oppnote = hr_pick.opposing_hr9_factor(
        getattr(opp_sp, "player_id", None), pen,
        (float(sa["starter_ip_last5"]) / 5.0) if sa.get("starter_ip_last5")
        else hr_pick.STARTER_IP_DEFAULT, season)
    wmult, wnote = hr_pick.win_factor(shared["p_win"].get(bat_team.name))
    slots = {h.player_id: i + 1 for i, h in enumerate(hitters)
             if getattr(h, "player_id", None)}
    rows = hr_pick.score_hitters(
        list(names), season, getattr(opp_sp, "player_id", None),
        shared["park"], wind=shared["wind"], min_pa=hr_pick.MIN_PA,
        min_hr=hr_pick.MIN_HR, temp=shared["temp"],
        hand=getattr(opp_sp, "hand", None), slots=slots, opp_factor=oppf,
        win=wmult, team=bat_team.name)
    for row in rows:
        row["name"] = names.get(row["player_id"])
        row["opposing"] = oppnote
        row["bullpen_ip"] = round(pen_ip, 1)
        row["win_note"] = wnote
        row["opp_hand"] = getattr(opp_sp, "hand", None)
    return rows


def _attach_hr_prop(r: dict, team, gm, is_home: bool, date: str) -> None:
    """Most likely home run in the GAME - either lineup - or nothing.

    BOTH TEAMS, not just the side the board backs, and not the three posted
    bats. The three are chosen to GET A HIT, which favours contact and penalises
    the strikeout rate that comes with power. Restricting to our own side then
    throws away half the hitters in the game for no reason - the question is who
    is likeliest to homer, not who is on our ticket.
    
    The two sides are made comparable by a WIN-PROBABILITY factor derived from
    hr_side_scan: winners homer at 1.73x losers over 26,141 batter-games, so a
    bat on the likely loser is discounted (x0.73 at the extreme) rather than
    excluded. Park, wind and temperature are shared; the opposing starter,
    bullpen and hand are per side.

    Booked into its own `home_runs` book in the prop ledger, never mixed into
    `singles`.
    """
    away_name, home_name = (r.get("matchup") or " @ ").split(" @ ")
    wc = _wind_component(r, home_name)
    cond = _contact_conditions(r, team.name)
    if (wc and wc[0] == "in") or cond.startswith("contact conditions: AGAINST THE BAT"):
        why = ("wind is blowing IN" if (wc and wc[0] == "in")
               else "conditions are against the bat")
        r["pick_criteria"]["hr_withheld"] = {
            "reason": f"no HR pick — {why} ({cond.split(': ', 1)[-1]})"}
        log.info("hr prop withheld on %s: %s", r.get("game_pk"), why)
        return

    w = r.get("weather") or {}
    wf, wnote = hr_pick.wind_factor(w.get("wind_mph"),
                                    wc[1] if wc else 0.0,
                                    wc[0] if wc else None)
    tf, tnote = hr_pick.temp_factor(w.get("temp_f"), w.get("roof"))
    pc = r.get("pick_criteria") or {}
    # de-vigged win probability per team, from the board's own two prices
    p_win: dict = {}
    adv, a_ml = pc.get("advantage_team"), pc.get("advantage_moneyline")
    o_ml = pc.get("opponent_moneyline")
    if adv and isinstance(a_ml, int) and isinstance(o_ml, int):
        ia, io = _implied(a_ml), _implied(o_ml)
        tot = ia + io
        if tot > 0:
            opp = home_name if adv == away_name else away_name
            p_win = {adv: ia / tot, opp: io / tot}
    shared = {"park": hr_factor(gm.home.name), "wind": wf, "temp": tf,
              "p_win": p_win}

    cands = (_hr_side(r, gm.away, gm.home, gm, False, date, shared)
             + _hr_side(r, gm.home, gm.away, gm, True, date, shared))
    if not cands:
        r["pick_criteria"]["hr_withheld"] = {
            "reason": f"no HR pick — nobody in either lineup has the season "
                      f"behind it ({hr_pick.MIN_PA}+ PA and "
                      f"{hr_pick.MIN_HR}+ HR)", "wind": wnote}
        log.info("hr prop withheld on %s: no qualifying bat", r.get("game_pk"))
        return
    cands.sort(key=lambda c: -c["p_game"])
    top = cands[0]
    if top["p_game"] < hr_pick.HR_FLOOR:
        r["pick_criteria"]["hr_withheld"] = {
            "best": top.get("name"), "team": top.get("team"),
            "p_game": round(top["p_game"], 4),
            "floor": round(hr_pick.HR_FLOOR, 4),
            "season": f"{top['hr']}/{top['pa']}", "wind": wnote,
            "reason": f"no HR pick — best in the game is "
                      f"{top['p_game']:.1%}, under the "
                      f"{hr_pick.HR_FLOOR:.1%} a league-average hitter manages"}
        log.info("hr prop withheld on %s: under the floor", r.get("game_pk"))
        return
    name = top.get("name")
    if not name:
        return
    row = {"player": name, "player_id": top["player_id"],
           "team": top.get("team"), "market": "1+ home run",
           "p_game": round(top["p_game"], 4),
           "season": f"{top['hr']}/{top['pa']}",
           "recent": f"{top['recent_hr']}/{top['recent_pa']}",
           "iso": top["iso"], "pitcher_factor": top["pitcher_factor"],
           "park": top["park"], "wind": wnote, "temp": tnote,
           "wind_factor": top.get("wind_factor"),
           "slot": top.get("slot"), "expected_pa": top.get("expected_pa"),
           "form_factor": top.get("form_factor"), "form": top.get("form_note"),
           "win_factor": top.get("win_factor"), "win": top.get("win_note"),
           "vs_hand": (None if top.get("hand_rate") is None else
                       f"{top['hand_rate']*top['hand_pa']:.0f}/{top['hand_pa']}"
                       f" vs {top.get('opp_hand') or '?'}HP"),
           "opposing": top.get("opposing"), "bullpen_ip": top.get("bullpen_ip"),
           "floor": round(hr_pick.HR_FLOOR, 4),
           "pool": "both lineups", "considered": len(cands),
           "our_side": top.get("team") == (pc.get("bet_team") or team.name)}
    try:
        line = prop_odds.hr_line(date, name, gm.away.name, gm.home.name)
        if line.get("over") is not None:
            row["odds"] = line["over"]
            if line.get("under") is not None:
                row["under"] = line["under"]
    except Exception as exc:
        log.warning("hr line unavailable for %s: %s", name, exc)
    r["pick_criteria"]["hr_prop"] = row


def _break_even(odds: int) -> float:
    """The hit rate a 1+ hit bet needs at this price just to break even."""
    o = int(odds)
    return abs(o) / (abs(o) + 100.0) if o < 0 else 100.0 / (o + 100.0)


def _prop_withheld(prop: dict, game: dict) -> dict | None:
    """Why this prop should NOT be posted, or None to post it.

    THE BAR IS THE PRICE, NOT A THRESHOLD I CHOSE. `_prop_score` is already on a
    hit-probability scale, so it is compared against the hit rate the actual price
    demands. A 1+ hit line at -213 needs 68.1%; at -335 it needs 77%, which
    nothing on these boards reaches.

    Applied ONLY when the night suppresses batted balls - cold, wind in, or a
    high-strikeout starter. On a neutral night the prop posts as before, because
    withholding there would be this gate inventing an opinion it has not earned.

    Why it exists: the posted props have hit 62.6% against a 68.1% break-even on
    the 91 entries with a real captured line, for -5.63u. The hit rate is not the
    problem; paying through it is.
    """
    score = prop.get("prop_score")
    if not isinstance(score, (int, float)) or not _conditions_against(game):
        return None
    odds = prop.get("odds", prop_grade.PROP_PRICE)
    try:
        need = _break_even(odds)
    except (TypeError, ValueError):
        return None
    if score >= need:
        return None
    return {"player": prop.get("player"), "score": round(score, 4),
            "need": round(need, 4), "odds": odds,
            "real_line": "odds" in prop,
            "reason": f"conditions against the bat and the read "
                      f"({score:.0%}) is under the {need:.0%} that "
                      f"{odds:+d} needs"}


def _platoon_for(bats: list, opp_hand: str | None, season: int) -> dict:
    """{player_id: {"hand", "avg", "pa", "delta", "shrunk"}} vs tonight's starter.

    `delta` is his AVG against that hand minus his OWN overall average, so it is
    the platoon swing rather than his quality. The overall average is the PA-
    weighted blend of his two hand splits, which costs no extra request.

    Fails soft to {} - a missing split costs the term, never the board.
    """
    out: dict = {}
    if opp_hand not in ("L", "R"):
        return out
    other_hand = "L" if opp_hand == "R" else "R"
    for b in bats:
        pid = b.get("player_id")
        if not pid:
            continue
        try:
            hands = batter_look.player_vs_hand(pid, season)
        except Exception as exc:
            log.warning("vs-hand split failed for %s: %s", pid, exc)
            continue
        same, other = hands.get(opp_hand) or {}, hands.get(other_hand) or {}
        try:
            a_s, pa_s = float(same.get("avg")), float(same.get("plateAppearances"))
        except (TypeError, ValueError):
            continue
        try:
            a_o, pa_o = float(other.get("avg")), float(other.get("plateAppearances"))
        except (TypeError, ValueError):
            a_o, pa_o = a_s, 0.0
        tot = pa_s + pa_o
        overall = ((a_s * pa_s + a_o * pa_o) / tot) if tot else a_s
        delta = a_s - overall
        w = pa_s / (pa_s + PLATOON_PRIOR_PA) if pa_s > 0 else 0.0
        out[pid] = {"hand": opp_hand, "avg": round(a_s, 3), "pa": int(pa_s),
                    "delta": round(delta, 3), "shrunk": round(delta * w, 4)}
    return out


def _conditions_against(g: dict) -> bool:
    """True when tonight actually suppresses batted balls - cold, wind blowing in,
    or a high-strikeout starter. Without one of those the profile term would be
    noise dressed as information, so it is simply not applied."""
    w = g.get("weather") or {}
    if isinstance(w.get("temp_f"), int) and w["temp_f"] <= TEMP_COLD:
        return True
    away, home = (g.get("matchup") or " @ ").split(" @ ")
    wind = _wind_component(g, home)
    if wind and wind[0] == "in":
        return True
    sa = g.get("statistical_advantage") or {}
    for side in ("home", "away"):
        k9 = (sa.get(side) or {}).get("starter_k9")
        if isinstance(k9, (int, float)) and k9 >= K9_POWER:
            return True
    return False


def _hit_lines(g: dict, winner: str | None = None) -> list[str]:
    """Who is most likely to get a hit if this pick wins, and the conditions.

    The percentage is hit rate in the team's season WINS, with the hitter's
    ALL-GAMES rate in brackets. That bracket is the point: the first number
    conditions on the outcome, so every regular's rate rises inside wins and a
    big gap mostly says "the team wins when he hits". A SMALL gap is the
    dependable bat, so the gap is what to read.
    """
    pc = g.get("pick_criteria") or {}
    held = pc.get("prop_withheld")
    if held:
        # the conditions line is the justification, so it stays
        out = [f"     NO PROP — {held['reason']}"]
        cond = _contact_conditions(g, winner or _bet_side(pc)[0])
        if cond:
            out.append(f"       {cond}")
        return out
    bats = pc.get("hit_bats") or []
    if not bats:
        return []
    sp = _surname(pc.get("opp_starter") or "") or "the starter"
    who = _abbr_of(g, winner) if winner else "they"
    out = [f"     LIKELY HITS (if {who} win{'s' if winner else ''})"]
    for b in bats:
        bits = [f"{b.get('player') or '?'}"]
        f = b.get("form")
        if f is not None:
            bits.append(f"form {f:+d}%" + ("  🔥" if b.get("super_hot") else ""))
        bits.append(_bvp_bit(b.get("bvp"), sp))
        # the vs-hand line, which is the big sample next to BvP's handful
        pl = b.get("platoon") or {}
        if pl.get("pa"):
            bits.append(f"vs {pl['hand']}HP {pl['avg']:.3f}".replace("0.", ".", 1)
                        + f" ({pl['pa']} PA, {pl['delta']:+.3f} vs himself)")
        hr, ar = b.get("hit_rate"), b.get("all_rate")
        # spelled out rather than "(usually X%)", which read as a hedge on the
        # first number instead of what it is: the same hitter across ALL games,
        # which is the only thing that makes the wins figure meaningful
        bits.append(f"hits in {hr}% of wins"
                    + (f", {ar}% of all games" if ar is not None else ""))
        out.append("       • " + "  ·  ".join(x for x in bits if x))
    hw = pc.get("hr_withheld")
    if hw:
        out.append(f"       {hw['reason']}")
    hp = pc.get("hr_prop")
    if hp:
        price = (f" {hp['odds']:+d}" if isinstance(hp.get("odds"), int)
                 else " (no line)")
        out.append(f"       💥 HR PICK: {hp['player']} 1+ HR{price}"
                   f"  ·  {hp['p_game']:.1%}  ·  {hp['season']} HR/PA"
                   f" season, {hp['recent']} last 15")
    sh = pc.get("shadow_hrr")
    if sh and sh.get("over") is not None:
        out.append(f"       ◻ tracking only, NOT a bet: {sh['player']} "
                   f"H+R+RBI o1.5 {sh['over']:+d}")
    cond = _contact_conditions(g, winner or _bet_side(pc)[0])
    if cond:
        out.append(f"       {cond}")
    return out


def _bvp_bit(bvp: dict | None, pitcher: str) -> str:
    """His career line against tonight's starter, or that he has not faced him.

    Career rather than season because per-season BvP samples are near-zero, and
    the PA count is always shown - a 1.200 OPS on 4 plate appearances is a
    coincidence, not a matchup, and hiding the sample is how it gets read as one.
    """
    if not bvp:
        return f"vs {pitcher} —"
    pa, ops = bvp.get("pa") or 0, bvp.get("ops") or 0.0
    if pa < 1:
        return f"never faced {pitcher}"
    return f"vs {pitcher} {ops:.3f}".replace("0.", ".", 1) + f" OPS ({pa} PA)"


def _surname(name: str) -> str:
    """Last name only - the board is read on a phone."""
    parts = (name or "").split()
    return parts[-1] if parts else name


# Wind, made park-relative. A compass string cannot say whether wind helps: a
# south wind blows OUT in a park facing north and IN in one facing south. The
# weather APIs report the direction wind comes FROM (met.no literally calls the
# field wind_from_direction), so the direction it blows TOWARD is that plus 180,
# and the component along the home-to-centre axis is the cosine of the angle
# between them.
#
# Only STRONG alignment is reported. The bearing table is approximate, so
# requiring the wind within ~60 degrees of the axis means a bearing wrong by
# 20-30 degrees weakens the read rather than reversing it. Light wind is
# ignored outright - 4 mph does not move a baseball whatever way it points.
WIND_MIN_MPH = 8
WIND_ALIGN = 0.5        # cos(60 degrees): how squarely the wind must run the axis


def _wind_component(g: dict, park_team: str | None) -> tuple[str, float] | None:
    """("out"|"in", strength 0-1) for tonight's wind, or None when unreadable."""
    w = g.get("weather") or {}
    if (w.get("roof") or "") == "closed":
        return None
    deg, mph = w.get("wind_deg"), w.get("wind_mph")
    bearing = bearing_for(park_team) if park_team else None
    if bearing is None or not isinstance(deg, (int, float)) \
            or not isinstance(mph, (int, float)) or mph < WIND_MIN_MPH:
        return None
    import math
    toward = (deg + 180) % 360                 # from-direction -> blowing-toward
    comp = math.cos(math.radians(bearing - toward))
    if abs(comp) < WIND_ALIGN:
        return None                            # crosswind: says nothing
    return ("out" if comp > 0 else "in", abs(comp))


# Contact conditions. Weather on its own says nothing about hits - what matters
# is whether the park, the umpire and the STARTER combine to put balls in play.
# A hot night in a big park is irrelevant behind a 12 K/9 arm and a wide-zone
# umpire, because the ball never gets hit.
#
# Wind is deliberately excluded. Turning a direction into "blowing out" needs
# each park's orientation, which this repo does not have, and guessing would
# manufacture a signal out of a compass reading.
#
# The thresholds below are conventional judgement calls, NOT fitted - nothing in
# this project has shown contact conditions predict hits, so this is labelled
# context and ranks nothing.
PARK_HOT, PARK_COLD = 1.02, 0.98
TEMP_HOT, TEMP_COLD = 80, 55
UMP_K_LOOSE, UMP_K_TIGHT = -0.5, 0.5     # ump_tend.k_extra: Ks above/below average
K9_CONTACT, K9_POWER = 7.5, 9.5


def _contact_conditions(g: dict, hitting_team: str | None) -> str:
    """Whether tonight favours the bat, from the things that decide contact.

    `hitting_team` is the side whose hitters are being read, so the STARTER
    considered is the one they face.
    """
    for_, against = [], []
    pf = g.get("park_factor")
    if isinstance(pf, (int, float)):
        if pf >= PARK_HOT:
            for_.append(f"park {pf:.2f}")
        elif pf <= PARK_COLD:
            against.append(f"park {pf:.2f}")

    w = g.get("weather") or {}
    t, roof = w.get("temp_f"), (w.get("roof") or "")
    if isinstance(t, int) and roof != "closed":     # a closed roof neutralises it
        if t >= TEMP_HOT:
            for_.append(f"{t}°F")
        elif t <= TEMP_COLD:
            against.append(f"{t}°F")

    away, home = (g.get("matchup") or " @ ").split(" @ ")
    wind = _wind_component(g, home)            # the park is the home team's
    if wind:
        way, strength = wind
        mph = (g.get("weather") or {}).get("wind_mph")
        txt = f"wind {mph} mph {way}" + ("" if strength >= 0.8 else " (angled)")
        (for_ if way == "out" else against).append(txt)

    tend = g.get("ump_tend") or {}
    ke, ump = tend.get("k_extra"), g.get("umpire_hp")
    if isinstance(ke, (int, float)) and ump:
        if ke <= UMP_K_LOOSE:
            for_.append(f"ump {_surname(ump)} {ke:+.1f} K/g")
        elif ke >= UMP_K_TIGHT:
            against.append(f"ump {_surname(ump)} {ke:+.1f} K/g")

    # the starter the hitting side actually faces
    opp_side = "home" if hitting_team == away else "away" if hitting_team == home else None
    sa = ((g.get("statistical_advantage") or {}).get(opp_side) or {}) if opp_side else {}
    k9, name = sa.get("starter_k9"), sa.get("probable_pitcher")
    if isinstance(k9, (int, float)) and name:
        if k9 <= K9_CONTACT:
            for_.append(f"{_surname(name)} {k9:.1f} K/9")
        elif k9 >= K9_POWER:
            against.append(f"{_surname(name)} {k9:.1f} K/9")

    # A single mild factor is not a verdict - that is the whole point of
    # combining them. One input alone gets "slightly"; the strong wording needs
    # at least two pointing the same way with nothing pointing back.
    if not for_ and not against:
        return "contact conditions: neutral"
    if for_ and not against:
        lead = "FAVOUR THE BAT" if len(for_) >= 2 else "slightly favour the bat"
        return f"contact conditions: {lead} — " + " · ".join(for_)
    if against and not for_:
        lead = ("AGAINST THE BAT" if len(against) >= 2
                else "slightly against the bat")
        return f"contact conditions: {lead} — " + " · ".join(against)
    return ("contact conditions: mixed — for: " + " · ".join(for_)
            + "  ·  against: " + " · ".join(against))


def _abbr_of(g: dict, team: str) -> str:
    """The board's own abbreviation for a team name."""
    aa, ha = _abbrs(g)
    away, home = (g.get("matchup") or " @ ").split(" @ ")
    return ha if team == home else aa if team == away else team


def _splits_or_empty(board: list) -> dict:
    """Each team's win rate as favourite and as dog. Never raises - a missing
    lookup costs a context line, and must not cost the board."""
    try:
        return good_dog.splits(_board_date(board))
    except Exception as exc:
        log.warning("fav/dog splits unavailable: %s", exc)
        return {}


def _board_date(board: list) -> str:
    """The slate's date, used as the cutoff for prior-games history."""
    for g in board:
        d = (g.get("game_datetime") or "")[:10]
        if d:
            return d
    return "9999-99-99"


def _good_dog_lines(board: list, picks: list) -> list[str]:
    """Tonight's good dogs that are NOT plays, as a watch list.

    Worded so it cannot be mistaken for a bet. The tag is an open question, not
    a pick: its two main effects came in at p = 0.154 and p = 0.277, and closing
    the question needs roughly 2.5x the data, so these are labelled and left
    alone to accumulate. Anything already on the board as a play is skipped -
    it is labelled there instead, and listing it twice was the bug that put the
    Yankees on the board twice.
    """
    bet_teams = {(_bet_side(g["pick_criteria"]) or (None,))[0] for g in picks}
    pick_pks = {g.get("game_pk") for g in picks}
    # how often each team actually wins as a dog and as a favourite - the trust
    # check, put where the decision is. Fails soft to no splits.
    sp = _splits_or_empty(board)
    out = []
    for g in board:
        gd = (g.get("pick_criteria") or {}).get("good_dog") or {}
        if not gd or gd.get("team") in bet_teams:
            continue
        aa, ha = _abbrs(g)
        away, home = g["matchup"].split(" @ ")
        at_home = gd["team"] == home
        # A good dog in a game we are already betting is the OTHER SIDE of that
        # play. Listing it unmarked put two opposing sides of one game on the
        # board looking like two suggestions - say so instead.
        clash = ("  ·  ⚠ opposes tonight's play — the rule and the tag disagree"
                 if g.get("game_pk") in pick_pks else "")
        out.append(f"👀 {gd['team']} {gd['odds']:+d} "
                   f"{'vs' if at_home else 'at'} {ha if not at_home else aa}"
                   f"  ·  favoured {gd['rate']:.0%} of its games{clash}")
        # BOTH teams' splits, labelled - the dog's record is only readable
        # against the side it is facing
        opp = away if at_home else home
        wp = _when_picked(gd["team"])
        if wp:
            out.append(f"      when we pick {ha if at_home else aa}: {wp}")
        for team, ab in ((gd["team"], ha if at_home else aa),
                         (opp, aa if at_home else ha)):
            line = good_dog.split_text(team, sp)
            if line:
                out.append(f"      {ab}  {line}")
        # one extra space so the hit block nests under this watch entry rather
        # than sitting at the same level as the 👀 line
        out += [" " + x for x in _hit_lines(g, winner=gd["team"])]
    return out


def _line_money_record() -> dict:
    """The tag's own forward record. Never raises - it costs a line, not the board."""
    try:
        return line_money.record(dt.datetime.now(EASTERN).date().isoformat())
    except Exception as exc:
        log.warning("line-money record unavailable: %s", exc)
        return {"all": [0, 0, 0.0], "strong": [0, 0, 0.0]}


def _line_money_lines(board: list, picks: list) -> list[str]:
    """Tonight's line-against-the-money games that are NOT plays, as a watch list.

    Worded so it cannot be mistaken for a bet. Its 95% CI runs -4.8 to +25.5 and
    the cell was selected over the same data it was measured on, so these are
    labelled and left alone to accumulate. A game already being played is skipped
    for the same reason good dogs are - it is a bet, not a thing being watched.
    """
    bet_teams = {(_bet_side(g["pick_criteria"]) or (None,))[0] for g in picks}
    pick_pks = {g.get("game_pk") for g in picks}
    out = []
    for g in board:
        lm = (g.get("pick_criteria") or {}).get("line_money") or {}
        if not lm or lm.get("team") in bet_teams:
            continue
        aa, ha = _abbrs(g)
        at_home = lm["team"] == g["matchup"].split(" @ ")[1]
        # There are only two sides, so the line moved toward the opponent named
        # on this same line - "the other way" says it without repeating them.
        # The flagged side is also the OTHER side of any play in this game, and
        # saying so beats printing two opposing teams as if they were two picks.
        clash = ("  ·  ⚠ opposes tonight's play — the rule and the tag disagree"
                 if g.get("game_pk") in pick_pks else "")
        # The two tags are independent questions that can land on the same side.
        # When they have, the good-dog block above already carries this team's
        # history, so say they agree instead of reprinting it.
        gd = (g.get("pick_criteria") or {}).get("good_dog") or {}
        dup = gd.get("team") == lm["team"]
        out.append(f"👁 {lm['team']} {lm['odds']:+d} "
                   f"{'vs' if at_home else 'at'} {aa if at_home else ha}"
                   f"  ·  price moved {lm['move']:.1%} the other way"
                   f"{' (big)' if lm.get('strong') else ''}{clash}"
                   f"{'  ·  same side as the good-dog tag above' if dup else ''}")
        wp = "" if dup else _when_picked(lm["team"])
        if wp:
            out.append(f"      when we pick {_short(g, lm['team'])}: {wp}")
    return out


def _telegram_records_lines() -> list[str]:
    """Day/Week/Month/YTD records per book plus the all-time combined row, laid
    out one window per line."""
    ledger = grade.load_ledger()
    today = dt.datetime.now(EASTERN).date()
    out: list[str] = []
    # Fades count in the MAIN record (user's call, 2026-09-22). They stay
    # tagged on the entry and labelled 🔁 FADE on the board, so they are still
    # identifiable game by game - they are simply tallied here with everything
    # else rather than held apart.
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
        roi = f" · {u/(w+l):+.1%} ROI" if (w + l) else ""
        out.append(f"   • All-time: {w}-{l} ({u:+.2f}u){roi}")
    return out


def telegram_text(payload: dict) -> str:
    """Readable phone layout for Telegram: the pick(s) up top, then leans, then
    the Day/Week/Month/YTD records — sectioned with blank lines and dividers."""
    date = payload["date"]
    games = payload.get("games", [])
    board = _board_games(games)
    picks = _by_win([g for g in board if _play(g) == "pick"])
    sp_all = _splits_or_empty(board)   # computed once; the cache makes it cheap

    # Minimal board: only the plays, one clean line each (ranked by win chance).
    # No-plays stay recorded in the picks JSON (backend); they're not shown.
    L = [f"⚾ MLB BOARD — {date}", ""]
    if picks:
        L.append(f"{len(picks)} play{'s' if len(picks) != 1 else ''} today:")
        L.append("")
        for g in picks:
            L.append(_pick_line(g, sp_all))
            L.append("")
        L.pop()          # no trailing blank before the divider
    else:
        L.append("No plays on the board.")

    dogs = _good_dog_lines(board, picks)
    money = _line_money_lines(board, picks)
    if dogs or money:
        L += ["", "👀 WATCHING — NOT BETS", "",
              "Open questions the backtest could not close. Tracking only —",
              "do not bet these."]
        if dogs:
            L += ["", "Usually-favoured teams priced as dogs tonight:", ""] + dogs
        if money:
            L += ["", "Line moved against the money — flagged side is the money:",
                  ""] + money
            rt = line_money.record_text(_line_money_record())
            if rt:
                L.append(f"      {rt}")
    # Legend, printed only when a marker actually appears above - an unexplained
    # emoji is worse than none, and a legend for symbols that are not on tonight's
    # board is clutter.
    if any("⭐" in x or "🧊" in x for x in L):
        L += ["", f"⭐ we are up more than {PICK_REC_HOT:.0%} betting this team  ·  "
                  f"🧊 down more than {-PICK_REC_COLD:.0%}",
              f"   (our own record on it, {PICK_REC_MIN}+ picks. History, not a "
              "forecast — team-by-team", "   differences here are not "
              "distinguishable from luck.)"]
    L += ["", "📊 RECORDS ($1/bet · pre-game ML)"] + _telegram_records_lines()
    # prop records stay backend-only for now (tracked in prop_ledger.json, not posted)
    return "\n".join(L)


def main() -> None:
    parser = argparse.ArgumentParser(description="MLB public-vs-stats edge finder")
    parser.add_argument("--date", default=os.environ.get("PICKS_DATE") or today_eastern())
    args = parser.parse_args()

    payload = run(args.date)
    write_outputs(payload, args.date)
    grade.update_ledger(args.date)  # record any games that just went final (idempotent)
    # Shadow book, its OWN ledger, nothing bet. Fails soft: a shadow log must
    # never be able to take the board down.
    try:
        hrr_shadow.settle([args.date])
    except Exception as exc:
        log.warning("hrr shadow settle failed (board unaffected): %s", exc)
    notify.send_telegram(telegram_text(payload))
    # A new pick gets a board post; a WITHDRAWN one used to get silence, which
    # is indistinguishable from "the board hasn't refreshed yet" - the common
    # case, since most scheduled runs are dropped. Runs after the board post so
    # the channel sees the board first, then what changed on it.
    try:
        pick_watch.check(payload.get("games") or [], args.date)
    except Exception as exc:
        log.warning("pick watch failed (board unaffected): %s", exc)
    print(json.dumps(payload.get("leans", []), indent=2))


if __name__ == "__main__":
    main()
