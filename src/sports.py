"""
Sport registry - one place that knows what each sport is called on each venue,
and where its records live.

WHY A REGISTRY RATHER THAN A REFACTOR
The MLB pipeline works and carries a live record, so nothing here changes it.
This adds the seam a second sport needs: per-sport venue identifiers, per-sport
file paths, and a per-sport holdout date. MLB keeps its existing unprefixed
filenames so its history stays exactly where it is.

RECORDS ARE SEPARATE BY CONSTRUCTION
Each sport gets its own picks files and its own ledger. This is deliberate and
not a convenience: the consensus rule is validated on MLB alone, and weakly
(n=10 holdout). Running it on football is a NEW hypothesis, not an extension of
a proven one. A shared ledger would let a profitable sport mask a bleeding one
for months, so the split is enforced at the path level where it cannot be
forgotten.

`live` gates whether a sport reaches the board and Telegram. A new sport starts
`live=False` - it records picks and grades them, silently, until its own holdout
says otherwise.

VENUE IDENTIFIERS ARE UNVERIFIED except MLB's. Kalshi's MLB series is
KXMLBGAME, confirmed against the API; the others are the obvious pattern and
nothing more. src/sport_probe.py checks them against the live endpoints - run it
before trusting any of them, because an unverified selector here fails silently,
which is exactly how the Kalshi logger sat dead for weeks.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


@dataclass(frozen=True)
class Sport:
    key: str
    name: str
    kalshi_series: str        # UNVERIFIED except mlb - see sport_probe.py
    pm_tag: str               # gamma tag_slug
    holdout_from: str         # rules derived before this date; after it is clean
    live: bool                # False = shadow only, never reaches the board


SPORTS: dict[str, Sport] = {
    "mlb": Sport("mlb", "MLB", "KXMLBGAME", "mlb", "2026-07-23", live=True),
    # Not live. NFL is the first branch: it starts soonest, carries the deepest
    # prediction-market liquidity (which the order-book gate needs), and gives
    # days of pre-game market action rather than hours. Its holdout starts at
    # the 2026 season opener, so every NFL bet is out-of-sample from day one.
    "nfl": Sport("nfl", "NFL", "KXNFLGAME", "nfl", "2026-09-01", live=False),
    # NBA follows in late October. This is where the SAMPLE comes from: ~1230
    # games a season against the NFL's 272, so it accumulates evidence roughly
    # 4.5x faster.
    "nba": Sport("nba", "NBA", "KXNBAGAME", "nba", "2026-10-01", live=False),
    "nhl": Sport("nhl", "NHL", "KXNHLGAME", "nhl", "2026-10-01", live=False),
}

DEFAULT = "mlb"


def get(key: str | None) -> Sport:
    return SPORTS[(key or DEFAULT).lower()]


def live_sports() -> list[Sport]:
    return [s for s in SPORTS.values() if s.live]


# ---------------------------------------------------------------- paths
# MLB keeps its historic unprefixed names so its existing record is untouched.

def _stem(sport: str, base: str) -> str:
    return base if sport == DEFAULT else f"{base}_{sport}"


def picks_path(date: str, sport: str = DEFAULT) -> Path:
    return OUTPUT_DIR / f"{_stem(sport, 'picks')}_{date}.json"


def ledger_path(sport: str = DEFAULT) -> Path:
    return OUTPUT_DIR / f"{_stem(sport, 'ledger')}.json"


def pm_books_path(date: str, sport: str = DEFAULT) -> Path:
    return OUTPUT_DIR / f"{_stem(sport, 'pm_books')}_{date}.json"


def money_log_path(date: str, sport: str = DEFAULT) -> Path:
    return OUTPUT_DIR / f"{_stem(sport, 'money')}_{date}.json"
