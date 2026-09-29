# When the model loves a team and the market doesn't, who is right?

_The hypothesis: a team the stat model rates far ahead, which the market prices only modestly, is a game where the two disagree - and the claim is the market wins those. This is not about the stat model's level but about its DEVIATION from the price, which is the Benter framing: the price is the best predictor available, and a model is worth only what its deviation from it is worth._

- graded games with both an index gap and a two-sided price: **1136**

## The grid the question was asked in

_Margin quartile is the board's own index gap. Each cell backs the stat side; the italic note is what FADING it returned instead._

| | stat side ≤-200 | stat side -199..-151 | stat side -150..-110 | stat side -109..+109 | stat side ≥+110 |
|---|---|---|---|---|---|
| **smallest gap (Q1)** | back +44% / fade -100% (n=4) | back +7% / fade -19% (n=37) | back -12% / fade +10% (n=99) | back -10% / fade +5% (n=58) | back -4% / fade -3% (n=86) |
| **Q2** | back +3% / fade -6% (n=14) | back +6% / fade -15% (n=56) | back +11% / fade -18% (n=106) | back -2% / fade -5% (n=63) | back +29% / fade -30% (n=45) |
| **Q3** | back +14% / fade -40% (n=15) | back -25% / fade +35% (n=55) | back +1% / fade -7% (n=132) | back -13% / fade +6% (n=41) | back -1% / fade -4% (n=41) |
| **biggest gap (Q4)** | back +3% / fade -20% (n=48) | back +5% / fade -16% (n=78) | back -6% / fade -1% (n=108) | back -14% / fade +7% (n=37) | back -17% / fade +4% (n=13) |

### The exact cell named

_biggest index gap (Q4), stat side priced -150..-110 - the model loves them, the market only mildly does_

- backing the stat side: 58-50 · -6.2u · **-5.8%** (n=108)
- **fading it** (backing the other team): 50-58 · -0.6u · **-0.6%** (n=108)

## Divergence quintiles (the powered version)

_`divergence` = percentile(index gap) - percentile(de-vigged price). High means the model likes them much more than the market does. Each row backs the stat side, fades the stat side, and - the control that decides it - backs the SAME price band irrespective of the model, because fading a -150 favourite just means backing a dog._

| divergence | back stat side | fade stat side | control: same prices, any model read | fade minus control |
|---|---|---|---|---|
| Q1 (-0.91..-0.28) | 133-94 · -10.4u · **-4.6%** (n=227) | 94-133 · -0.6u · **-0.3%** (n=227) | 477-659 · -62.3u · **-5.5%** (n=1136) | **+5.2 pts** |
| Q2 (-0.28..-0.07) | 136-91 · +6.4u · **+2.8%** (n=227) | 91-136 · -26.4u · **-11.6%** (n=227) | 792-928 · -68.1u · **-4.0%** (n=1720) | **-7.7 pts** |
| Q3 (-0.07..+0.07) | 134-93 · +18.4u · **+8.1%** (n=227) | 93-134 · -31.1u · **-13.7%** (n=227) | 1118-1132 · -76.6u · **-3.4%** (n=2250) | **-10.3 pts** |
| Q4 (+0.07..+0.27) | 111-116 · -21.5u · **-9.5%** (n=227) | 116-111 · +4.6u · **+2.0%** (n=227) | 1072-1044 · -60.0u · **-2.8%** (n=2116) | **+4.9 pts** |
| Q5 (+0.27..+0.88) | 110-118 · -6.5u · **-2.8%** (n=228) | 118-110 · -7.4u · **-3.2%** (n=228) | 1001-893 · -36.0u · **-1.9%** (n=1894) | **-1.3 pts** |

_Q5 is the hypothesis: the 228 games where the model is most out of step with the price._

## Does the best quintile beat the search that found it?

- fading the stat side in the top quintile: **-3.2%**
- biggest a redraw manufactures across five quintiles: median **+5.4%**, 95th pct **+14.5%**
- **corrected p = 0.979**

**Does not clear the scan** on its own.

## Does the shape repeat? (split-half)

| divergence | fade ROI, half A | fade ROI, half B |
|---|---|---|
| Q1 | +9.1% | -11.0% |
| Q2 | -11.5% | -11.8% |
| Q3 | -31.2% | +3.3% |
| Q4 | +11.4% | -4.8% |
| Q5 | -3.2% | -3.3% |

- **split-half r = -0.59** over 5 quintiles

_Not repeatable. The quintile pattern in one half does not predict the other, so the monotonic-looking column above is noise read as a trend._

## Top quintile over time

- in-sample: 55-50 · -2.4u · **-2.2%** (n=105)
- holdout: 63-60 · -5.0u · **-4.1%** (n=123)

## How to read this

- the **fade minus control** column is the only number that isolates the disagreement; a raw fade ROI includes whatever backing that price range did all season
- `ev_model` already found price x signal interactions at -0.0167 holdout log-loss with a CI excluding zero on the wrong side, which is the same claim measured with every game instead of a cell. If the delta column here is positive AND split-half holds, the two agree and there is something to build on
- nothing here changes the board on its own.
