"""
When the real-money venues disagree with the public ticket count, who wins -
and does it matter whether the money is on the favourite or the dog?

THE SETUP
Two different things get called "where the money is":

  PUBLIC  - percentage of BETS (covers.com consensus, VSiN bets). This is the
            Scores & Odds style number: a headcount, dominated by small tickets.
  MONEY   - actual cash at risk (Polymarket resting depth, Kalshi traded
            volume). Fewer participants, much larger average size.

Most games they point the same way. The question here is the minority where they
split, because that is where the headcount and the cash are telling different
stories - and one of them is wrong.

THE CUT THAT MATTERS
Disagreement alone is not directional. "Money on the dog, public on the
favourite" and "money on the favourite, public on the dog" are opposite
situations and could easily have opposite edges, so they are never pooled here.
Each is reported separately, for each venue, with the favourite's raw win rate
alongside - so it is visible whether any result is just the favourite winning.

Controls on the headline cell: holdout split, day-block bootstrap CI, and a
market-calibrated null. Writes output/money_vs_public.md. Reporting only.
"""

from __future__ import annotations

import logging
import random
from collections import Counter
from pathlib import Path

from . import grade
from .pregame_money import HOLDOUT_FROM, MIN_N, _implied
from .source_agreement import collect

log = logging.getLogger("money_vs_public")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

PUBLIC_SRC = ["covers", "vsin_bets"]          # headcount of tickets
MONEY_SRC = ["pm_book", "kalshi_money"]       # cash at risk


def _public_side(r: dict) -> str | None:
    """The ticket-count side. Both public sources must agree, else no read -
    a split public is not a public opinion."""
    votes = {r["sides"][s] for s in PUBLIC_SRC if s in r["sides"]}
    return votes.pop() if len(votes) == 1 else None


def _fav(r: dict) -> str | None:
    """The price favourite."""
    a, h = r["price"].get("away"), r["price"].get("home")
    if not isinstance(a, int) or not isinstance(h, int):
        return None
    ia, ih = _implied(a), _implied(h)
    if ia == ih:
        return None
    return "away" if ia > ih else "home"


def _devig(r: dict, side: str) -> float:
    ia, ih = _implied(r["price"]["away"]), _implied(r["price"]["home"])
    tot = ia + ih
    if tot <= 0:
        return 0.5
    return (ia if side == "away" else ih) / tot


def _rows(recs, chooser) -> list:
    out = []
    for r in recs:
        s = chooser(r)
        if s not in ("away", "home"):
            continue
        out.append({"won": r["win_side"] == s, "odds": r["price"][s],
                    "date": r["date"], "p": _devig(r, s)})
    return out


def _roi(rows) -> float:
    if not rows:
        return 0.0
    u = sum(grade.american_profit(x["odds"]) if x["won"] else -1 for x in rows)
    return u / len(rows)


def _fmt(rows) -> str:
    if not rows:
        return "—"
    w = sum(1 for x in rows if x["won"])
    u = sum(grade.american_profit(x["odds"]) if x["won"] else -1 for x in rows)
    tag = "" if len(rows) >= MIN_N else " _(thin)_"
    return (f"{w}-{len(rows)-w} ({w/len(rows):.0%}) · {u:+.1f}u · "
            f"**{u/len(rows):+.1%}** (n={len(rows)}){tag}")


def _cells(recs, venue: str) -> dict:
    """Split disagreement games by whether the money side is fav or dog."""
    out = {"money_fav": [], "money_dog": [], "agree": []}
    for r in recs:
        pub, mon, fav = _public_side(r), r["sides"].get(venue), _fav(r)
        if not pub or not mon or not fav:
            continue
        if pub == mon:
            out["agree"].append(r)
        elif mon == fav:
            out["money_fav"].append(r)
        else:
            out["money_dog"].append(r)
    return out


def _controls(rows, label: str) -> list[str]:
    if len(rows) < MIN_N:
        return [f"_{label}: n={len(rows)}, too thin for controls._", ""]
    rng = random.Random(11)
    actual = _roi(rows)

    pre = [x for x in rows if x["date"] < HOLDOUT_FROM]
    post = [x for x in rows if x["date"] >= HOLDOUT_FROM]

    beats = 0
    for _ in range(4000):
        u = 0.0
        for x in rows:
            u += grade.american_profit(x["odds"]) if rng.random() < x["p"] else -1
        if u / len(rows) >= actual:
            beats += 1

    by_day: dict = {}
    for x in rows:
        by_day.setdefault(x["date"], []).append(x)
    days = list(by_day)
    rois = []
    for _ in range(2000):
        samp = []
        for _ in days:
            samp.extend(by_day[rng.choice(days)])
        rois.append(_roi(samp))
    rois.sort()

    return [f"**Controls — {label}**", "",
            f"- in-sample: **{_roi(pre):+.1%}** (n={len(pre)}) · "
            f"holdout: **{_roi(post):+.1%}** (n={len(post)})",
            f"- market-calibrated null: **p = {beats/4000:.3f}**",
            f"- day-block bootstrap 95% CI: **{rois[50]:+.1%} to {rois[-50]:+.1%}**",
            ""]


def build() -> str:
    recs, _diag = collect()
    usable = [r for r in recs if _public_side(r) and _fav(r)]

    md = ["# Real money vs public tickets — who is right?", "",
          "_PUBLIC = share of BETS (covers consensus, VSiN) — the Scores & Odds "
          "style headcount, dominated by small tickets. MONEY = cash at risk "
          "(Polymarket resting depth, Kalshi traded volume). The interesting "
          "games are where the headcount and the cash disagree._", "",
          "## Coverage", "",
          f"- games with a clean public read and a price: **{len(usable)}**", ""]

    if len(usable) < MIN_N:
        return "\n".join(md + ["Too few games to read.", ""])

    # baseline: how often does the favourite win at all?
    fav_rows = _rows(usable, _fav)
    md += [f"_Baseline — backing the favourite in every one of these games: "
           f"{_fmt(fav_rows)}._", ""]

    for venue in MONEY_SRC + ["both"]:
        if venue == "both":
            sub = [r for r in usable
                   if r["sides"].get("pm_book")
                   and r["sides"].get("pm_book") == r["sides"].get("kalshi_money")]
            cells = _cells(sub, "pm_book")
            title = "Polymarket AND Kalshi agree with each other"
        else:
            cells = _cells(usable, venue)
            title = {"pm_book": "Polymarket order book",
                     "kalshi_money": "Kalshi traded volume"}[venue]

        md += [f"## {title}", "",
               f"- money and public agree: **{len(cells['agree'])}**",
               f"- disagree, money on the FAVOURITE: **{len(cells['money_fav'])}**",
               f"- disagree, money on the DOG: **{len(cells['money_dog'])}**", "",
               "| case | back the MONEY side | back the PUBLIC side |",
               "|---|---|---|"]
        mv = venue if venue != "both" else "pm_book"
        md += [
            f"| they agree | {_fmt(_rows(cells['agree'], lambda r: r['sides'][mv]))} | — |",
            f"| money on FAVOURITE, public on dog | "
            f"{_fmt(_rows(cells['money_fav'], lambda r: r['sides'][mv]))} | "
            f"{_fmt(_rows(cells['money_fav'], _public_side))} |",
            f"| money on DOG, public on favourite | "
            f"{_fmt(_rows(cells['money_dog'], lambda r: r['sides'][mv]))} | "
            f"{_fmt(_rows(cells['money_dog'], _public_side))} |", ""]

        # favourite win rate inside each disagreement bucket
        for key, lab in (("money_fav", "money on favourite"),
                         ("money_dog", "money on dog")):
            sub2 = cells[key]
            if sub2:
                fw = sum(1 for r in sub2 if r["win_side"] == _fav(r))
                md.append(f"_Favourite win rate, {lab}: "
                          f"**{fw}/{len(sub2)} ({fw/len(sub2):.0%})**._")
        md.append("")

    # controls on the two disagreement directions, using the widest venue
    cells = _cells(usable, "kalshi_money")
    md += ["## Controls on the disagreement cells", "",
           "_Kalshi is used here because it has the widest coverage. Both "
           "directions get controls, so a good-looking cell cannot be reported "
           "without its holdout and CI._", ""]
    md += _controls(_rows(cells["money_fav"], lambda r: r["sides"]["kalshi_money"]),
                    "money on favourite → back the money")
    md += _controls(_rows(cells["money_dog"], lambda r: r["sides"]["kalshi_money"]),
                    "money on dog → back the money")
    md += _controls(_rows(cells["money_dog"], _public_side),
                    "money on dog → back the public favourite")

    md.append("_A cell only becomes a rule if it survives its holdout and its CI "
              "clears zero. Two disagreement directions x three venues is six "
              "chances to find a good-looking number by accident._")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "money_vs_public.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
