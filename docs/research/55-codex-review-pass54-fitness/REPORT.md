# Codex pass 54 — the closing fitness review

**Run 2026-11-15**, read-only, `--model gpt-6.1-sol`, against `477bc2f` (checked out at the
documentation-only child `c154330`; it verified the two `v2` trees match). Prompt:
[`55-codex-review-pass54-prompt.md`](../55-codex-review-pass54-prompt.md).

**This was asked as a fitness review rather than a sixth defect hunt**, in the shape of pass 25.
Its verdict, in its own words:

> **The work is now disproportionate to its purpose. The card was worth building; this sequence of
> reviews was not worth completing before anyone opened it.**

**Defect sweep: no High findings in the pass 53 repairs**, which is the first time in six passes.
One Medium assurance limitation, and it is about a claim of mine rather than about the product:
`mutate_admissible.py` still counts any non-zero pytest exit as a catch, with no ERROR bucket, so
"0 errored anywhere" was not supported by the source.

**Where it disagrees with me**, which is the part worth reading twice:

* **Not that the browser is necessarily the single most useful hour.** The owner's repeat walk of
  `band15min_pass-03` could be more decisive, because it can establish a *materially wrong*
  recommendation while a successful browser session cannot establish an accurate one. In parallel,
  as §0 already requires.
* **Not that pass 52 was the stopping boundary.** The sharper criticism is that the next review of
  the card **should have followed its first browser use** — a different source of evidence instead
  of another examination of the same implementation.
* **Not that the card retired only defect risk.** It names five changes with direct product value,
  and separates them from the regression apparatus built around them: "the mitigation exists in
  code; its effectiveness remains unobserved".
* **Not that the walked-record code is "the one check that consults the world"** — its inputs are
  declarations, coordinates and durations supplied by a person. The *walk* consults the world.

**And the thing nobody in the chain has looked at**, which was the question I most wanted answered:
what a household concludes, and in particular **false exclusions**. This is a region finder, not a
journey inspector: somebody can discard a neighbourhood because it is outside the coloured area and
never open a card there, so destination omissions and cost-selected times remove candidates before
any explanation is met. Also unexamined: there is no persistent selection interaction at all —
`app.js` reads explanations on `mousemove` and clears them on `mouseout`, so whether a person can
select a home, keep its explanation, read it on a phone or reach it without a mouse is an open
question. Phone decode latency is one part of phone fitness.

**The report is reproduced verbatim below.**

---

**The work is now disproportionate to its purpose. The card was worth building; this sequence of reviews was not worth completing before anyone opened it.** What exists is a carefully guarded development spike, with useful disclosure logic and insufficient evidence that a household can obtain, understand, or safely rely on its answer.

The highest-value next **developer** action is one bounded browser session against the actual published bundle. Its purpose should be to follow a real recommendation from a known location through the coloured raster to the card, including the restricted-route disclosure. Merely establishing that the page renders would leave much of the important question unanswered.

I disagree with the stronger claim that opening the browser is necessarily the single most useful hour available overall. If the owner can undertake the repeat walk of `band15min_pass-03` now, that hour could be more decisive. It can establish a materially wrong recommendation; a successful browser session cannot establish an accurate one. These should proceed in parallel, as §0 already requires.

I also would not identify pass 52 as a defensible stopping boundary. The evidence supports stopping this kind of sequence, but it does not identify which numbered pass crossed the economic threshold. The stronger criticism is that **the next review of the card should have followed its first browser use**. That would have supplied a different source of evidence instead of another examination of the same implementation.

**The card has addressed product risk, but the later work mostly strengthened assurance about that mitigation.**

The strongest case against the effort is straightforward. The purpose is helping friends and family find suitable areas for a home search. The dominant unanswered questions concern usable destinations, actual journeys, the meaning of “grocery,” and the answer at the place a person selects. None becomes substantially better understood by proving that another deliberately corrupted response field turns a test red.

The supplied totals make the opportunity cost concrete: 4,773 added lines of tests and mutation guards, against 2,201 of product and script code, while no browser observation exists. That ratio alone proves nothing—small safety-critical components can warrant extensive tests—but this component has not yet been tested in its intended interaction. The effort has repeatedly improved confidence in an intermediate representation while deferring the observation that could invalidate the presentation altogether.

The distinction between finding a defect and demonstrating a product problem also matters. A mutant that forces every headline to INCLUDED demonstrates a gap in the suite. It does not demonstrate that the unmutated product was giving that headline incorrectly. That gap deserves attention, especially around disclosures, but its severity cannot by itself establish priority over a real, unresolved journey discrepancy.

I believe that argument substantially.

I do not believe the card retired *only* defect risk. Several changes have direct product value:

- Distinguishing an unknown criterion from an exclusion prevents a false negative explanation.
- Naming the destination lets someone discover that the estimate concerns the wrong kind of shop.
- Showing the restricted-route flag exposes a known limitation that engine agreement cannot detect.
- Clearing an obsolete card prevents a previous affirmative answer from accompanying changed criteria.
- Correcting “at least 11 minutes” prevents an actual overstatement of a lower bound.

Those are meaningful protections against misleading someone. The mistake was treating their implementation and increasingly elaborate regression protection as sufficient progress toward delivering them. **The mitigation exists in code; its effectiveness remains unobserved.**

The walked-record work has a similar distinction. `admissible.py` protects the project from making an unjustified accuracy claim. That was worthwhile after the report alternated between incompatible verdicts. But the predicate does not itself consult the world. The walk does. I disagree with describing the walked-record *code* as “the one check that consults the world”: its inputs are declarations, coordinates and durations supplied by someone. Its latest refinements primarily protect the interpretation of those declarations.

That protection should now be sufficient to collect the next observation. It should not become another prerequisite that keeps moving ahead of collection.

**The browser wins the next developer hour, with a narrower claim than the queue currently gives it.**

The strongest attack on browser priority is that it can become another exercise in self-agreement. A beautiful card can accurately reproduce an estimate to an unsuitable destination along an unusable route. A screenshot can confirm that a warning exists without establishing that anyone notices or understands it. Visual approval alone would retire little of the product’s principal truth risk.

There is also an important measurement distinction inside queue item 3. Three things must be separated:

1. The source projected cell used by the pipeline.
2. The published WGS84 pixel selected at a coordinate.
3. The pixel MapLibre actually draws under that coordinate.

Comparing the page directly with `GridSpec.cell_for_lonlat` combines re-tiling and rendering differences. Some disagreement is already expected. To isolate browser placement, compare the **drawn pixel with the published pixel first**, then trace that pixel back to the source grid. Otherwise another correct measurement could receive the wrong interpretation.

The next session should therefore have a small, concrete deliverable: captured browser output for a known restricted-route recommendation, an ordinary inclusion, an exclusion, an unknown and an outside-footprint location; a threshold change and pointer move; and a few known coordinates chosen to discriminate placement, including near the maximum predicted row displacement. A diagnostic raster with identifiable rows is more decisive for placement than looking at a smooth region and judging whether it appears aligned. This does not require a general browser-testing framework.

For the known journey, record what the **page actually says**. The audit sheet’s encoded 14 minutes is evidence about its recorded artifact; the outstanding placement question is precisely why it should not simply be assumed to authenticate the answer shown at a real door.

Against the alternatives:

The **repeat walk** has the greatest immediate potential to change the release decision. It resolves a specific standing discrepancy. It remains a targeted observation, not a population accuracy estimate, and a favourable result would not establish general reliability. But it could provide decisive adverse evidence with very little additional engineering.

The **grocery definition** may be cheaper still if the owner is ready to decide it. It changes the destination universe and therefore the published answers; it cannot be deferred indefinitely behind implementation work. However, rendering the existing bundle does not require that decision, and the browser work will remain useful after a rebuild. I would settle the definition before commissioning further destination-dependent measurements or presenting the current numbers as settled product results.

The **step 4 comparator** enables verdict-impact measurement and remains necessary. It is a longer route to a narrower kind of knowledge: whether construction and attachment choices change answers under the declared model. Shared destination errors and shared access assumptions can survive it. It should resume as a bounded development experiment after these immediate observations, without becoming a new certification project standing in front of them.

**Some apparatus should be removed, but deleting tests wholesale would confuse sunk cost with future cost.**

The last five passes meet the letter of “a named product risk” surprisingly easily: wrong destination, stale answer, lost observation. They fail its purpose when that phrase becomes enough to justify indefinite elaboration. The missing question was: **what decision will this additional assurance enable, and why is it more valuable than the next observation?**

Here is what I would delete:

I would delete [`byteswap_control.mjs`](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/byteswap_control.mjs). Its own account withdraws the claim that it was load-bearing. The byte-swap fixture and ordinary mutation already exercise the important behaviour. Keeping an additional executable experiment to prove which assertion catches it has acquired its own maintenance and review history without a corresponding household benefit.

I would retire [`bench_explain.mjs`](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/bench_explain.mjs) after retaining the existing measurement and its limitations in the experiment record. It answered a reversible implementation question: whether this bundle justifies caching per-layer outcomes. Further repairs to its explanatory wording have consumed review attention after that question was settled. Reintroduce a benchmark when an observed performance problem supplies a reason.

I would delete `test_the_migrated_header_is_the_generators_order` in [`test_migrate_audit_sheet.py`](C:/Users/arikt/documents/github/distanceFinder/v2/tests/test_migrate_audit_sheet.py:96), together with the “append new columns instead of placing them” mutation in `mutate_migrate.py`. Preserving observations, retaining additional owner columns and making required fields available justify checks. Requiring complete header equality with a committed generated sheet mainly protects a diff convention. Keeping related columns together is useful; treating exact generator order as a mutation-protected correctness property is excessive here.

I would also remove obsolete current-state prose from the live documents. The progress note still begins with “card unbuilt” and “not shown,” then later describes its completion. The decision report correctly says the private approach is unresolved, then later says “The walked journey took a private track.” Those contradictions cost more than untidy documentation: they can change the decision a resuming session makes. Keep the historical reports; make the live state and decision report state one current answer.

I would retain the actual card semantics tests, the small three-layer discriminating fixture, shipped-bundle loading, lifecycle regressions, and migration preservation tests. Their continuing execution cost is small and their risks are concrete. I would stop expanding the four mutation collections as the next milestone. An improvement to a mutation runner should require evidence that the runner is currently obstructing a product decision.

In particular, fixing migration paths that could overwrite observations was justified. Elaborating machinery around canonical column placement was not. That distinction is more useful than classifying every line of test code as waste.

**The cheapest immediate reduction in false household claims is to qualify the affirmative claim at its source.**

[`card.js`](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/card.js) opens an included result with:

> Every criterion you have on is satisfied here.

That is stronger than the evidence the decision report describes. The number is a rounded model estimate from a cell centre, for a destination selected by the routing cost rule. A restricted route can remain INCLUDED.

Before household exposure, I would change the opening to something like **“The model estimates this cell meets your limits.”** Immediately explain that times are rounded estimates from the cell centre, and put the restricted-route qualification beside the relevant time. Test the wording in the first browser session.

This does not improve the numerical estimate. It reduces the chance that the product asserts a demonstrated real-world fact where it possesses a model result. It is a small change to a consequential sentence, not a request for a larger disclaimer system.

For the cheapest **empirical** reduction, verify the actual displayed destination and usable journey for `band15min_pass-03`, then repeat the walk with the required record. No additional admissibility machinery is needed first.

There is another distinction to preserve here. `destination_qualifies`, `destination_open` and `route_usable` travel through the record, but their negative values do not determine the duration scorer’s outcome. Consequently, an E3 summary cannot stand in for a summary of failed recommendations. This is a known risk from pass 25, rather than a newly discovered one. Keep those observations visible in the release decision even when the timed journey itself is admissible.

**The most consequential unexamined risk is what a household concludes—and what it never investigates.**

I found no evidence in this chain of a nontechnical person being asked to use the result and explain its meaning. The tests authenticate intended words. They do not establish the proposition those words convey.

A useful first session would ask someone: “Would you keep this home on your shortlist? What do you believe the walk will take? Which shop would you reach? What does the restriction warning change?” Observe the answers before explaining the model.

There is a less obvious version on excluded locations. This is a **home-search region finder**, not merely a journey inspector. A household can discard an otherwise suitable neighbourhood because it lies outside the coloured region and never inspect a card there. Destination omissions and cost-selected times can therefore remove good candidates before their explanations are encountered. False exclusions have been examined computationally; **how the interface turns an exclusion into a home-search decision has not been examined in these passes**.

The interaction itself is also unexamined. [`app.js`](C:/Users/arikt/documents/github/distanceFinder/v2/spikes/g3-render/app.js:447) obtains explanations through `mousemove` and clears them on `mouseout`. There is no explicit persistent selection interaction in that wiring. Whether someone can select a home, retain its explanation, read it on a phone or reach it without a mouse remains an empirical question. Phone decode latency is only one part of phone fitness.

On excluded-cell destinations, I now take a firmer position than “defensible but unevidenced”: **retain the per-criterion disclosure.** A grocery estimate remains useful information when another criterion excludes the cell, and also when that grocery estimate exceeds its own limit. Suppressing the identity conceals what the number describes. The presentation should identify it as the destination used for that criterion’s estimate. Whether users mistake that information for an overall recommendation needs observation; suppressing accurate explanatory data is not the better default.

That is an explicit disagreement with any inclination to restore the combined-verdict suppression policy. I agree with your uncertainty about its usability, but favour the current information policy.

**Defect sweep — severities**

**High: none found in the pass 53 repairs.**

The explicit walk occurrence field and preparation split address the earlier inference problem. Per-name candidate lists preserve same-name permitted members, and the arrival comparison uses those members’ coordinates. The inspector’s position and compute checks, request-failure transition, and native-error adapter address the reported paths. The migration now validates the destructive cases before writing, verifies a temporary output, and preserves the original for in-place migration. The three-layer group now carries differing destination tables and planes, mixed flag availability, and every nonempty enable mask.

One **Medium assurance limitation** remains in the supplied description: [`mutate_admissible.py`](C:/Users/arikt/documents/github/distanceFinder/v2/scripts/mutate_admissible.py) still counts any nonzero pytest exit as caught. Unlike `mutate_migrate.py`, it does not require a failed-test line or maintain an ERROR bucket. Its landing-site checks exist, but “all four runners reject execution errors as catches” is not supported by the source. I would narrow that claim now; it does not justify another review sequence.

I replayed the JavaScript harnesses in memory: **87 worker checks and 33 card checks passed**. These were VM executions, not browser executions. I could not execute Python, pytest, the process-based mutation runners, geospatial measurements, or an actual browser session. The supplied Python and mutation totals remain owner-provided results.

The checkout is at `c154330`, the documentation-only child of `477bc2f`; I verified that their `v2` trees match and that the reviewed implementation files match `477bc2f`, allowing for CRLF conversion. No files were changed.
