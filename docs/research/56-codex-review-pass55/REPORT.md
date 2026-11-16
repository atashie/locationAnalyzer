# Codex review, pass 55 -- the three browser sessions, and what they claim

**Run 2026-11-16, gpt-6.1-sol, read-only, at 3705195.** Prompt:
[56-codex-review-pass55-prompt.md](../56-codex-review-pass55-prompt.md).

**The first run died at 1h28m without reporting** -- the process exited and the job state
stayed `running`. Four findings were recovered from the Codex session transcript and handed
back on resume as established facts, which is why the report opens by accepting them. The
two that matter: the card’s new origin sentence names the wrong centre, and the coordinate
this repository calls a recorded door is a query coordinate with blank start fields.

---

These commits retired some product risk. They established that a particular bundle could load and produce useful disclosures in the reported desktop browser sessions, corrected an overconfident affirmative headline, and prevented a repeat walk from being directed by the wrong grid index. They did **not** complete validation of the rendered placement, authenticate an answer at a recorded door, or establish that a household understands the card.

The most important new defect is in the disclosure itself: **“measured from the centre of this cell” identifies the wrong centre.** The strongest new assurance defects are that three probe self-tests never finish their assertions, and the latest browser run receives substantially weaker checks than the original run.

I reviewed the three commits through `3705195`, at the documentation-only child `7978468`. I used the four accepted findings as established facts.

**1. Did the work retire product risk, or only defect risk?**

The strongest case that the wording change is cosmetic is this: it changes neither the answer nor the action the interface encourages.

The same area is blue. The same criterion says PASS. The same bare “14 min” appears. The same destination may be unsuitable, and the same route may depend on a private approach. A household scanning neighbourhoods can accept or discard an area without ever opening the card. Even someone who opens it may read the bold headline and number while passing over the smaller, muted qualification.

On that account, “the model estimates” is a change in the author’s description of uncertainty, with no demonstrated change in the household’s understanding. The browser sessions were conducted by the system’s builder, who already knew exactly what the caveats meant. They supply no evidence that somebody looking for a home notices the warning, understands its consequence, or changes a decision because of it.

There is a further reason to press that argument hard: a qualification can make an interface *sound* more careful while increasing confidence in an incorrect explanation. That has happened here. The new sentence names the displayed cell’s centre as the measurement origin, although the answer was sampled from a different source-grid centre. The word “estimates” does not make that provenance statement true.

**I nevertheless do not believe the change is merely cosmetic.** Changing an unconditional assertion about a place into a statement about a model changes the product’s claim. Putting the restricted-route warning immediately under its time also improves the chance that a reader connects the limitation to the number. These are real mitigations against overreliance. Their effectiveness is unmeasured; their existence is not imaginary.

The distinction is between implementing a useful mitigation and demonstrating its effect.

The three commits have different value:

| Work | Product risk addressed | What remains |
|---|---|---|
| `1365f13`: first browser session | The feature might fail to load or never put its disclosures on a screen. The screenshot also supplies local evidence about the colour edge. | The probe does not observe rendered pixels at eleven locations. One operator’s session does not establish household usability. |
| `a34caa8`: wording | A household could interpret an affirmative model result as an established fact. Warning placement was also improved. | Exclusions remain categorical, and the new origin statement is false. |
| `3705195`: walked-cell reading and oracle correction | The planned verification could have inspected the wrong published cell and compared the wrong journey. The correction makes the next field check more specific. | The coordinate is not a recorded door. This is preparation for a real-world check, not that check. |

The index correction was therefore useful even though it repaired an instrument. An instrument defect has product significance when it can misdirect the evidence used to approve a release. But it should not be described as fixing a 400 m error in what the product gave a household. The demonstrated 400 m error was in the **named probe**.

The placement work also made the right harm concrete: false exclusions in the picture matter because they can remove an area from consideration before any explanation is opened. That is a better product question than whether another mutated field turns a test red. What overreaches is the promotion of the resulting analytical counts into exact browser-observed exposure.

My judgment is that these three commits were worth doing. They obtained evidence from a different boundary of the system and improved a claim people may read. Their value does not establish that the earlier review sequence was proportionate, or justify another long apparatus-only sequence now.

The next work should serve a person’s actual decision: correct the false origin and categorical exclusion wording, then have somebody unfamiliar with the implementation select a place, interpret its result, keep the explanation available, and explain what the map has ruled out. The repeat walk remains a separate, valuable check. Neither activity is replaced by a cleaner probe result.

**2. Is the wording honest, and honest in the right places?**

**The affirmative headline is an improvement.** “The model estimates this cell meets your limits” correctly identifies the source of the conclusion. It does not claim that a usable journey has been observed. It is appropriately prominent.

**The exclusion headline is still too certain.** At [card.js:47](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/card.js:47), “At least one criterion is not satisfied here” asserts a fact about the location. The evidence is still a model result, potentially affected by destination omissions, selection costs, representative origins and the road model.

The note below it helps, but does not remove the asymmetry. The categorical sentence is the headline; the qualification is smaller and muted. More fundamentally, “times are estimates” does not qualify every reason an area might be wrongly excluded. An omitted destination can produce a confident exclusion without the principal problem being numerical time uncertainty.

I would use:

> **Our model rules this cell out for at least one of your limits.**

That also accommodates exclusions established from a modelled lower bound, where no route time was calculated.

The UNKNOWN headline is different. “We cannot say” already expresses uncertainty, and “none has ruled this out” describes the criteria’s state. It is not another categorical negative answer. It could be made more consistent, but it is less urgent than EXCLUDED.

Leaving the negative wording unchanged was understandable as an editing-scope decision. It is not a defence of the resulting claim. Recording it as an owner decision is honest; claiming that the common note has resolved the asymmetry is not.

**The origin disclosure is false.** At [card.js:63](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/card.js:63), “this cell” refers to the published cell identified by the card. The time comes from a source-grid centre selected during reprojection.

This matters because the sentence answers a practical question: *where does this journey begin?* It can cause the owner to choose the wrong origin for the repeat walk and interpret the resulting difference as routing error. It can also imply that the published cell has its own evaluated centre-to-destination journey when it actually inherits another cell’s result.

A suitable immediate statement would be:

> **Times are model estimates for a nearby grid point, not your address, and are rounded up to whole minutes.**

That is less geographically precise, but accurately describes the present publication. Naming the exact origin would require carrying or recovering the source-cell identity.

The new test does not establish the stronger sentence. [test_browser_conformance.py:116](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/tests/test_browser_conformance.py:116) checks that the producer calls `cell_centers_xy()`. That establishes evaluation at **source** cell centres. It does not establish identity with the consumer’s displayed cell after reprojection. This is precisely the distinction the wording needed checked.

**“14 min” with a nearby rounding note is defensible.** A number need not print `(13, 14]` to be honest. The separate line is on the same card, identifies the direction of rounding, and does not require understanding the wire format.

I would nevertheless put “rounded up” beside the number if the intended interaction includes copying or sharing individual criterion rows. A common note is easier to lose when a row is viewed in isolation. This is a modest presentation improvement, not a reason to redesign the encoding immediately.

The more important qualifications are that it is a model estimate, that it does not start at the address, and that the represented route may be unusable. Halving display rounding cannot compensate for missing those facts.

**The restricted-route warning is now associated with the relevant time in the code.** The renderer builds a separate `.crit` block for each criterion and puts its warning directly after that criterion’s time, before its explanation and destination. With several criteria, it does not gather warnings into an ambiguous common paragraph.

That is a meaningful improvement. “Beside” need not mean the same horizontal line; directly underneath within the same block is reasonable. I found no new association defect there. What remains unestablished is whether the warning stays noticeable and readable with several criteria on a real device. The reported one-layer screenshot cannot settle that.

Finally, the card’s words cannot protect someone who never opens it. For a region finder, the map’s negative signal is itself a consequential claim. The mitigation needs to operate at selection and exclusion, not only after inspection.

**3. Should the encoding change?**

**Keep whole-minute `ceil` for the next pilot. Do not change to 30-second units now.**

The present encoding preserves the model’s verdict at whole-minute thresholds. Its display cost is understood and can be stated accurately. A 30-second representation would preserve that useful property and reduce rounding, but would not improve the underlying origin, route, destination or real-world validity.

The docstring’s trigger—“a per-cell number is now displayed”—is a reason to reconsider the tradeoff, not evidence that its previously proposed replacement is now the highest-value work. No household observation demonstrates that the extra rounding is causing a mistaken decision.

A format change would also require coordinated changes to units, threshold comparison, lower-bound interpretation, display and compatibility. The old “+32% bytes” should not be treated as a current whole-bundle price without remeasuring the destination-bearing bundle.

Keep the exact threshold behaviour, correct the disclosure, and observe use. Revisit finer units if people need that distinction. Do not replace `ceil` with nearest-minute rounding.

**4. Are the experiment records safe to quote?**

Not yet.

The clearest overclaim is [s3-11-browser-placement.json:638](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-11-browser-placement.json:638): the page draws the raster where predicted “at every one of the eleven probes.”

The accepted probe limitation prevents that conclusion. A safe account is:

> At eleven coordinates, the live map projection and source-canvas samples agreed with the analytical expectations. A screenshot at one selected colour edge was visually consistent with the predicted displacement.

The following assertion that the structure counts now describe the page a household actually gets is also too strong. Those remain analytical counts under the placement model, supported locally by the image.

The s3-12 record contains further quotable overclaims:

- At [line 2](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-12-what-the-page-says-at-the-walked-cell.json:2), “a household standing at that door” promotes a sheet query coordinate into a recorded door.
- At line 83, “the re-walk’s precondition is met” is too broad. A displayed candidate claim has been identified; the start door still needs choosing and recording.
- At line 87, “One explainAt per pointer move is free” overgeneralises a desktop message-round-trip measurement that stops **before the DOM update**.
- At line 94, “the page renders at 60 fps when something is looking at it” generalises a capture-associated burst of animation-frame callbacks into product rendering performance.
- At line 95, “untainted” is unjustified for a sample taken immediately after the capture intervention that reportedly changed frame scheduling.

The s3-11 caveat also says the walked route differs from the model by **20 minutes**. That is not the recorded approximately 25 versus 13.5 minutes, and no admissible accuracy difference has yet been established.

The historical preservation was handled correctly. I compared the JSON across commits: **`the_run` is unchanged from `1365f13`**, and the wording change was annotated rather than substituted into the old observation.

The annotation is adequate for the wording change. It is inadequate for the later probe correction: s3-11 still presents the old named walked-cell probe without a comparably prominent warning that it described the wrong location. The later s3-12 account does not stop somebody quoting s3-11 alone.

**5. The remaining methodological questions**

**The screenshot:** I inspected the committed colour-edge image. The painted edge is visibly near the red line, and the other nearby line is distinguishable. It is useful coarse evidence at that edge.

The important separation between the Mercator and latitude hypotheses is **9 px**, not 38 px. The ±38 px controls demonstrate that a gross whole-row alternative would be conspicuous; they do not themselves establish precision sufficient to distinguish a 9 px gap. The visible image supplies that narrower discrimination reasonably well.

It does not establish exact coincidence, subpixel placement, uniform scale correctness, or correct placement at the other ten probes. A one-pixel overlay also obscures the very edge being judged. The defensible conclusion is local visual consistency, not closure of every affine placement error.

There is a small recording inconsistency: the listed column spans—77–80, 91–93 and 102—cover eight columns if inclusive, not eleven.

**The alpha control:** the observations are consistent with premultiplication quantisation. Two opaque pixels returning exactly are useful, but do not uniquely distinguish premultiplication from every alpha-dependent painting or conversion defect. A more specific control would predict and test the written-to-read mapping for the same translucent colours and alpha values.

The ±1 RGB tolerance is a reasonable local accommodation for the recorded palette, with alpha exact. It does not by itself conceal PASS versus FAIL. But the claimed positive control for that tolerance is one of the unawaited tests described below.

**The pointer control:** the reported `464.378 → 464` directly supports conversion in that constructed event. Choosing an integer client coordinate deliberately is a sensible repair. It does not authenticate the repaired readout’s contents or mean the hover and analytical pixel sample are at exactly the same position: the hover may be moved to another screen pixel inside the desired cell.

I found no reason to reject the repair for the reported constructor behaviour. I would restrict its claim to that behaviour and environment.

**The changed oracle:** this was a legitimate correction, not an illegitimate goalpost move. The intended location supplies a reason independent of the browser’s result. My comparison found exactly one changed probe, `the_walked_cell`; every exposure table and every non-probe top-level field remained unchanged.

Keeping the original run and obtaining a fresh run was the right approach. The guard coverage nevertheless weakened: the newest run is not subjected to the original run’s detailed hover, timeout and disagreement checks.

**The 1002 ms figure:** yes, there is a reading under which it is real and the control is the intervention.

If frames arrive once per second, the page can actually wait approximately one second before its next render event in that operating state. Calling that delay a frame clock does not make it disappear. Capturing the window may change scheduling or presentation behaviour, giving a fast burst that does not represent normal interaction.

Conversely, the observation is plausible evidence of an automation-associated condition rather than a foreground household experience. The evidence does not distinguish these explanations sufficiently to declare the delay exclusively “the instrument.”

Keep both observations with their conditions. Foreground interactive latency remains unresolved. The approximately 69 ms post-capture sample is evidence that a faster response occurred, not an unconfounded baseline.

The 0.2 ms explanation statistic supports retaining the current architecture on that tested desktop. It excludes DOM work and does not establish pointer-to-visible-card latency. It also is not the same order as 0.0002 ms: those values differ by a factor of **1,000**. No new optimisation is justified yet, but neither is “free.”

**Ledger 49:** retain the narrow lesson about a rationale depending on a changing consumer. It is useful, though related to the existing invalidation and stale-claim instances. It does not demonstrate that 30-second units are now preferable. Its claim that the cross-check prevents drift is overstated: the new false-centre sentence passed that check. “The fortnight” is also inaccurate for the stated November 14–16 sequence.

**Ledger 50:** the index/grid lesson is sound and the cause is established. It overlaps earlier mixed-grid and wrong-unit failures, but is concrete enough to retain as a specialised example.

Withdraw “Nothing internal could have found it” and the claim that the check had to come from outside the system. The sheet coordinate, source grid and published grid were already available inside the repository. An internal coordinate/index consistency check could have found it. The browser session *prompted* the comparison; that does not establish that browser evidence was necessary. Replace “door” throughout with “sheet query coordinate.”

If a reported browser reading were wrong, the index correction, false origin disclosure, categorical exclusion wording and test-runner defects would still stand. The analytical displacement would still stand as analysis. Claims of actual placement and performance would lose their reported observational support.

**Ranked findings — ordered by product risk**

**F1 — High: the new origin disclosure names the wrong point.**

Location: [card.js:63](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/card.js:63); the purported check is [test_browser_conformance.py:116](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/tests/test_browser_conformance.py:116).

The accepted source/published-centre distinction directly contradicts the sentence.

**Product risk:** a household or walker evaluates the wrong starting journey and assigns the difference to routing accuracy. Withdraw “centre of this cell” until the referenced centre is identified correctly.

**F2 — Medium: exclusions retain a stronger headline than inclusions.**

Location: [card.js:47](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/card.js:47).

**Product risk:** suitable areas are discarded on an apparently factual exclusion. The common estimate note does not qualify all causes of model exclusion or match the headline’s prominence. Qualify EXCLUDED at its source.

**F3 — Medium: analytical/source-canvas agreement is reported as rendered-placement confirmation.**

Locations: [probe_placement.js:249](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/probe_placement.js:249), [s3-11-browser-placement.json:637](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-11-browser-placement.json:637).

The zero-disagreement result also leaves most displayed card values uncompared.

**Product risk:** the owner accepts exact exclusion-exposure figures or considers placement validation complete on insufficient evidence. Preserve the analytical figures, but label their status accurately. The screenshot supports a local observation.

**F4 — Medium: a query coordinate is repeatedly promoted into a walked door.**

Locations: [measure_drawn_pixel.py:74](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/measure_drawn_pixel.py:74), [write_s3_12_walked_cell.py:16](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/write_s3_12_walked_cell.py:16), [test_walked_cell_reading.py:84](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/tests/test_walked_cell_reading.py:84).

The test explicitly calls `query_lon/query_lat` the door while the start fields remain blank.

**Product risk:** the next walk can acquire a false claim of matched provenance. The index repair is correct; the claimed door provenance is not. Record an actual start before claiming this precondition complete.

**F5 — Medium: performance conclusions dismiss a condition rather than isolate it.**

Location: [s3-12-what-the-page-says-at-the-walked-cell.json:87](C:/Users/arikt/Documents/GitHub/distanceFinder/docs/experiments/s3-12-what-the-page-says-at-the-walked-cell.json:87), lines 93–95.

**Product risk:** a real interaction delay is dismissed, or an inexpensive message exchange is mistaken for a responsive explanation. Withdraw “free,” “untainted,” and the general 60 fps conclusion. Preserve the measurements and state the unresolved conditions.

**F6 — Medium: three probe self-tests report success before their assertions run.**

Locations: [probe_placement_selftest.mjs:37](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/spikes/g3-render/probe_placement_selftest.mjs:37), lines 379, 398, 403 and 412.

`check()` calls `fn()` without awaiting its result. The tolerance, wrong-grid and tilted-map checks return promises. `process.exit()` executes before their assertion continuations.

I replaced the tolerance continuation’s assertion with unconditional `assert(false, …)` **in memory**. The runner still printed that check as PASS and ended with **“all checks passed,” exit 0**.

**Product risk:** evidence that the probe can reject incorrect observations is falsely strengthened. The runner must await these checks before reporting success or exiting.

**F7 — Medium: the newest-run guard does not enforce the properties the old run’s guards enforce.**

Location: [test_browser_placement.py:67](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/tests/test_browser_placement.py:67).

I changed the latest run in memory to contain eleven timed-out hovers, wrong card text, wrong drawn cells and explicit per-probe disagreements. `test_the_run_is_against_the_oracle_that_is_committed` still passed. It trusts the outer summary’s zero rather than checking the recorded disagreements.

The detailed checks below it still operate on s3-11. Missing s3-12 also causes the newest-run fixture to skip.

**Product risk:** a failed or incomplete rerun can retain the status “current confirmation.” Apply the substantive run checks to each run against its own oracle. Preserve historical observations separately.

**F8 — Low: the exposure field counts outcome disagreements, not colour disagreements.**

Location: [measure_drawn_pixel.py:196](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/measure_drawn_pixel.py:196).

At 20 minutes I reproduced:

| Quantity | Structures |
|---|---:|
| Different outcome codes | 5,801 |
| Of those, identical source RGBA | 127 |
| Same outcome but different hatch pixels | 134 |
| Any different source RGBA | 5,808 |

An unstriped UNKNOWN pixel is transparent like FAIL. Conversely, shifting the hatch can change a pixel without changing UNKNOWN.

**Product risk:** the owner prices visible map harm using the wrong measurement. Rename the 5,801 as outcome disagreement under the placement model. Do not simply substitute 5,808 as a harm count. The important **2,771 PASS-to-FAIL picture disagreements remain** under that model.

**F9 — Low: collection and regeneration checks provide less record integrity than their descriptions promise.**

Locations: [collect_probe_run.py:51](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/collect_probe_run.py:51), [write_s3_12_walked_cell.py:198](C:/Users/arikt/Documents/GitHub/distanceFinder/v2/scripts/write_s3_12_walked_cell.py:198).

The collector accepts a complete `n=1` payload plus an extra `i=99,n=1` chunk, silently ignoring the extra chunk. I reproduced this with an in-memory log.

The writer also carries an existing browser run forward without checking its bundle or code identity. Preserving an observation is appropriate; presenting a preserved observation as current after regeneration requires a separate match check.

**Product risk:** an archived or malformed collection can be mistaken for current evidence. Reject indices outside `0..n-1`; retain observations with explicit version identity and applicability.

The three commits made useful progress, but their strongest claims still exceed what was observed. Correcting those claims and the live wording is a bounded repair. The next substantive evidence should come from a person using the product and from the properly recorded walk.

**Validation:** process execution worked in this session despite the prompt’s runtime warning. The focused tests across the four relevant Python test files passed. I executed the in-memory guard, asynchronous-control and collector counterexamples, recomputed the exposure distinctions, inspected the committed colour-edge image, and checked historical JSON preservation. I did not access a browser, run the full suite or load the routing graph. No repository files were changed; pytest used an external `--basetemp`.

Codex session ID: 01a1d670-aa9d-7492-98db-6909136a6aa2
Resume in Codex: codex resume 01a1d670-aa9d-7492-98db-6909136a6aa2
