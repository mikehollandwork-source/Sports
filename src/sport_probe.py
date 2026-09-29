"""
Verify each sport's venue identifiers before we depend on them.

WHY
Every selector in this repo that shipped unverified has failed silently. Kalshi
was queried with status="active", which 400s on every call, and the fail-soft
wrapper swallowed it - the logger looked healthy and recorded nothing for weeks.
The registry in sports.py currently contains three guessed Kalshi series names
and three guessed Polymarket tags. Guessing is fine; shipping a guess is not.

WHAT IT CHECKS, per sport
  * does the Kalshi series return OPEN markets, and do the tickers parse into
    two teams per event the way the MLB code assumes?
  * does it return SETTLED markets with volume, which is what any backtest needs?
  * does the Polymarket gamma tag return events?

Prints counts and sample tickers and asserts nothing. Off-season sports will
correctly show zero open markets - that is not a failure, so settled markets are
checked too, since those persist year-round.

Writes output/sport_probe.md.
"""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

from . import kalshi, pm_books
from .sports import SPORTS

log = logging.getLogger("sport_probe")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def _kalshi_check(series: str) -> dict:
    """Counts and a sample for one Kalshi series, both open and settled."""
    out: dict = {"series": series}
    for status in ("open", "settled"):
        try:
            data = kalshi._get("/markets", series_ticker=series,
                               status=status, limit=200)
        except Exception as exc:
            out[status] = f"error: {exc}"
            continue
        mkts = (data or {}).get("markets") or []
        out[status] = len(mkts)
        if not mkts:
            continue
        if status == "open":
            out["sample_ticker"] = mkts[0].get("ticker")
        # do tickers parse into a team, and do events pair up two-a-side?
        per_event: Counter = Counter()
        parsed = 0
        for m in mkts:
            if kalshi._abbr(m.get("ticker")):
                parsed += 1
            if m.get("event_ticker"):
                per_event[m["event_ticker"]] += 1
        out[f"{status}_parsed_team"] = f"{parsed}/{len(mkts)}"
        pairs = sum(1 for c in per_event.values() if c == 2)
        out[f"{status}_two_sided_events"] = f"{pairs}/{len(per_event)}"
        if status == "settled":
            with_vol = sum(1 for m in mkts
                           if kalshi.market_money(m).get("volume"))
            out["settled_with_volume"] = f"{with_vol}/{len(mkts)}"
    return out


def _pm_check(tag: str) -> dict:
    try:
        batch = pm_books._get(pm_books.GAMMA, tag_slug=tag, closed="false",
                              limit=20, offset=0)
    except Exception as exc:
        return {"tag": tag, "open": f"error: {exc}"}
    n = len(batch) if isinstance(batch, list) else 0
    out = {"tag": tag, "open_events": n}
    if n:
        out["sample"] = (batch[0].get("title") or batch[0].get("slug") or "")[:70]
    return out


def build() -> str:
    md = ["# Sport registry probe", "",
          "_Verifying the Kalshi series and Polymarket tags in `sports.py` "
          "against the live endpoints. Only MLB's were previously confirmed; the "
          "rest are pattern guesses. An off-season sport showing zero OPEN "
          "markets is expected - settled markets persist, so those are the real "
          "test of whether a series name is right._", ""]

    for key, sp in SPORTS.items():
        k = _kalshi_check(sp.kalshi_series)
        p = _pm_check(sp.pm_tag)
        ok = isinstance(k.get("settled"), int) and k["settled"] > 0
        md += [f"## {sp.name} (`{key}`){'  ✅' if ok else '  ⚠️'}", "",
               f"- Kalshi series `{sp.kalshi_series}`: "
               f"open **{k.get('open')}**, settled **{k.get('settled')}**"]
        for field in ("sample_ticker", "open_parsed_team", "open_two_sided_events",
                      "settled_parsed_team", "settled_two_sided_events",
                      "settled_with_volume"):
            if k.get(field) is not None:
                md.append(f"  - {field}: `{k[field]}`")
        md += [f"- Polymarket tag `{sp.pm_tag}`: open events "
               f"**{p.get('open_events')}**"]
        if p.get("sample"):
            md.append(f"  - sample: _{p['sample']}_")
        if not ok:
            md.append("  - **series name looks wrong or the sport has no history "
                      "on Kalshi** — do not build on this until it resolves")
        md.append("")

    md.append("_A sport is only safe to build on once its settled-market count "
              "is non-zero AND tickers parse into two-sided events, because that "
              "is what every downstream module assumes._")
    return "\n".join(md)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    md = build()
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "sport_probe.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
