"""
Wikipedia-attention calibration: does fading the more-popular team have edge?

For each completed game we take each team's pageviews in the days before the game
(point-in-time, no lookahead), call the higher-pageview team the "attention
favorite" (the popular/hyped side the public piles onto), and check how often it
WON. A fade system wants that number BELOW 50% - the more the public's attention
team loses, the more fading it is worth. Bucketed by the attention gap so we can
see whether a bigger popularity gap means a bigger fade edge.

Cheap (two pageview calls per game, cached). Runs on GitHub Actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import mlb_api, wiki

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("wiki_calibrate")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")


def _date_range(end: str, days: int) -> list[str]:
    e = dt.date.fromisoformat(end)
    return [(e - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def collect(end: str, days: int) -> list[dict]:
    """One row per game: {attn_fav_won, gap} where the attention favorite is the
    team with more pre-game pageviews and gap is the normalized popularity gap."""
    rows: list[dict] = []
    for d in _date_range(end, days):
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
            hv = wiki.team_window_views(g.home.name, d)
            av = wiki.team_window_views(g.away.name, d)
            if not hv or not av:
                continue
            fav = g.home if hv > av else g.away
            gap = round(abs(hv - av) / (hv + av), 3)
            rows.append({"attn_fav_won": int(res["winner"] == fav.name), "gap": gap})
        log.info("collected through %s (%d games with pageviews)", d, len(rows))
    return rows


def analyze(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"games": 0}
    fav_wr = sum(r["attn_fav_won"] for r in rows) / n
    cut = sorted(r["gap"] for r in rows)[int(n * 2 / 3)]
    big = [r for r in rows if r["gap"] >= cut]
    small = [r for r in rows if r["gap"] < cut]
    bwr = sum(r["attn_fav_won"] for r in big) / len(big) if big else None
    swr = sum(r["attn_fav_won"] for r in small) / len(small) if small else None
    return {
        "games": n,
        "attention_favorite_win_rate": round(fav_wr, 3),
        "fade_win_rate": round(1 - fav_wr, 3),
        "big_gap_favorite_win_rate": round(bwr, 3) if bwr is not None else None,
        "big_gap_fade_win_rate": round(1 - bwr, 3) if bwr is not None else None,
        "big_gap_n": len(big), "big_gap_cut": round(cut, 3),
        "fade_lift_big_vs_small": round(swr - bwr, 3) if bwr is not None and swr is not None else None,
    }


def summary_md(rep: dict) -> str:
    a = rep["analysis"]
    out = [f"# Wikipedia-attention calibration — {rep['window']}", ""]
    if not a.get("games"):
        out.append("No games with pageviews for both teams.")
        return "\n".join(out)
    out.append(f"**{a['games']} games** · the higher-attention (more-popular) team won "
               f"**{a['attention_favorite_win_rate']:.0%}** → **fading it wins "
               f"{a['fade_win_rate']:.0%}**")
    out.append("")
    if a["big_gap_favorite_win_rate"] is not None:
        out.append(f"At the **biggest popularity gaps** (top third, gap ≥{a['big_gap_cut']}, "
                   f"{a['big_gap_n']} games): attention team won "
                   f"**{a['big_gap_favorite_win_rate']:.0%}** → fade wins "
                   f"**{a['big_gap_fade_win_rate']:.0%}** "
                   f"(fade lift {a['fade_lift_big_vs_small']:+.0%})")
    out.append("")
    out.append("_Pageviews in the 3 days before the game, point-in-time. Fade win rate "
               "clearly above 50% (especially at big gaps) = fading the popular team has "
               "edge; ~50% = attention is noise and shouldn't vote._")
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Wikipedia-attention fade calibration")
    p.add_argument("--days", type=int, default=60)
    p.add_argument("--end", default=yesterday_eastern())
    args = p.parse_args()

    rep = {"window": f"{_date_range(args.end, args.days)[0]} → {args.end} ({args.days} days)",
           "analysis": analyze(collect(args.end, args.days))}
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "wiki_calibration.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "wiki_calibration.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
