"""
Backtest the Leans and Leans-faded books over the last N days, in units.

For each completed game, reconstruct the stat edge point-in-time (no lookahead)
to get the advantage team, price both sides from ESPN (covers gap-fill; even money
where neither has a line), and settle:

  - Leans       : $1 on the advantage team (the stat favorite)
  - Leans-faded : $1 on the other team (bet against the favorite)

PICKS are NOT here on purpose: a pick needs the public-fade gate, and there's no
recoverable historical public-betting data - so picks can't be backtested (the
forward ledger is their only measure). We do report the pick-eligible pool (games
that cleared the >=EDGE_THRESHOLD stat-edge gate) as context.

Runs on GitHub Actions (APIs firewalled in the sandbox). Full lineup enrichment,
so keep the window modest.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import covers, espn, grade, mlb_api
from .analysis import EDGE_THRESHOLD, find_slate_line, statistical_favorite

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("backtest_books")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")


def _date_range(end: str, days: int) -> list[str]:
    e = dt.date.fromisoformat(end)
    return [(e - dt.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _slate(date: str) -> list:
    try:
        s = espn.lines(date)
    except Exception:
        s = []
    if not s:
        try:
            s = covers.slate_lines()
        except Exception:
            s = []
    return s


def _book() -> dict:
    return {"wins": 0, "losses": 0, "units": 0.0, "real_odds": 0, "even_money": 0}


def _settle(book: dict, won: bool, ml: int | None) -> None:
    odds = ml if ml is not None else 100
    book["real_odds" if ml is not None else "even_money"] += 1
    book["units"] = round(book["units"] + (grade.american_profit(odds) if won else -grade.STAKE), 2)
    book["wins" if won else "losses"] += 1


def run(end: str, days: int) -> dict:
    leans, faded = _book(), _book()
    pool = 0  # games clearing the stat-edge gate (pick-eligible, fade unknown)
    entries: list[dict] = []
    for d in _date_range(end, days):
        try:
            games = mlb_api.schedule_for(d)
            results = mlb_api.results_for(d)
        except Exception as exc:
            log.warning("fetch %s failed: %s", d, exc)
            continue
        slate = _slate(d)
        for g in games:
            res = results.get(g.game_pk)
            if not res or not res["final"] or not res["winner"]:
                continue
            try:
                mlb_api.enrich_with_stats(g, d, as_of=d)
            except Exception as exc:
                log.warning("enrich %s failed: %s", g.game_pk, exc)
                continue
            fav, hs, as_ = statistical_favorite(g)
            opp = g.away if fav.team_id == g.home.team_id else g.home
            if abs(hs - as_) >= EDGE_THRESHOLD:
                pool += 1
            side = "home" if fav.team_id == g.home.team_id else "away"
            e = find_slate_line(g, slate)
            fav_ml = e.get(f"{side}_current") if e else None
            opp_ml = e.get(f"{'away' if side == 'home' else 'home'}_current") if e else None
            fav_won = res["winner"] == fav.name
            _settle(leans, fav_won, fav_ml)
            _settle(faded, not fav_won, opp_ml)
            entries.append({"date": d, "matchup": f"{g.away.name} @ {g.home.name}",
                            "favorite": fav.name, "won": fav_won})
    return {"window": f"{_date_range(end, days)[0]} → {end} ({days} days)",
            "settled_games": leans["wins"] + leans["losses"],
            "leans": leans, "leans_faded": faded, "pick_eligible_pool": pool,
            "entries": entries}


def summary_md(rep: dict) -> str:
    def book_line(name, b):
        n = b["wins"] + b["losses"]
        wr = f"{b['wins'] / n:.0%}" if n else "—"
        return (f"- **{name}: {b['units']:+.2f}u** ({b['wins']}-{b['losses']}, {wr} win) "
                f"_[{b['real_odds']} real odds, {b['even_money']} even-money]_")
    out = [f"# Books backtest — {rep['window']}", ""]
    out.append(f"**{rep['settled_games']} settled games** · $1/bet")
    out.append("")
    out.append(book_line("Leans (bet the stat favorite)", rep["leans"]))
    out.append(book_line("Leans faded (bet against)", rep["leans_faded"]))
    out.append("")
    out.append(f"**Picks: not backtestable** — a pick needs the public-fade gate and "
               f"there's no historical public-betting data. (Pick-eligible pool: "
               f"{rep['pick_eligible_pool']} games cleared the {EDGE_THRESHOLD} edge gate, "
               f"but whether the public was fading them can't be reconstructed.)")
    out.append("")
    out.append("_Stats point-in-time (no lookahead); odds from ESPN/covers, even money "
               "where unavailable; SOS uses season totals (small forward bias)._")
    return "\n".join(out)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    p = argparse.ArgumentParser(description="Backtest the Leans / Leans-faded books in units")
    p.add_argument("--days", type=int, default=10)
    p.add_argument("--end", default=yesterday_eastern())
    args = p.parse_args()

    rep = run(args.end, args.days)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "books_backtest.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "books_backtest.md").write_text(summary_md(rep))
    print(summary_md(rep))


if __name__ == "__main__":
    main()
