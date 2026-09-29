# Walk-forward on the line-movement threshold

_The only gate that earns its keep. `gate_sweep` had handle=tickets at −3.6 points and book-confirm at +1.3; the line gate was +5.8 at the live 1.0% bar and +10.1 at "moved against at all". Those are nested, so the band between is exact: the 185 games moving 0–1% against went 116-69, +10.3% — better than the 316 moving 1%+._

_Which is exactly why it cannot just be lowered. Choosing the best of four thresholds on all the data and quoting its return is how this session produced a +10.5% signal that was reading finished games. So the threshold is chosen on past days only and scored on days the chooser never saw._

- graded games with a majority side and a line reading: **1207**

## every game with a majority side

### Fixed thresholds, whole sample (what NOT to choose from)

| threshold | record |
|---|---|
| moved against at all | 301-200 · **+7.6%** (n=501) |
| ≥0.25% | 258-188 · **+3.9%** (n=446) |
| ≥0.50% | 250-177 · **+5.4%** (n=427) |
| ≥1.00% | 185-131 · **+6.0%** (n=316) |
| ≥2.00% | 106-70 · **+9.3%** (n=176) |

### Rolling walk-forward

- retrained every **10** board days after a **25**-day burn-in · **7** scored blocks
- thresholds it chose: any×3, 2.00%×4
- **out-of-sample: 153-112 · **+2.9%** (n=265)**

### The same out-of-sample days, each threshold held fixed

_The walk-forward is only worth its complexity if it beats every fixed bar over the identical days._

| threshold | over those blocks |
|---|---|
| moved against at all | 218-147 · **+5.8%** (n=365) |
| ≥0.25% | 191-138 · **+3.1%** (n=329) |
| ≥0.50% | 184-128 · **+5.0%** (n=312) |
| ≥1.00% | 130-95 · **+3.3%** (n=225) |
| ≥2.00% | 80-50 · **+10.5%** (n=130) |
| _no line gate at all_ | 501-376 · **-1.3%** (n=877) |

- walk-forward **+2.9%** against the live 1.0% bar **+3.3%** over the same days → **adapting did not pay** — it chose worse than the bar we already run
- best fixed bar out of sample was **2.00%** at +10.5% → **set it once, do not adapt** — a fixed bar beat the walk-forward, so the adaptation was noise-chasing

### Block by block

| block starts | threshold chosen | ROI | n |
|---|---|---|---|
| 2026-07-24 | any | +0.0% | 53 |
| 2026-08-03 | any | -13.0% | 66 |
| 2026-08-13 | any | +6.7% | 77 |
| 2026-08-23 | 2.00% | +56.3% | 13 |
| 2026-09-02 | 2.00% | +20.3% | 18 |
| 2026-09-12 | 2.00% | +2.0% | 21 |
| 2026-09-22 | 2.00% | -2.3% | 17 |

- blocks profitable: **5/7** · median block **+2.0%**

## games that also pass handle=tickets

### Fixed thresholds, whole sample (what NOT to choose from)

| threshold | record |
|---|---|
| moved against at all | 199-132 · **+6.2%** (n=331) |
| ≥0.25% | 173-128 · **+1.7%** (n=301) |
| ≥0.50% | 167-122 · **+2.6%** (n=289) |
| ≥1.00% | 124-84 · **+6.4%** (n=208) |
| ≥2.00% | 78-48 · **+12.0%** (n=126) |

### Rolling walk-forward

- retrained every **10** board days after a **25**-day burn-in · **7** scored blocks
- thresholds it chose: 1.00%×3, 2.00%×4
- **out-of-sample: 79-50 · **+8.6%** (n=129)**

### The same out-of-sample days, each threshold held fixed

_The walk-forward is only worth its complexity if it beats every fixed bar over the identical days._

| threshold | over those blocks |
|---|---|
| moved against at all | 148-96 · **+5.9%** (n=244) |
| ≥0.25% | 131-93 · **+2.2%** (n=224) |
| ≥0.50% | 125-88 · **+2.9%** (n=213) |
| ≥1.00% | 90-62 · **+4.0%** (n=152) |
| ≥2.00% | 58-35 · **+12.0%** (n=93) |
| _no line gate at all_ | 333-243 · **-1.8%** (n=576) |

- walk-forward **+8.6%** against the live 1.0% bar **+4.0%** over the same days → **the adaptive threshold earns its keep**
- best fixed bar out of sample was **2.00%** at +12.0% → **set it once, do not adapt** — a fixed bar beat the walk-forward, so the adaptation was noise-chasing

### Block by block

| block starts | threshold chosen | ROI | n |
|---|---|---|---|
| 2026-07-26 | 1.00% | +7.9% | 27 |
| 2026-08-05 | 1.00% | -21.4% | 29 |
| 2026-08-15 | 1.00% | +28.0% | 21 |
| 2026-08-25 | 2.00% | +71.1% | 10 |
| 2026-09-04 | 2.00% | -2.1% | 16 |
| 2026-09-14 | 2.00% | +11.0% | 16 |
| 2026-09-24 | 2.00% | +7.0% | 10 |

- blocks profitable: **5/7** · median block **+7.9%**
