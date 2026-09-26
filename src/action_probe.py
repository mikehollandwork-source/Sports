"""
Confirm the shape of Action Network's public scoreboard JSON.

WHY THIS ONE
The hunt found it carrying `ml_away_money` / `ml_home_money` / `num_bets`
across 30 MLB teams, on a 200 JSON response - moneyline HANDLE share, full
slate, no scraping. That is exactly what gate 1 has been missing.

A CORRECTION TO MY OWN SCORING
That hunt marked Action Network with **0** "split pairs" and flagged covers
matchups as the hit. Both were artefacts of the test, not the data:

  * the pair test looks for literal "%" characters, and JSON stores shares as
    bare numbers - so the best candidate scored zero on a criterion that
    cannot apply to it
  * covers matchups "passed" on 22 pairs that were all (50, 50), which is
    placeholder or layout noise rather than real splits, on only 5 teams

The keys are the signal for a JSON source. I wrote the criterion to avoid the
VSIN mistake of trusting percent counts, and it over-corrected into a
different one.

WHAT THIS CONFIRMS BEFORE ANY PARSER IS WRITTEN
  1. the money keys exist per game, not just somewhere in the blob
  2. away and home shares are present and sum to ~100
  3. games carry team names that map to ours
  4. how many of today's games are covered

Only then is a source worth wiring in, and only after a second run on another
day shows the path is stable. Two handle sources decayed this season; a third
earns its place by being sturdier, not by existing.

Reports only. Writes output/action_probe.md.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

log = logging.getLogger("action_probe")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
URL = "https://api.actionnetwork.com/web/v1/scoreboard/mlb"
# The bare scoreboard carries num_bets but no per-side money. Public betting
# usually rides on the odds sub-objects and often needs asking for: these are
# the variants worth trying before concluding the shares are not exposed.
import datetime as _dt
_TODAY = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
VARIANTS = [
    ("v1 scoreboard", URL),
    ("v1 + periods/props", URL + "?period=game&include=betting,polls"),
    ("v1 + date", f"{URL}?date={_TODAY}"),
    ("v2 public betting",
     "https://api.actionnetwork.com/web/v2/scoreboard/publicbetting/mlb"),
    ("v2 public betting + date",
     f"https://api.actionnetwork.com/web/v2/scoreboard/publicbetting/mlb?date={_TODAY}"),
]
BROWSER = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/129.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
}
MONEY_KEYS = ("ml_away_money", "ml_home_money", "money", "num_bets",
              "ml_away_bets", "ml_home_bets")


def _walk(node, path="", found=None, depth=0):
    """Every dict that carries a money-ish key, with where it sits."""
    found = found if found is not None else []
    if depth > 8:
        return found
    if isinstance(node, dict):
        if any(k in node for k in MONEY_KEYS):
            found.append((path or "<root>", node))
        for k, v in node.items():
            _walk(v, f"{path}.{k}" if path else k, found, depth + 1)
    elif isinstance(node, list):
        for i, v in enumerate(node[:3]):
            _walk(v, f"{path}[{i}]", found, depth + 1)
    return found


def build() -> str:
    md = ["# Action Network scoreboard JSON — does it carry real handle?", "",
          f"`{URL}`", "",
          "_Confirming shape before writing any parser. The hunt scored this "
          "source **0** on \"split pairs\" and flagged covers matchups "
          "instead — both artefacts of the test: the pair test needs literal "
          "`%` characters and JSON stores bare numbers, while covers passed "
          "on 22 pairs that were all (50, 50) across 5 teams._", ""]
    try:
        r = requests.get(URL, headers=BROWSER, timeout=25)
        status = r.status_code
        doc = r.json() if status == 200 else None
    except Exception as exc:
        return "\n".join(md + [f"**Fetch failed: {type(exc).__name__}: {exc}**", ""])
    if doc is None:
        return "\n".join(md + [f"**HTTP {status}**", ""])

    md += [f"- HTTP **{status}**",
           f"- top-level keys: `{', '.join(list(doc)[:12])}`" if isinstance(doc, dict)
           else f"- array of {len(doc)}"]
    games = doc.get("games") if isinstance(doc, dict) else None
    md += [f"- games in the payload: **{len(games) if games else 0}**", ""]

    hits = _walk(doc)
    md += [f"- objects carrying a money-ish key: **{len(hits)}**", ""]
    if not hits:
        return "\n".join(md + ["**No money keys found in the live payload.** "
                               "The hunt saw them in the raw text, so they may "
                               "sit under a query parameter this call omits.", ""])

    md += ["## Every object carrying a money-ish key", "",
           "_The first pass printed only the first of these, which hid "
           "whatever the other eleven were._", "",
           "| path | money keys and values |", "|---|---|"]
    for path, obj in hits[:14]:
        vals = {k: obj.get(k) for k in MONEY_KEYS if k in obj}
        md.append(f"| `{path}` | `{json.dumps(vals)[:110]}` |")
    md.append("")

    # do away+home actually sum to ~100 per game?
    pairs, named = [], 0
    for _, o in hits:
        a, h = o.get("ml_away_money"), o.get("ml_home_money")
        if isinstance(a, (int, float)) and isinstance(h, (int, float)):
            pairs.append((a, h))
    if games:
        for g in games:
            try:
                ts = g.get("teams") or []
                if len(ts) >= 2 and all(t.get("full_name") or t.get("display_name")
                                        for t in ts[:2]):
                    named += 1
            except Exception:
                continue
    md += ["## Does it behave like a split?", "",
           f"- away/home money pairs found: **{len(pairs)}**"]
    if pairs:
        sums = [a + h for a, h in pairs]
        ok = sum(1 for s in sums if 95 <= s <= 105)
        md += [f"- pairs summing to 95–105: **{ok}/{len(pairs)}**",
               f"- sample: {pairs[:4]}"]
    md += [f"- games with two named teams: **{named}**", ""]

    # If the bare call has no shares, ask the ways the site's own front end
    # does. A source that needs a parameter is still a source.
    md += ["## Other request shapes", "",
           "| variant | status | bytes | has ml_*_money | has 'value' bets |",
           "|---|---|---|---|---|"]
    for label, u in VARIANTS:
        try:
            rr = requests.get(u, headers=BROWSER, timeout=25)
            body = rr.text
            md.append(f"| {label} | {rr.status_code} | {len(body):,} | "
                      f"{'**yes**' if 'ml_away_money' in body else 'no'} | "
                      f"{'yes' if 'public_betting' in body or 'bet_info' in body else 'no'} |")
        except Exception as exc:
            md.append(f"| {label} | {type(exc).__name__} | — | — | — |")
    md += ["", "_A variant answering **yes** in the ml_*_money column is the "
           "call to build against._", "",
           ("_Money keys present, paired, summing to ~100 across a full slate "
            "is a usable handle source._" if pairs and named else
            "_Keys exist but do not resolve into per-game away/home pairs "
            "here; the parser would need the sub-object that does._"), "",
           "## Before this is wired in", "",
           "- a second run on a different day, to show the path is stable "
           "rather than a one-off",
           "- team-name mapping to ours, since a source we cannot match to a "
           "game is a source we cannot use",
           "- it joins as a THIRD handle source; changing `analysis`'s "
           "unanimity rule to a majority vote is a separate change that needs "
           "its own backtest", ""]
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "action_probe.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
