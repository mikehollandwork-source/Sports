"""
Audit the record itself: what was posted vs what got graded.

THE FLAW THIS EXISTS TO MEASURE
The board is stateless - every refresh regenerates picks_<date>.json from
scratch - and `grade.settle_day` reads only the FINAL committed version of that
file. `_lock_started_games` freezes a game 15 minutes before its first pitch, so
anything that stops qualifying BEFORE that window simply disappears.

A game can therefore be posted to Telegram at 2pm as a pick, stop qualifying at
5pm because the order book flipped or the line moved back, and never be graded.
It was a live bet to anyone reading the channel; it is absent from the ledger.

A probe over five dates found 25 games that were a pick in some version of the
board and 8 that survived to the final one. That is not a rounding error, and
whether it flatters or hurts the recorded ROI depends entirely on whether the
dropped picks won - which is what this measures.

WHY THIS MATTERS MORE THAN ANOTHER SIGNAL SCAN
Thirteen signal tests have found nothing. But every one of them, and every ROI
number quoted from this record, rests on the ledger being a faithful list of the
bets that were actually offered. If the ledger silently drops a third of them,
the bias in that number is larger than any edge being hunted.

WHAT IS RECONSTRUCTED
Every committed version of every board, from git history, giving for each game:
    first_posted   the earliest version where it was a pick, and its price then
    final          whether the last version still had it as a pick
Then both populations are graded and compared.

Also reports PRICE DRIFT: for picks that survived, the price when first posted
versus the price finally recorded. The ledger books the frozen closing price,
but the channel showed the earlier one - if they differ systematically, the
recorded ROI is not the ROI a reader of the channel would have got.

Needs full git history: the workflow must check out with fetch-depth 0.

Writes output/record_audit.md.
"""

from __future__ import annotations

import glob
import json
import logging
import subprocess
from pathlib import Path

from . import grade, mlb_api

log = logging.getLogger("record_audit")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPO = Path(__file__).resolve().parent.parent


def _versions(rel: str) -> list[str]:
    """Every commit that touched this board file, oldest first."""
    try:
        out = subprocess.run(["git", "log", "--format=%H", "--all", "--reverse",
                              "--", rel], cwd=REPO, capture_output=True,
                             text=True, timeout=120)
        return [s for s in out.stdout.split() if s]
    except Exception as exc:
        log.warning("git log failed for %s: %s", rel, exc)
        return []


def _at(sha: str, rel: str) -> dict | None:
    try:
        out = subprocess.run(["git", "show", f"{sha}:{rel}"], cwd=REPO,
                             capture_output=True, text=True, timeout=60)
        if out.returncode:
            return None
        return json.loads(out.stdout)
    except Exception:
        return None


def scan_date(date: str) -> dict:
    """{game_pk: {first_bet, first_odds, final_bet, final_odds, matchup}}"""
    rel = f"output/picks_{date}.json"
    shas = _versions(rel)
    if not shas:
        return {}
    seen: dict = {}
    for sha in shas:
        day = _at(sha, rel)
        if not day:
            continue
        for g in day.get("games", []):
            pc = g.get("pick_criteria") or {}
            if pc.get("play") != "pick":
                continue
            pk = g.get("game_pk")
            bet = pc.get("bet_team") or pc.get("advantage_team")
            odds = pc.get("bet_moneyline")
            if odds is None:
                odds = pc.get("advantage_moneyline")
            if not pk or not bet or not isinstance(odds, int):
                continue
            if pk not in seen:
                seen[pk] = {"matchup": g.get("matchup"), "first_bet": bet,
                            "first_odds": odds, "source": pc.get("source", "rule")}
    # the final committed state decides what the ledger books
    final = _at(shas[-1], rel) or {}
    for g in final.get("games", []):
        pc = g.get("pick_criteria") or {}
        pk = g.get("game_pk")
        if pk in seen and pc.get("play") == "pick":
            seen[pk]["final_bet"] = pc.get("bet_team") or pc.get("advantage_team")
            o = pc.get("bet_moneyline")
            seen[pk]["final_odds"] = o if isinstance(o, int) else pc.get("advantage_moneyline")
    return seen


def collect() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        seen = scan_date(date)
        if not seen:
            continue
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        for pk, d in seen.items():
            res = results.get(pk)
            if not res or not res.get("final") or not res.get("winner"):
                continue
            survived = "final_bet" in d
            rows.append({
                "date": date, "game_pk": pk, "matchup": d["matchup"],
                "survived": survived, "source": d.get("source", "rule"),
                "first_bet": d["first_bet"], "first_odds": d["first_odds"],
                "final_odds": d.get("final_odds"),
                "won_first": res["winner"] == d["first_bet"],
                "won_final": (res["winner"] == d["final_bet"]) if survived else None,
            })
    return rows


def _roi(rows, odds_key: str, won_key: str) -> tuple[int, int, float, float]:
    w = u = 0
    for r in rows:
        o = r.get(odds_key)
        if not isinstance(o, int) or r.get(won_key) is None:
            continue
        won = r[won_key]
        w += 1 if won else 0
        u += grade.american_profit(o) if won else -1
    n = sum(1 for r in rows
            if isinstance(r.get(odds_key), int) and r.get(won_key) is not None)
    return w, n - w, u, (u / n if n else 0.0)


def _fmt(rows, odds_key="first_odds", won_key="won_first") -> str:
    w, l, u, roi = _roi(rows, odds_key, won_key)
    if w + l == 0:
        return "—"
    return f"{w}-{l} ({w/(w+l):.0%}) · {u:+.2f}u · **{roi:+.1%}** (n={w+l})"


def build() -> str:
    rows = collect()
    md = ["# Record audit — what was posted vs what got graded", "",
          "_The board is stateless and `settle_day` reads only the final "
          "committed version, so a pick that stops qualifying before its "
          "15-minute lock window disappears. It was on Telegram; it is not in "
          "the ledger._", "",
          f"- games that were a pick in SOME version, and are final: "
          f"**{len(rows)}**"]
    if not rows:
        return "\n".join(md + ["", "No history recovered — is git history shallow?", ""])

    kept = [r for r in rows if r["survived"]]
    lost = [r for r in rows if not r["survived"]]
    md += [f"- survived to the final board (graded): **{len(kept)}**",
           f"- **dropped before the lock (never graded): {len(lost)}** "
           f"({len(lost)/len(rows):.0%})", "",
           "## Does dropping them flatter the record?", "",
           "| population | at the price first posted |", "|---|---|",
           f"| survived — what the ledger books | {_fmt(kept)} |",
           f"| **dropped — never graded** | **{_fmt(lost)}** |",
           f"| everything ever posted | {_fmt(rows)} |", ""]
    _, _, _, rk = _roi(kept, "first_odds", "won_first")
    _, _, _, ra = _roi(rows, "first_odds", "won_first")
    md += [f"- the recorded population returns **{rk:+.1%}**; everything that "
           f"actually appeared returns **{ra:+.1%}**",
           f"- **bias from silent dropping: {rk - ra:+.1f} points**", ""]
    md += ([f"The ledger is FLATTERED by {rk-ra:+.1f} points: the picks that "
            "quietly vanished did worse than the ones that stayed.", ""]
           if rk > ra else
           [f"The ledger UNDERSTATES the record by {ra-rk:+.1f} points: the "
            "dropped picks did better than the ones that stayed.", ""])

    # price drift on the survivors
    drift = [r for r in kept if isinstance(r.get("final_odds"), int)
             and r["final_odds"] != r["first_odds"]]
    md += ["## Price drift on the picks that survived", "",
           "_The ledger books the frozen closing price; the channel showed the "
           "earlier one. If they differ, the recorded ROI is not the ROI a "
           "reader would have got._", "",
           f"- survivors whose price changed: **{len(drift)}/{len(kept)}**",
           f"- graded at the FIRST posted price: {_fmt(kept)}",
           f"- graded at the FINAL recorded price: "
           f"{_fmt(kept, 'final_odds', 'won_final')}", ""]
    _, _, _, rf = _roi(kept, "final_odds", "won_final")
    md += [f"- difference: **{rk - rf:+.1f} points** in favour of the "
           f"{'posted' if rk > rf else 'recorded'} price", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "record_audit.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
