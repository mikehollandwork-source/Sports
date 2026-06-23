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
