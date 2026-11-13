**The categorical E3 verdict is inadmissible on this observation as recorded: the scorer cannot be applied to this observation.** Pass 46 F1 overreached by treating a valid numerical calculation as an admissible measurement. The repair moves that defect into the report’s headline.

I reviewed `6771b7b`, which adds the pass 47 prompt to `1a72551`, plus the uncommitted robustness paragraph. I changed no files.

**1. High — the report promotes an unresolved observation into a measured failure.**

Locations: [docs/s3-decision-report.md:8](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/s3-decision-report.md:8), repeated at lines 35, 44 and 59.

The recorded evidence does not establish a comparable journey:

- The start door is unrecorded.
- The shop reached is unconfirmed.
- Whether the private approach was used or avoided is unresolved.
- The duration is explicitly approximate and not stopwatch-timed.

The audit protocol requires a recorded door inside the cell and walking to the predicted destination. Its own account explicitly acknowledges these missing facts at [audit/README.md:160](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/audit/README.md:160). The diagnosis likewise calls the modelled and reported journeys **“potentially different journeys”** at [soft-way-dependence.md:26](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/engineering-notes/project-phase1-s3-soft-way-dependence.md:26).

Reproducer, from the repository root:

```powershell
@'
import csv
from pathlib import Path
p = Path("docs/experiments/audit/triangle-grocery-walk-chapelhill-with-destinations.csv")
r = next(r for r in csv.DictReader(p.open(encoding="utf-8-sig"))
         if r["journey_id"] == "band15min_pass-03")
for k in ("start_lon", "start_lat", "destination_used",
          "walked_seconds", "unresolved", "notes"):
    print(k, repr(r.get(k)))
'@ | v2/.venv/Scripts/python.exe -B -
```

**Cost:** withdraw the categorical measured `FAILED` verdict, “one measured instance,” and “the walked journey took a private track.” The last statement establishes what the **modelled** journey takes, not what the owner walked.

Keep the observation prominently as an unresolved discrepancy and the private-track route as an established model behaviour. A sensitivity sweep over duration cannot establish missing journey identity.

A door-origin observation is not automatically inadmissible: the protocol deliberately permits a door inside the cell. The problem is that this observation does not document that comparison.

**2. Medium — the robustness threshold uses the raw model time while claiming to assess the published answer.**

Locations: [docs/s3-decision-report.md:15](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/s3-decision-report.md:15), lines 23–26 and 42.

`810.8186` comes from the cell-centre journey decomposition: approximately 28.1508 seconds of access plus 782.6677 seconds on the network. The stored float32 cell value is **810.8185424804688**; the sheet rounds that to **810.8**.

The sheet’s encoded answer is **14 minutes**, or **840 seconds**. `Journey.reported_s` is documented as “what the product said.” The decision report itself defines the published number as a whole-minute answer.

Conditional on an admissible observation:

| Reported input | Median-limb boundary | Single-journey-limb boundary |
|---|---:|---:|
| Raw model: 810.8186 s | **16.892054 min** | **20.270465 min** |
| Encoded answer: 840 s | **17.5 min** | **21 min** |

These are strict mathematical boundaries. Thus **16.9 describes only the binding median limb**, not both limbs. For the encoded answer, a **17-minute** walk returns `UNVERIFIED`, contradicting the claim that it must be under 17 minutes.

```powershell
@'
import sys
import numpy as np
sys.path.insert(0, "v2")
from locfinder.measure.e3 import Journey, score_e3

a = np.load("v2/data/layers/own_triangle_grocery_walk.npy")
print("stored:", repr(float(a[286,129])))
print("encoded seconds:", np.ceil(a[286,129]/60)*60)

for reported in (810.8186, 840.0):
    print("reported:", reported,
          "median boundary:", 1.25*reported/60,
          "single boundary:", max(1.5*reported, reported+300)/60)
    for observed in (1020, 1050, 1050.001, 1500):
        r = score_e3([Journey("focus", reported, observed)])
        print(observed, r.outcome.value, r.offending)
'@ | v2/.venv/Scripts/python.exe -B -
```

**Cost:** the published-answer boundary moves from **16.9 to 17.5 minutes**. If the intended comparison is instead against the raw audit prediction, name that comparison explicitly. Neither choice repairs finding 1.

**3. Medium — the proposed ordering retains the unsupported ranking and gives an unattainable expectation for more walks.**

Location: [docs/s3-decision-report.md:118](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/s3-decision-report.md:118), especially lines 119–120.

The heading now labels the ordering as judgment, but its justification still calls the restricted-route class **“most likely to be wrong.”** No comparative error rates establish that ranking.

More concretely, more walks cannot clear this `FAILED` result while the accepted observation continues to trip limb (i). Every additional accurate journey leaves that offending journey in the set.

```powershell
@'
import sys
sys.path.insert(0, "v2")
from locfinder.measure.e3 import Journey, score_e3

bad = Journey("existing", 840, 1500)
for n in (0, 1, 8, 1000):
    good = [Journey(str(i), 840, 840) for i in range(n)]
    print(n, score_e3([bad] + good).outcome.value)

print("changed prediction:",
      score_e3([Journey("revised", 1201, 1500)]).outcome.value)
'@ | v2/.venv/Scripts/python.exe -B -
```

Output: every expanded set remains `FAILED`; the changed prediction returns `UNVERIFIED`.

**Cost:** withdraw “most likely” as an empirical claim and “the only thing that can move the FAILED verdict.” Additional walks can investigate prevalence and causes. Revalidating the existing observation or changing and reassessing the model can change the verdict.

**4. Low — the engine-disagreement row omits existing, qualified evidence.**

Location: [docs/s3-decision-report.md:34](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/s3-decision-report.md:34).

“Not measured in this release” survives **at the current Triangle extent**. The available Valhalla layers are `(401, 550)`; the current Triangle layer is `(514, 643)`.

But historical disagreement was measured. [g1-routing.md:332](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/g1-routing.md:332) reports 600 stratified walk cells on the old slice, with 599 finite comparisons. The saved matrix reproduces:

- signed median: **+12.05 seconds**;
- median absolute difference: **30.75 seconds**;
- p90 absolute difference: **173.45 seconds**.

```powershell
@'
import json
from pathlib import Path
import numpy as np
p = json.loads(Path(
    "v2/data/layers/matrix_grocery_walk_controlled.json").read_text())
d = (np.array(p["own_min"]) - np.array(p["ref_min"])) * 60
d = d[np.isfinite(d)]
print(len(d), np.median(d), np.median(abs(d)), np.quantile(abs(d), .9))
'@ | v2/.venv/Scripts/python.exe -B -
```

**Cost:** replace the omission with a qualified historical magnitude: old slice, old configuration, speed-controlled reference, different access treatment, no real-world accuracy implication, and no current full-Triangle replication. T3’s absence does not erase G1; they are different comparisons.

**5. Low — the advertised scorer call is not runnable, and the promised sweep is absent.**

Locations: [docs/s3-decision-report.md:15](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/s3-decision-report.md:15) and line 27.

The constructor arguments are `reported_s` and `observed_s`, not `reported` and `walked`.

```powershell
v2/.venv/Scripts/python.exe -B -c "import sys; sys.path.insert(0,'v2'); from locfinder.measure.e3 import Journey; Journey('band15min_pass-03',reported=810.8186,walked=1500)"
```

This raises `TypeError`.

The committed reproducer calls the scorer once; it contains no 14–30-minute sweep:

```powershell
rg -n "score_e3|sweep|range|linspace|arange" docs/research/47-codex-review-pass46-counterexamples/run_all.py
```

**Cost:** correct the displayed API call and supply the sweep, or withdraw “the reproducer sweeps 14 to 30 minutes.”

The pass 46 repair dispositions are:

| Finding | Disposition |
|---|---|
| **F1: FAILED** | **Moves.** Conditional arithmetic is correct; admissibility was never established. My previous categorical conclusion was too strong. |
| **F2: measurement unit** | **Closes** the source-cell attribution defect. All three populations reproduce; shipped lookup remains explicitly qualified. |
| **F3: endpoint flag** | **Closes** in the cases tested. No remaining zero-traversal counterexample found. |
| **F4: attachment row** | **Closes.** A/C/D, B unimplemented, and 843,685 census evaluations all check out. |
| **F5: households/ranking** | **Narrows.** Structure wording is repaired; unsupported comparative risk survives in the justification. |
| **F6: nearest grocery** | **Closes** the selection-cost wording and rounding-bound defect. The new “measured underestimate” claim inherits finding 1. |
| **F7: prerequisites** | **Closes** the named implementation omissions. The report now clearly identifies the bundle and UI gaps. |

I checked and could not break:

- **Population arithmetic:** every saved row reproduced, including **7,271 / 80,067**. Exactly **23,330** structures differ in flag between coordinate and source-cell evaluation.
- **Clipping:** **zero** of the 512,633 current structures needs clipping; **zero** is rejected by `cell_for_xy`. No figure moves. The population filter prevents the proposed outside-footprint relocation on this dataset.
- **Endpoint handling:** exact endpoints, offsets inside and outside `_NODE_EPS`, an actual loop fallback, and zero-access points with positive matched-edge traversal behaved consistently with reported seconds.
- **Node flags:** an endpoint’s onward route can legitimately remain flagged. I found no equivalent over-disclosure requiring it to be suppressed.
- **Singleton scoring:** explicitly supported by the implementation and fixtures. At *n*=1, the median limb is a defined 25% overrun rule; it is not evidence of systematic population bias. `planned=0` counts unwalked rows, not whether the completed walk was planned.
- **Delivery qualification:** the report’s source-grid figures are clearly marked candidate disclosures. I found no remaining unqualified claim that the automatic disclosure mechanism is ready.

As an owner-facing document, the report currently substitutes a categorical alarm for an unresolved comparison. It should retain the discrepancy prominently, distinguish the conditional calculation from an admissible E3 result, and identify the immediate decision: verify this journey’s start, destination and usable route, then choose between further supervised evidence gathering and completing the household delivery path. More walks should not be presented as a way to erase an accepted single-journey failure.

**Validation:** 29 focused E3/route-flag cases passed, plus the custom endpoint checks and full three-population recomputation. I skipped the full suite. Pytest used an external `--basetemp`; artifact writes were intercepted. No repository files or temporary directories were created.

Codex session ID: 01a1d670-aa9d-7492-98db-6909136a6aa2
Resume in Codex: codex resume 01a1d670-aa9d-7492-98db-6909136a6aa2
