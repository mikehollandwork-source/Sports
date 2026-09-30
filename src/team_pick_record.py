"""
Our own record by the team we picked - and whether any of it is real.

THE QUESTION
"Does the board do better on some teams than others?" The ledger answers the
first half directly: every entry carries the team bet, the result and the price.

THE HALF THAT NEEDS CARE
Thirty teams and a median of eight picks each. Scanning them for the best will
always turn up something, exactly as league_calibration found for team pricing,
so the scan is corrected rather than ranked and quoted.

Two statistics, because they answer different questions:

  ROI            what the picks returned. Dominated by price - five wins at
                 +180 outrank fifteen at -160 - so a team can top it on luck
                 with long prices.
  beat its price actual wins minus the wins the prices implied, in standard
                 deviations. This is the one that says the picks were BETTER
                 than the market on that team, and it is what gets corrected.

The null redraws every pick from its own price-implied probability and
recomputes all teams, keeping the maximum. A team counts only if it beats what
the best of twenty-odd reaches on noise.

Implied probability is used raw, without de-vigging, because the ledger stores
only the side taken. That OVERSTATES the expected wins, so every z here is
conservative - a team that clears the bar would clear it by more with exact
probabilities.

Writes output/team_pick_record.md.
"""

from __future__ import annotations

import json
import logging
import math
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

log = logging.getLogger("team_pick_record")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 20000
MIN_PICKS = 5


def _implied(o: int) -> float:
    return (abs(o) / (abs(o) + 100)) if o < 0 else (100 / (o + 100))


def _profit(o: int) -> float:
    return (100 / abs(o)) if o < 0 else (o / 100)


def _z(v: list[dict], wins: list[bool] | None = None) -> float:
    ps = [_implied(x["odds"]) for x in v]
    exp = sum(ps)
    sd = math.sqrt(sum(p * (1 - p) for p in ps))
    act = (sum(1 for x in v if x["result"] == "W") if wins is None else sum(wins))
    return (act - exp) / sd if sd else 0.0


def build() -> str:
    try:
        entries = json.loads((OUTPUT_DIR / "ledger.json").read_text())["plays"]["entries"]
    except (OSError, ValueError, KeyError) as exc:
        return f"# Our record by team\n\nLedger unreadable: {exc}\n"
    by: dict[str, list] = defaultdict(list)
    for x in entries:
        if isinstance(x.get("odds"), int) and x.get("bet") and x.get("result") in ("W", "L"):
            by[x["bet"]].append(x)
    md = ["# Our record by the team we picked", "",
          "_The ledger answers this directly. The care is in the reading: thirty "
          "teams and a median of eight picks each means scanning for the best "
          "always turns up something, so the scan is corrected rather than "
          "ranked and quoted._", "",
          "_**ROI** is dominated by price — five wins at +180 outrank fifteen at "
          "−160 — so a team can top it on luck. **Beat its price** is actual wins "
          "against the wins the prices implied, in SDs, and is the one that says "
          "the picks were better than the market._", "",
          f"- graded picks: **{sum(len(v) for v in by.values())}** across "
          f"**{len(by)}** teams", ""]
    if not by:
        return "\n".join(md + ["No graded picks.", ""])

    rows = []
    for t, v in by.items():
        w = sum(1 for x in v if x["result"] == "W")
        u = sum(x.get("profit", 0.0) for x in v)
        rows.append((t, len(v), w, len(v) - w, u, u / len(v), _z(v)))
    rows.sort(key=lambda r: -r[6])
    md += ["| team | record | units | ROI | beat its price |",
           "|---|---|---|---|---|"]
    for t, n, w, l, u, roi, z in rows:
        thin = "" if n >= MIN_PICKS else " ⚠"
        md.append(f"| {t}{thin} | {w}-{l} | {u:+.2f}u | {roi:+.1%} | "
                  f"**{z:+.2f} SD** |")
    md += ["", f"_⚠ marks fewer than {MIN_PICKS} picks — shown, not read._", ""]

    teams = {t: v for t, v in by.items() if len(v) >= MIN_PICKS}
    if len(teams) < 5:
        return "\n".join(md)
    obs = {t: _z(v) for t, v in teams.items()}
    best = max(obs, key=obs.get)
    rng = random.Random(4050)
    hi = []
    for _ in range(TRIALS):
        hi.append(max(_z(v, [rng.random() < _implied(x["odds"]) for x in v])
                      for v in teams.values()))
    p = (sum(1 for x in hi if x >= obs[best]) + 1) / (TRIALS + 1)
    md += [f"## Corrected for scanning {len(teams)} teams", "",
           f"- best: **{best}** at {obs[best]:+.2f} SD over {len(teams[best])} picks",
           f"- the best of {len(teams)} on noise alone reaches "
           f"{st.median(hi):+.2f} SD median, {sorted(hi)[int(.95*TRIALS)]:+.2f} "
           f"at the 95th",
           f"- **corrected p = {p:.4f}**", ""]

    # stability of the leader, which is what killed every other candidate
    v = sorted(teams[best], key=lambda x: x["date"])
    mid = len(v) // 2
    rh = random.Random(77)
    tag = [rh.random() < 0.5 for _ in v]
    md += [f"## Is {best} stable, or one stretch?", "",
           "| split | record | beat its price |", "|---|---|---|"]
    for lab, sub in (("first half (by date)", v[:mid]),
                     ("second half (by date)", v[mid:]),
                     ("random half", [x for x, t in zip(v, tag) if t]),
                     ("the other random half", [x for x, t in zip(v, tag) if not t])):
        if sub:
            w = sum(1 for x in sub if x["result"] == "W")
            md.append(f"| {lab} | {w}-{len(sub)-w} | {_z(sub):+.2f} SD |")
    bym = defaultdict(list)
    for x in v:
        bym[x["date"][:7]].append(x)
    md += ["", "| month | record | beat its price |", "|---|---|---|"]
    for m in sorted(bym):
        sub = bym[m]
        w = sum(1 for x in sub if x["result"] == "W")
        md.append(f"| {m} | {w}-{len(sub)-w} | {_z(sub):+.2f} SD |")
    md += ["", f"- most recent pick on {best}: **{v[-1]['date']}**", "",
           "## What this can and cannot be used for", "",
           "- it is retrospective TEAM SELECTION. The rule already backs these "
           "teams when they qualify; there is no separate action in knowing which "
           "ones it has been right about",
           "- a leader concentrated in one month is a streak the correction "
           "cannot fully price, because the permutation treats picks as "
           "independent and a team on a run is not",
           "- implied probabilities are not de-vigged, so every SD here is "
           "conservative", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "team_pick_record.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
