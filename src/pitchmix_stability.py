"""
Is a hitter's home-run tilt BY PITCH FAMILY stable year to year?

WHY THIS RUNS BEFORE ANYTHING IS BUILT
The plan was to match a hitter's power by pitch type against a starter's pitch
mix. The data exists - MLB's playLog carries pitch type, outcome and pitcher
hand for every plate appearance - so the idea is buildable. Whether it is WORTH
building is a different question, and one probe already raised the alarm:

  Gavin Sheets, HR per PA-ending pitch
    family     2026            2025
    fastball   5.38% (12/223)  2.53% (7/277)
    breaking   2.89% (3/104)   4.40% (8/182)
    offspeed   2.17% (2/92)    4.71% (4/85)

2026 says he only hits fastballs out. 2025 says fastballs were his WORST family.
The ordering reverses. Seventeen homers split three ways is four to twelve per
cell, which is the sample size where a pattern appears whether or not one is
there. Fitting that into the home-run selector would be fitting noise, which is
the one mistake this project keeps getting caught by.

A pitcher's MIX is not in doubt - usage is one of the most stable things in
baseball. The crux is the hitter side, so that is what gets measured.

THE MEASURE
Per hitter per season, one scalar per family:

  tilt = (share of his HR that came on this family)
       - (share of his PA-ending pitches that were this family)

Positive means his homers concentrate on that family beyond how often he sees
it. It is bounded, needs no zero-division, and is exactly the quantity a mix
matchup would exploit.

Three tests, in rising order of what they would let us do:

 1. YEAR-OVER-YEAR r, 2025 tilt against 2026 tilt. If a hitter's tilt carries
    forward, this is positive.
 2. SPLIT-HALF r within 2026 (alternating games). This is the reliability
    CEILING: if a season cannot even agree with itself, no year-over-year
    correlation is possible and the measure is noise by construction.
 3. QUARTILE table - group hitters by 2025 fastball tilt, then look at their
    2026 fastball HR rate minus their own 2026 overall rate. This is the
    bettable form of the claim, and the only one that answers "would this have
    helped?"

Permutation p-values throughout (shuffle one season's tilts against the other),
because n is a few hundred and these correlations are small.

Read-only. Writes output/pitchmix_stability.md. Nothing in the live pipeline
imports this, and no threshold anywhere is tuned from it - it decides a yes/no
about whether the pitch-mix term gets built at all.
"""

from __future__ import annotations

import json
import logging
import math
import random
from pathlib import Path

from . import mlb_api

log = logging.getLogger("pitchmix_stability")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
CACHE = OUTPUT_DIR / "pitchmix_cache.json"
REPORT = OUTPUT_DIR / "pitchmix_stability.md"

SEASON = 2026
PRIOR = 2025
MIN_PA = 150        # PA-ending pitches needed in a season for a usable tilt
MIN_HR = 5          # homers needed, or the HR shares are one or two events
LEAGUE_HR_PA = 0.0303   # league HR per PA, the same figure hr_pick.HR_FLOOR uses
FAMILIES = ("fastball", "breaking", "offspeed")
PERMUTATIONS = 2000
SEED = 20261004

FAMILY = {
    "FF": "fastball", "SI": "fastball", "FC": "fastball", "FT": "fastball",
    "FA": "fastball",
    "SL": "breaking", "CU": "breaking", "KC": "breaking", "ST": "breaking",
    "SV": "breaking", "CS": "breaking", "SC": "breaking",
    "CH": "offspeed", "FS": "offspeed", "FO": "offspeed", "EP": "offspeed",
    "KN": "offspeed",
}


# --- fetching -----------------------------------------------------------------
def _load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return {}


def _tallies(player_id: int, group: str, season: int, cache: dict) -> dict | None:
    """{family: [hr, pa], "_halves": {...}} for one player-season, cached.

    Only the tallies are cached, never the raw records - the report needs a few
    hundred players and the logs are a couple of thousand rows each.
    """
    key = f"{player_id}:{group}:{season}"
    if key in cache:
        return cache[key]
    try:
        data = mlb_api._get(f"people/{player_id}/stats", stats="playLog",
                            group=group, season=season)
    except Exception as exc:
        log.warning("playLog failed for %s (%s)", key, exc)
        return None
    out: dict = {f: [0, 0] for f in FAMILIES}
    out["other"] = [0, 0]
    # Alternating GAMES, not alternating plate appearances: two PAs in the same
    # game share the pitcher, the park and the weather, so splitting within a
    # game would share those and overstate the agreement between halves.
    halves: dict = {"A": {f: [0, 0] for f in FAMILIES},
                    "B": {f: [0, 0] for f in FAMILIES}}
    seen: list[str] = []
    for b in data.get("stats") or []:
        for sp in b.get("splits") or []:
            play = ((sp.get("stat") or {}).get("play") or {})
            det = play.get("details") or {}
            if not det.get("isPlateAppearance"):
                continue
            fam = FAMILY.get((det.get("type") or {}).get("code") or "?", "other")
            is_hr = det.get("eventType") == "home_run"
            cell = out[fam]
            cell[1] += 1
            if is_hr:
                cell[0] += 1
            date = sp.get("date") or ""
            if date and date not in seen:
                seen.append(date)
            if fam in FAMILIES and date:
                side = "A" if (seen.index(date) % 2 == 0) else "B"
                hc = halves[side][fam]
                hc[1] += 1
                if is_hr:
                    hc[0] += 1
    out["_halves"] = halves
    cache[key] = out
    return out


def _roster_ids() -> tuple[list[int], list[int]]:
    """(hitter ids, pitcher ids) across all 30 active rosters."""
    hitters, pitchers = [], []
    try:
        teams = mlb_api._get("teams", sportId=1, season=SEASON).get("teams", [])
    except Exception as exc:
        log.warning("team list failed (%s)", exc)
        return [], []
    for t in teams:
        try:
            r = mlb_api._get(f"teams/{t['id']}/roster", rosterType="active")
        except Exception as exc:
            log.warning("roster failed for %s (%s)", t.get("name"), exc)
            continue
        for e in r.get("roster", []):
            pid = (e.get("person") or {}).get("id")
            if not pid:
                continue
            if (e.get("position") or {}).get("type") == "Pitcher":
                pitchers.append(pid)
            else:
                hitters.append(pid)
    return hitters, pitchers


# --- the measure --------------------------------------------------------------
def tilt(tal: dict, family: str) -> float | None:
    """HR share minus PA share for one family, or None when too thin."""
    pa = sum(tal[f][1] for f in FAMILIES)
    hr = sum(tal[f][0] for f in FAMILIES)
    if pa < MIN_PA or hr < MIN_HR:
        return None
    return tal[family][0] / hr - tal[family][1] / pa


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def _perm_p(xs: list[float], ys: list[float], r: float) -> float:
    """Two-sided: how often a shuffled pairing reaches |r| this large."""
    rng = random.Random(SEED)
    shuffled = list(ys)
    hits = 0
    for _ in range(PERMUTATIONS):
        rng.shuffle(shuffled)
        rp = _pearson(xs, shuffled)
        if rp is not None and abs(rp) >= abs(r):
            hits += 1
    return (hits + 1) / (PERMUTATIONS + 1)


# --- report -------------------------------------------------------------------
def _pairs(ids: list[int], group: str, cache: dict,
           family: str) -> tuple[list[float], list[float]]:
    """(prior-season tilts, this-season tilts) for players usable in both."""
    xs, ys = [], []
    for pid in ids:
        a = _tallies(pid, group, PRIOR, cache)
        b = _tallies(pid, group, SEASON, cache)
        if not a or not b:
            continue
        ta, tb = tilt(a, family), tilt(b, family)
        if ta is None or tb is None:
            continue
        xs.append(ta)
        ys.append(tb)
    return xs, ys


def _halfpairs(ids: list[int], group: str, cache: dict,
               family: str) -> tuple[list[float], list[float]]:
    """The reliability ceiling: tilt in alternating games of SEASON, A against B.

    Each half is held to half of MIN_PA/MIN_HR, since each half holds half the
    season - applying the full bar would empty the sample.
    """
    xs, ys = [], []
    for pid in ids:
        t = _tallies(pid, group, SEASON, cache)
        if not t:
            continue
        halves = t.get("_halves") or {}
        vals = []
        for side in ("A", "B"):
            h = halves.get(side)
            if not h:
                vals = []
                break
            pa = sum(h[f][1] for f in FAMILIES)
            hr = sum(h[f][0] for f in FAMILIES)
            if pa < MIN_PA / 2 or hr < MIN_HR / 2:
                vals = []
                break
            vals.append(h[family][0] / hr - h[family][1] / pa)
        if len(vals) == 2:
            xs.append(vals[0])
            ys.append(vals[1])
    return xs, ys


def _corr_rows(ids: list[int], group: str, cache: dict,
               fn, label: str) -> list[str]:
    rows = ["| family | n | r | permutation p |", "|---|---|---|---|"]
    for fam in FAMILIES:
        xs, ys = fn(ids, group, cache, fam)
        r = _pearson(xs, ys)
        if r is None:
            rows.append(f"| {fam} | {len(xs)} | — | — |")
            continue
        p = _perm_p(xs, ys, r)
        mark = " **" if p < 0.05 else ""
        rows.append(f"| {fam} | {len(xs)} | {r:+.3f}{mark} | {p:.3f} |")
    return [f"**{label}**", ""] + rows + [""]


def _quartiles(ids: list[int], group: str, cache: dict) -> list[str]:
    """Group by PRIOR fastball tilt; report SEASON fastball HR rate minus own
    overall rate. The bettable form: would last year's tilt have helped?"""
    rows = []
    for pid in ids:
        a = _tallies(pid, group, PRIOR, cache)
        b = _tallies(pid, group, SEASON, cache)
        if not a or not b:
            continue
        ta = tilt(a, "fastball")
        if ta is None:
            continue
        pa = sum(b[f][1] for f in FAMILIES)
        hr = sum(b[f][0] for f in FAMILIES)
        fpa, fhr = b["fastball"][1], b["fastball"][0]
        if pa < MIN_PA or hr < MIN_HR or fpa < 40:
            continue
        rows.append((ta, fhr / fpa - hr / pa, fhr, fpa))
    if len(rows) < 8:
        return ["_Too few players with both seasons to quartile._", ""]
    rows.sort(key=lambda r: r[0])
    k = len(rows) // 4
    out = ["| 2025 fastball tilt | n | 2026 fastball HR% − own overall |",
           "|---|---|---|"]
    for i, name in enumerate(("lowest", "2nd", "3rd", "highest")):
        chunk = rows[i * k:(i + 1) * k] if i < 3 else rows[3 * k:]
        if not chunk:
            continue
        lo, hi = chunk[0][0], chunk[-1][0]
        hr = sum(c[2] for c in chunk)
        pa = sum(c[3] for c in chunk)
        delta = sum(c[1] for c in chunk) / len(chunk)
        out.append(f"| {name} ({lo:+.3f} to {hi:+.3f}) | {len(chunk)} "
                   f"| {delta:+.3%}  ({hr} HR / {pa} PA) |")
    return out + [""]


def _slope(ids: list[int], cache: dict, family: str) -> tuple[float, float, int]:
    """(slope, observed-tilt SD, n) for half-A tilt -> half-B rate-minus-overall.

    Regressing the OBSERVED tilt straight onto the later outcome is the point:
    it already absorbs the predictor's own noise, so the slope needs no further
    shrinkage. Shrinking it again by the reliability would double-count the
    noise and understate the effect about fivefold.
    """
    xs, ys = [], []
    for pid in ids:
        t = _tallies(pid, "hitting", SEASON, cache)
        if not t:
            continue
        h = t.get("_halves") or {}
        a, b = h.get("A"), h.get("B")
        if not a or not b:
            continue
        ahr = sum(a[f][0] for f in FAMILIES); apa = sum(a[f][1] for f in FAMILIES)
        bhr = sum(b[f][0] for f in FAMILIES); bpa = sum(b[f][1] for f in FAMILIES)
        if min(apa, bpa) < MIN_PA / 2 or min(ahr, bhr) < MIN_HR / 2:
            continue
        if b[family][1] < 20:
            continue
        xs.append(a[family][0] / ahr - a[family][1] / apa)
        ys.append(b[family][0] / b[family][1] - bhr / bpa)
    r = _pearson(xs, ys)
    if r is None or len(xs) < 10:
        return 0.0, 0.0, len(xs)
    sx = _stdev(xs)
    sy = _stdev(ys)
    return (r * sy / sx if sx else 0.0), sx, len(xs)


def _stdev(v: list[float]) -> float:
    n = len(v)
    if n < 2:
        return 0.0
    m = sum(v) / n
    return math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))


def _pct(sorted_v: list[float], p: float) -> float:
    return sorted_v[int(p * (len(sorted_v) - 1))] if sorted_v else 0.0


def effect_size(hitters: list[int], pitchers: list[int],
                cache: dict) -> list[str]:
    """How big is the matchup term at its most extreme, in the units the
    selector already uses?

    A p-value says the signal exists; this says whether it is worth wiring. The
    selector multiplies a per-PA home-run rate by form, wind, park, temperature
    and win probability, so a new factor has to be read on that same scale.

    A starter's fastball share shifts the fraction of a hitter's plate
    appearances that come on fastballs by (w - mean w). On those his rate differs
    from his overall by (slope x tilt). So the shift in his expected rate is
    (w - mean w) x slope x tilt, and the multiplier is 1 + that / league rate.
    """
    slope, _, n = _slope(hitters, cache, "fastball")
    tilts = sorted(
        t for t in (tilt(_tallies(p, "hitting", SEASON, cache) or {}, "fastball")
                    for p in hitters) if t is not None)
    shares = []
    for pid in pitchers:
        t = _tallies(pid, "pitching", SEASON, cache)
        if not t:
            continue
        pa = sum(t[f][1] for f in FAMILIES)
        if pa >= MIN_PA:
            shares.append(t["fastball"][1] / pa)
    shares.sort()
    if not tilts or not shares or not slope:
        return ["_Not enough data to size the effect._", ""]
    wbar = sum(shares) / len(shares)
    out = [f"slope {slope:+.4f} per unit tilt (n={n}) · hitter fastball tilt "
           f"p10 {_pct(tilts, .10):+.3f} / p90 {_pct(tilts, .90):+.3f} · "
           f"starter fastball share p10 {_pct(shares, .10):.0%} / "
           f"mean {wbar:.0%} / p90 {_pct(shares, .90):.0%}", "",
           "| hitter | starter | multiplier on HR rate |", "|---|---|---|"]
    mults = []
    for hl, tl in (("p90 fastball tilt", _pct(tilts, .90)),
                   ("p10 fastball tilt", _pct(tilts, .10))):
        for wl, w in (("p90 fastball share", _pct(shares, .90)),
                      ("p10 fastball share", _pct(shares, .10))):
            mult = 1 + ((w - wbar) * slope * tl) / LEAGUE_HR_PA
            mults.append(mult)
            out.append(f"| {hl} | {wl} | ×{mult:.4f} |")
    out += ["",
            f"**Full achievable range ×{min(mults):.3f} to ×{max(mults):.3f}** "
            f"— a {max(mults)/min(mults)-1:.1%} spread, and only between the "
            f"extremes of both distributions.", "",
            "For scale, the factors the selector already applies: form up to "
            "×1.30, win probability ×1.27, wind ×1.24, park ×1.12, temperature "
            "×1.08, opposing pitching ×1.05.", ""]
    return out


def build() -> str:
    cache = _load_cache()
    hitters, pitchers = _roster_ids()
    log.info("rosters: %d hitters, %d pitchers", len(hitters), len(pitchers))
    md = [f"# Is home-run tilt by pitch family stable? — {PRIOR} vs {SEASON}",
          "",
          "_Measured before the pitch-mix term is built, because one probe "
          "already showed a hitter whose family ordering reversed between "
          "seasons._", "",
          f"tilt = (share of HR on the family) − (share of PA-ending pitches "
          f"on it). Needs {MIN_PA}+ PA and {MIN_HR}+ HR in a season. "
          f"p from {PERMUTATIONS} permutations.", ""]

    md += ["## Hitters", ""]
    md += _corr_rows(hitters, "hitting", cache, _halfpairs,
                     f"Split-half within {SEASON} (alternating games) — the "
                     f"reliability CEILING")
    md += _corr_rows(hitters, "hitting", cache, _pairs,
                     f"{PRIOR} tilt vs {SEASON} tilt — does it carry forward?")
    md += [f"### Would {PRIOR}'s fastball tilt have helped in {SEASON}?", ""]
    md += _quartiles(hitters, "hitting", cache)

    md += ["## Pitchers (HR allowed)", ""]
    md += _corr_rows(pitchers, "pitching", cache, _halfpairs,
                     f"Split-half within {SEASON} (alternating games)")
    md += _corr_rows(pitchers, "pitching", cache, _pairs,
                     f"{PRIOR} vs {SEASON}")

    md += ["## How big is it, though?", "",
           "_A p-value says the signal exists. This says whether it is worth "
           "wiring, on the same scale as the factors already in the selector._",
           ""]
    md += effect_size(hitters, pitchers, cache)

    md += ["## How to read this", "",
           "- split-half r near zero means the season cannot agree with "
           "itself, so nothing carries forward by construction and the term "
           "must not be built",
           "- a split-half r that is clearly positive while the "
           "year-over-year r is not means the tilt is real within a season but "
           "does not persist - usable only from the CURRENT season, never from "
           "last year's",
           "- the quartile table is the one that matters: if the highest "
           "group does not out-homer the lowest on fastballs, last year's tilt "
           "is not information",
           "- a pitcher's MIX is stable regardless; it is his HR-by-family "
           "that is being questioned here",
           ""]
    try:
        CACHE.write_text(json.dumps(cache))
    except OSError as exc:
        log.warning("cache not written (%s)", exc)
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    OUTPUT_DIR.mkdir(exist_ok=True)
    text = build()
    REPORT.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
