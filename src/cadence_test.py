"""
Does refreshing the board more often produce better picks, or just more of them?

THE QUESTION
The board is stateless: every run re-evaluates every game against current data,
and three of the four gates move during the day. So a faster refresh catches
games in a qualifying state that an hourly one misses. The worry is that the
order-book gate fires on `drift > 0 or imbalance > 0.20`, where imbalance comes
from the LAST reading's resting sizes - an instantaneous, noisy number. Sample it
often enough and a game hovering near the threshold crosses it eventually. That
would select games for a lucky snapshot rather than for a genuinely confirming
book.

WHAT IS COMPARED
The order-book gate is replayed at every timestamp pm_books logged, and four
entry policies are graded on the same games:

    any      - bet if the book EVER confirmed (what "refresh constantly and post
               whatever qualifies" actually amounts to)
    first    - same games as `any`, but entered at the first qualifying moment
    t30      - confirmed at the last reading at least 30 min before first pitch
               (a fixed decision time - what a bot would use)
    last     - confirmed at the final pre-game reading (closest to today's board)
    none     - no book gate at all, as the baseline

If `any` beats `t30`, faster refreshing is finding real late signal. If `any`
underperforms while carrying more bets, it is harvesting noise, and the extra
picks are worth less than the ones already on the board.

SCOPE, stated plainly
Only the ORDER-BOOK gate is replayed over time. The consensus and line gates are
held at their stored end-of-day values, because the picks file records only the
final public/handle read - what covers said at 2pm is not recoverable. That is
the honest limit here, and it happens to isolate exactly the component under
suspicion, since the book gate is the one driven by a noisy instantaneous
quantity.

Writes output/cadence_test.md. Reporting only.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
from pathlib import Path

from . import grade, mlb_api, pm_books
from .consensus import IMBALANCE_MIN, MAX_SPREAD, MIN_READINGS, line_tag
from .pregame_money import HOLDOUT_FROM, MIN_N

log = logging.getLogger("cadence_test")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
T_MINUS = 30 * 60          # the fixed decision point, 30 min before first pitch
POLICIES = ["any", "first", "t30", "last", "none"]


def _clean(readings) -> list:
    out = []
    for r in readings or []:
        if r.get("empty"):
            continue
        b, a = r.get("bid"), r.get("ask")
        if (isinstance(b, (int, float)) and isinstance(a, (int, float))
                and a > b and (a - b) <= MAX_SPREAD):
            out.append(r)
    out.sort(key=lambda r: r.get("t", 0))
    return out


def _confirms_at(reads: list, upto: int, consensus_is_adv: bool) -> bool | None:
    """The live confirmation test, evaluated using only readings up to `upto`.
    None when there is not yet enough data to have an opinion."""
    win = [r for r in reads if r.get("t", 0) <= upto]
    if len(win) < MIN_READINGS:
        return None
    first, last = win[0], win[-1]
    drift = (last["bid"] + last["ask"]) / 2 - (first["bid"] + first["ask"]) / 2
    bs, as_ = last.get("bid_sz") or 0, last.get("ask_sz") or 0
    imb = (bs - as_) / (bs + as_) if (bs + as_) > 0 else 0.0
    toward_adv = drift > 0 or imb > IMBALANCE_MIN
    return toward_adv if consensus_is_adv else (not toward_adv)


def _start_ts(iso) -> int | None:
    try:
        return int(dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


def collect() -> list:
    recs = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        pb = pm_books.load_day(date)
        if not pb:
            continue
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        day = json.loads(Path(f).read_text())
        for g in day.get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            matchup = g.get("matchup") or ""
            if " @ " not in matchup:
                continue
            pc = g.get("pick_criteria") or {}
            chk = g.get("public_check") or {}
            maj = (g.get("public_majority") or {}).get("team")
            # consensus gate, from stored end-of-day values
            if chk.get("money") != "with public" or not maj:
                continue
            away, home = matchup.split(" @ ")
            adv = pc.get("advantage_team")
            if maj not in (away, home) or not adv:
                continue
            odds = (pc.get("advantage_moneyline") if maj == adv
                    else pc.get("opponent_moneyline"))
            if not isinstance(odds, int):
                continue
            reads = _clean((pb.get("games", {}).get(str(g.get("game_pk"))) or {})
                           .get("readings"))
            if len(reads) < MIN_READINGS:
                continue
            start = _start_ts(g.get("game_datetime"))
            if not start:
                continue

            is_adv = (maj == adv)
            # confirmation state at every logged timestamp
            timeline = []
            for r in reads:
                c = _confirms_at(reads, r.get("t", 0), is_adv)
                if c is not None:
                    timeline.append((r["t"], c))
            if not timeline:
                continue

            ever = any(c for _t, c in timeline)
            pre30 = [(t, c) for t, c in timeline if t <= start - T_MINUS]
            at_t30 = pre30[-1][1] if pre30 else None
            pre = [(t, c) for t, c in timeline if t <= start]
            at_last = pre[-1][1] if pre else None

            recs.append({
                "date": date, "won": res["winner"] == maj, "odds": odds,
                "line": line_tag(g, maj),
                "ever": ever, "t30": at_t30, "last": at_last,
                "flips": sum(1 for i in range(1, len(timeline))
                             if timeline[i][1] != timeline[i - 1][1]),
                "ticks": len(timeline),
            })
    return recs


def _select(recs, policy: str, require_line: bool) -> list:
    out = []
    for r in recs:
        if require_line and r["line"] != "against":
            continue
        if policy in ("any", "first"):
            ok = r["ever"]
        elif policy == "t30":
            ok = r["t30"] is True
        elif policy == "last":
            ok = r["last"] is True
        else:
            ok = True
        if ok:
            out.append(r)
    return out


def _fmt(rows, days: int) -> str:
    if not rows:
        return "—"
    w = sum(1 for x in rows if x["won"])
    u = sum(grade.american_profit(x["odds"]) if x["won"] else -1 for x in rows)
    per = len(rows) / days if days else 0
    tag = "" if len(rows) >= MIN_N else " _(thin)_"
    return (f"{w}-{len(rows)-w} · {u:+.1f}u · **{u/len(rows):+.1%}** "
            f"(n={len(rows)}, {per:.1f}/day){tag}")


def build() -> str:
    recs = collect()
    days = len({r["date"] for r in recs})
    md = ["# Does a faster refresh find better picks, or just more?", "",
          "_The order-book gate replayed at every timestamp `pm_books` logged. "
          "`any` is what 'refresh constantly and post whatever qualifies' comes "
          "to; `t30` is a fixed decision point 30 minutes before first pitch; "
          "`last` is closest to today's hourly board._", "",
          "## Coverage", "",
          f"- games clearing the consensus gate with a usable book log: **{len(recs)}**",
          f"- slate days: **{days}**", ""]
    if len(recs) < MIN_N:
        return "\n".join(md + ["Too few games to read.", ""])

    churn = [r for r in recs if r["ever"] and r["last"] is not True]
    flippy = [r for r in recs if r["flips"] > 0]
    md += ["## How much does the gate actually flap?", "",
           f"- games where the book confirmed at some point: "
           f"**{sum(1 for r in recs if r['ever'])}**",
           f"- of those, NOT confirming by the last pre-game reading: "
           f"**{len(churn)}** — these are picks a fast refresh would have posted "
           "and the rule would later have withdrawn",
           f"- games whose confirmation flips at least once: **{len(flippy)}** "
           f"of {len(recs)}",
           f"- median logged readings per game: "
           f"**{sorted(r['ticks'] for r in recs)[len(recs)//2]}**", ""]

    for require_line in (True, False):
        head = ("line-against required (the live setting)" if require_line
                else "no line filter")
        md += [f"## {head}", "",
               "| entry policy | all-time | in-sample | holdout |", "|---|---|---|---|"]
        for p in POLICIES:
            sub = _select(recs, p, require_line)
            pre = [r for r in sub if r["date"] < HOLDOUT_FROM]
            post = [r for r in sub if r["date"] >= HOLDOUT_FROM]
            md.append(f"| `{p}` | {_fmt(sub, days)} | {_fmt(pre, days)} | "
                      f"{_fmt(post, days)} |")
        md.append("")

    md += ["## Reading this", "",
           "If `any` beats `t30` on ROI, faster refreshing is catching real late "
           "signal and is worth doing. If `any` carries more bets at a worse ROI, "
           "the extra picks are noise crossings - the gate was sampled until it "
           "said yes - and the current cadence is already taking the better half.",
           "",
           "_Only the order-book gate is replayed over time; the consensus and "
           "line gates are held at their stored end-of-day values, since the "
           "picks file keeps only the final public read. That limit isolates the "
           "book gate, which is the component driven by a noisy instantaneous "
           "quantity and the one under suspicion._"]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "cadence_test.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
