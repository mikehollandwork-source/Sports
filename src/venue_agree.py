"""
Do Kalshi and Polymarket agree on where the money is - and does line movement
pay when they DON'T?

THE IDEA
Two independent real-money venues both show, pre-game, which side has more money
behind it. When they agree, that is a strong money read. When they disagree, one
of them is wrong - and the sportsbook line moving one way or the other may say
which. That disagreement is the interesting case: the money read is ambiguous
exactly where the line still has something to tell us.

MONEY LEAN, per venue, at the last clean pre-game reading
Both logs store the ADVANTAGE side's contract, so in both cases:
    bid_sz = money queued to back our side, ask_sz = money backing the other
    lean   = (bid_sz - ask_sz) / (bid_sz + ask_sz)
A venue "leans to" the advantage side when lean > MIN_LEAN, to the opponent when
lean < -MIN_LEAN, and is neutral in between.

WHAT IS TESTED
  1. coverage - how many games actually have BOTH venues (this gates everything)
  2. AGREE: both venues lean the same way -> back that side, and fade it
  3. DISAGREE: the venues split -> back the side the LINE moved toward, back the
     side each venue favours, and fade each, to see if the line breaks the tie
  4. a neutral/agree/disagree breakdown so the split sizes are visible

Kalshi logging started 2026-07-31, so early runs will report insufficient data
rather than a spurious answer. Writes output/venue_agree.md.
"""

from __future__ import annotations

import glob
import json
import statistics as st
from pathlib import Path

from . import grade, kalshi_books, mlb_api, pm_books

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MAX_SPREAD = 0.15
MIN_LEAN = 0.20        # resting-size lean that counts as "more money on this side"
MIN_N = 20             # below this we report insufficient data instead of a number


def _last_clean(readings):
    best = None
    for r in readings or []:
        if r.get("empty"):
            continue
        b, a = r.get("bid"), r.get("ask")
        if not (isinstance(b, (int, float)) and isinstance(a, (int, float))):
            continue
        if a <= b or (a - b) > MAX_SPREAD:
            continue
        if best is None or r.get("t", 0) > best.get("t", 0):
            best = r
    return best


def _lean(reading):
    """+1 toward the advantage side, -1 toward the opponent, 0 neutral."""
    if not reading:
        return None
    bs, as_ = float(reading.get("bid_sz") or 0), float(reading.get("ask_sz") or 0)
    if bs + as_ <= 0:
        return None
    v = (bs - as_) / (bs + as_)
    return 1 if v > MIN_LEAN else -1 if v < -MIN_LEAN else 0


def collect() -> list[dict]:
    recs = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        kb = kalshi_books.load_day(date)
        if not kb:
            continue                       # no Kalshi that day -> nothing to compare
        pb = pm_books.load_day(date) or {}
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        day = json.loads(Path(f).read_text())
        for g in day.get("games", []):
            pk = str(g.get("game_pk"))
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            if " @ " not in g.get("matchup", ""):
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            away, home = g["matchup"].split(" @ ")
            opp = home if adv == away else away
            k = _lean(_last_clean((kb.get("games", {}).get(pk) or {}).get("readings")))
            p = _lean(_last_clean((pb.get("games", {}).get(pk) or {}).get("readings")))
            if k is None or p is None:
                continue
            shift = (pc.get("line_check") or {}).get("implied_shift")
            line_team = None
            if isinstance(shift, (int, float)):
                if shift >= 0.01:
                    line_team = adv
                elif shift <= -0.01:
                    line_team = opp
            recs.append({
                "date": date, "winner": res["winner"],
                "price": {adv: a_ml, opp: o_ml}, "adv": adv, "opp": opp,
                "k": k, "p": p, "line_team": line_team,
            })
    return recs


def _rows(recs, chooser):
    out = []
    for r in recs:
        t = chooser(r)
        if not t or t not in r["price"]:
            continue
        out.append({"won": r["winner"] == t, "odds": r["price"][t]})
    return out


def _fmt(rows):
    if not rows:
        return "—"
    if len(rows) < MIN_N:
        w = sum(1 for x in rows if x["won"])
        return f"{w}-{len(rows)-w} · _n={len(rows)}, too few_"
    w = sum(1 for x in rows if x["won"])
    u = sum(grade.american_profit(x["odds"]) if x["won"] else -1 for x in rows)
    return f"{w}-{len(rows)-w} ({w/len(rows):.0%}) · {u:+.1f}u · **{u/len(rows):+.1%}** (n={len(rows)})"


def build() -> str:
    recs = collect()
    days = len({r["date"] for r in recs})
    md = ["# Kalshi vs Polymarket — do the venues agree on the money?", "",
          f"_{len(recs)} games with a clean pre-game book on BOTH venues, across "
          f"{days} day(s). Kalshi logging began 2026-07-31._", ""]
    if len(recs) < MIN_N:
        md += [f"## Not enough data yet", "",
               f"Only **{len(recs)}** games have both venues logged; this report "
               f"needs at least **{MIN_N}** before any number would mean anything. "
               "Kalshi depth cannot be backfilled - once a market moves the old "
               "book is gone - so this fills in from here at roughly the slate "
               "size per day.", "",
               "_Everything below stays blank until the sample arrives._", ""]

    agree = [r for r in recs if r["k"] == r["p"] != 0]
    disagree = [r for r in recs if r["k"] != 0 and r["p"] != 0 and r["k"] != r["p"]]
    neutral = [r for r in recs if r["k"] == 0 or r["p"] == 0]
    md += ["## Split", "",
           f"- both venues lean the SAME way: **{len(agree)}**",
           f"- venues DISAGREE: **{len(disagree)}**",
           f"- at least one venue neutral: **{len(neutral)}**", ""]

    side = lambda r, v: r["adv"] if v > 0 else r["opp"]
    md += ["## 1. When both venues agree", "",
           "| strategy | result |", "|---|---|",
           f"| back the agreed money side | {_fmt(_rows(agree, lambda r: side(r, r['k'])))} |",
           f"| fade the agreed money side | {_fmt(_rows(agree, lambda r: side(r, -r['k'])))} |", ""]

    md += ["## 2. When they disagree — does the line break the tie?", "",
           "| strategy | result |", "|---|---|",
           f"| back the side the LINE moved toward | {_fmt(_rows(disagree, lambda r: r['line_team']))} |",
           f"| fade the side the line moved toward | "
           f"{_fmt(_rows(disagree, lambda r: (r['opp'] if r['line_team'] == r['adv'] else r['adv']) if r['line_team'] else None))} |",
           f"| always back KALSHI's side | {_fmt(_rows(disagree, lambda r: side(r, r['k'])))} |",
           f"| always back POLYMARKET's side | {_fmt(_rows(disagree, lambda r: side(r, r['p'])))} |", ""]

    md.append("_Both logs store the advantage side's contract, so bid = money on "
              "our side and ask = money on the other, at both venues. Rows under "
              f"n={MIN_N} are shown as counts only - a percentage on a handful of "
              "games would be noise dressed as a finding._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "venue_agree.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
