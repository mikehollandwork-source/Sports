"""
Game-time ballpark weather, from Open-Meteo (free, no key, datacenter-friendly).

Display-only context for now (same discipline as every new signal: it doesn't
touch the decision until a calibration earns it a vote). The static park factor
is ALREADY inside the offense index (park_factors.py); this adds the day's
conditions: temperature, wind speed/direction, and rain chance at first pitch.
Roofed parks report their roof instead of wind.

forecast_for(venue, iso_start) -> {temp_f, wind_mph, wind_dir, precip_pct, roof}
or None (fail soft - board just omits the line).
"""

from __future__ import annotations

import datetime as dt
import logging

import requests

log = logging.getLogger("weather")

API = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
       "&hourly=temperature_2m,precipitation_probability,wind_speed_10m,wind_direction_10m"
       "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=UTC"
       "&start_date={day}&end_date={day}")
TIMEOUT = 15

# venue name -> (lat, lon, roof) - roof: open / retract / dome
STADIUMS = {
    "Chase Field": (33.4453, -112.0667, "retract"),
    "Truist Park": (33.8908, -84.4678, "open"),
    "Oriole Park at Camden Yards": (39.2839, -76.6217, "open"),
    "Fenway Park": (42.3467, -71.0972, "open"),
    "Wrigley Field": (41.9484, -87.6553, "open"),
    "Rate Field": (41.8299, -87.6338, "open"),
    "Guaranteed Rate Field": (41.8299, -87.6338, "open"),
    "Great American Ball Park": (39.0975, -84.5066, "open"),
    "Progressive Field": (41.4962, -81.6852, "open"),
    "Coors Field": (39.7559, -104.9942, "open"),
    "Comerica Park": (42.3390, -83.0485, "open"),
    "Daikin Park": (29.7573, -95.3555, "retract"),
    "Minute Maid Park": (29.7573, -95.3555, "retract"),
    "Kauffman Stadium": (39.0517, -94.4803, "open"),
    "Angel Stadium": (33.8003, -117.8827, "open"),
    "Dodger Stadium": (34.0739, -118.2400, "open"),
    "loanDepot park": (25.7781, -80.2197, "retract"),
    "American Family Field": (43.0280, -87.9712, "retract"),
    "Target Field": (44.9817, -93.2776, "open"),
    "Citi Field": (40.7571, -73.8458, "open"),
    "Yankee Stadium": (40.8296, -73.9262, "open"),
    "Sutter Health Park": (38.5802, -121.5133, "open"),
    "Citizens Bank Park": (39.9061, -75.1665, "open"),
    "PNC Park": (40.4469, -80.0057, "open"),
    "Petco Park": (32.7076, -117.1570, "open"),
    "T-Mobile Park": (47.5914, -122.3325, "retract"),
    "Oracle Park": (37.7786, -122.3893, "open"),
    "Busch Stadium": (38.6226, -90.1928, "open"),
    "George M. Steinbrenner Field": (27.9803, -82.5067, "open"),
    "Tropicana Field": (27.7683, -82.6534, "dome"),
    "Globe Life Field": (32.7473, -97.0842, "retract"),
    "Rogers Centre": (43.6414, -79.3894, "retract"),
    "Nationals Park": (38.8730, -77.0074, "open"),
}

_COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

_CACHE: dict = {}


def _compass(deg: float) -> str:
    return _COMPASS[int((deg / 22.5) + 0.5) % 16]


def forecast_for(venue: str, iso_start: str | None) -> dict | None:
    """Conditions at the game's start hour. None when the venue is unknown, the
    start time is missing, or the fetch fails (board omits the line)."""
    spot = STADIUMS.get(venue or "")
    if not spot or not iso_start:
        return None
    lat, lon, roof = spot
    try:
        start = dt.datetime.fromisoformat(iso_start.replace("Z", "+00:00"))
    except ValueError:
        return None
    key = (venue, start.strftime("%Y-%m-%dT%H"))
    if key in _CACHE:
        return _CACHE[key]
    try:
        r = requests.get(API.format(lat=lat, lon=lon, day=start.strftime("%Y-%m-%d")),
                         timeout=TIMEOUT)
        r.raise_for_status()
        h = r.json()["hourly"]
        idx = min(range(len(h["time"])),
                  key=lambda i: abs(dt.datetime.fromisoformat(h["time"][i] + ":00+00:00") - start))
        out = {
            "temp_f": round(h["temperature_2m"][idx]),
            "wind_mph": round(h["wind_speed_10m"][idx]),
            "wind_dir": _compass(h["wind_direction_10m"][idx]),
            "precip_pct": int(h["precipitation_probability"][idx] or 0),
            "roof": roof,
        }
    except Exception as exc:
        log.warning("weather failed for %s: %s", venue, exc)
        out = None
    _CACHE[key] = out
    return out
