# Owner ask 10 — supermarket inclusion review

Date: 2026-11-22. Reviewer: Codex.
Branch: v2-rethink. HEAD: 64e8f5fc01045eff175214bf42e652c40a2aa7e0.

**Status: partial execution review. The commissioned Python test/mutation run is NOT complete.**
I read the commissioned prompt, inspected the implementation and tests, independently decoded the actual accepted Parquet frame, computed the selections and exercised mutations in an independent JavaScript model. I could not launch the repository's Python code or pytest. The distinctions below are deliberate: independent numerical verification is not a passing repository test run, and a predicted test failure/survival is not an observed mutation-suite result.

Only this report was written. No source, tests, tables, data, artifacts, Git state, or temporary harness files were changed. No records or chains were added. No publication was performed. No Google data was acquired or persisted.

## Recommendation and ranking

**Rank: 3, 1, 4, 2. Option 2 is incoherent under the stated category contract.** This is a recommendation for an owner decision, not authorization to apply it.

1. **Option 3:** use grocery inclusion as a narrow repair to the taxonomy eligibility gate; require the existing classifier to supply the supermarket judgment. Keep forced_into(category) itself per-category. This yields 262 supermarkets in the independent calculation, retains all 555 grocery IDs, and leaves the three unknowns unresolved. Its tolerable failure is a visible false negative, rather than an unsupported positive. The cross-category candidate rule is a NEW policy decision, even though the twenty positive classifications already exist. Calling the whole change “no new judgment” overstates that distinction.
2. **Option 1:** explicit supermarket inclusions are a coherent alternative and the best fit if the owner wants a fixed, reviewed roster independent of future classifier changes. Specify WHICH IDs; the option as written does not say whether it lists 20 or 23. Listing the twenty produces 262; listing all twenty-three produces 265, including three explicit classifier overrides. A second table can drift, but that is controllable with set/identity tests. A record deliberately admitted to supermarket need not make classify_grocery return supermarket: the existing override mechanism bypasses classification as well as taxonomy. Make that override explicit in the reason.
3. **Option 4:** coherent as a temporary operating decision while supermarket remains unpublished. It leaves supermarket at 242. Give the deferral an enforceable publication condition; a note alone is weak. Ask 7 does not make this incoherent: rebuilding grocery does not publish supermarket. For an immediate grocery-only republish, deferring ask 10 remains a reasonable operational sequence even though option 3 is my preferred eventual policy.
4. **Option 2:** reject. Grocery admission establishes eligibility for the broad grocery destination set, not proof of the narrower class. Unconditional inheritance promotes all three unclassified records today and would promote a future deliberately admitted specialty shop or classifier-rejected record too. “Unclassified” means unknown, not proven unsuitable, but unknown still cannot support automatic supermarket membership. This is not a claim that those three real businesses are unsuitable; it is a claim about what the rule has established.

An additional option worth considering is a two-part per-record decision ledger: independently record taxonomy eligibility and the owner's semantic class, and derive the layers from those distinct facts. A small, reviewed supermarket override table is a practical version of this. It can resolve the three unknowns without making grocery membership itself a class assertion. Do not silently repurpose a regenerable OSM/name table to hold manual judgments, and do not turn a chain-bearing name into automatic admission.

## Numerical verification and corrections to the prompt

Method: read v2/data/triangle/overture_places_accepted.parquet through Node filesystem APIs; decode its Compact Thrift metadata, Snappy pages, dictionary/plain strings and definition/repetition levels in memory; independently reproduce the Python predicates in JavaScript using the tables read from source. The frame has 107,484 rows. Row-count checks were applied to every decoded column. The runnable independent reproducer is appended. These results are **not direct calls to select_overture or classify_grocery**.

| Prompt claim | Finding |
| --- | --- |
| One inclusion category, grocery | Confirmed from the source table. |
| 23 inclusion IDs | Confirmed; all 23 exist in the accepted frame. |
| Grocery 555 | Independently reproduced. Without forced admission it is 532. |
| Supermarket 242 | Independently reproduced. |
| None of the 23 in supermarket | Independently reproduced: intersection size zero. All 23 also fail the ordinary grocery taxonomy predicate. |
| Classifier split 20 supermarket / 3 unclassified | Independently reproduced, with exactly the three IDs named in the prompt. All twenty positive records have a matching brand field: 14 Walmart and 6 ALDI. |
| 20 generated reasons | Confirmed from twenty inclusion entries naming the rebuild generator. This is NOT the same twenty as the classifier-positive set: generated entry 182dc975 is unclassified; the manually admitted aec747a0 is classifier-positive. |
| 55 tests in test_place_exclusions.py | Source has 54 test functions; the one two-value parameterization implies 55 items. This is a source-derived count, not pytest collection or a 55-pass result. |
| Four added to a previous 51 | Git source history supports the transition: 50 functions plus the extra parameterized case to 54 plus that case. The four new guards are the witness guard, its self-check, the open-claim guard and the snapshot-date guard. I did not reproduce the historical claim that all twenty reasons could be rewritten while the previous 51 passed. |
| Supermarket unpublished | No supermarket entry exists in the local product manifest or exporter SOURCES. This does not independently establish what a remote deployment serves. |
| Bundle unchanged since 2026-11-14 | Local grocery destination table is stamped built 2026-11-14 08:28:39, with 468 records on 432 nodes and none of the 23 admitted IDs. The date supports its age, but cannot prove byte-for-byte immutability since then. |

**Corrections and qualifications:**

* The actual admitted taxonomy population is **11 department_store, 4 superstore, 6 discount_store, 2 null**. None is warehouse_club_store. The prompt's account of the 23 omits the six ALDIs and the two uncategorized Publix records. Warehouse clubs can explain the general problem, but are not this population.
* Supermarket is **taxonomy AND judgment**, followed by explicit inclusion, followed by exclusion. It is not a classifier-only layer. This second eligibility gate is why the twenty already-positive records disappear. Grocery likewise is taxonomy **plus owner inclusion minus dropped IDs**, rather than purely taxonomy-based.
* The classifier summary omits its identity rejection before all positive branches, NOT_A_GROCERY_BRANDS, and OSM_CONFIRMED_SPECIALTY before the supermarket ID tables. Order matters, especially for synthetic negative cases.
* The local product bundle has **seven layers**, including grocery walk AND grocery drive, plus park, school, coffee and two named destinations. Grocery walk is the default-on layer. “The bundle is a grocery walk” is too narrow.
* The exporter enumerates source surfaces; it does not infer supermarket publication from grocery. A grocery-only rebuild does not bake a nonexistent supermarket layer into the product. Ask 7 is a useful occasion to review this, not a data dependency that forces ask 10 to be applied first.
* “Everything named here is committed” needs qualification. The reviewed selector, classifier, exclusion source, test module and prompt match their HEAD Git blobs after line-ending normalization. The accepted frame is ignored local data. The current product destination table is untracked/ignored, and the local published-v4 manifest differs from the old tracked manifest at the same path (HEAD's manifest describes six legacy grocery comparison layers, exported 2026-11-09). Do not mistake the local 2026-11-14 product export for the committed artifact. I preserved these preexisting differences.
* The phrase about an explanatory note being four months old describes a possible future, not a verified current fact. Nothing in this checkout supplies a supermarket publication date four months hence.

## Question 1 — is option 3 coherent?

Yes, with a precise boundary. It does NOT infer supermarket from grocery membership. It infers eligibility from an explicit admission and class membership from a separate existing classifier result.

Let T be the current supermarket taxonomy predicate, C mean classify_grocery(record) == supermarket, G be explicit grocery inclusion, S be explicit supermarket inclusion, and E be DROPPED_PLACE_IDS membership. The proposed rule is:

    selected_supermarket = ((T AND C) OR S OR (G AND C)) AND NOT E

The current rule is:

    selected_supermarket = ((T AND C) OR S) AND NOT E

The grocery rule remains:

    selected_grocery = (T_grocery OR G) AND NOT E

Keep forced_into('supermarket') answering only S. Derive G AND C in the supermarket selector. In this implementation “inclusion” retains its existing meaning at the inclusion API; a clearly named and documented derived eligibility path does the extra work. Handle direct supermarket overrides separately so option 3 does not accidentally filter a deliberate S override away.

It is coherent for a broad category to contain a record that a narrower category cannot yet classify. It is also coherent for a taxonomy override to allow the same record to reach a class that its brand already establishes. The dangerous shortcut is dropping T for EVERY classifier-positive record. I independently counted **52** classifier-positive, nonexcluded records outside the taxonomy gate, of which only twenty are the admitted positives. A classifier-only layer would become **294**, adding **32 unreviewed records beyond option 3**, including:

| ID prefix | Name | Primary |
| --- | --- | --- |
| 770fec46 | Walmart Garden Center | nursery_and_gardening_store |
| 4f8a5af0 | Harris Teeter Pharmacy | pharmacy |
| 85e52182 | Family Haircut Center | barber |
| 865b378f | Leesville Market Place (brand Publix) | shopping_mall |

These are concrete reasons to preserve the “forced records only” boundary. The brand classifier is not a general identity validator outside its normal candidate population.

Option 3 also inherits future changes to C: a classifier table edit can admit or remove a grocery-forced record from supermarket. That is a real tradeoff against option 1's fixed roster, not freedom from all future drift.

## Question 2 — what happens to the three unclassified records?

| ID | Held record name | Brand / primary |
| --- | --- | --- |
| 182dc975-ff2e-4be1-8811-0dc710b42547 | Walmart Supercenter | null / department_store |
| 5074229c-e884-4097-8759-4308ddbab7e8 | Publix Super Market at Buffaloe Bend | null / null |
| c7fee873-a3c5-4691-8b12-f2c76bb101b9 | Publix Super Market at Middle Creek Crossings | null / null |

All three have brand-primary definition level zero in Parquet: the outer brand struct is absent, not merely an unrecognized spelling. None is on CURATED_INDEPENDENT_SUPERMARKETS, OSM_CONFIRMED_SUPERMARKETS, NAME_CONFIRMED_SUPERMARKETS, OSM_CONFIRMED_SPECIALTY or NOT_A_WEEKLY_SHOP_SITES. No applicable specialty primary exists. The resulting unclassified answer follows the code exactly. classify_grocery does not consult the record's name or call chain_in_name. A statement in an inclusion reason about an OSM match is not an entry in OSM_CONFIRMED_SUPERMARKETS.

The prompt's proposed explanation for 182dc975 is therefore supported by the decoded data and source. Its name alone does not reach this classifier. The same issue affects both Publix records.

* Option 1: each enters supermarket only if explicitly listed there. Listing just the twenty leaves all three out; listing all twenty-three overrides their unknown classification without changing the classifier's return value. Each needs a deliberate scoped reason.
* Option 2: all three enter automatically; all three remain unclassified in the classifier.
* Option 3: all three remain in grocery and outside supermarket. Their names and the evidence already recorded justify reviewing the missing classification, not secretly adding a name fallback to this fix.
* Option 4: all three remain in grocery and outside supermarket.

“Unknown” here does not mean nobody in the project has examined the business. The grocery admission reasons already record such examination. It means that examination has not been encoded in a classification table read by classify_grocery.

## Question 3 — can an option move grocery or defeat exclusion?

A correctly scoped implementation of options 1, 2 or 3 need not change any grocery selection at all. Option 4 changes none by definition. The independent model compared **ID sets**, not just lengths: both unfiltered supermarket-only inheritance and option 3 preserve all 555 grocery IDs with zero additions or removals. Explicit supermarket-only entries also cannot affect the current grocery lookup. No artifact bytes change just because a selector changes.

But “no grocery number moves” must distinguish this change from ask 7's separately authorized rebuild: the old local destination artifact contains 468 records while the current selector returns 555. Rebuilding routing and exporting together can change household times because of that preexisting population difference. A supermarket fix must add no additional difference to the grocery selection. Merely exporting existing surface arrays does not rerun the selector or repair stale routes.

The source's precedence is sound: construct taxonomy/classification mask; OR the scoped inclusion mask; call drop_excluded, which drops the union of EXCLUDED_PLACE_IDS and FSQ_CONFIRMED_CLOSURES. There are currently **zero** inclusion/dropped overlaps. Therefore the real data count cannot validate conflict precedence on its own.

In the executed independent conflict probe I temporarily inserted the already-excluded Harris Lake ID into the in-memory grocery inclusion set and gave it a department-store record. Correct precedence returned no record; applying forced inclusion after exclusion resurrected it. I removed the synthetic entry immediately from the in-memory model. No repository table was edited.

The actual test_exclusion_beats_inclusion already constructs this grocery conflict. That is a good test. It does not test a direct supermarket inclusion or the proposed inherited classifier-positive conflict. Parameterize exclusions from both dropped sources and test all admission routes. Do not implement option 3 by running classification on grocery-forced records for grocery too: my independent mutation did exactly that and removed the three unknowns, **555 -> 552**. A synthetic grocery forced record without a brand must remain eligible as well.

## Question 4 — would tests catch each option going wrong?

The present tests provide some real protection, but do not implement a behavioral contract for the proposed policies.

* Option 1 needs a synthetic direct supermarket inclusion that bypasses taxonomy, a classified and an unclassified example to establish override semantics, successful inclusion_reason lookup, conflict precedence, and isolation in both directions. Existing synthetic admissions populate only grocery. A mutation that ignores every non-grocery inclusion category has no present exercised positive counterexample.
* Option 2's unacceptable behavior needs a grocery-forced specialty record, an unclassified record and a not_a_grocery record, asserting none automatically becomes supermarket under the recommended policy. This also prevents a classifier truthiness check: every return value is a nonempty string.
* Option 3 needs a department-store positive, a grocery-forced unknown, specialty, an identity-rejected record even with a supermarket brand, a classifier-positive NON-forced outsider, and both explicit and derived conflict cases. It needs an unknown in ordinary grocery taxonomy to show grocery still ignores semantic class. Grocery ID-set invariance and supermarket identity-set equality matter more than matching counts.
* Option 4 needs a publication precondition when the layer becomes publishable. A test should reject a proposed supermarket export until its explicit population contract is approved; do not claim the currently absent guard exists. This need not block a grocery-only export.

The count assertion at test_place_exclusions.py:576 currently asserts grocery == 555 AND supermarket == 242. With the accepted frame present, it would reject both the intended option-3 change (262) and unconditional option 2 (265). Calling that a test that distinguishes the right policy from the wrong one would be false. Both accepted-frame tests skip when the file is absent. Updating 242 to 262 later is necessary but insufficient: require exactly the twenty approved additions and no unreviewed outsiders, with the three unknowns explicitly absent.

The four new reason guards also remain weaker than their names. I executed their corresponding logic independently:

    A corroborated supermarket admitted by id. Corroborated: FSQ "Walmart Pharmacy" at 20.0 m, open today. PRELIMINARY.

This is 115 characters, preserves the required preliminary marker, and contains an inadmissible witness and an unsupported present-tense claim. The witness regex extracts **no names** because it recognizes only single quotes. The date guard skips because it searches specifically for FSQ followed by a single quote. The open-claim guard rejects only two exact substrings, neither of which is “open today”. All three independent guard checks accept it. Replacing all twenty generated reasons with this string leaves every ID/count and the separately pinned aec747a0 reason intact. Source inspection predicts the commissioned module would miss it; **that prediction was not verified with pytest**.

A second independent probe used FSQ 'Trader Joe's Pharmacy' with the required snapshot date. The regex extracts only “Trader Joe” and loses “Pharmacy”, so its witness guard also accepts the bad witness. The full witness is rejected by names_a_service_point. Structured evidence fields, or a fail-closed parse with proper quoting, would make those claims testable. More prose substring checks cannot establish that a reason is truthful.

## Question 5 — mutation results and execution limitation

**I did not run the requested repository-suite mutations. No statement below claims a measured pytest kill or survivor.**

The shell tool failed before process creation with:

    UnsupportedOperation("windows unelevated restricted-token sandbox cannot enforce split writable root sets directly; refusing to run unsandboxed")

The failure affected both PowerShell and an explicit cmd.exe launch. Node child_process.execFile independently returned spawn EPERM. The actual targeted command attempted from v2 was:

    .\.venv\Scripts\python.exe -B -m pytest -p no:cacheprovider tests/test_place_exclusions.py

It did not start. Bytecode and pytest cache writing were disabled in that attempted command. No baseline pytest collection, baseline test run, direct Python selector call or mutated Python-suite run occurred. Prior commit messages' reported suite results are not my execution results.

The following mutations **were executed in the independent JavaScript model** over the current accepted data. They are useful population checks, not substitutes for the missing suite run. Every model is restarted from baseline except the explicitly described synthetic conflict probe.

| Model mutation | Grocery | Supermarket | Grocery set difference | Existing-test expectation from source, NOT executed |
| --- | ---: | ---: | --- | --- |
| Baseline | 555 | 242 | none | No pass result claimed. |
| forced_into always empty | 532 | 242 | loses 23 | Synthetic forced admission and accepted-frame assertions should fail. |
| Grocery inclusions returned for every category | 555 | 265 | none | forced_into(park)/unknown-category checks should fail, as should the real supermarket count. |
| Grocery inclusions copied only to supermarket, without class filter | 555 | 265 | none | Real supermarket count should fail; current synthetic scoping test checks park, not this route. |
| Intended option 3: supermarket-only forced AND classifier | 555 | 262 | none | Old supermarket count should fail even though this is the recommended policy. |
| Classifier filter wrongly applied to grocery-forced records | 552 | 242 | loses the three unknowns | Synthetic forced admission and real inclusion/count assertions should fail. |
| Replace inclusion OR with AND | 0 | 0 | loses 555 | Many selector assertions should fail. |
| Apply inclusion after exclusion | 555 | 242 | none on present real IDs | Grocery synthetic conflict should fail: independent probe resurrected Harris Lake. |
| Remove supermarket taxonomy gate globally | 555 | 294 | none | Real supermarket count should fail; synthetic brand-positive nonforced outsider needed to specify the actual defect. |

Additional concrete mutation holes inferred from source:

| Python mutation to run when execution is restored | Predicted gap |
| --- | --- |
| forced_into(category) returns the correct live grocery set only for grocery and an empty set for every other category | Existing tests never insert a positive supermarket or other-category inclusion. A general per-category API can be broken without changing the exercised current population. |
| Reverse precedence ONLY for explicit supermarket inclusions | No current supermarket inclusion or conflict is constructed; existing grocery precedence test does not exercise this branch. Same applies to a new derived route unless its conflict is tested. |
| inclusion_reason always returns None | The current module tests missing reasons only; it does not assert any successful lookup. |
| Rewrite all twenty generated reasons to the double-quoted pharmacy/open-today text above | Independent guard probes accept it; IDs, lengths, preliminary markers and separately pinned manual reason remain valid. Predicted survivor, not a measured one. |
| Use an apostrophe-bearing bad FSQ witness | Regex truncation can hide the disqualifying suffix. Predicted survivor of the witness guard, not a measured suite survivor. |

A future mutation run must use in-memory function/module replacement, restore it between cases, and disable bytecode/cache output. For the proposed option 3, distinguish (a) the unchanged baseline contract, including the now-obsolete count pin, from (b) a separately reviewed intended-policy test contract. Otherwise a mutant can be “killed” solely because every implementation of the approved new policy changes 242. Capture actual test node IDs, failures and skips; do not turn these predictions into results without executing them.

**Outstanding to finish the exact commission:** direct repository Python numerical checks, actual 55-item collection/baseline, actual forced_into/scoping/precedence mutations against that suite, and the observed survivor list. The environment's process-launch restriction must be resolved before those claims can be made. No owner record/policy decision is needed merely to perform that read-only execution.

## Evidence snapshot

The accepted frame, sources, and local product artifacts used in this review have these SHA-256 hashes:

* v2/data/triangle/overture_places_accepted.parquet — 26ad5ea1a4fde079096aa8d9179c8c481229041762d70ca904c55811184db0b7
* v2/tests/test_place_exclusions.py — 780381280797297f0f5855105c67984e8161fe4f71a639fe5a449c1a4115e1e7
* v2/locfinder/places/exclusions.py — 6ee38c6a696aa320f4186f60a86a58802cc8b1724e046395377864c371f09a2b
* v2/locfinder/places/grocery.py — f83aa4e3579e8ffe1a234306ca3e6f93ed8773fbf42536a7355d98108c7e5cf5
* v2/scripts/export_published_layers.py — 9256533a900af0edc02f0d614302f8612607a48928ee1313c4b8e9ecb651d7f5
* v2/scripts/rebuild_missing_grocery_stores.py — 0ea014d246575322c31760c0e5669af7aee76e778b231d156ad078da27ce2da0
* v2/locfinder/places/categories.py — 305e657f7dcd6cc207810b77e07b0d0ea6024224489f5ff9577942945f2b0af5
* v2/spikes/g3-render/fixtures/published/manifest.json — 6fa4a10b723fa20528a2a78d4d977f853605854b9d10bf5e1a77063af5e356bf
* v2/spikes/g3-render/fixtures/published/own_triangle_grocery_walk.destinations.json — 88284884b2f34abade6cca5e5773477f8908385a556e302a0c3c71057fcb7ad7

The 23 admitted records, independently decoded and classified, are:

| ID | Brand | Primary | Class |
| --- | --- | --- | --- |
| 0da6a7a0-a80a-4791-a971-d12369f300c7 | Walmart | department_store | supermarket |
| 182dc975-ff2e-4be1-8811-0dc710b42547 | null | department_store | unclassified |
| 1e4d47b1-3070-4824-ad66-bdea1e99e688 | ALDI | discount_store | supermarket |
| 28180454-c72d-495b-a239-5b50dbc3c579 | Walmart | department_store | supermarket |
| 30614a3f-db5b-4c11-94c6-116a59512152 | Walmart | superstore | supermarket |
| 4e8d15fb-950d-40c7-8bd9-7245edfb80d1 | Walmart | department_store | supermarket |
| 5074229c-e884-4097-8759-4308ddbab7e8 | null | null | unclassified |
| 50ada728-6b96-4536-b42b-87c7e192bb8e | Walmart | department_store | supermarket |
| 5a7ca34c-e4b3-4252-b29f-5d72c26469e2 | ALDI | discount_store | supermarket |
| 61939d74-fce6-429f-9681-e33d49507697 | Walmart | superstore | supermarket |
| 620e6fd2-19b2-4813-b5da-1ce42473f517 | ALDI | discount_store | supermarket |
| 73868d1a-9765-4391-a822-09065645c63b | ALDI | discount_store | supermarket |
| 7cd72bd3-e72b-473c-9205-3465b34d9ac6 | Walmart | department_store | supermarket |
| 84c14b53-6df7-4b18-adc2-a9147ac9b440 | Walmart | department_store | supermarket |
| 88f1168d-25de-48ae-b495-73dde8fe674e | Walmart | department_store | supermarket |
| 8e1fc43f-a5e0-47bc-82e9-3d0766510cbd | Walmart | department_store | supermarket |
| 9a9272e3-a667-4207-bce2-88092a86193d | ALDI | discount_store | supermarket |
| aec747a0-3bc4-4b87-81fe-94fae9b03f24 | Walmart | department_store | supermarket |
| c7fee873-a3c5-4691-8b12-f2c76bb101b9 | null | null | unclassified |
| d3a09343-a70b-4444-a5d8-543fca5b91ec | Walmart | department_store | supermarket |
| dae36e6e-2766-4dfd-95c5-76061fedb1ec | Walmart | superstore | supermarket |
| edb63737-4b7d-4172-9767-cef1f5d91cf9 | ALDI | discount_store | supermarket |
| efdcc3bc-9b12-4a20-9473-2a69a93f4d3c | Walmart | superstore | supermarket |

## Independent numerical reproducer

This appendix reproduces the independent calculations, not repository Python execution. It reads existing files only and requires Node with its standard filesystem/path modules; it does not download a package, write a harness, or run a subprocess. Set root to the checkout. The decoder intentionally handles the column/page forms needed by this snapshot and rejects unsupported encodings rather than guessing.

```javascript
var fs = await import('node:fs/promises');
var path = await import('node:path');
var root = "C:\\Users\\arikt\\documents\\github\\distanceFinder";
var texts = {};
for (var p of ['v2/locfinder/places/exclusions.py','v2/locfinder/places/grocery.py']) {
  texts[p] = await fs.readFile(path.join(root,p),'utf8');
}
var exsrc=texts['v2/locfinder/places/exclusions.py'];
var grsrc=texts['v2/locfinder/places/grocery.py'];
var pqbuf=await fs.readFile(path.join(root,'v2/data/triangle/overture_places_accepted.parquet'));
function varint(s){var n=0n,k=0n,b;do{b=s.b[s.i++];n|=BigInt(b&127)<<k;k+=7n}while(b&128);return n}

function zz(s){var x=varint(s);return Number((x>>1n)^-(x&1n))}

function thriftValue(s,t){switch(t){case 1:return true;case 2:return false;case 3:return s.b.readInt8(s.i++);case 4:case 5:case 6:return zz(s);case 7:var n=s.b.readDoubleLE(s.i);s.i+=8;return n;case 8:var len=Number(varint(s));var b=s.b.subarray(s.i,s.i+len);s.i+=len;return b;case 9:case 10:var h=s.b[s.i++],len=h>>4,typ=h&15;if(len===15)len=Number(varint(s));return Array.from({length:len},()=>typ===1?s.b[s.i++]===1:thriftValue(s,typ));case 12:return thriftStruct(s);default:throw Error('thrift type '+t)}}

function thriftStruct(s){var out={},prev=0;while(true){var h=s.b[s.i++];if(h===0)return out;var typ=h&15;var id=h>>4?prev+(h>>4):zz(s);out[id]=thriftValue(s,typ);prev=id;}}

function snappy(b){var s={b,i:0},len=Number(varint(s)),out=Buffer.alloc(len),o=0;while(s.i<b.length){var tag=b[s.i++],t=tag&3,n,off;if(t===0){n=(tag>>2)+1;if(n>60){var nb=n-60;n=0;for(var k=0;k<nb;k++)n+=b[s.i++]*2**(8*k);n++}b.copy(out,o,s.i,s.i+n);s.i+=n;o+=n}else{if(t===1){n=((tag>>2)&7)+4;off=((tag>>5)<<8)+b[s.i++]}else if(t===2){n=(tag>>2)+1;off=b.readUInt16LE(s.i);s.i+=2}else{n=(tag>>2)+1;off=b.readUInt32LE(s.i);s.i+=4}if(off>o||off===0)throw Error('snappy offset');for(var k=0;k<n;k++)out[o+k]=out[o-off+k];o+=n}}if(o!==len)throw Error('snappy size');return out}

function hybrid(s,width,count,byteLength){var end=byteLength===undefined?s.b.length:s.i+byteLength,out=[];while(out.length<count&&s.i<end){var h=Number(varint(s));if(h&1){var n=(h>>1)*8;for(var k=0;k<n;k++){var val=0;for(var bit=0;bit<width;bit++){var offset=k*width+bit;val|=((s.b[s.i+(offset>>3)]>>(offset&7))&1)<<bit}out.push(val)}s.i+=n*width/8}else{var n=h>>1,val=0;for(var k=0;k<Math.ceil(width/8);k++)val+=s.b[s.i++]*2**(8*k);for(var k=0;k<n;k++)out.push(val)}}if(byteLength!==undefined)s.i=end;return out.slice(0,count)}

function plainStrings(s,count){var out=[];for(var k=0;k<count;k++){var len=s.b.readUInt32LE(s.i);s.i+=4;out.push(s.b.toString('utf8',s.i,s.i+len));s.i+=len}return out}

function schemaRead(parts=[],def=0,rep=0){var e=meta[2][schidx++],name=e[4].toString();var p=parts.length||name!=='schema'?[...parts,name]:[];if(e[3]===1)def++;if(e[3]===2){def++;rep++}if(e[5])for(var k=0;k<e[5];k++)schemaRead(p,def,rep);else leaves[p.join('.') ]={def,rep,type:e[1]}}

function readCol(colpath){var desc=leaves[colpath],rows=[],pending=null;for(var rg of meta[4]){var c=rg[1].find(c=>c[3][3].map(b=>b.toString()).join('.')===colpath)[3];var s={b:pqbuf,i:c[11]??c[9]},end=s.i+c[7],dict=[];while(s.i<end){var ph=thriftStruct(s),raw=pqbuf.subarray(s.i,s.i+ph[3]);s.i+=ph[3];if(ph[1]!==0&&ph[1]!==2&&ph[1]!==3)throw Error('page type '+ph[1]);if(ph[1]===2){var b=c[4]===1?snappy(raw):raw;dict=plainStrings({b,i:0},ph[7][1]);continue}var n=ph[1]===0?ph[5][1]:ph[8][1],enc=ph[1]===0?ph[5][2]:ph[8][4],rs,ds,vals;var dswidth=Math.ceil(Math.log2(desc.def+1)),rswidth=Math.ceil(Math.log2(desc.rep+1));if(ph[1]===0){var b=c[4]===1?snappy(raw):raw,ps={b,i:0};rs=desc.rep?hybrid(ps,rswidth,n,(()=>{var l=ps.b.readUInt32LE(ps.i);ps.i+=4;return l})()):Array(n).fill(0);ds=desc.def?hybrid(ps,dswidth,n,(()=>{var l=ps.b.readUInt32LE(ps.i);ps.i+=4;return l})()):Array(n).fill(0)}else{var ph2=ph[8],ps={b:raw,i:0};rs=desc.rep?hybrid(ps,rswidth,n,ph2[6]):Array(n).fill(0);ps.i=ph2[6];ds=desc.def?hybrid(ps,dswidth,n,ph2[5]):Array(n).fill(0);var used=ph2[6]+ph2[5],b=raw.subarray(used);if(ph2[7]!==false&&c[4]===1)b=snappy(b);ps={b,i:0}}var count=ds.filter(x=>x===desc.def).length;if(enc===0)vals=plainStrings(ps,count);else if(enc===8||enc===2){var bw=ps.b[ps.i++];vals=hybrid(ps,bw,count).map(x=>dict[x])}else throw Error('encoding '+enc);var vi=0;for(var k=0;k<n;k++){var value=ds[k]===desc.def?vals[vi++]:null;if(!desc.rep)rows.push(value);else{if(rs[k]===0){pending=[];rows.push(pending)}if(value!==null)pending.push(value)}}} }if(rows.length!==meta[3])throw Error('rowcount '+colpath+': '+rows.length);return rows}

function tablePart(src,name){var start=src.search(new RegExp('^'+name+'[^\\n]*= \\{','m'));if(start<0)throw Error(name);var end=src.indexOf('\n}',start);return src.slice(start,end+2)}

function idsIn(src,name){return new Set([...tablePart(src,name).matchAll(/^\s*"([0-9a-f-]{36})":/gm)].map(m=>m[1]))}

function setIn(src,name){var part=src.match(new RegExp('^'+name+' = frozenset\\(\\{([\\s\\S]*?)^\\}\\)','m'))[1];part=part.split('\n').map(l=>l.split('#')[0]).join('\n');return new Set([...part.matchAll(/"([^"\n]+)"/g)].map(m=>m[1]))}

function classifyJS(r){if(sets.NOT_A_WEEKLY_SHOP_SITES.has(r.id)||sets.NOT_A_GROCERY_BRANDS.has(r.brand))return 'not_a_grocery';if(sets.SUPERMARKET_BRANDS.has(r.brand))return 'supermarket';if(sets.OSM_CONFIRMED_SPECIALTY.has(r.id))return 'specialty';if(sets.CURATED_INDEPENDENT_SUPERMARKETS.has(r.id)||sets.OSM_CONFIRMED_SUPERMARKETS.has(r.id)||sets.NAME_CONFIRMED_SUPERMARKETS.has(r.id))return 'supermarket';if(sets.SPECIALTY_BRANDS.has(r.brand)||sets.SPECIALTY_PRIMARIES.has(r.primary))return 'specialty';return 'unclassified'}

function taxJS(r){return r.primary!=='farmers_market'&&r.hierarchy.includes('grocery_store')}

function modelSelect(category,kind='baseline',input=rows){return input.filter(r=>{var c=classifyJS(r),t=taxJS(r),f=category==='grocery'&&inc.has(r.id);if(kind==='empty-forced')f=false;if(kind==='all-categories-forced'||(kind==='alias-supermarket'&&category==='supermarket'))f=inc.has(r.id);if(kind==='filter-grocery-forced'&&category==='grocery')f=f&&c==='supermarket';var base=t&&(category==='grocery'||c==='supermarket');if(kind==='global-classifier'&&category==='supermarket')base=c==='supermarket';if(kind==='option3'&&category==='supermarket')f=inc.has(r.id)&&c==='supermarket';if(kind==='and-inclusion')return base&&f&&!dropped.has(r.id);if(kind==='reverse-precedence')return (base&&!dropped.has(r.id))||f;return (base||f)&&!dropped.has(r.id)}).map(r=>r.id).sort()}

function normJS(s){return s.toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim().split(/\s+/).join(' ')}

function containsJS(h,n){return (' '+h+' ').includes(' '+n+' ')}

function chainJS(s){var h=normJS(s),list=[...sets.SUPERMARKET_BRANDS].map(b=>[normJS(b),b]);list.push(['wal mart','Walmart']);return list.sort((a,b)=>b[0].length-a[0].length).find(([n])=>containsJS(h,n))?.[1]??null}

function serviceJS(s){var h=normJS(s);return containsJS(h,'pick up')||[...serviceWords].some(w=>containsJS(h,w))}

function partJS(s){return chainJS(s)!==null&&[...partWords].some(w=>containsJS(normJS(s),w))}

function guardJS(reason){var parts=reason.split('Corroborated: '),clause=parts.length>1?parts.slice(1).join('Corroborated: '):reason;var witnesses=[...clause.matchAll(/(?:FSQ|named) '([^']+)'/g)].map(m=>m[1]);return {witnesses,noBadWitness:!witnesses.some(n=>serviceJS(n)||partJS(n)),noOpenClaim:!reason.toLowerCase().includes("' open at")&&!reason.toLowerCase().includes('is open at'),dated:!reason.includes("FSQ '")||reason.includes('2025-01-10')}}
var metalength=pqbuf.readUInt32LE(pqbuf.length-8);
var meta=thriftStruct({b:pqbuf,i:pqbuf.length-8-metalength});
var leaves={}, schidx=0;
schemaRead();
var cols={};
for(var c of ['id','brand.names.primary','names.primary','taxonomy.primary','taxonomy.hierarchy.list.element']) cols[c]=readCol(c);
var inc=idsIn(exsrc,'INCLUDED_PLACE_IDS');
var dropped=new Set([...idsIn(exsrc,'EXCLUDED_PLACE_IDS'),...idsIn(exsrc,'FSQ_CONFIRMED_CLOSURES')]);
var sets={};
for(var n of ['SUPERMARKET_BRANDS','SPECIALTY_BRANDS','SPECIALTY_PRIMARIES','NOT_A_GROCERY_BRANDS']) sets[n]=setIn(grsrc,n);
for(var n of ['CURATED_INDEPENDENT_SUPERMARKETS','OSM_CONFIRMED_SUPERMARKETS','OSM_CONFIRMED_SPECIALTY','NAME_CONFIRMED_SUPERMARKETS','NOT_A_WEEKLY_SHOP_SITES']) sets[n]=idsIn(grsrc,n);
var rows=cols.id.map((id,i)=>({id,brand:cols['brand.names.primary'][i],name:cols['names.primary'][i],primary:cols['taxonomy.primary'][i],hierarchy:cols['taxonomy.hierarchy.list.element'][i]}));
var includedRows=rows.filter(r=>inc.has(r.id));
console.log(JSON.stringify({frameRows:rows.length,inclusions:inc.size,includedRows:includedRows.map(r=>({...r,class:classifyJS(r)}))},null,2));
var gBaseline=modelSelect('grocery');
for(var kind of ['baseline','empty-forced','all-categories-forced','alias-supermarket','option3','filter-grocery-forced','and-inclusion','reverse-precedence','global-classifier']) {
  var g=modelSelect('grocery',kind),sm=modelSelect('supermarket',kind);
  console.log({kind,grocery:g.length,supermarket:sm.length,groceryMissing:gBaseline.filter(id=>!g.includes(id)).length,groceryExtra:g.filter(id=>!gBaseline.includes(id)).length});
}
var conflict={id:'5a1c8da5-ce62-41fc-af4a-fa2c0c4bd703',brand:'Walmart',primary:'department_store',hierarchy:['department_store'],name:'conflict probe'};
inc.add(conflict.id);
console.log({conflictBaseline:modelSelect('grocery','baseline',[conflict]),conflictReversed:modelSelect('grocery','reverse-precedence',[conflict])});
inc.delete(conflict.id);
var serviceWords=setIn(grsrc,'SERVICE_POINT_WORDS'),partWords=setIn(grsrc,'STORE_PART_WORDS');
console.log(guardJS('A corroborated supermarket admitted by id. Corroborated: FSQ "Walmart Pharmacy" at 20.0 m, open today. PRELIMINARY.'));
console.log(guardJS("A corroborated supermarket admitted by id. Corroborated: FSQ 'Trader Joe's Pharmacy' at 20.0 m, no closure recorded in the 2025-01-10 snapshot. PRELIMINARY."));
```
