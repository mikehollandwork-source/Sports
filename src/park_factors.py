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
# APPROXIMATE, and the weakest data in this file - same status as the run
# factors above, which are also public estimates meant to be tuned. Orientation
# is a matter of public record and fixed for the life of a stadium, so these can
# be verified once and then left alone.
#
# Callers must require STRONG alignment before reporting anything (see
# main._wind_component): only wind within ~60 degrees of the axis counts, so a
# bearing wrong by 20-30 degrees changes the strength of the read but not its
# sign. That tolerance is why an approximate table is usable at all.
PARK_BEARING: dict[str, int] = {
    "Arizona Diamondbacks": 0,     "Atlanta Braves": 65,
    "Baltimore Orioles": 32,       "Boston Red Sox": 45,
    "Chicago Cubs": 34,            "Chicago White Sox": 50,
    "Cincinnati Reds": 60,         "Cleveland Guardians": 0,
    "Colorado Rockies": 5,         "Detroit Tigers": 30,
    "Houston Astros": 345,         "Kansas City Royals": 45,
    "Los Angeles Angels": 45,      "Los Angeles Dodgers": 25,
    "Miami Marlins": 40,           "Milwaukee Brewers": 0,
    "Minnesota Twins": 30,         "New York Mets": 25,
    "New York Yankees": 75,        "Athletics": 60,
    "Oakland Athletics": 60,       # the API has used both names this season
    "Philadelphia Phillies": 15,   "Pittsburgh Pirates": 120,
    "San Diego Padres": 0,         "San Francisco Giants": 85,
    "Seattle Mariners": 0,         "St. Louis Cardinals": 60,
    "Tampa Bay Rays": 45,          "Texas Rangers": 20,
    "Toronto Blue Jays": 0,        "Washington Nationals": 30,
}


def bearing_for(team_name: str) -> int | None:
    """Home-to-centre bearing for a park, or None when unknown (no wind read)."""
    return PARK_BEARING.get(team_name)
