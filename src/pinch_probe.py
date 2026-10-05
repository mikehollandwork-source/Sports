"""What does the feed actually carry to tell a pulled starter from a sub?"""
import json
from src import mlb_api

out = ["# Pinch-hit detection probe", ""]

# 1. every field a hitting gameLog split carries
try:
    d = mlb_api._get("people/669221/stats", stats="gameLog", group="hitting",
                     season=2026, gameType="R,P")
    sp = [s for b in d.get("stats", []) for s in b.get("splits", [])]
    out += [f"## hitting gameLog — {len(sp)} splits", ""]
    if sp:
        out += ["stat keys:", "```",
                ", ".join(sorted((sp[0].get('stat') or {}).keys())), "```",
                "split-level keys:", "```",
                ", ".join(sorted(sp[0].keys())), "```"]
except Exception as exc:
    out.append(f"gameLog failed: {exc}")

# 2. the boxscore for the ATL @ LAD game, where two bats were lifted
try:
    sched = mlb_api._get("schedule", sportId=1, date="10/04/2026")
    pk = None
    for dd in sched.get("dates", []):
        for g in dd.get("games", []):
            names = {g["teams"]["away"]["team"]["name"], g["teams"]["home"]["team"]["name"]}
            if "Atlanta Braves" in names:
                pk = g["gamePk"]
    out += ["", f"## boxscore, gamePk {pk}", ""]
    if pk:
        bs = mlb_api._get(f"game/{pk}/boxscore")
        for side in ("away", "home"):
            team = (bs.get("teams") or {}).get(side) or {}
            if "Braves" not in ((team.get("team") or {}).get("name") or ""):
                continue
            players = team.get("players") or {}
            out += ["player entry keys:", "```",
                    ", ".join(sorted(next(iter(players.values())).keys())), "```", ""]
            out += ["| player | battingOrder | isSubstitute | PA |",
                    "|---|---|---|---|"]
            rows = []
            for p in players.values():
                bo = p.get("battingOrder")
                if not bo:
                    continue
                st = ((p.get("stats") or {}).get("batting") or {})
                rows.append((bo, (p.get("person") or {}).get("fullName"),
                             (p.get("gameStatus") or {}).get("isSubstitute"),
                             st.get("plateAppearances")))
            for bo, nm, sub, pa in sorted(rows):
                out.append(f"| {nm} | {bo} | {sub} | {pa} |")
except Exception as exc:
    out.append(f"boxscore failed: {exc}")

print("\n".join(out))
open("output/pinch_probe.md", "w").write("\n".join(out))
