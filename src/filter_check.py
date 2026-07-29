"""
Filter check: what the line-against filter actually does to the consensus board.

The filter was motivated by a test on "line disagrees with handle" across ALL
games (n=55, +17.3%). But stacked on top of the consensus rule it is far more
selective - the intersection of the two conditions is much smaller. This grades
the three buckets directly so the combined rule is judged on its own population
rather than on the broader test that inspired it.

Writes output/filter_check.md.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

from . import consensus, grade, mlb_api

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
HOLDOUT_FROM = "2026-07-23"


def collect():
    kept, cut, allc = [], [], []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        day = json.loads(Path(f).read_text())
        m = consensus.book_metrics(date)
        if not m:
            continue
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        for g in day.get("games", []):
            res = results.get(g.get("game_pk"))
            if not res or not res.get("final") or not res.get("winner"):
                continue
            consensus.REQUIRE_LINE_AGAINST = False
            play = consensus.evaluate(g, m)
            if not play:
                continue
            maj = (g.get("public_majority") or {}).get("team")
            tag = consensus.line_tag(g, maj) if maj else "flat"
            row = {"won": res["winner"] == play["bet"], "odds": play["odds"],
                   "date": date, "holdout": date >= HOLDOUT_FROM, "tag": tag}
            allc.append(row)
            (kept if tag == "against" else cut).append(row)
    consensus.REQUIRE_LINE_AGAINST = True
    return allc, kept, cut


def _fmt(rows):
    if not rows:
        return "—"
    w = sum(1 for r in rows if r["won"])
    u = sum(grade.american_profit(r["odds"]) if r["won"] else -1 for r in rows)
    return f"{w}-{len(rows)-w} ({w/len(rows):.0%}) · {u:+.1f}u · **{u/len(rows):+.1%}** (n={len(rows)})"


def _row(lab, rows):
    return (f"| {lab} | {_fmt(rows)} | {_fmt([r for r in rows if not r['holdout']])} "
            f"| {_fmt([r for r in rows if r['holdout']])} |")


def build() -> str:
    allc, kept, cut = collect()
    md = ["# Filter check — line-against filter on the consensus board", "",
          "_All three buckets are consensus-qualified picks. 'KEPT' is what the "
          "live board now bets; 'CUT' is what the filter throws away._", "",
          "| bucket | ALL | in-sample | HOLDOUT |", "|---|---|---|---|",
          _row("consensus, NO line filter (old board)", allc),
          _row("KEPT — line moved against the money", kept),
          _row("CUT — line moved with/flat", cut), ""]
    if allc:
        md.append(f"_Filter keeps {len(kept)}/{len(allc)} "
                  f"({len(kept)/len(allc):.0%}) of consensus picks._")
    return "\n".join(md)


def main() -> None:
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "filter_check.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
