"""
Player hot/cold form calibration - the money test for the new 6th signal.

Replays completed games point-in-time: for each final game, take both ACTUAL
lineups (boxscore batting order), compute every hitter's last-5 wOBA (as-of the
game date) minus his own season wOBA, PA-weight into the two team form deltas
(exactly what mlb_api._lineup_form does live), and ask: does the HOTTER lineup
win more often - and does betting it at the ESPN closing moneyline profit?
Bucketed by gap size so we learn where the meaningful floor actually is
(FORM_DIFF_FLOOR is currently 0.015, an untested guess).

Known caveat: the per-player season baseline is season-to-date AT RUN TIME (the
stats API has no cheap point-in-time season split), so early-window games get a
slightly future-peeking baseline. It biases deltas toward zero, not toward the
signal, so a positive result survives it.

Writes output/form_calibration.{json,md}. Heavy-ish (lineups + player logs,
cached per player-season). Run via calibrate.yml signal "form", ~14-21 days.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import espn, mlb_api
from .analysis import _canon_abbr

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("form_calibrate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

BANDS = ((0.015, 0.030), (0.030, 0.050), (0.050, 9.9))


def _team_delta(game_pk: int, team, date: str, season: int, home: bool) -> float | None:
    """The lineup's form delta as-of `date` (mirror of the live computation)."""
    hitters = mlb_api.lineup(game_pk, team.team_id, date, home)
    per_hitter = []
    for h in hitters:
        try:
            line = mlb_api.hitter_last5(h.player_id, team.name, season, as_of=date)
        except Exception:
            continue
        per_hitter.append((h.player_id, h.name, line))
    delta, _players = mlb_api._lineup_form(per_hitter, season)
    return delta


def collect(end: str, days: int) -> list[dict]:
    lo = (dt.date.fromisoformat(end) - dt.timedelta(days=days - 1)).isoformat()
    rows: list[dict] = []
    lines_cache: dict[str, list[dict]] = {}

    def closing(date, away_ab, home_ab):
        if date not in lines_cache:
            try:
                lines_cache[date] = espn.lines(date)
            except Exception as exc:
                log.warning("espn lines %s failed: %s", date, exc)
                lines_cache[date] = []
        a, h = _canon_abbr(away_ab), _canon_abbr(home_ab)
        for e in lines_cache[date]:
            if _canon_abbr(e["away_abbr"]) == a and _canon_abbr(e["home_abbr"]) == h:
                return e.get("away_current"), e.get("home_current")
        return None, None

    d = dt.date.fromisoformat(lo)
    endd = dt.date.fromisoformat(end)
    while d <= endd:
        date = d.isoformat()
        season = d.year
        try:
            games = mlb_api.schedule_for(date)
            results = mlb_api.results_for(date)
        except Exception as exc:
            log.warning("fetch %s failed: %s", date, exc)
            d += dt.timedelta(days=1)
            continue
        for g in games:
            res = results.get(g.game_pk)
            if not res or not res["final"] or not res["winner"]:
                continue
            try:
                hd = _team_delta(g.game_pk, g.home, date, season, True)
                ad = _team_delta(g.game_pk, g.away, date, season, False)
            except Exception as exc:
                log.warning("form %s failed: %s", g.game_pk, exc)
                continue
            if hd is None or ad is None:
                continue
            aml, hml = closing(date, g.away.abbreviation, g.home.abbreviation)
            rows.append({"date": date, "gap": round(hd - ad, 3),
                         "home_won": res["winner"] == g.home.name,
                         "away_ml": aml, "home_ml": hml})
        log.info("%s done (%d rows so far)", date, len(rows))
        d += dt.timedelta(days=1)
    return rows


def _profit(ml: int, won: bool) -> float:
    return (ml / 100 if ml > 0 else 100 / -ml) if won else -1.0


def analyze(rows: list[dict]) -> dict:
    def cut(lo, hi):
        """Hotter lineup's record + ROI at its closing price, gap in [lo, hi)."""
        n = w = pn = 0
        u = 0.0
        for r in rows:
            gap = abs(r["gap"])
            if not (lo <= gap < hi):
                continue
            hot_home = r["gap"] > 0
            hot_won = r["home_won"] == hot_home
            n += 1
            w += hot_won
            ml = r["home_ml"] if hot_home else r["away_ml"]
            if ml is not None:
                pn += 1
                u += _profit(int(ml), hot_won)
        return {"n": n, "hot_win": round(w / n, 3) if n else None,
                "priced": pn, "roi": round(u / pn, 3) if pn else None}
    out = {"games": len(rows),
           "any_gap_.015+": cut(0.015, 9.9),
           "bands": {f"{lo:.3f}-{hi if hi < 1 else '+'}": cut(lo, hi) for lo, hi in BANDS},
           "below_floor_<.015": cut(0.0, 0.015)}
    return out


def summary_md(rep: dict) -> str:
    a = rep["analysis"]
    out = [f"# Player-form calibration — {rep['window']}", "",
           f"**{a['games']} completed games** with both lineups' form computed "
           "point-in-time. 'Hot win' = how often the hotter lineup won; ROI = $1 "
           "on the hotter lineup at its ESPN closing moneyline.", "",
           "| gap bucket | games | hot lineup won | priced | ROI |", "|---|---|---|---|---|"]

    def row(label, c):
        hw = f"{c['hot_win']:.0%}" if c["hot_win"] is not None else "—"
        roi = f"{c['roi']:+.1%}" if c["roi"] is not None else "—"
        out.append(f"| {label} | {c['n']} | {hw} | {c['priced']} | {roi} |")
    row("below current floor (<.015)", a["below_floor_<.015"])
    row("ANY signal gap (>=.015, current rule)", a["any_gap_.015+"])
    for k, c in a["bands"].items():
        row(k, c)
    out += ["", "_~50% hot-win / ~-4% ROI = the gap is noise at that size; a band "
            "meaningfully above (and profitable) = set FORM_DIFF_FLOOR there. Season "
            "baseline is as-of-now (biases deltas toward zero, not toward the signal)._"]
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Player hot/cold form calibration")
    p.add_argument("--days", type=int, default=21)
    p.add_argument("--end", default=yesterday_eastern())
    args = p.parse_args()
    rows = collect(args.end, args.days)
    rep = {"window": f"{args.days} days ending {args.end}", "analysis": analyze(rows)}
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "form_calibration.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "form_calibration.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
