"""
Recurring winners-vs-losers audit: every ~10 days, do exactly what the manual
graded-game autopsy did - join every settled bet with the frozen signals it was
made on and report what's working and what isn't.

Per book (picks / leans / locks / fades): record + units. Across picks+leans
(the bets ON the stat side): win rate by signal count, by each individual
signal, and the winners-vs-losers medians of the underlying component gaps
(margin, FIP, wOBA, ISO). Writes output/audit.{json,md}.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import statistics as st
import zoneinfo
from pathlib import Path

from . import grade
from .analysis import LEAN_MIN_CONSISTENCY, LEAN_STRONG_MARGIN

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("audit")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")


def _game_for(entry: dict) -> dict | None:
    try:
        day = json.loads((OUTPUT_DIR / f"picks_{entry['date']}.json").read_text())
    except (OSError, ValueError):
        return None
    return next((x for x in day.get("games", [])
                 if x.get("matchup") == entry["matchup"]), None)


def _signals(g: dict, bet: str) -> dict | None:
    """Recompute the five signals from the frozen snapshot (only meaningful for
    bets ON the advantage team)."""
    pc = g.get("pick_criteria", {})
    if pc.get("advantage_team") != bet:
        return None
    ml = pc.get("advantage_moneyline")
    lc = pc.get("line_check") or {}
    b = g.get("bvp") or {}
    c = pc.get("components", {})
    margin = c.get("stat_edge", {}).get("margin")
    cons = c.get("consistency", {}).get("hits")
    if margin is None or cons is None:
        return None
    return {
        "margin": margin >= LEAN_STRONG_MARGIN,
        "favorite": ml is not None and ml < 0,
        "line": lc.get("status") == "confirms",
        "consistency": cons >= LEAN_MIN_CONSISTENCY,
        "bvp": not (b.get("edge_team") and b["edge_team"] != bet),
        "_margin_val": margin,
    }


def _gaps(g: dict, bet: str) -> dict:
    """Component gaps (our side minus theirs) from the frozen snapshot."""
    sa = g.get("statistical_advantage", {})
    h, a = sa.get("home") or {}, sa.get("away") or {}
    away_name, home_name = g["matchup"].split(" @ ")
    mine, theirs = (h, a) if bet == home_name else (a, h)

    def num(d, k):
        v = d.get(k)
        return v if isinstance(v, (int, float)) else None

    def off(d, k):
        return (d.get("offense") or {}).get(k)

    out = {}
    mf, tf = num(mine, "combined_fip_sos_adj"), num(theirs, "combined_fip_sos_adj")
    out["fip_gap"] = (tf - mf) if mf is not None and tf is not None else None
    for k in ("woba", "iso"):
        mv, tv = off(mine, k), off(theirs, k)
        out[f"{k}_gap"] = (mv - tv) if mv is not None and tv is not None else None
    return out


def _wr(rows: list[dict]) -> str:
    n = len(rows)
    if not n:
        return "0 games"
    w = sum(r["won"] for r in rows)
    u = round(sum(r["profit"] for r in rows), 2)
    return f"{w}-{n - w} ({w / n:.0%}) {u:+.2f}u"


def build() -> tuple[dict, str]:
    led = grade.load_ledger()
    books = {k: led.get(k, {}).get("entries", []) for k in ("picks", "leans", "locks", "fades")}

    # bets ON the stat side, joined with their frozen signals
    rows: list[dict] = []
    for book in ("picks", "leans"):
        for e in books[book]:
            g = _game_for(e)
            if not g:
                continue
            sig = _signals(g, e["bet"])
            if not sig:
                continue
            rows.append({"won": e["result"] == "W", "profit": e["profit"],
                         "book": book, "signals": sig, "gaps": _gaps(g, e["bet"])})

    md = [f"# 10-day audit — generated {dt.datetime.now(EASTERN).date()}", ""]
    md.append("## Books")
    for k in ("picks", "leans", "locks", "fades"):
        b = led.get(k, {})
        r = b.get("record", {})
        md.append(f"- **{k}**: {r.get('wins', 0)}-{r.get('losses', 0)} "
                  f"({b.get('bankroll', 0):+.2f}u)")
    md.append("")

    rep: dict = {"books": {k: led.get(k, {}).get("record") for k in books}}
    if rows:
        md.append(f"## Signals on the {len(rows)} graded picks+leans")
        counts: dict[int, list] = {}
        for r in rows:
            n = sum(1 for k in ("margin", "favorite", "line", "consistency", "bvp")
                    if r["signals"][k])
            counts.setdefault(n, []).append(r)
        md.append("")
        md.append("| signals hit | record |")
        md.append("|---|---|")
        for n in sorted(counts, reverse=True):
            md.append(f"| {n}/5 | {_wr(counts[n])} |")
        md.append("")
        md.append("| signal present | with it | without it |")
        md.append("|---|---|---|")
        for k in ("margin", "favorite", "line", "consistency", "bvp"):
            yes = [r for r in rows if r["signals"][k]]
            no = [r for r in rows if not r["signals"][k]]
            md.append(f"| {k} | {_wr(yes)} | {_wr(no)} |")
        md.append("")
        W = [r for r in rows if r["won"]]
        L = [r for r in rows if not r["won"]]
        if W and L:
            md.append("| component gap | winners median | losers median |")
            md.append("|---|---|---|")
            for k in ("fip_gap", "woba_gap", "iso_gap"):
                wv = [r["gaps"][k] for r in W if r["gaps"][k] is not None]
                lv = [r["gaps"][k] for r in L if r["gaps"][k] is not None]
                if wv and lv:
                    md.append(f"| {k} | {st.median(wv):+.3f} | {st.median(lv):+.3f} |")
            mw = [r["signals"]["_margin_val"] for r in W]
            ml_ = [r["signals"]["_margin_val"] for r in L]
            md.append(f"| margin | {st.median(mw):+.3f} | {st.median(ml_):+.3f} |")
        rep["graded_rows"] = len(rows)
    else:
        md.append("_No graded picks/leans joined yet - record is young._")

    md.append("")
    md.append("_Auto-generated every ~10 days. Same method as the manual autopsy: every "
              "settled bet joined back to the frozen signals it was made with._")
    return rep, "\n".join(md)


def main() -> None:
    rep, md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "audit.json").write_text(json.dumps(rep, indent=2))
    (OUTPUT_DIR / "audit.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
