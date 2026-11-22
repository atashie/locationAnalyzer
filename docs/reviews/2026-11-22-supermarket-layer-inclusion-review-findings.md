---
title: "Ask 10 findings: Codex ranks the options 3, 1, 4, 2 and calls option 2 incoherent"
date: 2026-11-22
reviewer: Codex (gpt-6.1-sol), commissioned by the owner
prompt: 2026-11-22-supermarket-layer-inclusion-review-prompt.md
raw: 2026-11-22-supermarket-layer-inclusion-codex-raw.md
status: findings recorded; NOTHING APPLIED -- ask 10 is still the owner's decision
---

# Ask 10: how should the 23 admitted records reach the `supermarket` layer?

The owner commissioned this with *"have codex review our options here"*. **Nothing has been
applied.** Codex's job was to rank the options and attack the one we were drawn to.

## The answer

**Rank: 3, 1, 4, 2. Option 2 is incoherent.**

| option | Codex's verdict |
|---|---|
| **3** — admit a forced record to `supermarket` iff `classify_grocery` says `supermarket` | **preferred.** "Its tolerable failure is a visible false negative, rather than an unsupported positive." Yields **262**. Leaves the 3 unknowns unresolved. |
| **1** — a hand-listed `"supermarket"` key in `INCLUDED_PLACE_IDS` | **coherent, and the better fit if the owner wants a fixed reviewed roster** independent of future classifier changes. Must say WHICH ids: 20 → **262**, all 23 → **265** with three explicit classifier overrides. |
| **4** — do nothing, record that `supermarket` is knowingly incomplete | **coherent as a temporary operating decision.** Leaves 242. Needs an *enforceable publication condition*, because "a note alone is weak". |
| **2** — inclusion copies across categories automatically | **REJECT.** "Grocery admission establishes eligibility for the broad grocery destination set, not proof of the narrower class." |

**It corrected our framing of our own favourite.** We called option 3 "no new judgement". Codex:
*"The cross-category candidate rule is a NEW policy decision, even though the twenty positive
classifications already exist. Calling the whole change 'no new judgment' overstates that
distinction."* Accepted.

**And it corrected the premise that ask 7 forced the timing.** We argued the republish made the
divergence urgent. Codex: the exporter enumerates source surfaces and does not infer `supermarket`
publication from `grocery`, so *"rebuilding grocery does not publish supermarket… Ask 7 is a useful
occasion to review this, not a data dependency that forces ask 10 to be applied first."* Confirmed
by the republish itself, which touched no `supermarket` artifact.

**The number that decides option 3 against a classifier-only layer.** Codex counted **52**
classifier-positive, non-excluded records outside the taxonomy gate, of which only 20 are the
admitted positives. A classifier-only `supermarket` layer would be **294** — **32 unreviewed records
beyond option 3**. That is the quantity we did not have and it is what makes option 3 narrow rather
than a dressed-up option 2.

**Its own further suggestion:** a two-part per-record ledger recording taxonomy eligibility and the
owner's semantic class as *separate facts*, with the layers derived from both — *"a small, reviewed
supermarket override table is a practical version of this"*, which is option 1 with the reason made
explicit. With the warning: *"Do not silently repurpose a regenerable OSM/name table to hold manual
judgments."*

## What it found wrong in our material, verified here before crediting

| claim | status |
|---|---|
| the 23 are filed under `department_store`, `superstore` or `warehouse_club_store` | **FALSE, reproduced.** Measured: **11 `department_store`, 6 `discount_store`, 4 `superstore`, 2 with no primary. Zero `warehouse_club_store`.** The list named a primary no admitted record uses and omitted the one six of them do — the six ALDIs. Corrected in five live places; left standing in the review prompt, which is a record of what was asked. |
| "the 20 generated reasons" and "the 20 `classify_grocery` calls supermarket" are the same 20 | **FALSE, reproduced.** They overlap in 19. `182dc975` names the generator and is `unclassified`; `aec747a0` was admitted by hand and is classifier-positive. Both counts are 20 and the sets differ. |
| `supermarket` is judgement-based, `grocery` taxonomy-based | **too simple, confirmed.** `supermarket` is taxonomy **and** judgement, then explicit inclusion, then exclusion — *"This second eligibility gate is why the twenty already-positive records disappear."* And `grocery` is taxonomy **plus** owner inclusion **minus** dropped ids. |
| the bundle is a grocery walk | **too narrow, confirmed.** Seven layers, including `grocery_drive`. |
| `grocery` returns 555 | reproduced — and **532 without forced admission**, which is where that figure comes from. |
| `supermarket` 242, none of the 23 in it, split 20/3 | all reproduced independently. All 20 positives have a brand field: 14 Walmart, 6 ALDI. |
| 55 tests in `test_place_exclusions.py` | **54 functions, 55 collected items** (one two-value parameterisation). Our "55" was a pytest count, which is the honest unit, but the function count is 54. |

## The limitation, which Codex stated first and loudest

**It could not run Python or pytest.** It read `overture_places_accepted.parquet` by decoding
Compact Thrift metadata, Snappy pages and definition levels **in JavaScript**, and reimplemented the
predicates there. So:

* every number above is an **independent reproduction**, not a call to `select_overture` or
  `classify_grocery` — which is arguably stronger evidence for the numbers and weaker evidence
  about the code;
* **the mutations commissioned in question 5 were predicted, not observed.** No mutation result
  from this pass has been watched to fail. Question 4 — "assume our tests are weaker than they look
  and pass a wrong implementation through them" — is therefore **not answered**, and it is the
  question that mattered most given that rewriting all twenty reasons broke none of the previous
  fifty-one tests.
* it also declined to reproduce our historical claim about those fifty-one tests, correctly, since
  it could not run them.

It was careful about provenance in a way worth keeping: *"Do not mistake the local 2026-11-14
product export for the committed artifact"* — the tracked `fixtures/manifest.json` describes six
legacy comparison layers exported 2026-11-09, while the product bundle under `fixtures/published/`
is untracked. Independently true, and now also recorded in the republish note.

## What this leaves the owner

Ask 10 is **unanswered and now better specified**. The decision is between:

* **option 3** (262, derives class from the existing classifier, 3 records stay unclassified), with
  the honest caveat that the cross-category rule is a new policy;
* **option 1 listing 20** (262, a fixed roster, same records as option 3 but written down rather
  than derived);
* **option 1 listing 23** (265, which means explicitly overriding the classifier for `182dc975`,
  `5074229c` and `c7fee873` and saying so in each reason);
* **option 4** (242, deferred, with an enforceable condition attached to publishing `supermarket`).

Codex's own sequencing advice: option 4 now is reasonable operationally even though option 3 is its
preferred eventual policy, because the republish did not create a dependency.

**Still owed and not done by this pass:** a mutation run against `forced_into`, the category
scoping and the precedence, actually executed. That is the next adversarial pass, not a conclusion
of this one.
