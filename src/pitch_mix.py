"""
Pitch-type matchup, shown on the board and applied to nothing.

WHY IT IS CONTEXT AND NOT A FACTOR
The question was whether a hitter's power by pitch type, matched against a
starter's mix, should tighten the home-run selector. The data turned out to be
there - `playLog` carries pitch type, outcome and both hands on every plate
appearance - and the signal turned out to be real but tiny. Measured in
`pitchmix_stability.py`:

  - only the FASTBALL family carries anything; breaking p=0.22, offspeed p=0.72
  - fastball tilt replicates out of sample twice (2025->2026 r=+0.145 p=0.038;
    half-A->half-B r=+0.141 p=0.026; Fisher p=0.0078 against a six-test
    Bonferroni bar of 0.0083)
  - and its full achievable effect is x0.991 to x1.010

The selector already swings form x1.30, win probability x1.27 and wind x1.24, so
a 1.9% spread between the extremes of both distributions cannot move a pick. A
factor that provably does nothing does not belong in the formula.

So the matchup is reported instead: printed on the board, accumulating forward,
so in a season the spread can be re-measured against a real record rather than
re-argued. Same standing as the `good_dog` and `line_money` watch tags.

ENFORCED BY CONSTRUCTION, NOT BY ASSERTION
`main._attach_hr_prop` calls this AFTER the hitter has been chosen, with the
winner's id. It is not in the candidate loop and never sees a losing candidate,
so there is no code path by which it could reorder a selection - which is a
stronger guarantee than a comment promising it does not. `multiplier_not_applied`
is named the way it is for the same reason.

TILT_SLOPE and LEAGUE_FASTBALL_SHARE come from the stability measurement and are
PRE-REGISTERED: they describe how big the effect was found to be, and must not be
re-fitted against the forward record this is accumulating.
"""

from __future__ import annotations

import json
import logging
from datetime import date as _date
from pathlib import Path

from . import mlb_api

log = logging.getLogger("pitch_mix")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
CACHE = OUTPUT_DIR / "pitch_mix_cache.json"

FAMILIES = ("fastball", "breaking", "offspeed")
FAMILY = {
    "FF": "fastball", "SI": "fastball", "FC": "fastball", "FT": "fastball",
    "FA": "fastball",
    "SL": "breaking", "CU": "breaking", "KC": "breaking", "ST": "breaking",
    "SV": "breaking", "CS": "breaking", "SC": "breaking",
    "CH": "offspeed", "FS": "offspeed", "FO": "offspeed", "EP": "offspeed",
    "KN": "offspeed",
}

MIN_PA = 150            # PA-ending pitches before a tilt is worth printing
MIN_HR = 5              # homers, or the HR shares are one or two events
LEAGUE_FASTBALL_SHARE = 0.56   # measured over 353 starters, PA-ending shares
TILT_SLOPE = 0.0087            # observed tilt -> fastball HR rate above own overall
LEAGUE_HR_PA = 0.0303          # the figure hr_pick.HR_FLOOR is derived from
# The measured ceiling: the most this matchup could ever multiply a HR rate by,
# at the extremes of both distributions. record_audit uses it to bound the
# runner-up when checking that the context never would have changed a pick.
MAX_MULT = 1.010


def _load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return {}


def tallies(player_id: int, group: str, season: int,
            cache: dict | None = None) -> dict | None:
    """{family: [hr, pa]} from a player's plate appearances, cached for a day.

    One fetch per player per day: the board rebuilds several times and these
    logs are a couple of thousand rows. Returns None on any failure, which the
    caller prints as no context rather than a guess.
    """
    cache = _load_cache() if cache is None else cache
    key = f"{player_id}:{group}:{season}"
    today = _date.today().isoformat()
    hit = cache.get(key)
    if isinstance(hit, dict) and hit.get("date") == today:
        return hit["fam"]
    try:
        data = mlb_api._get(f"people/{player_id}/stats", stats="playLog",
                            group=group, season=season)
    except Exception as exc:
        log.warning("playLog unavailable for %s (%s)", key, exc)
        return None
    fam = {f: [0, 0] for f in FAMILIES}
    for b in data.get("stats") or []:
        for sp in b.get("splits") or []:
            det = (((sp.get("stat") or {}).get("play") or {}).get("details") or {})
            if not det.get("isPlateAppearance"):
                continue
            f = FAMILY.get((det.get("type") or {}).get("code") or "?")
            if not f:
                continue
            fam[f][1] += 1
            if det.get("eventType") == "home_run":
                fam[f][0] += 1
    cache[key] = {"date": today, "fam": fam}
    try:
        CACHE.write_text(json.dumps(cache))
    except OSError as exc:
        log.warning("pitch-mix cache not written (%s)", exc)
    return fam


def _totals(fam: dict) -> tuple[int, int]:
    return (sum(fam[f][0] for f in FAMILIES), sum(fam[f][1] for f in FAMILIES))


def fastball_tilt(fam: dict) -> tuple[float, int, int] | None:
    """(tilt, HR on fastballs, total HR), or None when the sample is too thin.

    tilt = share of his HR on fastballs minus share of his PA-ending pitches
    that were fastballs. Positive means his power concentrates on fastballs
    beyond how often he sees them.
    """
    hr, pa = _totals(fam)
    if pa < MIN_PA or hr < MIN_HR:
        return None
    return (fam["fastball"][0] / hr - fam["fastball"][1] / pa,
            fam["fastball"][0], hr)


def fastball_share(fam: dict) -> float | None:
    """A starter's share of plate appearances ended on a fastball."""
    _, pa = _totals(fam)
    return (fam["fastball"][1] / pa) if pa >= MIN_PA else None


def context(batter_id: int, starter_id: int | None, season: int) -> dict | None:
    """The matchup, for printing. None when either side is too thin to say.

    Called with the ALREADY-CHOSEN hitter, so it cannot affect the choice.
    """
    if not batter_id or not starter_id:
        return None
    cache = _load_cache()
    bfam = tallies(batter_id, "hitting", season, cache)
    pfam = tallies(starter_id, "pitching", season, cache)
    if not bfam or not pfam:
        return None
    t = fastball_tilt(bfam)
    share = fastball_share(pfam)
    if t is None or share is None:
        return None
    tilt, fhr, thr = t
    mult = 1 + ((share - LEAGUE_FASTBALL_SHARE) * TILT_SLOPE * tilt) / LEAGUE_HR_PA
    lean = ("suits him" if mult > 1.002 else
            "works against him" if mult < 0.998 else "neutral")
    return {
        "starter_fastball_share": round(share, 3),
        "hitter_fastball_tilt": round(tilt, 3),
        "hitter_fastball_hr": f"{fhr}/{thr}",
        "multiplier_not_applied": round(mult, 4),
        "note": (f"starter ends {share:.0%} of PA on fastballs "
                 f"(lg {LEAGUE_FASTBALL_SHARE:.0%}) · hitter {tilt:+.2f} "
                 f"fastball tilt ({fhr} of {thr} HR) → {lean}, "
                 f"×{mult:.3f} if it were applied"),
    }
