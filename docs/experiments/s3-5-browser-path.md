# S3.5 — the browser path, and the encoding freeze it needed

**2026-11-13, revised the same day after Codex pass 43.** Step 6 of the S3 execution plan's §0.
`v2/locfinder/wire.py`, `v2/scripts/{export_published_layers,make_wire_vectors,measure_export_regrid}.py`,
`v2/spikes/g3-render/{worker.js, app.js, worker_conformance.mjs, mutate_worker.mjs}`,
`v2/tests/{test_wire,test_browser_conformance,test_export_published}.py`, review in
`docs/research/44-codex-review-pass43-counterexamples/`.

**Pass 43 found the page could not boot and the conformance harness passed materially wrong
decoders.** Both are fixed, and the corrections are marked below where the wrong claims stood.

## What was wrong, measured rather than described

§0 recorded the defect as "the export collapses UNKNOWN into EXCLUDED". Reading the code, it runs
in two directions at once:

* the **mask** the worker ships sets every missing cell to 0, which is what EXCLUDED looks like —
  §0's point, and correct;
* the **rendering** does the opposite, painting every missing cell as unknown, including the ones
  the pipeline can prove are over the threshold;
* and the loop `break`s on the first missing value, so a **known failure in a later layer is never
  looked at** — "one known failure beats any number of unknowns" exactly inverted.

On the published Triangle walk layer, 330,502 cells: 256,752 `OK`, 57,541 `OFF_NETWORK`, 16,209
`BEYOND_HORIZON`. At ten minutes **18,648 of the missing cells are known failures** — every
`BEYOND_HORIZON` cell plus 2,439 `OFF_NETWORK` cells whose lower bound exceeds ten minutes — and
one `NODATA` code cannot say so. Step 5's census put the same defect at about **10,000 of 512,633
structures** at every threshold.

None of it is a rounding error. `encode_minutes` already rounds up, so a finite cell's encoded
verdict equalled its float verdict.

## The format: `published-v2`

Two uint8 planes per layer.

| plane | meaning |
|---|---|
| `value` | travel time in whole minutes where `status` is `OK`; a **lower bound** on it where `status` is `OFF_NETWORK`, `BEYOND_HORIZON` or `NO_PATH`; `255` otherwise |
| `status` | `0 OK`, `1 OFF_NETWORK`, `2 BEYOND_HORIZON`, `3 NO_PATH`, `4 LAYER_UNKNOWN`, `5 OUTSIDE`, `6 UNKNOWN_CAUSE` |

The wire codes are assigned in `wire.py` and are **not** `status.Reason`'s integers, because the
layer contract says the enum "must never be written into a raster". `OUTSIDE` is a pixel the export
covers and the source did not. `UNKNOWN_CAUSE` is how a v1 artifact lifts into this format without
inventing provenance: missing, cause not recorded, never a known failure.

> **Qualified after pass 43.** "The lift moves no verdict" is true of the **mask** — an unknown
> cell stays out of the included set, including when another criterion fails. It is **not** true of
> the rendering, which can now show EXCLUDED where v1 showed the unknown hatch. That change comes
> from the precedence fix, which is deliberate, not from the lift.

**Rounding up is what makes the bound exact rather than approximate.** For an integer-minute
threshold, `ceil(x/60) > T` is equivalent to `x > 60T`, which is `evaluate`'s own comparison.

> **Corrected (pass 43 F7).** That equivalence holds **only** for integer `T`, and both decoders
> truncated a fractional one — `int()` in Python, `| 0` in JavaScript. At 10.5 minutes a
> 610-second `OK` cell decoded as a failure where the rule passes it, and a non-strict bound became
> an exclusion. Both now **refuse** a fractional threshold. The slider cannot produce one; a caller
> outside it could.

**Capping is sound in one direction only.** A bound above 254 saturates, which can only turn a
known failure into an unknown. An `OK` minute above 254 would do the reverse, so the encoder
refuses rather than capping. Legacy minute values 251–254 stay ordinary minutes; the sentinels live
in the status plane, which is what "version the format, do not reinterpret the codes" means.

**The value plane is redundant for `BEYOND_HORIZON`, and that makes it a checksum.**
`Surface.validate` forces such a cell's bound to equal the horizon exactly, so its byte is
`ceil(horizon_s/60)`, while the decoder compares against the manifest's horizon and never against
the stored bound. Pass 43 noted a wrong manifest horizon could therefore turn an unknown into an
exclusion with nothing to catch it. `worker.js` now refuses at init when the two disagree.

## It costs 18%, not 9%

| layer | v2 deflated | v1 deflated | increase |
|---|---|---|---|
| `own_triangle_grocery_walk` | 202,380 | 171,260 | **+18.2%, 31,120 bytes** |
| 200 m candidate | 101,696 | 81,645 | +24.6% |

> **Corrected (pass 43 F5).** The first version compared v2's two planes against **v2's own value
> plane**, which carries a lower bound at every missing cell. v1 stored `NODATA` there, and a
> constant compresses far better than a bound, so the baseline was too large and the overhead too
> small. The claim "the entire three-outcome algebra costs 17 KB" is withdrawn; it costs 31 KB.
> The 200 m candidate also has the **same raw byte count** as the 100 m layer, because both export
> to the same output raster — the quarter-size saving is in source cells, not in transfer.

## The decoder, and the part a Python test cannot reach

`wire.outcome_planes` and `worker.js`'s `outcomeFor` are the same function in two languages.

* `tests/test_wire.py` proves the **Python** one equals `status.evaluate` **cell for cell** on all
  330,502 published cells, at ten thresholds from 1 to 121 minutes.
* `worker_conformance.mjs` proves the **JavaScript** one equals Python, driving the real worker
  through its real message protocol with `self` shimmed.
* `tests/test_browser_conformance.py` runs that under pytest.

> **Corrected (pass 43 F2), and this is the serious one.** The harness reconstructed verdicts from
> the RGBA buffer, where INCLUDED is readable from the mask but EXCLUDED and UNKNOWN are
> distinguishable **only where the hatch stripe falls**. So three quarters of the cells were
> compared against nothing, the real-layer window — which has no inline expected array — was
> compared against **nothing at all**, and the digest was computed and then checked only for being
> a 32-character string. Two wrong decoders passed all 37 checks: one returning UNKNOWN for
> `NO_PATH`, and one **rotating the entire raster by 10,007 cells**, which moves 13,695 verdicts.
>
> The worker now reports its three-way verdict plane (`{type:'verdicts'}`), and the harness
> compares every cell, cross-checks the mask against the plane, cross-checks the counts against the
> plane, and compares the same digest over the same bytes. A case that asserts nothing about the
> arrangement of its verdicts now fails rather than passing.

**And the harness is itself checked now.** `mutate_worker.mjs` applies nine known-wrong decoders —
including both of pass 43's — and requires each to be caught; **9 of 9 are**. A mutation whose edit
matches nothing is reported `INERT` rather than banked as a catch, which immediately caught three
of my own anchors failing against a CRLF working tree.

The decoder refuses rather than guesses: an unknown encoding, a layer with no `horizon_s`, a
horizon that disagrees with the planes, a plane of the wrong size, a fractional threshold, and an
undefined status code are each rejected with a message naming the problem.

## The export ships a third grid, and it costs as much again

> **New, from pass 43 F3.** S3.1 compared two **UTM** grids and chose 100 m. The browser receives
> neither: it receives a 514 × 643 **WGS84** raster, reprojected with nearest. Nearest preserves
> every source code — the exported planes reproduce byte for byte — but it does **not** preserve
> each address's cell assignment, because the two tilings are not aligned.

`scripts/measure_export_regrid.py`, over the 500,451 structures inside the exported bounds:

| *T* | structures whose verdict moves between the source grid and the shipped raster |
|---|---|
| 10 min | 10,759 (2.15%) |
| 15 min | **12,098 (2.42%)** |
| 25 min | 7,926 (1.58%) |
| 45 min | 3,253 (0.65%) |

That is **about as large as the cell-centre error S3.1 measured** (2.52% at 15 minutes), so the
shipped answer carries roughly twice the discretisation error the grid decision reported. It is not
a reason to prefer the 200 m grid — the same re-tiling applies to both — but the grid comparison
describes the source layers, not the bytes a browser decodes, and that distinction was missing.

The exported bounds also **omit 12,182 structures** that have a published answer in the source
grid: the UTM grid is the bounding box of the lon/lat box's projected corners and is strictly
larger than the box itself.

## The exporter

`scripts/export_published_layers.py` reads the surface triple `build_layer_surface` produced and
writes both planes, reprojected with **nearest for both**: a status code is a name, and a minute is
a decision input.

> **Corrected (pass 43 F4).** It exported the rejected 200 m candidate into the product manifest,
> and every manifest entry starts enabled in the page — so the default answer was the
> **intersection of two versions of the same criterion**, removing 4,022 passing pixels at the
> default 20-minute threshold. The candidate now exports only under `--candidates`.
>
> **Corrected (pass 43 F8).** The shape guard existed only on the fallback branch. A transposed
> 83,076-cell triple passed the explicit branch and would have exported under a transform that
> moves every cell.

Two of §0's exporter defects are **retired rather than fixed**. `spikes/g3-render/export_layers.py`
discovered layers by `<engine>_<category>_<mode>` and so omitted `own_triangle_grocery_walk.tif`,
and targeted the 401 × 550 Phase 0 slice — together meaning the browser had never rendered the
layer the product publishes. It cannot be fixed into the product path: it reads **minute
GeoTIFFs**, and the reason and bound were discarded before those were written. It keeps the G1
engine comparison it was built for.

## What is not done, and what is weaker than it looks

* **Phone decode latency.** The sizes above are deflated byte counts. Decode time on a handset
  needs a handset, and that is the owner's.
* **The per-criterion card.** The worker returns three counts and a verdict plane, and `app.js`
  carries them, but the card that tells a household *which* criterion was unknown is not built.
* **With no criteria enabled the map turns entirely blue.** `status.combine` says a search with no
  constraints excludes nothing, and the renderer now matches it over all 330,502 cells. Pass 43
  recommends a transparent inactive state with an empty-search message while keeping the universal
  INCLUDED result for algebraic consumers. **Not done** — it is a UI decision, not an algebra one.
* **`OUTSIDE` has no live producer.** The export's bounds sit inside the source's projected
  footprint, so zero pixels are uncovered. The code is exercised by hand-built vectors only.
* **The conformance window is the first that matched, not a representative sample.** It is the
  200 × 200 block at `(0, 0)`, chosen because it contains all three produced codes — 31,312 `OK`,
  7,921 `OFF_NETWORK`, 767 `BEYOND_HORIZON`. The whole-layer agreement is proven in Python; what
  the window establishes is that two implementations agree, not that the layer is typical.
* **Recomputation eligibility.** The format carries what `needs_recomputation` needs; the UI does
  not offer it.
