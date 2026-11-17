# The TripAdvisor key cannot be revived: the API it belongs to is retired

> ## ACTED ON 2026-11-17. The client is removed, the module is kept, the silent failure is fixed.
>
> Owner, on the three questions this note ended with: *"1) remove it, but keep that search option
> as a module that will be reimplemented via alternative apis in the future. 2) fix it. 3) known
> backlog"*, and *"Let's document the need for tripadviser or yelp api, but defer integrating the
> api."*
>
> **What was done:**
>
> * `backend/app/services/tripadvisor.py` is **deleted**, along with `GET /poi/tripadvisor`,
>   `GET /tripadvisor/usage`, the `TripAdvisorEnrichment` schema, the seven `tripadvisor_*`
>   settings, and six root-level probe scripts that pointed at the dead API. The two frontend
>   client methods for those endpoints were dead code -- nothing called them -- so removing them
>   changed no behaviour.
> * **`POST /api/v1/premium-search` stays**, now provider-neutral. `backend/app/services/places/`
>   holds the `PlacesProvider` seam an alternative API plugs into. With no provider registered it
>   returns **503** and says what is missing.
> * **The silent failure is fixed**, in the module that survives rather than the client that did
>   not. `ProviderUnavailable` is raised for a transport failure and **never cached**; an empty
>   list now means the provider answered and found nothing. Over HTTP: 503 = no provider
>   configured, 502 = provider unreachable, 200 with `[]` = genuinely nothing there. The removed
>   client could not tell these apart. 14 tests, and the two that matter were confirmed to fail
>   when `lookup_cached` is mutated back to the old behaviour.
> * Where to look next for a source: [[reference-places-provider-needed]]. Short version: **Yelp
>   cannot source a published classification** -- its terms cap storage of Yelp content at 24
>   hours, which collides with Decision 17 -- and **Foursquare OS Places (Apache 2.0, monthly
>   Parquet)** is the better candidate, with one unmeasured objection.
>
> One more defect found while removing this: `backend/` had no pytest config, so a bare `pytest`
> collected the root-level `test_*.py` scripts, which **execute at import and fire requests at the
> production backend**, then call `exit(1)`. `pytest.ini` now sets `testpaths = tests`, and the two
> scripts worth keeping moved to `backend/scripts/manual/`.
>
> Everything below is kept as written. Only the verdict moved.

**2026-11-17.** The owner suggested using the project's existing TripAdvisor key to backfill
grocery and pharmacy classifications, then asked to be walked through reviving it. Two findings,
and the second is a live defect in shipped V1.

## 1. TripAdvisor could not have done the job anyway

The Content API's `location/search` accepts exactly four categories: **hotels, attractions,
restaurants, geos**. There is no grocery and no pharmacy. V1's own `CATEGORY_MAP` in
`backend/app/services/tripadvisor.py` maps to the same four and nothing else.

So even a working key could not classify a supermarket or a dispensing pharmacy. Where it *could*
help is **park** (attractions) and **coffee** (restaurants), which between them hold 165 of the 414
flagged classification candidates.

## 2. The key is dead because the API is, and keys do not carry over

Every probe returns:

```
HTTP 403
{"Message":"User is not authorized to access this resource with an explicit deny in an identity-based policy"}
```

Tested against `https://api.content.tripadvisor.com/api/v1/location/search` with three different
`Referer`/`Origin` values — the Railway backend domain the config defaults to, the Vercel frontend
domain, and `localhost` — and with no Referer header at all. **Identical response every time**, so
this is not a domain-allowlist problem.

TripAdvisor's own reference marks the API deprecated: *"This API is deprecated. The legacy
Tripadvisor Content API is no longer being updated. Please migrate to Terra, our new and actively
maintained API platform."* Their partner portal says they aimed to have all customers on Terra by
2026 Q3; third-party trackers put the Content API shutdown at **2026-08-31**, which is unconfirmed
against TripAdvisor's own pages but is consistent with what we observe. **Old Content API keys do
not transfer to Terra** — a new account and a new key are required.

So "revive the key" is not a thing that can be done. The options are migrate to Terra or drop the
dependency.

## 3. V1's Premium Search is therefore broken in production, silently

`POST /api/v1/premium-search` is listed in `CLAUDE.md` as Implemented, and the production backend
is live at `locationanalyzer-production.up.railway.app`. It calls the retired endpoint.

**It fails without telling anyone.** `_make_request` catches `httpx.HTTPStatusError`, logs a
warning and returns `None`; `search_location` then returns `None`; the caller caches
`{"found": false, "error": null}`. A retired API and a genuine "no such restaurant" are
**indistinguishable** to every layer above, including the user, who sees an empty Premium Search
rather than an error.

The local evidence agrees. `backend/cache/tripadvisor/` holds exactly **one** entry, from
2026-01-07, and it is `{"found": false, "error": null}` — the exact shape a 403 produces. And
`_increment_usage()` is called only on a successful request, so the absence of any
`monthly_usage.json` means **no successful call has ever been recorded**.

That `error: null` is the defect worth fixing regardless of what happens to TripAdvisor: a
transport failure should never be cached as a negative result, because it poisons the cache with
"this place does not exist" for as long as the entry lives.

## What to do, in order

1. **Decide whether V1 Premium Search stays.** If it goes, delete the client, the router and the
   cache, and the rest of this note is moot.
2. **If it stays, make the failure loud before anything else.** Have `_make_request` distinguish a
   transport failure from an empty result, and never cache the former. This is independent of
   TripAdvisor and fixes a bug that would recur with any provider.
3. **Then, if the data is still wanted, open a Terra account** and get a new key. Terra is a
   different API with different endpoints, auth and pricing, so this is a migration rather than a
   key swap.

Account creation is the owner's, not a session's.

Sources: [TripAdvisor Content API reference](https://tripadvisor-content-api.readme.io/reference/overview),
[TripAdvisor Partner Portal](https://developer-tripadvisor.com/partner/).

Related: [[project-phase1-s3-progress]], [[reference-where-secrets-hide]].
