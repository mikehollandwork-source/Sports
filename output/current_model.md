# What the current live system would have returned

_Every committed board version replayed under today's gates, scored only on the order-book readings that existed at that moment. A game that qualified in some version and not the last is a withdrawal, and therefore a fade._

- rule: confirm **BOTH** signals · line move **≥0.5%** · imbalance **>0.2** · fade rule **on**

- period: **2026-07-17 → 2026-09-20** (63 slates)

| | record | win rate | units | ROI |
|---|---|---|---|---|
| consensus picks | **49-20** | 71.0% | +19.63u | **+28.4%** |
| fades | **79-86** | 47.9% | +6.49u | **+3.9%** |
| **EVERYTHING** | **128-106** | 54.7% | +26.12u | **+11.2%** |

## Against what actually happened over the same period

| | record | units | ROI |
|---|---|---|---|
| actual ledger | 97-77 | -7.58u | **-4.4%** |
| current model | 128-106 | +26.12u | **+11.2%** |

## Split in half, as a stability check

| | record | win rate | units | ROI |
|---|---|---|---|---|
| first half | **60-51** | 54.1% | +11.08u | **+10.0%** |
| second half | **68-55** | 55.3% | +15.03u | **+12.2%** |

_These picks were never made. Settings chosen partly by looking at this data will flatter themselves here; the confirm change tested alone gave a **+10.2 point** holdout gain, which is the number to plan around._
