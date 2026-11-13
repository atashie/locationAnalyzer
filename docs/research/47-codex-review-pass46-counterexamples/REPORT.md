**The decision report should not be handed to the owner in its current form.** It misstates the E3 outcome, attributes address-level measurements to published answers, and leaves material release work out of the decision.

I reviewed `e35b0f4`; its implementation matches `972abb7`, with your attachment-row correction included. I changed no files.

**1. High — the accepted observation scores `FAILED`, not `UNVERIFIED`.**

Location: [docs/s3-decision-report.md:25](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/s3-decision-report.md:25), repeated at lines 55–58.

The report accepts one walked observation of approximately 1,500 seconds against 810.8186 reported seconds. That trips **both** limbs of the existing E3 scorer:

- 1.85× reported time and 689.18 seconds over;
- median difference 689.18 seconds against a 202.70-second limit.

Runnable reproducer, from the repository root:

```powershell
v2/.venv/Scripts/python.exe -B -c "import sys; sys.path.insert(0,'v2'); from locfinder.measure.e3 import Journey,score_e3; print(score_e3([Journey('band15min_pass-03',810.8186,1500)]))"
```

**Cost:** the reported E3 outcome changes from `UNVERIFIED` to `FAILED`. One observation cannot establish a population error rate, but the scorer deliberately allows one observation to establish failure.

If this approximate observation is inadmissible for E3, the report must identify that exclusion and its reason. It cannot simultaneously present it as accepted walked evidence and silently bypass the failure rule.

The same outcome paragraph also says “engine disagreement is reported,” although this report supplies no magnitude and explicitly says the comparator does not exist. That outcome should read **not measured**, with any older engine comparison separately qualified.

**2. High — the headline describes the structure-coordinate route, not the published cell’s route.**

Location: [v2/scripts/flag_restricted_routes.py:126](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/flag_restricted_routes.py:126), with the misleading interpretation at lines 132–133 and [docs/s3-decision-report.md:30](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/s3-decision-report.md:30).

Both the seconds and flag are evaluated at each structure’s own centroid. They are never looked up from its containing published cell.

All four artifact rows reproduce exactly. Evaluating the **containing source cell’s** seconds and flag instead gives:

| Threshold | Artifact: included / flagged | Source-cell lookup: included / flagged | Source-cell share |
|---|---:|---:|---:|
| 10 min | 78,627 / 8,033 | **80,067 / 7,276** | **9.09%** |
| 15 min | 162,699 / 16,871 | **163,875 / 15,299** | **9.34%** |
| 25 min | 298,236 / 33,413 | **298,716 / 30,990** | **10.37%** |
| 45 min | 424,650 / 50,197 | **424,886 / 47,257** | **11.12%** |

**23,330 structures change flag** between their own coordinate and their containing source cell.

Runnable reproducer; this intercepts the script’s output write, so it creates no artifact or temporary directory:

```powershell
@'
import sys, runpy, pathlib
from unittest.mock import patch
import numpy as np
sys.dont_write_bytecode = True

m = runpy.run_path("v2/scripts/flag_restricted_routes.py",
                   run_name="review46")
g = m["main"].__globals__
samples, flags = [], []
original_answer = g["cell_arrival_with_provenance"]
original_flag = g["cell_route_flag"]

def answer(*a, **kw):
    out = original_answer(*a, **kw)
    samples.append((a, out))
    return out

def flag(*a, **kw):
    out = original_flag(*a, **kw)
    flags.append(out)
    return out

g["cell_arrival_with_provenance"] = answer
g["cell_route_flag"] = flag
with patch.object(pathlib.Path, "write_text", return_value=0):
    g["main"]([])

grid = g["METRO"].grid()
x, y = samples[1][0][2:4]
row = np.floor((grid.y_max-y)/grid.cell_m).astype(int)
col = np.floor((x-grid.x_min)/grid.cell_m).astype(int)
key = row*grid.ncols + col
seconds = samples[0][1][0][key]
flagged = flags[0][key]

print("SOURCE CELL LOOKUP")
for t in (10, 15, 25, 45):
    included = seconds <= t*60
    n = int(included.sum())
    f = int((included & flagged).sum())
    print(t, n, f, f/n)
print("different flags:", int((flagged != flags[1]).sum()))
'@ | v2/.venv/Scripts/python.exe -B -
```

The WGS84 export moves it again. Reprojecting the current source flag with the exporter’s nearest-neighbour mapping gives **7,119 / 79,555 = 8.95%** at ten minutes. The analytical MapLibre placement gives **7,075 / 79,805 = 8.87%**. These are candidate disclosure counts: **no flag plane is currently shipped**.

**Cost:** withdraw “8,033 published structure answers depend on a restricted way.” Preserve those numbers as **address-coordinate model measurements**, or replace them with a consistently sampled published representation.

**3. Medium — an exact endpoint can disclose an edge the journey never traverses.**

Location: [v2/locfinder/traveltime/snap.py:366](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/locfinder/traveltime/snap.py:366).

`have` establishes that a journey exists. It does not establish that any positive portion of the matched edge was walked. `_snap_network` correctly permits zero on-edge travel at endpoints, but `cell_route_flag` still adds that direction’s edge flag.

Runnable reproducer:

```powershell
@'
import sys
sys.path.insert(0, "v2")
import networkx as nx
import numpy as np
from locfinder.traveltime.snap import (
    EdgeIndex, cell_route_flag, cell_seconds_from_arrival)

G = nx.MultiDiGraph()
G.add_node(0, x=0., y=0.)
G.add_node(1, x=100., y=0.)
G.add_edge(0, 1, travel_time=100., cost=220.,
           access_restricted=True)
idx = EdgeIndex.from_graph(G, {0: 0, 1: 1})
x, y = np.array([0., 50., 100.]), np.zeros(3)
kw = dict(mode="walk", max_access_m=200.,
          node_cost=np.array([220., 0.]))
print(cell_seconds_from_arrival(
    idx, np.array([100., 0.]), x, y, **kw))
print(cell_route_flag(
    idx, np.array([100., 0.]), x, y,
    node_flag=np.array([True, False]), **kw))
'@ | v2/.venv/Scripts/python.exe -B -
```

Output:

```text
[100.  50.   0.]
[ True  True  True]
```

The final flag should be **False**: the point is already at its destination.

**Cost:** one false disclosure in this fixture; withdraw the unconditional “flagged exactly when its chosen path is” claim until zero-length matched-edge traversal is excluded. The same endpoint overrides, including their epsilon convention, must govern seconds and membership.

**4. Medium — the corrected attachment row still claims evidence for an unimplemented candidate.**

Location: [docs/s3-decision-report.md:21](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/s3-decision-report.md:21).

The pilot explicitly says **B is not implemented**. Its exact-rational diagnostic is not B, which also includes degree-two normalisation. The artifact contains measurements for **A/C/D**.

Also, 844,685 is the total evaluation count, including two 500-point samples. The census evaluations total **843,685**.

Runnable reproducer:

```powershell
@'
import json, pathlib
p = json.loads(pathlib.Path(
    "docs/experiments/t0-attachment-pilot.json").read_text())
for name, s in p["sets"].items():
    print(name, s["points"], s["is_a_sample"],
          [c for c in "ABCD" if c in s])
print("census evaluations:",
      sum(s["points"] for s in p["sets"].values()
          if not s["is_a_sample"]))
'@ | v2/.venv/Scripts/python.exe -B -
```

**Cost:** withdraw “A/B/C/D’s prevalence measured by census over 844,685 points.” Your correction correctly leaves verdict impact open, but it still overstates which conventions and populations were measured.

**5. Medium — the denominator is legitimate; the household and error-risk interpretations are not.**

Locations: [docs/s3-decision-report.md:29](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/s3-decision-report.md:29), lines 62 and 68–71; [execution-plan.md:282](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/plans/2026-11-04-s3-execution-plan.md:282).

The script honestly reports a **share of included structures**. That is a useful quantity for auditing positive recommendations. It does not establish exposure among all answered structures or among households.

Runnable denominator check:

```powershell
@'
import json, pathlib
s = json.loads(pathlib.Path(
    "docs/experiments/s3-8-restricted-routes.json").read_text()
)["units"]["structures"]
print("among answered:",
      s["answered_on_a_restricted_route"]/s["answered_at_all"])
print("among all structures:",
      s["answered_on_a_restricted_route"]/s["population"])
'@ | v2/.venv/Scripts/python.exe -B -
```

These are **14.20%** and **13.82%**, respectively, under the artifact’s address-coordinate definition.

“About one in ten” is fair shorthand for **10.2%–11.8% of included structures at the four reported thresholds**. It is not a household estimate: structures have no measured household weights.

Furthermore, route membership does not establish that this class is “most likely to be wrong,” that its population bias is optimistic, or that walking it offers the greatest return per hour. The artifact explicitly leaves the signed-error numerator empty.

Runnable evidence check:

```powershell
rg -n "SIGNED ERROR|leaves the numerator empty|per hour|most likely|direction" docs/experiments/s3-8-restricted-routes.json docs/s3-decision-report.md
```

**Cost:** withdraw the household prevalence claim and the empirical interpretation of the ranking. Keep **one known optimistic failure**; label the work ordering as a proposed prioritisation, without measured comparative error rates or return per hour.

**6. Medium — “nearest qualifying grocery” still conflates selection cost with walking time.**

Location: [docs/s3-decision-report.md:9](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/s3-decision-report.md:9).

The opening promises walking time to the nearest grocery. The implementation can select a grocery with a longer walking time because its generalised cost is lower.

Runnable reproducer:

```powershell
@'
import sys
sys.path.insert(0, "v2")
import networkx as nx
from locfinder.traveltime.csr import graph_to_cost_time_csr
from locfinder.traveltime.arrival import arrival_with_selected_destination
G = nx.MultiDiGraph()
G.add_edge("home", "fast", cost=700., travel_time=500.)
G.add_edge("home", "slow", cost=650., travel_time=650.)
c, t, i = graph_to_cost_time_csr(G)
s, d = arrival_with_selected_destination(
    c, t, dest_idx=[i["fast"], i["slow"]])
print(s[i["home"]], list(i)[d[i["home"]]])
'@ | v2/.venv/Scripts/python.exe -B -
```

Output: **650 seconds to `slow`**, despite a 500-second journey being available.

**Cost:** withdraw the unqualified nearest-by-walking-time promise. Say **the grocery selected by the routing cost rule**.

The upper-bound statement at line 66 is defensible when narrowly applied to rounding the **modelled source-cell journey**. It must not imply an upper bound on the household-coordinate or real-world journey: finding 3’s example has a 60-second rounded cell answer against 100 seconds at the structure coordinate.

**7. Medium — the release decision omits implementation work beyond adding the flag plane.**

Locations: [docs/s3-decision-report.md:60](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/s3-decision-report.md:60) and [execution-plan.md:317](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/plans/2026-11-04-s3-execution-plan.md:317).

Acknowledging that the flag is unpublished is correct. However, the three promised household disclosures are not currently deliverable through the bundle:

- It carries neither route flags nor selected destinations.
- A selected node does not uniquely identify a grocery when several places share that node.
- The per-criterion explanation card is unbuilt. The report also omits the documented unmeasured phone latency, unavailable recomputation UI, and unstarted geocoding audit.
- The browser implementation being discussed is the **G3 render spike**, not an identified completed household product.

Runnable inspection:

```powershell
Get-Content v2/spikes/g3-render/fixtures/published/manifest.json
rg -n "Phone decode|per-criterion|no criteria|Recomputation" docs/experiments/s3-5-browser-path.md
rg -n "geocoding.*not started|G3 render spike" docs/plans/2026-11-04-s3-execution-plan.md v2/spikes/g3-render/index.html
rg -n "cell_selected_destination|cell_route_flag" v2/locfinder/traveltime/layer.py v2/scripts/export_published_layers.py
```

**Cost:** withdraw any implication that the disclosure mechanism is ready for household delivery. The report needs an explicit release prerequisite list covering flag and destination persistence, consistent reprojection/lookup, identity presentation, and the actual delivery UI. Remaining device and product gaps should be named for explicit acceptance or resolution. The owner’s sessions remain correctly identified as outstanding.

I checked these claims and could not break them:

- **A, predecessor forest:** time and flag follow the same forest. Equal-cost insertion-order changes moved them together. A parallel-edge tie produced `(10 seconds, flagged)` in one order and `(90 seconds, unflagged)` in the other.
- **A, direction:** reversed geometry and asymmetric directional flags agreed with the reported seconds. The loop fallback is reachable.
- **A, hand-built indices:** the four constructors are a future footgun, but I found no live under-disclosure path from them into this walk/grocery pipeline. Its builder and step-8 script use `EdgeIndex.from_graph`.
- **B, refactor:** old arrival and CSR implementations from `0cf91ea` matched the new implementations exactly on **1,000 seeded random multigraphs**, including ties, parallel edges, unreachable nodes, multiple destinations and cutoffs.
- **C, arithmetic:** all four saved rows reproduce. The failure is their attribution to published answers.
- **D, fixture:** it really selects the cheaper restricted path. It is weak as a metamorphic test because it never reroutes through the dearer alternative, but it does not pass for an unrelated reason.
- **E, other caveats:** comparator absence, the open E1c interval method, destination validation outstanding, and analytical qualification of MapLibre placement are warranted. The encoding and three-way algebra claims survived the focused checks.

**Validation:** 100 focused routing, snapping, wire and conformance tests passed. I did not run the full suite. Pytest used an explicit external `--basetemp`, disabled its cache, and ran with `-s` after normal capture failed under the read-only environment. No temporary directories were created inside the repository.

Codex session ID: 01a1d635-4304-72c0-b6c3-7b04b681b57b
Resume in Codex: codex resume 01a1d635-4304-72c0-b6c3-7b04b681b57b
