"""
Source-conflict test: does fading the public work better when the public-% sources
DISAGREE with each other?

THE THEORY (user's)
Fading the Scores&Odds public side "was spot on some days and lost terribly on
others". The hypothesis is that the good days are the ones where the evidence
CONFLICTS - where Scores&Odds says one thing and the other reads say another -
because that is where the book's posted numbers are hiding something.

WHAT WE ALREADY STORE
Every snapshot keeps the public read from five independent places:
    scoresodds_bets   ticket % (the site the user used)
    vsin_bets         ticket % from a second book feed
    polymarket_bets   real-money implied %
    covers            consensus %
    forum             hand-tallied forum posts
plus a per-source agree/dissent tally in public_check.sources. So "do the sources
conflict" is directly measurable, game by game, with no new scraping.

WHAT THIS TESTS
  1. the plain strategy: fade the Scores&Odds public side (and follow it) -
     establishing the baseline the user actually experienced
  2. that same strategy split by CONFLICT: all sources agreeing vs any dissent,
     covers-vs-S&O disagreement, and money (Polymarket) disagreeing with tickets
  3. by how LOPSIDED the public is, since a 50/50 "public side" is meaningless
  4. by the size of the gap between what the sources report

Rigour: every row shows in-sample vs holdout; the headline conflict split gets a
day-block bootstrap CI and a market-calibrated null p-value. Many slices are
scanned, so a lone green cell is a hypothesis, not a rule.

Writes output/source_conflict.md.
"""

from __future__ import annotations

import glob
import json
import random
import statistics as st
from pathlib import Path

from . import grade, mlb_api

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
HOLDOUT_FROM = "2026-07-23"
BOOTSTRAP = 2000
NULL_SIMS = 1500
SEED = 20260729


def _implied(ml: int) -> float:
    return 100 / (ml + 100) if ml > 0 else -ml / (-ml + 100)


def _side_team(side: str, away: str, home: str):
    return home if side == "home" else away if side == "away" else None


def collect() -> list[dict]:
    recs = []
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
            if " @ " not in g.get("matchup", ""):
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            away, home = g["matchup"].split(" @ ")
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}

            books = ((g.get("public_majority") or {}).get("detail") or {}).get("books") or {}
            so = books.get("scoresodds_bets") or {}
            if not isinstance(so.get("away"), (int, float)) or \
               not isinstance(so.get("home"), (int, float)):
                continue                       # no S&O read -> not this test's population
            so_pct = max(so["away"], so["home"])
            so_side = "home" if so["home"] >= so["away"] else "away"
            so_team = _side_team(so_side, away, home)

            chk = g.get("public_check") or {}
            srcs = chk.get("sources") or []
            by_name = {s.get("name"): s.get("side") for s in srcs if s.get("name")}
            covers_side = by_name.get("covers")
            vsin_side = by_name.get("vsin_bets")
            pm_side = by_name.get("polymarket_bets")

            # spread between the reported public percentages (how much the
            # sources actually differ in DEGREE, not just direction)
            pcts = []
            for k in ("scoresodds_bets", "vsin_bets", "polymarket_bets"):
                b = books.get(k) or {}
                if isinstance(b.get(so_side), (int, float)):
                    pcts.append(float(b[so_side]))
            pct_gap = (max(pcts) - min(pcts)) if len(pcts) >= 2 else None

            recs.append({
                "date": date, "winner": res["winner"], "price": price,
                "away": away, "home": home,
                "so_team": so_team, "so_pct": so_pct, "so_side": so_side,
                "fade_team": _side_team("away" if so_side == "home" else "home", away, home),
                "covers_conflict": (covers_side is not None and covers_side != so_side),
                "vsin_conflict": (vsin_side is not None and vsin_side != so_side),
                "pm_conflict": (pm_side is not None and pm_side != so_side),
                "dissent": chk.get("dissent"),
                "agree": chk.get("agree"),
                "pct_gap": pct_gap,
                "holdout": date >= HOLDOUT_FROM,
            })
    return recs


def _rows(recs, key):
    """key: 'fade_team' or 'so_team'."""
    out = []
    for r in recs:
        t = r.get(key)
        if not t or t not in r["price"]:
            continue
        out.append({"won": r["winner"] == t, "odds": r["price"][t],
                    "date": r["date"], "holdout": r["holdout"]})
    return out


def _roi(rows):
    if not rows:
        return None
    return sum(grade.american_profit(x["odds"]) if x["won"] else -1
               for x in rows) / len(rows)


def _fmt(rows):
    if not rows:
        return "—"
    w = sum(1 for x in rows if x["won"])
    u = sum(grade.american_profit(x["odds"]) if x["won"] else -1 for x in rows)
    return f"{w}-{len(rows)-w} ({w/len(rows):.0%}) · {u:+.1f}u · **{_roi(rows):+.1%}** (n={len(rows)})"


def _split_row(label, sub, key):
    return (f"| {label} | {_fmt(_rows(sub, key))} | "
            f"{_fmt(_rows([r for r in sub if not r['holdout']], key))} | "
            f"{_fmt(_rows([r for r in sub if r['holdout']], key))} |")


def _bootstrap(rows):
    by_day: dict = {}
    for x in rows:
        by_day.setdefault(x["date"], []).append(x)
    days = list(by_day)
    if len(days) < 4:
        return None
    rnd = random.Random(SEED)
    out = []
    for _ in range(BOOTSTRAP):
        pool = []
        for _ in range(len(days)):
            pool.extend(by_day[rnd.choice(days)])
        if pool:
            out.append(_roi(pool))
    out.sort()
    return out[int(0.025 * len(out))], out[int(0.975 * len(out))], st.median(out)


def _null_p(sub, key, observed):
    """Redraw winners from each game's own price-implied odds (no edge, real
    prices) and see how often the strategy matches or beats what we saw."""
    rnd = random.Random(SEED)
    prep = []
    for r in sub:
        teams = list(r["price"])
        if len(teams) != 2:
            continue
        p = [_implied(r["price"][t]) for t in teams]
        tot = sum(p) or 1.0
        prep.append((r, teams, p[0] / tot))
    beat = 0
    for _ in range(NULL_SIMS):
        sim = [{**r, "winner": teams[0] if rnd.random() < p0 else teams[1]}
               for r, teams, p0 in prep]
        v = _roi(_rows(sim, key))
        if v is not None and v >= observed:
            beat += 1
    return beat / NULL_SIMS


def build() -> str:
    recs = collect()
    if not recs:
        return "# Source conflict\n\n_No games with a Scores&Odds read._"
    H = "| slice | ALL | in-sample | HOLDOUT |\n|---|---|---|---|"
    md = [f"# Source conflict — fading Scores&Odds, {len(recs)} games", "",
          "_'FADE' backs the side opposite the S&O ticket majority; 'FOLLOW' backs "
          "the S&O majority itself. $1/bet at the real moneyline._", ""]

    # 1. the plain strategy the user ran
    md += ["## 1. The plain strategy (what you were doing)", "", H,
           _split_row("FADE the S&O public side", recs, "fade_team"),
           _split_row("FOLLOW the S&O public side", recs, "so_team"), ""]

    # 2. the theory: does conflict change it?
    md += ["## 2. Does CONFLICTING evidence change the fade?", "", H]
    for lab, sub in (
        ("all sources agree (dissent = 0)", [r for r in recs if r["dissent"] == 0]),
        ("ANY dissent among sources", [r for r in recs if (r["dissent"] or 0) > 0]),
        ("covers disagrees with S&O", [r for r in recs if r["covers_conflict"]]),
        ("covers agrees with S&O", [r for r in recs if not r["covers_conflict"]]),
        ("VSiN disagrees with S&O", [r for r in recs if r["vsin_conflict"]]),
        ("Polymarket MONEY disagrees with S&O tickets",
         [r for r in recs if r["pm_conflict"]]),
        ("Polymarket money agrees with S&O tickets",
         [r for r in recs if not r["pm_conflict"]]),
    ):
        md.append(_split_row("FADE — " + lab, sub, "fade_team"))
    md.append("")
    md += ["_Same slices, but FOLLOWING the public instead of fading:_", "", H]
    for lab, sub in (
        ("all sources agree", [r for r in recs if r["dissent"] == 0]),
        ("any dissent", [r for r in recs if (r["dissent"] or 0) > 0]),
        ("Polymarket money disagrees with S&O", [r for r in recs if r["pm_conflict"]]),
    ):
        md.append(_split_row("FOLLOW — " + lab, sub, "so_team"))
    md.append("")

    # 3. how lopsided is the public?
    md += ["## 3. By how heavy the S&O public side is", "", H]
    for lo, hi, lab in ((0, 60, "50–60% (barely a majority)"), (60, 70, "60–70%"),
                        (70, 80, "70–80%"), (80, 101, "80%+ (hammered)")):
        sub = [r for r in recs if lo <= r["so_pct"] < hi]
        md.append(_split_row(f"FADE — {lab}", sub, "fade_team"))
    md.append("")

    # 4. size of disagreement between the reported percentages
    md += ["## 4. By the GAP between what the sources report", "",
           "_Same side, different numbers: e.g. S&O says 72% and Polymarket says "
           "55%. A big gap is the clearest sign the posted % is not the whole story._",
           "", H]
    gaps = [r for r in recs if r["pct_gap"] is not None]
    for lo, hi, lab in ((0, 10, "< 10 pts apart"), (10, 20, "10–20 pts"),
                        (20, 100, "20+ pts apart")):
        sub = [r for r in gaps if lo <= r["pct_gap"] < hi]
        md.append(_split_row(f"FADE — {lab}", sub, "fade_team"))
    md.append("")

    # 5. rigour on the single best conflict cut
    best = None
    for lab, sub, key in (
        ("FADE when any source dissents", [r for r in recs if (r["dissent"] or 0) > 0], "fade_team"),
        ("FADE when covers disagrees with S&O", [r for r in recs if r["covers_conflict"]], "fade_team"),
        ("FADE when PM money disagrees with S&O", [r for r in recs if r["pm_conflict"]], "fade_team"),
        ("FOLLOW when all sources agree", [r for r in recs if r["dissent"] == 0], "so_team"),
    ):
        rr = _rows(sub, key)
        v = _roi(rr)
        if v is not None and len(rr) >= 25 and (best is None or v > best[3]):
            best = (lab, sub, key, v, rr)
    md += ["## 5. Rigour on the strongest conflict cut", ""]
    if best:
        lab, sub, key, v, rr = best
        md += [f"**{lab}** — {_fmt(rr)}", ""]
        ci = _bootstrap(rr)
        if ci:
            lo, hi, med = ci
            md += [f"- Day-block bootstrap 95% CI: **{lo:+.1%} to {hi:+.1%}** "
                   f"(median {med:+.1%}) — "
                   + ("cannot rule out zero." if lo <= 0 else "**excludes zero**."), ""]
        p = _null_p(sub, key, v)
        md += [f"- Market-calibrated null p-value: **{p:.3f}** — a result this good "
               f"happens {p:.1%} of the time with realistic prices and no edge."
               + ("  Not significant." if p > 0.05 else "  Significant at 5%."), ""]
    else:
        md += ["_No cut reached the minimum sample._", ""]

    md.append("_Many slices are scanned here. The holdout column and the p-value are "
              "the only things that separate a real effect from a lucky slice._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "source_conflict.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
