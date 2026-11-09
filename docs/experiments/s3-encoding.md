
### Whole-minute encoding at a threshold: grocery / walk (triangle, 2026-11-09 13:21:33)

`evaluate` uses float seconds, so nothing above is wrong on the Python side. A browser holding only the encoded raster answers a *different* threshold, and the error is one-sided: it shows cells as passing that do not pass, and never hides a cell that does. `wrong of shown` is `Pr(not actually a pass | displayed as a pass)` — the shape of conditional Codex pass 25 found missing from the estimand set, here for the encoding rather than the routing. It is an **artifact-to-artifact** comparison, the encoded raster against the float surface that produced it, and says nothing about routing or destination validity. `of all OK` is over OK cells, not over the frame. The browser path already built (`spikes/g3-render/worker.js:139`) does threshold the minute byte, so this is not hypothetical.

| rounding | T | truth | shown | wrong | missed | wrong of shown | of all OK | wrong buildings | of shown buildings |
|---|---|---|---|---|---|---|---|---|---|
| rint (shipped) | 10 min | 24,245 | 26,396 | **2,151** | 0 | **8.15%** | 0.84% | 7,959 | 9.04% |
| rint (shipped) | 15 min | 47,495 | 50,071 | **2,576** | 0 | **5.14%** | 1.00% | 8,702 | 5.04% |
| rint (shipped) | 25 min | 93,562 | 95,654 | **2,092** | 0 | **2.19%** | 0.81% | 5,317 | 1.75% |
| rint (shipped) | 45 min | 161,664 | 163,085 | **1,421** | 0 | **0.87%** | 0.55% | 1,895 | 0.44% |
| ceil | 10 min | 24,245 | 24,245 | **0** | 0 | **0.00%** | 0.00% | 0 | 0.00% |
| ceil | 15 min | 47,495 | 47,495 | **0** | 0 | **0.00%** | 0.00% | 0 | 0.00% |
| ceil | 25 min | 93,562 | 93,562 | **0** | 0 | **0.00%** | 0.00% | 0 | 0.00% |
| ceil | 45 min | 161,664 | 161,664 | **0** | 0 | **0.00%** | 0.00% | 0 | 0.00% |
| floor | 10 min | 24,245 | 28,540 | **4,295** | 0 | **15.05%** | 1.67% | 15,660 | 16.36% |
| floor | 15 min | 47,495 | 52,554 | **5,059** | 0 | **9.63%** | 1.97% | 16,949 | 9.37% |
| floor | 25 min | 93,562 | 97,609 | **4,047** | 0 | **4.15%** | 1.58% | 9,933 | 3.22% |
| floor | 45 min | 161,664 | 164,492 | **2,828** | 0 | **1.72%** | 1.10% | 3,702 | 0.86% |

`missed` is 0 in every row, in every rounding, which is the structural claim: rounding a value at or below `60T` cannot carry it above `T` minutes, so a minute-only client can only be too generous.

**`ceil` is exact for a finite OK cell at a whole-minute threshold below 254.** `ceil(s/60) <= T` is equivalent to `s <= 60T`, which is `evaluate`'s own comparison, so `wrong` and `missed` are both 0 by construction rather than by luck on this layer. At `T >= 254` the clip breaks it and NODATA is not a minute at all. The cost is the displayed number: an upper bound on our model's time, overstating by less than 60 s (a 0.1 s walk displays as 1 minute), where `rint` is within 30 s either way.

**Not yet decided.** Changing `encode_minutes` changes committed rasters and moves the boundaries of the legacy minute codes 251-254, which are real answers in artifacts already on disk. The browser path already built does threshold the minute byte, and the same loop treats NODATA as excluded -- so the export also collapses UNKNOWN into EXCLUDED, a second and larger step-6 finding that changing the rounding does not address. This section is the measurement the decision should be made against. `scripts/audit_recommendations.py` marks the affected rows in the walked-audit sheet (`encoding_disagrees_min`) so a walked journey is attributed to the right verdict in the meantime.
