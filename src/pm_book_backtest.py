"""
Polymarket ORDER-BOOK backtest: does the run-up money on our side - resting size
imbalance and price drift, NOT the mid quote - predict a win, alone or paired
with a signal (line, margin, ...)?

For each board PLAY we have a dense pre-game book log (pm_books_<date>.json:
readings of {t, bid, bid_sz, ask, ask_sz} for our side's token). We derive two
"money on our side" reads over the pre-game window:
  drift     = mid(last) - mid(first)          our side's price move in the run-up
                                              (+ = money flowed onto our side)
  imbalance = (bid_sz - ask_sz)/(bid_sz+ask_sz) at the last reading
                                              (+ = more resting money to BACK us)
then grade the pick vs the result and cross each read with the frozen signals.

Small by nature (order-book logging is days old) - every row is exploratory;
read the n=. Runs on GitHub Actions (MLB API firewalled locally). Writes
output/pm_book_backtest.md.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

from . import grade, mlb_api
from .signal_backtest import signals

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MAX_SPREAD = 0.15   # skip games whose book never tightened (no real two-sided market)


def _window_reads(g: dict) -> list[dict]:
    """Non-empty readings with a real (tight) two-sided book, in time order."""
    out = []
    for r in g.get("readings") or []:
        if r.get("empty"):
            continue
        b, a = r.get("bid"), r.get("ask")
        if isinstance(b, (int, float)) and isinstance(a, (int, float)) and a > b:
            out.append(r)
    out.sort(key=lambda r: r.get("t", 0))
    return out


def _reads_metrics(reads: list[dict]) -> dict | None:
    """drift (mid move over the run-up) + imbalance (last resting-size lean)."""
    tight = [r for r in reads if (r["ask"] - r["bid"]) <= MAX_SPREAD]
    if len(tight) < 2:
        return None
    first, last = tight[0], tight[-1]
    drift = (last["bid"] + last["ask"]) / 2 - (first["bid"] + first["ask"]) / 2
    bs, as_ = last.get("bid_sz") or 0, last.get("ask_sz") or 0
    imb = (bs - as_) / (bs + as_) if (bs + as_) > 0 else 0.0
    return {"drift": round(drift, 4), "imbalance": round(imb, 3)}


def _units(rows: list[dict]) -> tuple[int, int, float]:
    w = sum(1 for r in rows if r["won"])
    u = sum(grade.american_profit(r["odds"]) if r["won"] else -1 for r in rows)
    return w, len(rows) - w, round(u, 2)


def _roi(label: str, rows: list[dict]) -> str:
    if not rows:
        return f"| {label} | 0 | — | — |"
    w, l, u = _units(rows)
    return f"| {label} (n={len(rows)}) | {w}-{l} ({w / len(rows):.0%}) | {u:+.2f}u | {u / len(rows):+.1%} |"


def build() -> str:
    plays: list[dict] = []
    tracked = graded = 0
    for f in sorted(glob.glob(str(OUTPUT_DIR / "pm_books_*.json"))):
        date = Path(f).stem.split("pm_books_")[1]
        book = json.loads(Path(f).read_text())
        picks_path = OUTPUT_DIR / f"picks_{date}.json"
        if not picks_path.exists():
            continue
        picks = {g.get("game_pk"): g for g in json.loads(picks_path.read_text()).get("games", [])}
        try:
            results = mlb_api.results_for(date)
        except Exception:
            results = {}
        for pk_s, g in (book.get("games") or {}).items():
            if not g.get("play"):
                continue
            tracked += 1
            pk = int(pk_s)
            pg, res = picks.get(pk), results.get(pk)
            if not pg or not res or not res.get("final") or not res.get("winner"):
                continue
            sig = signals(pg)
            m = _reads_metrics(_window_reads(g))
            if not sig or not m:
                continue
            ml = sig["_ml"]
            if ml is None:
                continue
            graded += 1
            plays.append({"sig": sig, "won": res["winner"] == sig["_adv"], "odds": ml,
                          "drift": m["drift"], "imbalance": m["imbalance"]})

    md = [f"# Polymarket order-book backtest — {graded} graded of {tracked} tracked plays", "",
          "_Order-book money on our side (resting-size imbalance + pre-game price "
          "drift), NOT the mid quote. Bet our side at the book moneyline, $1/pick. "
          "Order-book logging is days old, so every row is small — read the n=._", ""]

    def bet(sub):
        return [{"won": p["won"], "odds": p["odds"]} for p in sub]

    # 1) money FLOW: did our side's PM price drift up in the run-up?
    md += ["## Order-book price DRIFT toward our side (money flowing in)", "",
           "| slice | record | units | ROI/bet |", "|---|---|---|---|",
           _roi("drift up (>0) — money came to us", bet([p for p in plays if p["drift"] > 0])),
           _roi("  ...meaningful (drift ≥ +0.03)", bet([p for p in plays if p["drift"] >= 0.03])),
           _roi("drift down (<0) — money left us", bet([p for p in plays if p["drift"] < 0])), ""]

    # 2) resting SIZE imbalance: is more money stacked to back our side?
    md += ["## Order-book SIZE imbalance (more resting money on our side)", "",
           "| slice | record | units | ROI/bet |", "|---|---|---|---|",
           _roi("more money on us (imb > +0.2)", bet([p for p in plays if p["imbalance"] > 0.2])),
           _roi("balanced (±0.2)", bet([p for p in plays if abs(p["imbalance"]) <= 0.2])),
           _roi("more money against us (imb < -0.2)", bet([p for p in plays if p["imbalance"] < -0.2])), ""]

    # 3) the question: order-book money PAIRED with a signal. "book money on us" =
    # drift up OR a positive size imbalance.
    book_on_us = [p for p in plays if p["drift"] > 0 or p["imbalance"] > 0.2]
    md += ["## Order-book money on us + each signal (does the pair net a win?)", "",
           "_'book money on us' = price drifted up OR resting size leans our way._", "",
           "| pair | record | units | ROI/bet |", "|---|---|---|---|",
           _roi("book money on us (alone)", bet(book_on_us))]
    for s in ("margin", "line", "consistency", "favorite", "bvp", "form"):
        md.append(_roi(f"  + {s}", bet([p for p in book_on_us if p["sig"].get(s) is True])))
    md.append("")

    md.append("_Exploratory: pre-game order book vs the graded result; $1/bet at the "
              "book moneyline. Samples are small until the book log accumulates._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "pm_book_backtest.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
