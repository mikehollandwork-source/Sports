"""
Why every game on the board passed or failed, gate by gate.

WHY THIS EXISTS
The board says "no play" and gives one reason - the FIRST gate that failed,
because `consensus.evaluate` short-circuits. That is the right thing for the
board and the wrong thing for understanding it: a game that dies at gate 1 might
have failed gates 5 and 6 as well, or might have sailed through them. Those are
very different slates and they look identical on the board.

This evaluates every gate independently for every game, so a near-miss is
visible as a near-miss.

THE GATES, in the order consensus.evaluate() checks them:
    1 handle agrees with tickets   public_check.money == "with public"
    2 ticket majority exists       public_majority.team
    3 price available              for whichever side the consensus names
    4 usable order-book read       >= MIN_READINGS quotes, spread <= MAX_SPREAD
    5 book confirms that side      mid drifted up, or resting bid lean > IMBALANCE_MIN
    6 line moved AGAINST us        implied prob moved away by >= LINE_MOVE_MIN

Gate 5 is skipped rather than failed when gate 4 gave nothing to read - absence
of data and data pointing the wrong way are different problems that look the
same on the board, and conflating them hides a dead feed.

Writes output/gates_<date>.md.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import sys
import zoneinfo
from collections import Counter
from pathlib import Path

from . import consensus as C

log = logging.getLogger("gate_report")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")

GATES = ["handle=tickets", "majority", "price", "book read",
         "book confirms", "line against"]


def evaluate_gates(g: dict, metrics: dict) -> dict:
    """Every gate for one game, evaluated independently of short-circuiting."""
    pc = g.get("pick_criteria") or {}
    chk = g.get("public_check") or {}
    maj = (g.get("public_majority") or {}).get("team")
    adv = pc.get("advantage_team")
    m = metrics.get(g.get("game_pk"))

    odds = None
    if maj and adv:
        odds = (pc.get("advantage_moneyline") if maj == adv
                else pc.get("opponent_moneyline"))
    tag = C.line_tag(g, maj) if maj else None
    return {
        "matchup": g.get("matchup") or "",
        "side": maj, "odds": odds, "adv": adv, "metrics": m, "line": tag,
        "money": chk.get("money") or "no money read",
        "start": g.get("game_datetime"),
        "play": pc.get("play"),
        "gates": [
            chk.get("money") == "with public",
            bool(maj),
            isinstance(odds, int),
            m is not None,
            # None, not False: nothing to read is not the same as reading wrong
            (C._confirms(m, maj == adv) if (m and maj and adv) else None),
            (tag == "against") if tag else None,
        ],
    }


def _mark(v) -> str:
    return "PASS" if v is True else ("FAIL" if v is False else "—")


def build(date: str) -> str:
    path = OUTPUT_DIR / f"picks_{date}.json"
    try:
        day = json.loads(path.read_text())
    except (OSError, ValueError):
        return f"# Gate report — {date}\n\nNo board file.\n"
    metrics = C.book_metrics(date)
    rows = [evaluate_gates(g, metrics) for g in day.get("games", [])]

    md = [f"# Gate report — {date}", "",
          f"_board generated `{day.get('generated_at')}` · {len(rows)} games_", "",
          "| # | matchup | consensus side | " + " | ".join(GATES) + " | verdict |",
          "|---" * (len(GATES) + 4) + "|"]
    for i, r in enumerate(rows, 1):
        side = r["side"] or "—"
        if isinstance(r["odds"], int):
            side += f" {r['odds']:+d}"
        cells = " | ".join(_mark(v) for v in r["gates"])
        verdict = "**PICK**" if r["play"] == "pick" else "no play"
        md.append(f"| {i} | {r['matchup']} | {side} | {cells} | {verdict} |")
    md.append("")

    md += ["## Gate definitions", "",
           f"1. **handle=tickets** — the dollars are on the same side as the "
           f"ticket majority",
           "2. **majority** — a ticket majority was read at all",
           "3. **price** — a moneyline exists for the side the consensus names",
           f"4. **book read** — ≥{C.MIN_READINGS} Polymarket quotes with spread "
           f"≤{C.MAX_SPREAD}",
           f"5. **book confirms** — mid drifted up on that side, or resting bid "
           f"lean >{C.IMBALANCE_MIN}",
           f"6. **line against** — implied probability moved AWAY from that side "
           f"by ≥{C.LINE_MOVE_MIN:.0%} (the price discount)", "",
           "_Gate 5 shows `—` when gate 4 gave nothing to read: no data and data "
           "pointing the wrong way are different problems._", ""]

    # near-misses are the interesting part and the board never shows them
    near = [r for r in rows if r["play"] != "pick"
            and all(v is not False for v in r["gates"][:5])
            and r["gates"][5] is False]
    if near:
        md += ["## Near-misses — cleared everything except the price discount", ""]
        for r in near:
            md.append(f"- **{r['matchup']}** — {r['side']} "
                      f"{r['odds']:+d}, line `{r['line']}`")
        md.append("")

    md += ["## Where games first failed", "", "| gate | games |", "|---|---|"]
    first = Counter()
    for r in rows:
        for name, v in zip(GATES, r["gates"]):
            if v is False:
                first[name] += 1
                break
        else:
            first["passed all"] += 1
    for k, v in first.most_common():
        md.append(f"| {k} | {v} |")
    md.append("")

    # book detail, since gate 5 is the least legible of the six
    md += ["## Order-book detail", "",
           "| matchup | drift | imbalance | reads |", "|---|---|---|---|"]
    for r in rows:
        m = r["metrics"]
        if not m:
            md.append(f"| {r['matchup']} | — | — | none |")
        else:
            md.append(f"| {r['matchup']} | {m['drift']:+.4f} | "
                      f"{m['imbalance']:+.2f} | ok |")
    md.append("")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    date = (sys.argv[1] if len(sys.argv) > 1
            else dt.datetime.now(EASTERN).date().isoformat())
    md = build(date)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / f"gates_{date}.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
