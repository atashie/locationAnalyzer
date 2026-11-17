# Adversarial review prompt: the places module and the silent-failure fix

**Committed before launching, 2026-11-17.** Target: commit `670a4a1` on `v2-rethink`.

## What changed

V1's TripAdvisor Content API client was removed (the API is retired; the key 403s from every
origin). `POST /api/v1/premium-search` was kept and made provider-neutral against a new
`backend/app/services/places/` package. The defect being fixed: `_make_request` caught the 403,
returned `None`, and the caller cached `{"found": false, "error": null}`, so a dead API was
indistinguishable from "no such place".

## The claims to attack

1. **"A provider failure can no longer be cached as a negative result."** Find a path that
   defeats this. `lookup_cached` is the only gate; is it bypassable, and is `ResultCache.store`
   reachable with a failure-derived payload?
2. **"The three states are distinct over HTTP"** — 503 no provider, 502 unreachable, 200+`[]`
   nothing found. Find an input where a failure still reads as success, or where a real empty
   result reads as an error.
3. **"The seam is usable."** Could somebody actually implement `PlacesProvider` against it, or
   does the protocol miss something premium search needs? Note the router calls only
   `nearby_search`; `monthly_usage`/`monthly_limit` are now called by nothing.
4. **"The removal is complete and broke nothing."** The two frontend client methods removed were
   claimed to be dead code. Verify. Check for orphaned schemas, settings, imports, docs.
5. **The honest weak point, stated so it is not missed:** `lookup_cached` and `ResultCache` have
   **no production caller**. Nothing in the live request path uses the cache, because there is no
   provider to cache. Argue whether that makes the "fix" real or theatre, and whether the
   `places_cache_dir` / `places_cache_ttl_days` settings are dead config.
6. **Test quality.** The mutation check (reverting `lookup_cached` to the V1 behaviour) failed
   exactly 2 of 14 tests. Are the other 12 load-bearing? Any that would pass against a broken
   implementation? `test_a_provider_that_finds_nothing_is_an_honest_empty_result` passed against
   the OLD code too, for the wrong reason — are there others like it?

## Rules

* Read the code, do not trust this description.
* Experimental results beat argument. If you claim a bug, give the input that triggers it.
* Report claims you could NOT substantiate as well, so the record shows what was checked.
* Do not edit files.
