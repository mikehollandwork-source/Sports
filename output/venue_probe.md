# Does the MLB API carry ballpark orientation?

_`PARK_BEARING` drives the board's out/in wind read and its values are estimates. Verifying them against public record is blocked in this environment — andrewclem.com, baseball-almanac.com and wikipedia.org are all refused by the egress policy. MLB's own StatsAPI is reachable, and its venue `location` hydration is documented to carry `azimuthAngle`, which is this bearing._

- venues returned: **62**

## Every populated field, and on how many venues

| field | venues |
|---|---|
| `location.city` | 62 |
| `location.country` | 62 |
| `fieldInfo.turfType` | 62 |
| `fieldInfo.roofType` | 62 |
| `fieldInfo.capacity` | 59 |
| `fieldInfo.leftLine` | 59 |
| `fieldInfo.center` | 59 |
| `fieldInfo.rightLine` | 59 |
| `location.address1` | 57 |
| `location.state` | 57 |
| `location.stateAbbrev` | 57 |
| `location.defaultCoordinates` | 57 |
| `location.postalCode` | 56 |
| `location.phone` | 39 |
| `fieldInfo.leftCenter` | 36 |
| `fieldInfo.rightCenter` | 36 |
| `location.azimuthAngle` | 33 |
| `location.elevation` | 33 |
| `fieldInfo.left` | 23 |
| `fieldInfo.right` | 17 |
| `location.address2` | 10 |

- venues with **`azimuthAngle`**: **33/62**

## The bearings, as MLB reports them

| venue | azimuthAngle |
|---|---|
| American Family Field | 129.0 |
| Angel Stadium | 43.61 |
| Busch Stadium | 62.0 |
| Chase Field | 0.0 |
| Citi Field | 13.0 |
| Citizens Bank Park | 9.0 |
| Comerica Park | 150.0 |
| Coors Field | 4.0 |
| Daikin Park | 343.0 |
| Fenway Park | 45.0 |
| George M. Steinbrenner Field | 60.0 |
| Globe Life Field | 30.0 |
| Great American Ball Park | 122.0 |
| Kauffman Stadium | 46.0 |
| Nationals Park | 28.0 |
| Oracle Park | 85.0 |
| Oriole Park at Camden Yards | 31.0 |
| PNC Park | 116.0 |
| Petco Park | 0.0 |
| Progressive Field | 0.0 |
| Rate Field | 127.0 |
| Rogers Centre | 345.0 |
| Salt River Fields at Talking Stick | 72.0 |
| Sutter Health Park | 46.0 |
| T-Mobile Park | 49.0 |
| TD Ballpark | 138.0 |
| Target Field | 129.0 |
| Tropicana Field | 359.0 |
| Truist Park | 145.0 |
| UNIQLO Field at Dodger Stadium | 26.0 |
| Wrigley Field | 37.0 |
| Yankee Stadium | 75.0 |
| loanDepot park | 128.0 |

_If this table is complete, PARK_BEARING should be replaced by these values and the estimates deleted._
