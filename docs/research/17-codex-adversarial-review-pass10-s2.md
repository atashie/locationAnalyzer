# Pass 10: adversarial review of S2.1 and S2.2

Reviewed 2026-11-04. Report only; no production code, tests, or experiment records changed. No Critical finding established. High findings below invalidate silent resolution and cache-provenance guarantees. The directed reachability implementation survives; its claimed benefit on the twelve anchors does not.

## Method and reproducibility

Ran from `v2/`, against the populated Triangle and slice artifacts, without Valhalla or MOTIS. The ordinary `uv run pytest` failed because the sandbox cannot access the default uv cache. The equivalent command with a workspace cache succeeded:

```powershell
uv --cache-dir data/.uv-cache run --no-sync pytest
```

Actual output:

```text
235 passed, 1 warning in 2.72s
```

The warning concerns permission to write pytest's existing cache. The prompt's 233-test count is stale. Tests passing did not prevent the failures below.

The complete review-only driver is embedded at the end of this report. Save that block as `v2/data/pass10_review.py` to reproduce these commands. It reads the real artifacts; its `state` test mocks both file storage and the downloader and never touches a real download. `resolver` changes scoring globals only inside its own process. Logs were captured under ignored `v2/data/`; relevant real output is pasted below. Output excerpts explicitly omit unrelated candidates. External pages were consulted to establish entity identity, not to validate routing or make licensing determinations.

## High H1 — Two of the seven confident answers are the wrong entity

**Claim:** 10/10 queries produce candidates, seven confidently resolve; the metro bound addresses the earlier wrong-place failures.

**Defect:** Bounding avoids another state but does not establish the intended entity. Exact names for tenants and transit stops beat the actual mall/hospital. `category` is never used in ranking, and OSM transport tags are lost in `Place.category` because `from_osm` considers neither `highway` nor `public_transport` nor `railway`.

Executed:

```powershell
uv --cache-dir data/.uv-cache run --no-sync python data/pass10_review.py resolver
uv --cache-dir data/.uv-cache run --no-sync python -c "import geopandas as g; x=g.read_parquet('data/triangle/osm_pois.parquet'); print(x.loc[['node/6509747409','node/7024572472']].dropna(axis=1,how='all').to_string())"
```

Real output excerpts from the first command (fields are name, source id, score, locality, category, address, lon/lat, locality-match):

```text
INDEX 96585
Southpoint ["resolved", [["Southpoint", "650b1aeb-5966-4028-8011-d72aefddb771", 1.0, "Durham", "dessert_shop", "8128 Renaissance Pkwy, Ste 113, Durham, North Carolina 27713", [-78.952858, 35.903352], false], ...]]
Duke Hospital ["resolved", [["Duke Hospital", "node/6509747409", 1.0, null, null, null, [-78.9375, 36.007633], false], ...]]
MALL_RANKS [(15, 'Southpoint Hotel', 0.725, 'shopping_mall'), (16, 'Southpoint Mall', 0.725, 'shopping_mall'), (76, 'The Streets At Southpoint', 0.6375, 'shopping_mall')]
```

The second command shows `node/6509747409`: `bus=yes`, `highway=bus_stop`, `public_transport=platform`, `network=Duke`, `ref=12114`. It is a bus platform at the hospital, not the hospital entity. Its geographic proximity makes this less serious than Southpoint, but a hospital resolved to a platform is not identity correctness.

Seven-answer audit (coordinates are **longitude, latitude**):

| Query | Selected location/category | Identity assessment |
|---|---|---|
| Whole Foods, Chapel Hill NC | -79.028054, 35.934640; supermarket; 81 South Elliot Road | Correct store. [Official store page](https://www.wholefoodsmarket.com/stores/chapelhill) confirms address. |
| Whole Foods Durham | -78.920556, 36.007099; supermarket; 621 Broad Street | Correct store. [Official store page](https://www.wholefoodsmarket.com/stores/durham) confirms address. |
| Harris Teeter Carrboro | -79.070958, 35.912353; supermarket; 310 North Greensboro Street | Correct store. [Official store page](https://www.harristeeter.com/stores/grocery/nc/carrboro/carr-mill/097/00297) confirms address. |
| Duke Hospital | -78.937500, 36.007633; category omitted | Wrong entity: bus platform. Spatially at the intended hospital, so an evaluation accepting any point at the hospital could count this as a location success. |
| Fidelity Investments Durham NC | -78.939432, 35.901147; broker; 7011 Fayetteville Road Suite 110 | Real Durham investor center, verified by [Fidelity](https://www.fidelity.com/branches/investor-center-durham-north-carolina-27713). Correct for a branch visit; not established for a workplace commute. The index also contains the corporate office at 100 New Millennium Way (-78.859048, 35.885799), and [Fidelity's own employment posting](https://fmr.wd1.myworkdayjobs.com/FidelityCareers/job/100-New-Millennium-Way-Bldg-2-Durham-NC/Senior-Litigation-Support-Analyst_2134812) confirms that work location. |
| Southpoint | -78.952858, 35.903352; dessert shop | Wrong for the mall. [Crumbl's own Southpoint page](https://crumblcookies.com/stores/nc/ncsouthpoint) confirms this exact tenant address. The [mall's official address](https://www.streetsatsouthpoint.com/en/visit/) is 6910 Fayetteville Road; the index contains it. |
| Carrboro Farmers Market | -79.077212, 35.910986; farmers market; 301 W Main Street | Correct venue. [Market's own contact page](https://www.carrborofarmersmarket.com/contact-us) confirms address. |

**Count:** four unqualified intended-entity successes, two wrong entities, one intent-dependent result. Five of seven select a verified real facility matching the literal query if Fidelity means the investor center. Counting the Duke platform as a nearby location would raise that broader spatial count to six, but would change the correctness criterion. Seven correct intended anchors is unsupported. The ten queries do still produce candidates and the outcomes remain seven resolved/three ambiguous: those narrow counts reproduce.

**Smallest correct fix:** Preserve feature type and distinguish facilities, tenants, and transport stops. Require selection when plausible entity types compete or the query does not distinguish a corporate workplace from a retail branch. Add asserted expected source identities/types to real-data fixtures. Merely raising the ambiguity margin or preferring OSM cannot identify the mall or the hospital.

## High H2 — Leading locality confidently resolves a grocery query to a railway station

**Claim:** Typed locality ranks candidates; all query words still describe the requested place.

**Defect:** Only trailing localities are stripped. The subset branch gives a one-word name a fixed 0.85 regardless of how much of the query it ignores. The real intended supermarket scores 0.30 and is discarded at the floor of 0.45.

Executed `... python data/pass10_review.py resolver`, actual output excerpts:

```text
Durham Whole Foods ["resolved", [["Durham", "node/7024572472", 0.85, null, null, null, [-78.906464, 35.997532], false], ["Amazon Hub Counter+ (durham - Whole Foods)", "4a104e2a-24de-44d9-8cd3-c90c3795030e", 0.725, "Durham", "package_locker", "621 Broad St", [-78.92063, 36.006993], false]]]
the Whole Foods in Durham ["not_found", []]
Carrboro Farmers Market Carrboro ["resolved", [["Carrboro Farmers Market", "19670ccb-d010-459a-999d-1bbc2b2b4023", 1.0, "Carrboro", "farmers_market", "301 W Main St", [-79.077212, 35.910986], true]]]
```

Raw OSM inspection from H1 identifies `node/7024572472` as `railway=station`, `operator=Amtrak`, `public_transport=station`, `railway:ref=DNC`. This is not a theoretical parser weakness.

**Smallest correct fix:** Recognize locality prefix/suffix and common connective forms without deleting words that belong to the actual entity name. Score remaining required name tokens; do not promote a candidate solely because its name is a subset of a long query. Carrboro Farmers Market itself survives both the original query and the explicit trailing-town variant, so that example is not a demonstrated failure.

## High H3 — Presentation limit changes truth from ambiguous to resolved

**Claim:** Ambiguity is surfaced, never silently resolved.

**Defect:** `resolve` applies `[:limit]` before `_decide`. Two equally good, distant same-name shops become a single confident answer at `limit=1`; `limit=0` reports `not_found` despite matches. Eight can hide the right answer even without changing the binary outcome: the real Southpoint mall ranks 16 and its longer official name ranks 76.

Executed:

```powershell
uv --cache-dir data/.uv-cache run --no-sync python data/pass10_review.py synthetic
```

Actual output excerpts:

```text
LIMIT 0 ['not_found', []]
LIMIT 1 ['resolved', [['Shop', 'a', 1.0, None, None, None, [-79.0, 35.9], False]]]
LIMIT 2 ['ambiguous', [['Shop', 'a', 1.0, None, None, None, [-79.0, 35.9], False], ['Shop', 'b', 1.0, None, None, None, [-78.9, 35.9], False]]]
```

**Smallest correct fix:** Decide against the complete merged ranking, then limit presentation. Validate positive limits and carry pagination/omission information so users can reach candidates beyond the initial list. For the ordinary top-two margin check, limits of at least two do preserve that decision; I did not find an eight-versus-nine binary flip in that branch.

## High H4 — Corroboration merges different entities, including within one source

**Claim:** Same normalized name within 60 m means one place in two sources.

**Defect:** `_merge_corroborating` checks neither source difference nor category, unit, address, or native identity. A bank and its ATM 9 m apart, both called Acme and both OSM records, collapse to the ATM. The ambiguity disappears. OSM preference can also discard an Overture facility point for a same-name adjacent feature without establishing that their identities agree.

Executed the `synthetic` command above. Actual output:

```text
MERGE_DISTINCT ['resolved', [['Acme', 'atm', 1.0, None, 'atm', None, [-79.0001, 35.9], False]]]
```

The fixture supplies two separate source ids, categories `bank` and `atm`, and no alias relationship. This is an executed synthetic false merge, not a claim that this particular pair occurs in the downloaded data. Same-name branches inside one mall or campus have the same vulnerability. A surveyed OSM record is not necessarily a better entrance/anchor than an Overture record; no such geometry-quality comparison exists here.

**Smallest correct fix:** Keep distinct native entities unless cross-source identity evidence supports merging; at least require different sources and compatible feature types/units. Preserve both records and their geometry/provenance until a canonical anchor is justified. For runtime, the nested scan is indeed quadratic in the number of scored candidates, even for candidates with different names. Grouping by normalized name before spatial comparison removes that unnecessary cross-name work; a spatial index addresses large same-name groups. No production latency failure was measured, so complexity alone is not a separate severity finding.

## High H5 — Interrupted buildings download can leave the wrong release/bbox under a valid old state

**Claim:** `fetch_raw` cannot silently relabel a raw download fetched for another release or bbox.

**Defect:** Download writes directly over `raw`, while the previous state remains valid until the subprocess succeeds. If B overwrites A and fails or is interrupted, state A survives alongside B's bytes. A subsequent request for A reuses those bytes. This applies to a changed bbox as well as a changed release. It can result in an obvious invalid-Parquet error, but a complete B file followed by failure before state write can instead be accepted and labeled A by `main`.

Executed with a downloader that overwrites bytes and raises, and an in-memory filesystem preserving the exact state transitions:

```powershell
uv --cache-dir data/.uv-cache run --no-sync python data/pass10_review.py state
```

Actual output (interpreter path shortened):

```text
re-downloading: pass10_mock_raw.parquet was fetched for A / bboxA, not B / bboxB
running: ...python.exe -m overturemaps.cli download --bbox=bboxB -f geoparquet --type=building -o data\pass10_mock_raw.parquet --release B
download B interrupted
reusing pass10_mock_raw.parquet: same release and bbox
requested A; actual: partial release-B bytes ; subprocess called: False
```

**Smallest correct fix:** Invalidate the old state before any in-place write, or download to a separate temporary file and commit raw/state with a failure-safe protocol. Do not leave a usable old state between replacing raw and committing its new metadata; bind metadata to raw content if independently replaced files must be detected. Happy-path matching/mismatching release and bbox checks are correct; they do not cover interruption.

## Medium M1 — Locality uniqueness is tested only against the second candidate

**Claim:** Exactly one candidate in the leading tier matches the locality.

**Defect:** `_decide` checks only `lead.locality_match and not second.locality_match`. A third candidate can match locality and be within the ambiguity margin. Score sorts ahead of locality, so it need not be second.

Executed `synthetic`; actual output:

```text
LOCAL_UNIQUE ['resolved', [['Acme', 'a', 1.0, 'Durham', None, None, [-79.0, 35.9], True], ['Acme', 'b', 1.0, 'Raleigh', None, None, [-78.9, 35.9], False], ['Acme Office', 'c', 0.95, 'Durham', None, None, [-78.8, 35.9], True]]]
LOCAL_WORSE ['resolved', [['Acme', 'a', 1.0, 'Raleigh', None, None, [-79.0, 35.9], False], ['Acme Office', 'b', 0.725, 'Durham', None, None, [-78.8, 35.9], True]]]
```

**Smallest correct fix:** Define the leading score tier explicitly and count every locality-matching candidate within it before deciding, independently of presentation limits. The second result also corrects the premise of attack 3: a much worse locality match does **not** displace a better nonlocal name match. Name score sorts first. Whether an explicit locality should instead require confirmation of a conflicting leader is a product policy decision; claiming the current code selects any sole locality match would be inaccurate.

## Medium M2 — The measured “once, at UNC Hospitals” is stale and the measurement still counts the wrong thing

**Claim:** Directed filtering changed the chosen node once among twelve anchors; UNC Hospitals had an unreachable node nearer than the selected node.

**Defect:** The previously fixed `nudged` predicate is correct, but `AnchorFix.rejected_unreachable` still counts **all** unreachable nodes in the radius. `s2_anchor_routability.py` uses that field (`rejected_any`) as a proxy for a nearer rejection and a changed chosen node. The spike will continue publishing the false “once” conclusion even with the corrected `status`.

Executed:

```powershell
uv --cache-dir data/.uv-cache run --no-sync python data/pass10_review.py graph
```

Actual Triangle output:

```text
GRAPH triangle kept 437615 unreachable 143 core 437298
INDEPENDENT_BFS triangle unreachable 143
ANCHOR UNC Hospitals nearest3 [(37.15238376476165, 181204, True), (49.85872131922849, 181202, True), (52.289092461801104, 181203, True)] selected ['ok', 181204, 37.152, 1, False] ...
ACTUAL_CHANGED []
```

The independent check uses `networkx.descendants` from a core node, not the SCC condensation implementation. For each anchor the driver sorts every node in the geometry-derived coordinate map and compares the chosen node with the nearest. All twelve choose the nearest node: **zero** directed/barrier selection changes; all twelve are `ok`, none `nudged`. The 143 / 437,615 = 0.0327% count survives. This does not invalidate the usefulness of directed filtering elsewhere.

**Smallest correct fix:** Measure chosen-node changes against a control with the reachability mask disabled, holding the graph and barriers fixed; separately record counts of *nearer* unreachable nodes. Correct the plan and appended results. Do not repurpose a total rejection count as a causal change count.

## Medium M3 — The new `node_too_far` fix uses bounding-box overlap as proof of nearby road

**Claim:** `node_too_far` means a road is inside the cap but its junctions are outside.

**Defect:** `STRtree.query(buffer)` without a predicate only compares envelopes. An edge with envelope overlap but true distance 197.99 m is reported as a road within a 150 m cap. The same issue can make the reported nearest-junction distance refer to a road outside the cap.

Executed `synthetic`; actual output:

```text
FALSE_ROAD_WITHIN_CAP node_too_far true_road_distance 197.99
```

The line runs from (140,140) to (300,300), anchor (0,0), default cap 150. It should be `off_network`.

**Smallest correct fix:** Filter tree hits by exact point-to-line distance `<= max_nudge_m` (or a suitable distance predicate). Keep the new status for genuinely nearby long edges. The supplied long-edge and farther-unreachable-node regression tests pass; this is a boundary failure of the first fix, not a repeat of the already addressed node limitation.

## Medium M4 — Valid Arrow common-name maps are silently dropped

**Claim:** `names.common` is a language map and its values become aliases.

**Defect:** The release schema is indeed `map<string,string>`, but its Pandas representation is normally a list of key/value tuples. `_common_names` accepts only `dict`. The current 90,349 accepted rows have zero non-null common-name maps, so this is not the cause of the observed RTP failure, but the loader contract fails on a valid non-empty value of that schema.

Executed:

```powershell
uv --cache-dir data/.uv-cache run --no-sync python -c "import pyarrow as a; from locfinder.places.resolve import _common_names; t=a.table({'names':a.array([{'primary':'Example','common':{'en':'Alias'}}],type=a.struct([('primary',a.string()),('common',a.map_(a.string(),a.string()))]))}); n=t.to_pandas().iloc[0]['names']; print(repr(n)); print('aliases:',_common_names(n))"
```

Actual output:

```text
{'primary': 'Example', 'common': [('en', 'Alias')]}
aliases: []
```

**Smallest correct fix:** Normalize both mapping and Arrow/Pandas key/value-sequence forms, validating values and nulls. Test through Arrow conversion rather than only a handwritten Python dictionary.

## Medium M5 — A nullable address can abort the entire index build

**Claim:** Loaders handle missing fields.

**Defect:** `from_overture` calls `len(addrs)` whenever `addrs is not None`. A NaN scalar raises. Separately, `_first` turns `pandas.NA` into the literal name `<NA>`; it filters only strings `nan` and `none`.

Executed `synthetic`; actual output:

```text
LOAD_ADDRESSES None 1
LOAD_ADDRESSES nan TypeError object of type 'float' has no len()
LOAD_PD_NA [('<NA>', '0')]
```

**Smallest correct fix:** Validate list-like nested containers before indexing/length checks, and explicitly recognize scalar missing values. Do not use a blanket `pd.isna` Boolean on array fields. These are synthetic nullable-frame cases; loading the current real frames succeeds. Missing names, unknown identities and nonfinite coordinates deserve explicit handling, not synthesized string identifiers.

## Medium M6 — Routing-bound resolver has evaluation-only Overture acquisition

**Claim:** Routing bbox is the honest place-search extent because a workplace can lie outside evaluation.

**Defect:** This is a sensible search policy, but `fetch_places.py:121–125` downloads Overture for **evaluation**, not routing. The raw state confirms `(-79.2,35.7,-78.5,36.15)` rather than routing `(-79.35,35.55,-78.35,36.30)`. Widening the loader's bound cannot restore places never fetched. OSM comes from the routing extract, making coverage differ by source.

Executed `resolver`, and read `data/triangle/overture_places_raw.parquet.state`:

```text
OUTSIDE_EVAL 593
OUTSIDE_BY_SOURCE {'osm': 593, 'overture': 0}
```

**Smallest correct fix:** Acquire the routing extent for the anchor index, or explicitly declare evaluation-only Overture coverage and offer correction outside it. Keep evaluation filtering separately for category destinations/coverage audits when appropriate. A destination outside evaluation is not itself a routing error: arrival search accepts destination node indices independent of output-grid extent. The remaining edge-of-extract risk is routes leaving the loaded routing area; the bbox alone is not a path-completeness guarantee. I did not run live-engine outside-evaluation routes, so that broader completeness claim is not validated.

## Low L1 — First endpoint wins can change cap/barrier decisions by edge order

**Claim:** `node_coordinates` gives stable node locations even when expansion endpoints share a 0.5 m bucket.

**Defect:** Two endpoints at +0.2 and -0.2 m map to the same expansion bucket, while `setdefault` takes whichever is first. The coordinate difference is small, but can cross a cap threshold or a barrier. Reversing the two physical-edge rows changes the answer without changing connectivity.

Executed `synthetic`; actual output:

```text
NODE_COORDS {0: (0.2, 0.0), 1: (100.0, 0.0)}
ENDPOINT_ORDER forward cap1 node_too_far barrier2 True moved 1.2
ENDPOINT_ORDER reversed cap1 ok barrier2 False moved 0.8
```

**Smallest correct fix:** Use one canonical coordinate per graph node at construction and propagate it; define tolerance for barriers/cap boundaries consistently. A same-key discrepancy can approach sqrt(2) × 0.5 m, not necessarily at most 0.5 m. On the actual OSM-based Triangle and slice edge indexes I checked every endpoint and found **zero** discrepancies (`ENDPOINT_DISAGREEMENTS ... 0 0`). Thus this is a demonstrated synthetic expansion-compatible boundary sensitivity, not a measured large real-anchor error.

## Claims that survived, and limits of those conclusions

### Reachability direction (attack 9)

Executed `synthetic` on edges `0↔1`, `1→2` (sink), `3→0` (source). Actual output:

```text
DIRECTION [True, True, True, False] arrival_to_sink [2.0, 1.0, 0.0, 3.0] arrival_to_source [inf, inf, inf, 0.0]
```

`CoreReachability` correctly accepts the sink and rejects the source. `arrival_seconds` transposes the original graph and gives finite core-to-sink times but infinite core-to-source times. Testing anchor→core would accept node 3, which those arrival results prove is wrong. Both SCC condensation and an independent forward traversal agree on 143 inaccessible Triangle nodes. No direction defect found.

### RDU (attack 11)

The `graph` command independently produced:

```text
BEFORE triangle nearest 13602873720 69.1328270751796 weak_size 4
RDU triangle [(74.353, 6312045600, True), (121.853, 6312045603, True), (125.096, 195419057, True), (136.038, 1210724011, True), (137.728, 6319182039, True), (143.657, 1957889047, True)]
BEFORE slice nearest 13602873720 69.1328270751796 weak_size 4
GRAPH slice kept 201700 unreachable 155 core 201391
INDEPENDENT_BFS slice unreachable 155
RDU slice [(74.353, 6312045600, True), (121.853, 6312045603, True), (125.096, 195419057, True), (136.038, 1210724011, True), (137.728, 6319182039, True), (143.657, 1957889047, True)]
```

Thus all six **retained-graph** candidates within 150 m are core-reachable, in both metros. The unpruned graph has nearer candidates excluded by weak pruning; “all nodes within 150 m” must retain that qualification.

Executed an additional ablation, inspecting raw slice geometry before filtering and component membership immediately after mode filtering:

```powershell
uv --cache-dir data/.uv-cache run --no-sync python data/pass10_review.py rdu_history
```

Actual output excerpts:

```text
RAW_NEAREST [(69.1328270751796, 13602873720), (74.35310075753763, 6312045600), (95.0992731642343, 13602873718), (119.49731258842081, 8541305922), (119.93199875990503, 1957871726), (121.85305004008494, 6312045603)]
AFTER_MODE 13602873720 69.133 degree 2 weak_size 4
AFTER_MODE 6312045600 74.353 degree 6 weak_size 201700
AFTER_MODE 13602873718 95.099 degree 6 weak_size 4
```

Removing degree-zero nodes cannot remove that nearer four-node stub: it has nonzero degree. Weak-component pruning does remove it and leaves the 74.353 m node. That establishes pruning's causal role on current artifacts. **The historical 4 m snap itself cannot be reproduced from these files:** even the raw graph's nearest node is 69.133 m away. I do not certify that the historical run used identical source geometry/coordinates/profile, or attribute its exact numbers solely to pruning without its original inputs. The current six-node claim survives; the historical-distance narrative remains insufficiently reproduced.

### Barrier ranking and 150 m cap (attacks 12–13)

Real RDU output selects the nearest reachable node at 74.353 m with `crossed_barrier=True`. All twelve real selections agree with global nearest-node choices. I inspected `_crosses_barrier`, the fallback branch and the existing clear-versus-fenced tests. The implementation ranks **zero intersections versus any intersections**, not the number of fences: if every reachable candidate crosses something, a nearer candidate crossing three barriers beats a farther one crossing one. That is the stated Boolean policy, not an implementation mistake.

Fallback can be worse than failure at a genuinely inaccessible enclosed site: reachability proves a path to the road node, not a lawful connector from that node to the POI. Conversely, a straight-line veto rejects legitimate perimeter sites. The existing plan explicitly calls the connector unvalidated. Keeping an uncertainty flag plus requiring a real entrance/connector before claiming lawful access is defensible; asserting `usable` proves lawful access is not. Excluding kerbs/guard rails/ditches is a heuristic, especially weak for driving, but adding all of them as vetoes would not establish lawful driving access either. I did not independently extract each excluded barrier class or measure mode-specific false positives, so no numerical safety claim for that exclusion is validated. Endpoint contact counts as intersection, not just a transverse crossing. This remains a ranking heuristic, not an approach-path test.

Executed caps 25, 50, 75, 100, 150 and 200 m on every real anchor with the real barriers. Results:

| Cap | Usable anchors | Selection effect |
|---|---|---|
| 25 m | 5/12 | Carrboro Town Hall, Franklin Street, NC State Bell Tower, Moore Square, Cary only |
| 50 m | 9/12 | Duke University Hospital, RTP, RDU still fail |
| 75 m | 11/12 | Duke University Hospital still fails (nearest 77.607 m) |
| 100 m | 12/12 | Same selected nodes as 150 m |
| 150 m | 12/12 | Baseline; none nudged |
| 200 m | 12/12 | Same selected nodes as 150 m |

Actual output example:

```text
ANCHOR Duke University Hospital nearest3 [(77.60664602233433, 141099, True), (89.67097820405716, 197799, True), (93.23885920868845, 141101, True)] selected ['ok', 141099, 77.607, 0, False] caps [(25, 'node_too_far', 77.61), (50, 'node_too_far', 77.61), (75, 'node_too_far', 77.61), (100, 'ok', 77.61), (150, 'ok', 77.61), (200, 'ok', 77.61)]
```

150 m is a real acceptance bound, but the twelve cases do not distinguish it from 100 or 200 m. No empirical optimum established. Changing the cap can also add a farther clear candidate and replace a nearer barrier-crossing one, so acceptance/selection is not solely a distance-threshold question.

### Score constants and area gap (attacks 2 and 8)

The constants do real work, but are not calibrated confidence probabilities. Executed `resolver` sweep:

```text
MARGIN 0.02 [('Southpoint', 'resolved'), ('Duke Hospital', 'resolved'), ('NC State', 'resolved')]
MARGIN 0.08 [('Southpoint', 'resolved'), ('Duke Hospital', 'resolved'), ('NC State', 'resolved')]
MARGIN 0.15 [('Southpoint', 'resolved'), ('Duke Hospital', 'resolved'), ('NC State', 'ambiguous')]
MARGIN 0.3 [('Southpoint', 'ambiguous'), ('Duke Hospital', 'ambiguous'), ('NC State', 'ambiguous')]
```

The current margin accepts Southpoint's wrong dessert-shop answer; a larger margin surfaces uncertainty but does not fix ranking. At floor 0.30 the real Whole Foods stores reappear for `Durham Whole Foods` at score 0.30, while the station still wins at 0.85. At 0.45 and 0.50 the stores disappear. The containment formula penalizes longer official names: Southpoint Mall gets 0.725, The Streets At Southpoint 0.6375, versus the tenant's exact 1.0. These measured failures justify semantic/type evidence and held-out labeled queries, not replacing arbitrary constants with different arbitrary constants. `>=` also means a difference **exactly** 0.08 resolves, despite prose saying “within” the margin is ambiguous; boundary wording should be precise.

The current index has **no RTP alias** and exactly **35 names containing Research Triangle Park**. The stronger assertion that all 35 are businesses situated in it does **not** survive inspection of the source records. The extracted rows include these two park-classified records, with no street address:

| Native Overture id | Name | Category | Longitude, latitude |
|---|---|---|---|
| `aae36152-d2ea-414b-9052-8c7724c61ed9` | Research Triangle Park | park | -78.8617462, 35.9080578 |
| `698e5fb5-ce6f-4e32-944d-ed2d2fcb6c69` | Research Triangle Park, Durham, North Carolina | park | -78.8737067976, 35.9004517115 |

Neither has an RTP alias. These are points rather than a verified area/entrance model, and source category alone does not prove physical identity: several other downloaded categories are plainly noisy. I therefore do **not** certify either point as the right general-purpose anchor. But the claim that an area cannot be represented anywhere in this POI index is not established, and adding an alias/canonical-entity mapping could change RTP candidate generation without acquiring a new area polygon. The report's driver prints the full raw matching records so this distinction is inspectable.

`RTP` currently produces businesses such as Aventura RTP and Boulevard RTP. `downtown Raleigh` returns Downtown Glenwood, Downtown Psychology and Downtown Radiator; `Duke campus` returns Duke Campus Club and Duke Campus Farm as leaders. These support a missing area-intent/index path, while also exposing ranking and alias gaps. A verified area model remains a sound improvement; “coverage, not scoring” is too categorical for the actual payload.

However, the blanket claim that campuses are simply absent is too strong: the raw matching rows include 30 names containing North Carolina State University and 150 containing Duke University, with university/school records among much unrelated material. `NC State` confidently returns an Overture `college_university` point at **(-78.699642,35.754641)**, while other institutional candidates exist. I have not established that point's precise physical role and do **not** certify it as the university's correct general-purpose anchor. `Duke campus` has campus-named records lower down. An explicit area layer with canonical identities/aliases/entrances is still appropriate, but ranking and entity disambiguation also need repair. For Southpoint the **mall is already present**: that specific failure is scoring/entity selection, not lack of coverage. Southpoint as a district remains an area-intent question.

### Loader bounds, polygons and licensing (attacks 6, 7 and 15)

Read both loader calls and `BBox.contains(lat, lon)`; argument order is correct. Both use `representative_point`, an interior point for polygons, not a guaranteed entrance. Metro clipping tests that point, not geometric overlap. This can exclude a partly overlapping polygon or anchor a large site away from its legal entrance; I did not execute a real polygon-boundary false exclusion, so that effect is not a validated real-data defect. `None`/empty geometry is skipped. The NaN/container and Arrow-map failures are separately reproduced above.

Scoping of the widened license set survives review. Executed `rg -n 'resolve_licence|DIAGNOSTIC_LICENCES' v2`: only the buildings production caller passes `allowed=DIAGNOSTIC_LICENCES`; the places caller keeps the strict default. The sets are immutable and the union does not mutate `ALLOWED_LICENCES`. This is caller scoping, not a security boundary: another future caller could explicitly import/pass that set. There is no current implicit path widening places acceptance.

Executed the manifest allowlist check in `synthetic`:

```text
LICENCE None UnknownLicence
LICENCE frozenset({'ODbL-1.0'}) ODbL-1.0
```

The fixture's missing explicit license resolves through a manifest to ODbL; default correctly rejects, explicit diagnostic allowance accepts. Existing tests also verify the strict default still rejects after a widened call. Every source entry is checked; returning the primary license does not bypass secondary-source validation. I accept the owner's diagnostic-use decision as supplied; this report makes no independent legal determination. The state-file interruption hole H5 is independent of the correctly scoped allowlist.

## Reproduction driver

Save the following as `v2/data/pass10_review.py`. Review-only fixtures are deliberately embedded here so the report remains reproducible without relying on an untracked helper file.

```python
import sys, json, time, math
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
sys.path.insert(0, str(Path.cwd() / 'spikes'))
import numpy as np
import shapely
from locfinder.places.resolve import *
from locfinder.places.anchor import *

def show(r):
    return [r.outcome, [[c.place.name,c.place.source_id,c.score,c.place.locality,c.place.category,c.place.address,[round(c.place.lon,6),round(c.place.lat,6)],c.locality_match] for c in r.candidates]]

def resolver():
    import geopandas as gpd
    from locfinder.metros import TRIANGLE
    from s2_resolver_fixtures import FIXTURES
    ov=gpd.read_parquet('data/triangle/overture_places_accepted.parquet')
    osm=gpd.read_parquet('data/triangle/osm_pois.parquet')
    idx=build_metro_index(ov,osm,bbox=TRIANGLE.routing)
    print('INDEX',len(idx),flush=True)
    for q in FIXTURES+['Durham Whole Foods','the Whole Foods in Durham','Carrboro Farmers Market Carrboro','downtown Raleigh','Southpoint mall','NC State','Duke campus']:
        print(q,json.dumps(show(idx.resolve(q)),ensure_ascii=True),flush=True)
    for text in ['Southpoint','Duke Hospital','Fidelity Investments','Carrboro Farmers Market','Research Triangle Park','North Carolina State University','Duke University']:
        rows=[p.__dict__ for p in idx.places if normalise(text) in normalise(p.name)]
        print('RAW',text,json.dumps(rows,ensure_ascii=True),flush=True)
    common=[n.get('common') for n in ov.names if isinstance(n,dict) and n.get('common') is not None]
    print('COMMON',len(common),repr(common[:5]),flush=True)
    print('RTP_ALIASES',[(p.name,p.aliases) for p in idx.places if any(normalise(a)=='rtp' for a in p.aliases)],flush=True)
    print('OUTSIDE_EVAL',sum(not TRIANGLE.evaluation.contains(p.lat,p.lon) for p in idx.places),flush=True)
    print('OUTSIDE_BY_SOURCE',{s:sum(p.source==s and not TRIANGLE.evaluation.contains(p.lat,p.lon) for p in idx.places) for s in ['osm','overture']},flush=True)
    full=idx.resolve('Southpoint',limit=1000)
    print('MALL_RANKS',[(i+1,c.place.name,c.score,c.place.category) for i,c in enumerate(full.candidates) if c.place.category=='shopping_mall'],flush=True)
    import locfinder.places.resolve as module
    for margin in [.02,.08,.15,.3]:
        module.AMBIGUITY_MARGIN=margin
        print('MARGIN',margin,[(q,idx.resolve(q).outcome) for q in ['Southpoint','Duke Hospital','NC State']],flush=True)
    module.AMBIGUITY_MARGIN=.08
    for floor in [.3,.45,.5]:
        module.SCORE_FLOOR=floor
        print('FLOOR',floor,show(idx.resolve('Durham Whole Foods')),flush=True)

def graph():
    import osmnx as ox, networkx as nx
    from pyproj import Transformer
    from locfinder.traveltime.speeds import add_travel_times
    from locfinder.traveltime.csr import graph_to_cost_time_csr
    from locfinder.traveltime.components import largest_component
    from locfinder.traveltime.snap import EdgeIndex
    from spotcheck_engines import PLACES
    import geopandas as gpd
    tr=Transformer.from_crs(4326,32617,always_xy=True)
    for metro,filename in [('triangle','roads.graphml'),('slice','slice-roads.graphml')]:
        print('LOADING',metro,flush=True)
        G=ox.project_graph(ox.load_graphml(Path('data')/metro/filename),to_crs='EPSG:32617')
        add_travel_times(G,mode='drive')
        G.remove_nodes_from([n for n,d in G.degree() if d==0])
        x,y=tr.transform(-78.7875,35.8776)
        nd=sorted((math.hypot(d['x']-x,d['y']-y),n) for n,d in G.nodes(data=True))
        nearest=nd[0][1]
        comp=nx.node_connected_component(G.to_undirected(as_view=True),nearest)
        print('BEFORE',metro,'nearest',nearest,nd[0][0],'weak_size',len(comp),flush=True)
        Gp,rep=largest_component(G)
        del G
        c,t,index=graph_to_cost_time_csr(Gp)
        reach=CoreReachability.from_csr(c)
        print('GRAPH',metro,'kept',len(index),'unreachable',int((~reach.reachable_from_core).sum()),'core',reach.core_size,flush=True)
        # Independent forward graph traversal, without SCC condensation.
        root=next(n for n,i in index.items() if reach.component[i]==reach.core)
        desc=nx.descendants(Gp,root)|{root}
        print('INDEPENDENT_BFS',metro,'unreachable',len(index)-len(desc),flush=True)
        e=EdgeIndex.from_graph(Gp,index); xy=node_coordinates(e)
        if metro=='triangle':
            bar=gpd.read_parquet('data/triangle/osm_barriers.parquet').to_crs(32617)
            bars=shapely.STRtree(list(bar.geometry))
            changed=[]
            for name,(lat,lon) in PLACES.items():
                ax,ay=tr.transform(lon,lat)
                distances=sorted((math.hypot(px-ax,py-ay),n,bool(reach.reachable_from_core[n])) for n,(px,py) in xy.items())
                fixes=[fix_anchor(ax,ay,edge_index=e,reach=reach,barriers=bars,node_xy=xy,max_nudge_m=cap) for cap in [25,50,75,100,150,200]]
                f=fixes[4]
                print('ANCHOR',name,'nearest3',distances[:3],'selected',[f.status,f.node,round(f.moved_m,3),f.rejected_unreachable,f.crossed_barrier], 'caps',[(cap,z.status,round(z.moved_m,2)) for cap,z in zip([25,50,75,100,150,200],fixes)],flush=True)
                if f.node!=distances[0][1]: changed.append(name)
            print('ACTUAL_CHANGED',changed,flush=True)
        near=[(round(d,3),n,bool(reach.reachable_from_core[index[n]])) for d,n in nd if d<=150 and n in index]
        print('RDU',metro,near,flush=True)
        # Find conflicting geometry endpoints attached to the same node.
        disagreements=[]
        for i,g in enumerate(e.geoms):
            for n,p in [(int(e.start_idx[i]),g.coords[0]),(int(e.end_idx[i]),g.coords[-1])]:
                gap=math.dist(xy[n],p)
                if gap>1e-6: disagreements.append(gap)
        print('ENDPOINT_DISAGREEMENTS',metro,len(disagreements),max(disagreements,default=0),flush=True)
        del Gp,e,xy,c,t

def synthetic():
    import networkx as nx, geopandas as gpd
    from locfinder.traveltime.snap import EdgeIndex
    from locfinder.traveltime.csr import graph_to_csr
    from locfinder.traveltime.arrival import arrival_seconds
    from locfinder.places.licence import resolve_licence, UnknownLicence
    def p(name,sid,**kw):
        return Place('osm',sid,name,kw.pop('lon',-79.),35.9,**kw)
    two=PlaceIndex([p('Shop','a'),p('Shop','b',lon=-78.9)])
    for limit in [0,1,2,8]: print('LIMIT',limit,show(two.resolve('Shop',limit=limit)))
    merge=PlaceIndex([p('Acme','shop',category='bank'),p('Acme','atm',lon=-79.0001,category='atm')])
    print('MERGE_DISTINCT',show(merge.resolve('Acme')))
    local=PlaceIndex([p('Acme','a',locality='Durham'),p('Acme','b',lon=-78.9,locality='Raleigh'),p('Acme Office','c',lon=-78.8,aliases=('Acme',),locality='Durham')])
    print('LOCAL_UNIQUE',show(local.resolve('Acme Durham')))
    poor=PlaceIndex([p('Acme','a',locality='Raleigh'),p('Acme Office','b',lon=-78.8,locality='Durham')])
    print('LOCAL_WORSE',show(poor.resolve('Acme Durham')))
    def prep(nodes,edges,geoms=None):
        g=nx.MultiDiGraph()
        for n,xy in enumerate(nodes): g.add_node(n,x=xy[0],y=xy[1])
        for j,(u,v) in enumerate(edges):
            g.add_edge(u,v,travel_time=1.,geometry=shapely.LineString(geoms[j]) if geoms else shapely.LineString([nodes[u],nodes[v]]))
        csr,ix=graph_to_csr(g)
        return EdgeIndex.from_graph(g,ix),CoreReachability.from_csr(csr),csr
    e,r,c=prep([(0,0),(1,0),(2,0),(3,0)],[(0,1),(1,0),(1,2),(3,0)])
    print('DIRECTION',r.reachable_from_core.tolist(),'arrival_to_sink',arrival_seconds(c,dest_idx=[2]).tolist(),'arrival_to_source',arrival_seconds(c,dest_idx=[3]).tolist())
    e,r,c=prep([(140,140),(300,300)],[(0,1),(1,0)])
    f=fix_anchor(0,0,edge_index=e,reach=r,barriers=None)
    print('FALSE_ROAD_WITHIN_CAP',f.status,'true_road_distance',round(shapely.distance(shapely.Point(0,0),e.geoms[0]),3))
    # Same snapped node (bucket 0) has two endpoint positions straddling a wall.
    geom=[[(.2,0),(100,0)],[(100,0),(-.2,0)]]
    e,r,c=prep([(.2,0),(100,0)],[(0,1),(1,0)],geom)
    print('NODE_COORDS',node_coordinates(e))
    from dataclasses import replace
    reverse=replace(e,tree=shapely.STRtree(e.geoms[::-1]),geoms=e.geoms[::-1],start_idx=e.start_idx[::-1],end_idx=e.end_idx[::-1])
    for label,ei in [('forward',e),('reversed',reverse)]:
        f=fix_anchor(-1,0,edge_index=ei,reach=r,barriers=None,max_nudge_m=1.)
        b=fix_anchor(-1,0,edge_index=ei,reach=r,barriers=shapely.STRtree([shapely.LineString([(0,-2),(0,2)])]),max_nudge_m=2.)
        print('ENDPOINT_ORDER',label,'cap1',f.status,'barrier2',b.crossed_barrier,'moved',b.moved_m)
    for a in [None,float('nan')]:
        frame=gpd.GeoDataFrame([{'id':'x','names':{'primary':'Shop'},'addresses':a,'geometry':shapely.Point(-79,35.9)}],crs=4326)
        try: print('LOAD_ADDRESSES',repr(a),len(from_overture(frame)))
        except Exception as ex: print('LOAD_ADDRESSES',repr(a),type(ex).__name__,str(ex))
    frame=gpd.GeoDataFrame([{'name':__import__('pandas').NA,'geometry':shapely.Point(-79,35.9)}],crs=4326)
    print('LOAD_PD_NA',[(p.name,p.source_id) for p in from_osm(frame)])
    for allow in [None,frozenset({'ODbL-1.0'})]:
        try: print('LICENCE',allow,resolve_licence({'sources':[{'dataset':'x'}]},release='r',manifests={'r':{'x':'ODbL-1.0'}},allowed=allow))
        except UnknownLicence as ex: print('LICENCE',allow,type(ex).__name__)

def state():
    import subprocess
    from unittest.mock import patch
    sys.path.insert(0,str(Path.cwd()/'scripts'))
    from fetch_buildings import fetch_raw,_state_path
    raw=Path('data/pass10_mock_raw.parquet')
    files={raw:'release-A bytes',_state_path(raw):json.dumps({'release':'A','bbox':'bboxA','type':'building'})}
    def write(path,text,**kw): files[path]=text
    with patch.object(Path,'exists',lambda p:p in files), patch.object(Path,'read_text',lambda p,**kw:files[p]), patch.object(Path,'write_text',write):
        def fail(*a,**kw):
            files[raw]='partial release-B bytes'
            raise subprocess.CalledProcessError(1,a[0])
        with patch('fetch_buildings.subprocess.run',side_effect=fail):
            try: fetch_raw(raw,'bboxB','B')
            except subprocess.CalledProcessError: print('download B interrupted')
        with patch('fetch_buildings.subprocess.run') as run:
            fetch_raw(raw,'bboxA','A')
            print('requested A; actual:',raw.read_text(),'; subprocess called:',run.called)

def rdu_history():
    import osmnx as ox, networkx as nx
    from pyproj import Transformer
    from locfinder.traveltime.speeds import add_travel_times
    g=ox.project_graph(ox.load_graphml('data/slice/slice-roads.graphml'),to_crs=32617)
    x,y=Transformer.from_crs(4326,32617,always_xy=True).transform(-78.7875,35.8776)
    near=sorted((math.hypot(d['x']-x,d['y']-y),n) for n,d in g.nodes(data=True))[:6]
    print('RAW_NEAREST',near,flush=True)
    add_travel_times(g,mode='drive')
    for dist,n in near:
        comp=nx.node_connected_component(g.to_undirected(as_view=True),n)
        print('AFTER_MODE',n,round(dist,3),'degree',g.degree(n),'weak_size',len(comp),flush=True)

if __name__=='__main__':
    globals()[sys.argv[1]]()

```
