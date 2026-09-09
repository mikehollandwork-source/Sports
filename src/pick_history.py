"""
How picks at this price have actually done, from our own record.

WHY PRICE AND NOT TEAM
"How often would this bet have hit" has three readings - picks at this price,
picks on this team, picks with this gate profile. Price is the one worth
showing. `team_line_move` tested the team version directly: the spread of
per-team ROIs sits inside chance (p = 0.62), the split-half correlation is
r = -0.12, and backing the first half's best teams lost money in the second.
A per-team hit rate would look authoritative and mean nothing.

WHAT THE NUMBER IS AND IS NOT
It is the rule's realised hit rate among past picks in the same price band, next
to the breakeven that price demands. The gap between them is the only part that
matters: 70.8% sounds strong until you see that -200 needs 70.8% to break even.

It is NOT a probability for tonight's game. It is a small-sample history of
similar bets, and the buckets hold 24-89 picks, so a couple of games move them
several points. Shown with n so that is visible rather than implied.
"""

from __future__ import annotations

import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

BUCKETS = [
    ("≤-200", lambda o: o <= -200),
    ("-199..-150", lambda o: -199 <= o <= -150),
    ("-149..-120", lambda o: -149 <= o <= -120),
    ("-119..-101", lambda o: -119 <= o <= -101),
    ("+100..+139", lambda o: 100 <= o <= 139),
    ("≥+140", lambda o: o >= 140),
]


def _implied(o: int) -> float:
    return (100 / (o + 100)) if o > 0 else (abs(o) / (abs(o) + 100))


def bucket_for(odds: int) -> str | None:
    for label, test in BUCKETS:
        if test(odds):
            return label
    return None


def record(odds: int) -> dict | None:
    """{bucket, n, wins, losses, hit, breakeven, edge, roi} for past picks at
    this price, or None when the ledger has no comparable bets."""
    label = bucket_for(odds)
    if not label:
        return None
    try:
        entries = json.loads((OUTPUT_DIR / "ledger.json").read_text())["plays"]["entries"]
    except (OSError, ValueError, KeyError):
        return None
    test = dict(BUCKETS)[label]
    rows = [e for e in entries if isinstance(e.get("odds"), int) and test(e["odds"])]
    if not rows:
        return None
    n = len(rows)
    wins = sum(1 for e in rows if e.get("result") == "W")
    hit = wins / n
    be = sum(_implied(e["odds"]) for e in rows) / n
    return {"bucket": label, "n": n, "wins": wins, "losses": n - wins,
            "hit": hit, "breakeven": be, "edge": hit - be,
            "roi": sum(e.get("profit", 0) for e in rows) / n}


def summary(odds: int) -> str:
    """One line for the board: hit rate vs the breakeven that price demands."""
    r = record(odds)
    if not r:
        return "no comparable picks in the record yet"
    return (f"picks at {r['bucket']}: {r['wins']}-{r['losses']} "
            f"({r['hit']:.0%}) vs {r['breakeven']:.0%} breakeven "
            f"({r['edge']:+.0%}), ROI {r['roi']:+.1%} — n={r['n']}")
