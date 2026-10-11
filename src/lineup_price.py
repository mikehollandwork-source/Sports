"""
Does the lineup's PROP PRICING predict the game beyond the moneyline?

THE IDEA
Take every hitter in a starting lineup, read what the book charges for his 1+
hit prop, average it, and compare the two teams. The question is whether that
aggregate says anything the moneyline has not already said.

WHY IT IS NOT OBVIOUSLY CIRCULAR
It very nearly is. Prop prices and the moneyline are set off the same
information, so summing nine props mostly restates the team price - and
`ev_model` already concluded that everything we track is in the price. But
these are two DIFFERENT markets, and the only edges this repo has ever found
live in disagreements between markets, which is why Polymarket and Kalshi are
tracked at all. So the test is not "do good lineups win" - of course they do -
it is whether the prop aggregate adds anything ONCE THE MONEYLINE IS HELD
FIXED. Without that control the answer is guaranteed and worthless.

TWO DATA COMPROMISES, BOTH STATED UP FRONT
1. Only 2% of stored hitter prices carry both sides (73 of 4,447), so the
   per-hitter vig cannot be removed. Raw over-implied probability is inflated
   by the hold, but the hold is ~6.5-7% and roughly flat across hitters, and
   the metric is a DIFFERENCE between two lineups, so most of it cancels. It
   does not cancel perfectly - longer prices carry more vig - so the gap is
   slightly noisy, not biased toward either side.
2. The odds file pools both lineups under one matchup key with no team labels.
   Teams come from the boxscore, which also lets the population be the actual
   STARTERS (battingOrder ending 00, not a substitute) rather than everyone
   who was quoted - which is what "every hitter in the starting lineup" means.

Read-only. Writes output/lineup_price.md. Changes no pick.
"""

from __future__ import annotations

import glob
import json
import logging
import statistics as st
import unicodedata
from pathlib import Path

from . import mlb_api, prop_odds
from .pregame_money import _implied

log = logging.getLogger("lineup_price")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPORT = OUTPUT_DIR / "lineup_price.md"
CACHE = OUTPUT_DIR / "lineup_price_cache.json"
MIN_PRICED = 6        # starters with a price needed before a side is usable


def _norm(s: str) -> str:
    """Lowercase, accent-stripped, punctuation-free: the odds feed writes
    'jose ramirez' where the boxscore has 'Jose Ramirez'."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s.lower() if c.isalnum() or c == " ").strip()


def _starters(game_pk: int) -> dict[str, list[str]] | None:
    """{team name: [starter names]} from the boxscore, or None."""
    try:
        bs = mlb_api._get(f"game/{game_pk}/boxscore")
    except Exception as exc:
        log.warning("boxscore %s failed (%s)", game_pk, exc)
        return None
    out = {}
    for side in ("away", "home"):
        t = (bs.get("teams") or {}).get(side) or {}
        nm = (t.get("team") or {}).get("name")
        if not nm:
            return None
        names = []
        for p in (t.get("players") or {}).values():
            bo = p.get("battingOrder")
            if not bo:
                continue
            try:
                n = int(bo)
            except (TypeError, ValueError):
                continue
            if n % 100 != 0:
                continue                      # a substitute, not a starter
            if (p.get("gameStatus") or {}).get("isSubstitute"):
                continue
            full = (p.get("person") or {}).get("fullName")
            if full:
                names.append(full)
        out[nm] = names
    return out


def collect() -> list[dict]:
    try:
        cache = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        cache = {}
    rows = []
    files = [f for f in sorted(glob.glob(str(OUTPUT_DIR / "prop_odds_2026-*.json")))
             if "_hr_" not in f and "_hrr_" not in f]
    for f in files:
        date = Path(f).stem.split("prop_odds_")[1]
        try:
            odds = json.loads(Path(f).read_text())
        except (OSError, ValueError):
            continue
        try:
            results = mlb_api.results_for(date)
            board = json.loads((OUTPUT_DIR / f"picks_{date}.json").read_text())
        except Exception:
            continue
        by_matchup = {g.get("matchup"): g for g in board.get("games", [])}
        for matchup, hitters in odds.items():
            if not isinstance(hitters, dict) or not hitters:
                continue
            key = matchup.replace("@", " @ ")
            g = by_matchup.get(key) or by_matchup.get(matchup)
            if not g:
                continue
            pk = g.get("game_pk")
            res = results.get(pk)
            if not res or not res.get("final") or not res.get("winner"):
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            ck = str(pk)
            if ck not in cache:
                s = _starters(pk)
                if not s:
                    continue
                cache[ck] = s
            starters = cache[ck]
            # The cache changed shape mid-season: older files store the over
            # price as a bare int, newer ones as {"over","under"}. Reusing
            # prop_odds._as_row rather than re-checking the type here - my own
            # version saw only the new shape and matched 4 games out of 306.
            priced = {}
            for nm_, v in hitters.items():
                o = prop_odds._as_row(v).get("over")
                if isinstance(o, int):
                    priced[_norm(nm_)] = o
            team_p = {}
            for team, names in starters.items():
                ps = [_implied(priced[_norm(n)]) for n in names
                      if _norm(n) in priced]
                if len(ps) >= MIN_PRICED:
                    team_p[team] = (st.mean(ps), len(ps))
            if len(team_p) != 2:
                continue
            away, home = key.split(" @ ")
            if away not in team_p or home not in team_p:
                continue
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0:
                continue
            rows.append({
                "date": date, "matchup": key, "home": home, "away": away,
                "winner": res["winner"],
                "home_prop": team_p[home][0], "away_prop": team_p[away][0],
                "n_home": team_p[home][1], "n_away": team_p[away][1],
                "home_ml": price[home], "away_ml": price[away],
                "ml_home_prob": _implied(price[home]) / tot,
            })
    try:
        CACHE.write_text(json.dumps(cache))
    except OSError as exc:
        log.warning("cache not written (%s)", exc)
    return rows


def _profit(odds: int, won: bool) -> float:
    if not won:
        return -1.0
    return odds / 100 if odds > 0 else 100 / abs(odds)


def _auc(pairs: list[tuple[float, int]]) -> float | None:
    """P(a winner scores above a loser), ties half. Threshold-free."""
    pos = [s for s, y in pairs if y]
    neg = [s for s, y in pairs if not y]
    if not pos or not neg:
        return None
    ordered = sorted(pairs, key=lambda t: t[0])
    ranks, i = {}, 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1][0] == ordered[i][0]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = r
        i = j + 1
    rp = sum(r for k, r in ranks.items() if ordered[k][1])
    n1, n2 = len(pos), len(neg)
    return (rp - n1 * (n1 + 1) / 2) / (n1 * n2)


def build() -> str:
    rows = collect()
    md = ["# Does lineup prop pricing beat the moneyline?", "",
          "_Average 1+ hit price across each starting lineup, compared between "
          "the two teams, then tested against the moneyline rather than "
          "against nothing._", "",
          f"- graded games with both lineups priced: **{len(rows)}**", ""]
    if len(rows) < 60:
        return "\n".join(md + ["_Too few games to test._", ""])

    for r in rows:
        r["edge"] = r["home_prop"] - r["away_prop"]
        r["home_won"] = 1 if r["winner"] == r["home"] else 0
    md += [f"- mean starters priced per side: "
           f"{st.mean([r['n_home'] for r in rows] + [r['n_away'] for r in rows]):.1f}",
           f"- mean lineup hit probability (raw, vig included): "
           f"{st.mean([r['home_prop'] for r in rows]):.1%}", ""]

    a_edge = _auc([(r["edge"], r["home_won"]) for r in rows])
    a_ml = _auc([(r["ml_home_prob"], r["home_won"]) for r in rows])
    md += ["## 1. On its own — and against the moneyline", "",
           "| predictor of a home win | AUC |", "|---|---|",
           f"| lineup prop edge | {a_edge:.4f} |",
           f"| **moneyline** | **{a_ml:.4f}** |", "",
           "_Both should beat 0.50. The question is the next section._", ""]

    # 2. THE CONTROL: within moneyline buckets, does the prop edge still sort?
    srt = sorted(rows, key=lambda r: r["ml_home_prob"])
    k = len(srt) // 3
    md += ["## 2. Held against the moneyline", "",
           "_Games split into thirds by moneyline, then each third split by "
           "prop edge. If the prop aggregate is only restating the price, the "
           "two halves inside a third win at the same rate._", "",
           "| moneyline third | prop edge | n | home win% |", "|---|---|---|---|"]
    resid = []
    for i, lbl in enumerate(("longest home dogs", "middle", "biggest home favs")):
        chunk = srt[i * k:(i + 1) * k] if i < 2 else srt[2 * k:]
        if len(chunk) < 20:
            continue
        med = st.median(r["edge"] for r in chunk)
        for side, sel in (("above median", lambda r: r["edge"] > med),
                          ("below median", lambda r: r["edge"] <= med)):
            sub = [r for r in chunk if sel(r)]
            if not sub:
                continue
            wr = sum(r["home_won"] for r in sub) / len(sub)
            md.append(f"| {lbl} | {side} | {len(sub)} | {wr:.1%} |")
        hi = [r for r in chunk if r["edge"] > med]
        lo = [r for r in chunk if r["edge"] <= med]
        if hi and lo:
            resid.append(sum(r["home_won"] for r in hi) / len(hi)
                         - sum(r["home_won"] for r in lo) / len(lo))
    if resid:
        md += ["", f"_Mean gap between the two halves, inside a moneyline "
               f"third: **{st.mean(resid):+.1%}**. That is the part the "
               f"moneyline had not already priced._", ""]

    # 3. The bettable form
    md += ["## 3. Betting it", "",
           "_Back the side the props favour, whenever they disagree with the "
           "moneyline by more than a threshold. Graded at the board's own "
           "price._", "",
           "| disagreement | bets | record | units | ROI |", "|---|---|---|---|---|"]
    for thr in (0.00, 0.01, 0.02, 0.03):
        bets = []
        for r in rows:
            prop_home = r["edge"] > 0
            ml_home = r["ml_home_prob"] > 0.5
            if prop_home == ml_home:
                continue                   # no disagreement
            if abs(r["edge"]) < thr:
                continue
            team = r["home"] if prop_home else r["away"]
            odds = r["home_ml"] if prop_home else r["away_ml"]
            bets.append(_profit(odds, r["winner"] == team))
        if len(bets) < 15:
            md.append(f"| edge ≥ {thr:.0%} | {len(bets)} | _too few_ | | |")
            continue
        w = sum(1 for b in bets if b > 0)
        u = sum(bets)
        md.append(f"| edge ≥ {thr:.0%} | {len(bets)} | {w}-{len(bets)-w} "
                  f"| {u:+.2f}u | **{u/len(bets):+.1%}** |")
    md += ["", "## How to read this", "",
           "- section 1 proves nothing: a lineup the book prices highly wins "
           "more often, which is the moneyline restated",
           "- section 2 is the real test. A gap near zero means the prop "
           "aggregate is already inside the team price and there is nothing "
           "to add",
           "- section 3 pays the vig, so it has to clear roughly +3% to be "
           "worth anything at all, and n is small at the wider thresholds",
           "- the per-hitter vig could not be removed (only 2% of stored "
           "prices are two-sided), so the edge is a difference of two "
           "inflated numbers — mostly cancelling, not perfectly", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    OUTPUT_DIR.mkdir(exist_ok=True)
    text = build()
    REPORT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
