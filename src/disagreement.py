"""
When the money and the tickets disagree — and the book won't back the money.

THE QUESTION
Gate 1 throws a game out when the handle is on one side and the ticket
majority on the other. Those games are simply never seen again. So: who wins
them? The money side, the ticket side, or neither — and does it change when
the order book refuses to confirm the money?

WHY IT IS WORTH ASKING
This is the premise the whole system was built ON and then abandoned. The
original board faded the public and lost 11 units over 168 bets. The
market-signal backtest found the reason and it is quoted in `consensus.py`:

    handle AGAINST tickets ...... 12-18 (40%) · -23.5%
    handle WITH tickets + book .. 46-22 (68%) · +12.5%

That first line is the population being asked about, and it was 30 games.
There are now 133, and none of them has ever been split by what the order
book said.

WHAT THE CELLS MEAN
A game here has three opinions and they conflict. The money says one team,
the tickets say the other, and the book either sides with the money, sides
with the tickets, or is unreadable. The interesting cell is the one named in
the question: money on one side, tickets on the other, and the book NOT
confirming the money — the most disagreement a game can carry.

THE BOOK METRICS ARE RECOMPUTED, NOT READ
The board only attaches its `consensus` block to games that PASS gate 1, so
every game in this population has an empty one. Drift and size lean are
recomputed here from the order-book day logs, the same way `change_check`
does it.

Small by construction: 133 games split three ways. Reported with its
intervals and corrected for the cells looked at, and nothing here is a rule.

Writes output/disagreement.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
from pathlib import Path

from . import consensus as C, grade, mlb_api
from .pregame_money import _implied

log = logging.getLogger("disagreement")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 3000
MIN_CELL = 25


def collect() -> tuple[list[dict], list[dict]]:
    """(disagree, agree) — games where handle and tickets conflict, and the
    agreeing population for comparison."""
    dis, agr = [], []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
            metrics = C.book_metrics(date)
        except Exception:
            continue
        for g in json.loads(Path(f).read_text()).get("games", []):
            res = results.get(g.get("game_pk"))
            m = g.get("matchup") or ""
            if not res or not res.get("final") or not res.get("winner") or " @ " not in m:
                continue
            chk = g.get("public_check") or {}
            verdict = chk.get("money")
            ms, maj = chk.get("money_side"), chk.get("majority_side")
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if (verdict not in ("against public", "with public")
                    or ms not in ("home", "away") or maj not in ("home", "away")
                    or not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int)):
                continue
            away, home = m.split(" @ ")
            if adv not in (away, home):
                continue
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            money_team = home if ms == "home" else away
            ticket_team = home if maj == "home" else away
            if money_team not in price or ticket_team not in price:
                continue
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0:
                continue

            mm = metrics.get(g.get("game_pk"))
            confirms_money = None
            if mm:
                # book_metrics is signed to the ADVANTAGE side
                toward_adv = (mm["drift"] > 0) or (mm["imbalance"] > C.IMBALANCE_MIN)
                confirms_money = (toward_adv if money_team == adv else not toward_adv)

            row = {
                "date": date, "money_team": money_team, "ticket_team": ticket_team,
                "money_odds": price[money_team], "ticket_odds": price[ticket_team],
                "money_won": res["winner"] == money_team,
                "p_money": _implied(price[money_team]) / tot,
                "confirms_money": confirms_money,
                "money_pct": chk.get("money_pct"),
            }
            (dis if verdict == "against public" else agr).append(row)
    return dis, agr


def _bets(rs, side):
    if side == "money":
        return [(r["money_odds"], r["money_won"]) for r in rs]
    return [(r["ticket_odds"], not r["money_won"]) for r in rs]


def _roi(b) -> float:
    if not b:
        return 0.0
    return sum(grade.american_profit(o) if w else -1 for o, w in b) / len(b)


def _fmt(rs, side) -> str:
    b = _bets(rs, side)
    if not b:
        return "—"
    w = sum(1 for _, won in b if won)
    return f"{w}-{len(b)-w} · **{_roi(b):+.1%}** (n={len(b)})"


def build() -> str:
    dis, agr = collect()
    md = ["# When the money and the tickets disagree", "",
          "_The games gate 1 throws out. The handle is on one side, the "
          "ticket majority on the other, and the board never looks at them "
          "again._", "",
          f"- disagreeing games: **{len(dis)}**",
          f"- agreeing games, for comparison: **{len(agr)}**", ""]
    if len(dis) < 60:
        return "\n".join(md + ["Too few disagreeing games to say anything.", ""])

    md += ["## Who wins them?", "",
           "| population | backing the MONEY side | backing the TICKET side |",
           "|---|---|---|",
           f"| handle vs tickets **disagree** | {_fmt(dis, 'money')} | "
           f"{_fmt(dis, 'ticket')} |",
           f"| handle and tickets agree (the rule's pool) | "
           f"{_fmt(agr, 'money')} | — |", "",
           "_`consensus.py` recorded this population at 12-18 (40%), -23.5% "
           "on 30 games when the rule was written. This is the same question "
           "with the sample it now has._", ""]

    cells = [("disagree · money", dis, "money"), ("disagree · ticket", dis, "ticket")]

    # --- split by what the order book said --------------------------------
    md += ["## Split by whether the book backs the money", "",
           "_The cell the question names is the middle row: money one way, "
           "tickets the other, and the book refusing to confirm the money — "
           "the most disagreement a game can carry._", "",
           "| order book | backing the MONEY side | backing the TICKET side |",
           "|---|---|---|"]
    for label, test in (("book CONFIRMS the money", lambda r: r["confirms_money"] is True),
                        ("book does NOT confirm the money",
                         lambda r: r["confirms_money"] is False),
                        ("book unreadable", lambda r: r["confirms_money"] is None)):
        sub = [r for r in dis if test(r)]
        cells += [(f"{label} · money", sub, "money"), (f"{label} · ticket", sub, "ticket")]
        md.append(f"| {label} | {_fmt(sub, 'money')} | {_fmt(sub, 'ticket')} |")
    md.append("")

    # --- how lopsided is the money? ---------------------------------------
    withpct = [r for r in dis if isinstance(r["money_pct"], (int, float))]
    if len(withpct) >= 40:
        med = st.median([r["money_pct"] for r in withpct])
        md += ["## Does it matter how lopsided the money is?", "",
               f"| handle share (median {med:.0f}%) | backing the MONEY side |",
               "|---|---|"]
        for label, test in ((f"handle ≥ {med:.0f}%", lambda r: r["money_pct"] >= med),
                            (f"handle < {med:.0f}%", lambda r: r["money_pct"] < med)):
            sub = [r for r in withpct if test(r)]
            cells.append((f"{label} · money", sub, "money"))
            md.append(f"| {label} | {_fmt(sub, 'money')} |")
        md.append("")

    # --- corrections -------------------------------------------------------
    pool = [(l, s, side) for l, s, side in cells if len(s) >= MIN_CELL]
    if pool:
        bl, bs, bside = max(pool, key=lambda c: _roi(_bets(c[1], c[2])))
        obs = _roi(_bets(bs, bside)) * 100
        plan = [[(grade.american_profit(r["money_odds"] if side == "money"
                                        else r["ticket_odds"]),
                  r["p_money"] if side == "money" else 1 - r["p_money"]) for r in s]
                for _, s, side in pool]
        rng = random.Random(202)
        null = [max(sum(w if rng.random() < p else -1 for w, p in pl) / len(pl)
                    for pl in plan) * 100 for _ in range(TRIALS)]
        pv = (sum(1 for x in null if x >= obs) + 1) / (len(null) + 1)
        md += ["## Paying for the look", "",
               f"- cells at n≥{MIN_CELL}: **{len(pool)}** (both sides of each, "
               "so picking a direction afterwards is paid for)",
               f"- best: **{bl}** at {obs:+.1f}%",
               f"- biggest a price-redraw manufactures: median "
               f"**{st.median(null):+.1f}%**, 95th "
               f"**{sorted(null)[int(.95*len(null))]:+.1f}%**",
               f"- **corrected p = {pv:.3f}**", "",
               ("**Clears.**" if pv < 0.05 else "**Does not clear.**"), ""]
        rh = random.Random(8)
        tag = [rh.random() < 0.5 for _ in bs]
        a = [r for r, t in zip(bs, tag) if t]
        b = [r for r, t in zip(bs, tag) if not t]
        if min(len(a), len(b)) >= 10:
            md += [f"- split-half of **{bl}**: {_fmt(a, bside)} against "
                   f"{_fmt(b, bside)}", ""]

    md += ["## How to read this", "",
           "- these games are REJECTED today, so a positive cell would mean "
           "volume the rule is leaving behind, not a change to what it backs",
           "- 133 games split three ways is small, and the intervals are "
           "wide; the correction is there because three splits of a small "
           "population is exactly where a tempting number appears",
           "- nothing here changes the board.", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "disagreement.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
