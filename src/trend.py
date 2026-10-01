"""
Short-window batting trend for one team: the last N games, hitter by hitter.

READ-ONLY. Changes no pick, writes no ledger entry.

WHY A SEPARATE WINDOW
The board's `form` is a FIVE-game window (`props.RECENT_GAMES`) and it feeds the
prop ledger, so it is not something to retune for a question. This reports a
shorter window beside the 5-game and season numbers instead, leaving that alone.

READ THE SAMPLE BEFORE READING THE TREND
Three games is roughly 12 plate appearances. At that size a hitter's slash line
moves several hundred points on one extra double, so the ordering here is mostly
noise and is NOT a forecast - it answers "who has been hitting lately", which is
a question about the past. The season column is printed next to it so the gap is
visible rather than implied, and the per-game line is printed so a flat 3-for-12
cannot masquerade as a trend.

Writes output/trend.md.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from . import props
from .mlb_api import lineup, schedule_for

log = logging.getLogger("trend")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
WINDOW = 3
LONG_WINDOW = props.RECENT_GAMES      # the board's own window, for contrast
AUDIT_GAMES = 8        # dated games printed raw, so the window is checkable


def _f(st: dict, key: str) -> float:
    try:
        return float(st.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _slash(games: list[dict]) -> dict | None:
    """AVG/OBP/SLG/OPS over a list of per-game stat dicts."""
    ab = sum(_f(g, "atBats") for g in games)
    h = sum(_f(g, "hits") for g in games)
    bb = sum(_f(g, "baseOnBalls") for g in games)
    hbp = sum(_f(g, "hitByPitch") for g in games)
    sf = sum(_f(g, "sacFlies") for g in games)
    tb = sum(_f(g, "totalBases") for g in games)
    denom = ab + bb + hbp + sf
    if ab <= 0 or denom <= 0:
        return None
    avg, obp, slg = h / ab, (h + bb + hbp) / denom, tb / ab
    return {"avg": avg, "obp": obp, "slg": slg, "ops": obp + slg,
            "h": int(h), "ab": int(ab), "bb": int(bb), "games": len(games)}


def _games_before(player_id: int, season: int, date: str) -> list[dict]:
    """His games with a plate appearance, strictly before `date`, oldest first.

    The date cut matters: without it tonight's own game - or a later one, if the
    log is ahead - would be read back as recent form.
    """
    rows = []
    for s in props._game_log(player_id, season):
        st = s.get("stat") or {}
        d = s.get("date") or ""
        if _f(st, "plateAppearances") < 1 or not d or d >= date:
            continue
        rows.append((d, st))
    rows.sort(key=lambda x: x[0])
    return [{**st, "_date": d} for d, st in rows]


def _line(g: dict, with_date: bool = True) -> str:
    """'09-30 0-2 2B' - the date is NOT optional detail. Without it a per-game
    line cannot be checked against what actually happened, which is exactly the
    gap that made the first version of this report unverifiable."""
    h, ab = int(_f(g, "hits")), int(_f(g, "atBats"))
    d = (g.get("_date") or "")[5:]
    bits = (f"{d} " if with_date and d else "") + f"{h}-{ab}"
    for key, tag in (("doubles", "2B"), ("triples", "3B"), ("homeRuns", "HR"),
                     ("baseOnBalls", "BB")):
        n = int(_f(g, key))
        if n:
            bits += f" {n}{tag}" if n > 1 else f" {tag}"
    return bits


def build(team_name: str, date: str, window: int = WINDOW) -> str:
    md = [f"# {team_name} — last {window} games, hitter by hitter", "",
          f"_Board date {date}. Read-only; changes no pick._", "",
          f"_**{window} games is about {window * 4} plate appearances.** A slash "
          "line moves hundreds of points on one extra double at that size, so "
          "this ranks who HAS hit lately - it is not a forecast. Season numbers "
          "are beside it so the gap is visible, and the per-game line is there "
          "so a flat 3-for-12 cannot look like a trend._", ""]
    games = schedule_for(date)
    gm = next((g for g in games if team_name in (g.away.name, g.home.name)), None)
    if gm is None:
        return "\n".join(md + [f"No {team_name} game on {date}, so no lineup to "
                               "read. Pass --date for a day they played.", ""])
    is_home = gm.home.name == team_name
    team = gm.home if is_home else gm.away
    try:
        bats = lineup(gm.game_pk, team.team_id, date, is_home)
    except Exception as exc:
        return "\n".join(md + [f"Lineup unavailable ({exc}).", ""])
    if not bats:
        return "\n".join(md + ["No lineup or roster hitters returned.", ""])

    season = int(date[:4])
    rows = []
    for p in bats:
        logs = _games_before(p.player_id, season, date)
        audit = [_line(g) for g in logs[-AUDIT_GAMES:]]
        if len(logs) < window:
            rows.append({"name": p.name, "thin": len(logs), "audit": audit})
            continue
        short = _slash(logs[-window:])
        longw = _slash(logs[-LONG_WINDOW:]) if len(logs) >= LONG_WINDOW else None
        allg = _slash(logs)
        if not short or not allg:
            rows.append({"name": p.name, "thin": len(logs), "audit": audit})
            continue
        rows.append({"name": p.name, "short": short, "long": longw, "all": allg,
                     "delta": short["ops"] - allg["ops"], "audit": audit,
                     "per_game": [_line(g) for g in logs[-window:]]})
    ranked = sorted([r for r in rows if "delta" in r], key=lambda r: -r["delta"])

    md += [f"| hitter | last {window} | OPS | season OPS | vs season | "
           f"last {LONG_WINDOW} OPS | game by game |", "|---|---|---|---|---|---|---|"]
    for r in ranked:
        s, a = r["short"], r["all"]
        arrow = "▲" if r["delta"] > 0.050 else "▼" if r["delta"] < -0.050 else "—"
        lng = f"{r['long']['ops']:.3f}" if r["long"] else "—"
        md.append(f"| {r['name']} | {s['h']}-{s['ab']} | {s['ops']:.3f} | "
                  f"{a['ops']:.3f} ({a['games']} g) | **{r['delta']:+.3f}** {arrow} "
                  f"| {lng} | {' · '.join(r['per_game'])} |")
    md.append("")
    thin = [r["name"] for r in rows if "delta" not in r]
    if thin:
        md += [f"_Too few games logged to window ({window} needed): "
               + ", ".join(thin) + "._", ""]
    md += ["## The raw log these numbers come from", "",
           f"_Last {AUDIT_GAMES} dated games per hitter, newest last. The window "
           f"above is the final {window}. Check any row against the box score._",
           "", "| hitter | games (oldest → newest) |", "|---|---|"]
    for r in sorted(rows, key=lambda x: x["name"]):
        md.append(f"| {r['name']} | {' · '.join(r.get('audit') or []) or '—'} |")
    md.append("")

    up = [r for r in ranked if r["delta"] > 0.050]
    md += ["## Trending up", ""]
    if up:
        for r in up:
            md.append(f"- **{r['name']}** — {r['short']['ops']:.3f} over "
                      f"{r['short']['h']}-{r['short']['ab']} against a "
                      f"{r['all']['ops']:.3f} season, {r['delta']:+.3f}"
                      f"  ·  {' · '.join(r['per_game'])}")
    else:
        md.append("- nobody in this lineup is more than 50 OPS points above his "
                  "own season over this window")
    return "\n".join(md + [""])


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default=os.environ.get("TREND_TEAM") or "Atlanta Braves")
    ap.add_argument("--date", default=os.environ.get("PICKS_DATE"))
    ap.add_argument("--window", type=int,
                    default=int(os.environ.get("TREND_WINDOW") or WINDOW))
    a = ap.parse_args()
    date = a.date
    if not date:
        from .main import today_eastern
        date = today_eastern()
    md = build(a.team, date, a.window)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "trend.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
