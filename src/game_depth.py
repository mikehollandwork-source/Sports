"""
In-depth per-game read: both sides' hottest bats against the opposing starter,
and the full line-movement record.

READ-ONLY. It changes no pick, writes no ledger entry and reads nothing the board
does not already have. It exists because the board shows the hot-bat block for
ONE side only - the play, or the watch-listed good dog - and "who is swinging well
against this pitcher" is a question about both lineups.

THE LINE SECTION, AND WHY IT SHOWS BOTH CUTS
The order-book logs run through the game and past settlement, so a losing side's
last reading is 0.00/1.00. Any drift taken from an uncut series reports the winner
rather than the money; measured cost of that mistake in this project was +9.9%
against -5.0% on the same 714 games. So the series here is cut at first pitch
minus consensus.LOCK_LEAD, the moment the board freezes, using the same helper the
live rule uses - and the UNCUT number is printed beside it so the gap is visible
rather than taken on trust.

It also prints the game's start time as the board recorded it AND as the
order-book logs recorded it. Those are both meant to come from the MLB schedule,
so when they disagree the freeze is computed from one of them and the board locks
on the other, and that is worth seeing rather than averaging away.

Writes output/game_depth.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
from pathlib import Path

from . import consensus, pm_books, props
from .mlb_api import schedule_for

log = logging.getLogger("game_depth")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TOP_BATS = 5
LEAGUE_OPS = 0.710     # the point a thin BvP sample shrinks toward
BVP_PRIOR = 20         # PA at which BvP gets half its own weight


def _mid(side: dict | None) -> float | None:
    if not isinstance(side, dict):
        return None
    b, a = side.get("bid"), side.get("ask")
    if isinstance(b, (int, float)) and isinstance(a, (int, float)) and a > b:
        return (a + b) / 2
    return None


def _ts(t) -> str:
    try:
        return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%H:%M")
    except (TypeError, ValueError, OSError):
        return "??:??"


def _bvp_text(b: dict | None) -> str:
    """BvP with its sample, plus the shrunk value actually worth weighing."""
    if not b or not isinstance(b.get("pa"), int) or b["pa"] <= 0:
        return "never faced him"
    pa, ops = b["pa"], b.get("ops")
    if not isinstance(ops, (int, float)):
        return f"{pa} PA, no OPS"
    w = pa / (pa + BVP_PRIOR)
    shrunk = w * ops + (1 - w) * LEAGUE_OPS
    return f"{ops:.3f} OPS in {pa} PA (shrunk {shrunk:.3f})"


def _bats_block(gm, is_home: bool, date: str) -> list[str]:
    """One team's lineup ranked against the opposing starter."""
    team = gm.home if is_home else gm.away
    opp_sp = (gm.away if is_home else gm.home).probable_pitcher
    name = f"{team.name}"
    if not opp_sp:
        return [f"**{name}** — opposing starter not posted yet, no read.", ""]
    try:
        ranked = props.hit_in_wins_ranked(
            gm.game_pk, team.team_id, date, is_home,
            opp_pitcher_id=opp_sp.player_id)
    except Exception as exc:
        log.warning("bats unavailable for %s: %s", name, exc)
        return [f"**{name}** — lineup/game-log fetch failed ({exc}).", ""]
    if not ranked:
        return [f"**{name}** vs {opp_sp.name} — no lineup posted yet.", ""]
    out = [f"**{name}** vs {opp_sp.name}", "",
           "| bat | form (last 5) | vs this SP | hits in wins | in all games |",
           "|---|---|---|---|---|"]
    # Hottest = form, which is the question asked. hit_in_wins_ranked orders by
    # rate inside wins, and that conditions on the outcome - a team that wins
    # hit well, so every regular looks good there.
    for b in sorted(ranked, key=lambda x: -(x.get("form") or 0))[:TOP_BATS]:
        hot = " 🔥" if b.get("super_hot") else ""
        out.append(f"| {b['player']}{hot} | {b.get('form', 0):+.0f}% | "
                   f"{_bvp_text(b.get('bvp'))} | {b.get('hit_rate', 0):.0%} | "
                   f"{b.get('all_rate', 0):.0%} |")
    return out + [""]


def _line_block(board_game: dict, date: str) -> list[str]:
    pc = board_game.get("pick_criteria") or {}
    chk = board_game.get("public_check") or {}
    lc = pc.get("line_check") or {}
    out = ["**The price**", "",
           f"- Pinnacle, this morning: **{lc.get('pinny_morning')}**",
           f"- board open → current: **{lc.get('open')} → {lc.get('current')}**"
           f"  (implied shift **{(lc.get('implied_shift') or 0):+.1%}** toward "
           f"{pc.get('advantage_team')})",
           f"- board's reading: _{lc.get('status')} — {lc.get('reason')}_", ""]
    try:
        early = json.loads((OUTPUT_DIR / f"lines_early_{date}.json").read_text())
        for r in early.get("pinnacle") or []:
            if r.get("home_name") and r["home_name"] in (board_game.get("matchup") or ""):
                out.append(f"- early Pinnacle capture "
                           f"({early.get('captured_utc', '?')[:16]}): away "
                           f"{r.get('away_ml')}, home {r.get('home_ml')}")
        out.append("")
    except (OSError, ValueError):
        pass

    out += ["**Where the public and the money are**", "",
            f"- public tickets lean **{chk.get('majority_side')}** "
            f"(`line` {chk.get('line')})",
            f"- the dollars are on **{chk.get('money_side')}** at "
            f"**{chk.get('money_pct')}%** (`money` {chk.get('money')})",
            f"- source agreement: {chk.get('agree')} agree / "
            f"{chk.get('dissent')} dissent → _{chk.get('verdict')}_"]
    for s in chk.get("sources") or []:
        out.append(f"    - {s.get('name')}: {s.get('side')}")
    for f in chk.get("flags") or []:
        out.append(f"- ⚠ {f}")
    out.append("")

    # ---- the order book, cut at the freeze ------------------------------
    try:
        day = pm_books.load_day(date) or {}
    except Exception as exc:
        log.warning("book log unavailable: %s", exc)
        return out
    g = (day.get("games") or {}).get(str(board_game.get("game_pk")))
    if not g:
        return out + ["_No order-book log for this game._", ""]
    cutoff = consensus._freeze_ts(g)
    out += ["**The order book** (Polymarket, advantage side)", "",
            f"- side logged: **{g.get('side')}**",
            f"- first pitch per the LOG: `{g.get('game_datetime')}`  ·  "
            f"per the BOARD: `{board_game.get('game_datetime')}`"]
    if g.get("game_datetime") != board_game.get("game_datetime"):
        out.append("- ⚠ **these disagree.** The freeze below is computed from the "
                   "log's time; the board locks its pick on its own. Both are "
                   "supposed to be the MLB schedule.")
    out.append(f"- freeze (first pitch − {consensus.LOCK_LEAD}): "
               f"`{_ts(cutoff) if cutoff else '?'}Z`")
    reads = [r for r in (g.get("readings") or []) if not r.get("empty")]
    pre = [r for r in reads if cutoff is None or (
        isinstance(r.get("t"), (int, float)) and r["t"] <= cutoff)]
    out += [f"- readings: **{len(pre)} before the freeze**, {len(reads)} in all", ""]
    if pre:
        first, last = _mid(pre[0]), _mid(pre[-1])
        if first is not None and last is not None:
            out.append(f"- mid price {first:.3f} → **{last:.3f}** "
                       f"(**{last - first:+.3f}** = {(last-first)*100:+.1f}c) "
                       f"between {_ts(pre[0]['t'])}Z and {_ts(pre[-1]['t'])}Z")
        u = _mid(reads[-1])
        if u is not None and first is not None and len(reads) > len(pre):
            out.append(f"- _uncut_, the last reading is {u:.3f} "
                       f"({u - first:+.3f}) — {len(reads)-len(pre)} reading(s) "
                       "after the freeze, which is the look-ahead this cut removes")
        out += ["", "| time | bid | ask | mid |", "|---|---|---|---|"]
        step = max(1, len(pre) // 12)          # keep the table readable
        for r in pre[::step] + ([pre[-1]] if len(pre) > 1 and (len(pre)-1) % step else []):
            m = _mid(r)
            out.append(f"| {_ts(r.get('t'))}Z | {r.get('bid')} | {r.get('ask')} | "
                       f"{f'{m:.3f}' if m is not None else '—'} |")
        out.append("")
    return out


def build(date: str) -> str:
    try:
        board = json.loads((OUTPUT_DIR / f"picks_{date}.json").read_text())
    except (OSError, ValueError) as exc:
        return f"# Game depth — {date}\n\nNo board for this date ({exc}).\n"
    games = {g.game_pk: g for g in schedule_for(date)}
    md = [f"# Game depth — {date}", "",
          "_Both lineups against the opposing starter, and the full price "
          "record. Read-only: this changes no pick._", ""]
    for bg in board.get("games", []):
        gm = games.get(bg.get("game_pk"))
        pc = bg.get("pick_criteria") or {}
        md += ["---", "", f"## {bg.get('matchup')}", "",
               f"- state **{bg.get('state')}** · board says "
               f"`{pc.get('play')}`"
               + (f" → **{pc.get('bet_team')} {pc.get('bet_moneyline'):+d}**"
                  if pc.get("bet_team") and isinstance(pc.get("bet_moneyline"), int)
                  else ""),
               f"- prices: {pc.get('advantage_team')} "
               f"{pc.get('advantage_moneyline')}, opponent "
               f"{pc.get('opponent_moneyline')}", ""]
        gd = pc.get("good_dog") or {}
        if gd:
            md.append(f"- 👀 good-dog tag on **{gd['team']}** "
                      f"(favoured {gd['rate']:.0%} of its games), watch only")
        lm = pc.get("line_money") or {}
        if lm:
            md.append(f"- 👁 line-vs-money tag on **{lm['team']}** "
                      f"(price moved {lm['move']:.1%} the other way), watch only")
        md.append("")
        md += ["### Hottest bats, both sides", ""]
        if gm is None:
            md += ["_Game not in today's schedule feed; no lineup read._", ""]
        else:
            md += _bats_block(gm, is_home=False, date=date)
            md += _bats_block(gm, is_home=True, date=date)
        md += ["### Line movement", ""] + _line_block(bg, date)
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=os.environ.get("PICKS_DATE"))
    date = ap.parse_args().date
    if not date:
        from .main import today_eastern
        date = today_eastern()
    md = build(date)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "game_depth.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
