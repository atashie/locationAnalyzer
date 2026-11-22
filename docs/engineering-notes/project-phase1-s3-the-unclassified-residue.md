---
title: "The largest known problem in the published layer, laid out"
date: 2026-11-22
status: measured, nothing applied; the structural decision is the owner's
---

# The published `grocery` layer does not implement the owner's definition of a grocery

Measured against the bundle republished on 2026-11-22 (ask 7). Reproduce with
`uv run python scripts/measure_published_grocery_classes.py` and
`uv run python scripts/triage_uncorroborated_grocery.py`.

## The problem is bigger than the number this was opened with

It was opened as *"78 published records nothing corroborates"*, later 76. That is a **slice** of a
larger population, and the slice was defined by the screen that happened to exist.

| | records | cells answered | share of answered cells |
|---|---:|---:|---|
| `supermarket` | 262 | 151,579 | 58.6% |
| **`unclassified`** | **258** | **117,096** | **45.3%** |
| `specialty` | 33 | 6,276 | 2.4% |
| `not_a_grocery` | 2 | 303 | 0.1% |

Shares exceed 100% because 15,833 answered cells end at a node carrying more than one grocery, so
a cell is counted once for each place on its node. The published layer is 555 records answering
258,497 cells.

**Nearly half of all household-facing answers point at a record nobody has classified.** The
76-record / 42,430-cell figure is the part of that residue where, in addition, *no source
corroborates that anything is there*.

Three nested problems, each needing a different thing:

1. **Two flat contradictions.** `Pet Dairy` (44 cells) and `Market at Colonnade Center`
   (259 cells) are published in the `grocery` layer while `classify_grocery` returns
   `not_a_grocery` for both. `Pet Dairy` is already in `NOT_A_GROCERY_BRANDS` as a dairy brand;
   `Market at Colonnade Center` is a shopping centre. No judgement is required to see this is
   wrong: two parts of our own code disagree, and the layer publishes the one that was never
   asked. The cause is structural -- `grocery` is taxonomy-based and **never calls the
   classifier**.
2. **The unclassified residue: 258 records, 117,096 cells.** `unclassified` is documented as
   deliberately neither `supermarket` nor `specialty`, because *"asserting a category nobody
   checked is how `Roofing Inc.` became a grocery"*. It means nobody has looked. It is also 46% of
   the layer.
3. **The unevidenced slice: 76 records, 42,430 cells** -- 72 `unclassified` plus 4 `specialty`,
   and **zero `supermarket`**. Nothing in Overture, OSM or Foursquare corroborates that a shop is
   at these points.

## The single cause

**Owner's definition, 2026-11-17:** a grocery means *"a supermarket you could do a weekly shop at"*
by default, **with specialty grocers selectable**.

**What is published:** Overture's `grocery_store` taxonomy wedge, plus 23 owner admissions, minus
26 dropped ids. 555 records, of which our own classifier calls 262 supermarkets.

The layer that implements the owner's definition is `supermarket`, and it is **unpublished**. The
layer a household is served is the wedge. Every item above follows from that one gap: the farms,
`Roofing Inc.`, the tortillerias, the two contradictions, the 258.

## Why the instrument we already have does not settle it

`locfinder/places/footprint.py` exists, states its asymmetry carefully, and has 84 MB of Overture
buildings behind it. The uncorroborated screen never consults it. Applying it to the 76:

| footprint verdict | records | cells |
|---|---:|---:|
| `CORROBORATED` (a big host building contains the point) | 23 | 7,353 |
| `NEIGHBOUR` (big building near, point not inside) | 23 | 7,504 |
| `REFUTED` (nothing ≥650 m² within 120 m) | 30 | 27,866 |

**It answers a different question than the one being asked.** `FLOOR_M2 = 650` is the
*weekly-shop* floor, so `REFUTED` means "not a supermarket", not "no shop here". The REFUTED set is
dominated by what are very probably real corner shops: `Jean's Neighborhood Market` (332 m²,
4,554 cells), `May's Grocery` on Mays Store Rd, `Joy Mart` (300 m²), `Foodmart` (578 m²),
`Summer Grocery Mart` (358 m²), `Variedades Orozco` (150 m²).

And `CORROBORATED` is worse than useless here, because **a big host building corroborates nothing
when the record is a unit inside it**: `Aloe Verapol, Llc` in a 994 m² building at suite
`# 120-245`; `Tower Market Place Partners` at 8,890 m²; `Body Agape Holistic` at `# 751`;
`Bar S Foods` at `Ste 106`; `Seal The Seasons` twice, at 1,741 m² and 1,870 m². This is the
borrowed-building error the module was written to prevent, **re-entering through the suite case
rather than the neighbour case** -- *a stale claim is a class, not a line*, again.

## Why this is harder than the rest of the project

**The asymmetry is inverted.** Everywhere else, the harmful act is an ADDITION and gates fail
closed by refusing. These records are **already published**, so inaction is not the safe default:
it is 42,430 cells carrying answers nobody can defend, inside 117,096 that nobody has checked.

**And the two harms land on different people.** They are not a single population:

* **Deleting** `Tienda Mi Ranchito`, four tortillerias, `El Ranchito`, `Los Portales De Butner`,
  `AZ Halal and Mangoes`, `Hill's Family Asian Markets`, `African Caribbean Market`,
  `Anchau Oriential Market` and the rest hides **real shops** from exactly the neighbourhoods whose
  shops our three sources under-record. Overture, OSM and Foursquare share that blind spot; the
  absence of a record is evidence about the sources.
* **Keeping** `Roofing Inc.` (16 cells), `No longer` (540), `Longview Poole Road` (332, a road),
  `Tower Market Place Partners` (11, a property partnership), six farms and producers (10,311
  cells between them), and the brand/wholesaler records -- `Seal The Seasons` ×2 (2,077),
  `Bar S Foods`, `McKee Foods Corp`, `Jovc Food Corp`, `Alam Food Inc`, `Insain Hot Sauce` (241),
  `KismetCrackers` (499) -- **inflates how well-served an area looks**, which is the one quantity
  this product exists to measure.

## Two constraints that rule options out before they are considered

* **Owner decision 2026-11-18**, narrowing rather than reversing: *"still refused: parsing a name
  to guess what KIND of shop something is; now allowed: looking a name up in the SAME EXPLICIT
  TABLE the brand is looked up in."* So **no rule may classify these by name shape.** A regex for
  `LLC|Corp|Farm` is exactly the forbidden move, however well it would score. The sanctioned path
  is per-record adjudication recorded with its evidence -- which is what the sheet's `verdict`
  column and `--emit` are for, and both work as of 2026-11-22.
* **Ask 8, answered 2026-11-22**: the preliminary caveat stays internal, nothing outward facing.
  That **removes the "publish it but mark it unverified" option.** A record is either in the
  household-facing layer or it is not.

## Evidence held and never read

* **Overture `confidence`.** A real field on every record, consulted nowhere. It separates, weakly:
  median **0.777** across the 76 against **0.972** across the other 479. Below 0.6 catches 28.9% of
  the uncorroborated against 6.5% of the corroborated. That is a usable **prior for ordering a
  human queue**, and not a rule -- a threshold on it would be the same semantic shortcut by another
  route.
* **The address shape as an IDENTITY signal.** A suite, unit or `#` number says the record is at an
  address *inside* something else, which is why the footprint corroborates it and why that
  corroboration is void. Roughly a dozen of the 76 carry one.
* **The Foursquare category when the name does not agree.** Currently only reaches
  `WEAK: fsq grocery category only` (30 records) and is then dropped.
* **Nothing at all** for the population that matters most: small independent grocers. The three
  sources share the blind spot, and no fourth source is configured -- the premium-search seam has
  no provider.

## What follows

The structural question is **which layer a household is served**, and it is the owner's. Until it
is answered, triaging the 76 one by one is work on a slice of a residue whose boundary was set by
whichever screen existed. The options, their sizes and the measurement that would price them are in
the chat of 2026-11-22 and are owed as asks 12-15.
