# How to rebuild the published criteria, and what each one is

**2026-11-16.** The published bundle held one criterion — grocery, on foot — from the day it was
first exported. The owner asked for a real househunt for the reading test
([[s3-13-reading-test]]), so it now holds seven. This note is the thing that was missing: the
command sequence that produces the bundle, in order, with what each step writes.

CLAUDE.md's rule is that anything needed to rebuild a published artifact is committed beside it.
Until now the sequence lived only in the heads of whoever last ran it.

## The seven criteria

| criterion | mode | target | destinations | opens on |
|---|---|---|---|---|
| Grocery shop, walk | walk | `grocery` | 510 nodes from 550 places | 20 min, **on** |
| Park, walk | walk | `park` | 723 nodes from 746 places | 15 min, off |
| School, walk | walk | `school` | 537 nodes from 559 places | 20 min, off |
| Grocery shop, drive | drive | `grocery` | 510 nodes from 550 places | 10 min, off |
| Coffee shop, bike | bike | `coffee` | *see build record* | 15 min, off |
| Duke University Hospital, drive | drive | `duke-hospital` | 1 point | 30 min, off |
| RDU airport, drive | drive | `rdu-airport` | 2 points | 40 min, off |

The last two are **named places**, not wedge categories. See below.

## The sequence, per layer

Run from `v2/`. `<target>` is a wedge category or a named-place slug; `<mode>` is `walk`, `bike`
or `drive`.

```
python spikes/g1_own_graph_layer.py <target> <mode>
python spikes/s2_building_weighted_coverage.py <target> <mode>
```

| step | writes |
|---|---|
| `g1_own_graph_layer` | `data/layers/own_triangle_<target>_<mode>.npy` (float32 seconds), `.tif` (uint8 minutes), `own_triangle_oneway-mask_<mode>.npy` |
| `s2_building_weighted_coverage` | `_reason.npy`, `_min_possible_s.npy`, `_build.json` — the surface triple the exporter reads |

Two more steps exist and are **grocery/walk only**, because both scripts hardcode `MODE`,
`CATEGORY` and `STEM` at module level:

```
python scripts/flag_restricted_routes.py --write-raster        # _restricted_route.npy
python scripts/persist_selected_destination.py --write-raster  # _selected_destination.npy + table
```

**A layer without them is not broken, it is quieter.** The wire format says an absent flag plane
means *this layer does not disclose*, which is a different statement from *no route is
restricted*, and the decoder reports the difference rather than defaulting to clean. The same
holds for the destination plane. So the six new criteria publish a time and a status and say
nothing about restricted routes or which park, school or shop the time was measured to.

**The destination plane is held back for a licence reason, not an effort one.** Parameterising
`persist_selected_destination.py` is mechanical. What it would publish is not. Counted on the
accepted-places frame:

| category | places | Apache-2.0 | CC0-1.0 | CDLA-Permissive-2.0 |
|---|---|---|---|---|
| grocery *(already shipped)* | 550 | 41 | 26 | 483 |
| park | 746 | **44** | 0 | 702 |
| school | 559 | **3** | 0 | 556 |
| coffee | 678 | **90** | 5 | 583 |

> **Both counts corrected 2026-11-16 after pass 56, which called this claim WRONG.** The table
> above counts the **accepted input**. What *ships* is what `persist_selected_destination.py`
> retains — the places on nodes a published answer actually selected. The shipped grocery table
> holds **35** Apache records, not 41; the manifest says so on its face
> (`"Apache-2.0": 35`) and counting the side table gives 35. And park, school and coffee would add
> **120** (39 + 2 + 79), not 137. Both reviewers found this; Gemini ran the selection to get 120.

That is **120 further Apache-licensed records**, against the 35 already shipped — more than
quadrupling them. The published manifest says on its own face
`"apache_records_are_cleared_for_redistribution": false`, because §4(b) is not discharged by
`ATTRIBUTION.md`, §4(c) needs an inventory of upstream notices nobody has made, and §4(d) needs a
readable copy of the source NOTICE that the shipped file says it is not. **Shipping three more
tables would multiply an exposure the bundle already declares it has not cleared.** The Apache
question is an owner decision and it is already on their list; until it is answered, the right
number of new place tables to publish is zero.

The route-flag plane carries no such problem — it is a bit per cell and names nothing — so that
one is held back only for effort, and is the cheaper of the two to add.

Finally, once:

```
python scripts/export_published_layers.py
```

It reads `SOURCES` in that file — a hardcoded list, not a directory scan — and skips any stem with
no `.npy` on disk. Add a layer there or the exporter will not see it.

## Named places

`locfinder/places/named_places.py` holds the registry. A slug there can be used anywhere a wedge
category can, because `select_target` dispatches on the name and both builders call it.

Two rules the registry enforces, with tests:

- **The slug is filename-safe.** It becomes the layer's `<target>` in every filename the build
  writes. The first design put the coordinate in the target string, which gives
  `own_triangle_at:-78.93,36.00_drive.tif` — a filename Windows cannot open.
- **Every point says where it came from.** A coordinate with no provenance is one somebody typed
  from memory, which is ledger instance 52 exactly.

Both current entries were chosen against the data rather than by name match, because Overture's
records for these two places are unreliable: it holds *JFK Airport New York* and *Fort Lauderdale
Int Airport* at RDU, and the whole Duke campus as per-department records (*Duke Pediatric Eye
Center*, *Duke Central Tower*) with no record that is the hospital. Duke comes from OSM way
305879102 via the Nominatim search API; RDU is the two terminal buildings, deliberately not the
aerodrome centroid, which lies inside the airfield where there is no road a household drives on.

`points` is a list because "the airport" is two terminals, not one door — and they carry one
label, so no consumer can answer "RDU Terminal 1" to a household who asked about the airport.

## The defect a real criteria set exposed

Pass 43 F4 recorded that **every manifest entry starts enabled in the page**. With one criterion
that was harmless. With seven it makes the opening view the **intersection of all seven** at seven
default minutes, and *drive to RDU in under 10 minutes* is empty from anywhere in Chapel Hill. A
household's first sight of the product would have been a blank map. `resetAll` had the same bug
one button press away: it set `checked = true` on every layer.

The manifest now carries `default_on` and `default_threshold_min` per layer. Both optional, both
absent-safe — a bundle publishing neither behaves exactly as before, so nothing already shipped
changes meaning. The two rules live in `card.js`, not `app.js`, because pass 51's two presentation
findings were both in logic that sat in `app.js` where nothing could reach it; `card_selftest.mjs`
now checks them, including one check that reads the **shipped** manifest and fails if more than one
criterion opens switched on.

**No test in the suite could have caught this.** Every one of them checks a layer, a message or a
sentence; this was a property of the *set*. It was found by preparing the reading test, which is
the argument for the reading test in miniature.

## The second one: the card named criteria by their layer id

Found by hovering **one cell** on the built page. The card read:

```
own_triangle_grocery_walk        FAIL   22 min, your limit 20 min
own_triangle_duke-hospital_drive PASS   20 min, your limit 30 min
```

The manifest has carried a `label` for every layer since it was first written — *Duke University
Hospital, drive* — and the card had never used it. With one criterion this was a single ugly line
nobody looked at twice. With four switched on it is most of the text on the card, and
`own_triangle_duke-hospital_drive` is not something a person who did not build this can read.

The worker now sends `label` beside `layer`, so the id stays available to anything that needs to
identify a layer, and the card prints the label and falls back to the id — a bundle that publishes
no label must still render a name rather than the word `undefined`. Three checks and two
mutations, one for each direction.

## `NO_PATH` ships for the first time

The drive and bike layers produce a status no published layer has ever carried: **57 cells per
drive layer and 95 in the bike layer** on the 330,502-cell UTM surface, 39 and 80 after
reprojection. The drive figure is identical across all three drive layers, which is what you would
expect — a node with no directed path out has none to any destination set.

They sit in several small groups, the largest 19 cells near 35.87659/-79.20377 at the western edge
of the grid. A one-way road cut by the clip boundary would produce exactly this, and that
mechanism is **plausible, not established**: nobody has traced one of these cells.

This falsified a sentence in [[project-phase1-s0-complete]] that said `NO_PATH` was unreachable in
every shipped configuration. See ledger instance 53. One consequence worth noting for the reading
test: the card's `NO_PATH` wording — *"no route to anywhere qualifying exists in the map we
hold"* — has existed all along and **had never once rendered from a real published layer** until
now.

## What this build does not establish

- **Nothing re-measured the slider budget.** Gate G3 is a median slider-to-repaint under 100 ms,
  measured on a one-layer bundle. A compute now evaluates up to seven layers over 330,502 cells
  each. The opening case is one enabled criterion and is unchanged; the all-on case is new and
  unmeasured. It is still an owner item, because it must be measured with the window **on screen**:
  a background tab is throttled by the browser and the number would be meaningless.

  **How to take it** (written out 2026-11-17, because "one click of Auto-bench" left out the step
  that matters):

  1. Serve the spike and open it: from `v2/spikes/g3-render`,
     `python -m http.server 8099 --bind 127.0.0.1`, then <http://localhost:8099/>.
  2. **Tick all seven criterion checkboxes.** This is the step that is easy to miss. Auto-bench
     moves each layer's slider in turn, but the worker only evaluates **enabled** layers, so
     clicking it on the opening view measures the one-layer case we already have.
  3. Leave the window visible and in the foreground. Do not switch tabs while it runs.
  4. Click **Auto-bench**. It performs 20 scripted slider changes, waiting for each repaint before
     starting the next, and logs `auto-bench: finished 20 of 20 scripted changes`. If it stops
     early, the number in that line is how many actually completed and the medians describe only
     those.
  5. Read the **Timings** panel: *Slider -> repaint, total (last / median)* is the gate. *Worker
     compute* and *Transfer + paint* beside it say which half any overage is in.

  Report the median, not the last. The panel's median is over the last 20 changes, which is exactly
  what Auto-bench produces.
- **Nothing checked the park destinations are places you can enter.** **Corrected 2026-11-16,
  pass 57 — the sentence that stood here was wrong.** It said a park is a polygon whose centroid
  the builder snaps. It is not: **all 746 accepted park records are `Point` geometries, and 0 are
  polygons**, so the `.centroid` call in `g1_own_graph_layer.py` is a **no-op** and returns the
  input point unchanged. Both reviewers caught it independently and I reproduced it
  (`centroid == geometry` is `True` for all 107,484 accepted places).

  The real defect is **larger** than the one that was written here, and differently shaped. A park
  is represented by **one Overture point**, placed wherever Overture put it, and the route then ends
  at a nearby graph **node** with **no destination access time at all**. So the model's answer is
  not "to the middle of the park"; it is "to one arbitrary point associated with the park, plus
  nothing". Its errors are **not guaranteed to be conservative**, which the old sentence implied.

  Also corrected: **7 of 746 is a count of records, not of parks.** Dropped record #88 and
  **retained** record #293 both match William B. Umstead State Park, so at least one "missing" park
  is in the layer under another record. The admission bound is a **node** bound: record #456 is
  **356.44 m from the nearest node and 0.17 m from the nearest edge**.

  How much this costs is **measured but disputed**, and is the live question in
  [[project-phase1-s3-destination-identity]]. It remains a modelling choice nobody has priced and a
  good thing for a local reader to catch.
- **Nothing checked school catchment.** Walking distance to a school is not how a household with
  children is assigned one. The criterion answers the question it is named for and that question
  may not be the one a parent is asking — also a thing to watch for in the reading test.

Related: [[project-phase1-s3-progress]], [[s3-13-reading-test]],
[[project-phase1-s3-soft-way-dependence]].
