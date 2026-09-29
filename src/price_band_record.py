"""
Do they win more than they lose at that price? Straight record, home and away.

THE QUESTION, AS ASKED
Not whether a price has value - whether a team WINS MORE THAN IT LOSES at that
price band across the season, as a way of deciding whether to trust a board pick
on that team at that price. Wins and losses, split home and away. No ROI, no
break-even, no expected value; those answer a different question and I kept
answering it instead of this one.

One line of context and then out of the way: a favourite winning more than it
loses is normal rather than notable, so the band's own baseline is printed
beside every team - "won 6 of 9" means something different at -200, where the
band as a whole wins 68%, than at +150, where it wins 38%. The comparison that
makes a record informative is against its band, not against .500.

WHAT IS HERE
  by band          every team's W-L in each price band, with the band baseline
  home and away    the same split, because a team can be trustworthy at home
                   and not on the road and the pooled record hides it
  above the band   which teams beat their band's win rate, and how many would
                   be expected to by chance - 30 teams means a handful will
                   clear any bar, so the count is what says whether any of it
                   means anything

Bands are the same six used in team_calibration, so the two reports can be read
side by side.

Writes output/price_band_record.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
from collections import defaultdict
from pathlib import Path

from . import mlb_api

log = logging.getLogger("price_band_record")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 10000
MIN_BAND = 6          # a team needs this many games in a band to be listed

BANDS = [("−200 or shorter", -100000, -200),
         ("−199 to −150", -199, -150),
         ("−149 to −110", -149, -110),
         ("−109 to +109", -109, 109),
         ("+110 to +149", 110, 149),
         ("+150 to +199", 150, 199),
         ("+200 or longer", 200, 100000)]


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
            a, o = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            away, home = m.split(" @ ")
            if adv not in (away, home) or not isinstance(a, int) or not isinstance(o, int):
                continue
            price = {adv: a, (home if adv == away else away): o}
            for t in (away, home):
                rows.append({"date": date, "team": t, "odds": price[t],
                             "won": res["winner"] == t, "home": t == home})
    return rows


def _band(odds: int) -> str | None:
    for lab, lo, hi in BANDS:
        if lo <= odds <= hi:
            return lab
    return None


def _wl(rs) -> tuple[int, int]:
    w = sum(1 for r in rs if r["won"])
    return w, len(rs) - w


def _cell(rs) -> str:
    if not rs:
        return "—"
    w, l = _wl(rs)
    return f"{w}-{l} ({w/(w+l):.0%})"


def build() -> str:
    rows = collect()
    md = ["# Do they win more than they lose at that price?", "",
          "_Straight wins and losses at a price band, home and away — a trust "
          "check on a board pick, not a value calculation._", "",
          "_One piece of context and then out of the way: a favourite winning "
          "more than it loses is normal, not notable. So every team's record is "
          "printed beside its **band baseline** — \"6 of 9\" means something very "
          "different at −200, where the whole band wins 68%, than at +150, where "
          "it wins 38%. The informative comparison is against the band, not "
          "against .500._", "",
          f"- graded team-games: **{len(rows)}**", ""]
    if len(rows) < 500:
        return "\n".join(md + ["Not enough games.", ""])

    by_band = defaultdict(list)
    for r in rows:
        b = _band(r["odds"])
        if b:
            by_band[b].append(r)

    md += ["## The bands themselves", "",
           "| price band | all | at home | on the road |", "|---|---|---|---|"]
    base = {}
    for lab, _, _ in BANDS:
        rs = by_band.get(lab) or []
        if not rs:
            continue
        w, l = _wl(rs)
        base[lab] = w / (w + l)
        md.append(f"| {lab} | {_cell(rs)} | "
                  f"{_cell([r for r in rs if r['home']])} | "
                  f"{_cell([r for r in rs if not r['home']])} |")
    md.append("")

    # ---- per team, per band ---------------------------------------------
    teams = sorted({r["team"] for r in rows})
    for lab, _, _ in BANDS:
        rs = by_band.get(lab) or []
        if len(rs) < 60:
            continue
        md += [f"## {lab} — band wins {base[lab]:.0%}", "",
               "| team | record | vs band | at home | on the road |",
               "|---|---|---|---|---|"]
        listed = []
        for t in teams:
            tr = [r for r in rs if r["team"] == t]
            if len(tr) < MIN_BAND:
                continue
            w, l = _wl(tr)
            wp = w / (w + l)
            listed.append((t, tr, wp))
        for t, tr, wp in sorted(listed, key=lambda x: -x[2]):
            md.append(f"| {t} | **{_cell(tr)}** | "
                      f"{(wp - base[lab]) * 100:+.0f} pts | "
                      f"{_cell([r for r in tr if r['home']])} | "
                      f"{_cell([r for r in tr if not r['home']])} |")
        above = sum(1 for _, _, wp in listed if wp > base[lab])
        winning = sum(1 for _, tr, _ in listed if _wl(tr)[0] > _wl(tr)[1])
        # how many of these teams would beat the band by chance, if every team
        # were simply a band-average team
        rng = random.Random(len(lab))
        counts = []
        sizes = [len(tr) for _, tr, _ in listed]
        for _ in range(TRIALS):
            counts.append(sum(
                1 for n in sizes
                if sum(1 for _ in range(n) if rng.random() < base[lab]) / n > base[lab]))
        md += ["",
               f"- teams listed (≥{MIN_BAND} games in this band): **{len(listed)}**",
               f"- **winning records** (more wins than losses): **{winning}**",
               f"- **above the band's own rate: {above}** — if every team were "
               f"just a band-average team, you would expect "
               f"**{sum(counts)/len(counts):.1f}**",
               "- " + ("more teams beat the band than chance explains, so some of "
                       "this may be real" if above > sum(counts) / len(counts) + 2
                       else "that is what chance produces, so a team being above "
                            "its band here is not evidence it can be trusted "
                            "there"), ""]

    md += ["## How to use this", "",
           "- **read the `vs band` column, not the record.** Winning 7 of 10 at "
           "−180 is below par; winning 4 of 10 at +180 is above it",
           "- **home and away can disagree**, and when they do the pooled record "
           "is the least useful of the three numbers",
           f"- a team needs {MIN_BAND} games in a band to appear, and most cells "
           "are still small — one result moves a 6-game record by 17 points", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "price_band_record.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
