"""
Market-signal backtest: line movement + pre-game Polymarket order book, and the
"lights stay on in Vegas" alignment theory.

THE THEORY (user's): the house doesn't lose. When the SHARP money (handle) and
the PUBLIC money (tickets) are on the SAME side, and the Polymarket order book
confirms that side pre-game, while the book keeps the juice/exposure on the
opposite side - that consensus side should win. Our whole system to date does the
OPPOSITE (it fades the public), so this has never been tested.

The snapshots record exactly what's needed:
  public_check.money  = "with public" (handle and tickets AGREE - alignment),
                        "against public" (the classic sharp divergence),
                        "sources split" / "unknown"
  public_check.money_side / public_majority.team = which side each sits on
  pick_criteria.line_check = open/current/morning prices + window shifts
  pm_books_<date>.json = timestamped pre-game order book (bid/ask + sizes) for
                         the advantage side's token

Tested here:
  1. line movement (magnitude, direction, and which window it happened in)
  2. Polymarket order book (resting-size imbalance, pre-game drift, spread)
  3. THE ALIGNMENT THEORY, built up condition by condition so we can see which
     part (if any) carries the result
Every slice is reported bet AND fade, in-sample AND holdout.
Writes output/market_signals.md.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

from . import grade, mlb_api
from .main import _book_needs
from .signal_backtest import signals

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
HOLDOUT_FROM = "2026-07-23"
MAX_SPREAD = 0.15


def _pm_metrics(date: str) -> dict:
    """{game_pk: {drift, imbalance, last_mid}} from the pre-game order-book log."""
    p = OUTPUT_DIR / f"pm_books_{date}.json"
    try:
        book = json.loads(p.read_text())
    except (OSError, ValueError):
        return {}
    out = {}
    for pk_s, g in (book.get("games") or {}).items():
        reads = []
        for r in g.get("readings") or []:
            if r.get("empty"):
                continue
            b, a = r.get("bid"), r.get("ask")
            if isinstance(b, (int, float)) and isinstance(a, (int, float)) and a > b \
                    and (a - b) <= MAX_SPREAD:
                reads.append(r)
        if len(reads) < 2:
            continue
        reads.sort(key=lambda r: r.get("t", 0))
        first, last = reads[0], reads[-1]
        drift = (last["bid"] + last["ask"]) / 2 - (first["bid"] + first["ask"]) / 2
        bs, as_ = last.get("bid_sz") or 0, last.get("ask_sz") or 0
        imb = (bs - as_) / (bs + as_) if (bs + as_) > 0 else 0.0
        try:
            out[int(pk_s)] = {"drift": drift, "imbalance": imb,
                              "mid": (last["bid"] + last["ask"]) / 2}
        except ValueError:
            continue
    return out


def collect() -> list[dict]:
    recs = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        day = json.loads(Path(f).read_text())
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        pm = _pm_metrics(date)
        for g in day.get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            sig = signals(g)
            if not sig or sig.get("_ml") is None or " @ " not in g.get("matchup", ""):
                continue
            pc = g.get("pick_criteria") or {}
            away, home = g["matchup"].split(" @ ")
            adv = sig["_adv"]
            opp = home if adv == away else away
            price = {adv: sig["_ml"]}
            if pc.get("opponent_moneyline") is not None:
                price[opp] = int(pc["opponent_moneyline"])
            adv_side = "home" if adv == home else "away"

            chk = g.get("public_check") or {}
            maj = (g.get("public_majority") or {}).get("team")
            money_side = chk.get("money_side")          # "home"/"away" or None
            money_team = (home if money_side == "home"
                          else away if money_side == "away" else None)
            book = _book_needs(g)
            lc = pc.get("line_check") or {}
            recs.append({
                "date": date, "winner": res["winner"], "price": price,
                "adv": adv, "opp": opp, "adv_side": adv_side,
                "maj": maj,                              # public (ticket) side
                "money": chk.get("money"),               # with/against public
                "money_team": money_team,                # handle side
                "book_needs": (book or {}).get("bet"),   # side the book NEEDS
                "shift": lc.get("implied_shift"),        # + = toward adv side
                "timing": lc.get("timing"),
                "pm": pm.get(g.get("game_pk")),
                "holdout": date >= HOLDOUT_FROM,
            })
    return recs


def _bet(recs, team_of):
    """team_of(rec) -> team name to back (or None to skip)."""
    rows = []
    for r in recs:
        t = team_of(r)
        if not t or t not in r["price"]:
            continue
        rows.append({"won": r["winner"] == t, "odds": r["price"][t]})
    return rows


def _cell(rows):
    rows = [x for x in rows if x.get("odds") is not None]
    if not rows:
        return "—"
    w = sum(1 for r in rows if r["won"])
    u = sum(grade.american_profit(r["odds"]) if r["won"] else -1 for r in rows)
    return f"{w}-{len(rows)-w} ({w/len(rows):.0%}) · **{u/len(rows):+.1%}** (n={len(rows)})"


def _row(label, recs, team_of, opp_of=None):
    """label | BET all | BET holdout | FADE all | FADE holdout"""
    h = [r for r in recs if r["holdout"]]
    if opp_of is None:
        def opp_of(r):
            t = team_of(r)
            if not t:
                return None
            return r["opp"] if t == r["adv"] else r["adv"]
    return (f"| {label} | {_cell(_bet(recs, team_of))} | {_cell(_bet(h, team_of))} "
            f"| {_cell(_bet(recs, opp_of))} | {_cell(_bet(h, opp_of))} |")


def build() -> str:
    recs = collect()
    if not recs:
        return "# Market signals\n\n_No graded games._"
    H = ("| slice | BET (all) | BET (holdout) | FADE (all) | FADE (holdout) |\n"
         "|---|---|---|---|---|")
    hold = [r for r in recs if r["holdout"]]
    md = [f"# Market signals — {len(recs)} games ({len(hold)} holdout)", "",
          "_'BET' backs the named side; 'FADE' backs its opponent at the real "
          "price. Both pay vig, so a fade only wins if the straight side loses by "
          "more than the juice._", ""]

    adv_of = lambda r: r["adv"]

    # ---- 1. THE ALIGNMENT THEORY (the headline) ----
    md += ["## 1. The alignment theory — sharp money AND public on the same side", "",
           "_Backing the CONSENSUS side (the ticket majority, when the handle "
           "agrees with it), then layering the order-book and book-positioning "
           "conditions. This is the opposite of what the live system does._", "",
           H]
    aligned = [r for r in recs if r["money"] == "with public" and r["maj"]]
    md.append(_row("consensus side (handle agrees with tickets)", aligned,
                   lambda r: r["maj"]))
    # + the book is positioned AGAINST the consensus (it needs the other side)
    a_book = [r for r in aligned if r["book_needs"] and r["book_needs"] != r["maj"]]
    md.append(_row("  + book needs the OTHER side (vig opposite)", a_book,
                   lambda r: r["maj"]))
    # + Polymarket order book confirms the consensus side
    def pm_confirms(r):
        if not r["pm"]:
            return False
        toward_adv = r["pm"]["drift"] > 0 or r["pm"]["imbalance"] > 0.2
        return toward_adv if r["maj"] == r["adv"] else (not toward_adv)
    a_pm = [r for r in aligned if pm_confirms(r)]
    md.append(_row("  + PM order book confirms consensus", a_pm, lambda r: r["maj"]))
    a_all = [r for r in a_book if pm_confirms(r)]
    md.append(_row("  + BOTH (full theory)", a_all, lambda r: r["maj"]))
    md.append(_row("contrast: handle AGAINST public (classic sharp split)",
                   [r for r in recs if r["money"] == "against public" and r["money_team"]],
                   lambda r: r["money_team"]))
    md.append("")

    # ---- 2. line movement ----
    md += ["## 2. Line movement (shift is toward the advantage side)", "", H]
    for lo, hi, lab in ((0.02, 9, "moved ≥2% TOWARD our side"),
                        (0.005, 0.02, "drifted slightly toward us"),
                        (-0.005, 0.005, "flat"),
                        (-0.02, -0.005, "drifted slightly away"),
                        (-9, -0.02, "moved ≥2% AWAY from us")):
        sub = [r for r in recs if isinstance(r["shift"], (int, float))
               and lo <= r["shift"] < hi]
        md.append(_row(lab, sub, adv_of))
    for t, lab in (("early", "moved in the SHARP window"),
                   ("late", "moved in the PUBLIC window"),
                   ("both", "moved in both windows")):
        md.append(_row(lab, [r for r in recs if r["timing"] == t], adv_of))
    # reverse line movement: line moves toward the side the public is NOT on
    rlm = [r for r in recs if isinstance(r["shift"], (int, float))
           and r["shift"] >= 0.02 and r["maj"] and r["maj"] != r["adv"]]
    md.append(_row("REVERSE line move (toward us, public on them)", rlm, adv_of))
    md.append("")

    # ---- 3. Polymarket order book ----
    md += ["## 3. Polymarket pre-game order book", "",
           "_drift = our side's mid price move over the run-up; imbalance = "
           "resting bid vs ask size at the last reading (+ = money stacked to "
           "back our side)._", "", H]
    pmr = [r for r in recs if r["pm"]]
    for lo, hi, lab in ((0.03, 9, "drift ≥ +3¢ toward us"), (0.0, 0.03, "drift slightly up"),
                        (-9, 0.0, "drift down (money leaving us)")):
        md.append(_row(lab, [r for r in pmr if lo <= r["pm"]["drift"] < hi], adv_of))
    for lo, hi, lab in ((0.2, 9, "size imbalance toward us (>+0.2)"),
                        (-0.2, 0.2, "balanced book"),
                        (-9, -0.2, "size imbalance against us")):
        md.append(_row(lab, [r for r in pmr if lo <= r["pm"]["imbalance"] < hi], adv_of))
    md.append("")

    md.append("_Many slices are scanned here; treat a lone green cell as a "
              "hypothesis. The holdout columns are the only out-of-sample evidence._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "market_signals.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
