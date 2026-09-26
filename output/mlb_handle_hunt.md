# Hunting a free MLB handle (money %) source

_Retry with a browser User-Agent and real status codes. The first attempt sent the project's bot UA and reported every failure as "blocked", which confused how we ask with what is there._

**A hit is not "the page loaded".** CSS is full of percentages - that is what made me misread VSIN. A hit is a PAIR of percentages summing to 95-105, or JSON keys naming a bets/money share.

| candidate | status | type | bytes | teams | split pairs | split-ish keys |
|---|---|---|---|---|---|---|
| covers matchups | 200 | text/html | 975,270 | 5 | **22** | bsbetslipapibaseurl |
| covers consensus | 200 | text/html | 331,078 | 22 | **0** | — |
| action network scoreboard | 200 | application/json | 590,411 | 30 | **0** | ml_away_money, ml_home_money, num_bets, spread_away_money |
| action network v2 public | 200 | application/json | 470,315 | 30 | **0** | bet_info, money, moneyline, num_bets |
| oddsshark consensus | 200 | text/html | 331,078 | 22 | **0** | — |
| bettingpros splits | **403** | application/json | — | — | — | — |
| oddstrader public betting | **404** | text/html | — | — | — | — |
| wagertalk splits | **404** | text/html | — | — | — | — |
| sbr consensus | 200 | text/html | 877,355 | 26 | **0** | awaymoneylinepickpercent, bettingarticle, homemoneylinepickpercent, moneylinehistory |

## Candidates carrying a real split

### covers matchups

`https://www.covers.com/sports/mlb/matchups`

- MLB teams named: **5** (Angels, Athletics, Dodgers, Mets)
- percentage pairs summing to ~100: **22** (e.g. [(50, 50), (50, 50), (50, 50)])
- split-ish JSON keys: bsbetslipapibaseurl

_First 400 characters:_

```

<!DOCTYPE html>
<html lang="en" data-league="MLB">
    <head>
        
    <title>MLB Matchups 2026 - Today&#x27;s Baseball Previews, Scores, &amp; Schedules</title>
    <meta name="description" content="MLB Scores &amp; Matchups for Sept. 26, 2026 including previews, scores, schedule, stats, results, betting trends, and more." />
        <meta name="keywords" content=" mlb, mlb scores, mlb match
```

_A parser gets written against whichever of these is JSON on a stable path, and only after a second run on a different day confirms it is not a one-off. Two sources decayed this season already; a third is worth having only if it is sturdier than what it joins._
