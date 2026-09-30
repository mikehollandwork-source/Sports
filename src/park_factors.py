"""
Static ballpark run factors (multiplicative; 1.00 = league-average run env).

Used to *neutralize* a team's last-5 offense for the parks they actually played
in, so a team that piled up runs at Coors isn't credited with a true-talent
offensive edge. Values are approximate, well-known public estimates and are
meant to be tuned. Keyed by the MLB API's full team name (the park's home team).
"""

PARK_FACTORS: dict[str, float] = {
    "Colorado Rockies": 1.20,
    "Cincinnati Reds": 1.08,
    "Boston Red Sox": 1.06,
    "Arizona Diamondbacks": 1.05,
    "Kansas City Royals": 1.03,
    "Texas Rangers": 1.03,
    "New York Yankees": 1.02,
    "Baltimore Orioles": 1.02,
    "Philadelphia Phillies": 1.02,
    "Chicago Cubs": 1.02,
    "Toronto Blue Jays": 1.02,
    "Chicago White Sox": 1.01,
    "Atlanta Braves": 1.01,
    "Washington Nationals": 1.01,
    "Minnesota Twins": 1.00,
    "Houston Astros": 1.00,
    "Los Angeles Angels": 1.00,
    "Milwaukee Brewers": 1.00,
    "St. Louis Cardinals": 0.99,
    "Pittsburgh Pirates": 0.99,
    "Cleveland Guardians": 0.99,
    "Los Angeles Dodgers": 0.98,
    "Tampa Bay Rays": 0.98,
    "New York Mets": 0.97,
    "Oakland Athletics": 0.97,
    "Athletics": 0.97,
    "Detroit Tigers": 0.97,
    "San Diego Padres": 0.96,
    "San Francisco Giants": 0.96,
    "Miami Marlins": 0.95,
    "Seattle Mariners": 0.95,
}

DEFAULT_FACTOR = 1.00


def factor_for(team_name: str) -> float:
    """Park run factor for a team's home stadium (1.00 if unknown)."""
    return PARK_FACTORS.get(team_name, DEFAULT_FACTOR)


# Home plate -> centre field bearing, degrees clockwise from true north. Used to
# turn a wind direction into "blowing out" or "blowing in", which a compass
# string alone cannot say: a south wind helps hitters in a park facing north and
# suppresses them in one facing south.
#
# SOURCE: MLB StatsAPI, /api/v1/venues?hydrate=location -> location.azimuthAngle.
# These are MLB's own published values, not estimates. src/venue_probe.py
# re-fetches them; run it if a team moves or a park is rebuilt.
#
# They replaced a table of my estimates on 2026-09-30, which was wrong by more
# than 30 degrees at 9 of 30 parks and by more than 90 - enough to REVERSE the
# read - at Milwaukee (129 against my 0), Detroit (150 against 30) and Minnesota
# (129 against 30). The error was systematic: I assumed most parks follow the
# rulebook's east-northeast recommendation, and several modern parks face
# southeast instead.
#
# Callers still require STRONG alignment (see main._wind_component): only wind
# within ~60 degrees of the axis counts. That tolerance was written to survive
# an approximate table and is kept, since it also rejects crosswinds that say
# nothing.
PARK_BEARING: dict[str, float] = {
    "Arizona Diamondbacks": 0.0,     "Atlanta Braves": 145.0,
    "Baltimore Orioles": 31.0,       "Boston Red Sox": 45.0,
    "Chicago Cubs": 37.0,            "Chicago White Sox": 127.0,
    "Cincinnati Reds": 122.0,        "Cleveland Guardians": 0.0,
    "Colorado Rockies": 4.0,         "Detroit Tigers": 150.0,
    "Houston Astros": 343.0,         "Kansas City Royals": 46.0,
    "Los Angeles Angels": 43.61,     "Los Angeles Dodgers": 26.0,
    "Miami Marlins": 128.0,          "Milwaukee Brewers": 129.0,
    "Minnesota Twins": 129.0,        "New York Mets": 13.0,
    "New York Yankees": 75.0,        "Philadelphia Phillies": 9.0,
    "Pittsburgh Pirates": 116.0,     "San Diego Padres": 0.0,
    "San Francisco Giants": 85.0,    "Seattle Mariners": 49.0,
    "St. Louis Cardinals": 62.0,     "Tampa Bay Rays": 359.0,
    "Texas Rangers": 30.0,           "Toronto Blue Jays": 345.0,
    "Washington Nationals": 28.0,
    # the Athletics play at Sutter Health Park, Sacramento; the API has used
    # both team names this season, so both keys are here
    "Athletics": 46.0,               "Oakland Athletics": 46.0,
}


def bearing_for(team_name: str) -> float | None:
    """Home-to-centre bearing for a park, or None when unknown (no wind read)."""
    return PARK_BEARING.get(team_name)
