"""
Grade the picks the edge finder made against actual MLB results and keep a
running $1-per-pick bankroll in output/ledger.json.

Each flagged pick is a $1 bet on that team's moneyline. We have no true
historical closing odds (covers serves only current lines), so settlement uses
an even-money (+100) assumption: a win is +$1.00, a loss is -$1.00. The ledger
is idempotent per date, so re-running a day never double-counts it.

Runs on GitHub Actions (the MLB API is firewalled in the build sandbox). Default
date is yesterday (US/Eastern) - i.e. grade the prior day once its games are final.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import zoneinfo
from pathlib import Path

from . import mlb_api

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("grade")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
LEDGER_PATH = OUTPUT_DIR / "ledger.json"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

STAKE = 1.0
ODDS = 100  # even money (+100); see module docstring


def american_profit(odds: int, stake: float = STAKE) -> float:
    """Win profit for a `stake` bet at American `odds` (loss is always -stake)."""
    return stake * odds / 100.0 if odds > 0 else stake * 100.0 / abs(odds)


def empty_ledger() -> dict:
    return {"bankroll": 0.0, "stake": STAKE,
            "odds_basis": "pick-time moneyline when recorded, else +100 (even money)",
            "record": {"wins": 0, "losses": 0, "picks": 0},
            "entries": []}


def _pick_moneyline(g: dict) -> int | None:
    """The pick's actual moneyline captured at pick time (from betting_lines),
    as an int (+104, -115). None if this game had no recorded line."""
    bl = g.get("betting_lines")
    if not bl:
        return None
    for side in (bl.get("majority"), bl.get("non_majority")):
        if side and side.get("team") == g.get("pick") and side.get("moneyline"):
            try:
                return int(str(side["moneyline"]).replace("+", ""))
            except (ValueError, TypeError):
                return None
    return None


def load_ledger() -> dict:
    if LEDGER_PATH.exists():
        led = json.loads(LEDGER_PATH.read_text())
        led.pop("odds_assumption", None)  # legacy key -> normalize to odds_basis
        led.setdefault("odds_basis", empty_ledger()["odds_basis"])
        return led
    return empty_ledger()


def save_ledger(ledger: dict) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2))


def grade_date(date: str) -> list[dict]:
    """Settle the flagged picks in output/picks_<date>.json against final scores.
    Returns one entry per graded pick (skips games not yet final)."""
    picks_path = OUTPUT_DIR / f"picks_{date}.json"
    if not picks_path.exists():
        log.warning("no picks file for %s", date)
        return []
    payload = json.loads(picks_path.read_text())
    results = mlb_api.results_for(date)

    settled: list[dict] = []
    for g in payload.get("games", []):
        if not g.get("flagged"):
            continue
        res = results.get(g.get("game_pk"))
        if not res or not res["final"] or not res["winner"]:
            log.info("skip ungraded pick %s (%s)", g.get("pick"), g.get("matchup"))
            continue
        won = res["winner"] == g["pick"]
        ml = _pick_moneyline(g)
        odds = ml if ml is not None else ODDS
        sa = g.get("statistical_advantage", {})
        pc = g.get("pick_criteria", {})
        comp = pc.get("components", {})
        settled.append({
            "key": f"{date}#{g['game_pk']}",
            "date": date,
            "matchup": g["matchup"],
            "pick": g["pick"],
            "result": "W" if won else "L",
            "score": f"{res['away']} {res['away_score']} @ {res['home']} {res['home_score']}",
            "odds": odds,
            "odds_source": "pick-time moneyline" if ml is not None else "assumed even (+100)",
            "profit": round(american_profit(odds) if won else -STAKE, 2),
            # context kept so losses can be reviewed / the formula auto-tuned
            "win_condition_hits": pc.get("win_condition_hits"),
            "confidence": pc.get("confidence"),
            "edge_strength": comp.get("stat_edge", {}).get("strength"),
            "fade_strength": comp.get("public_fade", {}).get("strength"),
            "wc_strength": comp.get("win_condition", {}).get("strength"),
            "edge_margin": round(abs((sa.get("home_score") or 0) - (sa.get("away_score") or 0)), 3),
            "underdog": odds > 0,
        })
    return settled


def update_ledger(date: str) -> dict:
    """Append a date's newly-final picks to the ledger. Idempotent per *pick*
    (by game_pk), so re-running a partially-complete day safely catches the
    games that have since gone final without double-counting settled ones."""
    ledger = load_ledger()
    done = {e["key"] for e in ledger["entries"]}

    added = 0
    for e in grade_date(date):
        if e["key"] in done:
            continue
        ledger["bankroll"] = round(ledger["bankroll"] + e["profit"], 2)
        ledger["record"]["wins" if e["result"] == "W" else "losses"] += 1
        ledger["record"]["picks"] += 1
        e["bankroll_after"] = ledger["bankroll"]
        ledger["entries"].append(e)
        added += 1

    if added:
        ledger["review"] = review(ledger)
        save_ledger(ledger)
        log.info("graded %s: +%d pick(s), bankroll now %+.2f",
                 date, added, ledger["bankroll"])
    else:
        log.info("nothing new to settle for %s", date)
    return ledger


def _avg(xs: list) -> float | None:
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 2) if xs else None


def review(ledger: dict) -> dict:
    """Summarize wins vs losses so each loss makes the system tunable (item 3).
    Reporting only - it surfaces what to change, it does not change the formula."""
    e = ledger["entries"]
    wins = [x for x in e if x["result"] == "W"]
    losses = [x for x in e if x["result"] == "L"]
    rev = {
        "wins": len(wins), "losses": len(losses),
        "avg_win_cond_hits_on_wins": _avg([x.get("win_condition_hits") for x in wins]),
        "avg_win_cond_hits_on_losses": _avg([x.get("win_condition_hits") for x in losses]),
        "avg_edge_margin_on_wins": _avg([x.get("edge_margin") for x in wins]),
        "avg_edge_margin_on_losses": _avg([x.get("edge_margin") for x in losses]),
        "losses_as_underdog": sum(1 for x in losses if x.get("underdog")),
        "losses_as_favorite": sum(1 for x in losses if x.get("underdog") is False),
    }
    rev["suggestions"] = _suggestions(rev)
    return rev


def _suggestions(rev: dict) -> list[str]:
    """Actionable tuning hints once enough losses have accrued (>= 4)."""
    out: list[str] = []
    if rev["losses"] < 4:
        return out
    wc_w, wc_l = rev["avg_win_cond_hits_on_wins"], rev["avg_win_cond_hits_on_losses"]
    if wc_w is not None and wc_l is not None and wc_l + 0.5 < wc_w:
        out.append("Losses skew to lower win-condition hits — raise W_WC or CONF_MIN.")
    em_w, em_l = rev["avg_edge_margin_on_wins"], rev["avg_edge_margin_on_losses"]
    if em_w is not None and em_l is not None and em_l + 0.05 < em_w:
        out.append("Losses have thinner stat edges — raise W_EDGE or CONF_MIN.")
    if rev["losses_as_favorite"] >= 4 and rev["losses_as_favorite"] >= 2 * max(1, rev["losses_as_underdog"]):
        out.append("Most losses are favorites (-odds) — consider an underdog-only filter.")
    return out


def bankroll_line(ledger: dict | None = None) -> str:
    """One-line bankroll summary for the daily issue."""
    ledger = ledger or load_ledger()
    r = ledger["record"]
    return (f"**Running bankroll: {ledger['bankroll']:+.2f} units** "
            f"({r['wins']}-{r['losses']} on {r['picks']} picks, $1/pick; "
            f"pick-time moneyline odds, even-money fallback)")


def review_line(ledger: dict | None = None) -> str:
    """Loss-review note for the daily issue (empty until there are losses)."""
    ledger = ledger or load_ledger()
    rev = ledger.get("review") or review(ledger)
    if not rev["losses"]:
        return ""
    parts = [f"**Loss review:** {rev['losses']} loss(es); "
             f"avg win-condition hits — wins {rev['avg_win_cond_hits_on_wins']} "
             f"vs losses {rev['avg_win_cond_hits_on_losses']}."]
    parts += [f"→ {s}" for s in rev["suggestions"]]
    return " ".join(parts)


def yesterday_eastern() -> str:
    return (dt.datetime.now(EASTERN).date() - dt.timedelta(days=1)).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Grade picks + update the bankroll ledger")
    parser.add_argument("--date", default=os.environ.get("GRADE_DATE") or yesterday_eastern(),
                        help="date to grade (YYYY-MM-DD); default = yesterday US/Eastern")
    args = parser.parse_args()
    ledger = update_ledger(args.date)
    from . import tune
    state = tune.auto_tune(ledger)   # bankroll-driven param tuning (writes tuning.json)
    print(bankroll_line(ledger))
    print(tune.status_line(state))


if __name__ == "__main__":
    main()
