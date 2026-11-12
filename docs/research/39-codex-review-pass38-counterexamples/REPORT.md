# Pass 38 adversarial review

Reviewed committed `v2-rethink`, HEAD `0b7281d`, on 2026-11-12. Scope is the pass-38
prompt, including design revision 13, its primitives/tests/mutations, both supersession
claims, and the T0 refactor/adoption/explanation/renderer. **One High, five Medium,
two Low findings.** Production code and the reviewed documents/artifact are unchanged.

Run every reproducer from the repository root with the supplied interpreter:

```powershell
v2/.venv/Scripts/python.exe -B docs/research/39-codex-review-pass38-counterexamples/run_all.py
```

Each named script below also runs independently with the same command prefix.
`RESULTS.txt` contains the observed outputs. PASS means a counterexample or stated
survival check was reproduced, not that the reviewed claim passed. Mutations in the
reproducers run in fresh processes against in-memory modules, without editing source.

## F1 — High — “exact” adoption still accepts candidates outside both exact caps

**Claims refuted.** Design §2.4 item 7, its header and revision-13 block say
“every comparison that decides something made on the exact value.”
`exact.py:195` says “§2.2's residual ordering and both caps are therefore decided
exactly, by comparing against the squared cap.” Design §2.2 makes the caps inclusive
distance limits. The T0 exact path claims to adopt these primitives.

**Reproducer:** `f01_caps_and_band.py`.

For the admissible segment `(0,-1)→(0,0)` and point `(200,1e-6)`, the exact squared
distance is **40000 + approximately 1e-12**, strictly outside the origin cap.
`rational_sqrt` correctly rounds the residual to **200.0**. `dedup_and_cap`
(`t0_attachment_pilot.py:246–258`) compares that rounded residual with the cap,
so **A, C and D all retain the candidate**. At `(300,1e-6)` the same error accepts
a destination outside the 300 m cap. Exact-cap eligibility is false in both cases.
This changes answerable versus OFF_NETWORK/ineligible behavior, rather than just
an intermediate number. The examples use a 1 m segment and ordinary finite coordinates.

The band has a related, explicitly demonstrated semantic distinction. Vertical
segments at x=1 and x=1.01, queried from `(0,0)`, both survive A. The second exact
distance exceeds `1 + Fraction(0.01)` by **5/576460752303423488 =
8.6736173798840355e-18 m**. Adding the band in binary64 rounds that excess away.
Thus A_exact is an operational rounded-distance predicate; it is not the literal
exact-distance band. This does **not** make it B, which also requires degree-two
normalisation. The write-up acknowledges the rounded band, but that qualification
does not reconcile the normative blanket statement or the exact-cap claim.

**Repair:** use `exact_sq <= Fraction(cap)**2` on the exact path. State the band's
arithmetic separately and consistently. A comparison of two implementations that
share a rounded cap cannot establish conformance to an exact cap.

## F2 — Medium — the old prefix rule was implementable; irrationality is not impossibility

**Claims refuted.** Design §2.4 says “The span is also the only implementable
reading” and “there is no exact prefix to subtract.” The step-4 supersession block
says “There are no exact rational prefixes” and “the rule as worded is not
implementable.”

**Reproducer:** `f02_exact_prefixes.py`.

The preceding step-4 table explicitly defines `s_o` and `s_d` as **rounded**
prefixes. Those binary64 values are rational, and `Fraction(s_d)-Fraction(s_o)`
implements their exact subtraction immediately. On W3 the two rounded prefixes
are both **20000000**, so the old formula yields **0.0**, while the adopted span
yields **9.313225746154785e-17**, or **558.7935447692871 s** at weight 6e18.
The old rule was undesirable here, not unimplementable.

Even genuinely unrounded prefixes need not be stored as a single Fraction.
The script represents `sqrt(2) + 20000000*t` and `sqrt(2) + 20000000` as sparse
radical expressions. Exact symbolic subtraction cancels the common irrational
prefix and produces **1/536870912 = 1.862645149230957e-9 m**. The corresponding
polyline can stay inside the declared coordinate domain. More generally, finite
sums of rational radicals are exact algebraic expressions; a numeric binary64
prefix is not required to represent or subtract them.

**What survives:** true arclengths are not rational in general. The adopted span
avoids losing W3's interval and is a useful operational convention. The false
step is inferring non-representability or impossibility from “not a Fraction.”
Also distinguish the real span from the implementation's sum of rounded span
terms; they are not generally the same number.

## F3 — Medium — one advertised mutation only crashes; two substantial untested rules survive

**Claims attacked.** The step-4 plan records “22 mutations, all caught.” The
harness describes the purpose as testing “a wrong geometry arithmetic” and says
“What remains attacks ... the comparison being against the original rational.”

**Reproducer:** `f03_mutation_coverage.py`.

The “compare the midpoint against the floored scaling” mutation replaces a line
inside `_decide` with a reference to **`scaled`**, which exists only in the caller
`rational_sqrt`. Calling the mutant on 2 raises **NameError: name 'scaled' is not
defined**. A failed subprocess is counted as caught, so this result did not test
the advertised arithmetic. Repairing that mutant to compute `q/(u*u)` locally
produces **3 assertion failures**, showing that the intended arithmetic is in
fact covered. This is a harness-evidence defect, not evidence that that arithmetic
bug currently escapes the tests.

Two additional executable mutants each pass **all 40 fixtures**:

| mutation | observed incorrect result | required result |
|---|---:|---:|
| remove the y interpolation in `exact_position` | squared residual **4** for `(1.5,2)` on `(0,0)→(3,4)` | **0** |
| replace cross-segment destination partial `t_d` with `1-t_d` | fraction **0.625** on lengths 10,10, origin t=1/2 on segment 0, destination t=1/4 on segment 1 | **0.375** |

The second becomes **625 versus 375 seconds** at weight 1000. The only ordinary
multi-segment span fixture uses a destination midpoint, where these expressions
coincide. Direct vertical coordinate interpolation and a non-midpoint destination
partial have no mutations in the submitted harness. These are missing protections;
the unmutated implementations return the correct values.

**What survives:** the original harness really does print all 22 caught and restores
`exact.py` byte-identically. No equivalent active mutant was established. The
retirement identities are discussed below; a crash is different from equivalence.

## F4 — Medium — “parameters differ” counts unequal rounded images, not unequal parameters

**Claims refuted.** The write-up reports “1,333,808 parameters differ,” and the
raw block is offered to distinguish unchanged decisions from changed numbers.
`coarse_occurrence` says comparing parameters would report changes “which is noise.”
The normative occurrence key, however, includes the unrounded interior parameter.

**Reproducers:** `f04_adoption_blind_spots.py`; `verify_real_witnesses.py`.

`adoption_stats:627` first converts **both** parameters to float. On `(0,0)→(3,4)`
queried from `(1,1)`, the float parameter is **0.28**, while the exact parameter
is **7/25**. Their exact difference is **3/112589990684262400**, but the reported
parameter-difference count is **0**. The retained XY also changes from
`(0.8400000000000001,1.12)` to `(0.84,1.12)`, yet `points_with_any_change` is **0**.
The raw position block does detect this particular coordinate movement.

On `(0,0)→(1,1)` from `(0.1,0.2)`, parameters differ by **1/72057594037927936**,
while both rounded XY pairs are `(0.15000000000000002,0.15000000000000002)`.
Rounded XY is also not a substitute for exact occurrence identity.

This is present in the real data, not just constructed geometry. Replaying all
window geometries for the first reported census witness gives **4** parameter
differences under the published test versus **6** under exact rational comparison;
the second gives **1 versus 2**. The 1,333,808 figure is therefore not a count of
all unequal parameters. This review does not recompute its corrected census total.

**Repair:** compare `Fraction(pf.t)` with `px.t`, retaining a separate rounded-image
counter if useful. Label the occurrence comparison as vertex/segment structure,
and distinguish exact occurrence identity from tolerance-based location matching.
The raw block is valuable but is not a complete replacement for candidate-level
parameter tracking or routing impact.

## F5 — Medium — the sentinel bypasses the entry point whose adoption it purports to guard

**Claim refuted.** The sentinel docstring says “If either stops differing, the axis
is broken and the run stops rather than publishing zeros.” The write-up says the
witnesses must separate “or the run stops,” to guard an exact path silently acting
like the float path.

**Reproducer:** `f04_adoption_blind_spots.py`.

The script changes only `measure_point`'s dispatch in memory, forcing both arithmetic
requests to the float branch. `adoption_sentinel` still passes **2/2 witnesses**,
because it calls `raw_positions` directly. The real `adoption_stats` then compares
**1 position** and reports **zero for every raw difference**, accepting exactly
the failed-adoption shape the sentinel is meant to reject.

This does not show current dispatch is wrong: inspection and the reproduced real
differences show it is live. It shows the protection does not cover the census path.
Use W2/W3 through `measure_point` **and** `adoption_stats`, asserting expected clamp
counts and candidate changes. Add independent sentinels for the rounded root,
one-rounding partial, and prefix summation, since neither current witness isolates
all those primitives. A positive control for each counter is stronger than merely
asserting two raw labels differ.

## F6 — Low — equal record count is not a provenance guard

**Claim refuted.** `explain_adoption_diff.py:90–92`: “the copy is guarded” by the
design record count, and “A silent drift between the two copies is the failure
that guard exists for.”

**Reproducer:** `f06_graph_guard.py`.

Two virtual record sets have the artifact's actual expected count, **808433**, and
different geometry for the queried record. Both pass the exact count assertion.
The measured residual changes from **1.0** to **95.00526301210897 m**, and the
selected location from **(5,0)** to **(100,0)**. The other 808432 records may be
identical and far away; no count changes. Reordering records or changing weights
also need not change count. The fixture tests this guard, not a claim that such
drift occurred historically.

The currently committed six preparation operations match, and both actual census
examples reproduced. Nonetheless the guard does not establish the claimed invariant.
Share the preparation code and bind results to the graph/profile/runtime and an
ordered record/geometry/weight fingerprint, or compare the examples with retained
measured candidate identities and values.

## F7 — Low — artifact flattening discards container structure

**Claim refuted.** `compare_t0_artifacts.py` says “everything else is compared
exactly” and it “prints every difference with its JSON path.”

**Reproducer:** `f07_artifact_comparison.py`.

All these distinct nonvolatile JSON objects flatten identically:

```text
{"x": []}       -> {"x": [{}]}
{"x": {}}       -> {}
{"a.b": 1}      -> {"a": {"b": 1}}
```

Empty containers emit no leaves, and concatenated dotted paths can collide.
Python equality also treats false/0 and +0.0/-0.0 as equal; that is numeric equality,
not type-sensitive or bitwise identity. No actual historical measured number was
shown hidden by these cases. They limit the generic comparator's claim; use
recursive typed structural comparison, preserving empty containers and path tuples.

**What survives:** comparing the two historical committed artifacts around `df38f99`
really gives **610 equal nonvolatile leaves**. A one-ulp finite float edit nested
inside a list and dict is detected. The volatile patterns cover stamps, timing,
and the **entire runtime object**; the last is documented provenance, not just a
duration. No measured-count/histogram/residual path in the actual schema was found
mistakenly stripped. The historical behavior-preserving claim survives within
that measured scope.

## F8 — Medium — a third step-4 table row contradicts the adopted contract

**Claims refuted.** The supersession block says “Two rows of this table were
superseded.” Its remaining zero-total row says a record “contributes
`cost_base + penalty` once with no apportionment” and “Distinct structural vertices
on an all-zero-length record are one occurrence.” Revision 13 instead requires
fraction **0.0** for every occurrence pair, while §2.2/§2.4 require that fraction
to apportion cost and preserve structural occurrence keys.

**Reproducer:** `f08_zero_length_contract.py`.

For `(5,5),(5,5),(5,5)`, `same_edge_fraction` is **0.0**: the adopted partial cost
at weight 1000 is **0**, against the unsuperseded plan's **1000**. The exact pilot
retains **2 structural vertex occurrences**, `(0,'v',0)` and `(0,'v',1)`, against
the plan's instruction to merge them into one.

This is a contradictory specification, not an assertion that the current primitive
is wrong under revision 13. Mark the zero-total row superseded too, or explicitly
distinguish full topological edge traversal from a partial traversal and withdraw
its incompatible occurrence-merging instruction. A table presented as implementing
the adopted rules should not leave both instructions active.

## Surviving claims and limits of the evidence

### A and C: geometry rows, composition, remaining design gates

`verify_surviving_claims.py` independently certifies the output's exact rational
rounding cell on **2004 radicands**, including subnormal and tie cases. This compares
the original radicand with squared midpoints between the returned float and its
neighbors, rather than reproducing the implementation's binade algorithm.

| item-7 row | outcome |
|---|---|
| segment length | survives: exact endpoint differences and correctly rounded square root; the row should literally say rounding the **root of** the radicand |
| prefix arclength | survives as `RN(sum of the specified rounded terms)`, including the partial in the same `fsum`; not RN(real arclength) |
| projection/clamp | survives: exact rational dot products and exact clamp; degenerate returns 0; W2/W3 and an interior parameter whose float image is 1 are pinned by the 40 fixtures |
| traversal fraction | survives as correctly rounded division of the defined rounded prefix/total; it is not one rounding of the true geometric ratio |
| same-edge interval | current code implements an oriented symmetric magnitude, one-segment absolute parameter difference, and rounded partial/full terms under `fsum`; 400 symmetry/range checks pass; text should spell out the one-segment case, symmetry, total-length rule and summation order explicitly |
| zero total | the primitive implements fraction 0.0; F8 identifies the incompatible plan row |

One correct rounding is nearest to **that exact partial**, so a two-rounding float
cannot be closer to that partial. This argument survives. It is not a theorem
about subsequent prefixes, totals, fractions or route selection: errors can cancel
in later operations. The design's revision-13 qualification expressly acknowledges
this. `fsum` rounds a sum of already-rounded terms, and division rounds again.
The script certifies **4.16227766016838** for the adopted total on `(0,0),(1,0),(2,3)`
against **4.162277660168379** for RN(real total). The existing W5 test pins the
**1 s versus 994.1125 s** argmin limitation; it is disclosed, not a new finding.

Items 5 and 6 correctly remain open. The rounded-argmin witness is exercised by the
40 fixtures. I also ran pass 37's `f03_scalar_search.py`: final rounded costs tie at
`2**54`, the normative time discriminator gives **2 s**, and scalar-prefix
pruning gives **1001 s**. Item 7 does not solve that search problem. These results
support retaining both gates. No new contradiction with the §9 wire contract was
established: it encodes the resulting quantity and does not repair its arithmetic.
The exact-cap/rounded-band inconsistency in F1 remains a contract issue beyond the
acknowledged real-argmin limitation.

### D: the T0 measurement and both real C witnesses

`verify_real_witnesses.py --extract` prepared the real local graph, checked the
artifact's graph SHA-256 and **808433** design-record count, and extracted every
window geometry for both recorded adoption examples. `real-witnesses.json` makes
the subsequent reproduction runnable without the private data/cache. Its default
run replays those geometries through the committed pilot. `explain_adoption_diff.py`
was also run successfully against the full graph.

| witness | retained displacement | exact residual gap | float residual error on nearer segment |
|---|---:|---:|---:|
| first centroid | **3.562794224442979e-5 m** | **2.8883562208648073e-11 m** | **1.0130563055099628e-10 m** |
| second centroid | **6.998565223626435e-6 m** | **1.3820056210533949e-12 m** | **1.524611548120447e-10 m** |

Both C swaps reproduce, with unchanged counts and changed segment/vertex labels.
The first mechanism and the quadratic corroboration survive:
`(3.56e-5)**2/(2*21.97)` is approximately **2.8843e-11 m**. There are **zero raw
per-segment clamp flips** in these windows. That counter compares the right thing
for W2/W3: the end-to-end synthetic witnesses each increment it by **1**. Comparing
each segment with itself does **not** exclude a clamp flip; switching which
segment supplies a record minimum is a different event, as the write-up already says.

The artifact's five sets sum to **844685 points**, **36555718 positions**,
**2142080 residual differences**, **16459230 arclength differences**,
**1333808 rounded-parameter-image differences**, **42 rounded-XY movements** and
**0 per-segment clamp flips**. Maxima are **2.396749465560788e-10 m** residual,
**7.275957614183426e-12 m** arclength and **4.656612873077393e-10 m** XY movement.
These are verified artifact totals, not an independent repetition of the entire
50-plus-minute adoption census. F4 shows why one label needs correction.

Window correspondence survives inspection: both calls construct the radius/window
using the same unchanged STRtree/GEOS query before arithmetic dispatch, then
enumerate those records and segments in the same order without arithmetic-dependent
skipping. For this fixed tree the zipped positions correspond. The runtime checks
only equal list length; asserting equal windows and `(record,seg)` sequences would
make this assumption executable. No actual mispairing was found.

The 1 micrometre places tolerance is intentionally blind to subnanometre drift.
The raw block is useful evidence of that drift, subject to F4. A zero places count
does not establish exact occurrence equality, absence of a sub-tolerance candidate
swap, or unchanged routes. Likewise the large A band makes stability unsurprising
away from its boundary; zeros constrain the measured points under the implemented
predicates, not unseen boundary configurations, frame-C area, weighted journey
effects or routed verdicts. No routing-impact claim is established here.

C is explicitly defined using equality of *computed binary64 residuals*. Changing
those operands changes its operational retention decisions, so retaining a distinct
label/evidence series is defensible. `C_exact` still uses rounded residual equality:
it is not an exact rational per-record minimum. A retains its high-level band form,
but calling it the *same fully specified numerical rule* requires the predicate
qualification in F1. D retains its exact squared-distance selector; its output
locations/labels/caps need not thereby be exact or unchanged.

### E, F and G: refactor, cache, and mutation retirements

The historical **610-leaf refactor comparison survives**. In addition,
`verify_surviving_claims.py` extracts the old function from the committed source
and compares it with the imported implementation on **2005** cases, including
W2/W3, degeneracy and clamps: **2005 exact agreements**. The boundary change
`<`/`>` to `<=`/`>=` returns the same Fraction at 0/1. F7 limits the general tool,
not the observed historical agreement.

The cache equivalence **survives under its documented precondition**: it must
contain this unchanged geometry's actual `segment_lengths`. Both branches then
use the same preceding floats and recompute the same partial, so equivalence is
structural, with **400** additional checks. An invalid cache `[2,1]` on lengths
`[1,1]` gives prefix **2.5** instead of **1.5**; the code does not validate caches.
That is a caller precondition violation, not a counterexample using a valid cache.
The pilot constructs the cache immediately from the same geometry.

The retired `denom=1` degenerate mutation is equivalent because its numerator is
zero. The retired step-up loop is dead because
`floor(sqrt(floor(x))) = floor(sqrt(x))` for nonnegative x. The rounded-scaling
retirement has **2000** additional checks: **224** changed lattice indices and
**0** changed answers. Its bounded-reachable-index argument survives; it does not
justify an *arbitrary* off-by-one index. The harness's older comment still uses
that broader wording and names a nonexistent old test; the current `_decide`
docstring and current test correctly state the narrower guarantee. The additional
zero-total=1 equivalence comment holds for genuine zero-length geometry too.

### Validation performed and environment limitation

- All nine review/check programs in `run_all.py` exit 0; outputs are in `RESULTS.txt`.
- Unmodified `test_exact_geometry.py`: **40 fixtures pass**.
- Original `mutate_exact_geometry.py`: **22 reported caught**, source restored
  byte-identically; F3 explains the crash and missing coverage.
- `render_t0_results.py --check`: **matches the committed artifact**.
- Both real census witnesses reproduce; full-graph extraction and standalone
  snapshot replay succeed. The full adoption census was not rerun.
- The requested full-suite command was attempted. It encountered numerous
  `PermissionError` failures setting up temporary directories. A retry with an
  explicit workspace `--basetemp` also failed with WinError 5, including session
  cleanup; no clean full-suite result is claimed. `suite-output.txt` preserves
  the retry output. The generated `pytest-tmp` directory cannot be accessed or
  removed in this session. Automatic approval review rejected a broader cleanup
  command as blocked by policy; a narrower nonrecursive empty-directory removal
  also failed with access denied. No reviewed implementation was changed to work
  around these environment restrictions.
