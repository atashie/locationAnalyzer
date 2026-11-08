---
name: project-phase1-s2-progress
description: "Phase 1 stage S2 COMPLETE - all five tasks done, Codex passes 10-12 absorbed; the headline measurements and the over-correction pattern"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3448970c-7f62-4034-83e7-b7d86efb0261
  modified: 2026-11-04T20:05:00.000Z
---

Branch `v2-rethink`. **276 tests.** Head `dca5b49`. **S2 is COMPLETE.** Commits: `d4c6c6b` S2.1
resolver, `1bf0f41` S2.2 anchor routability, `42ea332` S2.5 penalty sweep, `9879105` the drive-gap
mechanism, `aead069` routing-extent re-acquisition, `32d5db9` pass 10, `6d1702c` pass 11, `5446d5e`
S2.4, `dca5b49` pass 12 + S2.3.
Not committed on purpose: `.claude/settings.local.json` (local config) and `backend/test_*.py`
(hard-code a TripAdvisor key).

| S2 task | state |
|---|---|
| S2.1 place-name resolver | **done** |
| S2.2 anchor routability | **done** |
| S2.3 access lawfulness audit | **done** (`dca5b49`) |
| S2.4 building-weighted coverage | **done** (`5446d5e`) |
| S2.5 penalty sweep re-run | **done** |

**S2.1 resolver** (`locfinder/places/resolve.py`). Real Triangle index — *these figures are the
superseded evaluation-extent download; current is 113,720 places / 107,484 Overture / 229
localities* — 96,585 places (90,349 Overture + 7,425 OSM), bounded by the **routing** bbox (a workplace can sit outside the grid). Ten verbatim
benchmark queries: **10/10 candidates, 7 single, 3 ambiguous, 0 not found, median 14 ms** - Census
had resolved **none**. Ambiguity is surfaced, never auto-picked (`anchor` is None), which is the
Morganton failure mode. OSM outranks Overture on a tie. Candidates carry source-native id, licence
(decision 17) and address.
*My bug, found only on real data:* locality was a score **bonus** and `min(1.0, ...)` capped it away,
so "Harris Teeter Carrboro" tied four exact matches and the Carrboro shop wasn't in the top four.
Now an explicit tiebreaker. **A ranking signal a cap can neutralise is worse than none.**
*Named gap:* "RTP" cannot resolve - **coverage, not scoring**. No place carries that alias; the index
is POIs, so districts/campuses (OSM `place=*`/`landuse=*`, boundary relations) are absent and area
queries return businesses with the area in their name. Needs an area index.

**S2.2 anchor routability** (`locfinder/places/anchor.py`). `CoreReachability` = the directed test
`components.py` says is the real one: a node is usable as a *destination* iff a directed path runs
**from** the largest SCC **to** it. O(V+E) once (0.0 s / 438,250 nodes), constant time per anchor.
A one-way *source* is unusable, a one-way *sink* is fine, and weak connectivity calls both connected.
Measured: **143 of 437,615 nodes (0.0327%)** survive weak pruning but cannot be reached from the
core; on 12 anchors it changed the chosen node **once**. **The RDU stub failure does NOT reproduce** -
all 6 nodes within 150 m are core-reachable, so `largest_component` had already fixed it and the
plan's RDU framing was stale. **12/12 usable, 1 nudged**, 3.6-77.6 m.
*Two defects of mine, both found by one real run:* (1) a barrier **veto** made RDU unusable - all 6
candidates are cut off by the airport perimeter `barrier=fence`, and a straight segment is a crude
proxy for an approach that loops round the terminal road, so at any fenced site a veto is a false
negative; barriers now **rank**, with `crossed_barrier` carrying the caveat. (2) `nudged` meant
"moved >1 m" so it fired on all 12; it now means a *nearer* candidate was rejected.
Barriers: QuackOSM from the routing extract, 4,665 separating ways (fence/wall/retaining_wall/
hedge/city_wall). **kerb (1,113), guard_rail (350), handrail, ditch excluded** - crossable, often
mode-dependently.

**S2.5 penalty sweep.** *Evaluation-extent figures; the routing-extent re-run below reads 77.69% at
the adopted penalty, 0.09 points across 0-960 s, 73,444 diverted at 960 s, and 4,420 of 256,752
restricted-nearest cells of which 4,178 are `access=private`.* Coverage at the adopted 120 s is
**76.76%** (superseded 77.32%), matching the
rebuilt layer's 76.7557%. Diverted-node counts are **identical** across runs, localising the old
defect to the cell stage. **The unvalidated prior barely moves what we publish**: 0-960 s moves
coverage 0.10 points and the median 0.3 min while diverted nodes go 0 -> 55,694 - a route-choice
knob, walk only. **The access fix is worth 1.7% of reachable cells** (4,367 of 253,679; 4,125
`access=private`).

**The drive gap is destination selection, not penalties** - my hypothesis was wrong. `/expansion` is
multi-source: it reports time along the cost-optimal path to the **cost**-nearest POI, while the
matrix takes the *smallest time* over POIs. drive 1 POI **+0.0 s**, 3 POIs +131 s; walk 1 +11.5 s,
3 +6.0 s. Controls: `/route` vs `sources_to_targets` agree to +0.6 s; gap persists where path
*lengths* agree (+206 s). **Same phenomenon as pass-8 H2 one level up** - any multi-destination
surface is an **upper bound** on `min_d t`. Anchor drive surfaces are faithful; **category** drive
surfaces over-report (false exclusions only).

**Also corrected:** `components.py` 4,208 -> **3,046** walk components (old figure predated the
`degree()==0` removal; drive's 1,685 unverified). `feeds_report.json` had 8 entries for 7 feeds
(Duke twice, a generator bug - its `agency.txt` has one row); deduped on disk and "count distinct
feeds and assert against `feeds.txt`" is now an explicit **S4.3** requirement.

**S2.4 data + the licence decision Buildings forced** (`1da0759`). 500,592 buildings for the
Triangle **evaluation** bbox. Registry row written from the docs *before* download per the registry
rule, then corrected from observed values (it had named Google Open Buildings - absent here).
**First partition accepted 0 of 500,592**: observed licences are `ODbL-1.0` (782,594 entries;
OpenStreetMap 437,549 + Microsoft ML Buildings 345,045) and a **non-SPDX free-text** CC BY string
(25,523; Esri). Fail-closed working, not a bug.
**Decision taken:** widen the allowlist **for this use only** - `resolve_licence` gained a per-use
`allowed` set and `fetch_buildings.py` passes `DIAGNOSTIC_LICENCES`. Mutating the module-level set
would have let ODbL rows into every other consumer silently. Reasoning: decision 17 welcomes
ODbL publication, and S2.4 rasterises to **counts** and republishes nothing (Produced Work).
**My reading, owner's to overturn** - revisit if footprints ever feed anything published, since a
derived *database* with ODbL rows is share-alike. The CC BY string is matched literally, so a
reworded release will quarantine again.
*Two defects found:* `licence.py`'s `row.get("sources") or []` raises on a multi-element numpy array
(what GeoParquet gives); survived only because the one caller normalised first. And a
manifest-resolved licence was never checked against the allowlist. Both fixed with tests.

**Codex pass 10 on S2.1/S2.2** (`docs/research/17-...`): 5 High, 6 Medium, 1 Low, all absorbed
(`32d5db9`). Worst finds: **"Duke Hospital" resolved to a BUS PLATFORM** (`from_osm` never read
`highway`/`public_transport`/`railway`, so a platform had no category); a **leading** locality sent
"Durham Whole Foods" to the **Amtrak station** at 0.85 (the `subset` branch gave a one-word name a
flat score); `[:limit]` applied *before* the ambiguity decision, so `limit=1` manufactured
confidence; corroboration merged a **bank and its own ATM** 9 m apart; and an **interrupted download
inherited the previous release label**. Nine real defects fixed and **the benchmark score did not
move** - the three failures are naming/coverage, not ranking. My correctness grade also *fell* from
3/5 to **2/5** once identity was checked instead of distance.
**My first H4 fix over-corrected**: requiring *equal* categories broke real de-duplication (one
Harris Teeter arrives as OSM `supermarket` + Overture `grocery_store`). Only a subsidiary/parent
distinction blocks a merge now. Lesson: a fix to a review finding needs re-running on real data too.

**Routing-extent re-acquisition** (`aead069`, owner-approved, closes pass-10 M6). 90,349 ->
**107,484** places, 452 -> **550** groceries, index 96,585 -> **113,720**, 229 localities, 0
quarantined. It also removed an unnamed artefact: **category destinations were evaluation-only**, so
an edge cell could not use a grocery just outside the grid - the very truncation the routing buffer
exists to prevent. Evaluation bbox is right for the output grid and coverage denominators, never for
inputs.
New: `locfinder/places/acquire.py` holds both S4.1 acquisition hazards in one place with **10 tests
that inject failing/interrupted downloaders** - neither failure is reachable from a happy-path test,
which is why both survived. `fetch_overture` used to return ANY existing raw file regardless of
release *or bbox*, which is how an evaluation-extent file backed a routing-extent claim.
**Determinism fix:** spikes take "the first N POIs" and file order is unstable across downloads, so
re-acquiring silently changed *which* groceries an experiment used. `select_overture`/`select_osm`
now sort deterministically. **A measurement from before this is not comparable with one after.**

Re-measured: sweep coverage **76.76% -> 77.69%**, reachable 253,679 -> **256,752**; decomposition
**OK 77.6855% / OFF_NETWORK 17.4102% / BEYOND_HORIZON 4.9044%**. The entire gain came out of
BEYOND_HORIZON and **OFF_NETWORK did not move one cell** - what the taxonomy predicts, and evidence
the statuses measure different things. The old **77.32%** being close to 77.69% is a coincidence,
not vindication: it was wrong pipeline + narrow inputs, two errors in opposite directions.

**Codex pass 11 absorbed** (`6d1702c`, `docs/research/18-...`): 3 High, 5 Medium, 1 Low.
- **H1** my acquisition-safety docstring exceeded the code: state-before-bytes makes one writer's
  interruption safe and says nothing about concurrency. Now an `O_CREAT|O_EXCL` lock around the
  whole check-download-commit, process-unique temp, stale-lock break. Reproduced deterministically
  by re-entering `acquire` from inside a downloader.
- **M1 I made the same over-correction twice.** The pass-10 raw-set replacement repeated the
  category-equality defect for `station`/`train_station` and `fuel`/`gas_station`. Categories are
  now normalised to **roles** (`role_of`, `REFERENCE_ROLES`, `SUBSIDIARY_ROLES`).
- **H4 moved correctness for the first time: 2 of 5 -> 3 of 5.** `_decide` abstains when the leader
  is a reference feature and a non-reference candidate exists, so "Duke Hospital" is `ambiguous`
  with the right place offered instead of confidently returning a bus platform.
- **H2** my pass-10 fix had regressed: a destructive locality parse sent "Durham Coffee" to a place
  called "Coffee". Fixed with a `_readings()` ladder (intact / locality-stripped / +connective) and
  `reading` in the rank key, so an intact match outranks a stripped one at equal score.
- **M3 a claim I had to withdraw.** "More destinations can only help reachability" is false for what
  this layer reports — time along the **cost**-nearest path under a horizon — so a coverage delta is
  not a count. `spikes/s2_destination_monotonicity.py` measures the 452->550 widening as a **paired
  transition matrix** on one graph and grid (eval set reconstructed exactly: 452 of 550 routing-
  extent groceries are inside the eval bbox, and they resnap to 417 nodes, both original figures).
  **+3,073 = 3,074 gained and 1 lost**, the loss a real `OK -> BEYOND_HORIZON` with 72 s of headroom
  against 7,200 s; 14 of 253,678 cells OK in both report a **longer** time, up to +213.9 s. No
  threshold crossing in the losing direction. **Report coverage changes as gained-and-lost, never a
  net.**
- **M2** the determinism fix was narrower than it sounded: sorting stabilises the POI *prefix*, not a
  rebuild. `csr.py` parallel-edge retention, `EdgeIndex.from_graph`, scipy equal-cost paths and
  `ox.nearest_nodes` ties are all still order-dependent (Codex: 10 s vs 90 s from one pair
  reversed). Deferred to **S4.1**.
- **M4** buildings had been downloaded over the *geographic* eval bbox, which the UTM grid overruns
  by ~0.010-0.014 deg on every side (**15,015 cells, 4.54%**). Added `GridSpec.envelope_wgs84()`;
  re-acquired **522,160** buildings. **M5** two supersession notices said "below" and so swept in
  the replacements they pointed at. **L1** S0's artifact check printed a 4,091 s mismatch and
  exited 0; it now raises.

**S2.4 result: coverage has two denominators and they disagree by twenty points** (`5446d5e`,
`spikes/s2_building_weighted_coverage.py`). Over the 512,633 buildings whose centroid is inside the
grid: **OK 97.3423%** (vs 77.6855% of cells), OFF_NETWORK **0.7134%** (vs 17.41% of cells),
BEYOND_HORIZON **1.9443%**. So "22% of the Triangle has no walk time" and "2.7% of its buildings do"
are both true and only the second is about people. **At a threshold it inverts**: 15 min covers
14.37% of cells but **31.96% of buildings**; 45 min 48.91% and **82.88%**. Publish both.
This also settled the contract's deferred `max_speed_mps` judgement — tightening could convert at
most **0.71% of buildings** from *unknown* to *excluded*, so it stays loose.
**A region's dominant reason by area is not its dominant reason by building.** The largest missing
region (23,184 cells near -79.101, 35.790) holds 9,002 buildings — two thirds of all missing — and
is 53.2% OFF_NETWORK *by cells*, which reads like a road-data defect; by *buildings* it is **1,446
off-network vs 7,556 beyond-horizon**, i.e. a real rural grocery desert. Only the 1,446 are worth
checking. Reporting the cell-dominant reason alone would have aimed the next work at the wrong
thing.
Caveats kept explicit: **building-weighted, not home-weighted** (no residential flag; sheds, barns
and a hospital campus's many structures each count one), and the weights are ODbL/CC BY counts under
decision 17 — a Produced Work, footprints never republished.

**A defect found on disk, not by test** (`5446d5e`). The `overturemaps` CLI writes a sidecar
`<output>.state` — *exactly* `acquire`'s own state-file convention.
`data/slice/overture_places_raw.parquet.state` **was** that sidecar: valid JSON, wrong keys, so
`describes()` returned False and the pair re-downloaded **on every run, silently, forever**. Pass-11
H1's process-unique name had reduced it to one orphan per download but left the collision class
open. The download now happens in a process-unique temp **directory** removed wholesale, cleanup in
`finally`. Lesson: **a module must not share a filename namespace with a tool it shells out to.**

**Codex pass 12 absorbed** (`dca5b49`, `docs/research/19-...`): 4 High, 4 Medium, 1 Low, all fixed.
It verified the M3 measurement *more strictly than I had*: the stored raw **bbox predicates** select
the same 452 ids (count-matching was my weaker argument), and "all 550 geometries are points" was
**not** sufficient proof because their stored bboxes have non-zero width. It also confirmed the lost
cell's mechanism directly — snap distance unchanged, selected cost **falls** 7,147.86 -> 7,127.05
while time **rises** 7,027.86 -> 7,127.05.
- **H1, the lock was wrong twice running.** Pass 11's lock file was owned by its own *content*,
  which cannot be released safely: staleness 3600 s against an 1800 s wait let a waiter break a live
  45-minute download's lock, and the holder's `finally` then unlinked the **replacement** and
  admitted a third process. Now an **OS lock** (`msvcrt.locking` / `fcntl.flock`) on a handle held
  open for the duration, and the lock file is **never unlinked** — unlinking was the bug. Tests must
  be **cross-process**: an OS lock is per process, so pass-11's same-process re-entrant test was
  testing the wrong thing.
- **Three of nine were my own over-corrections, one area, three consecutive passes.** equal
  categories (p10) -> raw-set repeat (p11) -> subsidiary boolean too coarse (p12 H4): `parking` and
  `fuel` are deliberately not subsidiary, so OSM **RDU** `parking` merged with Overture **RDU**
  `airport`, and `pharmacy_counter` fell through to `facility` and corroborated its own pharmacy.
  Rule is now **equal roles**. M5 is a fourth: the pass-11 abstention made "Franklin Street bus
  stop" ambiguous against a cafe it beat 1.000 to 0.830, so an explicit transport word now
  suppresses it.
  **What caught these was the graded real-data benchmark run after every change, not more care while
  fixing.** It held at 3 of 5 through all four resolver fixes.
- **H2/H3, my fixes had each removed something.** Merging rebuilt the `Candidate` without `reading`,
  so it defaulted to the intact value and corroboration *manufactured* an intact match ("Durham
  Coffee" went confident once an Overture copy of a "Coffee" landed within 60 m). And
  `_split_locality` stripped the boundary connective inside itself, so the ladder lacked the rung
  "locality removed, connective intact" — "Durham The Coffee" scored only `Coffee` 1.000 while `The
  Coffee` got 0.725.
- **M6** four corners do not bound a UTM rectangle: the top edge's latitude maximum is in the edge's
  *interior*, and Codex's counterexample put 806 cell centres outside. The Triangle agreed with a
  dense check so the buildings were never short — the method was wrong. Now boundary-sampled.
- **M7** the snap tie rule was **asymmetric** (`<` outright vs a time preference only inside
  `np.isclose`), so reversing an edge's stored geometry gave 90 s vs 10 s. Now exact cost equality,
  ties to lower time. STRtree nearest-edge ties and equal-size component selection added to S4.1.
- **L1** a 0.01 s artifact tolerance accepts stored 600.005 vs rebuilt 599.999 — opposite sides of a
  600 s threshold. Now exact float32 equality, and it **passes exactly** (0 cells differ). Bypass is
  recorded in the report.
- **Corrected:** "nothing crosses a 10/15/25/45-min threshold in the losing direction" is four data
  points, not a property — cell (126, 612) fails at **47 min**.

**S2.3 access lawfulness — done** (`dca5b49`, `spikes/s2_access_lawfulness_audit.py`). Restricted
edges identified as **`cost - time > 0`** on the retained matrices (the penalty and nothing else),
117,253 of 1,395,589 walk edges. **Two numbers that answer different questions and must not be
swapped:**
- *descriptive*: 48,865 nodes (9.05%) have a restricted **first hop** (the lawful driveway);
  **26,395 (4.89%) have a shipped path routing THROUGH restricted land.**
- *decisive*: a strict policy (restricted only as the origin's first hop) costs 5,533 cells and
  **4,881 buildings = 0.95%**; 12,042 nodes lose every path, 25,186 get slower by a median 703 s.
  An unmodelled lawful hop at the *destination* end makes this an **upper bound**.
**So a published time is defensible; a published route is not without a per-path check.** That is a
precondition on S6 drawing routes. The strict surface was **verified cell-for-cell against S2.4's
cached reason raster first** — which caught a real error: omitting `node_cost` moved 6 cells, so the
comparison would have measured my reconstruction rather than the product.
This also replaced an unsupported claim (pass-12 M8): "the access fix is worth 1.7% of reachable
cells" is a **length-keyed proximity approximation** counting cells with a restricted edge *nearby*,
not cells recovered. I had been using the first as the second.

**Codex pass 13 absorbed** (`17c44f8`, `docs/research/20-...`): 4 High, 5 Medium, 2 Low. Verdict:
*"the headline numbers reproduce, but the access audit does not establish the lawfulness or
coverage-loss bound claimed."* **S2.3's conclusions were withdrawn and it was rebuilt.**
- **Edge position does not establish lawfulness** (H3). Splitting a driveway into two ways flips a
  journey's verdict; `access=private` is restricted *public* access, not entitlement. 26,395 / 4.89%
  is an **edge-position diagnostic**, not unlawful routes.
- The strict surface was not its own policy: the cell snap re-admitted restricted travel below the
  node level (H1), both branches shared one penalised `EdgeIndex` (H2), and the filter ran *after*
  parallel-edge collapse so lawful public parallels were deleted — 27 pairs, 2,673 more hidden (H4).
- **Rebuilt as a language**: `locfinder/traveltime/policy.py` + `tests/test_policy.py`. Lawful set is
  **`R* O* R*`**, a three-state automaton, solved on the graph x automaton product; the language is
  its own reverse so arrival uses the same states with the chains swapped. A *chain* is split-
  invariant, which is H3's fix — demonstrated at **0.000000 s** by subdividing every restricted edge.
  **2,833 of 539,814 nodes (0.5248%)** have no lawful journey; the policy costs **2,092 of 507,037
  buildings (0.4126%)**. Reported at nodes weighted by buildings, NOT cells (H1); the 5,533-cell
  figure is withdrawn.
- See [[project-h2-upper-bound-trap]] for the confound a soundness invariant caught here.
- **M8/M9 doc withdrawals**: the largest missing region is a *modelled long-access region*, not a
  demonstrated rural desert (BEYOND_HORIZON does not exclude a missing connection or an omitted
  grocery; 274 of its buildings are outside the eval bbox). And "only the second is about people"
  was a population inference the data does not license — buildings are structures, and the 15-minute
  figure is a ratio between denominators, **2.224x**.
- Three more resolver over-corrections (M5/M6/M7) made it **four consecutive passes**, which changed
  the method — see [[feedback-benchmark-over-point-fixes]]. 41 graded assertions now, **40 pass, one
  deliberately red** ("parking" resolves confidently to a listing named "Parking"; the fix is
  product routing, not scoring). The resolver is otherwise **frozen**.

**Codex pass 14 absorbed** (`ab01ffa`, `docs/research/21-...`): 7 High, 7 Medium, 2 Low. Head is
now `ab01ffa`, **328 tests**, benchmark **41 of 42**.
- **H1 the lawfulness claim was withdrawn a SECOND time.** `R* O* R*` accepts `RRR` through an
  *unrelated* third estate, so membership does **not** mean "not through-traffic over private
  land". See [[feedback-computable-property-is-not-the-claim]] — the pattern, not just the bug.
- **H2 the building figure is a nearest-node PROXY**, not building service: the connector is assumed
  zero-time, unrestricted and traversable, and its travel time is not added (a node at 7,190 s with
  a 100 m connector counted inside a 7,200 s horizon). "Under half a percent of buildings"
  withdrawn.
- **H3 a PRODUCTION defect in `speeds.symmetrise`**: it added a walking reverse only when no edge
  existed between the two nodes at all, so any `v->u` edge suppressed the reverse of every `u->v`
  road — losing a legitimate pedestrian route where an open and a restricted road share a pair.
  This was in the **shipped walk graph**. Now deduplicated per physical road by `osmid` + length.
  Re-measured effect, stated plainly: both-class pairs **2,700 -> 2,748**, slowdowns 38,939 ->
  38,956, median +12.3 -> +12.2 s, headline **2,833 nodes / 2,092 buildings unchanged**.
- **H4 my pass-13 promotion fix manufactured confidence** — it ran inside `_merge_corroborating` so
  `_decide` saw the reordered list ("Northside Durham" -> resolved to a restaurant). Promotion is
  now presentation-only, applied after the outcome. **A reordering meant to improve a chooser must
  never remove the chooser.**
- **S3 design is revision 2** with its own change log: overlapping strata replaced by two
  self-weighting simple random samples plus unpooled diagnostics; two frames (a building frame
  cannot estimate all-cell rates); an explicit acceptance rule (E1a <= 2.0%, E1b <= 1.0%, one-sided
  95% upper, plus INCONCLUSIVE); a predeclared DEFF = 2.0 fallback since zero failures makes DEFF
  inestimable; a full comparator spec and a verdict table for every status; and a falsification rule
  for E3, which was unfalsifiable as written.
- **M1/M2/M3 the benchmark's own weaknesses** — see [[feedback-benchmark-over-point-fixes]], now
  extended with the revert-the-fix experiment. Tightening the assertions caught two more live
  defects: a **34.9 km** wrong leader (a transport phrase inflating names containing those words;
  the phrase-free form is now a reading) and a **32 km** confident wrong answer (a typed locality
  must now be **confirmed**, not merely un-contradicted — and the first version of that fix tested
  the per-reading `locality_match` flag, which broke six tests).
- Smaller: the bare-locality explanation was false — **62 records' normalised names equal 29
  locality strings** in this index (Burlington stores, a Gulf station), so it is entity-type
  ambiguity, not absence; **228** localities not 229; the apostrophe fix missed U+00B4 because
  `_INTRAWORD` ran after NFKD.

**Next:** S3 execution (frames, comparator harness, blocks, then the pilot). Owner-gated and not
startable by me: the published **maximum duration** (gates the S3.5 encoding freeze), the G4 device
matrix, G3 phone render, 3-5 G5a household sessions, 5-8 hand-timed journeys, and whether a bare
category noun should route to the category criterion instead of the anchor resolver (the one
deliberately red benchmark assertion).

Related: [[project-phase1-s1-complete]], [[project-phase1-s0-complete]],
[[feedback-codex-adversarial-review]], [[feedback-experiments-over-priors]].
