"""
Game-time ballpark weather, from Open-Meteo with a MET Norway fallback (both
free, no key, datacenter-friendly). If Open-Meteo times out or errors, we fall
back to api.met.no so a slow primary never leaves the board without conditions.

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
# MET Norway (api.met.no) - free, no key; requires an identifying User-Agent or
# it 403s. Returns SI units (C, m/s), converted below.
MET_API = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}"
MET_UA = "mlb-edge-finder/1.0 github.com/mikehollandwork-source/Sports"
TIMEOUT = 8   # per source; short so a dead primary fails over to the backup fast

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


def _open_meteo(lat: float, lon: float, start: dt.datetime) -> dict:
    """Open-Meteo conditions at the start hour (already in F / mph). Raises on
    any failure so the caller can fall back."""
    r = requests.get(API.format(lat=lat, lon=lon, day=start.strftime("%Y-%m-%d")),
                     timeout=TIMEOUT)
    r.raise_for_status()
    h = r.json()["hourly"]
    idx = min(range(len(h["time"])),
              key=lambda i: abs(dt.datetime.fromisoformat(h["time"][i] + ":00+00:00") - start))
    return {
        "temp_f": round(h["temperature_2m"][idx]),
        "wind_mph": round(h["wind_speed_10m"][idx]),
        "wind_dir": _compass(h["wind_direction_10m"][idx]),
        "precip_pct": int(h["precipitation_probability"][idx] or 0),
    }


def _met_norway(lat: float, lon: float, start: dt.datetime) -> dict:
    """MET Norway conditions at the nearest timeseries entry, converted from SI
    (C -> F, m/s -> mph). Raises on any failure."""
    # they ask for <=4 decimals (better edge caching) and an identifying UA
    r = requests.get(MET_API.format(lat=round(lat, 4), lon=round(lon, 4)),
                     headers={"User-Agent": MET_UA}, timeout=TIMEOUT)
    r.raise_for_status()
    series = r.json()["properties"]["timeseries"]
    e = min(series, key=lambda s: abs(
        dt.datetime.fromisoformat(s["time"].replace("Z", "+00:00")) - start))
    inst = e["data"]["instant"]["details"]
    precip = 0.0
    for span in ("next_1_hours", "next_6_hours"):
        d = e["data"].get(span, {}).get("details", {})
        if "probability_of_precipitation" in d:
            precip = d["probability_of_precipitation"]
            break
    return {
        "temp_f": round(inst["air_temperature"] * 9 / 5 + 32),
        "wind_mph": round(inst["wind_speed"] * 2.23694),
        "wind_dir": _compass(inst.get("wind_from_direction", 0)),
        "precip_pct": int(precip or 0),
    }


def forecast_for(venue: str, iso_start: str | None) -> dict | None:
    """Conditions at the game's start hour. None when the venue is unknown, the
    start time is missing, or BOTH sources fail (board omits the line)."""
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

    out = None
    for name, fetch in (("open-meteo", _open_meteo), ("met.no", _met_norway)):
        try:
            out = {**fetch(lat, lon, start), "roof": roof}
            if name != "open-meteo":
                log.info("weather for %s via fallback %s", venue, name)
            break
        except Exception as exc:
            log.warning("weather %s failed for %s: %s", name, venue, exc)
    _CACHE[key] = out
    return out
