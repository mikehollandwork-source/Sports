"""
Does MLB's own API know which way each ballpark faces?

WHY THIS EXISTS
park_factors.PARK_BEARING (home plate -> centre field, degrees) drives the
board's out/in wind read, and its values are my estimates. Verifying them
against public record is blocked here: andrewclem.com, baseball-almanac.com and
even wikipedia.org are all refused by this environment's egress policy.

But the wind read only needs ONE authoritative source, and MLB's own StatsAPI
serves venue metadata. Its `location` hydration is documented to carry an
`azimuthAngle` - which is exactly this bearing - alongside latitude and
longitude. If it is populated, the table stops being estimates and becomes
fetched data, and the guesses can be deleted rather than tuned.

This prints every field the API returns for every venue on the slate, so the
answer is visible whether or not the field is called what I expect.

Writes output/venue_probe.md.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from . import mlb_api

log = logging.getLogger("venue_probe")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def build() -> str:
    md = ["# Does the MLB API carry ballpark orientation?", "",
          "_`PARK_BEARING` drives the board's out/in wind read and its values are "
          "estimates. Verifying them against public record is blocked in this "
          "environment — andrewclem.com, baseball-almanac.com and wikipedia.org "
          "are all refused by the egress policy. MLB's own StatsAPI is reachable, "
          "and its venue `location` hydration is documented to carry "
          "`azimuthAngle`, which is this bearing._", ""]
    try:
        data = mlb_api._get("venues", sportId=1, hydrate="location,fieldInfo")
    except Exception as exc:
        return "\n".join(md + [f"**Venue fetch failed:** `{exc}`", ""])

    venues = data.get("venues") or []
    md += [f"- venues returned: **{len(venues)}**", ""]
    if not venues:
        return "\n".join(md + ["No venues returned.", ""])

    # what fields exist at all, and how often they are populated
    keys: dict[str, int] = {}
    for v in venues:
        loc = v.get("location") or {}
        for k, val in loc.items():
            if val not in (None, "", {}):
                keys[f"location.{k}"] = keys.get(f"location.{k}", 0) + 1
        for k, val in (v.get("fieldInfo") or {}).items():
            if val not in (None, "", {}):
                keys[f"fieldInfo.{k}"] = keys.get(f"fieldInfo.{k}", 0) + 1
    md += ["## Every populated field, and on how many venues", "",
           "| field | venues |", "|---|---|"]
    for k in sorted(keys, key=lambda k: -keys[k]):
        md.append(f"| `{k}` | {keys[k]} |")
    md.append("")

    az = [v for v in venues if (v.get("location") or {}).get("azimuthAngle") is not None]
    md += [f"- venues with **`azimuthAngle`**: **{len(az)}/{len(venues)}**", ""]
    if az:
        md += ["## The bearings, as MLB reports them", "",
               "| venue | azimuthAngle |", "|---|---|"]
        for v in sorted(az, key=lambda v: v.get("name") or ""):
            md.append(f"| {v.get('name')} | "
                      f"{(v.get('location') or {}).get('azimuthAngle')} |")
        md.append("")
        md += ["_If this table is complete, PARK_BEARING should be replaced by "
               "these values and the estimates deleted._", ""]
    else:
        md += ["**`azimuthAngle` is not populated.** The raw payload for one "
               "venue is below so any equivalent field can be spotted.", "",
               "```json", json.dumps(venues[0], indent=2)[:1500], "```", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "venue_probe.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
