"""
Verify the NFL plumbing end to end, on a runner with real network access.

The dev sandbox firewalls outbound APIs, so none of this can be checked locally - and
every piece here fails soft, which means a broken NFL path would look exactly
like an empty schedule. It has to be exercised where the network is open.

FOUR CHECKS, in dependency order:

  1. team table - do the name forms Kalshi and Polymarket actually use resolve
     to abbreviations?
  2. schedule - are there games, and do they carry kickoff times? This is
     the whole reason the module exists: Kalshi's NFL ticker has no HHMM.
  3. ABBREVIATION AGREEMENT between Kalshi and our table. The check that matters
     most. MLB needed an alias table (WAS/WSH, CHW/CWS, SDP/SD...) and the NFL
     has the same hazards - Washington, both LA teams, Jacksonville. A mismatch
     silently drops that team's games forever, which is how the Kalshi logger
     sat dead for weeks.
  4. Polymarket game markets under the `nfl` tag, using nfl_api.name_abbr -
     confirming season futures fall out and per-game markets survive.

Writes output/nfl_probe.md.
"""

from __future__ import annotations

import datetime as dt
import logging
import zoneinfo
from pathlib import Path

from . import kalshi, nfl_api, pm_books
from .sports import get as get_sport

log = logging.getLogger("nfl_probe")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
EASTERN = zoneinfo.ZoneInfo("America/New_York")
LOOKAHEAD_DAYS = 21


def _kalshi_nfl_abbrs() -> tuple[set, list]:
    """Team abbreviations Kalshi uses in open NFL tickers, plus sample tickers."""
    sp = get_sport("nfl")
    data = kalshi._get("/markets", series_ticker=sp.kalshi_series,
                       status="open", limit=200) or {}
    mkts = data.get("markets") or []
    abbrs, samples = set(), []
    for m in mkts:
        tk = m.get("ticker") or ""
        tail = tk.rsplit("-", 1)[-1].upper()
        if tail:
            abbrs.add(tail)
        if len(samples) < 5:
            samples.append(tk)
    return abbrs, samples


def build() -> str:
    md = ["# NFL plumbing probe", "",
          "_Everything here fails soft, so a broken NFL path looks identical to "
          "an empty schedule. This exercises it where the network is open._", ""]

    # ---- 1. team map ----
    tm = nfl_api.team_map()
    md += ["## 1. Team table", "",
           f"- name forms loaded: **{len(tm)}**",
           f"- distinct teams: **{len(set(tm.values()))}** (expect 32)", ""]
    if tm:
        md += ["| probe string | resolves to |", "|---|---|"]
        for s in ("Seattle Seahawks", "Seahawks", "Dallas Cowboys",
                  "Kansas City Chiefs", "Washington Commanders",
                  "Los Angeles Rams", "Los Angeles Chargers",
                  "Jacksonville Jaguars",
                  "Tush Push banned for 2026 NFL Season?"):
            md.append(f"| `{s}` | `{nfl_api.name_abbr(s)}` |")
        md.append("")
    else:
        md += ["**Team table did not load — everything below is blocked.**", ""]

    # ---- 2. schedule with kickoff times ----
    keys = nfl_api.sport_keys()
    md += ["## 1b. Odds API football sport keys", "",
           f"- exposed: {', '.join('`%s`' % k for k in keys) or '**none**'}",
           f"- we query: {', '.join('`%s`' % k for k in nfl_api.SPORT_KEYS)}", ""]
    missing = [k for k in nfl_api.SPORT_KEYS if keys and k not in keys]
    if missing:
        md += [f"**We query keys the API does not expose: {missing}** — that "
               "returns an empty schedule rather than an error.", ""]

    today = dt.datetime.now(EASTERN).date()
    found = []
    for d in range(LOOKAHEAD_DAYS):
        date = (today + dt.timedelta(days=d)).isoformat()
        games = nfl_api.schedule(date)
        if games:
            found.append((date, games))
        if len(found) >= 3:
            break
    md += ["## 2. Schedule and kickoff times", "",
           f"- dates with games in the next {LOOKAHEAD_DAYS}: **{len(found)}**", ""]
    for date, games in found:
        md.append(f"**{date}** — {len(games)} game(s)")
        md += ["", "| matchup | abbrs | kickoff (UTC) | start_ts |", "|---|---|---|---|"]
        for g in games[:6]:
            md.append(f"| {g['matchup']} | `{g['away_abbr']}` @ `{g['home_abbr']}` | "
                      f"{g['game_datetime']} | `{g['start_ts']}` |")
        md.append("")
    if found and not any(g["start_ts"] for _d, gs in found for g in gs):
        md += ["**No kickoff times parsed — the reason this module exists is "
               "unmet.**", ""]

    # ---- 3. abbreviation agreement (the one that silently kills teams) ----
    k_abbrs, samples = _kalshi_nfl_abbrs()
    espn_abbrs = set(tm.values())
    md += ["## 3. Kalshi vs our table's abbreviations", "",
           f"- Kalshi abbreviations in open tickers: **{len(k_abbrs)}**",
           f"- our table's abbreviations: **{len(espn_abbrs)}**"]
    if samples:
        md.append(f"- sample tickers: {', '.join('`%s`' % s for s in samples)}")
    only_k = sorted(k_abbrs - espn_abbrs)
    only_e = sorted(espn_abbrs - k_abbrs)
    md += ["", f"- **in Kalshi but not our table: {only_k or 'none'}**",
           f"- in our table but not Kalshi: {only_e or 'none'}", ""]
    if only_k:
        md += ["**These need alias entries.** Any team here has games that will "
               "never match, silently — the MLB equivalent of WAS/WSH and "
               "CHW/CWS. Teams appearing only in our column are "
               "expected (not every team plays in a given window).", ""]
    else:
        md += ["_No Kalshi-side mismatches: every abbreviation Kalshi uses is in "
               "our table, so no alias entries are needed._", ""]

    # ---- 4. Polymarket game markets ----
    try:
        idx = pm_books.open_market_index(tag="nfl", name_fn=nfl_api.name_abbr)
    except Exception as exc:
        idx = {}
        md += [f"_Polymarket index failed: {exc}_", ""]
    md += ["## 4. Polymarket NFL game markets", "",
           f"- matched game keys (both directions): **{len(idx)}** "
           f"→ ~**{len(idx)//2}** games", ""]
    if idx:
        md += ["| pair |", "|---|"]
        for pair in list(idx)[:6]:
            md.append(f"| `{pair[0]}` vs `{pair[1]}` |")
        md.append("")
    else:
        md += ["_No per-game markets matched. Either Polymarket has not listed "
               "NFL games yet, or the outcome labels do not resolve through "
               "`nfl_api.name_abbr` — check the sample titles in "
               "`sport_probe.md` before assuming the former._", ""]

    md.append("_NFL stays `live=False` regardless of these results. This probe "
              "verifies the plumbing carries data, not that the rule works._")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "nfl_probe.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
