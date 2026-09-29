"""
Backfill pre-game Polymarket price DRIFT for historical slates, to enlarge the
sample behind the consensus rule.

THE PROBLEM
The consensus rule (src/consensus.py) tested at n=68 all-time / 28 holdout,
because it needs order-book readings and the live logger (pm_books) only started
2026-07-16. The consensus half of the rule has 36 days of data; the order-book
half has 13. The order book is the binding constraint.

WHAT CAN BE RECOVERED
Resting-size imbalance is a snapshot of depth and is gone forever once the market
moves. But PRICE history is durable: the CLOB exposes /prices-history per token,
so the DRIFT component - did money move onto this side during the run-up - can be
reconstructed for any game whose market we can still resolve. That roughly
triples the sample for a drift-only version of the rule.

Tokens come from two places: the stored pm_books logs (for days it ran) and the
gamma API's CLOSED market index (for older days). Writes one small file per day,
output/pm_drift_<date>.json: {game_pk: {abbr, drift, points}}, where `abbr` names
the team the drift refers to.

Fails soft everywhere; re-running skips days already backfilled. Runs on Actions.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
import time
from pathlib import Path

import requests

from . import pm_books
from .analysis import _canon_abbr

log = logging.getLogger("pm_backfill")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
GAMMA = "https://gamma-api.polymarket.com/events"
HISTORY = "https://clob.polymarket.com/prices-history"
TIMEOUT = 20
PREGAME_HOURS = 8          # look back this far before first pitch
MIN_POINTS = 3             # need a few readings to call it a drift


def path_for(date: str) -> Path:
    return OUTPUT_DIR / f"pm_drift_{date}.json"


def _get(url: str, **params):
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT,
                         headers={"User-Agent": "mlb-edge-finder (personal research)"})
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        log.warning("fetch failed (%s): %s", url.rsplit("/", 1)[-1], exc)
        return None


def closed_market_index() -> dict:
    """{(abbr, abbr): {abbr: token}} for CLOSED MLB markets (historical games)."""
    index: dict = {}
    offset = 0
    while True:
        batch = _get(GAMMA, tag_slug="mlb", closed="true", limit=100, offset=offset)
        if not isinstance(batch, list) or not batch:
            break
        for ev in batch:
            for m in ev.get("markets") or []:
                try:
                    outcomes, tokens = m.get("outcomes"), m.get("clobTokenIds")
                    if isinstance(outcomes, str):
                        outcomes = json.loads(outcomes)
                    if isinstance(tokens, str):
                        tokens = json.loads(tokens)
                    if not outcomes or not tokens or len(outcomes) != 2 or len(tokens) != 2:
                        continue
                    a1 = pm_books._name_abbr(str(outcomes[0]))
                    a2 = pm_books._name_abbr(str(outcomes[1]))
                    if not a1 or not a2 or a1 == a2:
                        continue
                    tok = {a1: tokens[0], a2: tokens[1]}
                    index.setdefault((a1, a2), tok)
                    index.setdefault((a2, a1), tok)
                except Exception:
                    continue
        offset += 100
        if len(batch) < 100:
            break
        time.sleep(0.2)
    log.info("gamma closed index: %d keys", len(index))
    return index


def _stored_tokens(date: str) -> dict:
    """{game_pk: {"token": id, "abbr": side_abbr}} from that day's pm_books log."""
    try:
        day = pm_books.load_day(date) or {}
    except Exception:
        return {}
    out = {}
    for pk_s, g in (day.get("games") or {}).items():
        tok, side = g.get("token"), g.get("side")
        if not tok or not side:
            continue
        try:
            out[int(pk_s)] = {"token": tok, "abbr": _canon_abbr(side) or side}
        except (TypeError, ValueError):
            continue
    return out


def _drift(token: str, start_iso: str) -> tuple[float, int] | None:
    """(price drift over the pre-game window, #points) for a token, or None."""
    try:
        start = dt.datetime.fromisoformat(str(start_iso).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    end_ts = int(start.timestamp())
    data = _get(HISTORY, market=token, startTs=end_ts - PREGAME_HOURS * 3600,
                endTs=end_ts, fidelity=10)
    pts = (data or {}).get("history") or []
    pts = [p for p in pts if isinstance(p.get("p"), (int, float))]
    if len(pts) < MIN_POINTS:
        return None
    pts.sort(key=lambda p: p.get("t", 0))
    return round(float(pts[-1]["p"]) - float(pts[0]["p"]), 4), len(pts)


def backfill_date(date: str, closed_idx: dict, force: bool = False) -> int:
    if path_for(date).exists() and not force:
        return 0
    picks_path = OUTPUT_DIR / f"picks_{date}.json"
    if not picks_path.exists():
        return 0
    day = json.loads(picks_path.read_text())
    stored = _stored_tokens(date)
    out: dict = {}
    for g in day.get("games", []):
        pk = g.get("game_pk")
        start = g.get("game_datetime")
        if pk is None or not start:
            continue
        tok = stored.get(pk)
        if not tok:                       # fall back to the closed-market index
            aa = _canon_abbr(g.get("away_abbr") or "")
            ha = _canon_abbr(g.get("home_abbr") or "")
            pair = closed_idx.get((aa, ha))
            if not pair or ha not in pair:
                continue
            tok = {"token": pair[ha], "abbr": ha}
        d = _drift(tok["token"], start)
        if not d:
            continue
        out[str(pk)] = {"abbr": tok["abbr"], "drift": d[0], "points": d[1]}
        time.sleep(0.15)
    if out:
        OUTPUT_DIR.mkdir(exist_ok=True)
        path_for(date).write_text(json.dumps(out, indent=1))
        log.info("%s: backfilled drift for %d games", date, len(out))
    return len(out)


def load(date: str) -> dict:
    """{game_pk:int -> {abbr, drift, points}} for a date, or {}."""
    try:
        raw = json.loads(path_for(date).read_text())
    except (OSError, ValueError):
        return {}
    out = {}
    for k, v in raw.items():
        try:
            out[int(k)] = v
        except (TypeError, ValueError):
            continue
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    idx = closed_market_index()
    total = 0
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        total += backfill_date(date, idx)
    log.info("backfilled %d game-drifts in total", total)


if __name__ == "__main__":
    main()
