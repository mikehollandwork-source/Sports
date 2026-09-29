"""
Is the market right about every team, or only most of them?

THE QUESTION THIS ANSWERS
"Only pick teams the market prices correctly" is backwards - a correctly priced
team returns exactly minus the hold. The useful version is its mirror: is there
any team the market is reliably WRONG about, and can it be told apart from the
one team in thirty that looks wrong by chance?

That last clause is the whole difficulty, and it is why a single-team report
cannot answer this. Philadelphia came back at p = 0.651 and Atlanta at p =
0.652 - both correctly priced - but scanning thirty teams for the largest gap
will always turn up something. With every team in one grid the scan itself can
be corrected for, which is impossible one team at a time.

WHAT IS MEASURED
Each game's two prices are de-vigged to sum to one, giving the probability the
market assigned each side. Summed over a team's games, that is the wins the
market expected. Gap is actual minus expected.

  the permutation redraws EVERY game once per trial from those probabilities,
  then recomputes all thirty gaps from that one redraw, and keeps the largest
  and smallest. A team only counts as mispriced if its gap beats what the best
  of thirty reaches on noise alone - which is a much higher bar than its own
  p-value, and the correct one.

THE POOLED TESTS, AND ONE TRAP IN THEM
Three league-wide questions follow, on one row per GAME rather than per team.
That detail matters: every game contributes two team-games whose residuals sum
to zero by construction, so pooling both sides makes any favourite-versus-dog
comparison mechanically symmetric and guarantees a null. Using the favourite's
row only avoids that.

  favourite-longshot bias   do favourites as a group beat their price?
  the Philadelphia shape    teams that are usually favourites, in the games
                            where they are dogs. Their 4-12 as a dog was the
                            hint; sixteen games cannot test it and the league
                            can.
  trend across price        residual against implied probability, pooled.

Writes output/league_calibration.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import _implied

log = logging.getLogger("league_calibration")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 10000       # 30 gaps recomputed per trial; 10k is ample resolution
MIN_GAMES = 40


def collect() -> list[dict]:
    """One row per graded game: both teams, both de-vigged prices, the winner.
    Walks each board day once - thirty teams through the per-team collector
    would be thirty results fetches per day."""
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        for g in json.loads(Path(f).read_text()).get("games", []):
            res = results.get(g.get("game_pk"))
            m = g.get("matchup") or ""
            if not res or not res.get("final") or not res.get("winner") or " @ " not in m:
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            away, home = m.split(" @ ")
            if adv not in (away, home) or not isinstance(a_ml, int) \
                    or not isinstance(o_ml, int):
                continue
            opp = home if adv == away else away
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0:
                continue
            rows.append({
                "date": date, "winner": res["winner"],
                "home": home, "away": away,
                # per side: price and de-vigged probability
                "price": {adv: a_ml, opp: o_ml},
                "prob": {adv: _implied(a_ml) / tot, opp: _implied(o_ml) / tot},
            })
    return rows


def team_games(rows: list[dict]) -> dict[str, list[dict]]:
    out = defaultdict(list)
    for r in rows:
        for t in (r["home"], r["away"]):
            out[t].append({"date": r["date"], "odds": r["price"][t],
                           "p": r["prob"][t], "won": r["winner"] == t,
                           "home": t == r["home"]})
    return out


def _roi(rs) -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r["odds"]) if r["won"] else -1
               for r in rs) / len(rs)


def _pearson(xs, ys) -> float:
    if len(xs) < 3:
        return float("nan")
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** .5
    dy = sum((y - my) ** 2 for y in ys) ** .5
    return num / (dx * dy) if dx and dy else float("nan")


def build() -> str:
    rows = collect()
    tg = {t: v for t, v in team_games(rows).items() if len(v) >= MIN_GAMES}
    md = ["# Is the market right about every team, or only most of them?", "",
          "_\"Only bet teams the market prices correctly\" is backwards — a "
          "correctly priced team returns exactly minus the hold. The useful "
          "version is the mirror: is any team reliably MISpriced, and can it be "
          "told from the one team in thirty that looks mispriced by chance?_", "",
          "_That last clause is why a single-team report cannot settle this. "
          "Philadelphia came back p = 0.651 and Atlanta p = 0.652 — both "
          "correctly priced — but scan thirty teams for the biggest gap and "
          "something always turns up. Here the scan itself is corrected for._", "",
          f"- graded games: **{len(rows)}** · teams with ≥{MIN_GAMES} games: "
          f"**{len(tg)}**", ""]
    if len(rows) < 300 or len(tg) < 20:
        return "\n".join(md + ["Not enough data.", ""])

    # ---- per-team table -------------------------------------------------
    stats = {}
    for t, v in tg.items():
        exp = sum(r["p"] for r in v)
        act = sum(1 for r in v if r["won"])
        stats[t] = {"n": len(v), "exp": exp, "act": act, "gap": act - exp,
                    "roi": _roi(v)}
    md += ["## Every team, most underrated first", "",
           "| team | games | market expected | actual | gap | flat-stake |",
           "|---|---|---|---|---|---|"]
    for t in sorted(stats, key=lambda t: -stats[t]["gap"]):
        s = stats[t]
        md.append(f"| {t} | {s['n']} | {s['exp']:.1f} | {s['act']} | "
                  f"**{s['gap']:+.1f}** | {s['roi']:+.1%} |")
    md.append("")

    # ---- the scan, corrected --------------------------------------------
    order = list(tg)
    idx = {t: [i for i, r in enumerate(rows)
               if r["home"] == t or r["away"] == t] for t in order}
    probs = {t: {i: rows[i]["prob"][t] for i in idx[t]} for t in order}
    rng = random.Random(3030)
    hi, lo = [], []
    for _ in range(TRIALS):
        won = {}
        for i, r in enumerate(rows):
            won[i] = r["home"] if rng.random() < r["prob"][r["home"]] else r["away"]
        gaps = []
        for t in order:
            a = sum(1 for i in idx[t] if won[i] == t)
            gaps.append(a - sum(probs[t].values()))
        hi.append(max(gaps))
        lo.append(min(gaps))
    best = max(stats, key=lambda t: stats[t]["gap"])
    worst = min(stats, key=lambda t: stats[t]["gap"])
    obs_hi, obs_lo = stats[best]["gap"], stats[worst]["gap"]
    p_hi = (sum(1 for x in hi if x >= obs_hi) + 1) / (TRIALS + 1)
    p_lo = (sum(1 for x in lo if x <= obs_lo) + 1) / (TRIALS + 1)
    md += [f"## Corrected for scanning {len(tg)} teams", "",
           f"- most underrated: **{best}** at {obs_hi:+.1f} wins · the best of "
           f"{len(tg)} teams on noise alone reaches {st.median(hi):+.1f} median, "
           f"{sorted(hi)[int(.95*TRIALS)]:+.1f} at the 95th · "
           f"**corrected p = {p_hi:.3f}**",
           f"- most overrated: **{worst}** at {obs_lo:+.1f} wins · the worst "
           f"reaches {st.median(lo):+.1f} median, "
           f"{sorted(lo)[int(.05*TRIALS)]:+.1f} at the 5th · "
           f"**corrected p = {p_lo:.3f}**",
           "",
           "_Read the median column before the gap column. A gap of "
           f"{st.median(hi):+.1f} wins is what the LUCKIEST of {len(tg)} teams "
           "shows when every price is perfect._", ""]

    # ---- pooled tests, one row per GAME ---------------------------------
    md += ["## League-wide, one row per game", "",
           "_Per game, not per team: both sides' residuals sum to zero by "
           "construction, so pooling both would make any favourite-versus-dog "
           "comparison mechanically symmetric and guarantee a null._", ""]
    favs, dogs = [], []
    for r in rows:
        f = min(r["price"], key=lambda t: r["price"][t])
        d = max(r["price"], key=lambda t: r["price"][t])
        favs.append({"odds": r["price"][f], "p": r["prob"][f],
                     "won": r["winner"] == f})
        dogs.append({"odds": r["price"][d], "p": r["prob"][d],
                     "won": r["winner"] == d})
    md += ["| | games | expected | actual | gap | flat-stake |",
           "|---|---|---|---|---|---|"]
    for lab, side in (("back every favourite", favs), ("back every underdog", dogs)):
        e = sum(x["p"] for x in side)
        a = sum(1 for x in side if x["won"])
        md.append(f"| {lab} | {len(side)} | {e:.1f} | {a} | **{a-e:+.1f}** | "
                  f"{_roi(side):+.1%} |")
    md.append("")

    # ---- the Philadelphia shape, generalised ----------------------------
    fav_rate = {t: sum(1 for r in v if r["odds"] < 0) / len(v) for t, v in tg.items()}
    md += ["## The Philadelphia shape, tested on the league", "",
           "_Philadelphia met their price across 66 games as a favourite and "
           "went 4-12 as a dog. Sixteen games cannot test that. If it is real, "
           "teams who are usually favourites should underperform whenever they "
           "are priced as dogs._", "",
           "| cut | teams | their games AS DOGS | expected | actual | gap | flat-stake |",
           "|---|---|---|---|---|---|---|"]
    for cut in (0.55, 0.60, 0.65, 0.70):
        who = [t for t, fr in fav_rate.items() if fr >= cut]
        dogs = [r for t in who for r in tg[t] if r["odds"] > 0]
        if len(dogs) >= 40:
            e = sum(r["p"] for r in dogs)
            a = sum(1 for r in dogs if r["won"])
            md.append(f"| favourite ≥{cut:.0%} of the time | {len(who)} | "
                      f"{len(dogs)} | {e:.1f} | {a} | **{a-e:+.1f}** | "
                      f"{_roi(dogs):+.1%} |")
    md += ["", "_Four cuts are four looks; treat the best of them accordingly._", ""]

    # ---- trend across price, pooled -------------------------------------
    ps = [x["p"] for x in favs]
    resid = [(1 if x["won"] else 0) - x["p"] for x in favs]
    r_obs = _pearson(ps, resid)
    rng2 = random.Random(4040)
    null = [_pearson(ps, [(1 if rng2.random() < p else 0) - p for p in ps])
            for _ in range(2000)]
    pv = (sum(1 for x in null if abs(x) >= abs(r_obs)) + 1) / 2001
    md += ["## Trend across price, pooled over every game", "",
           f"- correlation of the favourite's residual with its implied "
           f"probability: **{r_obs:+.3f}**",
           f"- permuted null 95% within ±"
           f"{sorted(abs(x) for x in null)[int(.95*2000)]:.3f} · "
           f"**two-sided p = {pv:.3f}**",
           "- " + ("a real bias that varies with price — worth pursuing"
                   if pv < 0.05 else
                   "**no bias across price.** Philadelphia's p = 0.034 trend "
                   "does not reproduce league-wide, which is what one look in "
                   "nineteen at a single team predicts"), ""]

    md += ["## What this can and cannot support", "",
           "- a team's gap only means something if it beats the **best of "
           f"{len(tg)}** on noise, not its own p-value",
           "- a flat-stake return near **−4% to −5%** is a correctly priced "
           "team — that is the hold",
           "- one season per team. Even the extremes here have roughly 80 "
           "games behind them, which is why the corrected column matters more "
           "than the ranking", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "league_calibration.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
