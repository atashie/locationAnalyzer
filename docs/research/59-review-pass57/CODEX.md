# Pass 57 review - Codex (gpt-6.1-sol)

Run 2026-11-16 against the prompt in `docs/research/58-review-pass57-prompt.md`, independently of
the Antigravity pass beside it and without sight of it. Captured from stdout; the reviewer had
read-only sandbox access and no write access to the repository.

**It executed 38 commands.** Unlike pass 56's Codex run -- which the Windows restricted-token
sandbox blocked from starting any process -- this one ran the venv Python, reproduced
`measure_hatch_visibility.py` and `measure_donut_holes.py`, rebuilt cost-selected predecessor
forests, built a two-state routing prototype and a destination-attachment prototype, and ran 135
tests. Its own account of what it ran, and of what it could not, is in the final section.

**The launch failed silently the first time.** `codex exec` appends stdin to its positional prompt,
so in a background shell it printed `Reading additional input from stdin...` and blocked for 1 hour
48 minutes on 0.3 seconds of CPU without starting. Relaunched with `< /dev/null`; see
[[reference-codex-runtime-quirks]].

---

**Pass 57 review — 16 November 2026**

I started with W1–W13, executed the available measurements and additional probes through `v2/.venv/Scripts/python.exe`, and inspected the implementation. No file was changed, and no option was taken.

Throughout this review, **UTM** means the 100 m source grid; **published** means the exported WGS84 grid. Both contain 330,502 cells. Building counts below count accepted building records, not households or residential addresses.

**Declared weaknesses**

**W1 — A topology audit cannot conclusively classify all 121 holes.**

The proposed desk investigation is useful, but claim 8 promises too much. Geometric contact without a shared OSM node establishes a representation difference. It does not establish an available pedestrian connection.

For each original **published park/walk hole at 20 minutes**, the desk test should:

1. Recover the sampled UTM cell, matched edge, selected route and alternative attachment responsible for the apparent improvement.
2. Inspect the original OSM ways and nodes, including connecting ways that graph filtering or component pruning removed.
3. Check grade separation, access restrictions, barriers and identifiable entrances.
4. Identify a physically plausible pedestrian connection.
5. Evaluate that specific connection in a temporary routing counterfactual, checking whether it changes the original cell’s threshold verdict.

The result should distinguish **supported missing connection**, **supported legitimate separation**, and **unresolved**. Absence of a mapped fence is insufficient evidence for a connection.

A sharper test combines that audit with targeted ground verification of unresolved, occupied holes. The decisive question is whether an available journey makes the exclusion wrong. Auditing noding alone cannot answer that across all 121 cells.

**W2 — “Measure first” needs a stopping rule and an actionable consequence.**

The adversarial case for disclosure now is strong: these are 121 published cells containing 356 buildings, and their actual error rate remains unknown. A lengthy connectivity investigation could consume more effort than the harm warrants.

The case for routed access is stronger if independently verified examples show that households can reach roads the single-nearest-edge rule rejects. However, a routed connector cannot manufacture missing paths or establish permission to cross private ground.

Even “60% are noding gaps” would be insufficient without defining that classification and showing that correcting those connections changes household answers. Upstream propagation taking months is also not established here: publication depends on this project’s extract, cache and rebuild process.

I recommend a **bounded access-and-connectivity investigation**, prioritising occupied cells and recording original-hole repairs. Its deliverable should be enough evidence to choose among disclosure, attachment work and data correction. An indefinitely expanding topology census would not satisfy “measure first.”

**W3 — The building percentage is accurate but insufficient.**

I independently reproduced:

```text
Published park/walk, 20 minutes
holes                         121
buildings in holes            356
occupied hole cells            76
empty hole cells               45
published building population 500451
```

A better risk statement is:

> At 20 minutes on published park/walk, 121 isolated excluded cells contain 356 accepted buildings. Seventy-six cells contain buildings; the largest contains 27. The proportion of those exclusions that is wrong has not been established.

These are **76 occupied raster cells**, not necessarily 76 parcels. The 0.071% inventory share describes geographic concentration; it does not measure error prevalence or severity for affected households.

**W4 — Median one is true; “therefore nearly the same rule” does not follow.**

I reconstructed cost-selected predecessor forests, propagated restricted-edge counts and continuous restricted runs, included positive-length travel on the matched origin edge, and sampled those results through the exporter’s nearest-neighbour mapping.

The reconstructed baseline had **zero published minute-value differences on OK cells for all seven layers**.

For the three walk layers:

| Published layer | OK cells | Selected route touches restricted ground | Share of all published cells | Restricted edges exceed restricted runs |
|---|---:|---:|---:|---:|
| Grocery/walk | 258,684 | 57,193 | 17.31% | 13,329 |
| Park/walk | 270,308 | 67,676 | 20.48% | 16,843 |
| School/walk | 260,781 | 55,927 | 16.92% | 12,823 |

Conditional on touching restricted ground:

| Layer | Restricted-edge count: median / p75 / p90 / p95 / p99 / max | Restricted-run count: median / p90 / p95 / max |
|---|---|---|
| Grocery/walk | 1 / 2 / 3 / 4 / 8 / 25 | 1 / 1 / 2 / 7 |
| Park/walk | 1 / 2 / 3 / 4 / 8 / 25 | 1 / 2 / 2 / 6 |
| School/walk | 1 / 2 / 3 / 4 / 8 / 25 | 1 / 1 / 2 / 7 |

Exactly one restricted edge occurs in 41,645 grocery, 46,448 park and 41,241 school routes. Those are majorities of the restricted-route populations, but the remaining tails are substantial.

These counts measure **exposure**, not wrong journeys. A separate grocery/walk per-stretch prototype, retaining the current origin edge index and keeping the penalty at 120 s, changed:

```text
published minute values       5690
20-minute threshold decisions  189
finite journeys gained          38
finite journeys lost             0
```

Thus neither “almost no behavioural change” nor “20% of answers will change” is justified.

**W5 — State is required, but doubling every node is not compulsory.**

For the stated rule, sufficient forward-search state is:

```text
(node, whether the preceding traversed edge was restricted)
```

Traversing an edge with restriction flag `f`, from preceding flag `r`, costs:

```text
travel_time + penalty × [f and not r]
```

Its successor state is `(next_node, f)`. Reported time accumulates only travel time.

For arrival routing, reverse this expanded graph and initialise both states at each destination. Origin attachment also needs state-aware handling: a positive restricted partial edge starts a restricted run; zero traversal at an endpoint does not.

A transition cost or node-splitting formulation is an equivalent representation of this state. No fixed edge weight on the original vertices can represent both histories at a junction where entering a restricted continuation costs differently.

A full expansion was inexpensive in this execution:

| Grocery/walk measurement | Current graph | Full two-state prototype |
|---|---:|---:|
| States | 539,814 | 1,079,628 |
| CSR arcs | 1,395,589 | 2,796,674 |
| Cost + time CSR storage | 37.81 MB | 75.76 MB |
| Dijkstra | 0.089 s | 0.196 s |
| Search plus time reconstruction | 0.607 s | 1.194 s |

Expanded-array construction took 2.84 s. Graph preparation for that probe took 92 s. These are single-run measurements, not production benchmarks or peak-memory measurements.

Only **46,043 walk vertices** had mixed incoming restriction classes and restricted outgoing continuations. A compressed exact representation can concentrate additional labels at such boundaries, with appropriate handling of origins and terminals.

Two implementation details matter:

- **Preserve parallel alternatives until their restriction state is known.** The existing CSR collapses parallel edges under the current per-edge cost. That winner need not remain optimal when continuing an already restricted run.
- **Retain time-based horizon classification after an exhaustive cost search.** A cost cutoff cannot substitute for a reported-time cutoff.

Per-stretch selection does not inherently invalidate `access_distance / max_speed` as a time lower bound. Every selected physical journey still obeys the speed bound. `BEYOND_HORIZON` remains valid when derived from the new selected journey’s real time.

The existing admissibility tests concern admission of walked observations; they do not prove a future routing implementation correct. The read-only test run passed 135 tests, with two file-writing ingestion tests excluded.

**W6 — The presentation order is unsuitable as a work-priority order.**

My product-risk ranking is **2 → 4 → 3 → 1**, explained below. Discussing holes first followed the owner’s questions; doing the work in that order would not follow the execution plan’s product-risk principle.

**W7 — The requested all-park boundary measurement rests on a false description of the input.**

Execution found:

```text
accepted park records 746
Point geometries     746
Polygon geometries     0
```

The centroid operation therefore leaves each park input point unchanged. The repository is not currently calculating the centroid of each accepted park polygon.

It is impossible to compute “each published park’s own boundary” directly from these records. Polygon matching is necessary first.

I tested a deliberately limited matching rule: one OSM park polygon with the same normalised name within 100 m of the accepted point. This produced **204 point-to-polygon matches**; multiple records can match the same park.

Within that subset:

| Geometric distance | Median | p95 | Maximum |
|---|---:|---:|---:|
| Accepted point to matched boundary | 43.9 m | 194.8 m | 1,283.5 m |
| OSM polygon centroid to its boundary | 65.3 m | 305.2 m | 1,593.3 m |

For nominal published cell centres outside and within 100 m of selected matched boundaries:

| Matched park | OK abutting cells | Published park/walk minutes: median / maximum |
|---|---:|---:|
| William B. Umstead State Park | 260 | 24 / 76 |
| Dorothea Dix Park | 65 | 7 / 17 |
| Lake Crabtree County Park | 45 | 13 / 20 |
| E. Carroll Joyner Park | 30 | 10 / 24 |

These are genuine published-grid measurements, but **not measured boundary-access errors**. They do not establish entry permission, accessible crossings, or which park supplied the published answer.

The subset shows that large cases exist locally. It does not establish an all-746 median error or a defensible routed boundary counterfactual. Quoting the geometric gap divided by walking speed as actual time saved would repeat the straight-line-access mistake.

**W8 — Nearest boundary is not a sufficient replacement.**

An unrestricted nearest-boundary target can produce confident optimistic answers across fences, rivers and transport barriers.

My preferred destination model for further evaluation would be a set of **accessible entry locations**, using mapped entrances or verified network crossings, with provenance and uncertainty recorded. A polygon can help identify candidate crossings; proximity to a road within the access cap does not prove entry.

The repository already recognises this distinction in `locfinder/places/anchor.py`: reachability, displacement and barrier evidence are separate concerns. Its barrier-crossing disclosure also illustrates why a straight-line barrier test is not a complete access model.

The appropriate next measurement is a matched set of large parks with credible entrances, followed by published-grid threshold comparisons. Neither centroid nor boundary geometry alone establishes usability.

**W9 — A general destination-attachment change is broad, and the cap changes the answer.**

Using the current **300 m destination admission cap**, these existing retained destination records move their network attachment point by more than 1 mm when attached to the nearest edge:

| Criterion | Retained destination records | Attachment points that move |
|---|---:|---:|
| Grocery/walk | 549 | 519 |
| Park/walk | 739 | 656 |
| School/walk | 559 | 499 |
| Grocery/drive | 550 | 536 |
| Coffee/bike | 678 | 635 |
| Duke Hospital/drive | 1 | 1 |
| RDU/drive | 2 | 2 |

These count destination **records**, not distinct old destination nodes.

The crucial cap distinction is:

```text
Park edge attachment, 300 m cap:
  recovers 6 previously dropped records
  loses    0 previously retained records

Park edge attachment, 200 m cap:
  recovers 5 previously dropped records
  loses    4 previously retained records
```

For example, Ocaneechee Park is 329.65 m from its nearest node and 229.58 m from its nearest edge. A 300 m edge cap recovers it; the origins’ 200 m cap does not.

I also evaluated an explicit attachment prototype: nearest-edge destination projection, a straight destination access leg, directional partial-edge travel, and direct arrivals when origin and destination lie on the same edge. It used a **200 m destination cap**, with the existing origin rule and horizon.

| Criterion | Published minute values changed | Threshold flips at the criterion’s default |
|---|---:|---:|
| Grocery/walk | 103,881 | 2,136 at 20 min |
| Park/walk | 115,166 | 3,643 at 15 min |
| School/walk | 135,083 | 3,894 at 20 min |
| Grocery/drive | 65,331 | 2,630 at 10 min |
| Coffee/bike | 30,694 | 828 at 15 min |
| Duke Hospital/drive | 225,002 | 8,909 at 30 min |
| RDU/drive | 68,040 | 637 at 40 min |

This is a defined sensitivity experiment, not a validated replacement. It changes destination access-time accounting as well as attachment location. The result establishes that a general implementation affects all seven layers; it does not establish that every change improves accuracy.

**W10 — The code predicts several visual artefacts; the complaint does not identify one.**

The mask uses nearest-neighbour raster sampling. For an unrotated, unpitched map, its nominal CSS-pixel dimensions are approximately:

| Zoom | Pixels per raster cell | Diagonal hatch period, perpendicular to stripes |
|---|---:|---:|
| 8 | 0.40 | 2.23 px |
| 9 | 0.79 | 4.47 px |
| 10 | 1.58 | 8.94 px |
| 11 | 3.16 | 17.88 px |
| 12 | 6.32 | 35.75 px |
| 14 | 25.28 | 143.00 px |

At low zoom, subpixel cells and narrow stripes can be dropped or exhibit sampling beats. At higher zoom, the pattern becomes broad, stepped diagonal bands. Small marked regions can disappear at low zoom or become conspicuous blocks when enlarged; they are not necessarily visible specks at every zoom.

“Striping effects” most directly describes the diagonal texture or its sampling artefacts. The complaint does **not** establish that the owner was primarily concerned about invisible small components. That is a separate defect the investigation uncovered.

No screenshot-level diagnosis was performed here. These are code-and-projection predictions.

**W11 — Solid fill is a candidate, not an established design improvement.**

I would evaluate a restrained, visually distinct UNKNOWN underfill that preserves the distinction from EXCLUDED, with an explicit legend and hover explanation. If texture remains, screen-space texture over that underfill is worth evaluating.

A flat grey treatment could obscure context or look like another data class. Its success needs a reading check at the opening view and useful zoom levels.

For the listed alternatives:

| Rendering option | Assessment |
|---|---|
| Solid translucent fill | Removes holes in the marking at texture resolution; colour, opacity and comprehension remain untested. |
| Force one marked cell per component | Marks every component, but one dot does not communicate its extent or guarantee screen visibility. |
| Outline or stipple boundaries | Can identify boundaries while leaving large interiors ambiguous. |
| Screen-space pattern | Addresses scale-dependent texture size; needs separate handling of small regions and transparent gaps. |

The 166 large regions having at least one marked cell does not establish that their presentation works for readers.

**W12 — UNKNOWN is justified; clipping requires a coverage decision.**

I reproduced **3,364 accepted buildings** in published OFF_NETWORK cells: 0.672% of the 500,451-building published population.

That makes “usually nobody lives there” an inadequate justification for hiding the area. Building records also do not establish residential occupancy.

For cells where the model cannot establish a threshold failure from its lower bound, UNKNOWN is the appropriate epistemic verdict. The model has insufficient evidence for PASS or FAIL.

Publishing a deliberately smaller supported area can be honest if its boundary and outside-coverage meaning are explicit. Silently making unsupported land transparent would preserve the location ambiguity. A legend count alone does not tell a household whether its property is covered.

Also, the 56,036 published cells are approximately **535 km²**, rather than 560 km²: the published cells are not 100 m UTM squares.

**W13 — Building exposure is measurable without resampling a count raster.**

I computed building centroids in UTM using the project’s `structure_population` convention, transformed those points to WGS84, assigned each point once to its published cell, and counted by cell. This avoids duplicating or dropping building counts through raster reprojection.

The method reproduces the claimed published population and hole-building figures:

```text
UTM building population              512633
published building population        500451
buildings in published park holes       356
```

For **published park/walk at 20 minutes**:

```text
wholly invisible UNKNOWN regions        369
cells in those regions                  975
buildings in those regions               55
occupied invisible regions               17
occupied invisible cells                 25
all UNKNOWN-region buildings           3364
```

The invisible regions contain about **0.011% of published buildings**, or **1.64% of buildings in UNKNOWN cells**. This materially qualifies the “one-third of regions” headline.

The missing mark is still real. Its measured building exposure is much smaller than its component-count percentage suggests. Neither percentage alone decides whether the overall striping design is acceptable.

**Verdicts on claims 1–30**

**Decision 1 — Donut holes**

| Claim | Verdict | Evidence and correction |
|---|---|---|
| **1** | **CONFIRMED** | `_snap_network` obtains one nearest indexed geometry per cell. Different nearest attachments can produce discontinuous answers. This mechanism does not establish that every hole is erroneous. |
| **2** | **CONFIRMED** | Independently reproduced 121 published holes, 356 buildings, 76 occupied cells and 45 empty cells at park/walk 20 minutes. The 0.07% inventory share is correct. |
| **3** | **OVERSTATED** | The actual wrong-hole count is unmeasured. However, “most” structural flags are not defects is also unmeasured. The approximately 90,000 figure is a particular UTM candidate-experiment population gaining more than 60 s, not an audited defect classifier. |
| **4** | **CONFIRMED** | Net reduction is not original-hole repair. The executed identity measurement now closes this gap for the diagnostic: **UTM: all 125 originals filled, 30 new sites; published: all 121 originals filled, 29 new sites**, at park/walk 20 minutes. |
| **5** | **OVERSTATED** | The percentages concern the **125 UTM holes**, not the 121 published holes. Enrichment depends on the comparison population; the notes acknowledge an OFF_NETWORK-contaminated baseline. The evidence supports rejecting a universal class exclusion, not proving that tags explain no cases. |
| **6** | **WRONG** | The 76% figure is the UTM **net reduction** from 125 to 30, whereas all original holes are filled. The 77.13% denominator is 272,961 comparable, uncapped UTM cells, not all cells. The 169 m median applies only to the >60 s improvement subset. Cross-candidate selection minimises reported time; when selected on cost instead, my diagnostic found **3,202 UTM OK cells slower**. |
| **7** | **OVERSTATED** | Noding inspection alone does not measure actual wrong answers, and it is not the only way to investigate them. A bounded access investigation is justified; exclusivity and decisiveness are not. |
| **8** | **WRONG** | Physical walkability and legitimate separation cannot be settled across all cases by pure topology. A desk audit can establish candidates and resolve some cases, with explicit unresolved outcomes. |

The candidate experiment’s zero-slower result is partly guaranteed by its construction: it takes the minimum reported time including today’s answer. That is not evidence that a cost-selected production implementation must make every reported time faster.

**Decision 2 — Restricted-road penalty**

| Claim | Verdict | Evidence and correction |
|---|---|---|
| **9** | **CONFIRMED** | `access.py` declares 120 s walk/bike and 450 s drive, charged to selection cost. The constants are explicitly priors. |
| **10** | **CONFIRMED** | `add_travel_times` assigns the penalty inside the graph-edge loop. |
| **11** | **OVERSTATED** | The audit records three full restricted hops totalling approximately 159.5 m and 360 s of penalty on two OSM ways. “One OSM way” does not imply one graph edge: a single way crossing retained junctions can still incur three penalties. |
| **12** | **OVERSTATED** | Segmentation dependence is real, but arbitrary OSM geometry-node density is not the correct description. Degree-two nodes are simplified away. An executed example collapsed three same-way geometry segments to one penalised edge; adding junction branches retained three edges and 360 s of penalty on that same way. Origin partial-edge penalties are also prorated. |
| **13** | **OVERSTATED** | The calibration table measures a real, defined per-edge policy. Its results cannot be transferred unchanged to per-stretch pricing, but they do not measure a nonexistent quantity. The 1.10% figure is **UTM grocery/walk, 15-minute PASS buildings**. |
| **14** | **OVERSTATED** | The three definitions are useful. Per-stretch requires equivalent history state, but need not double every vertex. Calling it uniquely “faithful” is a behavioural assumption. A per-metre implementation also needs defined units, revised calibration and validation beyond a one-line edit. |
| **15** | **OVERSTATED** | The walked discrepancy establishes a failed estimate and evidence against the selected shortcut. It does not identify penalty magnitude as the sole cause. The observation remains usable evidence while the charging unit is being decided. |

A critical consequence of the owner’s leaning is that **keeping 120 s while switching to one charge per continuous run makes the audited three-edge shortcut cheaper**. Partition invariance and realistic route selection need separate validation.

**Decision 3 — Park destinations**

| Claim | Verdict | Evidence and correction |
|---|---|---|
| **16** | **CONFIRMED** | The builder takes centroids, finds nearest nodes and rejects distances above 300 m. In the current accepted park input, every centroid is the original point. |
| **17** | **OVERSTATED** | Seven of 746 **records** fail admission. They do not establish seven distinct parks absent from the layer. Dropped record #88 and another record #293 both match William B. Umstead State Park; the latter is retained. |
| **18** | **CONFIRMED** | Fresh measurement for #456: **356.44 m to the nearest node, 0.17 m to the nearest edge**. The node-admission problem is real. |
| **19** | **WRONG** | Matching origins’ 200 m cap recovers **five** dropped park records and loses four retained ones. Six recoveries require a **300 m edge cap**. Attachment geometry, admission distance and destination access semantics are separate choices. |
| **20** | **CONFIRMED** | The cited prior review records the subdivision experiment as **UTM park/walk**: 74,930 OK-cell changes and holes 125→134 after re-snapping. I did not rerun that expensive subdivision experiment. It demonstrates a side-effect-heavy counterfactual, not improved accuracy. |
| **21** | **WRONG** | The accepted parks are points, so “every park is measured to its middle” does not follow from this code. Routing ends at nearby nodes and omits destination access time. Its errors need not be conservative. The matched-polygon subset establishes substantial geometric cases, not that asserted mechanism. |
| **22** | **CONFIRMED** | A general destination-attachment replacement affects all seven criteria, as the explicit prototype demonstrates. Rebuilding and refreshing dependent statistics/disclosures is substantial work. Historical measurements remain valid descriptions of their original builds. |

**Decision 4 — Grey striping**

| Claim | Verdict | Evidence and correction |
|---|---|---|
| **23** | **CONFIRMED** | `worker.js` assigns UNKNOWN cells either grey or `PX_OUT`; `PX_OUT` is exactly the transparent value assigned to EXCLUDED. |
| **24** | **CONFIRMED** | Executed result, **published park/walk at 20 minutes**: 56,034 UNKNOWN; 14,023 painted; 42,011 transparent. |
| **25** | **CONFIRMED** | The same measurement gives 1,075 eight-connected regions, 369 wholly unmarked, covering 975 cells. Those cells are byte-identical to EXCLUDED in the mask image. Hover verdicts remain a separate channel. |
| **26** | **OVERSTATED** | The reported component-size percentages are reproduced. “The design works for the big ones” is not established by every large component containing some ink; scale, extent comprehension and visual interference remain untested. |
| **27** | **OVERSTATED** | The previous adequacy judgement was unsupported. The implementation still follows its deliberate rule. Evidence that the design is deliberate cannot establish that its disclosure is adequate. |
| **28** | **CONFIRMED** | I compared membership, not just counts: **zero OFF_NETWORK-set differences**, and zero UNKNOWN-set differences across all integer thresholds 1–60, at matched thresholds. Counts vary with threshold; different multi-criterion combinations can also change the combined mask. |
| **29** | **OVERSTATED** | The 56,036 count and 16.95% share are correct exported statuses. The distance classification belongs to sampled **UTM source centres**, not nominal published centres. A fresh audit found **3,615 exported OFF_NETWORK cells whose published centres are within 200 m**, and **3,716 other cells whose centres exceed 200 m**. “Road” also means retained mode-filtered graph here. |
| **30** | **CONFIRMED** | Presentation and model coverage are distinct intervention families with different costs and meanings. Shrinking coverage is not evidence that the remaining stripe design becomes satisfactory; changing the access cap also changes model assumptions. |

**Verdicts on the owner’s positions**

| Owner position | Verdict | Assessment and evidence that would move it |
|---|---|---|
| **1. “Measure first.”** | **SUPPORTED** | Actual wrong-hole prevalence remains unknown, and the proposed full-cap experiment changes access assumptions substantially. Support applies to a bounded access investigation. Existing comprehensive, independent journey verification could remove the need for another investigation; it is absent here. |
| **2. “Per stretch.”** | **SUPPORTED** | It removes dependence on graph segmentation, has measurable effects beyond the median route, and an exact state representation is affordable at this scale. This supports the charging unit, not 120 s or improved accuracy. Walked-route evidence showing that length or distinct access boundaries better predict usable routes would move the judgement. |
| **3. “We should never use a centroid…”** | **PREMATURE** | Avoiding an interior representative point for an entrance-distance product is sound. The current input does not contain park polygons, and a blanket centroid ban does not specify an accessible replacement. Matched park identities, credible entrance targets and published-grid comparisons are needed. |
| **4. Grey striping is problematic and should be rectified.** | **SUPPORTED** | This is an observed product-reading complaint, supported by scale-dependent texture and a demonstrated marking gap. The particular replacement remains unvalidated. A reading check should establish whether it distinguishes UNKNOWN, EXCLUDED and outside coverage at useful zooms. |

**Ranking by product risk retired**

My ranking is **Decision 2 → Decision 4 → Decision 3 → Decision 1**.

| Rank | Decision | Reason |
|---|---|---|
| **1** | Restricted-route charging and calibration | It connects directly to the demonstrated 13.5-versus-25-minute recommendation failure and affects route selection across all walk criteria. This rank requires resolving semantics **and validating usable journeys**; merely changing to per-stretch does not retire that risk. |
| **2** | UNKNOWN presentation | The owner has identified a reading failure, and transparent UNKNOWN pixels are demonstrated. A bounded presentation change can improve honesty without rebuilding routing. The 55-building invisible-region count limits the stronger prevalence claims. |
| **3** | Destination attachment and accessible park targets | The node-admission defect is demonstrated, and a general attachment change affects every criterion. Large-park access remains a credible risk, but the asserted polygon-centroid mechanism is wrong and entrance correctness needs investigation. |
| **4** | Isolated donut holes | The shape and occupied-cell exposure are established. Actual error prevalence is unknown, and broad candidate snapping changes many more journeys than the original holes. The investigation should remain bounded. |

Decision 4 is the cheapest clear product improvement among these. I would not infer that it retires the greatest recommendation risk from its 17% map-area share. Decision 2 has direct evidence of a materially misleading recommendation.

The original 1→2→3 presentation order is defensible as conversational order, but not as an execution priority under the plan.

**Execution evidence and limits**

Commands ran from `v2/`, using the requested interpreter.

```powershell
.\.venv\Scripts\python.exe -B scripts/measure_hatch_visibility.py
.\.venv\Scripts\python.exe -B scripts/measure_donut_holes.py
```

Selected hatch output:

```text
published grid 514 x 643 = 330,502 cells
park/walk:
limit UNKNOWN painted invisible blobs wholly-invisible cells-in-those
   5   38834    9756     29078   1077              370            977
  15   55752   13953     41799   1075              369            975
  20   56034   14023     42011   1075              369            975
  30   56036   14023     42013   1075              369            975
```

The candidate script was executed through `python -B -` from its source, with additional in-memory instrumentation for original-hole identity, published-grid mapping, cost-selected alternatives and state counts. Its unchanged diagnostic reproduced:

```text
UTM park/walk, full 200 m candidate cap
candidate pairs             8,010,516
improved >1 s                 210,533
share of comparable cells      77.13%
median improvement                 46 s
median winning access, >60 s      169 m
20-minute holes                125 -> 30
```

Additional stdin probes produced the route distributions, state benchmark, destination comparisons, geometry matching and independently binned building counts reported above. They did not persist surfaces or modify repository scripts.

The read-only test command was:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -o 'addopts=' `
  -p no:cacheprovider -p no:tmpdir -s `
  tests/test_admissible.py tests/test_two_weight.py `
  tests/test_cost_aware_snapping.py tests/test_status.py -q `
  -k 'not test_the_ingestion_refuses_a_sheet_that_cannot_produce_an_admissible_record and not test_the_ingestion_refuses_an_empty_sheet'
```

Result:

```text
135 passed, 2 deselected
```

Default pytest capture could not obtain a writable temporary directory. Disabling capture and temporary-file fixtures allowed the non-writing tests to run. The two excluded tests require file creation; no implementation change has been made that this run purports to validate.

The substantive findings that survive are the single-edge origin attachment mechanism, concentrated occupied holes, per-edge restricted penalties, the destination node-admission defect, and incomplete UNKNOWN marking. The principal corrections are the **net-versus-original repair count**, **200-versus-300 m destination cap**, **point-versus-polygon park input**, and **source-centre-versus-published-centre distance classification**.
