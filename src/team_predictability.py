"""
Are some teams harder to predict than others - and is anything else?

PREDICTABILITY IS NOT PROFITABILITY, AND THIS ONLY MEASURES THE FIRST
Whether a team BEATS its price is settled: the spread of team ROIs sits at
p = 0.621 over 2,420 team-games, and inside "line moved against", where a
spread test did clear at p = 0.036, the split-half came back r = +0.02 -
Houston +96% in one random half and -4% in the other. No team is a profitable
bet as a team.

This asks the different question. Predictability here means how well the
MARKET'S OWN de-vigged price tracks what happens, measured as log-loss per
team. A low score means the price is reliably right about them; a high score
means they are a coin flip the market cannot read. Neither is money by itself
- a well-priced team is well priced - but if predictability differs by team
or by condition, it says where the market's confidence is and is not earned,
and that is worth knowing before looking for edge anywhere.

THE CONTROL THAT MAKES IT A FAIR TEST
Log-loss depends on the prices themselves: a team always quoted -300 scores
better than one always at pick'em, with no skill involved either way. So the
null redraws each team's outcomes FROM ITS OWN PRICES and recomputes the
spread. Any difference that survives is about the team, not its price mix.

THE TEST THAT DECIDES IT
The same one that has killed everything this season: split-half. If a team is
genuinely hard to price, it is hard to price in both random halves of its
games. A spread that clears but does not repeat is thirty noisy numbers being
wide.

THE ADDITIONAL DATA
situational records (97% of games), weather (90%) and home-plate umpire
tendencies (80%) have never been examined. They are tested here as
CONDITIONS on predictability rather than as signals: are windy games, cold
games, open-roof games or high-strikeout umpires less predictable than the
market assumes? That is a structural question about where variance lives, and
it is well powered because every game contributes a continuous score rather
than one binary.

Writes output/team_predictability.md.
"""

from __future__ import annotations

import glob
import json
import logging
import math
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import mlb_api
from .pregame_money import _implied

log = logging.getLogger("team_predictability")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 3000
MIN_TEAM = 15
MIN_HALF = 7
EPS = 1e-6


def _ll(p: float, won: bool) -> float:
    p = min(max(p, EPS), 1 - EPS)
    return -(math.log(p) if won else math.log(1 - p))


def collect() -> list[dict]:
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
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            away, home = m.split(" @ ")
            if adv not in (away, home):
                continue
            opp = home if adv == away else away
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0:
                continue
            w = g.get("weather") or {}
            ut = g.get("ump_tend") or {}
            for team, odds in ((adv, a_ml), (opp, o_ml)):
                p = _implied(odds) / tot
                rows.append({
                    "date": date, "team": team, "p": p,
                    "won": res["winner"] == team,
                    "ll": _ll(p, res["winner"] == team),
                    "temp": w.get("temp_f"), "wind": w.get("wind_mph"),
                    "roof": w.get("roof"), "precip": w.get("precip_pct"),
                    "ump_k": ut.get("k_pg"), "ump_r": ut.get("r_pg"),
                    "park": g.get("park_factor"),
                })
    return rows


def _spread_test(groups: dict, seed: int) -> dict:
    """Spread of per-group mean log-loss, against redraws from each group's
    OWN prices - so a group of heavy favourites is not flattered."""
    obs = st.pstdev([st.mean([r["ll"] for r in rs]) for rs in groups.values()])
    rng = random.Random(seed)
    null = []
    for _ in range(TRIALS):
        vals = []
        for rs in groups.values():
            vals.append(st.mean([_ll(r["p"], rng.random() < r["p"]) for r in rs]))
        null.append(st.pstdev(vals))
    p = (sum(1 for x in null if x >= obs) + 1) / (len(null) + 1)
    return {"obs": obs, "med": st.median(null),
            "p95": sorted(null)[int(.95 * len(null))], "p": p}


def build() -> str:
    rows = collect()
    md = ["# Are some teams — or some conditions — harder to predict?", "",
          "_Predictability here is how well the market's own de-vigged price "
          "tracks what happens, as log-loss. Lower is more predictable. This "
          "is not profitability: whether a team beats its price is already "
          "settled (team ROI spread p = 0.621; inside line-against the spread "
          "cleared at p = 0.036 but split-half came back r = +0.02)._", "",
          f"- team-games: **{len(rows)}**", ""]
    if len(rows) < 500:
        return "\n".join(md + ["Not enough team-games.", ""])

    by = defaultdict(list)
    for r in rows:
        by[r["team"]].append(r)
    live = {t: rs for t, rs in by.items() if len(rs) >= MIN_TEAM}

    md += ["## 1. Do teams differ in how well the market prices them?", "",
           "_The null redraws each team's outcomes from ITS OWN prices, so a "
           "team of heavy favourites is not flattered by an easy schedule of "
           "quotes._", ""]
    res = _spread_test(live, 5)
    md += [f"- teams with ≥{MIN_TEAM} games: **{len(live)}**",
           f"- observed spread of per-team log-loss: **{res['obs']:.4f}**",
           f"- chance: median **{res['med']:.4f}**, 95th **{res['p95']:.4f}**",
           f"- **p = {res['p']:.3f}**", "",
           ("_Teams differ more than chance allows — some really are harder "
            "to price._" if res["p"] < 0.05 else
            "_No difference beyond chance. The market prices every team about "
            "equally well._"), ""]

    # split-half regardless of what the spread said
    rh = random.Random(31)
    ha, hb = defaultdict(list), defaultdict(list)
    for r in rows:
        (ha if rh.random() < 0.5 else hb)[r["team"]].append(r)
    pairs = [(t, st.mean([x["ll"] for x in ha[t]]), st.mean([x["ll"] for x in hb[t]]))
             for t in live if len(ha.get(t, [])) >= MIN_HALF
             and len(hb.get(t, [])) >= MIN_HALF]
    md += ["### Does a team's predictability repeat across random halves?", ""]
    if len(pairs) >= 8:
        r_ = st.correlation([a for _, a, _ in pairs], [b for _, _, b in pairs])
        md += [f"- teams in both halves: **{len(pairs)}** · "
               f"**split-half r = {r_:+.2f}**", "",
               ("_Repeats: a team hard to price in one half is hard to price "
                "in the other._" if r_ > 0.3 else
                "_Does not repeat. Per-team log-loss in one half does not "
                "predict the other, so any spread above is noise._"), "",
               "| team | half A | half B |", "|---|---|---|"]
        for t, a, b in sorted(pairs, key=lambda x: x[1])[:6]:
            md.append(f"| {t} (most predictable, half A) | {a:.3f} | {b:.3f} |")
        for t, a, b in sorted(pairs, key=lambda x: -x[1])[:4]:
            md.append(f"| {t} (least predictable, half A) | {a:.3f} | {b:.3f} |")
        md.append("")

    # --- 2. calibration: does any team beat or miss its price? ------------
    md += ["## 2. Calibration — actual against priced", "",
           "| team | n | priced to win | actually won | gap |",
           "|---|---|---|---|---|"]
    cal = []
    for t, rs in live.items():
        exp = st.mean([r["p"] for r in rs])
        act = sum(1 for r in rs if r["won"]) / len(rs)
        cal.append((t, len(rs), exp, act, act - exp))
    for t, n, exp, act, gap in sorted(cal, key=lambda x: -abs(x[4]))[:8]:
        md.append(f"| {t} | {n} | {exp:.1%} | {act:.1%} | **{gap:+.1%}** |")
    md += ["", "_The eight largest gaps in either direction. With 30 teams, "
           "gaps of this size are what chance produces — the spread test "
           "above is the one that judges them._", ""]

    # --- 3. conditions ----------------------------------------------------
    md += ["## 3. Conditions: is predictability about the game, not the team?",
           "", "_Every game contributes a continuous score, so these are "
           "better powered than anything per-team. Higher log-loss means the "
           "market read that kind of game less well._", "",
           "| condition | games | mean log-loss |", "|---|---|---|"]
    conds = [
        ("wind < 5 mph", lambda r: isinstance(r["wind"], (int, float)) and r["wind"] < 5),
        ("wind 5-12 mph", lambda r: isinstance(r["wind"], (int, float)) and 5 <= r["wind"] <= 12),
        ("wind > 12 mph", lambda r: isinstance(r["wind"], (int, float)) and r["wind"] > 12),
        ("temp < 60F", lambda r: isinstance(r["temp"], (int, float)) and r["temp"] < 60),
        ("temp >= 80F", lambda r: isinstance(r["temp"], (int, float)) and r["temp"] >= 80),
        ("roof closed/dome", lambda r: r["roof"] in ("closed", "dome", "roof closed")),
        ("roof open", lambda r: r["roof"] == "open"),
        ("ump K/9 high (>17)", lambda r: isinstance(r["ump_k"], (int, float)) and r["ump_k"] > 17),
        ("ump K/9 low (<15)", lambda r: isinstance(r["ump_k"], (int, float)) and r["ump_k"] < 15),
        ("hitter park (>1.03)", lambda r: isinstance(r["park"], (int, float)) and r["park"] > 1.03),
        ("pitcher park (<0.98)", lambda r: isinstance(r["park"], (int, float)) and r["park"] < 0.98),
    ]
    cond_groups = {}
    for label, test in conds:
        sub = [r for r in rows if test(r)]
        if len(sub) < 60:
            md.append(f"| {label} | {len(sub)} | _too few_ |")
            continue
        cond_groups[label] = sub
        md.append(f"| {label} | {len(sub)} | **{st.mean([r['ll'] for r in sub]):.4f}** |")
    md.append("")
    if len(cond_groups) >= 4:
        cr = _spread_test(cond_groups, 13)
        md += [f"- spread across conditions: **{cr['obs']:.4f}** against "
               f"chance median **{cr['med']:.4f}** (95th {cr['p95']:.4f})",
               f"- **p = {cr['p']:.3f}**", "",
               ("_Conditions differ more than chance allows: some kinds of "
                "game genuinely are priced worse than others._"
                if cr["p"] < 0.05 else
                "_No difference beyond chance. Weather, roof, umpire and park "
                "do not change how well the market reads a game._"), ""]

    md += ["## What a result here would and would not mean", "",
           "- a team or condition being LESS predictable does not make it "
           "profitable; it says the market's confidence is less earned there, "
           "which is where to look next — not what to bet",
           "- a spread that clears without repeating across halves is thirty "
           "noisy numbers being wide, which is the trap this whole file is "
           "built to avoid", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "team_predictability.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
