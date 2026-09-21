"""
Did the gate change help in every month, or only in the good one?

THE CONCERN, WHICH IS CORRECT
The gates were retuned using data that includes August, and August was hot: the
picks went 25-4 (+59%) that month against 13-9 (-0%) in September. A change
tuned on a hot month can be fitting the month rather than the rule.

Worse, the validation I quoted does not clear this. The confirm=BOTH change was
tested against the MLB holdout, which begins 2026-07-23 - so August sits INSIDE
that holdout. "+26.4% holdout" is partly the month in question, and a holdout
that contains the thing you are worried about is not a holdout for that worry.

THE TEST THAT DOES ANSWER IT
Run both configurations - the old gates and the new ones - separately in each
calendar month, and compare. A real improvement shows up in months it was not
tuned on. If the new settings only win in August, the change is fitting and
should be reverted.

    old: confirm EITHER signal, line move >= 1.0%
    new: confirm BOTH signals,  line move >= 0.5%

Also reports the leave-August-out comparison directly, since that is the precise
form of the question.

Writes output/change_check.md.
"""

from __future__ import annotations

import glob
import json
import logging
from collections import defaultdict
from pathlib import Path

from . import consensus as C, grade, mlb_api

log = logging.getLogger("change_check")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

OLD = {"both": False, "move": 0.01}
NEW = {"both": True, "move": 0.005}


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
            if chk.get("money") != "with public" or not maj or not adv:
                continue
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            odds = a_ml if maj == adv else o_ml
            mm = metrics.get(g.get("game_pk"))
            shift = (pc.get("line_check") or {}).get("implied_shift")
            if not isinstance(odds, int) or not mm or not isinstance(shift, (int, float)):
                continue
            toward = shift if maj == adv else -shift
            rows.append({
                "date": date, "odds": odds, "won": res["winner"] == maj,
                "drift_ok": mm["drift"] > 0,
                "size_ok": mm["imbalance"] > C.IMBALANCE_MIN,
                "is_adv": maj == adv, "toward": toward,
            })
    return rows


def _sel(rows, cfg):
    out = []
    for r in rows:
        toward_adv = ((r["drift_ok"] and r["size_ok"]) if cfg["both"]
                      else (r["drift_ok"] or r["size_ok"]))
        if not (toward_adv if r["is_adv"] else not toward_adv):
            continue
        if r["toward"] > -cfg["move"]:
            continue
        out.append(r)
    return out


def _stat(rs):
    if not rs:
        return "—", 0.0, 0
    w = sum(1 for r in rs if r["won"])
    u = sum(grade.american_profit(r["odds"]) if r["won"] else -1 for r in rs)
    return f"{w}-{len(rs)-w}", u / len(rs), len(rs)


def build() -> str:
    rows = collect()
    md = ["# Did the gate change help in every month, or only the good one?", "",
          "_The gates were retuned on data including August, and August was hot. "
          "The validation I quoted does not clear this: the confirm change was "
          "tested against a holdout beginning 2026-07-23, so August sits INSIDE "
          "it. A holdout containing the thing you are worried about is not a "
          "holdout for that worry._", "",
          "| | old | new |", "|---|---|---|",
          "| confirm | EITHER signal | **BOTH** signals |",
          "| line move | ≥1.0% | **≥0.5%** |", "",
          f"- games reaching the book gate: **{len(rows)}**", ""]
    if len(rows) < 100:
        return "\n".join(md + ["Too few games.", ""])

    by = defaultdict(list)
    for r in rows:
        by[r["date"][:7]].append(r)

    md += ["## Month by month", "",
           "| month | old record | old ROI | new record | new ROI | change |",
           "|---|---|---|---|---|---|"]
    for mth in sorted(by):
        o, oroi, on = _stat(_sel(by[mth], OLD))
        n, nroi, nn = _stat(_sel(by[mth], NEW))
        if on == 0 and nn == 0:
            continue
        delta = (nroi - oroi) * 100
        md.append(f"| {mth} | {o} ({on}) | {oroi:+.1%} | {n} ({nn}) | "
                  f"{nroi:+.1%} | **{delta:+.1f} pts** |")
    md.append("")

    o, oroi, on = _stat(_sel(rows, OLD))
    n, nroi, nn = _stat(_sel(rows, NEW))
    md += ["## Everything, and everything except August", "",
           "| period | old | new | change |", "|---|---|---|---|",
           f"| all months | {o} · {oroi:+.1%} (n={on}) | {n} · {nroi:+.1%} "
           f"(n={nn}) | **{(nroi-oroi)*100:+.1f} pts** |"]
    ex = [r for r in rows if r["date"][:7] != "2026-08"]
    o2, oroi2, on2 = _stat(_sel(ex, OLD))
    n2, nroi2, nn2 = _stat(_sel(ex, NEW))
    md += [f"| **excluding August** | {o2} · {oroi2:+.1%} (n={on2}) | "
           f"{n2} · {nroi2:+.1%} (n={nn2}) | "
           f"**{(nroi2-oroi2)*100:+.1f} pts** |", ""]
    if nn2 >= 15 and on2 >= 15:
        md += ([f"**The change survives August's removal.** It is worth "
                f"{(nroi2-oroi2)*100:+.1f} points on the months it was not "
                "tuned on, so it is not the hot month talking.", ""]
               if nroi2 > oroi2 else
               [f"**The change does NOT survive August's removal.** Outside "
                f"August it is worth {(nroi2-oroi2)*100:+.1f} points, which "
                "means the improvement was the hot month. Revert it.", ""])
    else:
        md += ["_Too few picks outside August to judge - which is itself the "
               "answer: the evidence for this change is concentrated in one "
               "month._", ""]

    md += ["## How to read this", "",
           "- a change that helps in **most months** is a change to the rule",
           "- a change that helps in **one month** is a change to that month",
           "- September is the only month fully after the retune was conceived, "
           "so it is the closest thing to a clean test available", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "change_check.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
