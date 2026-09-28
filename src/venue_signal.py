"""
Two real-money venues, one game: is there anything in their disagreement?

THREE QUESTIONS, IN ORDER OF HOW MUCH POWER THEY HAVE

1. OUR OWN PLAYS, WON vs LOST. What did the winners look like pre-game that
   the losers did not - line movement, ticket share, handle share, order-book
   drift and size lean? This is what was asked for first. It is also the
   weakest test here: ~150 settled bets split into two groups, so a 5-point
   difference in any column is noise. Reported because it was asked for, with
   its interval, and not as a basis for changing anything.

2. CROSS-VENUE PRICE GAP, ALL GAMES. Polymarket and Kalshi both trade these
   games with real money, and both are logged on the SAME side (the board
   tracks the advantage team's token and ticker). 794 games carry both since
   2026-07-31. That is five times the sample of question 1 and it has never
   been looked at. When the two venues price a side differently, is either one
   right?

3. DOES THE GAP PREDICT THE BOOK? The tradeable version. If the venues
   disagree at the point we bet, does the sportsbook line subsequently move
   toward one of them? That does not need a game outcome at all, so it has the
   most power of the three.

THE TRAP THIS FILE IS BUILT AROUND
Both venues keep logging THROUGH the game and after it settles - a late
Polymarket reading of 0.999, a Kalshi pair of 0.0/1.0, are a finished game,
not a market read. Using them would "predict" outcomes perfectly and mean
nothing. Every reading here is cut at first pitch minus LOCK_LEAD, the same
moment the board freezes a pick, and the report states how many readings
survive that cut so the guard is visible rather than promised.

Writes output/venue_signal.md.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
import random
import statistics as st
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import _implied

log = logging.getLogger("venue_signal")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
LOCK_LEAD = dt.timedelta(minutes=15)
MIN_READS = 2
MAX_SPREAD = 0.15
TRIALS = 3000


def _mid(r: dict) -> float | None:
    b, a = r.get("bid"), r.get("ask")
    if not (isinstance(b, (int, float)) and isinstance(a, (int, float))):
        return None
    if a <= b or (a - b) > MAX_SPREAD:
        return None
    return (a + b) / 2


def _pregame(readings: list, cutoff_ts: float) -> list:
    """Readings strictly before the freeze. Anything later is the game itself."""
    out = []
    for r in readings or []:
        if r.get("empty"):
            continue
        t = r.get("t")
        if not isinstance(t, (int, float)) or t > cutoff_ts:
            continue
        if _mid(r) is None:
            continue
        out.append(r)
    out.sort(key=lambda r: r["t"])
    return out


def _venue(readings: list) -> dict | None:
    if len(readings) < MIN_READS:
        return None
    first, last = readings[0], readings[-1]
    bs, as_ = last.get("bid_sz") or 0, last.get("ask_sz") or 0
    return {"close": _mid(last), "drift": _mid(last) - _mid(first),
            "imbalance": ((bs - as_) / (bs + as_)) if (bs + as_) else 0.0,
            "n": len(readings)}


def collect() -> tuple[list[dict], dict]:
    """One row per game that has both venues logged pre-game, joined to the
    board (for prices and our pick) and to the result."""
    rows, cut_stats = [], {"kept": 0, "dropped": 0}
    for f in sorted(glob.glob(str(OUTPUT_DIR / "pm_books_2026-*.json"))):
        date = Path(f).stem.split("pm_books_")[1]
        try:
            day = json.loads(Path(f).read_text())
            board = json.loads((OUTPUT_DIR / f"picks_{date}.json").read_text())
            results = mlb_api.results_for(date)
        except Exception:
            continue
        bg = {g.get("game_pk"): g for g in board.get("games", [])}
        for pk_s, g in (day.get("games") or {}).items():
            try:
                pk = int(pk_s)
            except (TypeError, ValueError):
                continue
            bgame, res = bg.get(pk), results.get(pk)
            if not bgame or not res or not res.get("final") or not res.get("winner"):
                continue
            start = bgame.get("game_datetime") or g.get("game_datetime")
            if not start:
                continue
            try:
                cutoff = (dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
                          - LOCK_LEAD).timestamp()
            except ValueError:
                continue
            allp = [r for r in (g.get("readings") or []) if not r.get("empty")]
            allk = [r for r in (g.get("k_readings") or []) if not r.get("empty")]
            p = _pregame(allp, cutoff)
            k = _pregame(allk, cutoff)
            cut_stats["kept"] += len(p) + len(k)
            cut_stats["dropped"] += (len(allp) + len(allk)) - (len(p) + len(k))
            pv, kv = _venue(p), _venue(k)

            pc = bgame.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            side = g.get("side")          # the team both venues are logged on
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            tot = _implied(a_ml) + _implied(o_ml)
            chk = bgame.get("public_check") or {}
            rows.append({
                "date": date, "game_pk": pk, "side": side, "adv": adv,
                "adv_odds": a_ml, "opp_odds": o_ml,
                "adv_won": res["winner"] == adv,
                "p_adv": (_implied(a_ml) / tot) if tot > 0 else 0.5,
                "pm": pv, "kalshi": kv,
                "shift": (pc.get("line_check") or {}).get("implied_shift"),
                "money": chk.get("money"), "money_pct": chk.get("money_pct"),
                "play": pc.get("play"), "bet_team": pc.get("bet_team"),
                "bet_odds": pc.get("bet_moneyline"),
                "source": pc.get("source") or "rule",
            })
    return rows, cut_stats


def _roi(bets) -> float:
    if not bets:
        return 0.0
    return sum(grade.american_profit(o) if w else -1 for o, w in bets) / len(bets)


def _fmt(bets) -> str:
    if not bets:
        return "—"
    w = sum(1 for _, won in bets if won)
    return f"{w}-{len(bets)-w} · **{_roi(bets):+.1%}** (n={len(bets)})"


def _mean(vals) -> str:
    vals = [v for v in vals if isinstance(v, (int, float))]
    return f"{st.mean(vals):+.3f}" if vals else "—"


def build() -> str:
    rows, cut = collect()
    md = ["# Line movement, tickets, handle and the two venues", "",
          "_Every order-book reading is cut at first pitch minus 15 minutes — "
          "the same moment the board freezes a pick. Both venues keep logging "
          "through the game and after settlement, and a Polymarket bid of "
          "0.999 or a Kalshi 0.0/1.0 pair is a finished game, not a market "
          "read. Using them would predict outcomes perfectly and mean "
          "nothing._", "",
          f"- readings kept: **{cut['kept']:,}** · discarded as at-or-after "
          f"the freeze: **{cut['dropped']:,}**",
          f"- games with a result and a board row: **{len(rows)}**",
          f"- of those, both venues readable pre-game: "
          f"**{sum(1 for r in rows if r['pm'] and r['kalshi'])}**", ""]
    if len(rows) < 100:
        return "\n".join(md + ["Not enough joined games.", ""])

    # --- 1. our own plays, won vs lost -----------------------------------
    plays = [r for r in rows if r["play"] == "pick" and r["bet_team"]
             and isinstance(r["bet_odds"], int)]
    for r in plays:
        r["won"] = (r["bet_team"] == r["adv"]) == r["adv_won"]
        # sign everything toward the side we actually backed
        flip = 1 if r["bet_team"] == r["adv"] else -1
        r["toward_bet"] = (r["shift"] * flip) if isinstance(r["shift"], (int, float)) else None
        r["pm_drift"] = (r["pm"]["drift"] * flip) if r["pm"] else None
        r["pm_imb"] = (r["pm"]["imbalance"] * flip) if r["pm"] else None
        r["k_drift"] = (r["kalshi"]["drift"] * flip) if r["kalshi"] else None
        r["k_imb"] = (r["kalshi"]["imbalance"] * flip) if r["kalshi"] else None
    won = [r for r in plays if r["won"]]
    lost = [r for r in plays if not r["won"]]
    md += ["## 1. Our settled plays: winners against losers", "",
           f"_{len(won)} won, {len(lost)} lost. Each column is signed toward "
           "the side we backed, so a positive line figure means the price "
           "moved our way. **This is the weakest test here** — two groups of "
           "~70 make a 5-point difference indistinguishable from noise._", "",
           "| pre-game measure | winners | losers |", "|---|---|---|"]
    for label, key in (("line move toward our side", "toward_bet"),
                       ("Polymarket drift", "pm_drift"),
                       ("Polymarket size lean", "pm_imb"),
                       ("Kalshi drift", "k_drift"),
                       ("Kalshi size lean", "k_imb"),
                       ("handle % on our side", "money_pct")):
        md.append(f"| {label} | {_mean([r.get(key) for r in won])} | "
                  f"{_mean([r.get(key) for r in lost])} |")
    md.append("")

    # --- 2. cross-venue gap, all games ------------------------------------
    both = [r for r in rows if r["pm"] and r["kalshi"]]
    for r in both:
        r["gap"] = r["pm"]["close"] - r["kalshi"]["close"]
    md += ["## 2. When the two venues disagree on price", "",
           "_Both are logged on the same side, so `gap` is Polymarket minus "
           "Kalshi on that side at the freeze. Backing that side at the "
           "sportsbook price._", "",
           f"- games: **{len(both)}** · mean gap "
           f"**{st.mean([r['gap'] for r in both]):+.4f}** · "
           f"median **{st.median([r['gap'] for r in both]):+.4f}**", "",
           "| Polymarket vs Kalshi | backing the tracked side |", "|---|---|"]
    buckets = [("PM richer by >3c", lambda g: g > 0.03),
               ("PM richer 1–3c", lambda g: 0.01 < g <= 0.03),
               ("agree within 1c", lambda g: abs(g) <= 0.01),
               ("Kalshi richer 1–3c", lambda g: -0.03 <= g < -0.01),
               ("Kalshi richer by >3c", lambda g: g < -0.03)]
    cells = []
    for label, test in buckets:
        sub = [r for r in both if test(r["gap"])]
        bets = [(r["adv_odds"] if r["side"] == r["adv"] else r["opp_odds"],
                 r["adv_won"] if r["side"] == r["adv"] else not r["adv_won"])
                for r in sub]
        cells.append((label, sub, bets))
        md.append(f"| {label} | {_fmt(bets)} |")
    md.append("")

    live = [(l, s, b) for l, s, b in cells if len(b) >= 40]
    if live:
        bl, bs, bb = max(live, key=lambda c: _roi(c[2]))
        rng = random.Random(9)
        null = []
        plan = [[(grade.american_profit(o), p) for o, p in
                 [((r["adv_odds"] if r["side"] == r["adv"] else r["opp_odds"]),
                   (r["p_adv"] if r["side"] == r["adv"] else 1 - r["p_adv"]))
                  for r in s]] for _, s, b in live]
        for _ in range(TRIALS):
            null.append(max(sum(w if rng.random() < p else -1 for w, p in pl) / len(pl)
                            for pl in plan) * 100)
        obs = _roi(bb) * 100
        pv = (sum(1 for x in null if x >= obs) + 1) / (len(null) + 1)
        md += ["### Does the best bucket beat the search?", "",
               f"- best: **{bl}** at {obs:+.1f}%",
               f"- biggest a price-redraw manufactures across {len(live)} "
               f"buckets: median **{st.median(null):+.1f}%**, 95th pct "
               f"**{sorted(null)[int(.95*len(null))]:+.1f}%**",
               f"- **corrected p = {pv:.3f}**", "",
               ("**Clears.**" if pv < 0.05 else "**Does not clear.**"), ""]

    # --- 3. does the gap predict the BOOK line? ---------------------------
    md += ["## 3. Does the gap predict where the sportsbook line goes?", "",
           "_No game outcome needed, so this has the most power of the three. "
           "If the venues disagree at the freeze and the book has already "
           "moved toward one of them, the gap is information the book is "
           "still absorbing._", ""]
    pairs = [(r["gap"], r["shift"] if r["side"] == r["adv"] else -(r["shift"] or 0))
             for r in both if isinstance(r["shift"], (int, float))]
    if len(pairs) >= 50:
        xs = [a for a, _ in pairs]
        ys = [b for _, b in pairs]
        corr = st.correlation(xs, ys) if len(set(xs)) > 1 and len(set(ys)) > 1 else 0.0
        md += [f"- games: **{len(pairs)}**",
               f"- correlation between the venue gap and the book's move: "
               f"**r = {corr:+.3f}**", "",
               ("_Positive and material: the book moves the way the venue gap "
                "points, so the gap carries information the book has not "
                "priced._" if corr > 0.15 else
                "_Near zero. The venue gap and the book's movement are "
                "unrelated, so there is nothing here to trade on._"), ""]
    else:
        md += ["_Too few games with both a gap and a line move._", ""]

    md += ["## How to read this", "",
           "- section 1 answers what was asked and is the least reliable; "
           "section 3 is the most powered and needs no outcomes",
           "- a bucket that clears the permutation still needs split-half "
           "before it is worth anything — that is the test that killed every "
           "other candidate this season",
           "- nothing here changes the board.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "venue_signal.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
