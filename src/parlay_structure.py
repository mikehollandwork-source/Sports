"""
Is there ANY parlay structure our data supports? Arithmetic first, then one test.

THE ARITHMETIC, WHICH DOES NOT NEED DATA
A parlay multiplies prices, so it multiplies the hold too. One side of a hit
prop carries roughly 4.5% hold; five legs carry about 1-(1-0.045)^5 = 21%. No
set of individually break-even legs survives a 21% tax, and our legs are not
break-even: posted hit props hit 62.6% against a 68.1% break-even at -200.

This repo already measured parlays and the answer is in `prop_grade`:
20-47, -28.2% ROI over 67 bets, day-block bootstrap CI -47.4% to -6.7%. That is
the ONLY confidence interval in the whole system that excludes zero, and it is a
loss. Breakeven at the median parlay price (+153) was 39.5% and the hit rate was
29.9%. The mechanism was arithmetic, not variance: two negative legs multiplied,
with each leg's vig compounding into one price.

So "put the odds in my favour" and "make it hit big" are not two requests, they
are opposite ends of one dial, and the dial is priced. What follows quantifies
both ends and then tests the one mechanism that could genuinely beat the price.

THE ONE MECHANISM: CORRELATION
A parlay is priced as if its legs are independent. If the legs are actually
POSITIVELY correlated, the true probability is higher than the product and the
parlay is underpriced. That is the only way a parlay is better than its legs,
and it is the whole reason books either restrict same-game combinations or price
them with a correlation adjustment.

Our hit props are a natural candidate: two hitters in the same lineup face the
SAME starting pitcher in the SAME conditions, so when one is getting hits the
other probably is too. This measures that, net of the obvious confound - good
hitters hit more, so any two good hitters look correlated even if games are
independent. Each hitter's rate is therefore computed LEAVE-ONE-OUT, excluding
the game being predicted, and the null is a permutation that keeps every
hitter's own outcomes and only destroys which game they were in.

Read-only. Writes output/parlay_structure.md. Stakes nothing, changes no pick.
"""

from __future__ import annotations

import json
import logging
import random
import statistics as st
from itertools import combinations

from . import totals_signal
from pathlib import Path

log = logging.getLogger("parlay_structure")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPORT = OUTPUT_DIR / "parlay_structure.md"
BOX = OUTPUT_DIR / "coherence_cache.json"
LINEUPS = OUTPUT_DIR / "lineup_price_cache.json"

HOLD_PER_LEG = 0.045       # a two-sided market's typical hold
PROP_RATE = 0.626          # our posted hit props' measured rate
PROP_PRICE = -200          # and the price they are typically offered at
# "prop quality" for the correlation test: hitters whose own rate is at least
# this, which is roughly the population our selector posts from.
QUALITY = 0.60
MIN_GAMES = 8
PERM_RUNS = 120    # permutations per cell; the null MEAN is what matters
SEED = 20261012


def _dec(american: int) -> float:
    return american / 100 + 1 if american > 0 else 100 / abs(american) + 1


def _american(dec: float) -> int:
    return round((dec - 1) * 100) if dec >= 2 else -round(100 / (dec - 1))


def payout_table() -> list[str]:
    """What each parlay length pays at our prop price, and what it needs.

    The point of the table is the last two columns: the hit rate the price
    demands, against the hit rate independent legs actually deliver.
    """
    md = ["## The arithmetic, before any data", "",
          f"_Every leg is a posted hit prop: measured **{PROP_RATE:.1%}** at "
          f"**{PROP_PRICE:+d}** (break-even "
          f"{abs(PROP_PRICE) / (abs(PROP_PRICE) + 100):.1%}). A $5 stake._", "",
          "| legs | parlay price | $5 returns | needs | independent legs give "
          "| edge |", "|---|---|---|---|---|---|"]
    for n in (1, 2, 3, 4, 5, 7, 9):
        dec = _dec(PROP_PRICE) ** n
        need = 1 / dec
        have = PROP_RATE ** n
        md.append(f"| {n} | {_american(dec):+d} | ${5 * dec:,.0f} | "
                  f"{need:.2%} | {have:.2%} | "
                  f"**{have / need - 1:+.1%}** |")
    md += ["", "_Two things fall out of this table._", "",
           "1. **The edge per leg does not change - it compounds.** A leg that "
           "is x% bad is x% bad every time it is multiplied, so the parlay's "
           "edge is just the leg's edge raised to the number of legs. A parlay "
           "cannot rescue a losing leg; it can only lose faster.",
           f"2. **$5 into $200 is decimal 40**, which these legs reach at "
           f"nine of them, and nine of them hit "
           f"{PROP_RATE ** 9:.2%} against the {1 / _dec(PROP_PRICE) ** 9:.2%} "
           "the price demands. To get there in five legs instead, each leg has "
           f"to pay {_american(40 ** 0.2):+d} - a "
           f"{1 / 40 ** 0.2:.1%} break-even, i.e. underdogs, not our props.",
           ""]
    return md


def hold_block() -> list[str]:
    md = ["## Why the tax grows", "",
          f"_Each leg of a two-sided market carries about "
          f"{HOLD_PER_LEG:.1%} hold. Parlaying multiplies the prices, so the "
          "holds compound._", "",
          "| legs | hold you are paying |", "|---|---|"]
    for n in (1, 2, 3, 5, 9):
        md.append(f"| {n} | **{1 - (1 - HOLD_PER_LEG) ** n:.1%}** |")
    return md + [""]


# --- the correlation test -----------------------------------------------------

def _load() -> tuple[dict, dict]:
    return json.loads(BOX.read_text()), json.loads(LINEUPS.read_text())


# The box cache was WRITTEN with `totals_signal._norm`, which keeps spaces, so
# reading it with a second normaliser that strips them matches nothing and the
# whole test silently reports n=0. Reuse the one that wrote the file.
_norm = totals_signal._norm


def build_rows() -> tuple[list, dict]:
    """[(pk, team, hitter, got_hit)] for every start, and each hitter's record.

    A hitter only counts for a game where he actually batted - a zero from a
    night he did not play is not a prop losing.
    """
    box, lineups = _load()
    rows, rec = [], {}
    for pk, teams in lineups.items():
        lines = box.get(pk) or {}
        for team, names in teams.items():
            for nm in names:
                line = lines.get(_norm(nm))
                if not isinstance(line, list) or len(line) < 2 or line[1] < 1:
                    continue
                hit = 1 if line[0] >= 1 else 0
                rows.append((pk, team, _norm(nm), hit))
                r = rec.setdefault(_norm(nm), [0, 0])
                r[0] += 1
                r[1] += hit
    return rows, rec


# WHY THE RATE COMES FROM A HELD-OUT HALF OF HIS GAMES
#
# The first version of this computed each hitter's rate LEAVE-ONE-OUT and then
# kept only hitters whose rate cleared `QUALITY`. That reported a lift of
# x0.807 - a 19% ANTI-correlation between same-lineup hitters, which no
# mechanism explains - and a permutation p of exactly 1.000 in all four cells,
# which is what a broken estimator looks like rather than a finding.
#
# The bug was selecting on the same estimate used as the expectation. Over ~18
# games a rate has a standard error near 0.115, so filtering at 0.60 from a
# population averaging 0.604 selects mostly upward noise: the kept rates
# overstate the hitters' true rates, the expected product inherits that, and the
# actual outcomes fall short of it. The deficit was the winner's curse, not the
# lineup.
#
# So the rate now comes from EVEN-indexed games and is only ever applied to
# ODD-indexed ones. The filter sees a number computed from games that are not
# being measured, the expectation uses that same independent number, and the
# permutation can shuffle outcomes without disturbing the rates at all.
MIN_HALF = 6


def split_rates(rows: list) -> tuple[dict, list]:
    """({hitter: rate from his EVEN games}, [the ODD-game rows to measure on]).

    Nothing measured below shares a game with the rate that judges it.
    """
    by_hitter: dict = {}
    for r in rows:
        by_hitter.setdefault(r[2], []).append(r)
    rates, measure = {}, []
    for who, items in by_hitter.items():
        even, odd = items[0::2], items[1::2]
        if len(even) < MIN_HALF or not odd:
            continue
        rates[who] = sum(x[3] for x in even) / len(even)
        measure += odd
    return rates, measure


def lift(rows: list, rates: dict, k: int, same_team: bool,
         outcomes: dict | None = None) -> tuple:
    """(observed joint rate, expected if independent, n combinations).

    `outcomes` overrides the result per (pk, hitter); the permutation null uses
    it so it runs through this exact code path rather than a parallel one. The
    rates are untouched by it, which is what makes that null clean.
    """
    by_game: dict = {}
    for pk, team, who, hit in rows:
        if rates.get(who, 0) < QUALITY:
            continue
        by_game.setdefault(pk, {}).setdefault(team, []).append((who, hit))
    obs = exp = 0.0
    n = 0
    for pk, teams in by_game.items():
        if same_team:
            groups = [[(t, w, h) for w, h in members]
                      for t, members in teams.items()]
        else:
            if len(teams) != 2:
                continue
            groups = [[(t, w, h) for t, members in teams.items()
                       for w, h in members]]
        for g in groups:
            if len(g) < k:
                continue
            for combo in combinations(g, k):
                if not same_team and len({c[0] for c in combo}) < 2:
                    continue      # must straddle the two lineups
                res = [outcomes.get((pk, c[1]), c[2]) if outcomes else c[2]
                       for c in combo]
                obs += 1.0 if all(res) else 0.0
                p = 1.0
                for c in combo:
                    p *= rates[c[1]]
                exp += p
                n += 1
    return (obs / n if n else None, exp / n if n else None, n)


def permute_outcomes(rows: list, rnd: random.Random) -> dict:
    """Each hitter keeps his own outcomes; only WHICH GAME they came from is
    shuffled. Hitter quality intact, game co-movement destroyed - and the rates
    are built from the other half of his games, so they do not move."""
    by_hitter: dict = {}
    for pk, _t, who, hit in rows:
        by_hitter.setdefault(who, []).append((pk, hit))
    out = {}
    for who, items in by_hitter.items():
        hits = [h for _pk, h in items]
        rnd.shuffle(hits)
        for (pk, _h), new in zip(items, hits):
            out[(pk, who)] = new
    return out


def correlation_block(rows: list, rates: dict) -> list[str]:
    md = ["## The only mechanism that could beat the price: correlation", "",
          "_A parlay is priced as if its legs are independent. Two hitters in "
          "the SAME lineup face the same starter in the same conditions, so "
          "they should not be._", "",
          "_`observed` is how often every leg actually hit and `independent` "
          "is the product of the legs' rates, each built from a HELD-OUT half "
          "of that hitter's games. **Read the `vs null` column, not `lift`.** "
          "Filtering hitters at "
          f"{QUALITY:.0%} selects upward noise in the half the rate is built "
          "from, so those rates overstate true skill and `independent` "
          "inherits it - which is why even the permuted null sits below "
          "×1.000. The null carries that bias identically, differing from the "
          "real data only in which game each outcome came from, so dividing "
          "by it leaves the part that is actually correlation._", "",
          "| legs | pairing | combos | observed | independent | lift | "
          "null lift | **vs null** | p |",
          "|---|---|---|---|---|---|---|---|---|"]
    rnd = random.Random(SEED)
    perms = [permute_outcomes(rows, rnd) for _ in range(PERM_RUNS)]
    for k in (2, 3):
        for same in (True, False):
            o, e, n = lift(rows, rates, k, same)
            label = "same team" if same else "opposite teams"
            if o is None or not e:
                md.append(f"| {k} | {label} | {n} | — | — | — | — |")
                continue
            # permutation null on the lift, reusing the same code path
            null = []
            for p in perms:
                po, pe, _n = lift(rows, rates, k, same, outcomes=p)
                if po is not None and pe:
                    null.append(po / pe)
            real = o / e
            pval = ((sum(1 for x in null if x >= real) + 1) / (len(null) + 1)
                    if null else None)
            nullm = st.mean(null) if null else None
            vs = real / nullm if nullm else None
            md.append(f"| {k} | {label} | {n} | {o:.3%} | {e:.3%} | "
                      f"×{real:.3f} | "
                      + (f"×{nullm:.3f}" if nullm else "—") + " | "
                      + (f"**×{vs:.3f}**" if vs else "—") + " | "
                      + (f"{pval:.3f}" if pval is not None else "—") + " |")
    return md + [""]


def verdict(rows: list, rates: dict) -> list[str]:
    """What the measured lift is worth in price terms, against the tax.

    Uses the NULL-CALIBRATED lift, for the reason the table explains: the raw
    ratio carries the quality filter's winner's curse and the null carries the
    same one, so only the ratio of the two is correlation.
    """
    md = ["## What that lift is worth, against what it has to beat", ""]
    rnd = random.Random(SEED + 1)
    perms = [permute_outcomes(rows, rnd) for _ in range(PERM_RUNS)]
    for k in (2, 3):
        o, e, n = lift(rows, rates, k, True)
        if not (o and e):
            continue
        null = []
        for pm in perms:
            po, pe, _n = lift(rows, rates, k, True, outcomes=pm)
            if po is not None and pe:
                null.append(po / pe)
        if not null:
            continue
        gain = (o / e) / st.mean(null) - 1
        tax = 1 - (1 - HOLD_PER_LEG) ** k
        md.append(f"- **{k} same-team legs:** correlation is worth "
                  f"**{gain:+.1%}** over independent pricing, against a "
                  f"compounded hold of **{tax:.1%}** → "
                  + ("**still negative**, by "
                     f"{gain - tax:+.1%}" if gain < tax else
                     f"**clears the hold** by {gain - tax:+.1%}")
                  + f" _(n={n})_")
    # THE ANSWER, in the only units that matter: what the best available
    # structure actually returns on our own legs.
    md += ["", "### The best structure available, priced out", "",
           f"_Legs are our posted hit props: **{PROP_RATE:.1%}** at "
           f"**{PROP_PRICE:+d}**. `correlated` applies the same-team lift "
           "measured above. The band is there because that lift is not "
           "significant (p around 0.10), so the honest read spans "
           "\"the lift is real\" to \"the lift is zero\"._", "",
           "| structure | true P(all hit) | price needs | ROI |",
           "|---|---|---|---|"]
    for k in (2, 3):
        o, e, n = lift(rows, rates, k, True)
        null = []
        for pm in perms:
            po, pe, _n = lift(rows, rates, k, True, outcomes=pm)
            if po is not None and pe:
                null.append(po / pe)
        if not (o and e and null):
            continue
        cal = (o / e) / st.mean(null)
        dec = _dec(PROP_PRICE) ** k
        need = 1 / dec
        for name, mult in ((f"{k} legs, independent (lift = 1.00)", 1.0),
                           (f"{k} legs, SAME TEAM (lift = {cal:.3f})", cal)):
            p_all = PROP_RATE ** k * mult
            md.append(f"| {name} | {p_all:.2%} | {need:.2%} | "
                      f"**{p_all / need - 1:+.1%}** |")
    md += ["",
           "_So the best structure this data supports - the shortest parlay, "
           "same lineup, correlation credited in full - is still negative. "
           "Correlation is a real effect with the right sign and it is simply "
           "not large enough to cover both the compounding hold and the "
           "deficit the legs start with._", "",
           "_Note this cuts against how the props are currently posted: three "
           "props from BOTH lineups is right for three SINGLE bets, since it "
           "spreads the risk, and wrong for a parlay, which wants the "
           "correlated same-team legs. They are different products and the "
           "board posts singles._"]
    md += ["",
           "_And that comparison is the generous version, because it credits "
           "the legs with a fair price to begin with. Our posted props hit "
           f"{PROP_RATE:.1%} against a {abs(PROP_PRICE) / (abs(PROP_PRICE) + 100):.1%} "
           "break-even, so each leg starts about 5.5 points behind before any "
           "correlation is applied. A lift has to cover the hold AND that "
           "deficit, compounded._",
           "",
           "_One more thing a book does: most price same-game parlays WITH a "
           "correlation adjustment already. Where that is true the lift below "
           "is in the price and there is nothing left to take. The edge, if it "
           "exists at all, lives only where legs are combined at independent "
           "pricing._", ""]
    return md


def build() -> str:
    md = ["# Structuring a parlay with the data we have", "",
          "_Read-only. Stakes nothing, changes no pick, enters no ledger._", ""]
    md += hold_block()
    md += payout_table()
    try:
        rows, rec = build_rows()
    except (OSError, ValueError) as exc:
        return "\n".join(md + [f"_Correlation test unavailable: {exc}_", ""])
    rates, measure = split_rates(rows)
    md += [f"- hitter-games with a plate appearance: **{len(rows)}** across "
           f"**{len({r[0] for r in rows})}** games, "
           f"**{len(rec)}** hitters",
           f"- rates built from held-out halves: **{len(rates)}** hitters; "
           f"measured on **{len(measure)}** hitter-games across "
           f"**{len({r[0] for r in measure})}** games", ""]
    md += correlation_block(measure, rates)
    md += verdict(measure, rates)
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    text = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
