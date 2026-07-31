"""
Historical money-per-side prober: can we recover TOTAL money on each side for
PAST games, from Kalshi and Polymarket?

THE DISTINCTION THAT MATTERS
Order-book DEPTH (resting bid/ask sizes) is ephemeral - once the market moves the
old book is gone, which is why the live loggers exist. But VOLUME and OPEN
INTEREST are cumulative and survive settlement, so they may be pullable for games
already played. Kalshi lists one market PER TEAM, each with its own volume and
open_interest, so "money on each side" is directly available there. Polymarket
reports volume per market rather than per outcome, so its per-side split is the
weaker half.

This probes rather than assumes: it reports how many settled markets come back,
what fields they actually carry, how many of OUR historical games can be matched,
and only then - if the data supports it - compares which side each venue had more
money on and grades that against the result.

Caveat kept in view: volume is total TRADED, and every trade has a buyer and a
seller, so per-team market volume is a proxy for interest in that side, not a
literal ledger of money backing it.

Writes output/venue_volume.md.
"""

from __future__ import annotations

import glob
import json
import re
import statistics as st
from collections import Counter
from pathlib import Path

from . import grade, kalshi, mlb_api
from .analysis import _canon_abbr

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MIN_N = 20

# 'KXMLBGAME-26JUL231840KCDET-KC' -> date part '26JUL23'
_TICKER_DATE = re.compile(r"-(\d{2})([A-Z]{3})(\d{2})")
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}


def _ticker_date(ticker: str) -> str | None:
    m = _TICKER_DATE.search(ticker or "")
    if not m:
        return None
    yy, mon, dd = m.groups()
    mo = _MONTHS.get(mon)
    if not mo:
        return None
    return f"20{yy}-{mo:02d}-{int(dd):02d}"


def kalshi_by_game() -> dict:
    """{(date, frozenset{abbr,abbr}): {abbr: {volume, open_interest, result}}}"""
    rows = kalshi.settled_markets()
    by_event: dict = {}
    for m in rows:
        tk, ev = m.get("ticker"), m.get("event_ticker")
        if not tk or not ev:
            continue
        team = kalshi._abbr(tk)
        if not team:
            continue
        rec = {}
        for k in ("volume", "open_interest"):
            v = m.get(k)
            if isinstance(v, (int, float)):
                rec[k] = float(v)
        if isinstance(m.get("result"), str):
            rec["result"] = m["result"]
        by_event.setdefault(ev, {"date": _ticker_date(tk), "teams": {}})
        by_event[ev]["teams"][team] = rec
    out = {}
    for ev, d in by_event.items():
        if len(d["teams"]) != 2 or not d["date"]:
            continue
        out[(d["date"], frozenset(d["teams"]))] = d["teams"]
    return out, rows


def build() -> str:
    md = ["# Historical money per side — Kalshi vs Polymarket", ""]

    try:
        kmap, raw = kalshi_by_game()
    except Exception as exc:
        return "\n".join(md + [f"_Kalshi probe failed: {exc}_"])

    # --- what did Kalshi actually give us? ---
    fields = Counter()
    for m in raw[:400]:
        for k in ("volume", "open_interest", "result", "close_time", "event_ticker"):
            if m.get(k) not in (None, ""):
                fields[k] += 1
    md += ["## 1. What Kalshi returns for settled markets", "",
           f"- settled market rows: **{len(raw)}**",
           f"- complete two-sided games parsed: **{len(kmap)}**"]
    if raw:
        md.append("- field coverage in the first 400 rows: " +
                  ", ".join(f"`{k}` {v}" for k, v in fields.most_common()) or "none")
        sample = raw[0]
        md += ["", "_sample row:_", "```",
               json.dumps({k: sample.get(k) for k in
                           ("ticker", "event_ticker", "volume", "open_interest",
                            "result", "close_time")}, indent=1), "```"]
    md.append("")

    if not kmap:
        md += ["## Verdict", "",
               "Kalshi returned no complete two-sided settled games, so a "
               "historical money-per-side comparison is not possible from this "
               "endpoint. The forward loggers remain the path.", ""]
        return "\n".join(md)

    # --- how many of OUR games can we match? ---
    recs, matched, unmatched = [], 0, 0
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        day = json.loads(Path(f).read_text())
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        for g in day.get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            aa = _canon_abbr(g.get("away_abbr") or "")
            ha = _canon_abbr(g.get("home_abbr") or "")
            if not aa or not ha or " @ " not in g.get("matchup", ""):
                continue
            teams = kmap.get((date, frozenset({aa, ha})))
            if not teams:
                unmatched += 1
                continue
            matched += 1
            away, home = g["matchup"].split(" @ ")
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            opp = home if adv == away else away
            name = {aa: away, ha: home}
            vols = {ab: (t.get("volume") or 0.0) for ab, t in teams.items()}
            if sum(vols.values()) <= 0:
                continue
            hi_ab = max(vols, key=vols.get)
            lo_ab = min(vols, key=vols.get)
            if vols[hi_ab] == vols[lo_ab]:
                continue
            recs.append({
                "date": date, "winner": res["winner"],
                "price": {adv: a_ml, opp: o_ml},
                "more_money": name.get(hi_ab), "less_money": name.get(lo_ab),
                "share": vols[hi_ab] / (vols[hi_ab] + vols[lo_ab]),
            })

    md += ["## 2. Matching to our historical games", "",
           f"- games matched to a Kalshi settled pair: **{matched}**",
           f"- games with no Kalshi match: **{unmatched}**",
           f"- usable rows (both sides priced, non-tied volume): **{len(recs)}**", ""]

    if len(recs) < MIN_N:
        md += ["## Verdict", "",
               f"Only **{len(recs)}** usable games - below the **{MIN_N}** needed "
               "for a meaningful read. Reporting counts only rather than a "
               "percentage on a handful of games.", ""]
        return "\n".join(md)

    def rows(pick):
        out = []
        for r in recs:
            t = pick(r)
            if t and t in r["price"]:
                out.append({"won": r["winner"] == t, "odds": r["price"][t]})
        return out

    def fmt(rr):
        if not rr:
            return "—"
        w = sum(1 for x in rr if x["won"])
        u = sum(grade.american_profit(x["odds"]) if x["won"] else -1 for x in rr)
        return f"{w}-{len(rr)-w} ({w/len(rr):.0%}) · {u:+.1f}u · **{u/len(rr):+.1%}** (n={len(rr)})"

    md += ["## 3. Does the side with MORE Kalshi money win?", "",
           "| strategy | result |", "|---|---|",
           f"| back the MORE-money side | {fmt(rows(lambda r: r['more_money']))} |",
           f"| back the LESS-money side | {fmt(rows(lambda r: r['less_money']))} |", ""]

    lop = [r for r in recs if r["share"] >= 0.70]
    md += ["_Lopsided games only (one side holds 70%+ of the volume):_", "",
           "| strategy | result |", "|---|---|",
           f"| back the MORE-money side | {fmt([x for x in rows(lambda r: r['more_money'] if r['share'] >= 0.70 else None)])} |",
           f"| back the LESS-money side | {fmt([x for x in rows(lambda r: r['less_money'] if r['share'] >= 0.70 else None)])} |",
           "", f"_{len(lop)} of {len(recs)} games are lopsided._", ""]

    md.append("_Volume is total TRADED on each team's market, not a ledger of "
              "money backing that side - every trade has a buyer and a seller. "
              "Treat it as a proxy for interest, and the holdout discipline used "
              "elsewhere still applies before acting on anything here._")
    return "\n".join(md)


def main() -> None:
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "venue_volume.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
