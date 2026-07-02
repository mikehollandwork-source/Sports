"""
Weather calibration: does weather actually move MONEYLINE outcomes?

Weather mostly moves totals (both teams share the park), so the only effect that
could matter for our bets is asymmetric: in a hot / windy open-air park the ball
carries, which should help the more POWER-dependent lineup. Test: for each
completed open-air game, point-in-time season ISO for both teams -> the "power
favorite" -> did they win? Compare hot/windy games vs mild ones. A real lift in
the hot/windy bucket = weather earns an ISO-interaction nudge; ~0 = weather stays
a display line.

Historical hourly conditions come from Open-Meteo's ERA5 archive (free, no key,
one call per stadium for the whole window). Domes/retractables are excluded
(roof state unknowable). Runs on GitHub Actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

import requests

from . import mlb_api
from .weather import STADIUMS

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("wx_calibrate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

ARCHIVE = ("https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
           "&start_date={start}&end_date={end}&hourly=temperature_2m,wind_speed_10m"
           "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=UTC")
HOT_TEMP = 85     # degrees F at first pitch that counts as a hot game
WINDY_MPH = 12    # wind speed that counts as windy
MIN_GAMES = 15    # season sample needed for a team's point-in-time ISO
_WX_CACHE: dict = {}
_ISO_CACHE: dict = {}


def _date_range(end: str, days: int) -> list[str]:
    e = dt.date.fromisoformat(end)
    return [(e - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _venue_hours(venue: str, start: str, end: str) -> dict[str, tuple[float, float]]:
    """{'"YYYY-MM-DDTHH"': (temp_f, wind_mph)} for the window, one archive call
    per stadium. {} on failure (those games just drop out)."""
    if venue in _WX_CACHE:
        return _WX_CACHE[venue]
    spot = STADIUMS.get(venue)
    out: dict = {}
    if spot and spot[2] == "open":
        try:
            r = requests.get(ARCHIVE.format(lat=spot[0], lon=spot[1], start=start, end=end),
                             timeout=30)
            r.raise_for_status()
            h = r.json()["hourly"]
            out = {h["time"][i][:13]: (h["temperature_2m"][i], h["wind_speed_10m"][i])
                   for i in range(len(h["time"]))
                   if h["temperature_2m"][i] is not None}
        except Exception as exc:
            log.warning("archive weather failed for %s: %s", venue, exc)
    _WX_CACHE[venue] = out
    return out


def _team_iso(team_id: int, season: int, as_of: str) -> float | None:
    """Point-in-time season ISO from the cached team game log (no lookahead)."""
    key = (team_id, season, as_of)
    if key in _ISO_CACHE:
        return _ISO_CACHE[key]
    iso = None
    try:
        hit_splits, _ = mlb_api._team_gamelog(team_id, season)
        ab = h = tb = 0
        games = 0
        for sp in hit_splits:
            if sp.get("date", "") >= as_of:
                continue
            st = sp.get("stat", {})
            ab += int(st.get("atBats", 0) or 0)
            h += int(st.get("hits", 0) or 0)
            tb += int(st.get("totalBases", 0) or 0)
            games += 1
        if games >= MIN_GAMES and ab > 0:
            iso = (tb - h) / ab
    except Exception as exc:
        log.warning("point-in-time ISO failed for %s: %s", team_id, exc)
    _ISO_CACHE[key] = iso
    return iso


def collect(end: str, days: int) -> list[dict]:
    """One row per completed OPEN-AIR game with weather + both ISOs:
    {power_won, iso_gap, temp, wind}."""
    dates = _date_range(end, days)
    rows: list[dict] = []
    for d in dates:
        season = int(d[:4])
        try:
            games = mlb_api.schedule_for(d)
            results = mlb_api.results_for(d)
        except Exception as exc:
            log.warning("fetch %s failed: %s", d, exc)
            continue
        for g in games:
            res = results.get(g.game_pk)
            if not res or not res["final"] or not res["winner"]:
                continue
            wx = _venue_hours(g.venue, dates[0], dates[-1])
            if not wx or not g.start_time:
                continue
            hour = g.start_time[:13]
            if hour not in wx:
                continue
            temp, wind = wx[hour]
            hi = _team_iso(g.home.team_id, season, d)
            ai = _team_iso(g.away.team_id, season, d)
            if hi is None or ai is None or hi == ai:
                continue
            power = g.home if hi > ai else g.away
            rows.append({"power_won": int(res["winner"] == power.name),
                         "iso_gap": round(abs(hi - ai), 4),
                         "temp": temp, "wind": wind})
        log.info("collected through %s (%d open-air games)", d, len(rows))
    return rows


def _wr(rs: list[dict]) -> tuple[int, float | None]:
    n = len(rs)
    return n, (round(sum(r["power_won"] for r in rs) / n, 3) if n else None)


def analyze(rows: list[dict]) -> dict:
    n, overall = _wr(rows)
    if not n:
        return {"games": 0}
    hot = [r for r in rows if r["temp"] >= HOT_TEMP or r["wind"] >= WINDY_MPH]
    mild = [r for r in rows if r not in hot]
    hn, hwr = _wr(hot)
    mn, mwr = _wr(mild)
    # sharpen: hot/windy AND a real power gap (top third of iso_gap)
    cut = sorted(r["iso_gap"] for r in rows)[int(n * 2 / 3)]
    hot_big = [r for r in hot if r["iso_gap"] >= cut]
    hbn, hbwr = _wr(hot_big)
    return {"games": n, "power_favorite_overall": overall,
            "hot_or_windy": {"n": hn, "power_won": hwr},
            "mild": {"n": mn, "power_won": mwr},
            "lift": round((hwr or 0) - (mwr or 0), 3) if hwr is not None and mwr is not None else None,
            "hot_windy_and_big_power_gap": {"n": hbn, "power_won": hbwr,
                                            "iso_gap_cut": round(cut, 3)}}


def summary_md(rep: dict) -> str:
    a = rep["analysis"]
    out = [f"# Weather calibration — {rep['window']}", ""]
    if not a.get("games"):
        out.append("No open-air games with weather + point-in-time ISO for both teams.")
        return "\n".join(out)
    out.append(f"**{a['games']} open-air games** · the power team (higher season ISO) "
               f"won **{a['power_favorite_overall']:.0%}** overall")
    out.append("")
    h, m = a["hot_or_windy"], a["mild"]
    out.append(f"- hot/windy (≥{HOT_TEMP}°F or ≥{WINDY_MPH}mph wind, {h['n']} games): "
               f"power team won **{h['power_won']:.0%}**")
    out.append(f"- mild ({m['n']} games): power team won **{m['power_won']:.0%}**")
    if a["lift"] is not None:
        out.append(f"- **weather lift: {a['lift']:+.0%}**")
    hb = a["hot_windy_and_big_power_gap"]
    if hb["power_won"] is not None:
        out.append(f"- hot/windy AND big power gap (ISO gap ≥{hb['iso_gap_cut']}, "
                   f"{hb['n']} games): **{hb['power_won']:.0%}**")
    out.append("")
    out.append("_Point-in-time season ISO (no lookahead); ERA5 hourly conditions at first "
               "pitch; domes/retractables excluded. Clear positive lift = weather earns an "
               "ISO-interaction nudge in the margin; ~0 = weather stays display-only._")
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Weather x power moneyline calibration")
    p.add_argument("--days", type=int, default=60)
    p.add_argument("--end", default=(dt.datetime.now(EASTERN).date()
                                     - dt.timedelta(days=6)).isoformat(),
                   help="last date; defaults to 6 days ago (ERA5 archive lag)")
    args = p.parse_args()

    rep = {"window": f"{_date_range(args.end, args.days)[0]} → {args.end} ({args.days} days)",
           "analysis": analyze(collect(args.end, args.days))}
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "wx_calibration.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "wx_calibration.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
