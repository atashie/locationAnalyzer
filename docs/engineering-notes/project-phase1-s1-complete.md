---
name: project-phase1-s1-complete
description: "Phase 1 stage S1 (the expansion primitive) after Codex pass 9 - roots are partial edges, walk agrees at the median with heavy tails, drive carries a +50 s bias that is not the adapter"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-04T14:57:34.952Z
---

Committed 2026-11-04 as `c04e34d`, then `fd67b02` absorbing Codex pass 9 (4 High, 4 Medium, no
Critical; `docs/research/16-...`). 194 tests pass. Results appended to
`docs/experiments/g1-routing.md`; plan §S1 rewritten with the numbers.

**Valhalla must be running for any S1/S3 spike**: `wsl.exe -e bash -lc 'cd
/mnt/c/Users/arikt/documents/github/distanceFinder/v2/infra/valhalla && docker compose up -d'`
starts `valhalla-slice` on :8002 with the Phase 0 slice tiles. `valhalla-nc` on :8003 and `motis`
on :8080 were already up. Slice-era baselines need `LOCFINDER_METRO=slice`.

**Six structural defects found before any aggregate, all fixed or reported in `expansion.py`:**
1. **`skip_opposites` must be `false`.** With it on, 636/254,323 drive edges (0.25%) name a
   predecessor Valhalla never serialised, so `strict=True` failed on every real request. Off: 0.
2. **The two directed features of one road were never merged** - same geometry twice in the
   STRtree, `nearest()` picked arbitrarily. **15.65%** of cells changed, 99.7% earlier (measured
   with node times and identities held fixed; the first 8.78% figure was confounded).
3. **One-way edges were marked bidirectional.** 9.17% of cells changed, **100% later** - the only
   possible sign when edges are removed, which is the consistency check. 12.7% are one-way-only.
4. **`skip_opposites=true` does not suppress every opposite** (664 pairs survive), so it cannot be
   inferred. `opposites_included` is a required keyword with no default.

**The headline result.** The old published method reproduced *exactly* (median 69 s, p90 271 s,
+66 s), validating the comparison. Then:

| | walk | drive |
|---|---|---|
| total signed median | +28 s | +82 s |
| access leg subtracted | **+0.0 s** (median abs 1.9 s) | **+50 s** |
| sampled at nodes - no grid, access leg or interpolation | **+0.0 s** (median abs 0.0 s) | **+50 s**, later on 92.5% |

**"Exact" was my error** (pass-9 H4): a median bounds no cell. Walk's node comparison has p90
**30 s** and max **632 s**, 17.1% later / 14.6% earlier. The defensible claim is **median agreement
with heavy tails**, and the tails are unexplained. The walk residual is the access leg
(bias/charge ratio 1.02). **Drive is not the adapter** - the gap survives at nodes and survived the
root fix unchanged. Mode-specific
**and the cause is now settled: destination selection, not penalties.** My turn-cost hypothesis was
wrong. `/expansion` is a MULTI-SOURCE reverse search reporting the time along the cost-optimal path
to the *cost*-nearest POI, while the matrix minimum takes the *smallest time* over POIs. Vary the
POI count: drive **1 POI -> +0.0 s**, 3 POIs -> +131 s; walk 1 -> +11.5 s, 3 -> +6.0 s. Controls:
`/route` and `sources_to_targets` agree to +0.6 s (so the reference was not the confound); the gap
persists where tree and router agree on path *length* (+206 s, so not path choice); zeroing
penalties halves rather than removes it (expected - penalties drive both divergence and route
choice, so that arm cannot separate them).

**So the primitive is FAITHFUL and the "+50 s biased drive primitive" framing is withdrawn.** This
is **the same phenomenon as pass-8 H2, one level up**: any multi-destination surface is an **upper
bound** on `min_d t`. Sharper product boundary: an **anchor** drive surface is faithful (one
destination); a **category** drive surface over-reports, giving false exclusions only. At a
10-minute drive threshold it misses **5 of 12
reference-positive cells** - a *conditional* figure, because the sample is drawn only from the
model's own reachable set, so a truly-close cell the model cannot reach has **zero probability of
being sampled** (pass-9 M3). Not a rate. Bike is still untested and inherits both the access-leg
and the selection question.

**Corrected a Phase 0 conclusion.** `g1-routing.md` called our walk model "unbiased" on +0.2 min.
Decomposed by access distance it is a *net* of ~10 s on-network optimism and a conservative access
charge reaching +97 s at 100-200 m, cancelling near the sample's median access distance of 31 m.
The cancellation is a property of the sample, not the model. Direction survives (<1% of a 22-min
journey) but "unbiased" overstates it, and **`ACCESS_SPEED_FACTOR` is now the larger term and is
still an unmeasured prior** - an access-leg calibration task affects every mode and both engines.

**Unit hazard, and my error.** `matrix_*.json` stores **minutes** (`own_min` = "own, in minutes",
not "own minimum"); `raster_primitive_*.json` stores **seconds**. I mixed them and got an
access-charge-to-bias ratio of 121.6 - the implausible number is what exposed it. Both spikes now
convert explicitly. Lesson that keeps paying: **treat an implausible ratio as a signal, not a
result.**

**Pass 9's biggest find (H1): a root is a PARTIAL edge.** The origin sits inside the road and
Valhalla does not split it, so neither endpoint is the near end. Time zero landed on a vertex a
matrix query answered in 2-5 s; both opposing roots picked the same nearer endpoint and merged,
**deleting a legal direction**; a partial duration was interpolated over a full road. Roots are now
**split at the origin's projection** (5 of 6 on the real payload), and **successors outrank origin
proximity** - 2 of 6 real roots had proximity contradict an unambiguous successor signal.

**Also from pass 9:** the merging effect is **15.65%**, not 8.78% (the old "before" changed four
things at once); a key groups a *shape*, not a topological edge (519 groups hold >2 features, max
5 - reported, identity not claimed); a closed loop defeated the endpoint-only order test; decreasing
cumulative durations were clamped and accepted rather than refused.

**Open from S1:** one root of six is still unorientable so `strict=True` fails on the real payload -
**`strict` is a self-consistency check, not a production validity gate**, and `dangling == 0` is not
one either; the walk/drive tails are unexplained; `_node_key` is a square bucket, not a distance
test; `tau` contains turn/stop costs that interpolation scales (median implied drive speed
3.17 m/s); Valhalla's `cost` exceeds `duration` on 100% of drive features (median cumulative gap
264 s), so carrying cost as a selection weight is a named follow-up; the drive turn-cost mechanism
is a **hypothesis** with a named decisive test.

**Two template/unit errors of mine, both caught by implausible output:** the minutes/seconds mix
above, and a report template that asserted "the remaining bias is our access leg" *unconditionally*,
printing it for drive right after printing drive's FAIL. Conclusions are now derived from results.

Related: [[project-phase1-s0-complete]], [[project-phase0-progress]],
[[feedback-codex-adversarial-review]], [[feedback-experiments-over-priors]].
