"""
What KIND of hitter is each bat — contact, power, ground-ball, speed — so a night's
conditions can be matched to a profile instead of to a name.

READ-ONLY. Changes no pick, writes no ledger entry.

WHY PROFILES AND NOT A RANKING
Conditions act on batted balls, not on hitters. Air that is cold, or wind blowing
in, takes distance off a FLY BALL and does almost nothing to a ground ball or a
line drive through the infield. A high-strikeout starter removes balls in play
altogether, which costs a free-swinging slugger more than a contact bat. So the
useful read is each hitter's own mix:

  K%        how often he removes himself from the batted-ball question entirely
  GB/AO     ground-outs per air-out, the closest thing the season line gives to
            a ground-ball/fly-ball lean
  ISO       slugging minus average: how much of his value needs the ball to travel
  speed     steals and triples, which turn ground balls and gaps into bases

This is CONTEXT, exactly like `main._contact_conditions`, and it ranks nothing for
betting. Nothing in this project has shown conditions predict hits; the thresholds
below are conventional reference points, not fitted ones.

Writes output/hitter_type.md.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from . import mlb_api
from .mlb_api import lineup, schedule_for

log = logging.getLogger("hitter_type")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

# conventional reference points, for labelling only
K_LOW, K_HIGH = 0.18, 0.26          # strikeout rate
GB_LEAN, AIR_LEAN = 1.25, 0.85      # ground-outs per air-out
ISO_POWER = 0.180


def season_line(player_id: int, season: int) -> dict:
    try:
        data = mlb_api._get(f"people/{player_id}/stats", stats="season",
                            group="hitting", season=season, gameType="R,P")
    except Exception as exc:
        log.warning("season line failed for %s: %s", player_id, exc)
        return {}
    for s in data.get("stats", []):
        for sp in s.get("splits", []):
            return sp.get("stat") or {}
    return {}


def _f(st: dict, key: str) -> float | None:
    v = st.get(key)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def profile(st: dict) -> dict:
    pa = _f(st, "plateAppearances") or 0
    k = _f(st, "strikeOuts")
    bb = _f(st, "baseOnBalls")
    go, ao = _f(st, "groundOuts"), _f(st, "airOuts")
    avg, slg = _f(st, "avg"), _f(st, "slg")
    return {
        "pa": int(pa),
        "k_pct": (k / pa) if k is not None and pa else None,
        "bb_pct": (bb / pa) if bb is not None and pa else None,
        "gb_ao": (go / ao) if go is not None and ao else None,
        "iso": (slg - avg) if slg is not None and avg is not None else None,
        "sb": int(_f(st, "stolenBases") or 0),
        "triples": int(_f(st, "triples") or 0),
        "hr": int(_f(st, "homeRuns") or 0),
    }


def label(p: dict) -> str:
    """A short profile tag from the mix, not from one number."""
    bits = []
    k, gb, iso = p["k_pct"], p["gb_ao"], p["iso"]
    if k is not None:
        bits.append("low-K contact" if k <= K_LOW
                    else "high-K" if k >= K_HIGH else "average-K")
    if gb is not None:
        bits.append("ground-ball" if gb >= GB_LEAN
                    else "fly-ball" if gb <= AIR_LEAN else "balanced")
    if iso is not None and iso >= ISO_POWER:
        bits.append("power")
    if p["sb"] >= 15 or p["triples"] >= 4:
        bits.append("speed")
    return ", ".join(bits) or "—"


def fit(p: dict) -> tuple[int, str]:
    """(score, why) for a cold / wind-in / high-K night. Positive = the profile
    loses least. Deliberately coarse: this is a label, not a projection."""
    s, why = 0, []
    k, gb, iso = p["k_pct"], p["gb_ao"], p["iso"]
    if k is not None:
        if k <= K_LOW:
            s += 2; why.append("rarely strikes out")
        elif k >= K_HIGH:
            s -= 2; why.append("strikes out a lot")
    if gb is not None:
        if gb >= GB_LEAN:
            s += 2; why.append("keeps it on the ground")
        elif gb <= AIR_LEAN:
            s -= 2; why.append("needs the ball to carry")
    if iso is not None and iso >= ISO_POWER:
        s -= 1; why.append("value is in the air")
    if p["sb"] >= 15 or p["triples"] >= 4:
        s += 1; why.append("speed plays on the ground")
    return s, "; ".join(why) or "nothing distinctive"


def build(team_name: str, date: str) -> str:
    md = [f"# {team_name} — hitter profiles, {date}", "",
          "_Read-only: changes no pick. Context, not a signal - nothing in this "
          "project has shown conditions predict hits._", ""]
    games = schedule_for(date)
    gm = next((g for g in games if team_name in (g.away.name, g.home.name)), None)
    if gm is None:
        return "\n".join(md + [f"No {team_name} game on {date}.", ""])
    is_home = gm.home.name == team_name
    team = gm.home if is_home else gm.away
    try:
        bats = lineup(gm.game_pk, team.team_id, date, is_home)
    except Exception as exc:
        return "\n".join(md + [f"Lineup unavailable ({exc}).", ""])

    season = int(date[:4])
    rows = []
    for p in bats:
        st = season_line(p.player_id, season)
        if not st:
            continue
        pr = profile(st)
        sc, why = fit(pr)
        rows.append({"name": p.name, "p": pr, "label": label(pr),
                     "score": sc, "why": why})
    if not rows:
        return "\n".join(md + ["No season lines returned.", ""])
    rows.sort(key=lambda r: -r["score"])

    md += [f"- reference points: K% low ≤ {K_LOW:.0%} / high ≥ {K_HIGH:.0%}  ·  "
           f"GB/AO ground-lean ≥ {GB_LEAN} / air-lean ≤ {AIR_LEAN}  ·  "
           f"ISO power ≥ {ISO_POWER:.3f}", "",
           "| hitter | PA | K% | BB% | GB/AO | ISO | HR | SB | profile |",
           "|---|---|---|---|---|---|---|---|---|"]
    def pct(v):
        return f"{v:.1%}" if v is not None else "—"

    def num(v, nd):
        return f"{v:.{nd}f}" if v is not None else "—"

    for r in rows:
        p = r["p"]
        md.append(f"| {r['name']} | {p['pa']} | {pct(p['k_pct'])} | "
                  f"{pct(p['bb_pct'])} | {num(p['gb_ao'], 2)} | "
                  f"{num(p['iso'], 3)} | {p['hr']} | {p['sb']} | {r['label']} |")
    md += ["", "## Who a cold, wind-in, high-strikeout night costs least", "",
           "_Coarse by design: +2 for rarely striking out, +2 for a ground-ball "
           "lean, +1 for speed, −2 for a high strikeout rate, −2 for an air lean, "
           "−1 for power that needs carry. A label, not a projection._", "",
           "| hitter | fit | why |", "|---|---|---|"]
    for r in rows:
        md.append(f"| {r['name']} | **{r['score']:+d}** | {r['why']} |")
    return "\n".join(md + [""])


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default=os.environ.get("TYPE_TEAM") or "")
    ap.add_argument("--date", default=os.environ.get("PICKS_DATE"))
    a = ap.parse_args()
    if not a.team:
        print("pass --team")
        return
    date = a.date
    if not date:
        from .main import today_eastern
        date = today_eastern()
    md = build(a.team, date)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "hitter_type.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
