
### Whole-minute encoding at a threshold: grocery / walk (triangle, 2026-11-09 13:37:24)

`evaluate` uses float seconds, so nothing above is wrong on the Python side. A browser holding only the encoded raster answers a *different* threshold, and the error is one-sided: it shows cells as passing that do not pass, and never hides a cell that does. `wrong of shown` is `Pr(not actually a pass | displayed as a pass)` — the shape of conditional Codex pass 25 found missing from the estimand set, here for the encoding rather than the routing. It is an **artifact-to-artifact** comparison, the encoded raster against the float surface that produced it, and says nothing about routing or destination validity. `of all OK` is over OK cells, not over the frame. The browser path already built (`spikes/g3-render/worker.js:139`) does threshold the minute byte, so this is not hypothetical.

| rounding | T | truth | shown | wrong | missed | wrong of shown | of all OK | wrong buildings | of shown buildings |
|---|---|---|---|---|---|---|---|---|---|
| rint (was shipped) | 10 min | 24,245 | 26,396 | **2,151** | 0 | **8.15%** | 0.84% | 7,959 | 9.04% |
| rint (was shipped) | 15 min | 47,495 | 50,071 | **2,576** | 0 | **5.14%** | 1.00% | 8,702 | 5.04% |
| rint (was shipped) | 25 min | 93,562 | 95,654 | **2,092** | 0 | **2.19%** | 0.81% | 5,317 | 1.75% |
| rint (was shipped) | 45 min | 161,664 | 163,085 | **1,421** | 0 | **0.87%** | 0.55% | 1,895 | 0.44% |
| ceil (shipped) | 10 min | 24,245 | 24,245 | **0** | 0 | **0.00%** | 0.00% | 0 | 0.00% |
| ceil (shipped) | 15 min | 47,495 | 47,495 | **0** | 0 | **0.00%** | 0.00% | 0 | 0.00% |
| ceil (shipped) | 25 min | 93,562 | 93,562 | **0** | 0 | **0.00%** | 0.00% | 0 | 0.00% |
| ceil (shipped) | 45 min | 161,664 | 161,664 | **0** | 0 | **0.00%** | 0.00% | 0 | 0.00% |
| floor | 10 min | 24,245 | 28,540 | **4,295** | 0 | **15.05%** | 1.67% | 15,660 | 16.36% |
| floor | 15 min | 47,495 | 52,554 | **5,059** | 0 | **9.63%** | 1.97% | 16,949 | 9.37% |
| floor | 25 min | 93,562 | 97,609 | **4,047** | 0 | **4.15%** | 1.58% | 9,933 | 3.22% |
| floor | 45 min | 161,664 | 164,492 | **2,828** | 0 | **1.72%** | 1.10% | 3,702 | 0.86% |

`missed` is 0 in every row, in every rounding, which is the structural claim: rounding a value at or below `60T` cannot carry it above `T` minutes, so a minute-only client can only be too generous.

**`ceil` is exact for a finite OK cell at a whole-minute threshold below 254.** `ceil(s/60) <= T` is equivalent to `s <= 60T`, which is `evaluate`'s own comparison, so `wrong` and `missed` are both 0 by construction rather than by luck on this layer. At `T >= 254` the clip breaks it and NODATA is not a minute at all. The cost is the displayed number: an upper bound on our model's time, overstating by less than 60 s (a 0.1 s walk displays as 1 minute), where `rint` is within 30 s either way.

**Decided 2026-11-09: `ceil`.** The `rint` row is kept as the comparison the decision was made against, not as a live option. Every minute raster was re-encoded from its stored seconds (`scripts/reencode_minute_rasters.py`, max shift 1 minute on all eight) and every raster and the browser manifest now carry `encoding=uint8-minutes-ceil-v1`, so a stale artifact is recognisable rather than merely byte-different. The walked-audit sheet's `encoding_disagrees_min` column is now blank on every row, where three of nineteen disagreed before.

**What this does not fix.** The same worker loop treats NODATA as excluded, so the export still collapses UNKNOWN into EXCLUDED -- NODATA is one code for OFF_NETWORK and BEYOND_HORIZON alike, and the three-outcome algebra S0 built the Reason enum for does not survive to the browser. That is the larger of the two step-6 findings and the rounding has nothing to do with it.

### Whole-minute encoding at a threshold: grocery / walk (triangle, 2026-11-10 14:39:23)

`evaluate` uses float seconds, so nothing above is wrong on the Python side. A browser holding only the encoded raster answers a *different* threshold, and the error is one-sided: it shows cells as passing that do not pass, and never hides a cell that does. `wrong of shown` is `Pr(not actually a pass | displayed as a pass)` — the shape of conditional Codex pass 25 found missing from the estimand set, here for the encoding rather than the routing. It is an **artifact-to-artifact** comparison, the encoded raster against the float surface that produced it, and says nothing about routing or destination validity. `of all OK` is over OK cells, not over the frame. The browser path already built (`spikes/g3-render/worker.js:139`) does threshold the minute byte, so this is not hypothetical.

| rounding | T | truth | shown | wrong | missed | wrong of shown | of all OK | wrong buildings | of shown buildings |
|---|---|---|---|---|---|---|---|---|---|
| rint (was shipped) | 10 min | 24,255 | 26,409 | **2,154** | 0 | **8.16%** | 0.84% | 7,959 | 9.04% |
| rint (was shipped) | 15 min | 47,509 | 50,083 | **2,574** | 0 | **5.14%** | 1.00% | 8,703 | 5.04% |
| rint (was shipped) | 25 min | 93,575 | 95,661 | **2,086** | 0 | **2.18%** | 0.81% | 5,318 | 1.75% |
| rint (was shipped) | 45 min | 161,670 | 163,093 | **1,423** | 0 | **0.87%** | 0.55% | 1,902 | 0.45% |
| ceil (shipped) | 10 min | 24,255 | 24,255 | **0** | 0 | **0.00%** | 0.00% | 0 | 0.00% |
| ceil (shipped) | 15 min | 47,509 | 47,509 | **0** | 0 | **0.00%** | 0.00% | 0 | 0.00% |
| ceil (shipped) | 25 min | 93,575 | 93,575 | **0** | 0 | **0.00%** | 0.00% | 0 | 0.00% |
| ceil (shipped) | 45 min | 161,670 | 161,670 | **0** | 0 | **0.00%** | 0.00% | 0 | 0.00% |
| floor | 10 min | 24,255 | 28,552 | **4,297** | 0 | **15.05%** | 1.67% | 15,672 | 16.37% |
| floor | 15 min | 47,509 | 52,567 | **5,058** | 0 | **9.62%** | 1.97% | 16,951 | 9.37% |
| floor | 25 min | 93,575 | 97,621 | **4,046** | 0 | **4.14%** | 1.58% | 9,935 | 3.22% |
| floor | 45 min | 161,670 | 164,495 | **2,825** | 0 | **1.72%** | 1.10% | 3,707 | 0.86% |

`missed` is 0 in every row, in every rounding, which is the structural claim: rounding a value at or below `60T` cannot carry it above `T` minutes, so a minute-only client can only be too generous.

**`ceil` is exact for a finite OK cell at a whole-minute threshold below 254.** `ceil(s/60) <= T` is equivalent to `s <= 60T`, which is `evaluate`'s own comparison, so `wrong` and `missed` are both 0 by construction rather than by luck on this layer. At `T >= 254` the clip breaks it and NODATA is not a minute at all. The cost is the displayed number: an upper bound on our model's time, overstating by less than 60 s (a 0.1 s walk displays as 1 minute), where `rint` is within 30 s either way.

**Decided 2026-11-09: `ceil`.** The `rint` row is kept as the comparison the decision was made against, not as a live option. Every minute raster was re-encoded from its stored seconds (`scripts/reencode_minute_rasters.py`, max shift 1 minute on all eight) and every raster and the browser manifest now carry `encoding=uint8-minutes-ceil-v1`, so a stale artifact is recognisable rather than merely byte-different. The walked-audit sheet's `encoding_disagrees_min` column is now blank on every row, where three of nineteen disagreed before.

**What this does not fix.** The same worker loop treats NODATA as excluded, so the export still collapses UNKNOWN into EXCLUDED -- NODATA is one code for OFF_NETWORK and BEYOND_HORIZON alike, and the three-outcome algebra S0 built the Reason enum for does not survive to the browser. That is the larger of the two step-6 findings and the rounding has nothing to do with it.
