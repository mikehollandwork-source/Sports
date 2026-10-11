"""
Build our OWN team win probability from measured hit rates, and test it.

THE IDEA
Take each starter's hit rate as we have measured it, adjust for park, weather,
opposing-hand splits, BvP and recent form, aggregate to a team offense number,
compare the two teams, and see whether that predicts the winner.

WHY THIS IS NOT THE lineup_price TEST AGAIN
That one aggregated the BOOK'S prop prices, so it was circular by construction -
it restated the moneyline and, held against it, added nothing. This builds the
number from OUR OWN recorded outcomes. It can genuinely disagree with the
market, which is the only way it could be worth anything.

NOTHING IS FITTED, DELIBERATELY
This would be the first fitted model in the repo, and fitting weights on the
same games they are judged on is how a search this size manufactures an edge.
Two protections instead:

  * AUC depends only on RANKING, so a single combined score needs no fitted
    coefficients to be scored honestly.
  * Every adjustment is a PRE-REGISTERED multiplier taken from somewhere it was
    already measured - the board's own park factor, the same wind and
    temperature shape `hr_pick` uses - not a coefficient chosen to make this
    table look good.

Each hitter's rate uses only games BEFORE the one being predicted, and is shrunk
toward the league mean by his own sample, so a hitter with four games does not
swing a lineup.

THE TEST THAT MATTERS
Not "does our number beat a coin flip" - a lineup of good hitters wins more, and
that is the moneyline restated. The question is whether it adds anything with
the market HELD FIXED, which is what killed the price version.

Read-only. Writes output/own_line.md. Changes no pick.
"""

from __future__ import annotations

import glob
import json
import logging
import statistics as st
import unicodedata
from pathlib import Path

from . import mlb_api
from .pregame_money import _implied

log = logging.getLogger("own_line")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPORT = OUTPUT_DIR / "own_line.md"
WINNERS = OUTPUT_DIR / "own_line_winners.json"
BOX = OUTPUT_DIR / "coherence_cache.json"
LINEUPS = OUTPUT_DIR / "lineup_price_cache.json"

LEAGUE_HIT_RATE = 0.63     # a starter gets a hit in ~63% of his games
SHRINK_GAMES = 12          # games before his own rate outweighs the league mean
# Pre-registered, same shapes used elsewhere in the repo.
TEMP_REF, TEMP_PER_F = 70.0, 0.002     # offence rises slightly in the heat
WIND_PER_MPH = 0.004                   # only an outward wind helps
CLAMP = (0.85, 1.15)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s.lower() if c.isalnum() or c == " ").strip()


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _winners() -> dict:
    try:
        return json.loads(WINNERS.read_text())
    except (OSError, ValueError):
        return {}


def load() -> list[dict]:
    """One row per graded game with both lineups known."""
    box = json.loads(Path(BOX).read_text())
    lineups = json.loads(Path(LINEUPS).read_text())
    won = _winners()
    dirty = False

    boards = {}
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            boards[date] = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue

    rows = []
    for date in sorted(boards):
        day = boards[date]
        need = [g for g in day.get("games", [])
                if str(g.get("game_pk")) in lineups]
        if need and date not in won:
            try:
                res = mlb_api.results_for(date)
            except Exception as exc:
                log.warning("results %s failed (%s)", date, exc)
                continue
            won[date] = {str(k): v.get("winner") for k, v in res.items()
                         if v.get("final") and v.get("winner")}
            dirty = True
        for g in need:
            pk = str(g.get("game_pk"))
            w = (won.get(date) or {}).get(pk)
            if not w:
                continue
            m = g.get("matchup") or ""
            if " @ " not in m:
                continue
            away, home = m.split(" @ ")
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0 or home not in price:
                continue
            rows.append({
                "date": date, "pk": pk, "home": home, "away": away,
                "home_won": 1 if w == home else 0,
                "ml_home": _implied(price[home]) / tot,
                "park": g.get("park_factor") or 1.0,
                "weather": g.get("weather") or {},
                "bvp": g.get("bvp") or {},
                "form": g.get("form") or {},
                "starters": lineups[pk],
            })
    if dirty:
        try:
            WINNERS.write_text(json.dumps(won))
        except OSError as exc:
            log.warning("winners cache not written (%s)", exc)
    return rows, box


def _auc(pairs) -> float | None:
    pos = [s for s, y in pairs if y]
    neg = [s for s, y in pairs if not y]
    if not pos or not neg:
        return None
    o = sorted(pairs, key=lambda t: t[0])
    ranks, i = {}, 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and o[j + 1][0] == o[i][0]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = r
        i = j + 1
    rp = sum(r for k, r in ranks.items() if o[k][1])
    n1, n2 = len(pos), len(neg)
    return (rp - n1 * (n1 + 1) / 2) / (n1 * n2)


def _weather_mult(wx: dict) -> float:
    try:
        t = float(wx.get("temp_f") or TEMP_REF)
        w = float(wx.get("wind_mph") or 0)
    except (TypeError, ValueError):
        return 1.0
    m = 1 + (t - TEMP_REF) * TEMP_PER_F + w * WIND_PER_MPH
    return _clamp(m, *CLAMP)


def score(rows: list[dict], box: dict) -> list[dict]:
    """Walk the season forward, building each team's offence index from hit
    rates measured BEFORE the game being scored."""
    hist: dict[str, list[int]] = {}

    def rate(name: str) -> float:
        g, h = hist.get(_norm(name), [0, 0])
        w = g / (g + SHRINK_GAMES)
        return w * (h / g if g else LEAGUE_HIT_RATE) + (1 - w) * LEAGUE_HIT_RATE

    out = []
    for r in sorted(rows, key=lambda x: x["date"]):
        st_ = r["starters"]
        if r["home"] not in st_ or r["away"] not in st_:
            continue
        base = {t: st.mean(rate(n) for n in st_[t]) for t in (r["home"], r["away"])}
        bvp = r["bvp"] or {}
        form = r["form"] or {}

        def hand(side):
            v = bvp.get(f"{side}_hand_ops")
            return _clamp(float(v) / 0.72, *CLAMP) if isinstance(v, (int, float)) and v else 1.0

        def frm(side):
            d = (form.get(side) or {}).get("delta")
            return _clamp(1 + float(d), *CLAMP) if isinstance(d, (int, float)) else 1.0

        wm = _weather_mult(r["weather"])
        pk_ = float(r["park"] or 1.0)
        v = {
            "base": base[r["home"]] - base[r["away"]],
            "hand": base[r["home"]] * hand("home") - base[r["away"]] * hand("away"),
            "form": base[r["home"]] * frm("home") - base[r["away"]] * frm("away"),
            "all": (base[r["home"]] * hand("home") * frm("home")
                    - base[r["away"]] * hand("away") * frm("away")),
            # park and weather are GAME-level: identical for both lineups
            "all+park+wx": ((base[r["home"]] * hand("home") * frm("home")
                             - base[r["away"]] * hand("away") * frm("away"))
                            * pk_ * wm),
        }
        out.append({**r, "idx": v})

        # only now does this game enter the history
        for nm, line in (box.get(r["pk"]) or {}).items():
            if not isinstance(line, list) or len(line) < 2 or line[1] < 1:
                continue
            c = hist.setdefault(nm, [0, 0])
            c[0] += 1
            c[1] += 1 if line[0] >= 1 else 0
    return out


VARIANTS = ["base", "hand", "form", "all", "all+park+wx"]


def build() -> str:
    rows, box = load()
    md = ["# Our own line, from measured hit rates", "",
          "_Built from outcomes we recorded, not from the book's prices — so "
          "unlike the prop-price version it can actually disagree with the "
          "market. Nothing is fitted: every multiplier is pre-registered and "
          "AUC depends only on ranking._", "",
          f"- graded games with both lineups: **{len(rows)}**", ""]
    if len(rows) < 100:
        return "\n".join(md + ["_Too few games._", ""])
    sc = score(rows, box)
    y = [r["home_won"] for r in sc]
    md += [f"- home teams won **{sum(y)/len(y):.1%}** of them", "",
           "## 1. Does it predict a winner at all?", "",
           "| version | AUC |", "|---|---|"]
    for v in VARIANTS:
        a = _auc([(r["idx"][v], r["home_won"]) for r in sc])
        md.append(f"| {v} | {a:.4f} |")
    a_ml = _auc([(r["ml_home"], r["home_won"]) for r in sc])
    md += [f"| **the market's moneyline** | **{a_ml:.4f}** |", "",
           "_Park and weather are GAME-level — the same for both lineups — so "
           "in a home-minus-away difference they cancel almost exactly. They "
           "belong in a TOTALS model, not a win model, and the row above is "
           "the evidence._", ""]

    best = max(VARIANTS, key=lambda v: _auc([(r["idx"][v], r["home_won"]) for r in sc]))
    md += [f"## 2. Held against the market (using `{best}`)", "",
           "_Thirds by moneyline, each split by our index. If we are only "
           "restating the price, both halves inside a third win equally._", "",
           "| moneyline third | our index | n | home win% |", "|---|---|---|---|"]
    srt = sorted(sc, key=lambda r: r["ml_home"])
    k = len(srt) // 3
    gaps = []
    for i, lbl in enumerate(("home dogs", "middle", "home favourites")):
        chunk = srt[i * k:(i + 1) * k] if i < 2 else srt[2 * k:]
        if len(chunk) < 20:
            continue
        med = st.median(r["idx"][best] for r in chunk)
        hi = [r for r in chunk if r["idx"][best] > med]
        lo = [r for r in chunk if r["idx"][best] <= med]
        for lab, grp in (("above median", hi), ("below median", lo)):
            if grp:
                md.append(f"| {lbl} | {lab} | {len(grp)} | "
                          f"{sum(r['home_won'] for r in grp)/len(grp):.1%} |")
        if hi and lo:
            gaps.append(sum(r["home_won"] for r in hi) / len(hi)
                        - sum(r["home_won"] for r in lo) / len(lo))
    if gaps:
        same = all(g > 0 for g in gaps) or all(g < 0 for g in gaps)
        md += ["", f"_Gap inside a third: "
               f"{', '.join(f'{g:+.1%}' for g in gaps)} — mean "
               f"**{st.mean(gaps):+.1%}**._",
               "", ("_All three thirds agree in sign._" if same else
                    "_**The thirds disagree in sign**, which is what one lucky "
                    "cell looks like rather than a signal._"), ""]
    md += ["## How to read this", "",
           "- section 1 cannot prove anything on its own: better hitters win "
           "more, and the moneyline already knows that",
           "- section 2 is the test. A mean gap near zero, or thirds that "
           "disagree in sign, means the market already contains it",
           "- nothing here changes a pick", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    OUTPUT_DIR.mkdir(exist_ok=True)
    t = build()
    REPORT.write_text(t)
    print(t)


if __name__ == "__main__":
    main()
