# Codex Adversarial Review - Phase 0 Plan (Pass 3)

Date: 2026-11-03 | Model: GPT-6 (Codex) | Method: ordered document review, sibling-code cross-checks, upstream documentation/source verification, and in-memory execution of supplied tests plus an endpoint counterexample. No experiments or deployments executed.

## Verdict

- **Not executable as written.** Current Overture selectors and results-file paths block several spikes; the transit setup cannot deliver the stated experiment.
- Before Task 0, specify a supported Overture release/schema, repair results paths, and replace the GTFS mounting and scheduled-arrival instructions.
- Correct nearest-edge matching and endpoint arithmetic before interpreting any own-graph comparison.
- The numerical median/p90 inequalities match decision 12, but missing reachability cases and unrepresentative samples permit misleading passes.
- Move G6 acceptance before routing inputs and G5a before heavy builds. Owner decision 16 authorizes comparing both engines; it does not require productionizing both.
- Either execute NC/VPS G2 measurements or mark that gate incomplete. A capped local slice cannot establish NC serving feasibility.
- Keep the accepted listings fallback, truthful static labels, square grid, and generated-only portal links. Task 15 needs a later review identifier, since this document is already pass 3.

## Findings

| id | severity | task/step | issue | why it matters | fix | confidence |
|---|---|---|---|---|---|---|
| C1 | Critical | 7, 8, 10 selectors | `categories` was removed from current Places releases. | `places["categories"]` raises `KeyError`; routing and coverage will not run. | Pin release; migrate selectors to its taxonomy. | High, upstream |
| C2 | Critical | 6, 8, 9, 10 output | `Path("docs/experiments/...")` resolves under `v2/`. | Commands fail writing results after computation. | Resolve repository root from `__file__`. | High |
| C3 | Critical | 5 transit input | Zips under `/custom_files/gtfs_feeds` are neither extracted nor mounted at `/gtfs_feeds`. | Transit tiles cannot build from these instructions. | Extract each feed separately; mount the documented directory. | High, upstream |
| H1 | High | 9 semantics | Departure queries, wrong UTC conversion, unsupported Valhalla arrival semantics. | Compares different journeys and cannot test the advertised scheduled anchor. | Use one arrival instant and a supporting engine. | High |
| H2 | High | 3 snapping | Endpoint products include `0 * inf`; edge keys do not identify physical reverse counterparts. | Reachable cells become nodata; parallel roads can be conflated. | Mask unavailable directions; match geometry/identity. | High, reproduced |
| H3 | High | 3, 8 graph | Raw highway XML plus coarse tag filters omits access rules and turn restrictions. | Illegal paths look fast; this is more than a direction fix. | Preserve mode tags; audit restrictions; reject unsafe models. | High |
| H4 | High | 4, 10 OSM schema | `keep_all_tags=True` defaults to unexpanded tags. | Coverage code sees no `shop`/`amenity` columns and reports zeros. | Request `explode_tags=True` or read the tags map. | High, upstream |
| H5 | High | 4, 7–10 licensing | Latest download, invented manifest pin, first-source-only resolver, no enforced quarantine. | Unknown rows enter layers before licence acceptance. | Bind release/schema/manifest; persist accepted rows separately. | High |
| H6 | High | 8 comparison | Both-finite mask excludes routing failures; rates use all finite cells. | A model can pass despite losing relevant reachable cells. | Evaluate the union, including nodata disagreements near thresholds. | High |
| H7 | High | 7, 8 comparability | Speeds, destination snapping, cutoffs and edge buffers differ. | Error conflates engine, profile and sampling choices. | Separate controlled algorithm and intended-profile comparisons. | High |
| H8 | High | 5, 6, 15 G2 | NC/VPS explicitly deferred; build time and peak memory are not measured correctly. | Gate cannot pass against synthesis §6. | Keep deployment feasibility pending; collect actual milestones and peaks. | High |
| H9 | High | 6, 8, 9 sampling | Random anchors, weak one-way audit, transit medians only. | No adequate boundary, restriction, or scheduled-transit acceptance test. | Specify fixtures, independent checks and threshold metrics. | High |
| H10 | High | 7 fallback | Polygon fallback has no implementation; method B still needs GeoTIFF. | Unsupported GeoTIFF blocks the reference path entirely. | Require a working GeoTIFF build or implement contour bracketing. | High |
| H11 | High | 14/dependencies | G5a follows routing, listings regions and raster explanations. | Early usability gate becomes a late architecture endorsement. | Use fixture imagery and scripted explanations immediately. | High |
| M1 | Medium | 9 services | Floating MOTIS image/API and incomplete Transitous policy handling. | Version drift or denied requests can masquerade as missing transit. | Pin working image/API; add client version and attribution. | High/medium |
| M2 | Medium | 10 audit | Proximity matching and nearest-only joins do not measure recall or duplicate pairs. | Source choice lacks defensible denominators. | Independent local inventory; all-pairs radius query for duplicates. | High |
| M3 | Medium | 11 geocoder | OSM addresses bias comparison; caching/autocomplete contract omitted. | Benchmark does not establish a usable address-resolution flow. | Add ambiguous/POI cases; provider-specific contract. | High |
| M4 | Medium | 13 renderer | Six layers unavailable; `^5` is not a pin; nodata and polygon coordinates underspecified. | Rendering may measure invented data or invalid geography. | Explicit fixtures, lockfile, masks and coordinate transforms. | High |
| M5 | Medium | 0, 4 execution | Shell/CRLF assumptions, missing startup checks and Windows multiprocessing guard. | Repeated runs may fail before meaningful measurements. | Idempotent preflight, LF scripts, explicit main entrypoint. | Medium/high |

## Detailed notes

### C1, H4, H5: bind acquisition to the actual schema and policy

The [Overture Places guide](https://docs.overturemaps.org/guides/places/) says `categories` disappeared in September 2026; `taxonomy` and `basic_category` replace it. The plan targets October or latest. Validate an actual Arrow schema before coding selectors. GeoParquet nested fields are structs/list-of-structs, not GeoJSON JSON strings: expect dict-like names/taxonomy and array/list source values after conversion, and normalize nulls explicitly.

That guide lists `meta`, Microsoft and Foursquare, so those provider names are not inherently fictitious. However, the hardcoded table is not evidence for every dataset in a pinned release; other providers and CC0 rows also exist. Preserve exact observed identifiers and verified obligations. Do not accept any arbitrary nonempty `license` string as automatically permitted. Check relevant source entries and field scopes, including unknown later entries.

Task 10 merely counts quarantined rows, then continues using the original dataframe. Tasks 7/8 read the raw file independently. Write an accepted artifact plus a rejected-row report, and require the accepted artifact for both engines. Experimental use does not waive the first-ingest rule. Audit G6 after the small registry-authorized acquisition and before downstream derivation.

The [Overture CLI source](https://github.com/OvertureMaps/overturemaps-py/blob/main/overturemaps/cli.py) supports the download format/options and release selection; the given module invocation is not itself an established bug. Add `--release` rather than downloading latest and labeling it with a constant.

The [QuackOSM implementation](https://github.com/kraina-ai/quackosm/blob/main/quackosm/pbf_file_reader.py) makes `explode_tags` false by default with `keep_all_tags=True`. Set it explicitly. Its [function source](https://github.com/kraina-ai/quackosm/blob/main/quackosm/functions.py) confirms `convert_pbf_to_geodataframe` and dictionary/list filters, including `True` for any value. On Windows, put script execution behind `if __name__ == "__main__": main()` because the reader uses spawned processes; avoid re-running downloads during child imports.

### C2: all results paths need one convention

The commands run from `v2/`; creating the repository's `docs/experiments` does not create `v2/docs/experiments`. For scripts in `v2/spikes`:

```python
REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "docs" / "experiments"
RESULTS.mkdir(parents=True, exist_ok=True)
with (RESULTS / "g1-routing.md").open("a", encoding="utf-8", newline="\n") as f:
    f.write(text + "\n")
```

Apply this to every supplied spike and every prose-only script requirement. Task 6 says root while its command changes into `v2`; resolve that contradiction.

### C3, H1: transit ingestion and arrival are distinct blockers

The [scripted-image README](https://github.com/valhalla/valhalla/blob/master/docker/README.md) confirms the image and supplied environment-variable names. It requires extracted feed subdirectories mounted at `/gtfs_feeds`, rather than zipped files in the custom-files directory:

```yaml
volumes:
  - ../../data/valhalla_custom_files:/custom_files
  - ../../data/gtfs_extracted:/gtfs_feeds:ro
```

Create `gtfs_extracted/<agency>/*.txt`, validate feed calendars/timezones and checksums, and fail clearly when a required feed is absent. `cp ... || true` hides a prerequisite failure. The [GoTriangle directory](https://gotriangle.org/developer-resources/) does expose the seven agencies and a CC BY 3.0 default, but links lead to multiple providers; save each feed's applicable terms and service dates. Assign stable filenames to avoid collisions from generic download names.

Valhalla `date_time.type=1` means departure, while type 2 means arrival and is unsupported for multimodal. Its [isochrone dispatch source](https://github.com/valhalla/valhalla/blob/master/src/thor/isochrone_action.cc) selects multimodal expansion ahead of reverse expansion. Adding `reverse:true` does not provide a scheduled inbound transit surface. See the [API reference](https://valhalla.github.io/valhalla/api/isochrone/). Record this as unsupported capability, not an ingestion failure.

On November 10, 08:00 in North Carolina is `2026-11-10T08:00:00-05:00`, equivalent to 13:00Z. The MOTIS/Transitous script sends 08:00Z and omits `arriveBy`, giving a different departure query. A corrected supporting-engine query needs:

```python
params = {
    "fromPlace": f"{o[0]},{o[1]}", "toPlace": f"{d[0]},{d[1]}",
    "time": "2026-11-10T08:00:00-05:00",
    "arriveBy": "true", "timetableView": "false",
}
```

Define elapsed commute as arrival deadline minus latest feasible departure, including early-arrival waiting; minimum itinerary duration across a search window answers another question. The [MOTIS OpenAPI](https://github.com/motis-project/motis/blob/master/openapi.yaml) documents these distinctions and currently exposes versioned plan/one-to-all paths at v6. Older paths are not automatically invalid; verify the deployed contract. One-to-all returns reachable stops, requiring street access/interpolation to become a home-origin surface.

The [MOTIS README](https://github.com/motis-project/motis#quick-start) confirms config/import/server commands. Pin an available registry digest; verify `latest` and executable lookup before adopting the Docker recipe. The [Dockerfile](https://github.com/motis-project/motis/blob/master/Dockerfile) installs `/motis`, uses an unprivileged user and defaults to serving `/data`; mount permissions need checking.

Transitous is another MOTIS deployment, not ground truth. Align static feed versions and disable/account for realtime before comparison; independently inspect published trips. Its [policy](https://transitous.org/api/) permits light prototype testing conditionally, with client name/version/contact and visible source attribution; it provides no blanket “under 100 requests” exemption. Add a client version, cache responses, and review its automated-request wording before running the batch. Never infer operational accuracy from agreement between two MOTIS instances.

### H2, H3, H7: snapping and graph validity

All **23 supplied tests passed** when extracted and run in memory using installed NumPy 2.3.1, SciPy 1.16.0, Shapely 2.1.1, GeoPandas 1.1.1 and OSMnx 2.0.4. These are not the future lockfile. No supplied assertion was demonstrated wrong. However, a point at A on the supplied one-way A→B graph, targeting C, returns `NaN`: the unavailable backward term is `0 * inf`. Encoding silently converts this reachable point to nodata. Mask before arithmetic:

```python
fwd = idx.fwd_time[nearest]
rev = idx.rev_time[nearest]
via_end = np.full(frac.shape, np.inf)
via_start = np.full(frac.shape, np.inf)
m = np.isfinite(fwd)
via_end[m] = (1 - frac[m]) * fwd[m] + T[e_idx[m]]
m = np.isfinite(rev)
via_start[m] = frac[m] * rev[m] + T[s_idx[m]]
network = np.minimum(via_end, via_start)
```

Also define exact-node access separately, including zero travel when the node is a destination. Test both endpoints, asymmetric costs, reversed geometry, loops, and parallel roads. NetworkX keys are local to ordered node pairs: `(min(u,v), max(u,v), k)` can pair geometrically different edges or fail to pair true counterparts. Equal-distance nearest-edge ties can arbitrarily select an unreachable candidate. Use verified geometry/OSM identity and evaluate eligible tied candidates.

Nearest-node POI snapping has no distance bound or destination access time. A POI halfway along a long simplified edge can move substantially. Use controlled endpoint fixtures first; then equivalent edge-based destination correlation. Bound access legs and account for barriers/entrances. Cutoff Dijkstra can censor an endpoint even when a partial-edge origin would fall inside the budget; preserve sufficient endpoint distances and apply final cutoffs after access/interpolation.

The XML path has no mode-specific access policy: private/service roads, `foot=no`, `bicycle=no`, conditional access, bicycle contraflow and restrictions need handling. Simplifying before filtering can aggregate unlike tags, then `_highway` arbitrarily takes the first. `retain_all=False` removes disconnected components before mode selection. Keep components for the audit. A node-state CSR cannot encode turn restrictions without additional state; make that limitation an adoption criterion.

The CHCCS source includes explicit intersection penalties and different friction constants; Task 3 drops the penalties and changes constants while calling itself a port. Document a new profile honestly. Set Valhalla pedestrian walking speed to 5.04 km/h for a controlled 1.4 m/s comparison; compare intended defaults separately. Record drive costing, access and turn policies instead of interpreting all discrepancies as algorithm error.

### H6, H8, H9, H10: make gates capable of failing honestly

Decision 12's inequalities are correct. The comparison excludes every one-sided unreachable cell before computing errors and false classifications. Include reachability disagreements in a union-based confusion table, report their rate near boundaries, and prohibit a numeric accuracy pass from hiding missing coverage. Compute boundary rates on the stated boundary sample, with explicit denominators. Retain float seconds for evaluation; uint8 rounding can shift a threshold by 30 seconds.

The 50-cell one-way audit lacks fixed destinations, expected legal paths or matched Valhalla correlation. Specify auditable cases with known asymmetric OD paths, restrictions, bridges, entrances and disconnected components. Category minima must be checked across candidate destinations, not only whichever destination the tested model selects. Grocery boundaries may provide fewer than 50 cells at long thresholds; `n/a` cannot count as a commute gate pass. Add arbitrary workplace anchors and 25-minute thresholds. Transit needs median/p90 at 45 minutes and false classifications, rather than only median engine disagreement.

Task 6 drops exceptions from per-case failure counts and computes percentiles only on successes. Preserve case identity, error bodies, coverage failures and response correctness; predefine an acceptable failure rate. Separate warm/cold runs and use reproducible routable anchors alongside explicit off-network tests.

`time docker compose up -d` measures container startup, not readiness after tile construction; occasional `docker stats --no-stream` does not measure peak RSS. Poll readiness with a deadline, sample memory over the complete build/load/concurrency run, and report cgroup usage separately from process RSS. The 8 GB cap excludes API/OS headroom, and a local 2-CPU slice does not establish NC VPS latency. Measure NC on intended hardware before closing G2; no defensible slice/NC time or RAM estimate follows from area alone.

GeoTIFF and reverse static isochrones are real features. The [serializer](https://github.com/valhalla/valhalla/blob/master/src/tyr/isochrone_serializer.cc) writes time in seconds and flips rows north-up, so Task 7's time-unit assumption is supported for that source version. Validate the pinned binary and bands. Method B still requires GeoTIFF: a single polygon cannot recover minute-valued cells. Implement repeated contours with explicit error bounds or require GeoTIFF support. Verify multi-location minima against a two-location per-POI baseline before raising limits; record grid-resolution differences and bound batch sizes.

## Facts to verify at execution time

- [ ] Resolve/lock Python dependencies and both image digests; inspect MOTIS executable, API version, itinerary fields and one-to-all response.
- [ ] Inspect actual Overture Arrow schema, available release, taxonomy values and source identifiers; verify licence manifest evidence.
- [ ] Compare two-location Valhalla output against per-location minima; inspect `service_limits.isochrone.max_locations`, distance/time limits, GeoTIFF support and nodata.
- [ ] Validate all GTFS calendars, agency timezones, feed terms, transfer coverage and Transitous data alignment.
- [ ] Preflight Docker daemon **and Compose**, ports 8002/8080, LAN access and exact WSL mount casing. Task 0 already includes daemon startup; that is not missing.
- [ ] Enforce LF shell scripts and strip CR from `feeds.txt`; update apt indexes if needed. No WSL pip/Java step is required by this Python-on-Windows/container design.
- [ ] Measure XML parsing RSS and I/O; avoid concurrent graph loading during benchmark runs. Use a Windows main guard for QuackOSM.

## Cuts and merges

Move G5a immediately after scaffold using fixtures; remove its dependency on Task 12 and real rasters. Keep both routing spikes under decision 16, but use one category and two modes initially, sharing one accepted POI artifact and one evaluation harness. Reuse arrays for six-layer rendering loads; label synthetic fixtures explicitly instead of building unused categories.

Merge G6's licence adapter into acquisition. For recall, use an independent bounded inventory; nearest matching is agreement, not truth. `sjoin_nearest(exclusive=True)` excludes geometrically identical points, including distinct co-located records, and returns nearest neighbors rather than every duplicate pair; use a radius query for that count.

Keep scheduled transit early; stop Valhalla arrival work once unsupported semantics are established and test MOTIS first. Defer r5py unless the experiment needs it. Separate desktop link generation from owner device sessions; keep fallback nonblocking and never fetch listing portals automatically.

For G3, explicitly mask 255, define validity on reprojection, supply canvas corners as longitude/latitude, transform contour pixel coordinates, and test holes/topology. Lock an exact MapLibre version. For Task 11, the cited reuse path is actually `localupdates/geocode.py`; add ambiguous/POI searches, caching and persistence terms. Follow the [Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/): single-threaded one-off requests, application-wide maximum 1/s, identifying User-Agent, attribution, caching and no autocomplete.

Keep NC/VPS feasibility as a small required deployment check, or explicitly leave G2 pending. Remove claims that every gate is complete when owner-run sessions or deployment measurements remain outstanding.

## What is right

The transposed multi-source Dijkstra is correct: [SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csgraph.dijkstra.html) returns infinity beyond `limit`, and `min_only=True` takes the minimum across destinations. CSR duplicate reduction correctly selects minimum weights. Grid tests pass: this slice is 550×401 cells; north-up centers, raster profile and array encoding work. Densified projected bounds and input validation remain worthwhile generalization work.

The [Geofabrik NC URL](https://download.geofabrik.de/north-america/us/north-carolina.html) and [osmium extraction](https://docs.osmcode.org/osmium/latest/osmium-extract.html)/[tag-filter](https://docs.osmcode.org/osmium/latest/osmium-tags-filter.html) forms are sound. Buffer routing data beyond evaluation bounds. Pass-2 absorption is strong on truthful labels, no Terrarium, the provisional 8 GB cap and accepted listings fallback; weak on G6 enforcement and early G5a. Comparing both engines now follows the later owner decision, while deploying one chosen engine remains sensible.
