# Codex adversarial review, pass 13 — the pass-12 fixes, S2.3 and S2.4

**Date:** 2026-11-04. **Model:** gpt-6.1-sol. **Head at review:** `dca5b49`. **Prompt:**
`codex-pass13-prompt.md` (scratchpad).

**Eleven defects: 4 High, 5 Medium, 2 Low.** Every headline number reproduced — Codex re-binned the
522,160 buildings and reproduced the count raster exactly, and matched the coverage, threshold and
classification figures to the digit. The verdict that matters is not about a number:

> "The headline numbers reproduce, but the access audit does not establish the lawfulness or
> coverage-loss bound claimed."

That was right, and S2.3 was reopened the same day.

## What it verified

- Building coverage 499,009 / 512,633 = 97.3423%; cell coverage 256,752 / 330,502 = 77.6855%;
  off-network 3,657 and beyond-horizon 9,967 buildings; 9,527 outside the grid; the 15-minute
  split 14.3706% / 31.9624%; the classification 26,395 / 539,814; the strict comparison
  5,533 cells and 4,881 buildings.
- **Boundary assignment in the building binning is consistent**: internal boundaries go east/south,
  west/north outer edges are included and east/south excluded. The 9,527 outside centroids are
  consistent with the envelope being larger than the UTM rectangle.
- The restricted-edge reconciliation: **126,197 raw → 127,426 symmetrised → 123,024 in the retained
  component → 117,253 in the CSR**. `access.py`'s documented 126,157 is a historical count, not an
  error.
- The predecessor recurrence and destination-root test are correct for a positive-cost
  multiple-source search; the CSR data alignment holds; the OS lock starts at deterministic offset
  zero and truncating a POSIX inode does not remove its advisory lock; the float32 check uses the
  writer's cast direction; exact snap ties remain reachable so the time preference is not dead code.
- The H2 `(score, -reading)` choice is "consistent with score-first ranking", and taking the minimum
  reading independently "would manufacture evidence again".

## The four High defects in S2.3, and the rebuild

All four say the same thing in different places: **the strict surface was not the policy it
advertised.**

1. **The cell snap re-admitted restricted travel.** A cell halfway along an open edge inherits its
   node's restricted-first-hop route, so the restricted edge ends up *inside* the cell's journey.
   Codex's case — A→B open, B→C restricted, C→destination open, every edge 10 s — gives the correct
   node answers (∞ at A, 20 s at B) and **25 s at a cell halfway along A→B**.
2. **The "unpenalised" branch still charged penalties.** Both branches shared one `EdgeIndex`, whose
   edge costs carry the access penalty; `node_cost=T_strict` changes only the node term. A cell a
   quarter along a restricted edge reported 22.5 s where the permitted branch takes 17.5 s, falsely
   losing it at a 20 s horizon.
3. **Edge position does not establish lawfulness.** Splitting one driveway into two edges changes a
   journey's verdict without changing the journey. And being the first edge does not establish that
   a private road serves *that* property or that the traveller may use it — `access=private`
   describes restricted public access, not entitlement. So 26,395 is measured; "26,395 unlawful
   routes" is not supported.
4. **Lawful alternatives were discarded before the policy was applied.** The filter ran on the CSR,
   after `graph_to_cost_time_csr` collapsed parallel edges to the cost-minimal one. Where a
   restricted edge won that contest, removing it removed a slower *public* parallel edge too: **27
   directed node pairs** in the real graph, with **2,673** more where a restricted winner hides an
   open alternative.

> "Omitting destination-end access alone cannot make this implementation a conservative bound."

### The rebuild

`locfinder/traveltime/policy.py` with `tests/test_policy.py`, driven by
`spikes/s2_access_lawfulness_v2.py`. The lawful journey set is stated as a **language**:

        R* O* R*

— a restricted chain from the origin, an open middle, a restricted chain into the destination. A
*chain* is invariant to how a driveway is divided into ways, which is what kills defect 3. The
language is recognised by a three-state automaton, so policy-respecting shortest paths are shortest
paths on the **product** of the graph and the automaton; and the language is its own reverse, so an
arrival search uses the same three states with the chains exchanged. Costs are **times** (defect 2),
and edge classes are separated on the **multigraph before any collapse** (defect 4).

Every one of Codex's four counterexamples is a test, plus two soundness invariants. One of those
invariants then caught a defect of my own: comparing the lawful time-minimum against the *shipped*
surface made **26,376 nodes look faster under the policy than without it**, which a subset of
journeys cannot be. The cause was mixing two things — the shipped surface reports the time along the
**cost**-selected path, an upper bound on the minimum time (pass-8 H2), so the baseline has to be
the unrestricted *time* minimum. `unrestricted_arrival` exists for that, and `min_time` builds it
(`sp.csr_matrix.minimum` is unusable: it treats a missing entry as a stored zero, and zero wins a
minimum).

**Results, on the right baseline:**

| | value |
|---|---|
| directed pairs with **both** an open and a restricted edge | **2,700** (= Codex's 27 + 2,673) |
| nodes with no journey in `R* O* R*` | **2,833 of 539,814 — 0.5248%** |
| nodes lawful but slower | 38,939; median **+12.3 s**, p90 +312.6 s, max +5,318.5 s |
| lawful faster than the baseline (must be 0) | **0** |
| buildings served within 120 min, no policy → under it | 507,037 → 504,945 |
| **cost of the policy** | **2,092 buildings — 0.4126%** |
| split invariance, subdividing every restricted edge | finiteness identical, **max diff 0.000000 s** |

The split-invariance check is the direct demonstration that defect 3 is gone: subdivision cannot
change the journey set, so a measure of journeys must be unchanged, and it is — exactly.

**Reported against buildings, not cells, and the reason is defect 1.** Carrying three automaton
states through the production cell snap is a real change to a tested module, and the state rule is
subtle: a cell reached along an *open* partial edge may continue only in states 0 or 1, while one on
a *restricted* partial edge may continue in any state. Rather than ship a second cell-level number I
am unsure of, the audit reports nodes completely and weights them by buildings assigned to their
nearest node — a building's own access leg is off-network, so all three states are admissible from
it and the subtlety does not arise. **No cell-level strict surface is claimed.**

## The resolver: three more over-corrections, and a change of method

M5, M6 and M7 were all mine, in `resolve.py`, which makes **four consecutive passes** finding
over-corrections in one file.

- **M5** — `at_end` was reconstructed by comparing tokens, which misreads a query whose remaining
  name begins with the same word as the locality removed from its end. "Durham Coffee in Durham"
  never produced the trimmed reading and resolved **confidently** to a different shop called "Durham
  Coffee In" (1.0 against 0.5667). Fixed by returning the split side from the split. The outcome is
  now `ambiguous` with both exact matches offered, which is the honest answer — Codex expected it to
  resolve to "Durham Coffee", and two exact matches on two legitimate readings is what `ambiguous`
  is for.
- **M6** — `STOP_INTENT_WORDS` listed `bus`, `bay`, `stand`, `shelter`, every one of which is an
  ordinary part of a business name, so a bus stop called "Bay Leaf Indian Cuisine" beat the
  restaurant 1.0 to 0.83 *and* suppressed the abstention. Now explicit **phrases**, and only at the
  **tail** of the query — my own test caught that phrases alone still fired on "The Bus Stop Cafe
  Company". The transport noun is the head of the phrase and the head comes last; this also puts the
  residual error in the safe direction, since missing an intent costs an abstention while inventing
  one costs a confident wrong answer.
- **M7** — role *equality* is only as good as the role assignment, and I had added five
  plausible-sounding categories to the fixture list in one go. `halt` sat with the platforms, and
  `kiosk`/`information` were called fixtures, so three real cross-source copies stopped corroborating
  each other. `halt` is now a `station`; `kiosk` and `information` are destinations.
- **L1** — every lock failure was reported as contention, so an unsupported filesystem was retried
  for 1,800 s and then blamed on a phantom holder. Non-contention errnos now raise.
- **L2** — `matched_on` came from the geometry winner, so a candidate scored 0.95 from an alias only
  Overture carried reported `name:contains` from the OSM record. Now taken from the evidence.

**And then the method changed.** Four rounds of point fixes, each closing the reviewed case and
breaking an adjacent one, is evidence about the method rather than about any one fix. The only thing
that caught every regression was a graded real-data benchmark — which had **five** graded queries.
So `benchmarks/resolver_queries.json` now holds **41 graded assertions** with intended answers
written down first, and `spikes/s2_resolver_benchmark.py` runs them.

It found six live defects on its first run:

- a **medial apostrophe** was replaced by a space, so "Trader Joe's" tokenised as
  `['trader','joe','s']` and the two spellings of one query returned different leading candidates.
  The pre-existing test used a *trailing* apostrophe, where a space is harmless, which is why this
  survived;
- a **bare locality query resolved confidently** — "Chapel Hill" to a **gym** 6.2 km away — because
  Overture's listing noise contains records whose name is exactly a place name, and a sole exact
  match scores 1.000 and wins outright. Now never confident, generalising the recorded "RTP" area
  gap. "Durham" had been passing only because the record of that name happens to sit 520 m from the
  reference;
- the **reference-feature demotion only broke exact ties**, which essentially never occur; widened
  to the ambiguity tier, where an exact alias match at 0.95 against an exact name match at 1.00 now
  correctly promotes the real place;
- and **two of my own assertions were wrong**, which is worth recording as plainly as the code
  defects. "Duke Hospital" demanded a non-stop leader, which no reordering can deliver when the
  platform is the only exact match and the nearest hospital scores 0.7833 — that is the naming gap
  pass 10 identified — and it used `offered_near`, which *the platform itself satisfies* by sitting
  56 m from the hospital. An assertion the wrong answer can pass is worse than no assertion.

**40 of 41 pass. One is deliberately red**: the query "parking" resolves confidently to an Overture
listing named exactly "Parking". Unlike a bare locality, this index legitimately holds car parks, so
the honest fix is to route a bare category noun to the *category* criterion rather than to the
anchor resolver — a product-routing decision, not a scoring tweak, so it is recorded rather than
guessed at.

## The documentation defects

- **M8** — the rural-desert conclusion exceeded the evidence. `BEYOND_HORIZON` establishes a long
  route *through the retained graph to the selected destinations*; it does not exclude a missing
  connection, a pruned component, or an omitted grocery, and "a road within 200 m" does not
  establish it is the *appropriate* road. **274** beyond-horizon and **20** off-network buildings in
  that region also fall outside the evaluation bbox. Now a **modelled long-access region**, to be
  audited before any of the 7,556 buildings is dismissed.
- **M9** — "only the second is about people" is a population inference the data does not license,
  and the caveat below it said so. Buildings are described as structures throughout, and the
  15-minute relationship is stated as what it is: the building share is **2.224×** the cell share, a
  comparison between denominators.
