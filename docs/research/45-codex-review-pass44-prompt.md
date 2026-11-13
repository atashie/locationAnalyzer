# Codex adversarial review, pass 44 — the pass 43 repairs

You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

Repository: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`, at commit
`3a86018`. Python: `v2/.venv/Scripts/python.exe`. Node is on PATH. **Do not create temporary
directories inside the repository** — pass pytest an explicit `--basetemp` outside it, or skip the
full suite and say so.

**This pass reviews the repairs to your pass 43, not the original work.** Your report is at
`docs/research/44-codex-review-pass43-counterexamples/REPORT.md`; the reproducers I re-ran are
beside it. The question for each finding is narrow: **does the repair actually close it, and did
the repair break something else?** A repair that moves the defect rather than removing it is worth
more to me than a new finding elsewhere.

## What changed, finding by finding

| your finding | what I did |
|---|---|
| F1, boot `ReferenceError` | `loadFixtures` returns `{manifest, values, statuses}`; `initWorker` takes all three |
| F2, the harness passed wrong decoders | `worker.js` reports a three-way verdict plane via a new `{type:'verdicts'}` message; the harness compares every cell, cross-checks mask and counts against the plane, compares the digest over the same bytes, and fails a case that asserts nothing. New `mutate_worker.mjs` requires 9 wrong decoders to be caught |
| F3, the export's third grid | new `scripts/measure_export_regrid.py` and a section in the S3.5 write-up |
| F4, the candidate in the product manifest | exported only under `--candidates` |
| F5, the wrong v1 size baseline | new `v1_plane()`; figures restated as +18.2% / 31,120 bytes |
| F6, the 15-minute "peak" | `--thresholds sweep`; the write-up now says 14, and the unmeasured explanation is withdrawn |
| F7, fractional thresholds | both decoders refuse a non-integer threshold |
| F8, the unchecked explicit transform | the build record's `nrows`/`ncols` are compared to the array |
| F9, model disagreement read as household accuracy | requalified throughout; "buys nothing a household notices" withdrawn |
| your note on the horizon's authority | `worker.js` refuses at init if a `BEYOND_HORIZON` cell's bound disagrees with the manifest's `horizon_s` |

## The claims to attack, hardest first

**A. Is F2 actually closed, or did I move it?** The harness now trusts the worker's own
`state.verdict`. Attack that:

* `verdict[]`, `mask[]` and the RGBA buffer are written in the same branch. Is a defect possible
  that corrupts what a **viewer** sees while leaving the verdict plane right? The harness checks
  `res.rgba.byteLength` and nothing else about the pixels. Construct one.
* `mutate_worker.mjs` has nine mutations. Are any **caught for the wrong reason** — a crash, a
  length error, or the `INERT` path — rather than by a verdict comparison? Is there a wrong
  decoder none of the nine resembles, which still passes the harness?
* the `INERT` detector compares mutated source to original. Can a mutation change the source and
  still be a no-op at runtime, so it reports "caught" or "survived" misleadingly?
* `delete require.cache[...]` plus the `self`/`performance` shimming: does any state leak between
  mutation runs now that the worker holds a verdict plane as well?

**B. `measure_export_regrid.py` re-implements the raster's tiling, and that is where I expect to be
wrong.** It computes a pixel index as `floor((lon − west) / (east − west) · ncols)`. The exporter
builds its destination with `rasterio.transform.from_bounds`. Are those the same tiling, at the
edges and at the half-open boundaries? If they differ, every number in that new section is wrong.
Check it against `rasterio`'s own `rowcol`, and against what the **browser** would compute from
the manifest's `bounds_wgs84`. Also: is comparing a structure's source-grid verdict against its
exported-pixel verdict the right comparison at all, or is some of that 2.42% an artifact of my
index arithmetic rather than of the reprojection?

**C. The horizon checksum.** `worker.js` scans each layer for the **first** `BEYOND_HORIZON` cell
and compares its byte to `ceil(horizon_s/60)`, then `break`s. Is one cell enough? `Surface.validate`
forces every such bound to equal the horizon, so they should be identical — but the planes arriving
at a browser have been through an exporter and a network. Say whether a single-cell check is
sufficient, cheap enough to widen, or security theatre. Also check the `min(expectedByte, 254)`
against `wire.encode_planes`'s own saturation, and whether a layer with **no** `BEYOND_HORIZON`
cell silently skips a check it should fail.

**D. The fractional-threshold refusal.** Python raises `ValueError`, JavaScript throws. Does
either break a legitimate existing caller — `evaluate` accepts a `threshold_s` of any magnitude,
and `Criterion` does not require whole minutes. Is refusing the right response, or should the
format answer a fractional threshold **conservatively** (toward unknown) rather than not at all?
Argue the alternative if you think it is better.

**E. The restated size figures.** `v1_plane` writes `255` wherever the status is not `OK`. Is that
what v1 **actually** wrote for each of these cells — check against `grid.encode_minutes` on the
same surface, not against my description of it. And is deflate at level 9 on a raw plane a fair
proxy for transfer size, given the browser fetches these over HTTP with whatever encoding the
server negotiates?

**F. Did the F4 fix break anything?** The product manifest now has one layer. Does
`measure_export_regrid.py` still work when the candidate is absent, does
`tests/test_export_published.py` assert the right thing, and is there now a path where the page
loads a manifest with zero layers?

**G. The write-ups after the corrections.** `docs/experiments/s3-1-candidate-grids.md` and
`s3-5-browser-path.md` were both edited rather than rewritten. Find any place where a correction
contradicts a sentence I left standing, where a withdrawn claim still appears in a summary, or
where I have now **over**-corrected into a claim weaker than the evidence supports. The grid
decision "keep 100 m" must still be supported after F9's requalification — if it is not, say so in
those words.

**H. Anything the repairs introduced.** New files: `mutate_worker.mjs`,
`measure_export_regrid.py`, `tests/test_export_published.py`, and the `verdicts` message. Review
them as new code, not as repairs.

## Output

For each finding: severity, the exact file and line, a **runnable reproducer**, and what it costs —
a number that moves, or a claim that must be withdrawn. For each of your pass 43 findings, say
plainly whether the repair **closes it, narrows it, or moves it**. Say which of my claims you
checked and could not break; that is as useful as a finding.
