# The layer contract

**Phase 1 stage S0.** What a published cell value means, why it can be missing, how criteria
combine into a region, and what identifies a surface.

**Status:** implemented and tested — `v2/locfinder/status.py`, `v2/locfinder/identity.py`,
`v2/locfinder/profile.py`, `v2/locfinder/traveltime/layer.py`, `v2/tests/test_status.py`,
`v2/tests/test_identity.py`. **184 tests pass** (118 before this stage). Revised after Codex
adversarial pass 8, which found three High and four Medium defects — including two false claims of
mine, corrected in §3 and §2; see the absorption record in §10.

**No encoding is chosen here.** That is deliberate and is the correction Codex pass 7 forced on
revision 1 of the Phase 1 plan: *what statuses exist* is decided by the algebra below, *what
durations must be representable* by the transit semantics in §4, and *which resolution* by the S3
measurement. Encoding is the last step of a semantic design. The integer values of the enums in
`status.py` are in-memory array codes for vectorised evaluation over 330,502 cells; they are **not
a wire format** and must never be written into a raster. S3.5 assigns wire codes, with the format
versioned, because minute values 251-254 are real answers in artifacts already on disk.

---

## 1. Why provenance, and not just `inf`

A cell with no time can have it for at least four different reasons, and the pipeline currently
discards which one at the first opportunity: `layer.py:38-41` and `snap.py` produce a single `inf`,
and `grid.encode_minutes` collapses that into a single `NODATA`.

That matters because the honest statuses differ in strength. "There is no road within 200 m of this
cell" and "we did not search this far" are different claims, and only one of them is a *known*
disqualification. Telling a household a cell is unreachable when it is merely past our search
horizon is telling them something false.

### Every cause, and whether this pipeline can produce it

| cause | arises at | producible | published as |
|---|---|---|---|
| no graph edge within `max_access_m` | `snap.py` access mask | **yes** — `access_m` is in hand | `OFF_NETWORK` |
| a route exists but exceeds the built horizon | `snap.py` cutoff | **yes** | `BEYOND_HORIZON` |
| no route exists in the built network | `arrival.py` | **only if the search was unbounded** | `NO_PATH`, else weakened |
| the category selected no destination | `arrival.py:28-29` | yes, build time, layer-wide | `NO_DESTINATIONS` |
| destinations exist, none snapped to a node | `g1_own_graph_layer.py:86` | yes, build time, layer-wide | `NO_ROUTABLE_DESTINATIONS` |
| a required source was missing or stale | S4.3 | yes, build time, layer-wide | `SOURCE_MISSING` |
| the cell's local network was dropped by component pruning | `components.py:77` | **no, not from the layer** | — |
| the true route left the routing bbox and was truncated | `metros.py` buffer | **no, not per cell** | — |

The last two get no status, because allocating a code for a distinction the pipeline cannot make
would publish a fiction (Codex pass-7 C4).

- **Component pruning** is knowable at build time — `largest_component` reports what it dropped —
  but not afterwards, because the dropped nodes are gone. It becomes a build-time diagnostic in
  S2.4, alongside building-weighted coverage. Measured through the production preparation path, the
  widened Triangle walk graph has **3,046 components** and drops **13,608 nodes (2.5%)**, so this
  is not a hypothetical. §9 explains why this, and not `NO_PATH`, is how a disconnected
  neighbourhood actually goes missing.
- **Extract truncation** would need the arrival path's node sequence, which the pipeline discards
  after reconstruction. S3 owns the build-time diagnostic. Note that truncation usually *inflates*
  a time rather than removing it, so it would not be visible as a missing value anyway.

`status.py`'s enum members are asserted to be exactly this producible set
(`test_only_statuses_the_pipeline_can_produce_exist`), so adding a member means committing to a
producer.

"Producible" here means the code emits it, which is weaker than "the shipped build contains it".
§9 measures the difference on the real Triangle walk layer, and finds that **`NO_PATH` is
unreachable in every configuration we currently ship.**

### `NO_PATH` is engine-dependent, and that is the S0.1 rule

Proving no route exists requires an exhaustive search. Checked against the code, not assumed:

| mode | engine | search | can prove `NO_PATH` |
|---|---|---|---|
| walk | our own graph | **unbounded** on cost — `layer.py:38-39` pass no `cutoff_s`; the cutoff is applied to the final per-cell total | **yes** |
| bike, drive | Valhalla `/expansion` | bounded by the requested contour — `g1_valhalla_layer.py:72`, `g1_expansion_primitive.py:46` | no |
| transit | MOTIS `one-to-all` | bounded by `maxTravelTime` | no |

Where the engine cannot prove it, `honest_reason` publishes the **weaker** status,
`BEYOND_HORIZON` — "not reached within the built horizon". The same cell on the same graph is
`NO_PATH` for the own-graph engine and `BEYOND_HORIZON` for a bounded one
(`test_the_same_cell_is_only_beyond_the_horizon_for_a_bounded_engine`): nothing about the world
changed, only which engine is entitled to claim exhaustiveness.

**But the engine is not the whole story, and the first version of this contract got that wrong.**
Codex pass-8 H1: `arrival_seconds` accepts a `cutoff_s` and scipy's `limit` prunes the search, so a
*bounded call on our own graph* returns `inf` for nodes that are merely distant. Reading
exhaustiveness off the engine name labelled a node 210 s away as having no route at all —
reproduced independently. Two fixes:

- `node_reasons` now takes **`search_bounded` as a required keyword**, with no default, because
  exhaustiveness is a property of the invocation.
- `layer.py`'s single-weight branch no longer passes a node cutoff. That changes no output — a node
  past the horizon cannot yield a cell inside it, since the access leg only adds time — verified
  over 25 graphs × 400 cells at a deliberately tight horizon with zero cells changed. The cell
  stage still applies the cutoff, after the access leg, which is where it belongs.

A consequence worth stating: **the horizon is a per-layer field, not a constant.** The own-graph
layers were built to 120 minutes and the Valhalla reference layers to 60
(`g1_valhalla_layer.py:40`). Comparing them without carrying each horizon reads one engine's
missing data as the other's disagreement.

A further consequence for a bounded engine: it must be queried at **exactly** the layer's horizon,
or there are two horizons and "past the horizon" means two things.

---

## 2. The algebra

Per criterion a cell is `PASS`, `FAIL` or `UNKNOWN`. Per cell those combine to `INCLUDED`,
`EXCLUDED` or `UNKNOWN`.

### Lower bounds turn some missing values into known failures

This is what makes the table non-trivial. A missing value is not automatically unknown: each non-OK
reason carries a **sound lower bound** on the time our model would have reported, and a lower bound
above the threshold is a known failure with no route computed at all.

| reason | lower bound | why it is sound |
|---|---|---|
| `OFF_NETWORK` | `access_m / max_speed_mps(mode)` | every destination is on the network, so the journey covers at least the straight-line distance to the nearest edge, at no more than the model's fastest speed |
| `BEYOND_HORIZON` | the horizon `H`, **strictly** (`t > H`) | the cutoff was applied and the value exceeded it |
| `NO_PATH` | `+inf` | no finite time at any budget |
| layer-wide | `0` | nothing is known |

The access *speed* is deliberately not used as the bound — but not for the reason first given
here, which Codex pass-8 L2 showed was wrong. The original claim was that an access-speed bound
would be unsound. It is not: the cell total is `network + access_m / access_speed` with
`network >= 0`, so the charged access time is itself a valid and **tighter** lower bound on this
model's answer.

The weaker `max_speed_mps` bound is kept as a **judgement, not a correctness requirement**: the
off-network access leg is a straight line over unmapped ground, and a tighter bound would use that
fiction to *exclude* households rather than call them unknown. S2.4's building-weighted coverage is
what should decide whether to tighten it, because that is what will say who lives in those cells.

These are bounds on **our model's** answer, not on reality. They say whether this pipeline could
possibly have returned a passing value, which is the right question for a published region.

### Per-criterion outcome

| reason | outcome | decided by |
|---|---|---|
| `OK`, `seconds <= threshold` | `PASS` — the threshold is inclusive | the reported time |
| `OK`, `seconds > threshold` | `FAIL` | the reported time |
| `NO_PATH` | `FAIL` at every threshold | the reason alone |
| `BEYOND_HORIZON`, `threshold <= H` | `FAIL` — the time is provably greater | `horizon_s` |
| `BEYOND_HORIZON`, `threshold > H` | `UNKNOWN`, and **answerable**: see below | `horizon_s` |
| `OFF_NETWORK`, `access bound > threshold` | `FAIL` | `min_possible_s` |
| `OFF_NETWORK`, otherwise | `UNKNOWN` | `min_possible_s` |
| any layer-wide reason | `UNKNOWN` at every threshold | the reason alone |

Every reason is decided by **exactly one** rule, which is the fix for two pass-8 findings. M2: the
`BEYOND_HORIZON` row reads `horizon_s`, never the stored bound, so an overstated bound cannot
change an eligibility answer and cannot disagree with `needs_recomputation` (the bound is also now
required to equal the horizon *exactly* — `np.allclose` admitted about 0.07 s of error at
H = 7200 s). M1 and L1: layer-wide reasons and `NO_PATH` are decided by the reason alone, so
neither a malformed bound nor an infinite threshold can flip them — `inf > inf` is false, which
used to make `NO_PATH` unknown at an infinite threshold.

The `BEYOND_HORIZON` row at `threshold == H` is `FAIL`, not `UNKNOWN`: the bound is strict, so the
time exceeds `H`, which equals the threshold. That one boundary is why the bounds cannot all be
compared with a single non-strict test.

A layer-wide failure is `UNKNOWN` everywhere and may **not** exclude a single cell. A metro with no
groceries is a data defect, not a fact about the metro; S4.4 blocks publication instead. `validate`
now requires such a surface to carry **one** reason uniformly with a lower bound of exactly zero:
checking only that every cell held *some* layer-wide reason let a mixed array through, and a
positive bound on one of them became an exclusion.

### Per-cell verdict

**One known failure beats any number of unknowns** (Codex pass-7 C4). A cell definitely 50 minutes
from work does not become a maybe because we are unsure about its walk to a grocery.

| criteria | verdict |
|---|---|
| any `FAIL` | `EXCLUDED` |
| no `FAIL`, any `UNKNOWN` | `UNKNOWN` |
| all `PASS` | `INCLUDED` |
| none at all | `INCLUDED` — a search with no constraints excludes nothing |

"Why is this out?" reports **every** failing criterion, never the first one found (`status.failing`,
for S6.2).

### A threshold past the horizon is answerable, and must be offered

`needs_recomputation` marks cells whose outcome is unknown *only* because the threshold exceeds the
built horizon. These can be answered by searching further, unlike an off-network cell, so the
product offers a fresh computation rather than reporting "unknown".

Raising a threshold above the horizon does **not** invalidate the cells that already passed — only
this fringe. The surface stays valid up to `H` whatever the user asks for.

---

## 3. Per-anchor semantics

A **category** criterion means "any qualifying destination": `∃ d ∈ category : t(cell → d) ≤ T`.

**The shipped category surface does not answer that exactly, and the first version of this contract
claimed it did.** Codex pass-8 H2, reproduced independently:
`arrival_seconds_two_weight` runs one multi-source search that picks the destination nearest by
**cost** and then reports *that* path's time. Access penalties change which destination wins, and
that does not commute with taking a minimum over times.

A fixture with a 28 m destination behind a penalised private residential edge and a 140 m
destination on an open road:

| | time | cost |
|---|---|---|
| destination A alone | **20 s** | 140 s |
| destination B alone | 100 s | 100 s |
| the category surface | **100 s** | — |

A "within 30 s of a grocery" criterion should pass — destination A qualifies — and the surface
fails it. So the surface is an **upper bound** on `min_d t(cell → d)`, not that minimum, and
category criteria evaluated on it can produce **false exclusions, never false inclusions**.

The aggregation is renamed accordingly: `cost_selected_category`, because the old name
`min_over_category` asserted something false. A second aggregation, `time_min_category`, is the
other side of a bracket, and both are one Dijkstra:

    time_min  ≤  the best time over a legal route  ≤  cost_selected

Neither end is the honest answer. `time_min` ignores the access policy entirely and would route
freely down private roads — the leak the two-weight model exists to prevent; `cost_selected`
respects it but over-reports. The honest quantity, "the best time over a route the public may
actually use", needs a different algorithm (restricted edges permitted as a final approach but not
as a through-route), which is a **design decision, not a bug fix**, because it changes the access
policy the owner already approved. §9 measures the gap on real data so that decision has a number
attached.

An anchor criterion is unaffected: with one destination there is nothing to choose between.

An **anchor** criterion means "this specific place": `t(cell → anchor) ≤ T`. It needs its own
surface.

The Phase 1 goal says "arrive by 08:45 at *each* of two workplaces". That is **two anchor criteria
combined with AND**. A single surface holding `min(t_A, t_B)` asks whether *either* workplace is
close enough, which is a different question, and a combined minimum cannot be decomposed back into
the pair. Where both thresholds are equal, `max(t_A, t_B) ≤ T` is equivalent and a max surface
would serve; different thresholds require the two surfaces.

`status.evaluate` **refuses** the substitution rather than trusting the caller: a surface carries
its aggregation and a criterion carries its kind, and a mismatch raises. Mode and target mismatches
raise too. The guard checks a declared label, so it cannot detect a surface built one way and
labelled another — that is what `build_layer_surface` is for.

S6.1 adds the consequence: individually acceptable per-criterion error distributions do not
establish the accuracy of their intersection, and p90s do not compose by arithmetic, so the
**combined region** is audited directly.

---

## 4. Transit query identity

A transit surface is not identified by `(mode, category)`. `locfinder/identity.py` fixes the fields
now, before the manifest (S4.2) and the cache (S5.3) are built, because the freshness gate cannot
be written against an unspecified "requested service date" (Codex pass-7 H8).

| field | decision | why |
|---|---|---|
| timezone | `America/New_York` | all seven adopted feeds declare it (`feeds_report.json`) |
| service date | a local calendar **date**; reference **2026-11-10**, a Tuesday | already used by `transit_compare.py:45`; an instant is not a service day |
| deadline | a local **wall-clock** time, e.g. 08:45 | what a household means, and what GTFS `stop_times` are expressed in |
| window | `window_s`, the longest journey searched, **and the surface's horizon** — enforced equal, and required finite | MOTIS takes it as `maxTravelTime`; two numbers would mean two definitions of "past the horizon" (pass-8 M3), and `window_s <= 0` is false for NaN so NaN and `+inf` both used to pass |
| duration | **total journey time**, cell to arrival: access walk, wait, ride, transfers, egress walk | the honest "when must I leave"; see below |
| prior service day | **required** | an overnight trip with a `stop_time` past `24:00:00` can serve an 08:45 arrival |
| DST | a deadline that is ambiguous or nonexistent on its service date is **refused** | a local wall-clock time is not always a unique instant |

**Waiting is inside the duration.** A cell whose only bus leaves 40 minutes before the deadline
reads over 40 minutes even if the ride is 10. The alternative presentation — the latest feasible
departure time — is recoverable exactly as `deadline − duration`, so storing duration loses
nothing and the UI can show either.

**A wall-clock deadline is not a fixed UTC offset.** 08:45 local is 12:45 UTC in July and 13:45 UTC
in December (`test_an_eight_am_deadline_shifts_with_dst_rather_than_staying_put`). A surface built
in one season and reused in the other would route to the wrong instant, which is exactly what the
service date in the cache key prevents.

**The DST rule exists for deadlines we do not yet use.** An 08:45 deadline is safe on every date,
including both 2026-11-01 and 2027-03-14. But the code accepts any deadline, so the rule is
enforced rather than left to the next person. Both failure modes make the two PEP 495 folds
disagree about the offset, so they are distinguished by a round trip through UTC: a nonexistent
local time comes back changed, an ambiguous one comes back unchanged with two valid offsets.

### Deferred to S4.3, and named so it cannot be mistaken for done

Validating a service date against the **feed contents** — the calendar, `calendar_dates`
exceptions, and a non-zero active-trip assertion — is the freshness gate, which is unimplemented.
The fixtures are already in hand:

- **Duke Transit**: `calendar.txt` runs 2025-05-05 to **2025-08-10**. Stale by more than a year.
- **Chapel Hill Transit**: 2026-10-09 to **2099-12-31**. A distant end date proves nothing; the
  active-trip assertion is what matters.
- **NC State**: carries both an expired service (ended 2026-03-07) and a blanket one running to
  2027-12-31 on all seven days. A feed can be simultaneously stale and valid.
- `feeds_report.json` lists **eight entries for seven agencies** — Duke appears twice. The report
  that documents the adopted configuration double-counts a feed, which is worth fixing before it is
  cited as evidence of coverage.

S4.3 must also **decide the policy explicitly**: the adopted seven-feed configuration *includes*
the stale Duke feed, so the choice is between blocking all transit and excluding Duke with a
declared partial-coverage statement. Revision 1 of the plan implied both.

---

## 5. Surface identity, all modes

`SurfaceKey` carries metro, mode, engine, target, aggregation, horizon, grid version, source
release, profile version, code version, the two access bounds, direction, the anchor and its
rounding, and the transit query. Its `digest()` is a stable 16-hex cache key — stable across
processes, because `hash()` is salted per process and would silently invalidate a disk cache on
restart.

Four details that are easy to get wrong:

- **`direction` is always `"arrival"`** and is carried explicitly, so a future departure-time
  surface cannot silently reuse an arrival cache. Constructing anything else raises.
- **A coordinate alone is not an identity** (Codex pass-7 H6). Rounding an anchor can move it
  across a divided road or a barrier, so the rounding applied is part of the key. S5.3 must bound
  how far it can move a point.
- **`profile_version` and `grid_version` are derived, not typed, and that is now *enforced*.** A
  hand-written version string does not change when the thing it describes changes, and the failure
  mode is a cache that confidently serves an answer built under different rules.
  `profile.profile_version()` digests the actual model constants — the speed tables, the access
  classification, the restricted penalties, the snapping epsilon, **the expansion adapter's
  node-merge quantisation and minimum-traversal floor**, the symmetrise and component-pruning
  policies — so changing any of them changes the key. Codex pass-8 H3 executed the counterexample:
  changing `expansion._NODE_SNAP_M`, which decides which endpoints merge into one node and
  therefore moves reported drive and bike times, changed neither the profile nor the key. It does
  now. And `SurfaceKey` **refuses a version that does not look derived**, because convention is not
  enforcement: a version string that cannot change is worse than none, since it looks like
  provenance. `profile.grid_version()` digests the grid's own origin, cell size and extent,
  which matters because the 100 m and 200 m Triangle grids are **not** nested:

  | grid | origin | shape | version |
  |---|---|---|---|
  | 100 m | 661900 / 4003500 | 643 × 514 | `grid-v0+7ab61db26b3cc98e` |
  | 200 m | 661800 / 4003600 | 322 × 258 | `grid-v0+a1259d05712a3ce2` |

  The current profile is `speeds-v0+9893b1b0168ff19a`. These are S4.1's "keyed by input hashes"
  applied to the parameters; the data — the OSM extract and the Overture release — stays in its own
  key fields.
- **`max_access_m` and `poi_snap_max_m` are explicit fields**, not folded into the profile digest.
  The first decides which cells are `OFF_NETWORK`, the second which destinations exist at all. They
  are per-build choices a reader should be able to see in the manifest, not hashed away.

### Still unrepresented, named so it is not mistaken for complete

Codex pass-8 H3's deeper point stands and is an **S4.1 obligation**, not something S0 can close:
`source_release` and `code_version` are caller-supplied strings, and no factory binds a key to the
actual build inputs. Until S4.1's single build specification exists, these change a surface's
values without necessarily changing its identity:

| gap | owner |
|---|---|
| the category selector definition — `target` is a bare name, and S6.3 has yet to publish versioned, validated category definitions, so two surfaces built from different selector revisions for "grocery" would collide | S6.3 defines the field's contents, S4.1 binds it |
| the OSM extract, the Overture release contents, the GTFS feed set and contents, the Valhalla tiles — one free-form `source_release` *can* hold a bundle hash but nothing requires separate source and content identities | S4.1 |
| the Valhalla version, its costing options and request settings — `spikes/_common.py:52`'s controlled-costing options change answers and are not in the own-graph profile digest | S4.1 |
| transit access, egress and transfer settings, the direct-walk policy, and the effective server cap as opposed to the requested one | S6.4 |
| the routing extract's extent, as distinct from the grid's | S4.1 |

`code_version` can legitimately subsume code-defined rules and a source-bundle digest can subsume
data — but only once something computes them rather than accepting a string.

---

## 6. Engines, stated once

| mode | engine | note |
|---|---|---|
| walk | our own graph | transposed-graph multi-source Dijkstra, unbounded on cost; cutoff applied per cell |
| bike | Valhalla `/expansion` | `action=isochrone`, bounded by the requested contour |
| drive | Valhalla `/expansion` | as above |
| transit | MOTIS `one-to-all` | `arriveBy`, bounded by the requested maximum travel time |

`ENGINE_BY_MODE` in `status.py` is the single source. Revision 1 of the Phase 1 plan named only
Valhalla and MOTIS in its architecture paragraph while other sections relied on the own-graph walk
path.

Caveats carried forward from Phase 0, not resolved here: Valhalla's walk speed was set equal to
ours, so our walk model was never independently tested; the drive spot check was drive-only, so
Valhalla's bike profile remains unvalidated; and the expansion adapter's real-payload behaviour is
S1, not yet measured.

---

## 7. The snap refactor is behaviour-preserving, measured

`cell_seconds_from_arrival`'s branch arithmetic moved into a shared `_snap_network` so that the
provenance path cannot drift from the seconds path. That refactor was verified against the
pre-refactor implementation taken directly from `git show HEAD:v2/locfinder/traveltime/snap.py`:
40 random graphs with one-ways, parallel edges and access penalties, 340 probe points each
(uniform, exact nodes, and edge midpoints), across all four combinations of `node_cost` present or
absent and `cutoff_s` present or absent.

**54,400 paired values, bit-identical, maximum absolute difference 0.0.**

## 8. One defect found while writing this

`cell_arrival_with_provenance`'s first version labelled every unreachable cell `BEYOND_HORIZON`.
The cutoff test is `total > horizon_s`, and an infinite network time satisfies it, so the cutoff
branch overwrote `NO_PATH` on the island fixture. "A route was found but it is too long" requires a
route; the test is now `isfinite(network) & (total > horizon_s)`.

It is worth recording because it is the same shape as the bug Codex found in `expansion.py`: an
expression that is true for the intended case and also true for a case nobody pictured. The test
that caught it asserts that all four per-cell reasons are produced by the real pipeline on one
graph in one call — not that the enum has four members.

---

## 9. What the shipped layer actually contains, measured

Unit tests prove the code can emit all four per-cell statuses. That is not the same as the
production build emitting them, and the `expansion.py` lesson was exactly that gap. So the shipped
Triangle walk layer was rebuilt through `layer.build_layer_surface`
(`v2/spikes/s0_status_on_real_layer.py`, output `v2/data/s0_status_triangle_grocery_walk.json`) —
the provenance-returning builder itself, not just the snapping function underneath it.

**The 23.24% of cells with no walk time are decomposed for the first time:**

| status | cells | share of grid |
|---|---|---|
| `OK` | 253,679 | 76.7557% |
| `OFF_NETWORK` | 57,541 | **17.4102%** |
| `BEYOND_HORIZON` | 19,282 | **5.8342%** |
| `NO_PATH` | 0 | 0% |

57,541 + 19,282 = 76,823 = **23.2443%**, which is exactly the nodata share measured on the
committed artifact. So three cells in four of the missing region have no road within 200 m, and one
in four has a road but is more than 120 minutes' walk from a grocery. Previously this was one
undifferentiated blob, and S2.4's "ten largest contiguous no-data regions with a named cause" now
has a cause per cell to start from.

`Surface.validate()` passes on all 330,502 cells. Against the committed
`own_triangle_grocery_walk.npy`: finiteness **identical**, maximum absolute difference **0.000244
s** — the artifact is float32, so that is quantisation, not disagreement. The builder's own timings
on this run: 3.58 s for the two Dijkstras, 3.30 s for the provenance snap over 330,502 cells.

### `NO_PATH` is unreachable in every shipped configuration today

Measured, not argued: after preparation the retained walk graph has **1 strongly connected
component**, and **0 of 539,814 nodes** are unreached by the unbounded cost search.

The reason is an ordering in `g1_own_graph_layer.py`: `symmetrise` runs *before*
`largest_component`, so the retained component is strongly connected, and the 417 destination nodes
are snapped on the pruned graph and therefore inside it. Every retained node reaches a destination.
`NO_PATH` cannot occur.

For bike and drive the status is unavailable for the other reason — Valhalla `/expansion` cannot
prove it. So **no shipped layer can currently contain `NO_PATH`.**

It stays in the enum, because the code path is correct and tested and an unsymmetrised own-graph
layer would produce it. But two consequences must not be missed:

- Nobody should write user-facing copy for a status users cannot see, and nobody should read its
  absence as evidence of anything.
- **Component pruning, not unreachability, is what hides a disconnected neighbourhood.** 3,046
  components were found and 13,608 nodes (2.5%) dropped. A household whose streets were in a
  dropped component does not get `NO_PATH`; their cells either snap to a retained road up to 200 m
  away — a finite time on a road they may not actually be able to reach — or fall outside the cap
  and read `OFF_NETWORK`. That is the honest-looking failure mode, and it is why S2.4's
  build-time diagnostic matters more than this status does.

A documentation correction while here: `components.py`'s docstring says the widened Triangle walk
graph has **4,208** components. Measured through the production preparation path it is **3,046**,
because the docstring's count predates the `degree() == 0` removal that strips isolated nodes. The
drive figure (1,685) was not re-measured.

### How far the category surface is from a minimum over destinations

§3 establishes that the shipped surface is an **upper bound** on `min_d t(cell → d)`, not that
minimum. The size of the gap decides whether that matters, and both ends of the bracket are one
Dijkstra, so it is directly measurable on the real build. Over the 253,679 cells where both sides
have a time:

| | |
|---|---|
| cells differing by more than 1 s | **23,468 — 9.25%** |
| median gap where they differ | **37.7 s** |
| p90 gap where they differ | 129.7 s |
| maximum gap | 668.6 s (11.1 min) |

A 9% disagreement rate sounds alarming, but seconds are not the product. What matters is how many
cells the gap moves across a threshold a household would actually set:

| threshold | cells the shipped surface excludes that the lower bound includes | share of passing cells |
|---|---|---|
| 10 min | 202 | **0.83%** |
| 15 min | 325 | **0.69%** |
| 25 min | 340 | 0.37% |
| 45 min | 256 | 0.16% |

So the defect is real, one-directional, and **bounded below 1% of the included region** at every
threshold tested — and the effect shrinks as the threshold grows, because a longer budget makes
the penalised shortcut less often decisive.

That is the number the design decision needs. Changing the algorithm means revisiting the access
policy the owner already approved, so it is not a fix to make quietly; and these figures use the
450/120 s penalties, which the access module labels as **priors, not measurements**. S2.5's penalty
sweep re-runs on the production path and should report this bracket alongside coverage, since both
move with the same unvalidated constant.

---

## 10. Codex absorption record, pass 8

Full review: `../research/15-codex-adversarial-review-pass8-s0-contract.md`. Three High, four
Medium, two Low; no Critical demonstrated. Every finding is absorbed; none is deferred without
being named.

| finding | where it landed |
|---|---|
| **H1** exhaustiveness belongs to a search invocation, not an engine name | §1 — `node_reasons` takes `search_bounded` as a required keyword; `layer.py`'s single-weight branch no longer passes a node cutoff (output-preserving, verified) |
| **H2** cost-optimal category routing is not minimum-over-destination time | §3 — the claim corrected, the aggregation renamed `cost_selected_category`, the bracket defined, §9 measures the gap |
| **H3** cache identity omits dependencies; derived versions were optional | §5 — expansion constants added to the digest, derived versions now enforced, the remaining gaps tabulated as S4.1 obligations |
| **M1** a validated layer-wide failure could exclude cells | §2 — `validate` requires one uniform reason with a zero bound; `evaluate` decides layer-wide reasons by the reason alone |
| **M2** approximate horizon validation changed exact threshold answers | §2 — exact equality required, and `evaluate` reads `horizon_s` rather than the stored bound |
| **M3** transit identity accepted contradictory horizons and invalid windows | §4 — window and horizon enforced equal, both required finite and positive |
| **M4** the existing artifact builder still discarded provenance | `layer.build_layer_surface` added, returning a validated `Surface` and distinguishing the two layer-wide destination failures; §9 runs the real build through it |
| **L1** an infinite threshold broke "`NO_PATH` always fails" | §2 — thresholds must be finite, *and* the rule no longer depends on that check |
| **L2** the rationale rejecting access-speed lower bounds was false | §2 — rationale corrected; the weaker bound kept deliberately, with the reason stated |

Two findings were corrections to claims rather than to code, and both were mine: H2's category
minimum and L2's soundness argument. The pattern is the same one that produced the `expansion.py`
bug and §8's — an argument that sounds right, asserted in a docstring, never executed. H2 took one
three-node fixture to falsify.

Codex also recorded what survived its attack, which is the more useful half: the taxonomy (no fifth
per-cell cause found), the pruning argument for `NO_PATH` within the retained graph, the
`OFF_NETWORK` bound for the implemented model, the strict-horizon comparison, the refactor
(1,200 calls / 1,200,000 cell results byte-identical against HEAD), the endpoint-relevance
precedence (36 directed fixtures), the truth table (all 363 combinations of one to five outcomes),
the per-anchor guards and the `max(t_A, t_B)` identity, the DST discrimination (including a
half-hour-offset zone, Australia/Lord_Howe), and stable hashing. Its limits are stated too: no live
Valhalla or MOTIS request was made, so engine boundary semantics are inspected rather than
certified, and "answerable by searching further" is an attempted computation, not a guaranteed
finite answer.
