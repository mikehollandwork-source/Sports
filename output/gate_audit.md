# Gate audit — is each gate earning its weight, in every period?

_For each gate, the games it UNIQUELY rejects: passing every other gate and failing only this one. That is what the gate saves you from, and a gate earns its weight when those games are consistently worse than the picks it lets through._

- graded games with a consensus side: **1218**
- evaluated under the CURRENT settings: confirm **BOTH**, line **≥1.0%**, imbalance **>0.2**

- picks under these gates: **63-41 · +5.5%** (n=104)

## Overall — what each gate rejects

| gate | uniquely rejects | their ROI | picks' ROI | gate is worth |
|---|---|---|---|---|
| `handle=tickets` | 34 | **-1.4%** | +5.5% | **+6.9 pts** |
| `book read` | 0 | — | — | — |
| `book confirms` | 64 | **+2.3%** | +5.5% | **+3.2 pts** |
| `line against` | 348 | **-2.6%** | +5.5% | **+8.1 pts** |

## By month — does each gate hold up throughout?

_A gate whose contribution flips sign between periods is not a gate, it is a coin that landed the same way for a while._

| month | games | picks | `handle=tickets` | `book read` | `book confirms` | `line against` |
|---|---|---|---|---|---|---|
| 2026-06 | 78 | 0-0 +0% | _0_ | _0_ | _0_ | _0_ |
| 2026-07 | 370 | 9-8 -3% | _5_ | _0_ | -13pts (17) | -9pts (79) |
| 2026-08 | 410 | 32-18 +10% | +10pts (15) | _0_ | +10pts (24) | +11pts (168) |
| 2026-09 | 360 | 22-15 +3% | -3pts (14) | _0_ | +4pts (23) | +16pts (101) |

_Cells show what the gate was worth that month - the picks' ROI minus the ROI of what it rejected - with the rejection count. Italic means too few rejections to judge._

## Verdict

| gate | months judged | positive | median worth | verdict |
|---|---|---|---|---|
| `handle=tickets` | 2 | 1/2 | +4% | **marginal** — helps on average, inconsistent |
| `book read` | 0 | — | — | too few months to judge |
| `book confirms` | 3 | 2/3 | +4% | **marginal** — helps on average, inconsistent |
| `line against` | 3 | 2/3 | +11% | **earns it** — positive in most months |

_A gate that only rejects a handful of games cannot be judged from this - absence of evidence, not evidence it is useless._
