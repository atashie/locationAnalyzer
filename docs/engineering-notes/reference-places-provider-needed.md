# We need a places data source, and Yelp is the wrong one

> ## MEASURED 2026-11-17. The objection is refuted; FSQ reaches what OSM cannot, with a caveat.
>
> Owner: *"3) yes, that sounds great, proceed."* Results in
> [[project-phase1-s3-fsq-coverage]]; script `v2/scripts/measure_fsq_coverage.py`.
>
> **FSQ holds a place within 120 m for 321 of the 334 records OSM could not reach**, at a median
> 4.4 m (grocery) and 13.8 m (pharmacy) for name-agreeing matches -- the same business, not a
> neighbour. So the overlap-with-Overture objection this note raised is answered: FSQ adds records
> our Overture extract does not reach.
>
> **But two findings outrank that number, and one corrects this note.**
>
> * **FSQ's categories are reliable in one direction only.** 16 of 26 "not a retail pharmacy"
>   proposals deny what the record's own name asserts -- FSQ calls Fuquay Pharmacy a *dentist* and
>   Kroger Pharmacy a *doctor's office*. Positives are corroborated; negatives are not. The rule
>   is **confirm, never reject**, and the check now runs on every invocation.
> * **This note's claim that FSQ supplies the missing "range" signal was WRONG.** The taxonomy
>   separates Supermarket from Grocery Store; the data does not apply it consistently. Among
>   unambiguous big chains in our bbox the split is 155 Supermarket / 38 Grocery Store / 1
>   Convenience Store, with Trader Joe's, Publix and Wegmans in *both* main buckets and Lidl in
>   three. Harris Teeter and Lidl came back as "Grocery Store". So 44 of the 58 grocery proposals
>   carry no information about store size, and **nothing available to us measures range** --
>   `OSM_CONFIRMED_SPECIALTY`'s holding position stands.
>
> **The unlooked-for win:** `date_closed`, a field neither OSM nor Overture carries. 25 records are
> marked closed, 12 of them high-confidence, including Kroger (2013) and Kroger Pharmacy (2019) --
> independent corroboration of a call the owner had already made on other evidence.
>
> **Conclusion unchanged on Yelp, sharpened on FSQ:** adopt FSQ as a corroborating source on the
> footing of the `OSM_CONFIRMED_*` tables -- existence, identity and closure -- and never as a
> classifier. Do not open a Yelp account for the V2 job.
>
> Everything below is kept as written, except that the "range signal" claim is corrected above.

**2026-11-17.** Owner decision: *"Let's document the need for tripadviser or yelp api, but defer
integrating the api. We can implement that in a future session."*

So this note records the need and stops there. Nothing here is built. But looking up the licence
terms changed the answer to *which* source, and that is worth knowing before anybody opens an
account.

## Two different jobs want a places source

They are usually discussed together and they are not the same job.

| | what it needs | who sees it |
|---|---|---|
| **V1 premium search** | live-ish detail for a handful of places inside a polygon: rating, reviews, price, photos | a user clicking "Premium" in the web app |
| **V2 classification backfill** | one durable fact per record — is this a weekly-shop supermarket? is this a dispensing pharmacy? | every household using a published layer |

V1 wants **depth, on demand, for a few**. V2 wants **one attribute, once, for hundreds**, written
into a committed table and published. A source can be fine for one and forbidden for the other.

## The backlog this is blocking

From `scripts/prefill_from_osm.py` (commit `eb0f6da`), the records OSM could not reach at all:

* **154 of 314 unclassified grocery records** have no OSM feature within 120 m
* **180 of 403 pharmacy records** have no OSM feature within 120 m

These are not hard cases, they are *absent* cases — nothing nearby carries a `shop`, `amenity`,
`healthcare` or `leisure` tag, so there is no tag to agree or disagree with. No amount of better
matching fixes them. They need a second source or they stay unknown.

OSM is also silent on the thing the grocery definition actually turns on. `shop=supermarket` is one
tag doing two jobs: it is applied to a full-service weekly-shop grocer and to a large international
market alike. Separating them needs a signal that measures **range** — floor area, department or
aisle counts, a product-range or category list — and neither OSM nor Overture holds one. That is
recorded in `OSM_CONFIRMED_SPECIALTY` as a holding position.

## Yelp cannot do the V2 job, and the reason is the licence

This is the finding that matters. Yelp Fusion's API Terms of Use bar caching, recording,
pre-fetching or otherwise storing Yelp content **beyond 24 hours of receipt**, with narrow
exceptions for non-commercial analysis and for storing business IDs for back-end matching. Bulk
download is barred separately.

**The V2 job is precisely the forbidden thing.** It would take a Yelp category, decide
`supermarket` from it, write that into `grocery.py`, commit it, and publish a layer derived from it.
That is storing Yelp-derived content indefinitely and building a database of business listing
information from it.

It also runs straight into **Decision 17**, which this project already made for its own reasons:
contractually restricted sources must never enter an ODbL-published artifact. The published V2
layers are ODbL. A Yelp-sourced classification inside them is the same category of mistake as a
Google place id inside them.

Yelp may still be legitimate for **V1 premium search**, which displays live results to a user and
caches nothing beyond the session. That is the use its terms are written for. The two jobs diverge
exactly here.

> The terms are versioned and were being revised during 2026; the January 2025 version is the one
> read here and a 2026 revision is reported but was not confirmed against Yelp's own page. Read the
> current terms before relying on any of this. The conclusion is not finely balanced, though — a
> 24-hour storage cap is nowhere near what the V2 job needs.

## Foursquare OS Places looks like the right source, and it is not an API

**FSQ Open Source Places** is Foursquare's places dataset released under **Apache 2.0**: ~100M
global POIs, ~22 core attributes, refreshed monthly, distributed as Parquet. Free, commercial use
permitted, attribution required.

That is the same *shape* as the data this project already uses. It is a file on disk, not a metered
API. No key tied to a billing account, no per-call budget, no 24-hour cache rule, no quota to run
out of mid-build, and the licence permits exactly what the V2 job does. It is also reproducible: a
dated release path means a build can name the snapshot it used, which a live API can never offer.

It would serve V1 premium search too, with no provider at all — a local spatial lookup instead of
a network call.

**The obvious objection, which is unresolved: Foursquare also contributes to Overture, and our
places data is Overture-derived.** If FSQ's records are already in our extract, FSQ adds nothing
for exactly the 154 and 180 records that need it. Nobody has checked.

## The one measurement to take first

Before any integration, before any account:

> Join FSQ OS Places against the 154 grocery and 180 pharmacy `no match` records, and count how
> many get a usable category.

It costs one dataset download and one spatial join, it needs no credentials, and it converts this
note from a plan into a number. If the answer is near zero, the overlap objection is correct and
the backlog needs a different source. If it is large, the backlog is cheap to clear and the licence
is already compatible with publishing the result.

Nothing in this note authorises doing that.

## Where the code is ready

`backend/app/services/places/` is the seam, left behind when the TripAdvisor client was removed.
A provider implements `PlacesProvider` — `nearby_search`, `monthly_usage`, `monthly_limit` — and
calls `register_provider(...)` at startup. Until one does, `POST /api/v1/premium-search` returns
**503** and says so.

The one rule that package enforces: **a transport failure raises `ProviderUnavailable` and is never
cached**. The client that was removed returned `None` for both "the API refused us" and "no such
place", and wrote the result to disk as `{"found": false, "error": null}`. See
[[reference-tripadvisor-content-api-retired]] and `backend/tests/test_places_cache.py`.

## What this note does NOT say

* It does not say Yelp is unusable. It says Yelp cannot source a **persisted, published**
  classification, which is the V2 job. V1 premium search is a different question.
* It does not establish that FSQ OS Places helps. The overlap with Overture is unmeasured and is
  the first thing to check.
* It does not claim the 154 and 180 are wrong. They are **unknown**, which is a different and
  honest state. Pharmacy is not a published layer at all, so none of it is in front of households.

Sources: [Yelp API Terms of Use](https://terms.yelp.com/developers/api_terms/20250113_en_us/),
[FSQ Open Source Places announcement](https://foursquare.com/resources/blog/products/foursquare-open-source-places-a-new-foundational-dataset-for-the-geospatial-community/),
[FSQ OS Places docs](https://docs.foursquare.com/data-products/docs/fsq-places-open-source).

Related: [[reference-tripadvisor-content-api-retired]], [[project-v2-rethink-decisions]],
[[project-phase1-s3-destination-identity]], [[project-phase1-s3-progress]].
