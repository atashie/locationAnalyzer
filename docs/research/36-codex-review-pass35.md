# Codex pass 35 — the rebuild, the owner's decision, and the guard that had the bug's own shape

**2026-11-10.** Reviewed `44a43d3..5bbdcfb`: the owner's decision to keep the 120 s restricted-walk
penalty, `surface` and `vehicle` entering `EXTRA_WAY_TAGS`, the graph-cache manifest, the
`explain_journey` cost-selection fix, and the Triangle walk-layer rebuild. Model `gpt-6.1-sol`,
8m 56s. Reproducers in `36-codex-review-pass35-counterexamples/`.

Verdict: *"The rebuild is correct. I independently reproduced both the preserved surface with
historical `symmetrise` and the rebuilt surface with current code."*

## What it confirmed, independently and bit-for-bit

This matters as much as the findings, and the previous pass's write-up was criticised for carrying
only corrections:

| check | reproduced |
|---|---|
| changed cells | **7,246 / 330,502** |
| faster / slower | 7,227 / 19, largest 2,316.8008 s |
| buildings in changed cells | 11,436 |
| finiteness / reason changes | 0 / 0 |
| 10-minute PASS | 24,245 → 24,255, +10 / −0 |
| 15-minute PASS | 47,495 → 47,509, +15 / −1 |

Historical `symmetrise` reproduces the preserved seconds **and reasons** exactly; current code
reproduces the new seconds, reasons and lower bounds exactly; the preserved TIFF encodes its
preserved seconds correctly; both metadata files' historical digests match the preserved bundle and
their new digests match disk; all 35 audit rows keep their exact stored seconds and outcomes.
**Preserving the draw and the walked observation, with explicit rebuild annotations, was judged the
right call.**

It also confirmed the decision record reads as intended — *"the operative passages clearly choose
120 seconds under acknowledged uncertainty and decline 600 seconds. They do not present 120 as
validated"* — and that `sel_cost` matches the CSR rule exactly, including the cost-to-time fallback
and first-wins on equal cost, with no parallel-edge report left selecting by time.

On the tags it went further than the note had: a small routing example moves drive from **15.66 s to
46.98 s** and bike from **31.11 to 93.33**, leaving walk at **100 s**. So "only the digest changes"
was false for drive and bike, as the note already conceded, and the size of the consequence is now
measured rather than described. Scalar and list-valued `surface`/`vehicle` round-trip through
graphml, including lists osmnx simplification actually produces.

## F1 (High) — the manifest did not say which graph it described

The fix for a silent cache reuse had the shape of the bug it fixed. Codex wrote a valid graph and
manifest, replaced **only the graphml** with a graph lacking `vehicle`, and `load_roads_graph`
accepted it — retaining a drive edge that `vehicle=no` should remove. Neither timestamps nor content
hashes were checked, and `g1` wrote the two files separately, so a crash between them left a pair
that did not belong together.

**Fixed.** The manifest records `graphml_bytes` and `graphml_sha256` and both are checked before the
graph is read (0.5 s to hash 695 MB, against a 35 s load). `graph_declared_edge_attrs` reads the
graphml's own `<key>` declarations, so the writer refuses to certify a graph that does not carry a
tag `EXTRA_WAY_TAGS` added deliberately — the graph itself is consulted, not a claim about it. The
required set now includes **osmnx's defaults**, not just our additions; `parse` options are
recorded and checked; and `g1` deletes the manifest **before** writing the graph, so an interrupted
run fails closed. The claim is now the narrower one Codex asked for: *the guard rejects an
incompatible declared tag set and a graph whose bytes the manifest does not describe.* It still says
nothing about parsing **semantics**.

## F2 (Medium) — monitoring was a commitment described as a mechanism

The decision note said `explain_journey.py` "already names the restricted edges on a route". It
printed a name and a highway class, so a penalised private service road rendered as
`private road [service]`; nothing computed the signed-error statistic, and the surface bundle
carries no restricted-route flag.

**Fixed where it was wrong, and narrowed where it was overclaimed.** The explainer now prints each
hop's access class and penalty and a per-journey `RESTRICTED EDGES` line, so the statistic's
membership is computable one journey at a time. The notes now say the monitoring is **specified and
manual**, and name the three things that would make it a release check: a per-cell restricted-route
flag written at build time, a defined aggregation, and a gate before delivery.

## F3 (Medium) — two reports could still name the wrong parallel road

`sel_cost` fixed the route hops but not the edge *labels*. `EdgeIndex` keys entries by
`(node pair, canonical geometry)`, so two parallel roads of different shapes are different entries —
and picking the cost-minimal edge over the node pair can name a road the point did not snap to.
Codex's case: a straight 10 s service road and a curved 20 s footway sharing endpoints; a point on
the footway matched its geometry and the tool printed the service road and its time.

**Fixed** with `edge_on_geometry`, which filters parallel edges to the matched geometry first and
takes the cost-minimal among those — what `EdgeIndex` itself does. It returns `None` rather than
substituting another road, and the caller prints that.

## F4 (Medium) — the manifest tests left consequential mutations alive

| mutation | before | now |
|---|---|---|
| reject a missing `surface`, wave every other missing tag through | **survived 11 tests** | caught |
| load, swallow the exception, then validate | **survived** | caught |
| load a valid graph twice | **survived** | caught |
| omit `written_at` | survived | still survives; informational only |

**Fixed** by parameterising the missing-tag test over the whole required set and replacing the
"raises if called" stub with a **call recorder** asserting the exact call list. The new
`scripts/mutate_graph_cache_guard.py` then found a twelfth mutation the twelve tests still missed —
*ignore the graph's sha256* — because every swap test changed the file's length too and the size
check caught them first. An equal-length byte change closes it. **12 of 12 caught.**

Codex also narrowed the derived access invariant correctly: it covers the OSM way tags the access
and speed rules read, not attributes osmnx derives (`osmid`, length, geometry, node coordinates) nor
the expansion adapter's response fields, and removing a default like `oneway` survived it. The
required set now includes the defaults, and the test's docstring states the scope limit.

## F5 (Medium) — a failed prediction still exited 0

`compare_rebuild_to_stored.py` printed `NOT PREDICTED` and returned 0; its failure counter only
covered sheet consistency. **Fixed**, and verified by mutating the expected count to 7,245 (exit 1,
restored byte-identically). Codex's second point is the sharper one and is now in the docstring: an
equal count cannot establish **attribution**. That evidence is the independent reproduction of both
surfaces, which pass 34 did for the stored one and pass 35 for both.

## F6 (Low) — my XML counts were element-blind

`grep -c 'k="surface"'` counts the tag on nodes too. Reproduced with an element-aware parse:

| tag | ways | nodes | total |
|---|---:|---:|---:|
| `surface` | **165,549** | 518 | 166,067 |
| `vehicle` | **98** | 4 | 102 |
| `vehicle=no` | **88** | 4 | 92 |
| `informal` | **449** | 2 | 451 |

Corrected everywhere. The 332 directed-edge figure and its value counts were right, and nothing
downstream was computed from the wrong number — but a count is a count *of* something, and these
were counts of the wrong thing. Same class as the generalisation written the same morning in
`feedback-decide-by-measurement-not-by-argument`.

## F7 (Low) — companion documents left stale

`project-phase1-s3-step2-conditional-estimand.md` still carried 7.3358%, 24,245, 4,076, 0.5089 and
4,454; the execution plan kept an `8.2×`; the design note still called the plan revision 11; the
soft-way note still said `surface` was absent and a rebuild was needed; the soft-way JSON still
asserts the committed raster differs by 7,246 cells.

**Fixed**, and the conditional-estimand note's figures are **labelled as the pre-rebuild
measurements they are** with the current values beside them, rather than rewritten — it records a
decision and the figures it was taken on, and none of its conclusions move.

## Accepted as-is

- `written_at` being informational.
- Archived review scripts under `docs/research/` still calling `ox.load_graphml` directly. They are
  historical records of what earlier passes ran, not live call sites.
- Browser fixtures still using the older slice layers — already a §0 step 6 item.

## The lesson

**A fix for an unchecked claim can itself be an unchecked claim.** The cache guard was written
because the code's rules and the data's contents were two separate assertions with nothing comparing
them. The guard then asserted a tag set with nothing comparing it to the file — the same shape, one
level up. The thing that caught it was an adversarial reviewer writing the swap, and the thing that
keeps it caught is a mutation harness, because the tests I wrote defended the shape of failure I had
imagined. Fourth instance; see `feedback-verify-the-shape-of-the-risk.md`.
