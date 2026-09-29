"""
Is every gate earning its weight, in every period - or did one month carry it?

THE QUESTION
`near_miss` showed the gates are not equal when pooled: games failing only the
book gate returned -12.6%, games failing only the line gate +1.0%. But a pooled
number can hide a gate that worked for three weeks and has done nothing since,
which is exactly how a rule quietly stops being a rule.

THE METHOD - ABLATION, NOT CORRELATION
For each gate, the games it UNIQUELY rejects: those passing every other gate and
failing only this one. That population is what the gate is saving you from, and
its ROI is the gate's contribution. A gate earns its weight when the games it
rejects are consistently worse than the picks it lets through.

Then the same split by time window. A gate whose contribution flips sign between
periods is not a gate, it is a coin that landed the same way for a while.

WHAT COUNTS AS PASSING
  * the rejected games should be WORSE than the picks in most windows
  * the sign should be stable - not +20 one month and -20 the next
  * enough rejections to say anything at all

Uses the CURRENT live settings, so this audits the rule as it actually runs
today rather than as it ran when each gate was added.

Writes output/gate_audit.md.
"""

from __future__ import annotations

import glob
import json
import logging
import statistics as st
from collections import defaultdict
from pathlib import Path

from . import consensus as C, grade, mlb_api

log = logging.getLogger("gate_audit")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MIN_REJ = 10

GATES = ["handle=tickets", "book read", "book confirms", "line against"]


def collect() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            metrics = C.book_metrics(date)
            results = mlb_api.results_for(date)
        except Exception:
            continue
        for g in json.loads(Path(f).read_text()).get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            pc = g.get("pick_criteria") or {}
            chk = g.get("public_check") or {}
            maj = (g.get("public_majority") or {}).get("team")
            adv = pc.get("advantage_team")
            m = g.get("matchup") or ""
            if not maj or not adv or " @ " not in m:
                continue
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            odds = a_ml if maj == adv else o_ml
            if not isinstance(odds, int) or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            mm = metrics.get(g.get("game_pk"))
            shift = (pc.get("line_check") or {}).get("implied_shift")
            toward = (shift if maj == adv else -shift) if isinstance(shift, (int, float)) else None
            rows.append({
                "date": date, "odds": odds, "won": res["winner"] == maj,
                "gates": {
                    "handle=tickets": chk.get("money") == "with public",
                    "book read": mm is not None,
                    # evaluated under the CURRENT settings, not the old ones
                    "book confirms": (C._confirms(mm, maj == adv) if mm else False),
                    "line against": (toward is not None
                                     and toward <= -C.LINE_MOVE_MIN),
                },
            })
    return rows


def _roi(rs):
    if not rs:
        return 0.0
    return sum(grade.american_profit(r["odds"]) if r["won"] else -1
               for r in rs) / len(rs)


def _rec(rs):
    w = sum(1 for r in rs if r["won"])
    return f"{w}-{len(rs)-w}"


def _picks(rs):
    return [r for r in rs if all(r["gates"].values())]


def _uniquely_rejected(rs, gate):
    """Passes every other gate, fails only this one - what the gate saves you from."""
    return [r for r in rs
            if not r["gates"][gate]
            and all(v for k, v in r["gates"].items() if k != gate)]


def _windows(rows):
    """Calendar months, since that is how anyone would eyeball a losing streak."""
    by = defaultdict(list)
    for r in rows:
        by[r["date"][:7]].append(r)
    return [(k, by[k]) for k in sorted(by)]


def build() -> str:
    rows = collect()
    md = ["# Gate audit — is each gate earning its weight, in every period?", "",
          "_For each gate, the games it UNIQUELY rejects: passing every other "
          "gate and failing only this one. That is what the gate saves you "
          "from, and a gate earns its weight when those games are consistently "
          "worse than the picks it lets through._", "",
          f"- graded games with a consensus side: **{len(rows)}**",
          f"- evaluated under the CURRENT settings: confirm **BOTH**, line "
          f"**≥{C.LINE_MOVE_MIN:.1%}**, imbalance **>{C.IMBALANCE_MIN}**", ""]
    if len(rows) < 200:
        return "\n".join(md + ["Too few games.", ""])

    picks = _picks(rows)
    md += [f"- picks under these gates: **{_rec(picks)} · {_roi(picks):+.1%}** "
           f"(n={len(picks)})", "",
           "## Overall — what each gate rejects", "",
           "| gate | uniquely rejects | their ROI | picks' ROI | gate is worth |",
           "|---|---|---|---|---|"]
    rej = {}
    for gate in GATES:
        sub = _uniquely_rejected(rows, gate)
        rej[gate] = sub
        if not sub:
            md.append(f"| `{gate}` | 0 | — | — | — |")
            continue
        md.append(f"| `{gate}` | {len(sub)} | **{_roi(sub):+.1%}** | "
                  f"{_roi(picks):+.1%} | **{(_roi(picks)-_roi(sub))*100:+.1f} pts** |")
    md.append("")

    # ---- per month ----
    wins = _windows(rows)
    md += ["## By month — does each gate hold up throughout?", "",
           "_A gate whose contribution flips sign between periods is not a gate, "
           "it is a coin that landed the same way for a while._", "",
           "| month | games | picks | " + " | ".join(f"`{g}`" for g in GATES) + " |",
           "|---" * (len(GATES) + 3) + "|"]
    per_gate = defaultdict(list)
    for name, sub in wins:
        p = _picks(sub)
        cells = []
        for gate in GATES:
            r = _uniquely_rejected(sub, gate)
            if len(r) < MIN_REJ:
                cells.append(f"_{len(r)}_")
                continue
            worth = _roi(p) - _roi(r) if p else None
            per_gate[gate].append(worth if worth is not None else 0.0)
            cells.append(f"{worth*100:+.0f}pts ({len(r)})" if worth is not None else "—")
        md.append(f"| {name} | {len(sub)} | {_rec(p)} {_roi(p):+.0%} | "
                  + " | ".join(cells) + " |")
    md.append("")
    md += ["_Cells show what the gate was worth that month - the picks' ROI "
           "minus the ROI of what it rejected - with the rejection count. "
           "Italic means too few rejections to judge._", ""]

    # ---- verdict per gate ----
    md += ["## Verdict", "", "| gate | months judged | positive | median worth | "
           "verdict |", "|---|---|---|---|---|"]
    for gate in GATES:
        v = per_gate.get(gate) or []
        if len(v) < 2:
            md.append(f"| `{gate}` | {len(v)} | — | — | too few months to judge |")
            continue
        pos = sum(1 for x in v if x > 0)
        med = st.median(v)
        verdict = ("**earns it** — positive in most months"
                   if pos >= len(v) * 0.6 and med > 0.05 else
                   "**marginal** — helps on average, inconsistent"
                   if med > 0 else
                   "**not earning it** — median contribution is negative")
        md.append(f"| `{gate}` | {len(v)} | {pos}/{len(v)} | {med:+.0%} | {verdict} |")
    md += ["", "_A gate that only rejects a handful of games cannot be judged "
           "from this - absence of evidence, not evidence it is useless._", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "gate_audit.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
