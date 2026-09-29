"""
Which withdrawals does the fade rule live on - and do they still happen?

WHAT PROMPTED THIS, AND A CORRECTION TO MY OWN FIRST GUESS
I assumed fade_profile's numbers were contaminated by the uncut book_metrics
fixed on 2026-09-29. They are not. fade_profile reads `pick_criteria` out of
COMMITTED git versions of each board, and those boards were built live, when the
day file held only pre-game readings. The look-ahead only ever affected backtests
that recompute book_metrics on a completed file. The fade evidence is clean.

THE REAL PROBLEM, WHICH IS BIGGER
The book-confirm gate was REMOVED from the live rule on 2026-09-29. A fade is
triggered by the consensus rule withdrawing a pick, so the fade rule's input is
the set of withdrawals - and two of the five withdrawal reasons were book-gate
reasons:

    no pre-game order-book read yet
    order book does not confirm the consensus side

Those can no longer occur. So however the fade rule performed historically, its
FORWARD population is a different population, and the +15.2% over 144
withdrawals may describe a distribution that no longer exists. That is not a
pocket-hunt; it is asking whether a live rule's evidence still applies to it.

HOW THE REASON IS RECOVERED
Not recomputed - read. consensus.reject_reason() is written into every
stay_away game's pick_criteria at board time, so the version immediately AFTER a
withdrawal records exactly which gate stopped passing, as judged live. Walking
the committed versions therefore gives the withdrawal reason with no
recomputation and no hindsight.

WHAT IS REPORTED
  every withdrawal reason, its share, and what fading it returned
  the split that matters: reasons that STILL happen against reasons that cannot
  and, since removing the gate also widens the pool, how many withdrawals the
  new rule would have produced at all

Writes output/fade_reason.md.
"""

from __future__ import annotations

import glob
import logging
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import grade, mlb_api
from .fade_profile import _at, _versions
from .pregame_money import _implied

log = logging.getLogger("fade_reason")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 10000

# reject_reason() phrasings, mapped to the gate that produced them
GATES = [("handle/ticket", "no handle/ticket agreement", True),
         ("no public read", "no public majority read", True),
         ("no order-book read", "no pre-game order-book read", False),
         ("book did not confirm", "order book does not confirm", False),
         ("line moved wrong way", "no price discount", True)]


def _classify(reason: str) -> tuple[str, bool]:
    """(label, still_possible) for a recorded reject reason."""
    r = (reason or "").lower()
    for label, needle, live in GATES:
        if needle.lower() in r:
            return label, live
    return "other/unrecorded", True


def collect() -> tuple[list[dict], int]:
    """(rows, boards_with_history). The second value distinguishes "no
    withdrawals" from "no git history" - a shallow clone yields one version per
    board, which makes every pick look like it was never withdrawn, and reporting
    that as "too few withdrawals" hides a broken checkout as a finding."""
    rows = []
    with_history = 0
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        rel = f"output/picks_{date}.json"
        shas = _versions(rel)
        if len(shas) < 2:
            continue
        with_history += 1
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        hist: dict = defaultdict(list)
        meta: dict = {}
        for sha in shas:
            day = _at(sha, rel)
            if not day:
                continue
            for g in day.get("games", []):
                pk = g.get("game_pk")
                pc = g.get("pick_criteria") or {}
                hist[pk].append({
                    "pick": pc.get("play") == "pick",
                    "bet": pc.get("bet_team"),
                    "reason": pc.get("reason"),
                    "source": pc.get("source"),
                })
                if pk not in meta or pc.get("play") == "pick":
                    meta[pk] = {"matchup": g.get("matchup"),
                                "adv": pc.get("advantage_team"),
                                "a_ml": pc.get("advantage_moneyline"),
                                "o_ml": pc.get("opponent_moneyline")}
        for pk, seq in hist.items():
            picked = [i for i, x in enumerate(seq) if x["pick"]]
            if not picked or picked[-1] == len(seq) - 1:
                continue                      # never picked, or never withdrawn
            i = picked[-1]
            # a fade of a fade is a re-assertion, not a withdrawal
            if seq[i].get("source") == "fade":
                continue
            after = seq[i + 1]
            m, res = meta.get(pk) or {}, results.get(pk)
            bet = seq[i]["bet"]
            if not res or not res.get("final") or not res.get("winner") or not bet:
                continue
            if " @ " not in (m.get("matchup") or ""):
                continue
            away, home = m["matchup"].split(" @ ")
            if bet not in (away, home):
                continue
            other = home if bet == away else away
            odds = m["o_ml"] if bet == m.get("adv") else m.get("a_ml")
            if not isinstance(odds, int):
                continue
            label, live = _classify(after.get("reason"))
            tot = _implied(odds) + _implied(
                m["a_ml"] if bet == m.get("adv") else m["o_ml"] or 0)
            rows.append({
                "date": date, "reason": label, "still_possible": live,
                "fade_team": other, "odds": odds,
                "won": res["winner"] == other,
                "p": (_implied(odds) / tot) if tot > 0 else 0.5,
            })
    return rows, with_history


def _roi(rs) -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r["odds"]) if r["won"] else -1
               for r in rs) / len(rs)


def _fmt(rs) -> str:
    if not rs:
        return "—"
    w = sum(1 for r in rs if r["won"])
    return f"{w}-{len(rs)-w} · **{_roi(rs):+.1%}** (n={len(rs)})"


def _boot(rs) -> tuple[float, float]:
    by = defaultdict(list)
    for r in rs:
        by[r["date"]].append(grade.american_profit(r["odds"]) if r["won"] else -1)
    days = sorted(by)
    if len(days) < 5:
        return (float("nan"), float("nan"))
    rng = random.Random(3939)
    out = []
    for _ in range(TRIALS):
        v = []
        for _ in days:
            v += by[days[rng.randrange(len(days))]]
        if v:
            out.append(st.mean(v) * 100)
    out.sort()
    return out[int(.025 * len(out))], out[int(.975 * len(out))]


def build() -> str:
    rows, with_history = collect()
    md = ["# Which withdrawals does the fade rule live on, and do they still "
          "happen?", "",
          "_First, a correction to my own guess: `fade_profile` is **not** "
          "contaminated by the look-ahead fixed on 2026-09-29. It reads "
          "`pick_criteria` out of committed board versions, and those boards were "
          "built live, when the day file held only pre-game readings. The "
          "look-ahead only affected backtests that recompute `book_metrics` on a "
          "completed file._", "",
          "_The real problem is larger. The book-confirm gate was REMOVED from "
          "the live rule, and a fade is triggered by a withdrawal — so two of the "
          "five withdrawal reasons (`no order-book read` and `book did not "
          "confirm`) can no longer occur. However the fade rule performed, its "
          "forward population is a different population._", "",
          "_The reason is read, not recomputed: `reject_reason()` is written into "
          "every stay-away game at board time, so the version immediately after a "
          "withdrawal records which gate stopped passing, as judged live._", "",
          f"- withdrawals reconstructed with an outcome: **{len(rows)}**", ""]
    if with_history == 0:
        return "\n".join(md + [
            "**No board history available — this is a broken run, not a result.** "
            "`_versions()` found fewer than two committed versions of every board, "
            "which happens when the checkout is shallow. The workflow needs "
            "`fetch-depth: 0`.", ""])
    if len(rows) < 40:
        return "\n".join(md + [
            f"Too few withdrawals to judge ({len(rows)} across {with_history} "
            "boards with history).", ""])

    md += ["## By the gate that caused the withdrawal", "",
           "| withdrawal reason | still possible? | fading it | 95% CI |",
           "|---|---|---|---|"]
    by = defaultdict(list)
    for r in rows:
        by[r["reason"]].append(r)
    for lab in sorted(by, key=lambda k: -len(by[k])):
        rs = by[lab]
        lo, hi = _boot(rs)
        md.append(f"| {lab} | {'yes' if rs[0]['still_possible'] else '**NO — gate removed**'} "
                  f"| {_fmt(rs)} | " + ("—" if lo != lo else f"{lo:+.1f}% to {hi:+.1f}%") + " |")
    md.append("")

    live = [r for r in rows if r["still_possible"]]
    dead = [r for r in rows if not r["still_possible"]]
    md += ["## The split that decides it", "",
           "| population | fading it | 95% CI |", "|---|---|---|"]
    for lab, rs in (("withdrawals that STILL happen", live),
                    ("withdrawals that can no longer happen", dead)):
        lo, hi = _boot(rs)
        md.append(f"| {lab} | {_fmt(rs)} | "
                  + ("—" if lo != lo else f"{lo:+.1f}% to {hi:+.1f}%") + " |")
    md.append("")
    if dead:
        md += [f"- **{len(dead)/len(rows):.0%} of the fade rule's historical "
               f"triggers came from the book gate**, which no longer exists", ""]
    if live and dead:
        md += [f"- so the forward-relevant record is **{_fmt(live)}**, not the "
               f"pooled **{_fmt(rows)}** the rule was shipped on", ""]

    lo, hi = _boot(live)
    md += ["## The call", ""]
    if lo == lo and lo > 0:
        md += ["- **the surviving population is still profitable** with an "
               "interval clear of zero, so the fade rule keeps running on a "
               "narrower but intact base", ""]
    elif live:
        md += [f"- the surviving population returns **{_roi(live):+.1%}** with an "
               f"interval of {lo:+.1f}% to {hi:+.1f}%, which spans zero. The fade "
               "rule is then running on evidence that no longer describes its "
               "input, and the honest options are to restrict it to the reasons "
               "that still occur and re-baseline the expectation, or to pause it "
               "until the new population has a record of its own", ""]
    md += ["- either way the historical pooled figure should stop being quoted "
           "for it: a third of its triggers are gone", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "fade_reason.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
