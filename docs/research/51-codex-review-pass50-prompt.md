# Codex adversarial review, pass 50 — the pass 49 repairs

You are an adversarial reviewer. Your job is to find what is wrong, not to confirm what is right.

Repository: `C:\Users\arikt\documents\github\distanceFinder`, branch `v2-rethink`, at the tip of
`v2-rethink` (pass 49's integration plus one follow-up commit). Python:
`v2/.venv/Scripts/python.exe`.

## Runtime note — read this first, it changes what you can check

Your sandbox on this machine **cannot start processes at all**. Passes 48 and 49 both established
this: every `exec_command` fails with `windows unelevated restricted-token sandbox cannot enforce
split writable root sets`, under `workspace-write`, with and without `--add-dir`, and with
`--ephemeral`. See `docs/engineering-notes/reference-codex-runtime-quirks.md`. So:

* You **cannot** run Python, pytest, `node` or `git`. Do not plan around them.
* You **can** read any file, and you **can** execute JavaScript through the `node_repl` MCP tool.
  Pass 49 used it to replay the whole conformance harness in `vm` contexts, decode the shipped
  NPY and binary planes, and build a run-length index over 330,502 cells. That is the strongest
  tool you have here.
* For anything needing Python, reason from the source and **say what you could not execute**. An
  unexecuted argument clearly labelled as such is worth more to me than a guess dressed as a
  measurement. Pass 49's unexecuted Python findings were among its best.
* Write your report **to stdout as your final message**, not to a file.

## What this pass reviews

Pass 49 found eleven things and I reproduced all eleven. This pass reviews **the repairs**, which
are a larger change than the thing they repaired. Your report on pass 49 is at
`docs/research/50-codex-review-pass49-counterexamples/REPORT.md`; the commit that integrated it is
`052ac7c`.

The repairs, in the order I rate their risk:

1. `export_published_layers.verify_provenance` — a new check that claims something strong.
2. The licence bundle: `v2/licences/`, `write_licence_bundle`, the exported `LICENSES/` and
   `ATTRIBUTION.md`.
3. The strengthened conformance harness and the shipped-bundle check.
4. The `state.computed` lifecycle in `worker.js`.
5. The required byte-order declaration.
6. The corrected cost report.
7. The repaired `byteswap_control.mjs` and the comment-stripping encoding guard.

## The claims to attack, hardest first

### A. `verify_provenance`, and a hazard I have already spotted in it

The claim: reprojecting a **source-cell index** through the same nearest call as the data planes
gives each published cell the identity of the source cell that fed it, so requiring every
published plane to equal its source plane at that index proves all planes share one source cell.
Measured result: 330,502 of 330,502 cells, 0 uncovered, all four planes.

**I think there may be something wrong with this, and I want you to decide.** Every plane is
reprojected with its own fill passed as `src_nodata`, and those fills are **in-band values**:

* `src_fill=wire.VALUE_NONE` (255) — the value plane
* `src_fill=wire.OUTSIDE` (5) — the status plane
* `src_fill=wire.DEST_NONE` (65535) — the destination plane
* `src_fill=wire.ROUTE_CLEAR` (**0**) — the route-flag plane, where 0 is the *overwhelmingly
  common* legitimate value, not a sentinel

The index plane uses `src_nodata=0xFFFFFFFF`, which cannot occur in 330,502 cells. So the index
plane's notion of "which source cells exist" may differ from each data plane's. If rasterio's
nearest resampling skips source cells it considers nodata, the index plane and a data plane can
pick **different** source cells for the same published cell — which would make my check either
fail spuriously or, worse, pass while comparing the wrong pair and hiding a real mismatch.

Questions:

* Does `Resampling.nearest` in rasterio actually honour `src_nodata` by excluding those source
  cells from selection, or does it select them and only then substitute `dst_nodata`? Answer from
  the rasterio/GDAL documentation or source if you can, and say which.
* If it excludes them: is `verify_provenance` sound at all, and is the flag plane's
  `src_nodata=ROUTE_CLEAR=0` a pre-existing bug independent of my new check — i.e. is the
  published flag plane built by resampling that ignores every clear cell?
* If it does not exclude them: say so, and say what `src_nodata` is doing in these calls at all.
* Either way: **the check passed with 0 disagreements on real data.** Is that because the hazard
  is nil, or because this grid is a 1:1 retiling where every published cell has exactly one
  candidate source cell and so the question cannot arise? If it is the second, the check is
  untested against the case it exists for, and the positive controls in
  `tests/test_export_published.py` are on a 2×3 grid with the same property.

That last point is the one I most want attacked: **a provenance check that only ever runs on a
one-to-one mapping has not been exercised.**

### B. The licence bundle

`v2/licences/README.md` states the reasoning; `write_licence_bundle` enforces it.

* Is `ATTRIBUTION.md` actually sufficient for Apache-2.0 §4 redistribution of Foursquare-sourced
  Overture records? Read the generated file at
  `v2/spikes/g3-render/fixtures/published/ATTRIBUTION.md`. §4(a)–(d) each impose something; say
  which are satisfied, which are not, and quote the text you are relying on.
* The Foursquare `NOTICE.txt` could not be fetched (gated Hugging Face repo, HTTP 401), so
  `v2/licences/NOTICE-foursquare.txt` carries the minimum line Overture's documentation names and
  declares itself not to be a copy. **Is shipping a self-declared partial notice better or worse
  than shipping none?** Argue it rather than assuming my answer.
* Is CDLA-Permissive-2.0 §2.1 satisfied by a copy of the text in `LICENSES/`, given that the data
  it accompanies is a JSON file in a sibling directory and nothing in the JSON points at it?
* The allowlist in `check_table_is_publishable` refuses unknown fields and unknown licences. Can
  you get a forbidden field — a phone, a website, an upstream provider id — into a published
  bundle anyway? Look at every path into the table, not only `place_record`.
* I withdrew the claim that separate files keep the permissive names out of the share-alike
  database. Did I over-withdraw? Is there any version of the separation argument that *does* hold,
  and have I now written something that is wrong in the other direction?

### C. The harness, and whether it is still checking the artifact

The new check `the shipped published bundle loads the way the page loads it` loads the manifest and
side table with `JSON.parse` and inits the real worker with the real planes. It is the check that
catches the pass 49 blocker.

* It reads files with `fs`, not `fetch`. What does `app.js` do that this does not? Read
  `app.js` around lines 148–240 and name every failure mode of the real load path that this check
  cannot see. `app.js` also validates the manifest itself before the worker does.
* Does it assert anything that would still hold if the destination plane were empty, the table
  were a stub, or the bundle were stale relative to the generators?
* The per-case comparison now checks `nodeIndex`, every place name, and the whole record set
  against the group's own `dest_tables`. Is the record-set comparison circular — does it compare
  the worker's output against the same object the worker was handed, such that a worker that
  returned its input by reference would pass trivially? If so, what is the non-circular version?
* Seven mutations were added from your findings and all 37 are caught. Find a destination defect
  that still survives all 75 checks. Pass 49 found four; I expect there are more.

### D. `state.computed`

`verdict` is allocated zero-filled and 0 means INCLUDED, so the old guard answered `included: true`
before any compute.

* `handleDestinationAt` is fixed. **What else reads `state.verdict`, `state.lastEnabled` or
  `state.lastSeq` and would answer from the zero-filled plane?** Check `handleVerdicts` and every
  other message type. I fixed the one you found; I want to know whether I fixed the class.
* Is `notComputed: true` with `included: null` the right shape, or does an `included` that can be
  `true`, `false` or `null` create a tri-state no consumer will handle correctly? There is no
  consumer yet — the card is unbuilt — so this is a design question, and say if you think the
  answer is to refuse the query instead.
* Reinitialisation resets `computed`, `lastSeq` and `lastEnabled`. Is anything else stale across
  an init?

### E. The required byte order

The guard now requires `destination_plane_byte_order === 'little'` wherever a plane is present,
and is skipped where no plane is. Is "wherever a plane is present" the right condition? Can you
construct a payload that carries destination ordinals the worker reads without the field being
required?

### F. The corrected cost report

The destination now costs 59,278 deflated bytes, 20.6% of a 287,309-byte bundle, with the side
table included. Your run-length index measurement reproduced exactly: 28,989 runs, 173,934 bytes,
0 mismatches over 330,502 cells.

* Is 20.6% computed on the right denominator this time? The planes are deflated individually and
  summed; a real HTTP response would compress them separately too, but the side table is JSON and
  the planes are binary. Say if summing per-file deflated sizes is the wrong model for "what
  ships".
* `on_the_source_grid` and `on_the_published_grid` are now reported separately. Is anything still
  comparing across them?
* The decision text now rests on **simplicity**, not cost or necessity. Is that an honest
  argument, or have I just moved an unfalsifiable claim into a word that sounds smaller?

### G. The guards I repaired, and the ones I wrote this time

* `byteswap_control.mjs` now requires its mutation to have applied, a completely correct baseline,
  and ordinals exactly `1 ↔ 256`. Defeat it again.
* `executable_lines` in `tests/test_wire.py` strips line comments and line-leading block comments.
  My first attempt deleted 200 lines of `app.js`. Find a JavaScript construct that defeats the
  current one — a declaration it treats as commented, or a comment it treats as code.
* `test_every_json_artifact_is_strict_json` scans three directory roots. What JSON artifact that a
  non-Python consumer loads is **outside** those roots?
* `destination_tie_control` and the provenance controls: can any of them pass on the wrong cause,
  the way `byteswap_control` did?

### H. The figures and the records

* `docs/engineering-notes/project-phase1-s3-destination-identity.md` has been substantially
  rewritten with the withdrawals. Is anything in it still wrong, or now wrong in a new way?
* Ledger instances 29–33 in `feedback-verify-the-shape-of-the-risk.md`. Are any of them
  mis-generalised — a shape stated more broadly than the evidence supports?
* 1,442 tests / 1,418 passed / 24 skipped, 75 conformance checks, 37 of 37 mutations. Verify the
  conformance and mutation counts in `node_repl`; say if either disagrees.

## Output

For each finding: severity, the exact file and line, a **runnable reproducer** (JavaScript you
executed, or Python clearly marked unexecuted), and what it costs — a number that moves, or a
claim that must be withdrawn. Say which claims you checked and could not break.

**Start with section A.** If `verify_provenance` is unsound, or is sound but has never been
exercised against the case it exists for, say so first and in those words.
