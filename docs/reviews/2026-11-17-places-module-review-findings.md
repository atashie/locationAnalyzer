# Adversarial review findings: the places module

**2026-11-17.** Review of commit `670a4a1` against
[the prompt committed beforehand](./2026-11-17-places-module-review-prompt.md). Reviewer: Codex
`gpt-6.1-sol`. Fixes in the commit that carries this file.

**A limitation to state first:** the reviewer's shell was blocked by a Windows sandbox error
(`windows unelevated restricted-token sandbox cannot enforce split writable root sets`), so it
could not run the backend. Its backend findings are source-derived, and it said so unprompted.
It did execute the frontend component in memory with mocked dependencies. Every backend finding
below was reproduced here as a failing test before being fixed, so nothing rests on the static
reading alone.

## Verdicts, and what came of each

| # | Claim | Verdict | Outcome |
|---|---|---|---|
| 1 | A provider failure can no longer be cached as a negative | **REFUTED** | claim was overstated; narrowed, and a real related defect found |
| 2 | The three HTTP states are distinct | **CONFIRMED** | no change |
| 3 | The seam is usable | **REFUTED** | `subcategory` was unreachable; fixed |
| 4 | The removal is complete and broke nothing | **REFUTED** | `ranking_string` had no route; fixed |
| 5 | The cache has no production caller | **CONFIRMED** | dead config removed; the gap documented |
| 6 | The mutation run | **UNSUBSTANTIATED** | could not run tests; re-run here, plus two new mutations |

## The defects worth fixing, all in code written that day

**1. A cache record missing its `payload` key became a cached "no such place".** `load` used
`raw.get("payload")`, so a record without the key produced `CacheEntry(payload=None)` and
`lookup_cached` returned it without asking the provider.

This is the exact defect the module exists to prevent, re-entering through a file-format change.
And it is not hypothetical: **the V1 files have precisely that shape** —
`{"found": false, "error": null, "cached_at": ...}` — so a leftover file in the cache directory
would be read as "this place does not exist". Now `raw["payload"]`, and a missing key means
*unreadable*, which means re-fetch. Regression test uses the literal V1 shape.

**2. A timezone-aware `cached_at` crashed.** `datetime.fromisoformat` accepts an offset; the
subtraction against a naive clock raises `TypeError`, and the subtraction sat **outside** the
guarded block. Moved inside, `TypeError` already caught.

**3. Expiry was rounded down to whole days.** `(now - then).days > 7` keeps an entry for 7 days
and 23:59:59. Now compared in seconds. Inherited from V1 rather than introduced, but it was
inherited into new code.

**4. `subcategory` was accepted and silently dropped.** The request schema takes it and the UI
sends it, but the router never read it and `nearby_search` had no parameter for it — so searching
"pizza" and "seafood" produced identical provider calls. It predates the commit, and the new seam
had preserved the lie. Now part of the protocol and passed through. This broke a test double
immediately, which is the contract working: the cheapest moment to widen a protocol is while the
only implementors are fakes.

**5. `ranking_string` lost its route.** `PremiumLocation.ranking_string` survives and `Map.tsx`
renders it, but `ProviderPlace` had no such field and `_to_premium_location` never set it — a
provider could not populate a field the UI displays. Added and mapped.

**6. Four dead settings.** `places_provider`, `places_cache_dir`, `places_cache_ttl_days` and
`places_timeout` were read by nothing. `PLACES_PROVIDER=` in `.env.example` was worse than
useless: it implied that filling it in would connect a provider. All removed. A provider
registers in code and brings the configuration it actually needs.

**7. The panel showed a failure wearing the last success's clothes.** After a successful search
then a failed one, the error appeared beside a stale "1 location found" summary while the map
markers cleared, because the catch branch never reset `result`. Predates the commit; one line.

## The claim I had overstated

I wrote "a provider failure can no longer be cached as a negative result" into my own review
prompt as a universal guarantee. It is not one. `ResultCache.store` is public and accepts `None`,
and a `fetch` that catches its own `ProviderUnavailable` and returns `None` is indistinguishable
from an honest miss.

The reviewer noted its trigger violates the documented contract, and that it found **no path where
a correctly propagated `ProviderUnavailable` becomes a negative entry**. So the code does what it
should; the claim was wrong. The guarantee is now stated at its real size in `lookup_cached`'s
docstring: it protects a failure that is *propagated*, and keeping failures distinguishable is the
provider's contract, enforceable nowhere but in the provider.

## Still open, deliberately

* **The cache has no production caller.** Confirmed, and it was in the prompt as the honest weak
  point. The live fix is the 503/502/200 distinction; `lookup_cached` is a contract waiting for its
  first provider, not a boundary anything currently traverses. Wiring it would mean inventing a
  provider to wire it to.
* **`api_calls_used` counts adapter invocations, not network requests.** A provider may make
  several calls per search or none at all. Now commented rather than renamed, because the field is
  part of the response schema the frontend reads.
* **`monthly_usage` / `monthly_limit` have no callers.** The usage endpoint they served was
  removed with the TripAdvisor client. Kept in the protocol: a metered provider needs somewhere to
  report quota, and the docstring now says this plainly instead of referring to an endpoint that
  no longer exists.
* **Documentation remnants** in `brainstorm.md` and `reference-where-secrets-hide.md`. Both are
  dated historical records; `changelog.md` was treated the same way and got a new entry rather
  than edits to old ones.
* **Frontend has no test runner configured**, so finding 7 is fixed and verified by `tsc` and a
  build, not by a test. That is a gap, not a fix.

## What the review cost and returned

One prompt, one run, no edits by the reviewer. It found two defects that would have silently
produced wrong answers (1 and 2), two that made the seam unusable as documented (4 and 5), and it
correctly refused to accept a test-run claim it could not reproduce. The most valuable finding was
the one that attacked a claim I had written down myself.

Related: [[reference-tripadvisor-content-api-retired]], [[reference-places-provider-needed]],
[[feedback-a-predeclared-gate-must-be-shown-reachable]], [[feedback-codex-adversarial-review]].
