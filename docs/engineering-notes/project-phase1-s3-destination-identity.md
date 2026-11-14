# What a destination *is*, and why the artifact may not say which shop

**2026-11-13.** The owner's decision, in their words: **the node plus the set, leaving the choice
to the card.** This note records what that settles, what it deliberately leaves open, and the
licensing finding that makes publishing the names possible at all.

## The problem the decision answers

`docs/s3-decision-report.md` says a household is owed three things, and the second is *the
destination the time was measured to*. The computation always knew it —
`arrival_with_selected_destination` returns the chosen destination node beside the seconds, and
`scipy`'s `min_only=True` search hands it over for free — and the pipeline threw it away. So the
walked audit could record "ten minutes" and not "ten minutes to where", which is precisely what
made the owner's one walked journey unscorable: `measure/e3.py` needs a reported time and an
observed time **for the same journey**, and nothing in the artifact identified the journey.

Persisting the node was never the hard part. The hard part is that **a node is not a shop.** 549
of 550 grocery places snap to within 300 m of a node, onto 510 distinct nodes.

The decision report's phrasing for this — "550 places snap to 510 nodes and 75 share one" — is
right and easy to misread, so here it is measured: **36 nodes carry more than one place, holding 75
places between them.** Of the 510 candidate nodes, **432 are selected by at least one cell**, and
among those 432:

| places on the node | destinations | answered cells |
|---|---:|---:|
| 1 | 399 | 242,265 |
| 2 | 30 | 14,116 |
| 3 | 3 | 371 |

So **14,487 of 256,752 answered cells — 5.6% — end at a node carrying more than one grocery**, and
for those the artifact names a set rather than a shop.

## Why the set is the truthful answer rather than a convenience

The selection is a **cost-argmin over nodes**. The model never compared two groceries sharing a
node, because from the routing graph's point of view they are the same place: same arrival time,
same route, same cost. So *which of them a household would actually walk into* is not a fact this
pipeline computed, at any confidence.

That makes the set the honest output and a single name an invention. A card that silently printed
one of three co-located groceries would be asserting a comparison nobody ran — the same error shape
as reading minute values 251–254 as sentinels, or as reporting `restrictedIncludedCount: 0` for a
layer that discloses nothing. The artifact's job is to say what it knows and mark the boundary.

So the division of labour is:

| layer | says |
|---|---|
| the plane | the destination **node**, as a dense ordinal |
| the side table | every place on that node, with its `place_count` |
| the card | which of them to show, or "one of 3 at this corner" |

The card may legitimately choose — a UI has to put something on screen, and "one of 3" is a fine
thing to print. What it may not do is present its choice as the pipeline's.

## The licensing finding, which gates all of it

The names can be published. The grocery rows in `overture_places_accepted.parquet` carry:

| licence | rows (whole table) |
|---|---|
| `CDLA-Permissive-2.0` | 98,982 |
| `Apache-2.0` | 7,082 |
| `CC0-1.0` | 1,420 |

No ODbL, and **none of the contractually restricted sources decision 17 forbids** — no Google place
ids, no RentCast, no MLS/IDX, no portal terms. The `sources` column shows Meta as the upstream
provider under CDLA-Permissive-2.0, which is a permissive data licence requiring attribution and
notice, not share-alike.

**So the constraint is the other direction.** Decision 17's rule is that an ODbL-published artifact
must carry no contractually restricted source, and separately that **OSM contributions may not be
sourced from Overture or Google**. Neither forbids publishing these names.

The side table is **a separate artifact with its own licence block**:
`<stem>_selected_destination_table.json` beside the layer, published as
`<stem>.destinations.json`.

### Two things this note got wrong about that, corrected by pass 49

**The separation is organisation, not a legal determination (finding 4).** This note used to say
that keeping the table apart was "what keeps the share-alike layer and the permissive name table as
two files with two licences", and that it satisfied decision 17 "without having to argue about
derivative-database boundaries". Both claims are withdrawn. ODbL distinguishes a collective
database from a derivative one by the substantive relationship between the parts, not by how many
files they are stored in, and separate files do not establish independence any more than a shared
manifest establishes dependence. Decision 17 as written **permits** OSM-derived and Overture-derived
data in the same tables, provided the notices travel with them. What is actually load-bearing is
decision 17's real rule, which this table does satisfy: no contractually restricted source.

**"Publishable with attribution" described the licence, not anything the build had done
(finding 3).** The table carried SPDX identifiers and an Overture release label and nothing else.
That is not redistribution compliance:

* **CDLA-Permissive-2.0 §2.1** requires a sharer to make available *the text of this agreement*
  with the shared data. 411 published place records are CDLA.
* **Apache-2.0 §4** requires recipients to receive the licence, a statement that files were changed
  and when, and the attribution notices from the source `NOTICE`. 35 published records are Apache,
  which in Overture means Foursquare-sourced.

So `v2/licences/` now holds the texts, `scripts/export_published_layers.py` copies the ones a
bundle actually needs into `LICENSES/`, writes `ATTRIBUTION.md` with the modification statement and
the ODbL position of the planes, and **refuses to finish** if a licence appearing in a table has no
text on disk. One gap is recorded rather than papered over: Foursquare's upstream `NOTICE.txt` is
behind a gated Hugging Face repository (HTTP 401), so the bundle carries the minimum line Overture's
documentation names and says so in `v2/licences/README.md`.

Only what is needed to name a destination is carried: the GERS id, the name, the brand, the
category and the operating status. **Deliberately omitted:** phones, emails, websites, socials,
addresses, and any upstream provider record id. Minimum necessary, because the cheapest way to
avoid a licensing argument is not to carry the field. The exporter now enforces that list as an
**allowlist** — an unreviewed field or an unreviewed licence is refused rather than shipped,
because a blocklist cannot name a field nobody has invented yet.

## The invariant this plane has and the route flag cannot

Pass 48 F3 found that a route-flag plane cannot be validated from its own contents: a *clear* flag
asserts nothing, so Codex could flip one flag down and one up on the shipped plane and every check
in the pipeline accepted it. Shape matched, aggregate count matched, `flag ⇒ OK` held, the verdict
digest did not move.

The destination plane is different, and it is worth being precise about why. `DEST_NONE` beside a
published time is **not a silence but a contradiction**: a published time is a time *to somewhere*.
So this plane is checkable in **both** directions —

* a destination named where the status is not OK asserts a journey the layer does not publish;
* `DEST_NONE` where the status *is* OK means the plane and the surface disagree about whether a
  journey exists.

`wire.encode_selected_destination` enforces both, and the exporter re-enforces both *after*
reprojection.

### What that invariant does not establish — pass 49 finding 1

This note claimed the two-directional invariant was "the first check in this pipeline that would
actually *catch* a mixed reprojection triple". **That is withdrawn.** The invariant compares the
destination plane's answer-*presence* mask against the status plane's and **never reads a value**.
Codex exchanged the destinations of two shipped OK cells — cell 7 took cell 112's ordinal and cell
112 took cell 7's — and both directions held, the shipped OK count, the named count, the distinct
destination count and the zero-disagreement figure were all unchanged, and two journeys were
silently misidentified. A mask check cannot catch a defect that preserves the mask.

It is sound as what it is: a **completeness** check. Nothing found a legitimate `DEST_NONE` beside
`OK` in a layer that promises to name every destination.

The provenance check it was mistaken for now exists, in `export_published_layers.verify_provenance`.
A source-cell **index** is reprojected through the same nearest call as the planes, so each
published cell carries the identity of the source cell that fed it; then every published plane is
required to equal its source plane at that index. Three nearest calls that disagreed about which
source cell fed a published cell cannot survive that, whatever the values are. On the shipped
bundle: **330,502 of 330,502 cells trace to one source cell across all four planes, 0 uncovered.**
Two positive controls in `tests/test_export_published.py` exchange a destination and shift a
status, and both are caught — including the exchange that passes the invariant.

One related hole closed at the source: `persist_selected_destination.py` stamped the plane with a
fingerprint of whatever `<stem>.npy` happened to hold, without ever checking the two agreed, so a
fresh destination computation could be blessed against stale published seconds. It now compares the
masks before stamping. Pass 48's lesson was to bind a derived plane to its surface; the binding has
to be earned.

Also corrected from pass 48's write-up: a *clear* route flag beside `OK` is not "asserting
nothing" — it asserts that the selected route uses no restricted way. What is missing is an
independent witness to that assertion. There is still no valid reverse implication.

## The format, with its price on the record

A `uint16` plane, little-endian, declared. `uint8` is not an option: 510 candidate destinations
exceed a 254-entry palette, and more to the point **a plane whose width depends on the data is a
format that breaks silently when the data changes.**

`uint16` brings a problem no other plane has: **a byte order.** Every other plane is a byte, where
the question does not arise. Read with the wrong order, this plane's ordinals are *valid* — they
index real destinations — and wrong, so the failure mode is a confident incorrect shop name rather
than an error. No *structural* check can catch it. Hence the order is written through an explicit
`<u2` dtype rather than `tobytes()` on whatever the caller held, declared in the manifest, and a
decoder that cannot confirm it must refuse the plane.

**The decoder did not actually do that (pass 49 finding 7).** The guard refused a manifest that
declared `big` and *accepted* one that declared nothing, falling back to little-endian — so a plane
written the other way round was read as if confirmed. Silence is not confirmation; the field is now
required wherever a plane is present, and a bundle that carries no destination plane still needs no
byte order. Requiring the field cannot catch bytes that are wrongly *labelled* little-endian.
Nothing can.

And the claim that "the name comparison is the only thing that catches a big-endian read" is
withdrawn (finding 6). The vectors record the expected **ordinal** beside the expected name, so
`got.ordinal === want.ordinal` fires first and the name is never reached. What a byte swap survives
is the structural *bounds* check; what catches it is comparing against a recorded expectation at
all. `byteswap_control.mjs` also used to print `CONFIRMED` without performing an endian mutation —
reformatting the little-endian expression made its `replace` inert, and any unrelated wrong-name
defect then satisfied it. It now requires its mutation to have applied, the baseline to answer
*completely* correctly, and the mutated ordinals to be exactly `1 ↔ 256`.

### The price, corrected

`scripts/price_destination_encodings.py` prices the alternatives, including one that is **free** —
renumbering the ordinals by first appearance in row-major order, which changes which integer names
a destination and nothing else. Pass 48's twenty-fifth instance was defending a format with a
measurement of the option that was chosen, so this measurement was built before the argument.

Pass 49 finding 9 found the measurement itself wrong in three ways, and the corrected figures are
worse than the ones first published:

* It priced the destination encodings on the **source** raster and took the value, status and flag
  costs from the **reprojected published** bundle, then added the **cheapest** encoding when
  reporting the total for the bundle that ships the **chosen** one.
* It left the side table out of every total, although a household downloads it to be told a
  destination at all.
* So the headline was "4.1% of the bundle". The real figure is **59,278 deflated bytes, 20.6% of
  what ships** — plane 37,999 plus side table 21,279 against a 287,309-byte bundle.

And the access argument was a false necessity. It said answering one cell from run-length means
"expanding 330,502 run-length entries", and that an index to avoid that is "a second structure to
ship and validate". Measured: cumulative run endpoints, built at load from the same bytes and never
shipped, answer any cell by binary search over **28,989** runs in **173,934 bytes** — *less* than
the expanded plane's 661,004 — with **0 mismatches over all 330,502 cells**. So the honest reason
for the plane is **simplicity**: no decode step, no second structure to keep in step with the side
table, no code path that can be wrong only at a run boundary. That is an engineering preference
bought for a known number of bytes. **Phone latency is still unmeasured**, so nothing here is a
performance argument.

## What is still open

* **Which place on a shared node.** Not computed, by design. Resolving it needs either a rule
  (nearest to the node? largest? first by id?) or a finer routing target than a node, and the first
  is an invention and the second is a model change.
* **Whether the destination moves at a cost tie.** Pass 48 found the route flag is order-dependent
  at an exact cost tie and reaches 0 nodes on this graph. The destination is the *same argmin* and
  is **shown to a household**, so the stakes are higher: a tie means the name we print is decided
  by heap order. `scripts/persist_selected_destination.py --ties` measures it, and the measurement
  now runs its own positive control — three nodes, two destinations equidistant from one target,
  where the published seconds take one value and the destination takes **both**. It refuses to
  report if that control cannot move.

  The result is 0 moves under **three** relabellings, and pass 49 finding 8 is right that the
  earlier wording overstated it. Three permutations sample the space; they do not enumerate it. So
  the record now says what it is: evidence that ties are not being hit, not proof that none exist.
* **A destination query answered before any compute.** Fixed (finding 11), and worth recording as a
  shape rather than a bug: `verdict` is allocated at init and zero-filled, and zero means
  INCLUDED, so a guard that checked *allocation* answered `included: true` and named a shop for a
  cell no criterion had been applied to. **Allocation is not evaluation.** The reply is now
  `notComputed: true` with `included: null` — "nothing has been evaluated" is neither included nor
  excluded.
* **The card itself**, which is the remaining interface gap for all three owed disclosures.
