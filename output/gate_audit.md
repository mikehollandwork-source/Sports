# Gate audit — is each gate earning its weight, in every period?

_For each gate, the games it UNIQUELY rejects: passing every other gate and failing only this one. That is what the gate saves you from, and a gate earns its weight when those games are consistently worse than the picks it lets through._

- graded games with a consensus side: **1128**
- evaluated under the CURRENT settings: confirm **BOTH**, line **≥0.5%**, imbalance **>0.2**

- picks under these gates: **48-19 · +30.0%** (n=67)

## Overall — what each gate rejects

| gate | uniquely rejects | their ROI | picks' ROI | gate is worth |
|---|---|---|---|---|
| `handle=tickets` | 37 | **+12.7%** | +30.0% | **+17.3 pts** |
| `book read` | 0 | — | — | — |
| `book confirms` | 149 | **-6.8%** | +30.0% | **+36.8 pts** |
| `line against` | 181 | **-2.4%** | +30.0% | **+32.4 pts** |

## By month — does each gate hold up throughout?

_A gate whose contribution flips sign between periods is not a gate, it is a coin that landed the same way for a while._

| month | games | picks | `handle=tickets` | `book read` | `book confirms` | `line against` |
|---|---|---|---|---|---|---|
| 2026-06 | 78 | 0-0 +0% | _0_ | _0_ | _0_ | _0_ |
| 2026-07 | 370 | 10-6 +18% | _9_ | _0_ | +28pts (32) | -2pts (43) |
| 2026-08 | 410 | 25-4 +59% | +56pts (18) | _0_ | +73pts (87) | +65pts (86) |
| 2026-09 | 270 | 13-9 -0% | -52pts (10) | _0_ | -16pts (30) | +16pts (52) |

_Cells show what the gate was worth that month - the picks' ROI minus the ROI of what it rejected - with the rejection count. Italic means too few rejections to judge._

## Verdict

| gate | months judged | positive | median worth | verdict |
|---|---|---|---|---|
| `handle=tickets` | 2 | 1/2 | +2% | **marginal** — helps on average, inconsistent |
| `book read` | 0 | — | — | too few months to judge |
| `book confirms` | 3 | 2/3 | +28% | **earns it** — positive in most months |
| `line against` | 3 | 2/3 | +16% | **earns it** — positive in most months |

_A gate that only rejects a handful of games cannot be judged from this - absence of evidence, not evidence it is useless._
