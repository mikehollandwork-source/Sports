"""
Can we project RUNS and STRIKEOUTS better than `projections.py` does now?

WHAT IS BEING TESTED, AND WHY EACH TEST EXISTS

`projections.py` ships three numbers on every board - full-game runs, first-five
runs and each starter's strikeouts - built from plain proportional scalings off
league means. Nothing in it is fitted, and nothing in it has been checked
against what actually happened. `totals_signal.py` measured the INPUTS against
real scores (starter FIP last-5 at r=+0.180 full / +0.138 first-five, bullpen
FIP +0.139 full / +0.030 first-five) but never the assembled projection.

So this measures the output, and three specific candidate changes:

  1. THE UMPIRE, on strikeouts. Asked for directly. `ump_tend.k_extra` is on
     1041 board games and has only ever been tested against WIN rates
     (`ump_calibration.md`), never against strikeouts - the thing it is
     literally a count of. It gets a real holdout: the table in
     `ump_tendencies_2026.json` was built `through 2026-07-02`, so every board
     game after that date is out of sample for it.

  2. STARTER AND BULLPEN SPLIT BETWEEN THE TWO TOTALS. `runs()` scales both the
     full-game and the first-five number by the same starter-FIP multiplier.
     That cannot be right by mechanism: the starters pitch the first five and
     the bullpen pitches much of the rest, and the measured correlations say so
     out loud - bullpen FIP is +0.139 against full-game runs and +0.030 against
     the first five. So full game should carry bullpen weight and first five
     should not.

  3. THE UMPIRE, on runs. Same table, opposite sign expected: more strikeouts
     means fewer balls in play.

HOW A CANDIDATE IS JUDGED
Against the projection it would replace, on the same games, by mean absolute
error and by correlation, with a DAY-BLOCK bootstrap interval on the difference
- a game's runs are not independent of the other games that day (same weather,
same umpire pool), so resampling games would understate the interval.

A projection has no price, so there is no ROI here and nothing is staked. Beating
the market is a separate question this cannot answer; `market_log` is
accumulating the lines that will let it be asked.

Read-only. Writes output/totals_model.md. Changes no pick.
"""

from __future__ import annotations

import glob
import json
import logging
import math
import random
import statistics as st
from pathlib import Path

from . import mlb_api, park_factors, projections, totals_signal

log = logging.getLogger("totals_model")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPORT = OUTPUT_DIR / "totals_model.md"
CACHE = OUTPUT_DIR / "totals_model_cache.json"

# The umpire table's build cutoff. Board games after it are out of sample for
# `k_extra`, which is the only clean holdout available here.
UMP_TABLE_THROUGH = "2026-07-02"
BOOTSTRAP = 2000
SEED = 20261012


def _load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return {}


def _box_row(pk: int) -> dict | None:
    """Per-game actuals from one boxscore: game strikeouts, runs, and each
    STARTER's strikeouts and innings.

    The starter is `pitchers[0]` - the boxscore lists a side's pitchers in the
    order they appeared, so the first is who started.
    """
    box = mlb_api._get(f"game/{pk}/boxscore")
    teams = box.get("teams") or {}
    if not teams.get("home") or not teams.get("away"):
        return None
    row: dict = {"k_total": 0, "r_total": 0, "starters": []}
    for side in ("home", "away"):
        t = teams.get(side) or {}
        bat = ((t.get("teamStats") or {}).get("batting") or {})
        # a side's BATTING strikeouts are the ones the other side's pitchers got
        row["k_total"] += int(bat.get("strikeOuts", 0) or 0)
        row["r_total"] += int(bat.get("runs", 0) or 0)
        pids = t.get("pitchers") or []
        if not pids:
            continue
        pid = pids[0]
        p = (t.get("players") or {}).get(f"ID{pid}") or {}
        ps = ((p.get("stats") or {}).get("pitching") or {})
        if not ps:
            continue
        row["starters"].append({
            "side": side, "id": int(pid),
            "name": ((p.get("person") or {}).get("fullName") or ""),
            "k": int(ps.get("strikeOuts", 0) or 0),
            "ip": mlb_api._ip_to_innings(ps.get("inningsPitched", "0") or "0")})
    return row


def collect() -> list[dict]:
    """One row per board game that reached a final, with actuals and the board's
    own point-in-time signals.

    Deliberately NOT restricted the way `totals_signal.collect` is - that one
    only keeps games present in the lineup-price cache, which costs it three
    quarters of the season for tests that never touch a lineup price.
    """
    cache = _load_cache()
    scores_cache: dict = {}
    try:
        scores_cache = json.loads(totals_signal.SCORES.read_text())
    except (OSError, ValueError):
        pass
    rows, dirty = [], False
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            day = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        sc = totals_signal._scores(date, scores_cache)
        for g in day.get("games", []):
            pk = str(g.get("game_pk"))
            s = sc.get(pk)
            if not s:
                continue                      # not final, or no linescore
            if pk not in cache:
                try:
                    r = _box_row(int(pk))
                except Exception as exc:
                    log.warning("boxscore %s failed: %s", pk, exc)
                    continue
                if not r:
                    continue
                cache[pk] = r
                dirty = True
            box = cache[pk]
            sa = g.get("statistical_advantage") or {}
            wx = g.get("weather") or {}
            tend = g.get("ump_tend") or {}
            home_name = ((sa.get("home") or {}).get("name")
                          or (g.get("matchup") or " @ ").split(" @ ")[-1])
            rows.append({
                "date": date, "pk": pk,
                "total": s["total"], "f5": s["f5"],
                "k_total": box["k_total"], "starters": box["starters"],
                "park": g.get("park_factor"), "temp": wx.get("temp_f"),
                "k_extra": tend.get("k_extra"), "ump_games": tend.get("games"),
                "ump": g.get("umpire_hp"),
                # SIGNED wind, which is the only form that can carry anything:
                # `totals_signal` tested wind SPEED, where a 15 mph gale blowing
                # in and one blowing out are the same number, so they cancel.
                "wind_signed": _wind_signed(g, home_name),
                "pen_down": _both(sa, "pen_arms_down"),
                "pen_ip": _both(sa, "bullpen_ip_last5"),
                "sa": sa})
    if dirty:
        try:
            OUTPUT_DIR.mkdir(exist_ok=True)
            CACHE.write_text(json.dumps(cache))
            totals_signal.SCORES.write_text(json.dumps(scores_cache))
        except OSError as exc:
            log.warning("cache not written (%s)", exc)
    return rows


def _both(sa: dict, key: str):
    """The two sides' mean for a board field, or None."""
    vals = []
    for side in ("home", "away"):
        v = (sa.get(side) or {}).get(key)
        if isinstance(v, (int, float)):
            vals.append(float(v))
    return st.mean(vals) if vals else None


# 16-point compass -> degrees. `wind_deg` was only added to the board recently
# and sits on 24 of 1299 games, while the compass string `wind_dir` is on all
# 1167 that have weather at all - so without this the signed-wind test runs at
# n=17 and says nothing.
COMPASS = {"N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5, "E": 90,
           "ESE": 112.5, "SE": 135, "SSE": 157.5, "S": 180, "SSW": 202.5,
           "SW": 225, "WSW": 247.5, "W": 270, "WNW": 292.5, "NW": 315,
           "NNW": 337.5}


def _wind_signed(g: dict, home_name: str):
    """+mph when the wind blows OUT to centre, -mph when it blows in, None for
    a crosswind, a closed roof or an unknown park bearing.

    Same geometry `main._wind_component` uses for the contact line; the sign is
    the whole point here.
    """
    wx = g.get("weather") or {}
    if (wx.get("roof") or "") == "closed":
        return None
    deg, mph = wx.get("wind_deg"), wx.get("wind_mph")
    if not isinstance(deg, (int, float)):
        deg = COMPASS.get((wx.get("wind_dir") or "").strip().upper())
    bearing = park_factors.bearing_for(home_name)
    if bearing is None or not isinstance(deg, (int, float)) \
            or not isinstance(mph, (int, float)):
        return None
    toward = (deg + 180) % 360              # from-direction -> blowing-toward
    comp = math.cos(math.radians(bearing - toward))
    if abs(comp) < 0.5:
        return None                         # crosswind says nothing
    return mph * comp


# --- statistics ---------------------------------------------------------------

def _pearson(xs, ys):
    n = len(xs)
    if n < 10:
        return None
    mx, my = st.mean(xs), st.mean(ys)
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else None


def _mae(pairs):
    return st.mean(abs(p - a) for p, a in pairs) if pairs else None


def _boot_delta_mae(a_pairs: list, b_pairs: list) -> tuple:
    """CI on MAE(a) - MAE(b), resampling DAYS. Negative means `a` is better.

    Both lists must be aligned game-for-game and carry their date, so the same
    resampled day moves both models together - that is the whole point of
    pairing, and it is what makes a small difference measurable.
    """
    by_day: dict = {}
    for (pa, act, d), (pb, _a2, _d2) in zip(a_pairs, b_pairs):
        by_day.setdefault(d, []).append((abs(pa - act), abs(pb - act)))
    days = list(by_day)
    if len(days) < 5:
        return None, None
    rnd = random.Random(SEED)
    diffs = []
    for _ in range(BOOTSTRAP):
        ea, eb, n = 0.0, 0.0, 0
        for _ in days:
            for x, y in by_day[rnd.choice(days)]:
                ea += x
                eb += y
                n += 1
        if n:
            diffs.append(ea / n - eb / n)
    diffs.sort()
    return diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs))]


def _tercile(rows, key, outcome):
    vals = sorted(r[key] for r in rows if isinstance(r.get(key), (int, float)))
    if len(vals) < 30:
        return None
    lo_cut, hi_cut = vals[len(vals) // 3], vals[2 * len(vals) // 3]
    lo = [r[outcome] for r in rows
          if isinstance(r.get(key), (int, float)) and r[key] <= lo_cut]
    hi = [r[outcome] for r in rows
          if isinstance(r.get(key), (int, float)) and r[key] >= hi_cut]
    if len(lo) < 10 or len(hi) < 10:
        return None
    return st.mean(lo), st.mean(hi), len(lo), len(hi)


# --- the models being compared ------------------------------------------------
#
# Each takes a board row and returns a number, so the current shipped
# projection and a candidate are scored on identical games with identical
# inputs. The only thing that differs between a pair is the one change being
# tested.

LEAGUE_UMP_K_PG = 16.74    # ump_tendencies_2026.json's own league baseline
LEAGUE_OPP_K = 0.225
UMP_CLAMP = (0.88, 1.12)


def _fip_mean(sa: dict, key_pref: tuple) -> float | None:
    vals = []
    for side in ("home", "away"):
        d = sa.get(side) or {}
        for k in key_pref:
            v = d.get(k)
            if isinstance(v, (int, float)) and v > 0:
                vals.append(float(v))
                break
    return st.mean(vals) if vals else None


def runs_current(row: dict) -> tuple | None:
    """What `projections.runs` ships today: one starter-FIP multiplier for both
    the full game and the first five."""
    sp = _fip_mean(row["sa"], ("starter_fip_last5", "starter_fip_season"))
    if sp is None:
        return None
    m = projections._clamp(sp / projections.LEAGUE_FIP)
    return projections.LEAGUE_FULL_RUNS * m, projections.LEAGUE_F5_RUNS * m


def runs_split(row: dict) -> tuple | None:
    """CANDIDATE: the bullpen only enters the FULL game.

    The starters pitch the first five, so the first-five number is unchanged.
    The full game is weighted by innings - `STARTER_IP_DEFAULT` of nine from the
    starters, the rest from the pen - which is where the measured bullpen
    correlation (+0.139 full, +0.030 first five) says the weight belongs.
    """
    sp = _fip_mean(row["sa"], ("starter_fip_last5", "starter_fip_season"))
    bp = _fip_mean(row["sa"], ("bullpen_fip_last5",))
    if sp is None:
        return None
    if bp is None:
        return runs_current(row)
    w = projections.STARTER_IP_DEFAULT / 9.0
    m_full = projections._clamp((w * sp + (1 - w) * bp) / projections.LEAGUE_FIP)
    m_f5 = projections._clamp(sp / projections.LEAGUE_FIP)
    return (projections.LEAGUE_FULL_RUNS * m_full,
            projections.LEAGUE_F5_RUNS * m_f5)


def ump_k_mult(k_extra) -> float:
    """The umpire's own game strikeout rate over the league's, clamped.

    Proportional scaling off a league mean, same as every other mapping in
    `projections` - the magnitude is the table's measured K/game, not a fitted
    coefficient.
    """
    if not isinstance(k_extra, (int, float)):
        return 1.0
    return max(UMP_CLAMP[0], min(UMP_CLAMP[1],
                                 (LEAGUE_UMP_K_PG + k_extra) / LEAGUE_UMP_K_PG))


def starter_k_proj(row: dict, s: dict, with_ump: bool,
                   starts_only: bool = False) -> float | None:
    """`projections.strikeouts` recomputed point-in-time for one start, with the
    umpire multiplier optionally applied.

    POINT-IN-TIME on purpose: the pitcher's K/9 and expected innings come from
    starts STRICTLY BEFORE this game's date, so the projection cannot see the
    night it is projecting.
    """
    try:
        line = mlb_api.pitcher_season_line(s["id"], 2026, as_of=row["date"])
    except Exception:
        return None
    ip, k, gs = line.get("ip") or 0, line.get("k") or 0, line.get("gs") or 0
    if ip < 20:
        return None
    ip_gs, k_gs = line.get("ip_gs") or 0, line.get("k_gs") or 0
    if starts_only and ip_gs > 0 and gs >= 3:
        k9 = k_gs * 9.0 / ip_gs
        exp_ip = ip_gs / gs
    else:
        k9 = k * 9.0 / ip
        exp_ip = (ip / gs) if gs >= 3 else projections.STARTER_IP_DEFAULT
    opp_side = "away" if s["side"] == "home" else "home"
    opp_k = (((row["sa"].get(opp_side) or {}).get("offense") or {}).get("k_pct"))
    opp = 1.0
    if isinstance(opp_k, (int, float)) and opp_k > 0:
        opp = projections._clamp(opp_k / LEAGUE_OPP_K, 0.85, 1.15)
    proj = k9 * exp_ip / 9.0 * opp
    return proj * ump_k_mult(row.get("k_extra")) if with_ump else proj


# --- report -------------------------------------------------------------------

def _fmt_r(v) -> str:
    return f"{v:+.3f}" if isinstance(v, float) else "—"


def _pair_block(name: str, pairs: list) -> list[str]:
    """One model against one outcome: n, bias, MAE, correlation."""
    if not pairs:
        return [f"| {name} | 0 | — | — | — |"]
    proj = [p for p, _a, _d in pairs]
    act = [a for _p, a, _d in pairs]
    bias = st.mean(proj) - st.mean(act)
    mae = st.mean(abs(p - a) for p, a, _d in pairs)
    r = _pearson(proj, act)
    return [f"| {name} | {len(pairs)} | {bias:+.2f} | {mae:.2f} | "
            f"{_fmt_r(r)} |"]


def build() -> str:
    rows = collect()
    md = ["# Projecting runs and strikeouts — what the actuals say", "",
          "_Read-only. No line, no stake, no ROI: this measures the shipped "
          "projection and three candidate changes against what actually "
          "happened. Beating a price is a separate question the accumulating "
          "`market_log` will answer._", "",
          f"- board games that reached a final with a linescore: "
          f"**{len(rows)}**"]
    if len(rows) < 50:
        md.append("")
        md.append("_Too few games to measure. Nothing changes._")
        return "\n".join(md)

    with_ump = [r for r in rows if isinstance(r.get("k_extra"), (int, float))]
    holdout = [r for r in with_ump if r["date"] > UMP_TABLE_THROUGH]
    md += [f"- of those, carrying an umpire tendency: **{len(with_ump)}**",
           f"- OUT OF SAMPLE for the umpire table (after "
           f"{UMP_TABLE_THROUGH}): **{len(holdout)}**",
           f"- actual full-game runs mean **{st.mean(r['total'] for r in rows):.2f}**"
           f", first five **{st.mean(r['f5'] for r in rows):.2f}**"
           f", game strikeouts **{st.mean(r['k_total'] for r in rows):.2f}**", ""]

    # --- 1. the umpire against the thing it counts ---------------------------
    md += ["## 1. Does the umpire table predict STRIKEOUTS?", "",
           "_It has only ever been checked against win rates. The table was "
           f"built `through {UMP_TABLE_THROUGH}`, so the holdout column is "
           "games it has never seen - which is the column that matters._", "",
           "| sample | n | r (k_extra vs game K) | low third K/gm | "
           "high third K/gm | gap |", "|---|---|---|---|---|---|"]
    for label, rs in (("all boards", with_ump), ("HOLDOUT", holdout)):
        if len(rs) < 30:
            md.append(f"| {label} | {len(rs)} | — | — | — | — |")
            continue
        r = _pearson([x["k_extra"] for x in rs], [x["k_total"] for x in rs])
        t = _tercile(rs, "k_extra", "k_total")
        if t:
            lo, hi, nlo, nhi = t
            md.append(f"| {label} | {len(rs)} | {_fmt_r(r)} | {lo:.2f} "
                      f"({nlo}) | {hi:.2f} ({nhi}) | **{hi - lo:+.2f}** |")
        else:
            md.append(f"| {label} | {len(rs)} | {_fmt_r(r)} | — | — | — |")
    md.append("")

    # --- 2. the umpire against runs -----------------------------------------
    md += ["## 2. Does it predict RUNS?", "",
           "_Opposite sign expected: a strikeout is a ball not in play._", "",
           "| sample | n | r vs full game | r vs first five | low third runs | "
           "high third runs |", "|---|---|---|---|---|---|"]
    for label, rs in (("all boards", with_ump), ("HOLDOUT", holdout)):
        if len(rs) < 30:
            md.append(f"| {label} | {len(rs)} | — | — | — | — |")
            continue
        rf = _pearson([x["k_extra"] for x in rs], [x["total"] for x in rs])
        r5 = _pearson([x["k_extra"] for x in rs], [x["f5"] for x in rs])
        t = _tercile(rs, "k_extra", "total")
        lo = f"{t[0]:.2f}" if t else "—"
        hi = f"{t[1]:.2f}" if t else "—"
        md.append(f"| {label} | {len(rs)} | {_fmt_r(rf)} | {_fmt_r(r5)} | "
                  f"{lo} | {hi} |")
    md.append("")

    # --- 3. the shipped runs projection vs a split one -----------------------
    cur_full, cur_f5, spl_full, spl_f5 = [], [], [], []
    for r in rows:
        c, s = runs_current(r), runs_split(r)
        if c is None or s is None:
            continue
        cur_full.append((c[0], r["total"], r["date"]))
        spl_full.append((s[0], r["total"], r["date"]))
        cur_f5.append((c[1], r["f5"], r["date"]))
        spl_f5.append((s[1], r["f5"], r["date"]))
    md += ["## 3. The shipped runs projection, and splitting the bullpen out "
           "of the first five", "",
           "_`bias` is projected minus actual, so positive means the "
           "projection runs hot. `MAE` is the mean absolute miss in runs - "
           "lower is better, and it is the number that decides this._", "",
           "| model | n | bias | MAE | r |", "|---|---|---|---|---|"]
    md += _pair_block("full game — current (starter FIP only)", cur_full)
    md += _pair_block("full game — CANDIDATE (starter + pen by innings)", spl_full)
    md += _pair_block("first five — current", cur_f5)
    md += _pair_block("first five — CANDIDATE (unchanged by construction)", spl_f5)
    md.append("")
    lo, hi = _boot_delta_mae(spl_full, cur_full)
    if lo is not None:
        verdict = ("**the candidate is better** - the interval is entirely "
                   "below zero" if hi < 0 else
                   "**no improvement** - the interval spans zero" if lo < 0 <= hi
                   else "**WORSE** - the interval is entirely above zero")
        md += [f"- full-game ΔMAE (candidate − current), day-block bootstrap: "
               f"**[{lo:+.3f}, {hi:+.3f}]** → {verdict}", ""]

    # --- 4. strikeouts, with and without the umpire --------------------------
    base, umped = [], []
    for r in rows:
        for s in r["starters"]:
            if s["ip"] < 1:
                continue             # opener or injury exit, not a projection
            b = starter_k_proj(r, s, with_ump=False)
            u = starter_k_proj(r, s, with_ump=True)
            if b is None or u is None:
                continue
            base.append((b, s["k"], r["date"]))
            umped.append((u, s["k"], r["date"]))
    md += ["## 4. Starter strikeouts, with and without the umpire", "",
           "_Point-in-time: the pitcher's K/9 and expected innings come from "
           "starts strictly before the game being projected, so nothing sees "
           "its own night. Starts under one inning are dropped - an opener or "
           "an injury exit is not a projection miss._", "",
           "| model | n | bias | MAE | r |", "|---|---|---|---|---|"]
    md += _pair_block("starter K — current", base)
    md += _pair_block("starter K — CANDIDATE (× umpire)", umped)
    md.append("")
    lo, hi = _boot_delta_mae(umped, base)
    if lo is not None:
        verdict = ("**the umpire helps**" if hi < 0 else
                   "**no improvement - the interval spans zero**" if lo < 0 <= hi
                   else "**the umpire HURTS**")
        md += [f"- ΔMAE (with umpire − without): **[{lo:+.3f}, {hi:+.3f}]** → "
               f"{verdict}", ""]
    # the residual test: does the umpire explain what the projection misses?
    res = [(r.get("k_extra"), s["k"] - b)
           for r, b, s in _residual_rows(rows)]
    res = [(x, y) for x, y in res if isinstance(x, (int, float))]
    if len(res) >= 30:
        rr = _pearson([x for x, _ in res], [y for _, y in res])
        md += [f"- correlation between `k_extra` and what the current K "
               f"projection MISSES (actual − projected), n={len(res)}: "
               f"**{_fmt_r(rr)}**",
               "  _This is the cleanest form of the question: a positive "
               "number means a big-zone umpire adds strikeouts the projection "
               "does not already account for._", ""]
    # --- 5. is the umpire's strikeout rate a TRAIT at all? -------------------
    md += ["## 5. Is an umpire's strikeout rate a stable trait?", "",
           "_Section 1 says the table does not predict. Two things could cause "
           "that: the table is three months stale, or there is nothing there "
           "to measure. This separates them. Each umpire's games are split "
           "into alternate halves and his K/game in one half is correlated "
           "with the other, across umpires - then Spearman-Brown lifts that "
           "to the reliability of his full record. A near-zero split-half "
           "means more games will not help._", ""]
    md += _reliability(rows)

    # --- 6. the strikeout bias, and the starts-only fix ----------------------
    md += ["## 6. Starter strikeouts: innings per START, not per appearance",
           "",
           "_The projection divided ALL-APPEARANCE innings by games STARTED, "
           "which overstates how long a pitcher goes whenever he also "
           "relieved. Both rates below are point-in-time. `k9/exp_ip from "
           "starts` also takes his K rate from starts only, which is the rate "
           "a start should be projected at._", "",
           "| model | n | bias | MAE | r |", "|---|---|---|---|---|"]
    fixed = []
    for r in rows:
        for st_ in r["starters"]:
            if st_["ip"] < 1:
                continue
            v = starter_k_proj(r, st_, with_ump=False, starts_only=True)
            if v is not None:
                fixed.append((v, st_["k"], r["date"]))
    md += _pair_block("starter K — current (all appearances / starts)", base)
    md += _pair_block("starter K — CANDIDATE (starts only)", fixed)
    md.append("")
    if len(fixed) == len(base):
        lo, hi = _boot_delta_mae(fixed, base)
        if lo is not None:
            verdict = ("**better**" if hi < 0 else
                       "**no improvement - interval spans zero**"
                       if lo < 0 <= hi else "**worse**")
            md += [f"- ΔMAE (starts-only − current): **[{lo:+.3f}, "
                   f"{hi:+.3f}]** → {verdict}", ""]
    else:
        md += [f"- _not paired ({len(fixed)} vs {len(base)} usable), so no "
               "bootstrap - compare the rows above directly._", ""]

    # --- 7. signed wind, and a depleted bullpen ------------------------------
    md += ["## 7. Two signals the earlier sweep could not have found", "",
           "_`totals_signal` tested wind SPEED, where a gale blowing in and "
           "one blowing out are the same number and cancel; this is the signed "
           "component toward centre field. A depleted bullpen can only matter "
           "AFTER the starters leave, so it is read against the full game and "
           "the first five separately - if it is real, the full-game number is "
           "the larger of the two._", "",
           "| signal | n | r vs full game | r vs first five | low third runs | "
           "high third runs | gap |", "|---|---|---|---|---|---|---|"]
    for key, label in (("wind_signed", "wind out (+) / in (−), mph"),
                       ("pen_down", "bullpen arms down"),
                       ("pen_ip", "bullpen innings last 5"),
                       ("temp", "temperature °F")):
        rs = [r for r in rows if isinstance(r.get(key), (int, float))]
        if len(rs) < 30:
            md.append(f"| {label} | {len(rs)} | — | — | — | — | — |")
            continue
        rf = _pearson([r[key] for r in rs], [r["total"] for r in rs])
        r5 = _pearson([r[key] for r in rs], [r["f5"] for r in rs])
        t = _tercile(rs, key, "total")
        lo = f"{t[0]:.2f}" if t else "—"
        hi = f"{t[1]:.2f}" if t else "—"
        gap = f"**{t[1] - t[0]:+.2f}**" if t else "—"
        md.append(f"| {label} | {len(rs)} | {_fmt_r(rf)} | {_fmt_r(r5)} | "
                  f"{lo} | {hi} | {gap} |")
    md += ["", f"_At n around a thousand the standard error on a correlation "
           f"is about {1 / math.sqrt(1000):.3f}, so anything inside roughly "
           "±0.06 is not distinguishable from nothing._", ""]

    # --- 8. the umpire, measured the way it should have been -----------------
    md += ump_residual_section(rows)
    return "\n".join(md)


UMP_MIN_STARTS = 12


def ump_residual_section(rows: list[dict]) -> list[str]:
    """The umpire as K ABOVE WHAT THE PITCHERS IMPLY, split chronologically.

    This is the real version of the question. `k_extra` is raw K/game, so over
    a dozen games it mostly measures which PITCHERS an umpire happened to draw
    - a confound that does not transfer, and the likeliest reason section 1
    comes back wrong-signed. Averaging the projection's RESIDUAL instead
    (actual minus what this pitcher, against this lineup, was projected for)
    removes the pitcher from the measurement by construction.

    Judged out of sample: each umpire's mean residual is built from the FIRST
    half of the season by date and then asked to predict his residuals in the
    second half. A tendency that only exists inside its own training games is
    not a tendency.
    """
    starts = []
    for r in rows:
        if not r.get("ump"):
            continue
        for s in r["starters"]:
            if s["ip"] < 1:
                continue
            proj = starter_k_proj(r, s, with_ump=False, starts_only=True)
            if proj is not None:
                starts.append((r["date"], r["ump"], s["k"] - proj))
    out = ["## 8. The umpire, measured as strikeouts ABOVE the pitchers", "",
           "_`k_extra` is raw K/game, so over a dozen games it largely "
           "measures which PITCHERS the umpire drew - which is the likeliest "
           "reason section 1 comes back wrong-signed. This averages the "
           "projection's residual instead, which removes the pitcher by "
           "construction, and then asks the first half of the season to "
           "predict the second._", ""]
    if len(starts) < 200:
        return out + [f"- only {len(starts)} usable starts; not measurable.",
                      ""]
    starts.sort()
    cut = starts[len(starts) // 2][0]
    train: dict = {}
    test: list = []
    for date, ump, res in starts:
        if date <= cut:
            train.setdefault(ump, []).append(res)
        else:
            test.append((ump, res))
    tend = {u: st.mean(v) for u, v in train.items()
            if len(v) >= UMP_MIN_STARTS}
    paired = [(tend[u], res) for u, res in test if u in tend]
    out += [f"- usable starts: **{len(starts)}**, split at **{cut}**",
            f"- umpires with {UMP_MIN_STARTS}+ starts in the first half: "
            f"**{len(tend)}**",
            f"- second-half starts under one of them: **{len(paired)}**"]
    if tend:
        vals = list(tend.values())
        out.append(f"- spread of their residual tendencies: SD "
                   f"**{st.pstdev(vals):.2f}** K/start, range "
                   f"{min(vals):+.2f} to {max(vals):+.2f}")
    if len(paired) < 100:
        return out + ["- too few paired second-half starts to test.", ""]
    r = _pearson([a for a, _ in paired], [b for _, b in paired])
    out += ["",
            f"- **OUT-OF-SAMPLE correlation, first-half tendency vs "
            f"second-half residual: {_fmt_r(r)}** (n={len(paired)}, "
            f"SE about {1 / math.sqrt(len(paired)):.3f})"]
    # does sorting on it separate anything?
    t = _tercile([{"t": a, "res": b} for a, b in paired], "t", "res")
    if t:
        lo, hi, nlo, nhi = t
        out.append(f"- second-half residual by first-half tendency: low third "
                   f"**{lo:+.2f}** K/start ({nlo}), high third **{hi:+.2f}** "
                   f"({nhi}), gap **{hi - lo:+.2f}**")
    good = isinstance(r, float) and r >= 2 / math.sqrt(len(paired))
    out.append("- " + ("**this version carries signal** — worth building a "
                       "residual-based umpire table and re-testing it as a "
                       "multiplier before the idea is closed"
                       if good else
                       "**still nothing.** Removing the pitcher confound does "
                       "not rescue it, so the umpire is not a usable "
                       "strikeout term in this data - not because the table "
                       "is stale or built wrong, but because the effect is "
                       "too small to survive one start's variance."))
    return out + [""]


def _reliability(rows: list[dict]) -> list[str]:
    """Split-half reliability of an umpire's K/game, across umpires."""
    by_ump: dict = {}
    for r in rows:
        if r.get("ump"):
            by_ump.setdefault(r["ump"], []).append(r["k_total"])
    pairs = [(st.mean(ks[0::2]), st.mean(ks[1::2]))
             for ks in by_ump.values() if len(ks) >= 10]
    if len(pairs) < 20:
        return [f"- only {len(pairs)} umpires with 10+ games here; not "
                "measurable.", ""]
    r = _pearson([a for a, _ in pairs], [b for _, b in pairs])
    out = [f"- umpires with 10+ board games: **{len(pairs)}** "
           f"(mean {st.mean(len(k) for k in by_ump.values()):.1f} games each)",
           f"- split-half correlation of K/game: **{_fmt_r(r)}**"]
    if isinstance(r, float) and r > -0.99:
        sb = 2 * r / (1 + r) if (1 + r) else None
        if sb is not None:
            out.append(f"- Spearman-Brown, lifted to the full record: "
                       f"**{sb:+.3f}**")
        if sb is not None and sb >= 0.25:
            out.append("- **a trait exists, but a weak one.** At this "
                       "reliability the honest use of `k_extra` is to shrink "
                       "it toward zero by roughly that fraction - which makes "
                       "an already-null term smaller, not larger. And note "
                       "what this number cannot separate: an umpire's K/game "
                       "also reflects the PITCHERS he drew, and over ~12 "
                       "games that is most of it. Section 8 strips that out.")
        else:
            out.append("- **no trait to find** — his half-seasons barely "
                       "agree with each other, so a bigger table cannot "
                       "rescue a term the outcome already rejected.")
    return out + [""]


def _residual_rows(rows: list[dict]):
    """(row, base projection, starter) for every usable start - so the residual
    test reuses exactly the projections table 4 scored."""
    for r in rows:
        for s in r["starters"]:
            if s["ip"] < 1:
                continue
            b = starter_k_proj(r, s, with_ump=False)
            if b is not None:
                yield r, b, s


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    text = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
