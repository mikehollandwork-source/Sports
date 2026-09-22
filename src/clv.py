"""
Closing line value: did the market move toward our picks after we made them?

WHY THIS AND NOT ANOTHER SCAN
Every dead end this session died of the same cause - not enough games. Cells of
90, confidence intervals 40 points wide, split-halves flipping sign. ROI is an
extremely noisy way to measure a betting edge: one extra win at +150 moves a
15-game cell by 16 points.

Closing line value does not have that problem. It asks a different question of
the same picks - not "did it win" but "did the price move our way after we
bought" - and the answer is a continuous number per pick with roughly a fifth
the variance of a win/loss. It is the professional standard for exactly this
reason, and with ~250 picks it can be measured to useful precision where ROI
cannot be.

WHAT IT TESTS THAT NOTHING ELSE DOES
The live rule REQUIRES that the line has already moved against the side we back
(>=1.0%). That is the load-bearing assumption in the whole system, and it has
two completely different readings:

    a DISCOUNT   the move overshot, the price reverts, we bought the bottom
    a WARNING    the move is information, it keeps going, we caught a knife

Backtest ROI cannot separate these, because it only sees the final result. CLV
separates them directly: positive CLV means the market came back toward us after
we bet, negative means it kept walking away.

HOW THE PRICES ARE RECOVERED
The board is stateless and committed to git on every hourly refresh, so every
version of every day's board survives in history. For each pick, the ENTRY price
is its price in the first version where the pick appeared - the moment we would
have bet it - and the CLOSING price is its price in the last version, which
`_lock_started_games` freezes ~15 minutes before first pitch. Both sides'
moneylines are stored, so every price is de-vigged before comparison:

    p = implied(side) / (implied(side) + implied(opponent))
    CLV = p_closing - p_entry          in probability points

Positive CLV means the side shortened after we bought it.

THE BASELINE, WHICH IS WHY THE FIRST VERSION OF THIS WAS WRONG
A control is computed alongside: the same measurement on every home team on the
board, picked or not. It was built as a pass/fail guard against a broken
reconstruction, on the assumption that the market does not systematically drift
toward home teams and the control would therefore sit at zero.

It does not sit at zero - it comes out around +0.25 pp - and prices parse
correctly, so this is not a broken pipeline. As first pitch approaches the
book's overround tightens, so a de-vigged probability measured at entry and
again at the close does not share a baseline. Every side of every game inherits
that drift.

That makes the control a BASELINE TO SUBTRACT, not a threshold to clear, and it
is the whole finding: the first version of this file compared the picks' +0.32
pp against zero, called the interval clear, and reported closing line value that
does not exist. The real quantity is the difference, and its interval has to be
bootstrapped as a difference.

Games whose first and last version are the same commit are excluded, since their
CLV is mechanically zero.

Writes output/clv.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
import subprocess
from collections import defaultdict
from pathlib import Path

from . import grade, mlb_api
from .pregame_money import HOLDOUT_FROM, _implied

log = logging.getLogger("clv")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPO = Path(__file__).resolve().parent.parent
TRIALS = 4000


def _versions(rel: str) -> list[str]:
    """Every commit that touched this board file, oldest first."""
    try:
        out = subprocess.run(["git", "log", "--format=%H", "--all", "--reverse",
                              "--", rel], cwd=REPO, capture_output=True,
                             text=True, timeout=180)
        return [s for s in out.stdout.split() if s]
    except Exception as exc:
        log.warning("git log failed for %s: %s", rel, exc)
        return []


def _at(sha: str, rel: str) -> dict | None:
    try:
        out = subprocess.run(["git", "show", f"{sha}:{rel}"], cwd=REPO,
                             capture_output=True, text=True, timeout=120)
        if out.returncode:
            return None
        return json.loads(out.stdout)
    except Exception:
        return None


def _devig(side_ml: int, opp_ml: int) -> float | None:
    a, b = _implied(side_ml), _implied(opp_ml)
    return (a / (a + b)) if (a + b) > 0 else None


def _sides(g: dict) -> dict:
    """{team: moneyline} for both sides of one board game, or {}."""
    m = g.get("matchup") or ""
    pc = g.get("pick_criteria") or {}
    adv = pc.get("advantage_team")
    a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
    if " @ " not in m or not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
        return {}
    away, home = m.split(" @ ")
    if adv not in (away, home):
        return {}
    return {adv: a_ml, (home if adv == away else away): o_ml}


def scan_date(date: str) -> dict:
    """Walk every committed version of one board.

    {game_pk: {matchup, home, away, entry: {team: ml}, close: {team: ml},
               pick, pick_entry_ml, pick_source, versions}}
    `entry` is the FIRST version seen, `close` the LAST."""
    rel = f"output/picks_{date}.json"
    shas = _versions(rel)
    if len(shas) < 2:
        return {}
    out: dict = {}
    for sha in shas:
        day = _at(sha, rel)
        if not day:
            continue
        for g in day.get("games", []):
            pk = g.get("game_pk")
            sides = _sides(g)
            if not pk or not sides:
                continue
            m = g["matchup"]
            away, home = m.split(" @ ")
            rec = out.setdefault(pk, {
                "matchup": m, "home": home, "away": away,
                "entry": dict(sides), "close": dict(sides),
                "pick": None, "pick_entry": None, "pick_source": None,
                "pick_at": None, "versions": 0})
            rec["close"] = dict(sides)          # last one wins
            rec["versions"] += 1
            pc = g.get("pick_criteria") or {}
            if pc.get("play") == "pick" and rec["pick"] is None:
                bt = pc.get("bet_team")
                bml = pc.get("bet_moneyline")
                if bt in sides and isinstance(bml, int):
                    rec["pick"] = bt
                    # the price at the moment the pick first appeared, and WHICH
                    # version that was - a pick that first appears in the final
                    # version has no interval left to measure
                    rec["pick_entry"] = dict(sides)
                    rec["pick_at"] = rec["versions"]
                    rec["pick_source"] = pc.get("source") or "rule"
    return {pk: r for pk, r in out.items() if r["versions"] >= 2}


def collect() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
        except Exception:
            results = {}
        for pk, r in scan_date(date).items():
            res = results.get(pk) or {}
            rows.append({"date": date, "game_pk": pk, **r,
                         "winner": res.get("winner") if res.get("final") else None})
    return rows


def _clv(entry: dict, close: dict, team: str) -> float | None:
    """Probability points the market moved TOWARD `team` after entry."""
    others = [t for t in entry if t != team]
    if not others or team not in entry or team not in close:
        return None
    o = others[0]
    if o not in close:
        return None
    pe, pc_ = _devig(entry[team], entry[o]), _devig(close[team], close[o])
    if pe is None or pc_ is None:
        return None
    return (pc_ - pe) * 100


def _summary(vals: list[float], label: str) -> str:
    if not vals:
        return f"| {label} | — | — | — | — |"
    beat = sum(1 for v in vals if v > 0) / len(vals)
    return (f"| {label} | **{st.mean(vals):+.2f} pp** | {st.median(vals):+.2f} pp "
            f"| {beat:.0%} | {len(vals)} |")


def _day_boot(pairs: list[tuple[str, float]]) -> tuple[float, float]:
    """Day-block bootstrap CI on the mean: resample DAYS, not picks, because
    same-day games share a market state."""
    by_day = defaultdict(list)
    for d, v in pairs:
        by_day[d].append(v)
    days = list(by_day)
    if len(days) < 5:
        return (float("nan"), float("nan"))
    rng = random.Random(77)
    out = []
    for _ in range(TRIALS):
        vals: list[float] = []
        for _ in days:
            vals += by_day[days[rng.randrange(len(days))]]
        if vals:
            out.append(st.mean(vals))
    out.sort()
    return out[int(.025 * len(out))], out[int(.975 * len(out))]


def _day_boot_diff(a: list[tuple[str, float]],
                   b: list[tuple[str, float]]) -> tuple[float, float]:
    """Day-block bootstrap CI on mean(a) - mean(b).

    The control is not zero (see the guard), so the quantity of interest is a
    DIFFERENCE, and its interval has to be bootstrapped as a difference rather
    than read off the interval of `a` alone. Days are resampled jointly so the
    two populations stay paired within a day."""
    ga, gb = defaultdict(list), defaultdict(list)
    for d, v in a:
        ga[d].append(v)
    for d, v in b:
        gb[d].append(v)
    days = sorted(set(ga) | set(gb))
    if len(days) < 5:
        return (float("nan"), float("nan"))
    rng = random.Random(311)
    out = []
    for _ in range(TRIALS):
        va, vb = [], []
        for _ in days:
            d = days[rng.randrange(len(days))]
            va += ga.get(d, [])
            vb += gb.get(d, [])
        if va and vb:
            out.append(st.mean(va) - st.mean(vb))
    if not out:
        return (float("nan"), float("nan"))
    out.sort()
    return out[int(.025 * len(out))], out[int(.975 * len(out))]


def build() -> str:
    rows = collect()
    md = ["# Closing line value — did the market come to us?", "",
          "_Not \"did it win\" but \"did the price move our way after we "
          "bought\". A continuous number per pick with roughly a fifth the "
          "variance of a win/loss, which is why it is the professional "
          "standard and why it can be measured on the sample we have when ROI "
          "cannot._", "",
          f"- board games with at least two committed versions: **{len(rows)}**", ""]
    if len(rows) < 100:
        return "\n".join(md + ["Not enough reconstructed board history.", ""])

    carried = [r for r in rows if r["pick"] and r["pick_entry"]]
    # A pick that first appears in the LAST committed version was made AT the
    # close, so there is no interval left to measure and its CLV would be a
    # mechanical zero. Counting those as zeroes would drag the mean toward
    # nothing and manufacture a false "no edge" - the local dry-run hit exactly
    # this, so they are excluded and counted instead.
    picks = [r for r in carried if r["pick_at"] < r["versions"]]
    at_close = len(carried) - len(picks)
    room = [r["versions"] - r["pick_at"] for r in picks]
    md += [f"- of those, games that carried a pick: **{len(carried)}**",
           f"- measurable (at least one board version after the pick "
           f"appeared): **{len(picks)}**",
           f"- excluded because the pick first appeared in the final version, "
           f"leaving no interval: **{at_close}**"]
    if room:
        md += [f"- board refreshes between entry and close, median: "
               f"**{int(st.median(room))}**"]
    md += [""]

    # --- the guard, first, because nothing else counts if it fails ---------
    home_clv = [v for r in rows
                if (v := _clv(r["entry"], r["close"], r["home"])) is not None]
    md += ["## The baseline (read this before anything else)", "",
           "_The same measurement applied to every home team, picked or not. "
           "It was built as a pass/fail guard on the assumption it would come "
           "out at zero. It does not, and that turned out to be the important "
           "result rather than a failure: whatever the board-wide drift is, "
           "every pick inherits it, so it is a baseline to subtract and not a "
           "threshold to clear._", "",
           "| population | mean CLV | median | beat the close | n |",
           "|---|---|---|---|---|",
           _summary(home_clv, "every home team (control)"), ""]
    cm = st.mean(home_clv) if home_clv else 0.0
    md += [(f"_Control mean is **{cm:+.2f} pp**, not zero. That is not a "
            "broken pipeline - prices parse correctly - but a systematic "
            "drift that applies to EVERY side on the board: as first pitch "
            "approaches the book's overround tightens, so a de-vigged "
            "probability measured at entry and again at the close does not "
            "have the same baseline. Whatever its cause, it is the floor "
            "under any number in this report, and the only meaningful "
            "quantity is a pick's CLV MINUS this._" if abs(cm) > 0.05 else
            "_Control is at zero, so raw CLV can be read directly._"), ""]

    # --- the headline ------------------------------------------------------
    rule = [r for r in picks if (r["pick_source"] or "rule") != "fade"]
    fades = [r for r in picks if r["pick_source"] == "fade"]
    rule_clv = [(r["date"], v) for r in rule
                if (v := _clv(r["pick_entry"], r["close"], r["pick"])) is not None]
    fade_clv = [(r["date"], v) for r in fades
                if (v := _clv(r["pick_entry"], r["close"], r["pick"])) is not None]
    # the side we did NOT pick in games we rejected: did we select the movers?
    rej = [r for r in rows if not r["pick"]]
    rej_home = [v for r in rej
                if (v := _clv(r["entry"], r["close"], r["home"])) is not None]

    md += ["## Our picks", "",
           "| population | mean CLV | median | beat the close | n |",
           "|---|---|---|---|---|",
           _summary([v for _, v in rule_clv], "**consensus-rule picks**"),
           _summary([v for _, v in fade_clv], "fade book (separate)"),
           _summary(rej_home, "rejected games, home side (reference)"), ""]
    # Measurement resolution: an exactly-zero CLV means the stored price did
    # not move at all between entry and close. Those are real, but a large
    # share of them attenuates the mean toward zero in BOTH directions, so the
    # share is reported rather than left to hide inside the average.
    if rule_clv:
        z = sum(1 for _, v in rule_clv if v == 0.0)
        md += [f"- picks whose price did not move at all between entry and "
               f"close: **{z}/{len(rule_clv)}** ({z/len(rule_clv):.0%})"]
        if z / len(rule_clv) > 0.35:
            md += ["", "_More than a third of picks show no movement at all, "
                   "which attenuates the mean toward zero in both directions. "
                   "Read the non-zero subset below alongside the headline._"]
            nz = [v for _, v in rule_clv if v != 0.0]
            md += ["", "| population | mean CLV | median | beat the close | n |",
                   "|---|---|---|---|---|",
                   _summary(nz, "rule picks, price actually moved"), ""]
        else:
            md += [""]

    if rule_clv:
        ctrl_pairs = [(r["date"], v) for r in rows
                      if (v := _clv(r["entry"], r["close"], r["home"])) is not None]
        lo, hi = _day_boot_diff(rule_clv, ctrl_pairs)
        mean = st.mean([v for _, v in rule_clv]) - cm
        md += [f"- rule picks **{st.mean([v for _, v in rule_clv]):+.2f} pp** "
               f"minus the board-wide drift **{cm:+.2f} pp** = "
               f"**{mean:+.2f} pp** of actual closing line value",
               f"- day-block bootstrap 95% CI on that DIFFERENCE: "
               f"**{lo:+.2f} to {hi:+.2f} pp**", ""]
        if lo > 0:
            verdict = ("**Positive CLV against the control, interval excluding "
                       "zero.** The market moves toward our side faster than it "
                       "moves toward an arbitrary side. That is an edge measured "
                       "independently of whether the picks won, and it means the "
                       "line-against gate is buying a DISCOUNT: the adverse move "
                       "overshoots and reverts.")
        elif hi < 0:
            verdict = ("**Negative CLV against the control, interval excluding "
                       "zero.** The market keeps moving AWAY from our side "
                       "relative to an arbitrary side. The line-against gate is "
                       "a WARNING being read as a discount - we are buying into "
                       "information, not value, and the ROI so far is a hot "
                       "streak rather than an edge. This would argue for "
                       "dropping the gate.")
        else:
            verdict = (f"**No closing line value.** Once the board-wide drift "
                       f"is subtracted the picks are worth {mean:+.2f} pp with "
                       "an interval spanning zero. The market does not come to "
                       "meet these picks any faster than it comes to meet an "
                       "arbitrary side of an arbitrary game.\n\nThat does not "
                       "make the ROI fake, but it removes the independent "
                       "confirmation it was hoped this would provide: the "
                       "record still rests on the record. It also leaves the "
                       "discount-versus-warning question open rather than "
                       "settling it - the line-against gate is buying "
                       "something the closing price does not recognise either "
                       "way.")
        md += [verdict, ""]

    # --- does CLV predict the result on our own games? ---------------------
    graded = [r for r in rule if r["winner"]
              and _clv(r["pick_entry"], r["close"], r["pick"]) is not None]
    if len(graded) >= 40:
        # key= is required, not stylistic: exact-zero CLVs are common (the
        # price simply did not move), and on a tie Python falls back to
        # comparing the dicts, which raises. The 4-pick dry-run never tied.
        vals = sorted(((_clv(r["pick_entry"], r["close"], r["pick"]), r)
                       for r in graded), key=lambda t: t[0])
        third = len(vals) // 3
        groups = [("worst CLV third", vals[:third]),
                  ("middle third", vals[third:2 * third]),
                  ("best CLV third", vals[2 * third:])]
        md += ["## Does CLV predict the result on our own picks?", "",
               "_If the picks that the market moved toward also won more, CLV "
               "is validated as the low-variance stand-in for ROI, and every "
               "future question can be answered on a fraction of the sample._",
               "", "| CLV third | mean CLV | record | ROI |", "|---|---|---|---|"]
        for label, grp in groups:
            if not grp:
                continue
            w = sum(1 for _, r in grp if r["winner"] == r["pick"])
            u = sum(grade.american_profit(r["pick_entry"][r["pick"]])
                    if r["winner"] == r["pick"] else -1 for _, r in grp)
            md.append(f"| {label} | {st.mean([c for c, _ in grp]):+.2f} pp | "
                      f"{w}-{len(grp)-w} | **{u/len(grp):+.1%}** (n={len(grp)}) |")
        md.append("")
        cl = [c for c, _ in vals]
        wn = [1.0 if r["winner"] == r["pick"] else 0.0 for _, r in vals]
        if len(set(cl)) > 1 and len(set(wn)) > 1:
            md += [f"- correlation between CLV and winning: "
                   f"**r = {st.correlation(cl, wn):+.2f}** over {len(vals)} picks",
                   "", "_A positive r says the two agree and CLV can stand in "
                   "for ROI. Near zero on this sample says only that one "
                   "season of picks cannot resolve it - it does not overturn "
                   "the mean CLV above, which is the better-powered number._",
                   ""]

    # --- time split --------------------------------------------------------
    pre = [v for d, v in rule_clv if d < HOLDOUT_FROM]
    post = [v for d, v in rule_clv if d >= HOLDOUT_FROM]
    by_month: dict = defaultdict(list)
    for d, v in rule_clv:
        by_month[d[:7]].append(v)
    md += ["## Over time", "",
           "| period | mean CLV | median | beat the close | n |",
           "|---|---|---|---|---|",
           _summary(pre, "in-sample"), _summary(post, "holdout")]
    for mth in sorted(by_month):
        md.append(_summary(by_month[mth], mth))
    md += ["", "_CLV is the one number here that does not care whether a month "
           "ran hot: a month can win at +59% on luck, but it cannot fake the "
           "market coming to meet it._", "",
           "## How to read this", "",
           "- **mean CLV** is the edge estimate; the bootstrap interval is "
           "whether it is distinguishable from zero",
           "- **beat the close** is the same thing as a rate, and 50% is the "
           "no-edge benchmark",
           "- CLV cannot be gamed by a hot streak, which is why it is worth "
           "more than the ROI table for deciding whether this system works",
           "- nothing here changes the board. It is a measurement.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "clv.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
