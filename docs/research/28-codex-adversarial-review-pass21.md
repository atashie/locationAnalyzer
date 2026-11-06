# Adversarial review pass 21 — design revision 7, plan revision 6, corrected T4

Reviewed `v2-rethink`, HEAD `8518fab`, on 2026-11-06. This report is the only repository file written. Existing workspace changes were left alone. Counterexamples and mutations below ran in memory with bytecode and pytest caching disabled.

**T3 is still not ready to become a frozen reference.** Revision 7 repairs several earlier examples, but its replacement candidate rule still destroys distinct occurrences, and its summation rule does not determine the terms being summed. Both have executed ten-minute verdict flips. The frame protection is also bypassable, and a new wrong comparator passes all 112 T4 tests.

## P21-F1 — High — rounded arclength still merges distinct occurrences and discards the winning route

**Location:** design §2.2, candidate definition and “each is retained” promise; `v2/locfinder/measure/toy.py:295–304`.

Changing XY to arclength repairs the 400 m separation in pass 20, but rounding the arclength still merges distinct occurrences. Choosing the smallest residual does not make those occurrences interchangeable under either objective. Equal residuals choose the earlier occurrence, which is specifically the worse starting position on a forward edge.

**Executed input:** one one-way edge, time and cost both **602 s**, geometry:

```text
(0,0), (0.002,0), (0,0), (0,1)
```

Origin `(0,0)`, destination `(0,1)`. Length is **1.004 m**. There are zero-residual origin occurrences at arclengths **0 and 0.004 m**, and the intervening segment endpoint also falls in the same rounded bucket. Both zero-residual occurrences round to `0.00`. The representative rule retains arclength 0.

**Actual:** both objectives return **602 s**, FAIL at ten minutes. **Keeping the distinct occurrence:** `1 / 1.004 × 602 = 599.601593625498 s`, PASS. The loss is **2.398406374502 s** from only 4 mm of arclength. Scaling edge weight scales the loss; the design supplies no bound relating weights to this quantization.

The bucket rule is explicit, so this is not an insertion-order ambiguity within that rule. It is a conflict between the new lossy convention and the adjacent promise that distinct equally nearest positions are retained. Revision 7 has reproduced the mechanism of pass-20 F2 at a smaller arclength separation.

**Minimal fix — design amendment:** deduplicate the same occurrence, such as the two descriptions of one shared vertex, rather than every occurrence in a centimetre bucket. A segment/vertex occurrence representation can merge shared endpoints without merging a short out-and-back. If lossy merging is intended instead, withdraw the retention promise and explicitly adopt its potentially unbounded time error; it cannot be described as merely removing duplicates. Add this short-return fixture.

## P21-F2 — High — `fsum` does not specify partial-edge arithmetic, and two `fsum` implementations disagree by 999 seconds

**Location:** design §§2.2, 2.4 item 6, and §12 equivalence contract; `toy.py:140–142,409–446,486–495`.

The new rule determines the sum of supplied terms, not how those terms are formed. In binary64:

```python
0.1 * (1.0 + 120.0)                 # 12.100000000000001
math.fsum((0.1 * 1.0, 0.1 * 120.0)) # 12.1
```

Both apportion the base cost and penalty by the same fraction. Both can use `fsum` for every journey total. Exact comparison then distinguishes their answers.

**Executed graph:** a one-way edge `0→1`, geometry `(0,0),(100,0)`, time **10**, base cost **1**, penalty **120**; and a one-way bypass `0→2`, geometry `(0,0),(0,100),(10,0)`, time **1000**, cost **12.1**. Origin `(0,0)`, destination `(10,0)`. Both connectors are zero. The fast direct fraction is **0.1**; the bypass is traversed completely.

**Current oracle:** direct cost **12.100000000000001** loses to bypass cost **12.1**, so objective 2 returns **1000 s**, FAIL. **Changing only the direct cost term to the second expression above:** costs tie at **12.1**, and the travel-time tie key selects **1 s**, PASS. Objective 1 is 1 s in both runs.

There is no uniquely “right” objective-2 output until the arithmetic convention is completed. Under a grouped-edge convention 1000 is right; under a separately apportioned-component convention 1 is right. Calling both implementations equivalent is wrong.

**Minimal fix — design amendment:** specify binary64 operation boundaries: formation of full edge cost, formation of traversal fractions, partial multiplication/subtraction, connector terms, and the exact list of terms supplied to the final summation. Freeze one convention and pin this argmin decision, not merely an approximate total. Geometry length/arclength construction also needs a compatible arithmetic contract if §12 promises equivalence across implementations.

The same-multiset `.1,.2,.3` example is repaired on this runtime. I found no new same-multiset order failure here and do not claim one. That success does not address the different-multiset counterexample above, or establish a portable proof of the stronger “exactly rounded” claim.

## P21-F3 — High — private NumPy bases remain public through `.base`; pickle bypasses construction protection

**Location:** `v2/locfinder/measure/frames.py:120–160`; measurement-consumer requirement in `verify()`; build record T2.

The new public view exposes the owning ndarray as its `.base`. An underscore on `_points_base` is not needed to reach it.

**Executed input:** frame C on `GridSpec('EPSG:32617', 0, 100, 100, 2, 2)`, `n=1`, seed 7. Its point is `(77.56856902451935,22.520718999059184)`.

```python
f.points.base.setflags(write=True)
f.points.base[0, 0] += 999
```

**Actual:** the point becomes `(1076.5685690245193,22.520718999059184)` under the unchanged digest. The correct behavior is to prevent the write or refuse use of the mutated frame. A product boundary at x=100 can change a sampled agreement into a false inclusion under the same declared frame identity; at n=500, changing k=1 to k=2 changes E1b from PASS to INCONCLUSIVE.

**Second executed path:** `pickle.loads(pickle.dumps(fresh_frame))` returns a frame whose `points.flags.writeable` and `source_ids.flags.writeable` are both **True**. Direct assignment then invalidates its digest. Unpickling does not rerun this dataclass's `__post_init__`.

`verify()` detects the changed digest when explicitly invoked. Repository search found its definition and **no calls**. `write_frame` independently recomputes the digest, so the saved-file boundary is protected; the same cannot yet be claimed for future measurement consumption. T3/T5 do not exist, so this is a requirement to implement there, not evidence that existing measurements were corrupted.

**Minimal fix — implementation correction:** expose arrays backed by immutable bytes, or copies whose mutation cannot alter held contents; restore validation and protection on deserialization. Verify at measurement entry and before persisting derived results. Add `.base`, pickle, and consumer-boundary checks. Object-dtype conversion to fixed-width text removes shared mutable referents for the actual string Overture IDs; that part does not repair the buffer exposure.

## P21-F4 — Medium — a new wrong comparator passes every T4 test

**Location:** T4 corpus; `toy.py:_same_edge_direct`; `v2/tests/test_conformance.py`.

I installed this mutation in memory, then ran the entire test file:

```python
real = toy._same_edge_direct
def wrong(graph, origin, dest):
    if origin.edge == dest.edge and origin.fraction == dest.fraction:
        return None
    return real(graph, origin, dest)
toy._same_edge_direct = wrong
```

**Result: all 112 tests pass.** This is a systematic missing zero-span branch, not a special case keyed to fixture names.

**Executed distinguishing input:** one bidirectional edge `(0,0)→(100,0)`, time/cost **1000**, origin and destination both `(50,0)`. **Correct:** zero connector, zero traversal, **0 s**, PASS. **Mutant:** travels via an endpoint and returns **1000 s**, FAIL. The destination ID and eligibility do not change.

**Minimal fix — implementation correction to T4:** add zero-span same-edge cases with zero and nonzero residual connectors, and different destination IDs at the same attachment position. The nonzero-connector case must retain both explicitly required connector charges; coincidence alone does not repeal §2.1. Retain this mutant and demonstrate its rejection.

## P21-F5 — Medium — endpoint journeys omit their partial edges from the route key

**Location:** `toy.py:489,491–496`; design §2.4 route identity and journey ranking.

Direct journeys receive a directed edge identity. Endpoint journeys receive only `path_ids`, omitting both the origin-to-entry and exit-to-destination traversals. `Journey.rank_key` therefore compares different representations of a route.

**Executed input:** one bidirectional edge `0→1`, geometry `(0,0),(100,0)`, time/cost **0**, origin `(20,0)`, destination `(80,0)`. The direct route and endpoint detours all have time/cost zero. `min(journeys(...), key=lambda j: j.rank_key).route` is `()` (the empty tuple).

No empty network route travels from arclength 20 to 80. The direct route's sequence is `[forward]`; detours have sequences `[forward,reverse]` or `[reverse,forward]`, possibly with an intervening full traversal. Under normal lexicographic prefix order, `[forward]` wins. The oracle instead prefers a falsely empty route. This flips selected provenance, not a numeric verdict.

**Minimal fix — implementation correction:** include identities for every nonzero partial traversal, with its actual direction, in the route key. Specify whether zero-span partials contribute identities and use that convention on both enumeration paths. A reconstruction reference also needs traversal intervals, because an edge sequence alone does not identify which occurrences were used on a self-crossing edge.

## P21-F6 — Medium — the claimed total order still leaves objective 1's reported cost to insertion order

**Location:** design §2.4's “identical in every quantity this design reports” claim; `toy.py:336–352,572–584`.

Preserving same-identity weight alternatives repairs premature collapse. It also exposes a remaining tie: objective 1 selects on time, while the final journey key contains no cost or record discriminator.

**Executed input:** two bidirectional records `0→1`, both geometry `(0,0),(100,0)`, identical identity, both time **100**, costs **1 and 2**. Origin `(0,0)`, destination `(100,0)`. **Actual:** `objective1_cost` is **1** with the first order and **2** with the reverse order. Both objectives' times remain 100 and objective 2 correctly chooses cost 1.

The selected cost is an explicitly reported quantity. Therefore these alternatives are not identical in every reported quantity, even though all existing objective-1 tie fields agree. Correct provenance requires a specified result, or an explicit declaration that this field is not uniquely determined. No PASS/FAIL flip is claimed.

**Minimal fix — design amendment:** complete the tie order for observationally distinct records, for example by defining a final cost/weight discriminator for objective-1 ties and a stable record identity where needed. Then apply it in the oracle and add `objective1_cost` to insertion-order checks. Deterministic selection within one input ordering is weaker than the claimed invariance under reversing alternatives.

## P21-F7 — Medium — reversal by `1 - orientation` disagrees with reversal by geometry for palindromes

**Location:** design §2.4 item 1 and reverse pairing; `toy.py:163–180,355–362`.

**Executed input:** `ToyEdge(0,0, ((0,0),(1,0),(0,0)), time_s=1, cost_base=1)`. Its geometry equals its reversal, so both explicit traversals have orientation **0** under the normative definition.

**Actual:** `directed_identity(edge, forward=False)` gives:

```text
(0,0, ((0,0),(1,0),(0,0)), 1, (), 2.0)
```

Constructing the explicitly reversed edge gives the same tuple with orientation **0**. Thus reconstructing the same reversed traversal through two supported representations yields unequal identities. This changes reverse pairing and recorded route identity.

This is not another demonstrated 3800/200 numeric failure. With identical weights and all occurrences retained, a true palindrome's reverse traces the same ordered coordinate sequence, and the two descriptions can be interchangeable. The present implementation invents a distinction that the design's geometry-derived field does not have. Rounded palindromes also need an explicit policy if direction provenance is meant to survive sub-centimetre geometry differences.

**Minimal fix — implementation correction plus design clarification:** derive the reverse key from the reversed traversal using the same normalization function, rather than blindly complementing a bit. State whether palindromic reversals share identity or require a separate source-direction discriminator. Do not require both “derived only from rounded geometry” and “always different under reversal.”

## P21-F8 — Medium — lexicographic journey ranking has no minimum over some zero-weight walks

**Location:** design §2.4 journey lift and admissible path domain; `toy.py:_simple_paths` and its sufficiency argument.

Ordinary lexicographic order is defined for finite sequences of different lengths, including prefixes. It is not a well-order on all finite walks. Numeric cycle excision does not prove preservation of lexicographic provenance.

**Concrete graph:** a zero-length self-loop `0→0`, geometry `(0,0),(0,0)`, time/cost **0**, and an exit `0→1`, geometry `(0,0),(1,0)`, time/cost **1**. Origin `(0,0)`, destination `(1,0)`. Let their directed identities be A and B. Since `(0,0) < (0,1)`, **A < B**. Every route `B`, `AB`, `AAB`, ... costs and takes **1**. But `AB < B`, `AAB < AB`, and so on: there is **no smallest route** among unrestricted walks.

The oracle forbids repeated nodes and returns a finite choice. A comparator allowing all walks cannot supply the specified lexicographic minimum. Correct time remains 1 s, but the design's claimed uniquely selected route does not exist on this admitted nonnegative-weight input.

**Minimal fix — design amendment:** declare the finite route domain used for provenance, with a precise cycle-removal convention including partial-edge endpoints, or adopt an order that cannot improve indefinitely by adding zero-weight cycles. Preserve the valid statement that node-simple enumeration suffices for the numeric extrema; withdraw the inference that this alone settles the selected route.

## P21-F9 — Medium — T6 still cannot regenerate the entire mandatory report

**Location:** execution-plan T6, T9–T11; design §§11–12.

The corrected payload supplies the missing numeric operands for selection-gap, snapping, encoding, and E2 distributions. That is a real repair. It is still narrower than the promised test of regenerating **the report** without sources.

**Concrete indistinguishable routing bundles:** retain all required T6 fields identically and a reported E3 journey time of **5 minutes**. In one run the walked time is **5 minutes**, giving UNVERIFIED; in the other it is **20 minutes**, giving FAILED. T6 requires neither the E3 reported/observed records nor their walked/missing flags, and T9's implementation is a scorer rather than persistence. The mandatory T11 E3 result therefore cannot be regenerated from those routing bundles. The correct difference is a **15-minute signed discrepancy** and a changed E3 outcome, not another routing query.

Similarly, self-contained route geometry does not specify the extraction warning's boundary predicate. A route whose nearest boundary distance is **15 m** counts under a **20 m** band and not a **10 m** band. The band value and extraction footprint are not required T6 fields. A missing-path denominator must retain its population as well as the paths that survived.

**Minimal fix — plan/payload correction:** require the T9 input records and the T10 footprint/band configuration plus membership and missing-path accounting, or explicitly require separate saved artifacts containing them in the regeneration bundle. For any development grid-comparison or device-performance distributions included in the report, retain their observations/configurations too. Require rejection tests for absent report inputs, rather than treating “self-contained paths” as a substitute for all analysis inputs.

For the named routing distributions alone, I found no necessary third own objective-2 time operand. The two named operands suffice if all status, selected destination, cost and residual fields are qualified by objective and destination population. The residual payload should explicitly say whether it contains each origin/destination residual or their sum, and identify which selected journey it belongs to; “both residuals” is too loose as a schema definition.

## Checks that did not produce another defect

- **§2.1's two own operands:** the full-set selection gap and intersection E2 distinction is now explicit. The instruction that only the intersection operand pairs with the engine also determines E2 joint finiteness, status cross-tab and the `|d| > 60 s` denominator. D1/D2 should use E1's full-set objective-1 comparator; they do not require another objective-2 time. No third time operand is established by these quantities.
- **Connector asymmetry:** current normative text consistently charges own connectors to time and cost and independent-engine connectors to time only. The earlier example and historical amendment rows describe superseded rules; they should not be implemented as current policy. E2 is correctly named as including attachment and selection-policy differences.
- **Long edges:** rounding metres rather than fractions fixes the old length-scaled bucket width on a 10 km edge. It does not fix F1's loss of distinct nearby occurrences. Closed-ring arclengths 0 and length are distinct traversal occurrences despite equal XY; blindly merging them would lose legal continuation choices. Adjacent descriptions of one vertex need occurrence-aware deduplication, including consistent arclength arithmetic.
- **Zero total edge length:** the oracle avoids division by zero by using fraction 0. The design should explicitly adopt or reject that convention. I did not demonstrate a coordinate-objective verdict flip from choosing a different endpoint fraction on an isolated coincident edge, so I do not count one as a defect.
- **Sequence and float comparison:** ordinary finite, consistently typed tuples support different geometry-key lengths, different route lengths and prefix ordering. Finite `-0.0` compares equal to `0.0`; it is not itself a decision-order failure. Non-finite toy edge weights/coordinates are not rejected by all toy constructors, so a finite-input validation contract should accompany any claim of total ordering over floats. No additional numeric finding is asserted from malformed inputs here.
- **`origin_nearest_m`:** nearest distance survives cap filtering, and an empty graph returns no invented distance. `OracleResult`'s general prose equating every absent result with `NO_PATH` remains too broad for an off-network origin, but the structural fields now permit the caller to distinguish it.
- **F11 repair:** raising for negative/non-finite times is appropriate at this validation boundary. A caller must normalize a routing non-result to `None` together with termination/bound information; blindly normalizing every invalid number would erase corrupt data. Repository search finds only test callers today, so no existing production caller is shown broken by the change.

## Build-record correction audit

I checked all ten correction-table entries against the current text and available implementation/tests. The table's accounts of the old claims are accurate; several repaired claims still need narrower conclusions:

| Earlier correction | Assessment now |
|---|---|
| Pass 19: absolute `1e-10` calibration | Repaired: stricter assertions use `rel=0`; confidence calibration varies levels. |
| Pass 19: cached frame-B ordering | Repaired: `validate_population` is called on both builder paths. |
| Pass 19: tracked count-checking script | Repaired: `build_dev_frames.py` is tracked and checks both counts; the cached builder guard is explicit and caller-supplied. It is not an automatic proof that every same-size cached population is the real source population. |
| Pass 19: seed/hash reproducibility | Repaired in scope: saved points are authoritative, grid parameters and runtime are recorded, cross-version redraw is not promised. I did not rederive the reported full-data rebuild equality in this pass. |
| Pass 19: two independent guards | Repaired: the record correctly calls them complementary and does not infer joint uniformity from correlation alone. |
| Pass 20: T4/coverage completeness | Coverage caveat is improved, but F4 supplies another comparator passing every test. “Done” cannot mean full §2 conformance. |
| Pass 20: every journey enumerated | Still too broad for provenance: F1 discards distinct occurrences, F5 drops partial identities, and F8 separates numeric sufficiency from route minimization. |
| Pass 20: no more design work before T3 | Still premature: F1/F2 and the route-domain/tie issues need decisions, not another implementation-only patch. |
| Pass 20: test annotations | Repaired: the multi-segment threshold is 2 min and eligibility is distinguished structurally, not by a minimum over an added infinity. |
| Pass 20: tolerance scope | The time-only limitation is now stated correctly. The assertion that exactly-rounded cost totals settle argmin stability remains overstated by F2. |

The new claim that **all seven mutants are killed by named cases** is also too broad: the text-order route check constructs two synthetic `Journey` objects and compares their keys; it does not install a text-rank mutant and show rejection by a named graph corpus case. That unit check is useful, but its evidence should be described accurately. The final T4 coverage paragraph is substantially more candid than the opening test-file claim that the corpus covers every rule.

## Validation and environment limits

The corpus contains **17 cases**, and its digest recomputes to `e645be28…` as recorded. The zero-span mutant passed **all 112** conformance tests. Running T1/T2/T4/T9 unmutated collected **297** tests: **292 passed** and **five frame tests errored during temporary-directory setup** with `PermissionError [WinError 5]` at `C:/Users/arikt/AppData/Local/Temp/pytest-of-arikt`. Those are environment errors, not product findings. I did not bypass the restriction or claim to reproduce the full 625-test build record. No new test files or temporary repository artifacts were created.

## T3 readiness and the finish line

**No, revision 7 does not settle T3 as a frozen reference.** The remaining §2 rules admitting incompatible answers or lacking a defined selected answer are:

1. **§2.2:** retaining distinct minimizers versus merging distinct arclength occurrences into one bucket. The bucket convention alone is executable, but the adjacent retention promise is incompatible with it. Zero-length and same-vertex occurrence conventions also need explicit definitions.
2. **§§2.2/2.4:** which binary64 terms constitute a journey total. F2 gives 1 s and 1000 s while both implementations use `fsum`.
3. **§2.4 identity/reverse pairing:** whether palindromic reversal shares identity, and how explicit and synthesized reverses agree.
4. **§2.4 ranking:** selection among same-identity, equal-time records with different reported costs; treatment of partial and zero-span traversals in route identity; and the route domain/order when zero-weight cycles exist.

The two objective-2 populations and the current connector-charge asymmetry are no longer blockers. F5 is an oracle implementation error, not a reason to invent another population policy.

The finish line is a coherent contract for the four items above, independently calculated decision/provenance fixtures for them, and an oracle that represents the complete declared journey key. Require the zero-span mutant to fail and the reverse-normalization invariant to hold. State the exact arithmetic operations and route domain, then test equivalent representations against those contracts. Frame-consumption verification and the remaining bundle fields must also be implemented before measurement/freeze. None requires changing the owner decisions, allocations or acceptance thresholds.

## Is the fix-breaks-adjacent-case pattern still running?

**Yes.** The clearest fresh examples are centimetre arclength buckets destroying millimetre-separated occurrences, exact summation exposing unspecified partial arithmetic, view protection exposing its writable base, and orientation complementation mishandling palindromes. These are specific replacement-rule defects. The recurring process problem is treating repair of the motivating example as evidence that a replacement rule's domain is settled.

The appropriate next review target is a compact set of invariants and admissible-input rules exercised across representations, rather than another claim that the previous named examples now pass. Independence and a green finite corpus remain valuable evidence; neither establishes the completed specification that T3 is meant to freeze.
