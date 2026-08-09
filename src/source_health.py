"""
Tell a dead data source apart from a quiet slate.

THE PROBLEM THIS EXISTS FOR
Every input the board needs degrades to the same symptom: an empty board. If
covers stops parsing, if VSiN changes its markup, if Polymarket's index comes
back empty, if the odds API key lapses - the rule finds nothing and reports "no
plays today", which is exactly what a genuinely quiet slate looks like. Nothing
errors, nothing alerts.

That has already cost real money once: the Kalshi logger sat dead for weeks
behind a status="active" call that 400'd every time, and the fail-soft wrapper
swallowed it. The board itself went dark for six hours on 2026-08-06 with no
error surfaced anywhere.

WHAT IT DOES
Counts, for today's board, how many games carry each input, and compares that
against how many games are on the slate. A source present on nearly every game
is healthy; one present on none while games exist is dead. The distinction the
board cannot make on its own is:

    0 picks + all sources healthy   -> a quiet slate, working as designed
    0 picks + a source at zero      -> BROKEN, and the board is lying to you

Alerts to Telegram only on the second case, and only when it would otherwise
pass unnoticed. A source that is degraded on a day with picks is worth
recording but not worth waking someone for.

Writes output/source_health_<date>.md and appends to output/source_health.json
so degradation over time is visible rather than only the current snapshot.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import zoneinfo
from pathlib import Path

from . import notify

log = logging.getLogger("source_health")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
HISTORY = OUTPUT_DIR / "source_health.json"

# A source is DEAD if it covers this fraction of games or fewer. Not zero:
# covers legitimately misses the odd game, and a single miss is not an outage.
DEAD_AT = 0.10
DEGRADED_AT = 0.60


def _has_tickets(g: dict) -> bool:
    det = ((g.get("public_majority") or {}).get("detail") or {})
    return bool(((det.get("consensus") or {}).get("pcts")))


def _has_handle(g: dict) -> bool:
    """VSiN/handle read. `money` carries the verdict; `vegas.basis` names its
    source. Either present means the handle half actually ran."""
    chk = g.get("public_check") or {}
    if chk.get("money"):
        return True
    return bool((g.get("pick_criteria") or {}).get("vegas", {}).get("basis"))


def _has_line(g: dict) -> bool:
    shift = ((g.get("pick_criteria") or {}).get("line_check") or {}).get("implied_shift")
    return isinstance(shift, (int, float))


def _pm_covered(date: str) -> set:
    """game_pks with at least one real Polymarket reading logged today.

    Read from the pm_books day file, NOT from pick_criteria.consensus. The
    consensus block is only attached to games that clear the gates, so counting
    it measured 'is this a pick' - which reported PM as degraded on exactly the
    quiet days this check exists to vindicate. First run caught it: 4/15
    'coverage' against 4 picks."""
    from . import pm_books

    try:
        day = pm_books.load_day(date) or {}
    except Exception:
        return set()
    out = set()
    for pk, g in (day.get("games") or {}).items():
        if any(not r.get("empty") for r in (g.get("readings") or [])):
            out.add(str(pk))
    return out


def _has_price(g: dict) -> bool:
    pc = g.get("pick_criteria") or {}
    return isinstance(pc.get("advantage_moneyline"), int)


CHECKS = {
    "covers tickets": _has_tickets,
    "handle (VSiN)": _has_handle,
    "line movement": _has_line,
    "moneylines": _has_price,
}


def assess(date: str | None = None) -> dict:
    date = date or dt.datetime.now(EASTERN).date().isoformat()
    path = OUTPUT_DIR / f"picks_{date}.json"
    try:
        day = json.loads(path.read_text())
    except (OSError, ValueError):
        return {"date": date, "games": 0, "error": "no board file"}

    games = day.get("games") or []
    n = len(games)
    picks = sum(1 for g in games
                if (g.get("pick_criteria") or {}).get("play") == "pick")
    out = {"date": date, "generated_at": day.get("generated_at"),
           "games": n, "picks": picks, "sources": {}}
    if not n:
        return out

    pm_pks = _pm_covered(date)
    checks = dict(CHECKS)
    checks["PM order book"] = lambda g: str(g.get("game_pk")) in pm_pks

    for label, fn in checks.items():
        have = sum(1 for g in games if fn(g))
        frac = have / n
        state = ("dead" if frac <= DEAD_AT else
                 "degraded" if frac < DEGRADED_AT else "ok")
        out["sources"][label] = {"have": have, "of": n,
                                 "pct": round(frac * 100), "state": state}
    out["dead"] = [k for k, v in out["sources"].items() if v["state"] == "dead"]
    out["degraded"] = [k for k, v in out["sources"].items()
                       if v["state"] == "degraded"]
    # the case the board cannot report on its own
    out["silent_failure"] = bool(out["dead"]) and picks == 0
    return out


def _append_history(rec: dict) -> None:
    try:
        hist = json.loads(HISTORY.read_text())
    except (OSError, ValueError):
        hist = []
    hist = [h for h in hist if h.get("date") != rec.get("date")]
    hist.append({k: rec.get(k) for k in
                 ("date", "games", "picks", "dead", "degraded", "silent_failure")})
    hist.sort(key=lambda h: h.get("date") or "")
    HISTORY.write_text(json.dumps(hist[-120:], indent=1))


def report(rec: dict) -> str:
    md = [f"# Source health — {rec.get('date')}", "",
          f"- board generated: `{rec.get('generated_at')}`",
          f"- games on slate: **{rec.get('games')}** · picks: **{rec.get('picks')}**",
          ""]
    if rec.get("error"):
        md += [f"**{rec['error']}**", ""]
        return "\n".join(md)
    md += ["| input | games covered | state |", "|---|---|---|"]
    for label, v in (rec.get("sources") or {}).items():
        mark = {"ok": "✅", "degraded": "⚠️", "dead": "❌"}[v["state"]]
        md.append(f"| {label} | {v['have']}/{v['of']} ({v['pct']}%) | {mark} {v['state']} |")
    md.append("")
    if rec.get("silent_failure"):
        md += ["## ❌ SILENT FAILURE", "",
               f"The board shows **0 picks** while these inputs are dead: "
               f"**{', '.join(rec['dead'])}**. That empty board is a data "
               "outage, not a quiet slate - the two are indistinguishable from "
               "the board alone, which is the reason this check exists.", ""]
    elif rec.get("dead"):
        md += [f"## ❌ Dead inputs: {', '.join(rec['dead'])}", "",
               "Picks are still being produced, so the board is not empty - but "
               "it is running on fewer gates than it is supposed to.", ""]
    elif rec.get("degraded"):
        md += [f"## ⚠️ Degraded: {', '.join(rec['degraded'])}", ""]
    else:
        md += ["## ✅ All inputs healthy", "",
               "An empty board today would be a genuinely quiet slate.", ""]
    return "\n".join(md)


def run(date: str | None = None, alert: bool = True) -> dict:
    rec = assess(date)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / f"source_health_{rec['date']}.md").write_text(report(rec))
    _append_history(rec)

    # Alert only on the case that would otherwise pass unnoticed. A dead source
    # on a day with picks is in the report; waking someone for it trains them to
    # ignore the alert that matters.
    if alert and rec.get("silent_failure"):
        try:
            notify.send_telegram(
                "⚠️ Board shows no plays, but that is a DATA OUTAGE, not a quiet "
                f"slate.\n\nDead inputs: {', '.join(rec['dead'])}\n"
                f"Games on slate: {rec['games']}")
        except Exception as exc:
            log.error("could not send health alert: %s", exc)
    log.info("source health %s: dead=%s degraded=%s picks=%s",
             rec["date"], rec.get("dead"), rec.get("degraded"), rec.get("picks"))
    return rec


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    rec = run()
    print(report(rec))
    raise SystemExit(1 if rec.get("silent_failure") else 0)


if __name__ == "__main__":
    main()
