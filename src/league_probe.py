"""
Discover a league's teams and identifiers from the venues themselves.

WHY DISCOVERY RATHER THAN VERIFICATION
nfl_probe checks a hand-written team table against Kalshi. That works when the
table is already right. For a league whose franchise list may have changed - the
WNBA has expanded recently - writing the table first means writing a guess and
then checking my own guess, which is how a wrong entry survives: it looks
verified because the check was built to agree with it.

So this asks the venues what the teams ARE. It reports the abbreviations Kalshi
uses, the full team names The Odds API returns, and the outcome labels
Polymarket carries, then pairs them by nickname so the mapping table can be
written from data instead of memory.

Also reports, per league: whether tickers carry a time (MLB does, NFL does not),
whether gamma events expose a kickoff, and how many games each venue lists - the
three things that decided whether the NFL branch worked.

Usage: python -m src.league_probe wnba
Writes output/league_probe_<sport>.md.
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path

import requests

from . import kalshi, nfl_api, pm_books
from .sports import get as get_sport

log = logging.getLogger("league_probe")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _kalshi(series: str) -> dict:
    out: dict = {"abbrs": set(), "samples": [], "open": 0, "settled": 0}
    for status in ("open", "settled"):
        data = kalshi._get("/markets", series_ticker=series,
                           status=status, limit=200) or {}
        mkts = data.get("markets") or []
        out[status] = len(mkts)
        for m in mkts:
            tk = m.get("ticker") or ""
            tail = tk.rsplit("-", 1)[-1].upper()
            if tail:
                out["abbrs"].add(tail)
            if status == "open" and len(out["samples"]) < 4:
                out["samples"].append(tk)
    return out


def _odds_teams(odds_key: str) -> tuple[set, list]:
    """Full team names from The Odds API events, plus sample events."""
    names, samples = set(), []
    evs = nfl_api._get("/events", odds_key) or []
    for ev in evs:
        a, h = ev.get("away_team"), ev.get("home_team")
        if a and h:
            names.update({a, h})
            if len(samples) < 4:
                samples.append(f"{a} @ {h}  ({str(ev.get('commence_time'))[:16]})")
    return names, samples


def _pm_outcomes(tag: str) -> tuple[Counter, list, int]:
    """Outcome labels on two-sided gamma markets, sample game titles, kickoffs."""
    labels: Counter = Counter()
    titles, kicks = [], 0
    for off in (0, 100, 200):
        batch = pm_books._get(pm_books.GAMMA, tag_slug=tag, closed="false",
                              limit=100, offset=off)
        if not isinstance(batch, list) or not batch:
            break
        for ev in batch:
            is_game = False
            for m in ev.get("markets") or []:
                outs = m.get("outcomes")
                if isinstance(outs, str):
                    try:
                        outs = json.loads(outs)
                    except ValueError:
                        continue
                if not outs or len(outs) != 2:
                    continue
                a, b = str(outs[0]).strip(), str(outs[1]).strip()
                # a game has two DIFFERENT short labels; futures are prose
                if a != b and len(a) <= 30 and len(b) <= 30:
                    labels.update([a, b])
                    is_game = True
            if is_game:
                if ev.get("startTime"):
                    kicks += 1
                if len(titles) < 4:
                    titles.append(str(ev.get("title"))[:60])
        if len(batch) < 100:
            break
    return labels, titles, kicks


def build(key: str) -> str:
    sp = get_sport(key)
    md = [f"# League probe — {sp.name}", "",
          "_Asks the venues what the teams are, rather than checking a table "
          "written from memory. A hand-written guess that gets 'verified' by a "
          "check built to agree with it is not verified._", "",
          f"- Kalshi series `{sp.kalshi_series}` · Polymarket tag `{sp.pm_tag}` "
          f"· Odds API `{sp.odds_key}`", ""]

    k = _kalshi(sp.kalshi_series)
    md += ["## Kalshi", "",
           f"- open markets: **{k['open']}** · settled: **{k['settled']}**",
           f"- distinct abbreviations: **{len(k['abbrs'])}**", ""]
    if k["samples"]:
        md += ["_sample tickers:_", ""] + [f"- `{s}`" for s in k["samples"]] + [""]
    if k["abbrs"]:
        md += [f"- abbreviations: {', '.join('`%s`' % a for a in sorted(k['abbrs']))}",
               "",
               "_Ticker time format: " +
               ("carries HHMM (start time available from the ticker)"
                if any(len(s.split('-')[1]) > 7 for s in k["samples"] if '-' in s)
                else "**date only — start time must come from a schedule**") + "._", ""]

    names, ev_samples = _odds_teams(sp.odds_key)
    md += ["## The Odds API", "",
           f"- distinct team names in listed events: **{len(names)}**", ""]
    if ev_samples:
        md += ["_sample events:_", ""] + [f"- {s}" for s in ev_samples] + [""]
    if names:
        md += [f"- names: {', '.join(sorted(names))}", ""]
    else:
        md += ["_No events listed — either out of season or the sport key is "
               "wrong. A wrong key returns an empty list, not an error._", ""]

    labels, titles, kicks = _pm_outcomes(sp.pm_tag)
    md += ["## Polymarket", "",
           f"- distinct outcome labels on two-sided markets: **{len(labels)}**",
           f"- game events exposing `startTime`: **{kicks}**", ""]
    if titles:
        md += ["_sample game titles:_", ""] + [f"- {t}" for t in titles] + [""]
    if labels:
        md += [f"- labels: {', '.join('`%s`' % l for l, _ in labels.most_common(40))}",
               ""]

    # ---- pair them up so the table can be written from data ----
    md += ["## Proposed mapping (abbr → name), built from the above", "",
           "_Matched by nickname: the last word of the Odds API name against the "
           "Kalshi abbreviation and the Polymarket label. Anything unmatched is "
           "listed separately and needs a human eye._", ""]
    by_nick = {n.rsplit(" ", 1)[-1].upper(): n for n in names}
    rows, unmatched_k = [], []
    for ab in sorted(k["abbrs"]):
        hit = next((n for nick, n in by_nick.items() if nick.startswith(ab)
                    or ab.startswith(nick[:3])), None)
        if hit:
            rows.append((ab, hit))
        else:
            unmatched_k.append(ab)
    if rows:
        md += ["| abbr | name |", "|---|---|"] + \
              [f"| `{a}` | {n} |" for a, n in rows] + [""]
    md += [f"- Kalshi abbreviations with no name match: "
           f"**{unmatched_k or 'none'}**",
           f"- Odds API names with no abbreviation: "
           f"**{sorted(set(names) - {n for _a, n in rows}) or 'none'}**", ""]
    md.append("_Nickname matching is a starting point, not the answer — write "
              "the final table by hand from these lists, then let the probe "
              "confirm it._")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    key = sys.argv[1] if len(sys.argv) > 1 else "wnba"
    md = build(key)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / f"league_probe_{key}.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
