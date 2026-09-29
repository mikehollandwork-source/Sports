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

VENUE IDENTIFIERS ARE VERIFIED (sport_probe.py, 2026-08-06). All four Kalshi
series return two-sided events whose tickers parse into teams, with volume on
settled markets. Re-run the probe if anything downstream starts coming back
empty.

TWO PORTABILITY TRAPS the probe surfaced, both of which would have failed
silently:

  1. TICKER DATE FORMATS DIFFER BY SPORT.
        MLB  KXMLBGAME-26AUG092020HOUSD-SD   date + HHMM
        NFL  KXNFLGAME-26AUG15DALSEA-SEA     date only, no time
     Anything reusing dog_money.ticker_start() - which expects the HHMM - gets
     nothing for NFL. First pitch has to come from the schedule for sports whose
     tickers omit it.

  2. THE POLYMARKET TAG RETURNS FUTURES, NOT GAMES. `nfl` returns "Tush Push
     banned for 2026 Season?", `mlb` returns "World Series Champion 2026". The
     tag is a starting filter only; per-game events still have to be matched the
     way pm_books already does for MLB.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


@dataclass(frozen=True)
class Sport:
    key: str
    name: str
    kalshi_series: str        # all verified 2026-08-06 via sport_probe.py
    pm_tag: str               # gamma tag_slug
    odds_key: str             # The Odds API /v4/sports key
    holdout_from: str         # rules derived before this date; after it is clean
    live: bool                # False = shadow only, never reaches the board


SPORTS: dict[str, Sport] = {
    "mlb": Sport("mlb", "MLB", "KXMLBGAME", "mlb", "baseball_mlb",
                 "2026-07-23", live=True),
    # Not live. NFL is the first branch: deepest prediction-market liquidity
    # (which the order-book gate needs) and days of pre-game action rather than
    # hours. Kalshi already lists it - 32 two-sided preseason games as of
    # 2026-08-06 - but holdout starts at the regular-season opener ON PURPOSE.
    # Preseason outcomes are close to noise (starters barely play) and the money
    # behaves differently, so grading against it would teach us the wrong thing.
    "nfl": Sport("nfl", "NFL", "KXNFLGAME", "nfl", "americanfootball_nfl",
                 "2026-09-01", live=False),
    # NBA follows in late October. This is where the SAMPLE comes from: ~1230
    # games a season against the NFL's 272, so it accumulates evidence roughly
    # 4.5x faster.
    "nba": Sport("nba", "NBA", "KXNBAGAME", "nba", "basketball_nba",
                 "2026-10-01", live=False),
    "nhl": Sport("nhl", "NHL", "KXNHLGAME", "nhl", "icehockey_nhl",
                 "2026-10-01", live=False),
    # WNBA is the one branch that is IN SEASON right now, so it starts
    # accumulating out-of-sample evidence immediately instead of in October.
    # Holdout begins the day logging starts - there is no history to fit to, so
    # every WNBA game is clean by construction.
    "wnba": Sport("wnba", "WNBA", "KXWNBAGAME", "wnba", "basketball_wnba",
                  "2026-08-08", live=False),
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
