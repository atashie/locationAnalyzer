**The nine closed places should not be filtered on this evidence. Require corroboration.** The audit establishes nine flagged records, not nine unusable grocery destinations. Its arithmetic reproduces, but several interpretations and the brand-based price list fail.

I reviewed the requested files against `b02d857`; the current checkout is `2879213`, with no differences in those files. I loaded the graph once, evaluated all 512,633 structures, and made no repository changes. I skipped pytest.

1. **High — Closure flags are promoted to ground truth without validating either the business or the site.**

   Locations: [report:16](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-7-destination-truth.md:16), [report:174](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-7-destination-truth.md:174), [plan:219](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/plans/2026-11-04-s3-execution-plan.md:219), [script:330](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/audit_destination_truth.py:330).

   The repository contains evidence the validity audit omits:

   | Flagged record | Other evidence |
   |---|---|
   | Kroger | OSM Harris Teeter **14.8 m** away; included Overture Harris Teeter **16.2 m** away, **same destination node** |
   | La Tiendita Market | OSM `ktown market`, supermarket, **31.8 m** away; included Overture Green Berry LLC **29.5 m** away |
   | Kinstar International Food | OSM Little India, convenience, **34.1 m** away; included Overture Little India **19.8 m** away |
   | Carolina Cupboard | Included Overture Southern Season at **identical coordinates**, same destination node |

   There is no exactly coincident OSM supermarket among the nine; the nearby supermarkets above are the relevant contradictions to **site unavailability**. Different successor names can actually support closure of the old business. They do not support deleting grocery service at that site.

   Eight flags come from BrightQuery; Kroger’s status comes from Overture-signals. The quoted place-level confidence is not an independently measured closure error rate. Neither audit sheet contains completed destination qualifications establishing these closures, and the recovery note establishes selected identities, not operating status.

   **Cost:** withdraw “nine closed grocery destinations” as an established real-world finding. Rename the impact to *effect of removing nine flagged records*. Removing them eliminates **seven nodes**, because two remain supported by other records. “Needed no walk and no external source” describes discovering the flags, not verifying the claimed failures.

   **Reproducer:** R below, outputs `CLOSED` and `CLOSED-NODES`.

2. **High — The supposedly store-only matcher admits nonstores, and “nine chains split” confuses records with branches.**

   Locations: [script:75](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/audit_destination_truth.py:75), [script:253](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/audit_destination_truth.py:253), [script:286](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/audit_destination_truth.py:286), [report:67](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-7-destination-truth.md:67), [report:90](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-7-destination-truth.md:90).

   Three admitted rows are clear failures:

   - `756dd932…`: **Harris Teeter Fuel Center**, taxonomy absent.
   - `46176241…`: **TARGET PharmaSolutions**, taxonomy `department_store`; its recorded website is `targetpharmasolutions.com`.
   - `cc27b383…`: **Mariachi Garibaldi NC**, taxonomy absent. `GaribALDI` matches `Aldi`.

   The per-chain check gives:

   | Chain | What the excluded rows actually establish |
   |---|---|
   | Harris Teeter | Sole row is the fuel center. **No demonstrated branch split.** |
   | Publix | Named supermarket at Buffaloe Bend; coordinate agreement remains unresolved—OSM counterpart is **354.4 m** away. |
   | Kroger | Named Kroger record, but an included Harris Teeter is **12.9 m** away. **Current branch identity unresolved.** |
   | Aldi | **Five** named Aldi stores plus the mariachi row, rather than six stores. |
   | Lidl | Sole excluded store shares **1105 N Harrison Ave** with an included record named `Cary NC - N. Harrison Ave`, whose **brand is Lidl**. **Already represented as a branch.** |
   | Trader Joe’s | One named store, OSM counterpart **12.0 m** away. |
   | Whole Foods | Five named store rows; one already shares a destination node with included **Market Cocina**. |
   | Weaver Street | Three named retail rows outside; the three “inside” rows include **Weaver Street Market Administration** and another record at that administration address. |
   | Compare Foods | One named store, OSM counterpart **10.8 m** away. |

   Thus “nine chains split across the wedge” must be withdrawn as a branch-level finding. Several real taxonomy inconsistencies remain, but Harris Teeter and Lidl do not demonstrate the claimed omission; Kroger needs identity reconciliation.

   **Cost:** removing just the three clear false matches changes the price:

   | Minutes | Reported gains | Gains without those three |
   |---|---:|---:|
   | 10 | 4,318 | **3,403** |
   | 15 | 7,128 | **5,423** |
   | 25 | 10,411 | **7,402** |
   | 45 | 5,566 | **5,213** |

   These corrected figures still retain unresolved identities and duplicates; they are not validated adoption estimates. Target’s candidate count becomes **15**, Aldi’s **5**.

   **Reproducer:** R, outputs `CANDIDATE`, `CHAIN`, `LIDL-ALIAS`, and `ROUTED`.

3. **High — Adding destinations can worsen published answers; the audit’s monotonicity premise is false.**

   Locations: [script:310](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/audit_destination_truth.py:310), [script:364](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/audit_destination_truth.py:364), [report:97](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-7-destination-truth.md:97).

   This implementation minimizes **cost** and reports **time**. Adding a cheaper destination can select a slower journey. The report counts gains and omits losses:

   | Minutes | Brand addition: INCLUDED → not INCLUDED | OSM addition: INCLUDED → not INCLUDED |
   |---|---:|---:|
   | 10 | **69** | **1** |
   | 15 | **32** | **5** |
   | 25 | 0 | 0 |
   | 45 | 0 | 0 |

   Brand addition increases reported seconds at **429** previously finite structure evaluations; OSM addition does so at **126**. Removing flagged records also produces **14 gains at 10 minutes**, alongside the reported 1,473 losses. Its net inclusion reduction there is **1,459**.

   **Cost:** withdraw “removing destinations can only lengthen a time, and adding them can only shorten one.” Report both transition directions. “Served only by” also overstates what a cost-selected verdict difference proves about available qualifying routes.

   **Reproducer:** R, output `ROUTED`. A minimal independent example is:

   ```powershell
   @'
   import sys
   sys.path.insert(0, "v2")
   from scipy.sparse import csr_matrix
   from locfinder.traveltime.arrival import arrival_seconds_two_weight
   cost = csr_matrix(([700.,650.], ([0,0],[1,2])), shape=(3,3))
   time = csr_matrix(([500.,650.], ([0,0],[1,2])), shape=(3,3))
   for destinations in ([1], [1,2]):
       print(destinations, arrival_seconds_two_weight(
           cost, time, dest_idx=destinations)[0])
   '@ | .\v2\.venv\Scripts\python.exe -B -
   ```

   Prints **500 seconds → 650 seconds**: adding a destination turns a ten-minute pass into a fail.

4. **Medium — The measured unit is a direct structure query, not the cell answer published for that structure.**

   Locations: [script:321](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/audit_destination_truth.py:321), [script:339](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/audit_destination_truth.py:339), [report:43](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-7-destination-truth.md:43).

   Replacing each structure coordinate with its containing UTM cell centre, holding graph and destination sets fixed, changes the results:

   | Minutes | Flag-removal losses: direct / cell | OSM gains: direct / cell | Brand gains: direct / cell |
   |---|---:|---:|---:|
   | 10 | 1,473 / **1,568** | 4,551 / **4,619** | 4,318 / **4,412** |
   | 15 | 1,979 / **2,073** | 6,455 / **6,364** | 7,128 / **7,110** |
   | 25 | 963 / **950** | 7,450 / **7,417** | 10,411 / **10,394** |
   | 45 | 0 / **0** | 5,595 / **5,557** | 5,566 / **5,508** |

   **Cost:** **+95** and **+94** closure-removal losses at ten and fifteen minutes under the containing-cell evaluation. Direct coordinates are useful for model sensitivity, but cannot support “structures are told” without qualification.

   This rerun evaluates current graph results at UTM centres; it does not certify the complete exported viewer path or the historical raster.

   **Reproducer:** R, output `CELL-CENTRES`.

5. **Medium — “Same shop within 300 m” hides real omissions and does not follow from the snap cap.**

   Locations: [script:85](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/audit_destination_truth.py:85), [script:187](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/audit_destination_truth.py:187), [report:142](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-7-destination-truth.md:142).

   These rejected store counterparts disappear from the candidate sheet because a **different** selected grocery is nearby:

   | OSM store | Distance to its rejected Overture store | Selected grocery masking it |
   |---|---:|---|
   | Trader Joe’s | 12.0 m | Wegmans, 299.3 m |
   | Weaver Street Market | 21.6 m | Harris Teeter, 139.0 m |
   | Whole Foods Market | 5.2 m | Market at Colonnade Center, 141.0 m |
   | Aldi | 14.2 m | Food Lion, 273.2 m |

   Conversely, the named Publix counterparts are **354.4 m** apart. Centroids can therefore manufacture apparent disagreements, while proximity to unrelated shops suppresses actual identity disagreements. The bias can run both ways.

   A 300 m *point-to-node* acceptance radius is not a *point-to-point* identity rule: two points 400 m apart can both snap to their midpoint node within the cap.

   **Cost:** the sheet’s **28** is a count of spatially unmatched records under this heuristic, not an upper bound on omitted destinations. At least these four rejected store identities are masked.

   The comparator also excludes `shop=convenience`; more fundamentally, [fetch_places.py:29](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/fetch_places.py:29) never acquires `shop=grocery` as a requested shop tag. Merely changing `select_osm` cannot recover that missing acquisition stratum. “197 is mostly definitional” remains an unmeasured explanation.

   **Reproducer:** R, outputs `MASKED` and `PUBLIX`.

6. **Medium — The curated name list is neither a complete chain inventory nor a reliable price for a definition.**

   Locations: [script:61](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/audit_destination_truth.py:61), [script:242](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/audit_destination_truth.py:242), [report:114](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-7-destination-truth.md:114), [plan:227](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/plans/2026-11-04-s3-execution-plan.md:227).

   The matcher misses **eight** excluded rows named simply `Walmart`, plus an excluded `Wal-Mart` row. These are not automatically nine additional physical stores—some duplicate other representations—but they prove the named candidate inventory is incomplete.

   The list also omits locally present names that would show successful coverage: **18 selected Lowes Foods rows**, four selected names containing `Carlie`, and Save A Lot variants. It omits rejected **Chatham Marketplace**, already on the OSM sheet. Meanwhile, `Fresh Market` counts **Las Carolinas Fresh Market** as though it belonged to the same named brand group.

   **Cost:** withdraw “the options are priced above” as a sufficient decision basis. The disclaimer admits incompleteness but does not repair the owner’s price list. The evidence supports examples of taxonomy inconsistency, not a balanced or complete household-grocery inventory.

   **Reproducer:** R, output `NAME-OMISSIONS` and `OTHER-BRANDS`.

7. **Medium — “Destination half done” and “resolution is not the problem” exceed the audit’s domain.**

   Locations: [report:120](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-7-destination-truth.md:120), [report:131](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-7-destination-truth.md:131), [plan:213](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/plans/2026-11-04-s3-execution-plan.md:213).

   The audit measures proximity to road nodes. It does not establish correct store coordinates, entrance access, distinct retail identities, or destination qualification. The included **Weaver Street Market Administration** record is a concrete missed validity candidate. The recovery note’s **7/16 specialty-market journeys** remain unresolved qualification evidence.

   The **75 shared-node places** have equal model times because the representation makes them equal. That supports “no time distinction in this representation,” not “no resolution problem.” The Publix coordinate discrepancy and Lidl duplicate representation demonstrate unresolved geography and identity questions.

   **Cost:** withdraw the broad completion and resolution claims. Describe this as a completed automated screening pass with validation outstanding. Confidence needs source-stratified validation or sensitivity analysis before becoming a filter; a distribution paragraph cannot establish a safe threshold. The report does explicitly leave confidence policy and arrival usability open, so those are acknowledged gaps rather than concealed completed work.

   **Reproducer:** R, outputs `VALIDITY-CANDIDATES`, `LIDL-ALIAS`, and `PUBLIX`.

**Checks I could not break**

- All original routed counts reproduce exactly, including **1,473 at ten minutes and zero at forty-five**. That shape is legitimate: the difference counts thresholds lying between two results; it need not grow with the threshold. Zero at forty-five does not validate the destinations.
- Keeping the **106 unknown-status records** is correct for a narrowly labelled *remove flagged records* experiment. Calling the result `open_only` is misleading. Requiring explicit `open` instead produces **11,962 / 16,867 / 11,811 / 4,832** losses, a substantially different counterfactual.
- The footprint inequalities match `GridSpec.cell_for_xy` for finite coordinates, including north/west inclusion and south/east exclusion. Including buffered Overture groceries in matching does **not** change the 28 in this extract.
- Routing deduplicates destination **nodes**: **49 brand rows → 48 nodes → 47 new nodes**. The duplicate BJ’s rows do not double-count routing impact. Physical-site deduplication remains absent.
- Target Optical and BJ’s Restaurants are excluded by the primary filter. I found no farmers’ market admitted through `Fresh Market`; its actual name collision is Las Carolinas.
- **F’s overlap claim is true**, now quantified:

  | Minutes | Structures gained in both experiments |
  |---|---:|
  | 10 | **2,091** |
  | 15 | **3,715** |
  | 25 | **4,736** |
  | 45 | **4,494** |

  These are intersections of the separately measured gain sets, not a measurement of a joint amendment.
- The geocoding half is clearly marked unstarted.
- “Arbitrary, not cautious” is unsupported as a universal characterization: some differences are concessions, duplicate identities, or stale brands. Real branch taxonomy differences remain after those are removed.

**Runnable reproducer R**

Run from the repository root. It writes no artifacts or temporary directories. Set `RUN_ROUTING = False` for the cheap checks; the complete run loads the graph once.

```powershell
@'
import sys, inspect
sys.path[:0] = ["v2/scripts", "v2", "v2/spikes"]
import audit_destination_truth as a
import geopandas as gpd
import numpy as np
from shapely.strtree import STRtree

RUN_ROUTING = True
grid = a.METRO.grid()
ov = gpd.read_parquet(
    a.METRO_DIR / "overture_places_accepted.parquet").to_crs(grid.crs)
osm = gpd.read_parquet(
    a.METRO_DIR / "osm_pois.parquet").to_crs(grid.crs)
g = a.select_overture(ov, "grocery")
og = a.select_osm(osm, "grocery")

def name(r):
    return a.overture_name(r.names)

def inside(f):
    c = f.geometry.centroid
    return ((c.x >= grid.x_min) & (c.x < grid.x_max)
            & (c.y > grid.y_min) & (c.y <= grid.y_max))

oi = ov[inside(ov)]
b = a.brand_candidates(oi, g)
closed = g[g.operating_status == "permanently_closed"]
bad_ids = {
    "756dd932-f0ed-484b-9c9b-63dddd977cfb",
    "46176241-2dc5-4558-90ee-02be4dc6a54e",
    "cc27b383-473a-4cd6-8245-aecc6f016d29",
}
clean = b[~b.id.isin(bad_ids)]
gp = list(og.geometry.centroid)
tree = STRtree(gp)

for r in closed.itertuples():
    p = r.geometry.centroid
    j = int(tree.nearest(p))
    peers = [(name(s), s.operating_status,
              round(p.distance(s.geometry.centroid), 1))
             for s in g.itertuples()
             if s.id != r.id and p.distance(s.geometry.centroid) < 300]
    status_sources = [
        (s.get("dataset"), s.get("update_time"), s.get("confidence"))
        for s in r.sources
        if s.get("property") == "/properties/operating_status"
    ]
    print("CLOSED", name(r), r.confidence, status_sources,
          "OSM", og.iloc[j].get("name"), round(p.distance(gp[j]), 1),
          "OV peers", peers)

for r in b.itertuples():
    primary = r.taxonomy.get("primary") if r.taxonomy else None
    print("CANDIDATE", r.id, name(r), primary, r.addresses)

for brand in ["Harris Teeter", "Publix", "Kroger", "Aldi", "Lidl",
              "Trader Joe", "Whole Foods", "Weaver Street", "Compare Foods"]:
    print("CHAIN", brand, [
        (r.id, name(r), r.addresses)
        for r in b.itertuples() if brand.lower() in name(r).lower()
    ])

for pid in ["6fd58076-d794-4823-90ed-f0b76a1d7722",
            "4ff51c50-4e5d-4b0d-8bbe-ddb55a26be53",
            "1e99e399-b118-4d95-8c78-6770a47287c8"]:
    r = ov[ov.id == pid].iloc[0]
    print("LIDL-ALIAS" if "Harrison" in name(r)
          else "VALIDITY-CANDIDATES",
          pid, name(r), r.brand, r.addresses, pid in set(g.id))

missed = oi[oi.names.apply(
    lambda n: a.overture_name(n) in {"Walmart", "Wal-Mart"})]
print("NAME-OMISSIONS", [
    (r.id, name(r), r.taxonomy)
    for r in missed[~missed.id.isin(g.id)].itertuples()
])
for term in ["Lowes Foods", "Carlie", "Save A Lot", "Save-A-Lot",
             "Chatham Marketplace", "Fresh Market"]:
    print("OTHER-BRANDS", term, [
        (name(r), r.id in set(g.id))
        for r in oi.itertuples() if term.lower() in name(r).lower()
    ])

for fid in ["way/318319675", "way/44264917",
            "way/231354567", "way/804771012"]:
    r = osm.loc[fid]
    p = r.geometry.centroid
    near_g = min(g.itertuples(),
                 key=lambda s: p.distance(s.geometry.centroid))
    near_b = min(b.itertuples(),
                 key=lambda s: p.distance(s.geometry.centroid))
    print("MASKED", fid, r.get("name"),
          "selected", name(near_g),
          round(p.distance(near_g.geometry.centroid), 1),
          "rejected", name(near_b),
          round(p.distance(near_b.geometry.centroid), 1))

pub = b[b.id == "5074229c-e884-4097-8759-4308ddbab7e8"].iloc[0]
print("PUBLIX", pub.geometry.centroid.distance(
    osm.loc["node/13159948114"].geometry.centroid))

if not RUN_ROUTING:
    raise SystemExit

import osmnx as ox
from locfinder.traveltime.components import largest_component
from locfinder.traveltime.csr import graph_to_cost_time_csr
from locfinder.traveltime.speeds import add_travel_times, symmetrise
from locfinder.status import Criterion, Verdict, evaluate
from locfinder.measure.frames import structure_population

G = ox.project_graph(a.load_roads_graph(), to_crs=grid.crs)
G = symmetrise(add_travel_times(G, mode="walk"))
G.remove_nodes_from([n for n, d in G.degree() if d == 0])
G, _ = largest_component(G)
cost, time, index = graph_to_cost_time_csr(G)

cov = a.coverage(g, og, grid)
u = og.loc[[r["osm_feature_id"]
            for r in cov["candidate_omitted_destinations"]]]

# Expose existing local results; no change to the calculation or files.
src = inspect.getsource(a.impact).replace(
    "    return out",
    '    globals()["captured_surfaces"] = surfaces\n'
    '    globals()["captured_surface_for"] = surface_for\n'
    "    return out")
exec(src, a.__dict__)
print("ORIGINAL", a.impact(
    G, (cost, time), index, g, u, grid, brand_frame=b), flush=True)

surfaces = a.captured_surfaces
surface_for = a.captured_surface_for
def nodes(f):
    return set(a.destination_nodes(
        G, index, list(f.geometry.centroid)))

surfaces["clean"] = surface_for(sorted(nodes(g) | nodes(clean)))
surfaces["confirmed_open"] = surface_for(
    sorted(nodes(g[g.operating_status == "open"])))
print("NODE-COUNTS", len(b), len(nodes(b)),
      len(nodes(b) - nodes(g)))

for r in closed.itertuples():
    n = nodes(g[g.id == r.id])
    other = g[g.id != r.id]
    print("CLOSED-NODES", name(r), n,
          "retained by another record", n <= nodes(other))

for t in a.THRESHOLDS_MIN:
    criterion = Criterion(label="g", mode="walk", target="grocery",
                          kind="category", threshold_s=t * 60.)
    v = {k: evaluate(criterion, s) == int(Verdict.INCLUDED)
         for k, s in surfaces.items()}
    base = v["published"]
    osm_gain = ~base & v["plus_unmatched_osm"]
    brand_gain = ~base & v["plus_household_brands"]
    print("ROUTED", t,
          "overlap", int((osm_gain & brand_gain).sum()),
          "brand losses",
          int((base & ~v["plus_household_brands"]).sum()),
          "OSM losses",
          int((base & ~v["plus_unmatched_osm"]).sum()),
          "removal gains", int((~base & v["open_only"]).sum()),
          "clean gains", int((~base & v["clean"]).sum()),
          "confirmed-open losses",
          int((base & ~v["confirmed_open"]).sum()), flush=True)

ids, pts, total = structure_population(
    a.METRO_DIR / "overture_buildings_accepted.parquet", grid)
cols = np.floor((pts[:, 0] - grid.x_min) / grid.cell_m)
rows = np.floor((grid.y_max - pts[:, 1]) / grid.cell_m)
centres = np.column_stack((
    grid.x_min + (cols + .5) * grid.cell_m,
    grid.y_max - (rows + .5) * grid.cell_m))
a.structure_population = lambda *args: (ids, centres, total)
print("CELL-CENTRES", a.impact(
    G, (cost, time), index, g, u, grid, brand_frame=b), flush=True)
'@ | .\v2\.venv\Scripts\python.exe -B -
```

Codex session ID: 01a1d5d7-afeb-7f61-8aeb-371f24df0ff3
Resume in Codex: codex resume 01a1d5d7-afeb-7f61-8aeb-371f24df0ff3
