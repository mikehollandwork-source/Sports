# gameLog probe — Ozzie Albies (645277), 2026

_Does the hitting gameLog include postseason games?_

## no gameType (what props._game_log sends)

- games returned: **162**
- last 6: 2026-09-22 0-4 · 2026-09-23 1-3 · 2026-09-24 1-5 · 2026-09-25 0-3 · 2026-09-26 0-4 · 2026-09-27 0-2

## gameType=R (regular season)

- games returned: **162**
- last 6: 2026-09-22 0-4 · 2026-09-23 1-3 · 2026-09-24 1-5 · 2026-09-25 0-3 · 2026-09-26 0-4 · 2026-09-27 0-2

## gameType=P (postseason)

- games returned: **2**
- last 6: 2026-09-29 1-2 · 2026-09-30 1-4

## gameType=R,P (both)

- games returned: **164**
- last 6: 2026-09-24 1-5 · 2026-09-25 0-3 · 2026-09-26 0-4 · 2026-09-27 0-2 · 2026-09-29 1-2 · 2026-09-30 1-4

# TEAM gameLog endpoint

_Different endpoint. The advantage metric's last-5 wOBA/ISO/FIP comes through here, so gameType must be confirmed to work before anything depends on it._

## team: no gameType (what _team_gamelog sends)

- **hitting**: 162 game(s), last 4: 2026-09-24 · 2026-09-25 · 2026-09-26 · 2026-09-27
- **pitching**: 162 game(s), last 4: 2026-09-24 · 2026-09-25 · 2026-09-26 · 2026-09-27

## team: gameType=R

- **hitting**: 162 game(s), last 4: 2026-09-24 · 2026-09-25 · 2026-09-26 · 2026-09-27
- **pitching**: 162 game(s), last 4: 2026-09-24 · 2026-09-25 · 2026-09-26 · 2026-09-27

## team: gameType=P

- **hitting**: 2 game(s), last 4: 2026-09-29 · 2026-09-30
- **pitching**: 2 game(s), last 4: 2026-09-29 · 2026-09-30

## team: gameType=R,P

- **hitting**: 162 game(s), last 4: 2026-09-24 · 2026-09-25 · 2026-09-26 · 2026-09-27
- **pitching**: 162 game(s), last 4: 2026-09-24 · 2026-09-25 · 2026-09-26 · 2026-09-27
