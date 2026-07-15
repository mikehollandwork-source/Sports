"""
Polymarket TRADE-OUT backtest: enter each graded pick on PM at lock time, then
test "lock the profit at +X cents" exits against holding to settlement.

For every graded snapshot pick we find its Polymarket market (closed MLB events
via the gamma API, matched by team names + game date), pull the market's LIVE
price history (CLOB prices-history, public), enter at the first price at/after
lock (15 min before first pitch), and simulate exit thresholds: if the price
ever reaches entry + X, sell there (profit X/entry per $1 staked, guaranteed);
otherwise the position settles like a normal bet (win: 1/entry - 1, loss: -1).

Endpoints are UNVERIFIED until the first Actions run and everything fails soft,
same as covers/ESPN/pinnacle. Writes output/pm_tradeout.md (+ .json).

Honest caveats baked into the report: history points are coarse (fidelity ~10
min), fills assume the printed price with no fee/spread/depth, and the sample
is only as big as the snapshot archive.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
import statistics as st
import time
from pathlib import Path

import requests

from . import grade, mlb_api
from .public_sources import _name_abbr

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pm_tradeout")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
GAMMA = "https://gamma-api.polymarket.com/events"
HISTORY = "https://clob.polymarket.com/prices-history"
THRESHOLDS = (0.03, 0.05, 0.08, 0.10, 0.15, 0.20)
TIMEOUT = 20


def _get(url: str, **params):
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT,
                         headers={"User-Agent": "mlb-edge-finder (personal research)"})
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # network/HTTP/JSON - degrade gracefully
        log.warning("fetch failed (%s %s): %s", url, params, exc)
        return None


def closed_mlb_markets(date_min: str, date_max: str) -> dict:
    """{(away_abbr, home_abbr, 'YYYY-MM-DD'): {abbr: token_id}} for closed MLB
    game markets in the window, from the gamma events API."""
    index: dict = {}
    offset = 0
    while True:
        batch = _get(GAMMA, tag_slug="mlb", closed="true", limit=100, offset=offset,
                     start_date_min=date_min, start_date_max=date_max)
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
                    a1, a2 = _name_abbr(str(outcomes[0])), _name_abbr(str(outcomes[1]))
                    if not a1 or not a2 or a1 == a2:
                        continue
                    start = m.get("gameStartTime") or ev.get("startDate") or ""
                    d = _et_date(start)
                    if not d:
                        continue
                    # gamma order isn't guaranteed away-first: key both orderings,
                    # the token map is by abbr so the order never matters.
                    tok = {a1: tokens[0], a2: tokens[1]}
                    index[(a1, a2, d)] = tok
                    index[(a2, a1, d)] = tok
                except Exception:
                    continue
        offset += 100
        if len(batch) < 100:
            break
        time.sleep(0.2)
    log.info("gamma: indexed %d market keys", len(index))
    return index


def _implied_prob(ml) -> float:
    ml = int(ml)
    return 100.0 / (ml + 100) if ml > 0 else -ml / (-ml + 100.0)


def _et_date(iso: str) -> str | None:
    try:
        t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        import zoneinfo
        return t.astimezone(zoneinfo.ZoneInfo("America/New_York")).date().isoformat()
    except Exception:
        return None


def price_history(token_id: str, start_ts: int, end_ts: int) -> list[tuple[int, float]]:
    data = _get(HISTORY, market=token_id, startTs=start_ts, endTs=end_ts, fidelity=10)
    out = []
    for h in (data or {}).get("history") or []:
        try:
            out.append((int(h["t"]), float(h["p"])))
        except Exception:
            continue
    return out


def simulate(points: list[tuple[int, float]], entry_ts: int, won: bool) -> dict | None:
    """Enter at the first print at/after entry_ts; record entry, the max price
    seen afterward (the best exit that existed), and the settle outcome."""
    after = [(t, p) for t, p in points if t >= entry_ts]
    if not after:
        return None
    entry = after[0][1]
    if not 0.02 <= entry <= 0.98:
        return None
    return {"entry": entry, "max": max(p for _, p in after), "won": won}


def settle_profit(entry: float, won: bool) -> float:
    """Hold to settlement, $1 staked: win pays 1/entry - 1, loss loses the $1."""
    return (1.0 / entry - 1.0) if won else -1.0


def hedged_profit(row: dict, x: float) -> float:
    """Exit at entry+x if the price ever got there (guaranteed x/entry per $1
    staked), else the position settles normally."""
    if row["max"] >= row["entry"] + x:
        return x / row["entry"]
    return settle_profit(row["entry"], row["won"])


def collect() -> list[dict]:
    """One row per graded snapshot pick that matched a PM market with history:
    {date, matchup, play (bool), entry, max, won}."""
    files = sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json")))
    if not files:
        return []
    dates = [Path(f).stem.split("picks_")[1] for f in files]
    index = closed_mlb_markets(dates[0], dates[-1])
    rows, seen = [], set()
    for f, date in zip(files, dates):
        day = json.loads(Path(f).read_text())
        try:
            results = mlb_api.results_for(date)
        except Exception:
            results = {}
        for g in day.get("games", []):
            pk = g.get("game_pk")
            if (date, pk) in seen:
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            res = results.get(pk)
            if not adv or not res or not res.get("final") or not res.get("winner"):
                continue
            if " @ " not in g.get("matchup", ""):
                continue
            away, home = g["matchup"].split(" @ ")
            a_ab, h_ab = _name_abbr(away), _name_abbr(home)
            tok = index.get((a_ab, h_ab, date)) if a_ab and h_ab else None
            adv_ab = h_ab if adv == home else a_ab
            opp_ab = a_ab if adv == home else h_ab
            if not tok or adv_ab not in tok or opp_ab not in tok:
                continue
            try:
                start = dt.datetime.fromisoformat(
                    str(g.get("game_datetime", "")).replace("Z", "+00:00"))
            except Exception:
                continue
            entry_ts = int(start.timestamp()) - 15 * 60
            won = res["winner"] == adv
            # Fetch BOTH sides' histories and pick our side by PRICE, validated
            # against the book moneyline frozen at the same lock moment - the
            # first pass trusted gamma's outcome->token pairing by name and a
            # chunk of games came back side-inverted (audit: cheap entries won
            # 56-100%, dear entries 33-36% - a mirror around 50c).
            pts_name = price_history(tok[adv_ab], entry_ts - 3600, entry_ts + 8 * 3600)
            time.sleep(0.25)
            pts_flip = price_history(tok[opp_ab], entry_ts - 3600, entry_ts + 8 * 3600)
            time.sleep(0.25)
            sim_name = simulate(pts_name, entry_ts, won)
            sim_flip = simulate(pts_flip, entry_ts, won)
            ml = pc.get("advantage_moneyline")
            ref = _implied_prob(ml) if ml is not None else None
            sim = sim_name
            if ref is not None and sim_name and sim_flip:
                if abs(sim_flip["entry"] - ref) + 0.03 < abs(sim_name["entry"] - ref):
                    sim = sim_flip     # the "wrong" token matches the lock price
            elif sim_name is None:
                sim = sim_flip if (sim_flip and ref is not None
                                   and abs(sim_flip["entry"] - ref) <= 0.10) else None
            if not sim:
                continue
            seen.add((date, pk))
            rows.append({"date": date, "matchup": g["matchup"], "ref": ref,
                         "flipped": sim is sim_flip,
                         "play": grade._play(g) == "pick", **sim})
    log.info("collected %d simulated positions (%d plays)",
             len(rows), sum(1 for r in rows if r["play"]))
    return rows


def report(rows: list[dict]) -> str:
    md = [f"# Polymarket trade-out backtest — {len(rows)} positions "
          f"({sum(1 for r in rows if r['play'])} were board PLAYS)", "",
          "_Enter our side at lock (15 min pre-pitch) at the live PM price; "
          "'lock at +X¢' sells the moment the price reaches entry+X (profit "
          "guaranteed regardless of the final score); otherwise the bet settles "
          "normally. $1 staked per position. Prices are ~10-min prints with no "
          "fee/spread/depth modeling - a stated best case._", ""]
    refd = [r for r in rows if r.get("ref") is not None]
    if refd:
        gaps = [abs(r["entry"] - r["ref"]) for r in refd]
        md += [f"_Side-mapping audit: {sum(1 for r in rows if r.get('flipped'))} of "
               f"{len(rows)} tokens flipped after price-validation vs the lock-time "
               f"book price; median |entry - book| now {st.median(gaps) * 100:.1f} pts._", ""]
    for label, pool in (("ALL stat-advantage sides", rows),
                        ("BOARD PLAYS only", [r for r in rows if r["play"]])):
        md += [f"## {label} (n={len(pool)})", ""]
        if not pool:
            md += ["_no positions_", ""]
            continue
        hold = sum(settle_profit(r["entry"], r["won"]) for r in pool)
        w = sum(1 for r in pool if r["won"])
        md += ["| strategy | locked | record | units | ROI/bet |", "|---|---|---|---|---|",
               f"| hold to settlement | — | {w}-{len(pool) - w} | {hold:+.2f}u "
               f"| {hold / len(pool):+.1%} |"]
        for x in THRESHOLDS:
            hits = sum(1 for r in pool if r["max"] >= r["entry"] + x)
            u = sum(hedged_profit(r, x) for r in pool)
            md.append(f"| lock at +{int(x * 100)}¢ | {hits}/{len(pool)} "
                      f"({hits / len(pool):.0%}) | — | {u:+.2f}u | {u / len(pool):+.1%} |")
        ups = [r["max"] - r["entry"] for r in pool]
        md += ["", f"_Best exit that ever existed (max price minus entry): median "
                   f"+{st.median(ups) * 100:.0f}¢, mean +{st.mean(ups) * 100:.0f}¢. A "
                   f"winning position almost always passes through a lockable price on "
                   f"its way to $1 - the question the table answers is whether banking "
                   f"it early beats letting winners settle._", ""]
    return "\n".join(md)


def main() -> None:
    rows = collect()
    md = report(rows)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "pm_tradeout.md").write_text(md)
    (OUTPUT_DIR / "pm_tradeout.json").write_text(json.dumps(rows, indent=1))
    print(md)


if __name__ == "__main__":
    main()
