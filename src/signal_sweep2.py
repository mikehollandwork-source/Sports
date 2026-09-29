"""
The rest of the signals, isolated, both directions.

`signal_sweep` covered sixteen. This covers everything else on the board that
can name a side - thirty-odd, in five families:

  the OTHER venue      Kalshi's drift, size lean and closing price, and the
                       two venues agreeing or disagreeing. Polymarket has been
                       isolated; Kalshi never has, and it is a second pool of
                       real money.
  the crowd, split up  covers consensus %, the covers forum, Wikipedia
                       pageviews, Polymarket's bet %, VSIN's bet %, the
                       blended lean, and which side the book profits from.
                       These have only ever been tested BLENDED, so a source
                       that carries signal and one that cancels it are
                       indistinguishable in everything done so far.
  the model, split up  offense and pitching indexes, wOBA, ISO, discipline,
                       speed, platoon, starter FIP (last-5 and season),
                       bullpen FIP, combined FIP, arms down, schedule faced.
                       The blend has been tested; the parts have not, and a
                       blend at -1.3% can hide a part that works.
  the win condition    complete_win_condition, scored_target,
                       held_under_ceiling, out_hit, last-5 wins, the
                       runs-to-win bar, projected run differential. Built as
                       reporting-only and never once scored against results.
  the park table       raw wOBA/ISO against park-neutralised wOBA/ISO, as
                       separate rows. park_factors.py has never been
                       validated; if neutralising helps, the neutral row beats
                       the raw one.

SAME BAR AS BEFORE, AND IT IS A HIGH ONE
Every row prints both directions and their `sum`, because both directions pay
the hold: they add to about minus twice the vig, not to zero, so a signal at
-6% does NOT have a +6% fade waiting behind it. Roughly seventy cells enter
one grid, and the best and worst are corrected by max- and min-statistic
permutation with winners redrawn from de-vigged prices. Whatever survives is
split-halved. Thirty-five signals is a lot of lottery tickets, so the
correction is doing most of the work here - that is the point of it.

Not included, because they cannot name a side: weather, roof, umpire (None
pre-game on most boards), confidence, signals_hit, sharp_money. Those are
filters, and `untested_fields` already scanned filters.

Writes output/signal_sweep2.md.
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import logging
import random
import statistics as st
from pathlib import Path

from . import consensus as C, grade, mlb_api, pm_books
from .pregame_money import _implied
from .signal_sweep import _fmt, _roi, _view
from .venue_signal import _pregame, _venue

log = logging.getLogger("signal_sweep2")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TRIALS = 3000
MIN_CELL = 60


def _lower(h, a, home, away):
    """Side with the LOWER value (FIP, runs-to-win: less is better)."""
    if not (isinstance(h, (int, float)) and isinstance(a, (int, float))) or h == a:
        return None
    return home if h < a else away


def _higher(h, a, home, away):
    if not (isinstance(h, (int, float)) and isinstance(a, (int, float))) or h == a:
        return None
    return home if h > a else away


def _lean(v, home, away):
    """A signed lean: positive means home."""
    if not isinstance(v, (int, float)) or v == 0:
        return None
    return home if v > 0 else away


def collect() -> list[dict]:
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        try:
            results = mlb_api.results_for(date)
            metrics = C.book_metrics(date)
            books = pm_books.load_day(date) or {}
        except Exception:
            continue
        bk = (books.get("games") or {})
        for g in json.loads(Path(f).read_text()).get("games", []):
            pk = g.get("game_pk")
            res = results.get(pk)
            m = g.get("matchup") or ""
            if not res or not res.get("final") or not res.get("winner") or " @ " not in m:
                continue
            pc = g.get("pick_criteria") or {}
            adv = pc.get("advantage_team")
            a_ml, o_ml = pc.get("advantage_moneyline"), pc.get("opponent_moneyline")
            if not adv or not isinstance(a_ml, int) or not isinstance(o_ml, int):
                continue
            away, home = m.split(" @ ")
            if adv not in (away, home):
                continue
            opp = home if adv == away else away
            price = {adv: a_ml, opp: o_ml}
            tot = _implied(a_ml) + _implied(o_ml)
            if tot <= 0:
                continue

            sa = g.get("statistical_advantage") or {}
            H, A = sa.get("home") or {}, sa.get("away") or {}
            oh, oa = H.get("offense") or {}, A.get("offense") or {}
            sh = (H.get("strength_of_schedule") or {}).get("raw") or {}
            sax = (A.get("strength_of_schedule") or {}).get("raw") or {}
            cons = g.get("consistency") or {}
            ch, ca = cons.get("home") or {}, cons.get("away") or {}
            bh, ba = ch.get("back_test") or {}, ca.get("back_test") or {}
            det = (g.get("public_majority") or {}).get("detail") or {}
            bks = det.get("books") or {}
            veg = pc.get("vegas") or {}
            bvp = g.get("bvp") or {}
            lc = pc.get("line_check") or {}

            # --- the other venue, cut at the freeze like everything else ----
            kal = None
            gb = bk.get(str(pk)) or {}
            start = gb.get("game_datetime") or g.get("game_datetime")
            side_tok = gb.get("side")          # whose token the log is written from
            if start and side_tok in (home, away):
                try:
                    cut = (dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
                           - C.LOCK_LEAD).timestamp()
                    kal = _venue(_pregame(gb.get("k_readings") or [], cut))
                except ValueError:
                    kal = None
            k_other = (home if side_tok == away else away) if side_tok in (home, away) else None
            mm = metrics.get(pk)

            def kside(val, invert=False):
                """Kalshi's log is one team's token; flip for the other side."""
                if kal is None or side_tok not in (home, away) or not val:
                    return None
                pos = side_tok if (val > 0) != invert else k_other
                return pos

            sides = {
                # ---- the other venue ----------------------------------------
                "Kalshi drift": kside(kal["drift"] if kal else None),
                "Kalshi size lean": kside(kal["imbalance"] if kal else None),
                "Kalshi favourite (closing)": (
                    (side_tok if kal["close"] > 0.5 else k_other)
                    if kal and kal["close"] != 0.5 and side_tok in (home, away) else None),
                "both venues agree (drift)": (
                    kside(kal["drift"] if kal else None)
                    if kal and mm and kside(kal["drift"])
                    == ((adv if mm["drift"] > 0 else opp)) else None),
                "venues DISAGREE — take Kalshi": (
                    kside(kal["drift"] if kal else None)
                    if kal and mm and kside(kal["drift"])
                    and kside(kal["drift"]) != (adv if mm["drift"] > 0 else opp) else None),

                # ---- the crowd, one source at a time ------------------------
                "covers consensus %": _lean(det.get("consensus_lean"), home, away),
                "covers forum": _lean(det.get("forum_lean"), home, away),
                "Wikipedia pageviews": _lean(det.get("wiki_lean"), home, away),
                "Polymarket bet %": _lean((bks.get("polymarket_bets") or {}).get("lean"),
                                          home, away),
                "VSIN bet %": _lean((bks.get("vsin_bets") or {}).get("lean"), home, away),
                "blended lean": _lean(det.get("blended_lean"), home, away),
                "book profits if this side wins": _higher(
                    veg.get("hold_home"), veg.get("hold_away"), home, away),

                # ---- the model, one part at a time --------------------------
                "offense index": _higher(H.get("offense_index"),
                                         A.get("offense_index"), home, away),
                "pitching index": _higher(H.get("pitching_index"),
                                          A.get("pitching_index"), home, away),
                "wOBA (raw)": _higher(oh.get("woba"), oa.get("woba"), home, away),
                "wOBA (park-neutral)": _higher(oh.get("woba_neutral"),
                                               oa.get("woba_neutral"), home, away),
                "ISO (raw)": _higher(oh.get("iso"), oa.get("iso"), home, away),
                "ISO (park-neutral)": _higher(oh.get("iso_neutral"),
                                              oa.get("iso_neutral"), home, away),
                "plate discipline (bb−k)": _higher(
                    (oh.get("bb_pct") - oh.get("k_pct"))
                    if isinstance(oh.get("bb_pct"), (int, float))
                    and isinstance(oh.get("k_pct"), (int, float)) else None,
                    (oa.get("bb_pct") - oa.get("k_pct"))
                    if isinstance(oa.get("bb_pct"), (int, float))
                    and isinstance(oa.get("k_pct"), (int, float)) else None, home, away),
                "speed (sb rate)": _higher(oh.get("sb_rate"), oa.get("sb_rate"),
                                           home, away),
                "platoon edge": _higher(H.get("platoon_factor"),
                                        A.get("platoon_factor"), home, away),
                "starter FIP (last 5)": _lower(H.get("starter_fip_last5"),
                                               A.get("starter_fip_last5"), home, away),
                "starter FIP (season)": _lower(H.get("starter_fip_season"),
                                               A.get("starter_fip_season"), home, away),
                "bullpen FIP (last 5)": _lower(H.get("bullpen_fip_last5"),
                                               A.get("bullpen_fip_last5"), home, away),
                "combined FIP (SoS-adj)": _lower(H.get("combined_fip_sos_adj"),
                                                 A.get("combined_fip_sos_adj"), home, away),
                "fewer bullpen arms down": _lower(H.get("pen_arms_down"),
                                                  A.get("pen_arms_down"), home, away),
                "faced tougher pitching": _higher(sh.get("bat_opp_fip"),
                                                  sax.get("bat_opp_fip"), home, away),
                "faced tougher opponents": _higher(ch.get("avg_opp_win_pct_faced"),
                                                   ca.get("avg_opp_win_pct_faced"),
                                                   home, away),
                "BvP by hand (platoon OPS)": _higher(bvp.get("home_hand_ops"),
                                                     bvp.get("away_hand_ops"), home, away),

                # ---- the win condition, scored for the first time -----------
                "complete win condition": _higher(bh.get("complete_win_condition"),
                                                  ba.get("complete_win_condition"),
                                                  home, away),
                "scored its target": _higher(bh.get("scored_target"),
                                             ba.get("scored_target"), home, away),
                "held under its ceiling": _higher(bh.get("held_under_ceiling"),
                                                  ba.get("held_under_ceiling"), home, away),
                "out-hit its opponent": _higher(bh.get("out_hit"), ba.get("out_hit"),
                                                home, away),
                "won more of its last 5": _higher(bh.get("actually_won"),
                                                  ba.get("actually_won"), home, away),
                "lower runs-to-win bar": _lower(ch.get("runs_to_win"),
                                                ca.get("runs_to_win"), home, away),
                "projected run differential": _higher(
                    (ch.get("expected_own_runs") - ch.get("expected_opponent_runs"))
                    if isinstance(ch.get("expected_own_runs"), (int, float))
                    and isinstance(ch.get("expected_opponent_runs"), (int, float)) else None,
                    (ca.get("expected_own_runs") - ca.get("expected_opponent_runs"))
                    if isinstance(ca.get("expected_own_runs"), (int, float))
                    and isinstance(ca.get("expected_opponent_runs"), (int, float)) else None,
                    home, away),

                # ---- price -------------------------------------------------
                "opening-line favourite": (
                    (adv if lc.get("open") < 0 else opp)
                    if isinstance(lc.get("open"), int) and lc.get("open") != 0 else None),
                "pitching-dog edge": (adv if pc.get("pitching_dog") else None),
                "book_stance side": (pc.get("book_stance") or {}).get("side"),
            }
            rows.append({"date": date, "winner": res["winner"], "price": price,
                         "adv": adv, "opp": opp, "sides": sides,
                         "p_adv": _implied(a_ml) / tot})
    return rows


FAMILIES = [
    ("The other venue — Kalshi, never isolated before",
     ["Kalshi drift", "Kalshi size lean", "Kalshi favourite (closing)",
      "both venues agree (drift)", "venues DISAGREE — take Kalshi"]),
    ("The crowd, one source at a time — only ever tested blended",
     ["covers consensus %", "covers forum", "Wikipedia pageviews",
      "Polymarket bet %", "VSIN bet %", "blended lean",
      "book profits if this side wins"]),
    ("The model, one part at a time — the blend hides the parts",
     ["offense index", "pitching index", "wOBA (raw)", "wOBA (park-neutral)",
      "ISO (raw)", "ISO (park-neutral)", "plate discipline (bb−k)",
      "speed (sb rate)", "platoon edge", "starter FIP (last 5)",
      "starter FIP (season)", "bullpen FIP (last 5)", "combined FIP (SoS-adj)",
      "fewer bullpen arms down", "faced tougher pitching",
      "faced tougher opponents", "BvP by hand (platoon OPS)"]),
    ("The win condition — built as reporting-only, never scored",
     ["complete win condition", "scored its target", "held under its ceiling",
      "out-hit its opponent", "won more of its last 5", "lower runs-to-win bar",
      "projected run differential"]),
    ("Price", ["opening-line favourite", "pitching-dog edge", "book_stance side"]),
]
SIGNALS = [s for _, group in FAMILIES for s in group]


def build() -> str:
    rows = collect()
    md = ["# The rest of the signals, isolated, both directions", "",
          "_`signal_sweep` did sixteen. These are the ones it left: Kalshi as "
          "a venue in its own right, each crowd source on its own rather than "
          "blended, each part of the stat model rather than the blend, and the "
          "win-condition counts, which were built as reporting and have never "
          "once been scored against results._", "",
          "_Same bar. Both directions of every signal, because both pay the "
          "hold and sum to about minus twice the vig rather than to zero — a "
          "signal at −6% has no +6% fade behind it. Thirty-five signals is "
          "thirty-five lottery tickets, so the max/min-statistic correction is "
          "doing most of the work below._", "",
          f"- graded games: **{len(rows)}**", ""]
    if len(rows) < 300:
        return "\n".join(md + ["Not enough graded games.", ""])

    cells, sums = [], []
    for title, group in FAMILIES:
        md += [f"## {title}", "",
               "| signal | n | BACK it | FADE it | sum |", "|---|---|---|---|---|"]
        for sig in group:
            bkv, fdv = _view(rows, sig), _view(rows, sig, fade=True)
            if len(bkv) < MIN_CELL:
                md.append(f"| {sig} | {len(bkv)} | _too few_ | | |")
                continue
            s = (_roi(bkv) + _roi(fdv)) * 100
            sums.append(s)
            cells += [(f"back {sig}", bkv), (f"fade {sig}", fdv)]
            md.append(f"| {sig} | {len(bkv)} | {_fmt(bkv)} | {_fmt(fdv)} | {s:+.1f}% |")
        md.append("")

    if sums:
        md += [f"_Median `sum`: **{st.median(sums):+.1f}%** across "
               f"{len(sums)} signals. That is the hold, paid twice._", ""]

    pool = [(l, s) for l, s in cells if len(s) >= MIN_CELL]
    if not pool:
        return "\n".join(md)

    best_l, best_s = max(pool, key=lambda c: _roi(c[1]))
    worst_l, worst_s = min(pool, key=lambda c: _roi(c[1]))
    plan = [[(grade.american_profit(x["odds"]), x["p"]) for x in s] for _, s in pool]
    rng = random.Random(808)
    hi, lo = [], []
    for _ in range(TRIALS):
        vals = [sum(w if rng.random() < p else -1 for w, p in pl) / len(pl)
                for pl in plan]
        hi.append(max(vals) * 100)
        lo.append(min(vals) * 100)
    obs_hi, obs_lo = _roi(best_s) * 100, _roi(worst_s) * 100
    p_hi = (sum(1 for x in hi if x >= obs_hi) + 1) / (TRIALS + 1)
    p_lo = (sum(1 for x in lo if x <= obs_lo) + 1) / (TRIALS + 1)

    md += [f"## Corrected for {len(pool)} cells, in both tails", "",
           f"- best: **{best_l}** at {obs_hi:+.1f}% (n={len(best_s)}) · "
           f"redraws reach {st.median(hi):+.1f}% median, "
           f"{sorted(hi)[int(.95*TRIALS)]:+.1f}% at the 95th · "
           f"**corrected p = {p_hi:.3f}**",
           f"- worst: **{worst_l}** at {obs_lo:+.1f}% (n={len(worst_s)}) · "
           f"redraws reach {st.median(lo):+.1f}% median, "
           f"{sorted(lo)[int(.05*TRIALS)]:+.1f}% at the 5th · "
           f"**corrected p = {p_lo:.3f}**", ""]

    rh = random.Random(909)
    for lab, cell in ((best_l, best_s), (worst_l, worst_s)):
        tag = [rh.random() < 0.5 for _ in cell]
        a = [x for x, t in zip(cell, tag) if t]
        b = [x for x, t in zip(cell, tag) if not t]
        if min(len(a), len(b)) >= 30:
            md.append(f"- split-half of **{lab}**: {_fmt(a)} (n={len(a)}) "
                      f"against {_fmt(b)} (n={len(b)})")
    md.append("")

    md += ["## Reading it", "",
           "- a signal is only worth anything if its BACK column beats the "
           "vig AND it survives the correction AND both halves agree",
           "- the `sum` column is the fade test: only a signal summing well "
           "below the median is wrong by more than the vig",
           "- **raw against park-neutral** is a test of `park_factors.py`: if "
           "neutralising is worth anything the neutral row beats the raw one",
           "- **each crowd source alone** is the test the blend cannot do — a "
           "source that carries signal and one that cancels it look identical "
           "once averaged together", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "signal_sweep2.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
