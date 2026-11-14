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
sourced from Overture or Google**. Neither forbids publishing these names. What does need care is
that the travel-time layer *is* ODbL-published and ODbL is share-alike, so merging a permissively
licensed name table into it invites the question of whether the result is one derivative database.

The side table is therefore **a separate artifact with its own licence block**:
`<stem>_selected_destination_table.json` beside the layer, published as
`<stem>.destinations.json`. That keeps the share-alike layer and the permissive name table as two
files with two licences, and it keeps decision 17 satisfied without having to argue about
derivative-database boundaries.

Only what is needed to name a destination is carried: the GERS id, the name, the brand, the
category and the operating status. **Deliberately omitted:** phones, emails, websites, socials,
addresses, and any upstream provider record id. Minimum necessary, because the cheapest way to
avoid a licensing argument is not to carry the field.

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
reprojection. That second check earns its place for a reason beyond this plane: value, status and
destination are three **independent** nearest-resampling calls, and pass 48 measured that 0 of
330,502 shipped cells take a mixed triple — a measurement, not a guarantee. The destination
plane's two-directional invariant is the first check in this pipeline that would actually *catch* a
mixed triple, because a status drawn from one source cell beside a sentinel drawn from another is a
contradiction the bytes themselves express.

## The format, with its price on the record

A `uint16` plane, little-endian, declared. `uint8` is not an option: 510 candidate destinations
exceed a 254-entry palette, and more to the point **a plane whose width depends on the data is a
format that breaks silently when the data changes.**

`uint16` brings a problem no other plane has: **a byte order.** Every other plane is a byte, where
the question does not arise. Read with the wrong order, this plane's ordinals are *valid* — they
index real destinations — and wrong, so the failure mode is a confident incorrect shop name rather
than an error. Nothing in the bytes can catch it. Hence the order is written through an explicit
`<u2` dtype rather than `tobytes()` on whatever the caller held, declared in the manifest, and a
decoder that cannot confirm it must refuse the plane.

`scripts/price_destination_encodings.py` prices the alternatives, including one that is **free** —
renumbering the ordinals by first appearance in row-major order, which changes which integer names
a destination and nothing else. Pass 48's twenty-fifth instance was defending a format with a
measurement of the option that was chosen, so this measurement was built before the argument.

## What is still open

* **Which place on a shared node.** Not computed, by design. Resolving it needs either a rule
  (nearest to the node? largest? first by id?) or a finer routing target than a node, and the first
  is an invention and the second is a model change.
* **Whether the destination moves at a cost tie.** Pass 48 found the route flag is order-dependent
  at an exact cost tie and reaches 0 nodes on this graph. The destination is the *same argmin* and
  is **shown to a household**, so the stakes are higher: a tie means the name we print is decided
  by heap order. `scripts/persist_selected_destination.py --ties` measures it with the same
  instrument.
* **The card itself**, which is the remaining interface gap for all three owed disclosures.
