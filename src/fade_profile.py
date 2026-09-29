"""
Which fades win and which lose - and whether that is knowable at all.

THE SITUATION
The fade is live at the user's call. Pooled it returned +12.8% over 196 games
with a CI spanning zero; slicing by withdrawal reason gave p = 0.984 and by
reason x price p = 0.901. Neither found a pocket. The request is to keep
digging, so this digs in the two directions that have not been tried.

NEW FEATURES, chosen because they have a mechanism rather than because they are
available:

    versions      how many committed board versions the pick survived before
                  being dropped. A pick that flickered for one refresh was
                  probably marginal all along; one that stood all afternoon and
                  then died is a genuine change of mind by the market.
    lead_hours    how long before first pitch the withdrawal happened. Late
                  withdrawals follow late money, which is the informed kind.
    readded       whether it came back as a pick afterwards. A pick that
                  oscillates is a pick sitting exactly on a threshold, and a
                  threshold coin-flip is not a signal in either direction.

THE TEST THAT DECIDES IT
Not "which category looks best" - every scan answers that, and this dataset has
answered it wrong sixteen times. Instead, SPLIT-HALF: rank the categories by
first-half fade ROI, then back only those in the second half. If the winners
stay winners the profile is real and dialling in is possible. If not, no amount
of further slicing will help, and that is a definitive answer rather than
another inconclusive table.

Writes output/fade_profile.md.
"""

from __future__ import annotations

import glob
import json
import logging
import random
import statistics as st
import subprocess
from collections import defaultdict
from pathlib import Path

from . import grade, mlb_api

log = logging.getLogger("fade_profile")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
REPO = Path(__file__).resolve().parent.parent
MIN_CELL = 20


def _versions(rel: str) -> list[str]:
    try:
        out = subprocess.run(["git", "log", "--format=%H", "--all", "--reverse",
                              "--", rel], cwd=REPO, capture_output=True,
                             text=True, timeout=120)
        return [s for s in out.stdout.split() if s]
    except Exception:
        return []


def _at(sha: str, rel: str):
    try:
        out = subprocess.run(["git", "show", f"{sha}:{rel}"], cwd=REPO,
                             capture_output=True, text=True, timeout=60)
        return json.loads(out.stdout) if out.returncode == 0 else None
    except Exception:
        return None


def collect() -> list[dict]:
    import datetime as dt
    rows = []
    for f in sorted(glob.glob(str(OUTPUT_DIR / "picks_2026-*.json"))):
        date = Path(f).stem.split("picks_")[1]
        rel = f"output/picks_{date}.json"
        shas = _versions(rel)
        if len(shas) < 2:
            continue
        try:
            results = mlb_api.results_for(date)
        except Exception:
            continue
        # walk every version, tracking each game's pick state over time
        hist: dict = defaultdict(list)
        meta: dict = {}
        for sha in shas:
            day = _at(sha, rel)
            if not day:
                continue
            stamp = day.get("generated_at")
            for g in day.get("games", []):
                pk = g.get("game_pk")
                pc = g.get("pick_criteria") or {}
                is_pick = pc.get("play") == "pick"
                hist[pk].append((stamp, is_pick, pc.get("bet_team"),
                                 pc.get("bet_moneyline")))
                if pk not in meta:
                    meta[pk] = {"matchup": g.get("matchup"),
                                "start": g.get("game_datetime"),
                                "adv": pc.get("advantage_team"),
                                "a_ml": pc.get("advantage_moneyline"),
                                "o_ml": pc.get("opponent_moneyline")}
                if is_pick:
                    meta[pk].update({"adv": pc.get("advantage_team"),
                                     "a_ml": pc.get("advantage_moneyline"),
                                     "o_ml": pc.get("opponent_moneyline")})
        for pk, seq in hist.items():
            picked = [i for i, x in enumerate(seq) if x[1]]
            if not picked:
                continue
            last_pick = picked[-1]
            if last_pick == len(seq) - 1:
                continue                     # survived; not a fade
            m = meta[pk]
            res = results.get(pk)
            if not res or not res.get("final") or not res.get("winner"):
                continue
            bet = seq[last_pick][2]
            if not bet or " @ " not in (m["matchup"] or ""):
                continue
            away, home = m["matchup"].split(" @ ")
            other = home if bet == away else away
            odds = m["o_ml"] if bet == m["adv"] else m["a_ml"]
            if not isinstance(odds, int):
                continue
            # when the withdrawal was seen, vs first pitch
            lead = None
            drop_stamp = seq[last_pick + 1][0]
            if drop_stamp and m.get("start"):
                try:
                    a = dt.datetime.fromisoformat(drop_stamp.replace("Z", "+00:00"))
                    b = dt.datetime.fromisoformat(m["start"].replace("Z", "+00:00"))
                    lead = (b - a).total_seconds() / 3600.0
                except ValueError:
                    pass
            rows.append({
                "date": date, "pk": pk, "matchup": m["matchup"],
                "fade_team": other, "odds": odds,
                "won": res["winner"] == other,
                "versions": len(picked),
                "lead_hours": lead,
                "readded": any(i > last_pick for i in picked),
            })
    return rows


def _roi(rs) -> float:
    if not rs:
        return 0.0
    return sum(grade.american_profit(r["odds"]) if r["won"] else -1
               for r in rs) / len(rs)


def _fmt(rs) -> str:
    if not rs:
        return "—"
    w = sum(1 for r in rs if r["won"])
    tag = "" if len(rs) >= MIN_CELL else "_"
    return f"{tag}{w}-{len(rs)-w} · {_roi(rs):+.1%} (n={len(rs)}){tag}"


def build() -> str:
    rows = collect()
    md = ["# Fade profile — which withdrawals are worth fading?", "",
          "_The fade is live. Pooled it returned +12.8% with a CI spanning zero, "
          "and slicing by reason (p=0.984) and reason x price (p=0.901) found "
          "no pocket. These are the two directions not yet tried._", "",
          f"- withdrawn picks reconstructed with an outcome: **{len(rows)}**",
          f"- pooled fade: **{_fmt(rows)}**", ""]
    if len(rows) < 60:
        return "\n".join(md + ["Too few to profile.", ""])

    cats: dict = {}
    md += ["## By how long the pick survived before being dropped", "",
           "_A pick that flickered for one refresh was marginal all along; one "
           "that stood all afternoon and then died is the market changing its "
           "mind._", "", "| board versions as a pick | fading it |", "|---|---|"]
    for lbl, t in (("1 (flicker)", lambda r: r["versions"] == 1),
                   ("2-3", lambda r: 2 <= r["versions"] <= 3),
                   ("4+ (sustained)", lambda r: r["versions"] >= 4)):
        sub = [r for r in rows if t(r)]
        if len(sub) >= MIN_CELL:
            cats[f"versions {lbl}"] = sub
        md.append(f"| {lbl} | {_fmt(sub)} |")
    md.append("")

    md += ["## By how late the withdrawal came", "",
           "_Late withdrawals follow late money, which is the informed kind._",
           "", "| hours before first pitch | fading it |", "|---|---|"]
    have = [r for r in rows if r["lead_hours"] is not None]
    for lbl, t in (("> 6h out", lambda r: r["lead_hours"] > 6),
                   ("2-6h out", lambda r: 2 <= r["lead_hours"] <= 6),
                   ("< 2h out (late)", lambda r: r["lead_hours"] < 2)):
        sub = [r for r in have if t(r)]
        if len(sub) >= MIN_CELL:
            cats[f"lead {lbl}"] = sub
        md.append(f"| {lbl} | {_fmt(sub)} |")
    md.append("")

    md += ["## Did it come back?", "",
           "_A pick that oscillates is sitting exactly on a threshold, and a "
           "threshold coin-flip is not a signal in either direction._", "",
           "| | fading it |", "|---|---|",
           f"| withdrawn and stayed out | {_fmt([r for r in rows if not r['readded']])} |",
           f"| withdrawn then re-added | {_fmt([r for r in rows if r['readded']])} |", ""]
    for lbl, t in (("stayed out", lambda r: not r["readded"]),
                   ("re-added", lambda r: r["readded"])):
        sub = [r for r in rows if t(r)]
        if len(sub) >= MIN_CELL:
            cats[f"readded {lbl}"] = sub

    # ---- the decisive test ----
    md += ["## Can this be dialled in? The split-half test", "",
           "_Rank the categories by first-half fade ROI, then back only the top "
           "ones in the second half. If the winners stay winners, dialling in is "
           "possible. If not, no further slicing will help._", ""]
    if len(cats) < 3:
        md += ["Too few categories reach n=20 to test.", ""]
        return "\n".join(md)
    dates = sorted({r["date"] for r in rows})
    mid = dates[len(dates) // 2]
    pairs = []
    for k, v in cats.items():
        a = [r for r in v if r["date"] < mid]
        b = [r for r in v if r["date"] >= mid]
        if len(a) >= 8 and len(b) >= 8:
            pairs.append((k, _roi(a), _roi(b), len(a), len(b)))
    if len(pairs) < 3:
        md += ["Too few categories have games in both halves.", ""]
        return "\n".join(md)
    md += ["| category | first half | second half |", "|---|---|---|"]
    for k, ra, rb, na, nb in sorted(pairs, key=lambda x: -x[1]):
        md.append(f"| {k} | {ra:+.1%} (n={na}) | {rb:+.1%} (n={nb}) |")
    xs = [p[1] for p in pairs]
    ys = [p[2] for p in pairs]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    dx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    dy = (sum((y - my) ** 2 for y in ys)) ** 0.5
    r = (sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (dx * dy)) if dx and dy else float("nan")
    top = sorted(pairs, key=lambda x: -x[1])[:max(1, len(pairs) // 2)]
    names = {p[0] for p in top}
    picked = [x for k in names for x in cats[k] if x["date"] >= mid]
    md += ["", f"- correlation between halves across {n} categories: "
           f"**r = {r:+.2f}**",
           f"- backing the top half of categories in the second half: "
           f"**{_fmt(picked)}**",
           f"- the whole pooled fade in the second half: "
           f"**{_fmt([x for x in rows if x['date'] >= mid])}**", ""]
    md += (["**Dialling in works.** The categories that led in the first half "
            "led again in the second.", ""] if r > 0.4 else
           ["**Dialling in does not work.** A category's first-half record says "
            "little or nothing about its second, so picking the good ones is "
            "picking noise. The pooled fade, which selects nothing, remains the "
            "right version to run.", ""])
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "fade_profile.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
