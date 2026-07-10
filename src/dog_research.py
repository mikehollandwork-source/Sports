"""
Underdog research: scan every FINAL game this season, identify the market
underdog (ESPN closing moneyline > 0), build a broad set of point-in-time,
pre-game features for the dog (no lookahead), and mine for what actually
predicts an outright dog win with positive units/ROI. Includes line movement
(open -> close). Bets $1 on the dog at the CLOSING price.

Runs on GitHub Actions (MLB API + ESPN are firewalled in the dev sandbox).
Writes output/dog_research.{md,json}. Cheap: team/pitcher game logs are cached,
so point-in-time stats cost one fetch per team / per pitcher for the whole run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import itertools
import json
import logging
import statistics as st
from pathlib import Path

from . import espn, grade, mlb_api
from .analysis import FIP_CONSTANT

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("dogresearch")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _implied(ml: int) -> float:
    return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)


def _fip(pid: int, season: int, as_of: str) -> float | None:
    try:
        t = mlb_api.pitcher_season_line(pid, season, as_of=as_of)
    except Exception:
        return None
    if not t.get("ip"):
        return None
    return round((13 * t["hr"] + 3 * (t["bb"] + t["hbp"]) - 2 * t["k"]) / t["ip"] + FIP_CONSTANT, 3)


def _last10_winpct(team_id: int, season: int, as_of: str) -> float | None:
    """Win% over the team's last 10 games strictly before as_of."""
    try:
        hit, pit = mlb_api._team_gamelog(team_id, season)
    except Exception:
        return None
    games = []
    for sp in hit:
        d = sp.get("date", "")
        if d and d < as_of:
            rs = int(sp.get("stat", {}).get("runs", 0) or 0)
            ra = int(pit.get(d, {}).get("stat", {}).get("runs", 0) or 0)
            games.append((d, 1 if rs > ra else 0))
    games.sort()
    last = games[-10:]
    return round(sum(w for _, w in last) / len(last), 3) if last else None


def _team_feats(team_id: int, season: int, as_of: str, is_home: bool) -> dict:
    """Point-in-time team quality for one side (no lookahead)."""
    try:
        form = mlb_api.team_season_form(team_id, season, as_of=as_of)
    except Exception:
        form = {}
    try:
        ha = mlb_api.team_home_away_split(team_id, season, as_of=as_of)
    except Exception:
        ha = {}
    role = ha.get("home" if is_home else "away", {}) or {}
    rg = role.get("games") or 0
    return {
        "winpct": form.get("win_pct"),
        "rd_per_g": form.get("rd_per_g"),
        "games": form.get("games"),
        "role_winpct": (role.get("wins") / rg) if rg else None,   # home rec if home / road if away
        "role_rd": role.get("rd_per_g"),
        "last10": _last10_winpct(team_id, season, as_of),
    }


def collect(start: str, end: str) -> list[dict]:
    d0, d1 = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    rows: list[dict] = []
    day = d0
    while day <= d1:
        ds = day.isoformat()
        day += dt.timedelta(days=1)
        try:
            results = mlb_api.results_for(ds)
        except Exception as exc:
            log.warning("results %s failed: %s", ds, exc)
            continue
        if not any(r.get("final") for r in results.values()):
            continue
        try:
            odds = {(_c(e["away_abbr"]), _c(e["home_abbr"])): e for e in espn.lines(ds)}
        except Exception as exc:
            log.warning("odds %s failed: %s", ds, exc)
            odds = {}
        try:
            sched = {g.game_pk: g for g in mlb_api.schedule_for(ds)}
        except Exception:
            sched = {}
        season = int(ds[:4])
        for pk, res in results.items():
            if not res.get("final") or not res.get("winner"):
                continue
            g = sched.get(pk)
            if not g:
                continue
            e = odds.get((_c(g.away.abbreviation), _c(g.home.abbreviation)))
            if not e:
                continue
            ac, hc = e.get("away_current"), e.get("home_current")
            ao, ho = e.get("away_open"), e.get("home_open")
            if ac is None or hc is None or (ac < 0 and hc < 0) or (ac > 0 and hc > 0):
                continue  # need a clean fav/dog split at close
            dog_home = hc > 0
            dog = g.home if dog_home else g.away
            fav = g.away if dog_home else g.home
            dog_ml, fav_ml = (hc, ac) if dog_home else (ac, hc)
            dog_open = (ho if dog_home else ao)
            try:
                df = _team_feats(dog.team_id, season, ds, dog_home)
                ff = _team_feats(fav.team_id, season, ds, not dog_home)
            except Exception as exc:
                log.warning("feats %s failed: %s", pk, exc)
                continue
            dog_fip = _fip(dog.probable_pitcher.player_id, season, ds) if dog.probable_pitcher else None
            fav_fip = _fip(fav.probable_pitcher.player_id, season, ds) if fav.probable_pitcher else None
            line_move = (_implied(dog_ml) - _implied(dog_open)) if dog_open is not None else None
            won = res["winner"] == dog.name
            rows.append({
                "date": ds, "dog": dog.name, "won": won, "dog_ml": dog_ml,
                "dog_home": dog_home,
                "winpct_gap": _gap(df["winpct"], ff["winpct"]),
                "rd_gap": _gap(df["rd_per_g"], ff["rd_per_g"]),
                "role_winpct": df["role_winpct"],
                "last10_gap": _gap(df["last10"], ff["last10"]),
                "sp_fip_gap": _gap(fav_fip, dog_fip),   # positive = dog's starter better (lower FIP)
                "dog_winpct": df["winpct"], "fav_winpct": ff["winpct"],
                "line_move": round(line_move, 4) if line_move is not None else None,
                "dog_price_bucket": ("short (+100..+130)" if dog_ml <= 130
                                     else "mid (+131..+180)" if dog_ml <= 180 else "long (>+180)"),
            })
        log.info("%s: %d dog rows so far", ds, len(rows))
    return rows


def _c(a):
    return (a or "").upper().strip()


def _gap(x, y):
    return round(x - y, 4) if isinstance(x, (int, float)) and isinstance(y, (int, float)) else None


def _wr(rows: list[dict]) -> tuple[int, int, float]:
    w = sum(1 for r in rows if r["won"])
    u = sum((grade.american_profit(r["dog_ml"]) if r["won"] else -1) for r in rows)
    return w, len(rows) - w, round(u, 2)


def _line(label: str, rows: list[dict]) -> str:
    if not rows:
        return f"| {label} | 0 | — | — |"
    w, l, u = _wr(rows)
    return f"| {label} | {w}-{l} ({w/len(rows):.0%}) | {u:+.2f}u | {u/len(rows):+.0%} |"


NUM_FEATS = ["winpct_gap", "rd_gap", "role_winpct", "last10_gap", "sp_fip_gap",
             "dog_winpct", "line_move"]


def analyze(rows: list[dict]) -> str:
    md = [f"# Underdog research — {len(rows)} dog games ({rows[0]['date']}..{rows[-1]['date']})"
          if rows else "# Underdog research — no games", ""]
    if not rows:
        return "\n".join(md)
    w, l, u = _wr(rows)
    md += [f"**Baseline: bet every dog at close — {w}-{l} ({w/len(rows):.0%}), {u:+.2f}u, "
           f"{u/len(rows):+.0%} ROI**", ""]

    # winners vs losers medians
    W = [r for r in rows if r["won"]]
    L = [r for r in rows if not r["won"]]
    md += ["## Winning dogs vs losing dogs — median of each stat", "",
           "| stat (dog edge) | winners | losers |", "|---|---|---|"]
    for k in NUM_FEATS:
        wv = [r[k] for r in W if r.get(k) is not None]
        lv = [r[k] for r in L if r.get(k) is not None]
        if wv and lv:
            md.append(f"| {k} | {st.median(wv):+.3f} | {st.median(lv):+.3f} |")
    md.append("")

    # single-feature threshold sweeps (both directions), best ROI with n>=25
    md += ["## Best single-stat thresholds (bet dogs meeting it, n≥25, by ROI)", "",
           "| rule | record | units | ROI |", "|---|---|---|---|"]
    best = []
    for k in NUM_FEATS:
        vals = sorted(r[k] for r in rows if r.get(k) is not None)
        if len(vals) < 40:
            continue
        for q in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
            thr = vals[int(q * len(vals))]
            hi = [r for r in rows if r.get(k) is not None and r[k] >= thr]
            lo = [r for r in rows if r.get(k) is not None and r[k] <= thr]
            for sub, op in ((hi, "≥"), (lo, "≤")):
                if len(sub) >= 25:
                    _, _, uu = _wr(sub)
                    best.append((uu / len(sub), f"{k} {op} {thr:+.3f}", sub))
    seen = set()
    for roi, name, sub in sorted(best, reverse=True):
        key = name.split()[0]
        if key in seen:
            continue
        seen.add(key)
        md.append(_line(name, sub))
    md.append("")

    # categorical splits
    md += ["## Categorical splits", "", "| slice | record | units | ROI |", "|---|---|---|---|",
           _line("dog at HOME", [r for r in rows if r["dog_home"]]),
           _line("dog on ROAD", [r for r in rows if not r["dog_home"]])]
    for b in ("short (+100..+130)", "mid (+131..+180)", "long (>+180)"):
        md.append(_line(f"price {b}", [r for r in rows if r["dog_price_bucket"] == b]))
    md.append("")

    # line movement
    lm = [r for r in rows if r.get("line_move") is not None]
    md += ["## Line movement (open→close, dog implied prob)", "",
           "| slice | record | units | ROI |", "|---|---|---|---|",
           _line("dog STEAMED (line toward dog, +0.02)",
                 [r for r in lm if r["line_move"] >= 0.02]),
           _line("dog drifted (line away, -0.02)",
                 [r for r in lm if r["line_move"] <= -0.02]),
           _line("line flat", [r for r in lm if abs(r["line_move"]) < 0.02]), ""]

    # best 2-feature threshold combos (median split), n>=25 by ROI
    md += ["## Best 2-stat combos (median split each, n≥25, by ROI)", "",
           "| rule | record | units | ROI |", "|---|---|---|---|"]
    meds = {k: st.median([r[k] for r in rows if r.get(k) is not None]) for k in NUM_FEATS
            if sum(1 for r in rows if r.get(k) is not None) >= 40}
    combos = []
    for a, b in itertools.combinations(meds, 2):
        sub = [r for r in rows if r.get(a) is not None and r.get(b) is not None
               and r[a] >= meds[a] and r[b] >= meds[b]]
        if len(sub) >= 25:
            _, _, uu = _wr(sub)
            combos.append((uu / len(sub), f"{a} ≥ med & {b} ≥ med", sub))
    for roi, name, sub in sorted(combos, reverse=True)[:12]:
        md.append(_line(name, sub))
    md.append("")

    md.append("_Point-in-time features (no lookahead); market underdog by ESPN closing "
              "moneyline; $1/dog at the closing price. Season scan via the MLB Stats API._")
    return "\n".join(md)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2026-03-25")
    p.add_argument("--end", default=(dt.date.today() - dt.timedelta(days=1)).isoformat())
    args = p.parse_args()
    log.info("scanning %s..%s", args.start, args.end)
    rows = collect(args.start, args.end)
    rows.sort(key=lambda r: r["date"])
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "dog_research.json").write_text(json.dumps(rows, indent=2))
    md = analyze(rows)
    (OUTPUT_DIR / "dog_research.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
