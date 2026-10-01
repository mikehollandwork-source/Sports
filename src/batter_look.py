"""
One hitter, one night: his record against tonight's starter, his record against
that starter's HAND, and whether the park, weather and umpire favour contact.

READ-ONLY. Changes no pick, writes no ledger entry.

WHY THE TWO SAMPLES SIT SIDE BY SIDE
An exact batter-vs-pitcher line is almost always too small to mean anything on its
own - this project's own shrink gives it half the weight only at
`analysis.BVP_SHRINK_PA` (50) plate appearances. So the vs-hand split is printed
next to it as the backbone, and the shrunk blend is printed too, using
`analysis._bvp_effective` - the same function the board uses - rather than a second
method invented here.

Writes output/batter_look.md.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from . import analysis, mlb_api
from .mlb_api import lineup, probable_hands, schedule_for

log = logging.getLogger("batter_look")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
HAND_NAME = {"R": "right-handed", "L": "left-handed", "S": "switch"}


def bvp_detail(batter_id: int, pitcher_id: int) -> dict:
    """The full career line vs one pitcher. mlb_api.batter_vs_pitcher returns only
    {pa, ops} because that is all the board needs; this keeps the rest."""
    try:
        data = mlb_api._get(f"people/{batter_id}/stats", stats="vsPlayerTotal",
                            group="hitting", opposingPlayerId=pitcher_id)
    except Exception as exc:
        log.warning("bvp fetch failed: %s", exc)
        return {}
    for s in data.get("stats", []):
        for sp in s.get("splits", []):
            return sp.get("stat", {}) or {}
    return {}


def player_vs_hand(player_id: int, season: int) -> dict:
    """{'R': {...stat}, 'L': {...stat}} - his season splits vs each pitching hand.

    Same endpoint shape mlb_api.team_vs_hand uses for teams. Season splits only:
    the postseason adds a game or two, which cannot move a several-hundred-PA
    split, so the gameType fix that matters for game logs is immaterial here.
    """
    out: dict = {}
    try:
        data = mlb_api._get(f"people/{player_id}/stats", stats="statSplits",
                            group="hitting", season=season, sitCodes="vr,vl")
    except Exception as exc:
        log.warning("vs-hand split failed: %s", exc)
        return out
    for s in data.get("stats", []):
        for sp in s.get("splits", []):
            hand = {"vr": "R", "vl": "L"}.get(sp.get("split", {}).get("code", ""))
            if hand:
                out[hand] = sp.get("stat", {}) or {}
    return out


def _n(st: dict, *keys):
    for k in keys:
        v = st.get(k)
        if v not in (None, "", "-", ".---"):
            return v
    return "—"


def _slashline(st: dict) -> str:
    return (f"{_n(st,'avg')}/{_n(st,'obp')}/{_n(st,'slg')}  "
            f"(OPS {_n(st,'ops')})")


def build(player: str, date: str) -> str:
    md = [f"# {player} — {date}", "",
          "_Read-only: changes no pick._", ""]
    games = schedule_for(date)
    found = None
    for gm in games:
        for is_home in (False, True):
            team = gm.home if is_home else gm.away
            try:
                bats = lineup(gm.game_pk, team.team_id, date, is_home)
            except Exception:
                continue
            for p in bats:
                if player.lower() in (p.name or "").lower():
                    found = (gm, is_home, team, p)
                    break
            if found:
                break
        if found:
            break
    if not found:
        return "\n".join(md + [f"{player} is not in a posted lineup on {date}.", ""])
    gm, is_home, team, p = found
    opp = gm.away if is_home else gm.home
    # schedule_for does NOT fill the probable pitchers' throwing hand, so without
    # this the hand reads "?" and - worse - the vs-hand lookup silently misses,
    # leaving the "two put together" blend as the raw exact line while claiming a
    # weight that was never applied.
    try:
        probable_hands(gm)
    except Exception as exc:
        log.warning("probable hands unavailable: %s", exc)
    sp = opp.probable_pitcher
    md += [f"- **{team.name}** {'vs' if is_home else 'at'} {opp.name}",
           f"- he bats **{HAND_NAME.get(p.hand, p.hand or '?')}**"]
    if not sp:
        return "\n".join(md + ["", "Opposing starter not posted yet.", ""])
    md += [f"- opposing starter **{sp.name}**, throws "
           f"**{HAND_NAME.get(sp.hand, sp.hand or '?')}**", ""]

    season = int(date[:4])
    bvp = bvp_detail(p.player_id, sp.player_id)
    hands = player_vs_hand(p.player_id, season)
    same = hands.get(sp.hand or "", {})

    md += [f"## Against {sp.name} (career)", ""]
    if bvp and int(_n(bvp, "plateAppearances") or 0 or 0):
        md += [f"- **{_n(bvp,'plateAppearances')} PA** · "
               f"{_n(bvp,'hits')}-for-{_n(bvp,'atBats')} · "
               f"{_slashline(bvp)}",
               f"- {_n(bvp,'doubles')} 2B · {_n(bvp,'homeRuns')} HR · "
               f"{_n(bvp,'baseOnBalls')} BB · {_n(bvp,'strikeOuts')} K · "
               f"{_n(bvp,'rbi')} RBI", ""]
    else:
        md += ["- never faced him", ""]

    hand_label = HAND_NAME.get(sp.hand) or "unknown-handed"
    md += [f"## Against {hand_label} pitching this season", ""]
    for hand in ("R", "L"):
        st = hands.get(hand)
        tag = "  ← tonight" if hand == (sp.hand or "") else ""
        if st:
            md.append(f"- **vs {hand}HP**: {_n(st,'plateAppearances')} PA · "
                      f"{_slashline(st)}{tag}")
        else:
            md.append(f"- vs {hand}HP: no split returned{tag}")
    md.append("")

    # the blend the board itself would use
    try:
        ex_ops = float(_n(bvp, "ops")) if _n(bvp, "ops") != "—" else None
        ex_pa = int(_n(bvp, "plateAppearances")) if _n(bvp, "plateAppearances") != "—" else 0
    except (TypeError, ValueError):
        ex_ops, ex_pa = None, 0
    try:
        h_ops = float(_n(same, "ops")) if same else None
        h_pa = int(_n(same, "plateAppearances")) if same else 0
    except (TypeError, ValueError):
        h_ops, h_pa = None, 0
    eff, eff_pa = analysis._bvp_effective(ex_ops, ex_pa, h_ops, h_pa)
    md += ["## The two put together", ""]
    if eff is None:
        md += ["- neither sample is readable, so there is nothing to blend.", ""]
    elif h_ops is None or not ex_pa:
        # say so rather than print a weight that was not applied
        md += [f"- **{eff:.3f} OPS** over {eff_pa} PA — but this is ONE sample, "
               "not a blend: "
               + ("the vs-hand split is missing (starter's hand unknown?)"
                  if h_ops is None else "he has never faced this pitcher") + ".", ""]
    else:
        w = ex_pa / (ex_pa + analysis.BVP_SHRINK_PA)
        md += [f"- shrunk expectation **{eff:.3f} OPS** over {eff_pa} PA, using "
               f"`analysis._bvp_effective` - the board's own method",
               f"- the exact line carries **{w:.0%}** of that "
               f"({ex_pa} PA against a {analysis.BVP_SHRINK_PA}-PA half-weight "
               f"point); the vs-hand split carries the remaining "
               f"**{1-w:.0%}**", ""]
    return "\n".join(md + [""])


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--player", default=os.environ.get("LOOK_PLAYER") or "")
    ap.add_argument("--date", default=os.environ.get("PICKS_DATE"))
    a = ap.parse_args()
    if not a.player:
        print("pass --player")
        return
    date = a.date
    if not date:
        from .main import today_eastern
        date = today_eastern()
    md = build(a.player, date)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "batter_look.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
