"""Place records an owner decision ADDS to or REMOVES from a layer, by what the thing IS.

**EVERY DECISION IN THIS MODULE IS PRELIMINARY.** Owner instruction 2026-11-19: push through the
QA of businesses and establishments, note that the data are preliminary, and leave a robust
approach built on well-vetted sources as future work. See
`docs/engineering-notes/reference-business-data-is-preliminary.md` for what that covers, what
these tables are actually built from, and the five things a robust source would have to supply.
Each entry repeats the word PRELIMINARY in its own text so the caveat travels with the record.

Overture's taxonomy answers "is this record categorised as a park". It does not answer "is this a
park", and for a handful of records those differ in a way no tag in the data distinguishes. Those
records are listed here, by stable Overture id, each with the evidence and the decision that
removed it, so the judgement is reviewable in a diff rather than buried in a builder.

**Why a list and not a rule.** The obvious rule -- drop a park record whose containing OSM polygons
carry no park designation -- was measured before it was written. It would drop **25** records, and
almost all are real parks that happen to sit inside a school ground or a state recreation area
whose OSM polygon lacks the tag: Lynn Road Park, Barwell Road Park, Dixon Drive Park, Anderson
Community Park, Sandling Beach State Recreation Area, Falls Dam Playground. It would delete about
twenty-three genuine parks to remove two. OSM's designation tagging is not consistent enough to
carry a general rule here, and a rule that is wrong twenty-three times out of twenty-five is worse
than no rule.

Keep this list short. If it grows past a handful, that is evidence the acceptance stage needs a
real screen and this file has become a place to hide the need for one.
"""
from __future__ import annotations

#: Overture place id -> why it is not what its taxonomy says, and whose decision removed it.
#:
#: Each entry must carry enough for a reader to re-check it without this module: what the record
#: claims to be, what the evidence says it is, and the date of the decision.
EXCLUDED_PLACE_IDS: dict[str, str] = {
    "5a1c8da5-ce62-41fc-af4a-fa2c0c4bd703":
        "'Shearon  Harris Lake', taxonomy primary=park. It is the cooling reservoir of the Harris "
        "Nuclear Plant, not a park. The only OSM polygon containing it is 'Duke Energy: Harris "
        "Nuclear Plant' (leisure=nature_reserve, 9,627.8 ha), which carries no park designation, "
        "no access tag and no parks operator. Seven of the nine accepted park records on that site "
        "DO fall inside 'Harris Lake County Park' (leisure=park, access=yes, ownership=county) and "
        "are kept. Owner decision 2026-11-17: designated as a public park yes, open space that is "
        "not designated a park no. PRELIMINARY.",
    "dc218eca-83a0-4889-acde-0ec39b54224d":
        "'Shearon Harris Reservoir', taxonomy primary=park. The same water body as the record "
        "above under another name, and the same evidence: contained only by 'Duke Energy: Harris "
        "Nuclear Plant', outside 'Harris Lake County Park'. Owner decision 2026-11-17. PRELIMINARY.",
    "81190996-0ac4-401f-817a-a9ebff1af58c":
        "Kroger, grocery. Overture marks it permanently_closed, and unlike the eight below the "
        "signal is strong: it comes from `Overture-signals` at confidence 1.0 rather than from a "
        "business registry, and OSM shows a `shop=supermarket` named Harris Teeter operating at "
        "the same spot. So the Kroger closed and somebody else trades there -- routing a "
        "household to 'Kroger' names a shop that is not there. Owner decision 2026-11-17: drop "
        "this one, hold the other eight. PRELIMINARY.",
    # ---- 2026-11-19: seven bays lifted, their parents admitted; and ask 6 settled ----
    #
    # Owner instruction to push through on preliminary data. Each bay below came out ONLY
    # because its parent store is now in the layer -- the condition the hold stated.
    "686a0d8f-b451-45c5-af0b-1dc3cc76a426":
        "A Walmart collection bay, held 2026-11-19 and removed the same day because **its parent store is "
        "now published**: `ccff8ac5-0b7d-4ac7-8d5d-3a7f5e0fa768` at 0.2 m, which was ALREADY in the "
        "published layer and is NOT in `INCLUDED_PLACE_IDS` -- an earlier version of this entry said it "
        "was admitted there, which was false. Corroborated independently: OSM `shop=supermarket` named "
        "'Walmart Neighborhood Market' 14.5 m away, a different FORMAT from a Supercenter and still a "
        "weekly shop. The hold said these come out together with their replacements and that "
        "condition is met for this one. A bay is not a weekly shop; the shop beside it is, and a household "
        "now routes to the shop. PRELIMINARY.",
    "b570ea04-a662-4fee-9823-16d464eb02a2":
        "A Walmart collection bay, held 2026-11-19 and removed the same day because **its parent store is "
        "now published**: `84059dec-19b8-4741-aa20-0f2cad92744c` at 75.4 m, which was ALREADY in the "
        "published layer and is NOT in `INCLUDED_PLACE_IDS` -- an earlier version of this entry said it "
        "was admitted there, which was false. The hold said these come out together with their "
        "replacements and that "
        "condition is met for this one. A bay is not a weekly shop; the shop beside it is, and a household "
        "now routes to the shop. PRELIMINARY.",
    "8226f374-206c-4e30-88d5-8dfed581b3ee":
        "A Walmart collection bay, held 2026-11-19 and removed the same day because **its parent store is "
        "now published**: `30614a3f-db5b-4c11-94c6-116a59512152` at 20.0 m, admitted via "
        "`INCLUDED_PLACE_IDS`. The hold said these come out together with their replacements and that "
        "condition is met for this one. A bay is not a weekly shop; the shop beside it is, and a household "
        "now routes to the shop. PRELIMINARY.",
    "38c97738-83e4-4227-bffe-e352043c8606":
        "A Walmart collection bay, held 2026-11-19 and removed the same day because **its parent store is "
        "now published**: `88f1168d-25de-48ae-b495-73dde8fe674e` at 63.4 m, admitted via "
        "`INCLUDED_PLACE_IDS`. The hold said these come out together with their replacements and that "
        "condition is met for this one. A bay is not a weekly shop; the shop beside it is, and a household "
        "now routes to the shop. PRELIMINARY.",
    "2023f7f8-de17-4056-8d77-67f8cf180b0f":
        "A Walmart collection bay, held 2026-11-19 and removed the same day because **its parent store is "
        "now published**: `182dc975-ff2e-4be1-8811-0dc710b42547` at 110.7 m, admitted via "
        "`INCLUDED_PLACE_IDS`. The hold said these come out together with their replacements and that "
        "condition is met for this one. A bay is not a weekly shop; the shop beside it is, and a household "
        "now routes to the shop. PRELIMINARY.",
    "ea38688f-cdfe-46e4-8ab4-d6373e611d63":
        "A Walmart collection bay, held 2026-11-19 and removed the same day because **its parent store is "
        "now published**: `d3a09343-a70b-4444-a5d8-543fca5b91ec` at 249.3 m, admitted via "
        "`INCLUDED_PLACE_IDS`. The hold said these come out together with their replacements and that "
        "condition is met for this one. A bay is not a weekly shop; the shop beside it is, and a household "
        "now routes to the shop. PRELIMINARY.",
    "cee0e25b-aef4-410c-ae89-a0be7ad2bf41":
        "A Walmart collection bay, held 2026-11-19 and removed the same day because **its parent store is "
        "now published**: `aec747a0-3bc4-4b87-81fe-94fae9b03f24` at 27.4 m, admitted via "
        "`INCLUDED_PLACE_IDS`. The hold said these come out together with their replacements and that "
        "condition is met for this one. A bay is not a weekly shop; the shop beside it is, and a household "
        "now routes to the shop. PRELIMINARY.",
    "4ff51c50-4e5d-4b0d-8bbe-ddb55a26be53":
        "'Weaver Street Market Administration', taxonomy hierarchy=grocery_store. The co-op's OFFICE, at "
        "the same coordinate as the Food House already removed above -- the third wrong destination from "
        "that one address, and the destination audit has already seen it chosen. Checked against both "
        "second sources before removing: NO agreeing Foursquare record within 120 m (of 14 records there) "
        "and NO shop-tagged OSM feature within 120 m, so nothing says a shop is here. Owner instruction "
        "2026-11-19 to push through. PRELIMINARY.",
    "ee14e175-556e-4b89-af7b-adea914d618c":
        "'Food Line Distribution Center', taxonomy hierarchy=grocery_store. A DISTRIBUTION CENTRE, and "
        "`classify_grocery` already returned `not_a_grocery` for it while the published layer went on "
        "offering it -- the same taxonomy-versus-classifier gap as the Food House. **Foursquare disagrees "
        "and is not trusted here:** it carries a record of this name, not closed, labelled BOTH 'Retail > "
        "Drugstore' AND food-and-beverage retail, which is a category guess rather than an observation of a "
        "shopfront. No shop-tagged OSM feature within 120 m. A distribution centre is not a weekly shop. "
        "PRELIMINARY.",
    "c8899cfc-9df9-4d98-b186-063ed5581515":
        "'Variety Pick-Up', taxonomy hierarchy=grocery_store, `unclassified`. **STILL THE WEAKEST ENTRY IN "
        "THIS TABLE, AND ITS FIRST REASON WAS FALSE.** That reason said no second source says a shop is "
        "here. The sixth review executed the check: FSQ holds **'Harveys Supermarkets' at 1830 New Bern "
        "Ave -- this record's own address -- 16.3 m away with no closure date**, alongside a Shell and a "
        "Valero fuel pin and 'NYC Grill' at the same address. The search had required the NAME to agree, "
        "and reported 'no evidence of a shop' when what it had was an unresolved IDENTITY. "
        "**WHAT THE EXCLUSION NOW RESTS ON was also already on disk and was not cited: "
        "`docs/experiments/audit/grocery-brandless-footprint-shortlist.csv` records this record inside a "
        "181 m2 building** (largest within 120 m: 427 m2), far below `footprint.py`'s 650 m2 floor, which "
        "yields `not_a_weekly_shop` by the project's own measured rule. A fuel-station forecourt unit is "
        "not a weekly shop whatever the name beside it. **STILL REVISIT THIS ONE FIRST**, and when a "
        "vetted source arrives the question to ask is which business is at 1830 New Bern Ave, not whether "
        "the name matches. PRELIMINARY.",
    # ---- owner ask 3, 2026-11-18, PARTLY HELD 2026-11-19 ----
    #
    # The ask covered eleven records. ONE is removed here; the ten collection bays are HELD in
    # `HELD_SERVICE_POINTS` below after the fifth adversarial review. Published `grocery`
    # 543 -> 542.
    #
    # `grocery` is taxonomy-based and never calls `classify_grocery`, so `NOT_A_WEEKLY_SHOP_SITES`
    # governed `supermarket` alone while the published layer went on offering a meat-processing
    # plant as a grocery destination. The published cut is by explicit id with evidence per record.
    # The service-point SCREEN only ever DISCOVERED the candidates; what decides membership here is
    # evidence and an owner decision, which is the distinction the fifth review asked for and the
    # reason the id table is not merely a transcript of a heuristic.
    "1e99e399-b118-4d95-8c78-6770a47287c8":
        "'Weaver Street Market, Inc', taxonomy hierarchy=grocery_store. It is the co-op's FOOD HOUSE: a "
        "commercial kitchen, an NCDA-inspected meat-processing plant (P-317), two bakeries and warehousing "
        "that supply the four Weaver Street shops twice a day. A SUPPLIER, not a shop, and nothing in the "
        "data distinguishes them -- the name is the co-op's legal name, so it carries no service-point word "
        "for any screen to catch. Already in `NOT_A_WEEKLY_SHOP_SITES`, which governs `supermarket` only; "
        "this entry is what removes it from the PUBLISHED `grocery` layer. Nearest surviving grocery record "
        "0.0 m, 'Weaver Street Market Administration' -- an office at the SAME COORDINATE, which the "
        "destination audit has already seen chosen as a destination and which the owner has NOT decided on. "
        "**SO THIS REMOVAL DOES NOT RETIRE THE BAD DESTINATION LOCATION**, as the fifth review pointed out; "
        "it removes the record that claims to be a shop and leaves the one that claims to be an office. "
        "Found by the third adversarial review 2026-11-18, owner decision the same day, and KEPT when the "
        "ten bays beside it were held on 2026-11-19: a plant that supplies shops is not a shop by any "
        "reading of the owner's definition, and no judgement about shopping methods turns on it. "
        "PRELIMINARY.",
    # ---- owner ask 14, 2026-11-23 ----
    #
    # Two records published in the `grocery` layer that `classify_grocery` calls `not_a_grocery`.
    # Not a judgement call and not a borderline reading: BOTH brands were already in
    # `NOT_A_GROCERY_BRANDS` before today. The layer published them because `grocery` is
    # taxonomy-based and never calls the classifier, so two parts of this codebase disagreed and
    # the published artifact carried the one that was never asked. Published `grocery` 555 -> 553.
    #
    # `test_no_published_grocery_record_is_one_our_own_classifier_refuses` now fails if a third
    # one appears. It is a GUARD and not a filter on purpose: a class filter on `grocery` would
    # mean the next brand typed into `NOT_A_GROCERY_BRANDS` silently removed published records,
    # and a published number may not move as a side effect of a name being added to a table.
    "8bfc9ae7-468e-4008-892a-02cd09f52b08":
        "'Pet Dairy', taxonomy hierarchy=grocery_store, confidence 0.957, 8812 Midway West Rd, Raleigh. "
        "The record's OWN `brand` field reads 'Pet Dairy' and its own `websites` field reads "
        "petdairy.com: a regional DAIRY BRAND, which is why 'Pet Dairy' was already in "
        "`NOT_A_GROCERY_BRANDS` before this entry existed. `classify_grocery` has therefore returned "
        "`not_a_grocery` for it all along, and the published layer offered it as a grocery destination "
        "anyway, for 44 answered cells. The evidence here is the record's own brand and website, not its "
        "name -- nothing is inferred from the words 'Pet' or 'Dairy'. WHAT THE FOOTPRINT DOES AND DOES "
        "NOT SAY: the point sits inside a 779 m2 building (largest within 120 m: 1,745 m2), so "
        "`corroboration` returns CORROBORATED. That verdict means a building of weekly-shop size stands "
        "there. It does NOT mean a shop stands there, and it is not evidence for or against this removal; "
        "reading it as support either way would repeat the error of reading REFUTED as 'no shop here'. "
        "Nearest surviving grocery record 720.8 m, 'El encanto market', so the removal does not orphan "
        "the site, but it does change the answer for cells that were being sent 720 m short of a shop.",
    "8c5d8cb0-755c-40f2-844a-03a5a679740e":
        "'Market at Colonnade Center', taxonomy hierarchy=grocery_store, confidence 0.920, 8511 Colonnade "
        "Center Dr, Raleigh. The record's OWN `brand` field reads 'Regency Centers' -- a listed retail "
        "property company, already in `NOT_A_GROCERY_BRANDS` -- and its own `websites` field is a Regency "
        "Centers PROPERTY DETAIL PAGE, regencycenters.com/property/detail/60301. So the record is the "
        "shopping centre itself rather than a shop inside it, established from the record's own brand and "
        "website rather than from its name. `classify_grocery` returns `not_a_grocery`; the published "
        "layer carried it for 259 answered cells. THE SHOPS IN THE CENTRE ARE NOT REMOVED WITH IT: the "
        "nearest surviving grocery record is 548.1 m away and is 'Food Lion', the centre's own anchor "
        "supermarket, published as its own record. That is the distinction this entry turns on -- the "
        "centre is not a shop, and removing the centre does not remove the shop. WHAT THE FOOTPRINT DOES "
        "AND DOES NOT SAY: the point sits inside a 1,864 m2 building (largest within 120 m: 3,596 m2), so "
        "`corroboration` returns CORROBORATED, which means a large building stands there and says nothing "
        "about whether the thing at that address is a shop or a landlord's leasing office.",
    # ---- owner ask 15, 2026-11-23 ----
    #
    # *"yes"* to removing the records that are plainly not shops you can walk into, adjudicated
    # PER RECORD with its evidence, and explicitly NOT touching any tienda, tortilleria or ethnic
    # market: all three of our sources under-record shops in exactly those neighbourhoods, so a
    # missing record there is evidence about the sources and not about the shop.
    #
    # WHAT MAY COUNT AS EVIDENCE HERE. Owner decision 2026-11-18 forbids parsing a name to guess
    # what KIND of shop something is, so no entry below rests on its name. Each rests on the
    # record's OWN fields -- the `websites` value Overture carries, and the address shape -- plus,
    # for the four largest, a check against a public source. None of them carries a `brand` at
    # all, which is why the brand tables could never reach them.
    #
    # THE EVIDENCE SHRANK THE SET TWICE, and that is the point of adjudicating per record.
    #
    #   * `Funny Girl Farm` (1,875 cells) is NOT removed. LocalHarvest and Durham Magazine both
    #     describe a farm stand with posted hours -- Tue-Fri 2-6, Sat 9-3 -- selling produce, eggs,
    #     cheeses, meats and preserves. That is a shop a household walks into.
    #   * `Allen Powell Memorial Collard Patch` (3,228 cells) is NOT removed. WRAL reports an
    #     operating family collard farm at 2107 Hamlin Road selling direct to customers, run by
    #     John Powell since his father died, with a memorial sign on the road.
    #   * `Homestead Harvest Farm` (3,590), `Currin Farm` (1,618), `Wilkerson Farms` (0) and
    #     `Hamm's Greenhouse` (0) are HELD, not removed. Homestead Harvest takes phone orders with
    #     "call the farm to schedule a visit", which is not a walk-in shop, but after the two
    #     above a farm is no longer something this table removes without checking the individual
    #     place. They are owed as an ask. The last two answer 0 cells, so holding them costs
    #     nothing.
    #
    # Published `grocery` 553 -> 542. 3,879 answered cells change hands.
    "dc09b073-d0ac-4141-8275-3127c748878d":
        "'Roofing Inc.', taxonomy hierarchy=grocery_store, confidence 0.650, 206 New Edition Ct, Cary, "
        "16 answered cells. The record's OWN `websites` field reads ncbestroof.com -- a roofing "
        "contractor. No `brand`, and the address is a cul-de-sac unit rather than a retail frontage. "
        "Nothing is inferred from the word 'Roofing': the evidence is the website the record itself "
        "carries. Nearest surviving grocery 524.6 m, 'Food Lion', so the site is not orphaned. "
        "Owner ask 15, 2026-11-23.",
    "4f318935-7d66-4a5e-833a-1131fdf4b4fe":
        "'Longview Poole Road', taxonomy hierarchy=grocery_store, confidence 0.650, 2405 Poole Rd, "
        "Raleigh, 332 answered cells. The record's OWN `websites` field reads raleighnc.gov -- the City "
        "of Raleigh, which is not a grocery's website. A municipal web address on a record named after "
        "a road is a municipal ASSET record that has been filed under a shop taxonomy. Nearest "
        "surviving grocery 507.7 m, 'Family Fare'. Owner ask 15, 2026-11-23.",
    "f4f83562-7244-4d65-9f15-7c7a02a9c700":
        "'McKee Foods Corp', taxonomy hierarchy=grocery_store, confidence 0.755, 106 Gibson Rd, Mebane, "
        "0 answered cells. The record's OWN `websites` field reads mckeefoods.com -- a national snack "
        "MANUFACTURER. A plant or office is not a shop, the same reading that removed the Weaver Street "
        "Food House on 2026-11-18. Nearest surviving grocery 2,698.3 m, 'Food Lion' -- far, and it "
        "costs nothing here because this record answers no cells. Owner ask 15, 2026-11-23.",
    "7864cc9b-c5d6-462b-aede-057a51a97cb8":
        "'Bar S Foods', taxonomy hierarchy=grocery_store, confidence 0.650, 1001 Corporation Pkwy "
        "**Ste 106**, Raleigh, 163 answered cells. Two own-field signals agree: the `websites` value is "
        "bar-sfoods.com, a meat PROCESSOR's brand site, and the address is a SUITE on a street called "
        "Corporation Parkway -- a unit inside a business park, which is why its CORROBORATED footprint "
        "verdict (4,642 m2 host) is void. A big host building corroborates nothing when the record is a "
        "unit inside it. Nearest surviving grocery 878.5 m, 'La Estrella'. Owner ask 15, 2026-11-23.",
    "96516656-b397-4e5c-ad1b-1696f91fc364":
        "'Insain Hot Sauce', taxonomy hierarchy=grocery_store, confidence 0.958, 1717 Shallow Water Dr, "
        "Knightdale, 241 answered cells. The record's OWN `websites` field is a PRODUCT PAGE on the "
        "brand's own shop, insainhotsauce.com/products/wicked-chocol..., and the address is a "
        "residential street. A sauce brand selling online from a house is not a grocery a household "
        "walks to. Nearest surviving grocery 664.2 m, 'Paul's Grill and Grocery'. Owner ask 15, "
        "2026-11-23.",
    "c2b874a3-cff2-42a9-a889-e2b1206f5e85":
        "'KismetCrackers', taxonomy hierarchy=grocery_store, confidence 0.716, 9522 Hampton Rd, "
        "Rougemont, 499 answered cells. The record's OWN `websites` field reads kismetcrackers.com -- a "
        "cracker BRAND -- at a rural residential address. **THE CONSEQUENCE IS STATED BECAUSE IT IS "
        "LARGE**: Nearest surviving grocery 8,883.2 m, 'Los Portales De Butner', so the 499 "
        "cells this record answers do not get a nearer answer -- most will become BEYOND_HORIZON on "
        "foot. That is the correct outcome if there is no shop there, and the website is the reason to "
        "think there is not. Its `REFUTED` footprint verdict is NOT part of this: it is one of the 15 "
        "the 2026-11-23 review found to be missing building data, now `UNSURVEYED`. Owner ask 15, "
        "2026-11-23.",
    "2d238ae6-285f-4965-b51f-d41e4293f8d0":
        "'Seal The Seasons', taxonomy hierarchy=grocery_store, confidence 0.950, 501 W Franklin St "
        "**Ste 106**, Chapel Hill, 757 answered cells. A flash-frozen local produce COMPANY: it sets up "
        "freezing facilities on partner farms and distributes to retail -- UNC and the Daily Tar Heel "
        "both describe the business, and it reports reaching thousands of retail locations. So it is a "
        "SUPPLIER of groceries rather than a place to buy them, the Weaver Street Food House reading "
        "again. The address is a SUITE, which also voids the 1,870 m2 CORROBORATED host building. "
        "Nearest surviving grocery 202.5 m, 'Hill's Family Asian Markets'. Owner ask 15, 2026-11-23.",
    "8665f77f-7c89-4d1a-badb-853e5c99159a":
        "'Seal The Seasons', taxonomy hierarchy=grocery_store, confidence 0.750, 4426 S Miami Blvd, "
        "Durham, 1,320 answered cells. Seal the Seasons is a flash-frozen local produce COMPANY: it "
        "installs freezing facilities on partner farms and distributes packaged frozen produce to "
        "retail, which UNC and the Daily Tar Heel both describe and which the company says reaches "
        "thousands of retail locations. So it SUPPLIES groceries rather than selling them to a "
        "household, the same reading that removed the Weaver Street Food House on 2026-11-18. This "
        "record carries NO `websites` value and no `brand`, so unlike the other removals in this ask "
        "its own fields name nothing; the evidence is the public record of what the company is, plus "
        "an address on an industrial boulevard. Its 1,741 m2 CORROBORATED host building is consistent "
        "with the freezing and warehousing the company describes and is NOT offered as support either "
        "way -- a footprint is an upper bound on what is inside it. Stated in full rather than by "
        "reference to the company's other record in this table, because an entry that defers to its "
        "neighbour cannot be re-checked without it, and a version of one inclusion reason in this "
        "repository once said 'same shape as the record above' when the record above was a different "
        "chain. Nearest surviving grocery 2,038.6 m, 'Snowie of NC'. Owner ask 15, 2026-11-23.",
    "6098ae5b-2002-4844-91a6-8400c7f739c6":
        "'Body Agape Holistic', taxonomy primary=organic_grocery_store, confidence 0.650, 1003 Mulford "
        "Ct **# 751**, Knightdale, 0 answered cells. The record's OWN `websites` field reads "
        "bodyagapeholistic.com, a holistic health business, and the address is a MAILBOX number -- "
        "`# 751` at a single court address is a mail drop, not a shopfront, which is also why its 775 "
        "m2 CORROBORATED host building says nothing. **THE ONLY ONE OF THE ELEVEN THAT WAS NOT MERELY "
        "`unclassified`**: Overture's primary is `organic_grocery_store`, which is in "
        "`SPECIALTY_PRIMARIES`, so `classify_grocery` called it `specialty` and it was published as a "
        "specialty GROCER rather than as something nobody had checked. It answers 0 cells, so no "
        "published number moves with it. Nearest surviving grocery 250.4 m, 'Walmart'. Owner ask 15, "
        "2026-11-23.",
    "80916e67-4f04-4a5e-a6c5-fee8bf7e1aad":
        "'Tower Market Place Partners', taxonomy hierarchy=grocery_store, confidence 0.482 -- the "
        "lowest in the uncorroborated set -- 3511 Maitland Dr, Raleigh, 11 answered cells. No website "
        "and no brand, so the own-field evidence here is thin and the owner named this record "
        "specifically in ask 15. What the data does say: an 8,890 m2 host building and 11 answered "
        "cells, which is a record sitting in a large retail property while almost no household is "
        "routed to it. Nearest surviving grocery 142.5 m, 'Food Lion', in the same place. Same structure as "
        "`Market at Colonnade Center`, removed under ask 14: the property is not the shop, and removing "
        "the property does not remove the shop. Owner ask 15, 2026-11-23.",
    "d2f1e817-cb2f-4a48-b6d3-75765a460fc0":
        "'No longer', taxonomy hierarchy=grocery_store, confidence 0.541, 1025 Blue Ridge Rd, Raleigh, "
        "540 answered cells. The `names.primary` field contains the string 'No longer'. This is NOT a "
        "name being parsed for what KIND of shop it is, which 2026-11-18 forbids -- it is the "
        "observation that the field does not contain a business name at all, which is a different "
        "statement and the only one being made. The owner named this record specifically in ask 15. "
        "Nearest surviving grocery 1,479.3 m, 'Harris Teeter', so the 540 cells get a more distant "
        "answer. Owner ask 15, 2026-11-23.",
}

#: Closures Overture asserts that we are NOT acting on, with why. Recorded rather than applied.
#:
#: **All eight come from BrightQuery**, a business-registry provider: every one carries confidence
#: 0.55-0.65 and the same single update time, and the signal is about a legal entity rather than
#: an observation of a storefront. An entity can deregister while the shop trades on under new
#: ownership, and it can be registered at an address that was never a shop.
#:
#: Of the original eight, two have a different shop within 100 m in OSM and six have no OSM shop
#: within 100 m at all -- which is weak evidence in both directions, because OSM's coverage of small
#: independent grocers is itself patchy.
#:
#: **SIX REMAIN. Two were superseded on 2026-11-23**, and both supersessions are recorded here
#: rather than by quietly shortening the table.
#:
#: `4f318935-7d66-4a5e-833a-1131fdf4b4fe`, *Longview Poole Road*, left the published layer under
#: owner ask 15. Its hold said *"The name is a street, not a shop, which is what a registry record
#: looks like"*, and the removal AGREES with that fact while resting on different and stronger
#: grounds: the record's own `websites` field reads raleighnc.gov, so it is a municipal asset record
#: filed under a shop taxonomy. That is a statement about what the record IS, which does not depend
#: on whether a registry entity deregistered -- so the closure question this table was holding no
#: longer arises for it. BrightQuery's assertion at confidence 0.65 and the decision not to act on
#: it are kept in this note because a decision that was overtaken is still part of the record.
#:
#: `dc09b073-d0ac-4141-8275-3127c748878d`, *Roofing Inc.*, also left under ask 15. Its hold had
#: ALREADY reached the right diagnosis -- *"Not a grocery under any definition -- it is a roofing
#: company classified as a grocery store, and the closure flag is incidental to the real defect"* --
#: and then held the record anyway, because this table's job was to decide closures and not
#: classifications. So the defect sat correctly described and unacted on for five days. Ask 15 acted
#: on it, with the record's own `websites` field, ncbestroof.com, as the evidence. BrightQuery's
#: assertion at confidence 0.65 is kept here for the same reason as above.
#:
#: Both supersessions share a shape worth naming: a table scoped to ONE question (did this entity
#: deregister?) saw the answer to a different and more important one (is this a shop at all?) and
#: had nowhere to put it. The note is the record of that, so the next table written with a narrow
#: scope carries the same door out.
#:
#: Owner decision 2026-11-17: hold them as pending. The owner also raised building a closure
#: **likelihood index** from several sources (OSM, Google, Yelp) rather than a yes/no list; that
#: is not built, and it carries a licensing question -- Google output may be queried live for
#: validation but must not be persisted as a dataset.
PENDING_CLOSURES: dict[str, str] = {
    "0d5215b0-3192-4bc8-aee5-d5ba6fdb2973":
        "La Tiendita Market. BrightQuery, confidence 0.65. OSM has a `shop=supermarket` named "
        "'ktown market' within 100 m, so something trades there under another name.",
    "27b4e2f0-fc2a-442f-be32-afdaad6fb309":
        "Kinstar International Food Inc. BrightQuery, confidence 0.65. OSM has a "
        "`shop=convenience` named 'Little India' within 100 m -- a different business.",
    "3fed30d2-7538-4f0f-aece-e77ab3a4d484":
        "Carolina Cupboard. BrightQuery, confidence 0.55 -- the lowest of the nine. No OSM shop "
        "within 100 m.",
    "a4cd9c69-95d2-4170-8433-c5e48adc9406":
        "Bell Tower Mart. BrightQuery, confidence 0.65. No OSM shop within 100 m.",
    "b7b9f517-7f58-4a53-abd2-ac8620a93726":
        "Jinja Fair Trade Llc. BrightQuery, confidence 0.65. 'Llc' in the name is the registry "
        "showing through. No OSM shop within 100 m.",
    "fa488537-1065-4f10-80e6-8e7d978375fb":
        "La Nueva Mexicana. BrightQuery, confidence 0.65. No OSM shop within 100 m.",
}


#: Closures FSQ asserts that we ARE acting on. Ten records, by stable Overture id.
#:
#: Owner decision 2026-11-18: *"accept the 10 closures"*. The measurement
#: (`scripts/measure_fsq_coverage.py`, results in
#: `docs/engineering-notes/project-phase1-s3-fsq-coverage.md`) found 25 records FSQ marks closed,
#: of which **12** both agree on name and sit within 60 m. **Eleven are applied here and the
#: twelfth is flagged, not dropped** -- see `FSQ_FLAGGED_CLOSURES` below. Ten were accepted first;
#: the other two were held for a day pending an OSM cross-check and then released; then Sam's Club
#: was moved out of this table into the flag on a third pass, because it had been accepted over an
#: objection nobody had answered. The last entry here, Harris Teeter, records what the cross-check
#: found.
#:
#: **Why this table is separate from `EXCLUDED_PLACE_IDS` above.** Same reason
#: `OSM_CONFIRMED_SUPERMARKETS` is separate from `CURATED_INDEPENDENT_SUPERMARKETS`: this is a
#: REGENERABLE DERIVATION from a dated third-party snapshot, and a hand-made judgement is not. Re-run
#: the script against a newer FSQ release and this set moves; a curated entry is somebody's decision
#: and must not be overwritten by a data refresh.
#:
#: **What `date_closed` is and is not.** The snapshot is FSQ OS Places 2025-01-10, so every date is
#: a LOWER BOUND -- a shop that closed after that release still looks open here, and the absence of
#: a date is not evidence of trading. The dates are also not independently verified; what makes
#: them usable is that `date_closed` is a field neither OSM nor Overture carries at all, so unlike
#: FSQ's CATEGORIES it cannot be an echo of our own Overture-derived data. FSQ's categories are
#: reliable in one direction only and must never reject a record; see the coverage note.
#:
#: Licence: FSQ OS Places is Apache-2.0 with attribution. It is cleared for our own ODbL layers and
#: NOT for upload into OpenStreetMap, which needs explicit import permission. Decision 17 stands.
FSQ_CONFIRMED_CLOSURES: dict[str, str] = {
    "790e99cf-ceef-415a-babb-849e75732fa4":
        "'Kroger', grocery. FSQ OS Places 2025-01-10 carries date_closed=2013-06-25 on 'Kroger' at 0.0 "
        "m with name agreement 1.00. Owner decision 2026-11-18. Corroborates the OTHER Kroger dropped "
        "above, which was decided on independent Overture-signals evidence rather than on FSQ.",
    "3e8b0d81-ca69-4cd5-9948-c8d858ff0a59":
        "'Southern Season', grocery. FSQ OS Places 2025-01-10 carries date_closed=2016-09-27 on "
        "'Southern Season' at 6.3 m with name agreement 1.00. Owner decision 2026-11-18. FSQ files it "
        "under Business and Professional Services rather than food retail, so the CATEGORY is "
        "unreliable here; only the closure is being taken.",
    "4fe3f836-f1f6-45e9-9553-a92a6c9f8752":
        "'El Atoron', grocery. FSQ OS Places 2025-01-10 carries date_closed=2024-06-26 on 'El Atoron' "
        "at 19.4 m with name agreement 1.00. Owner decision 2026-11-18.",
    "2f30a8c1-497f-4ca7-9be4-0654fe808c57":
        "'Family Market', grocery. FSQ OS Places 2025-01-10 carries date_closed=2024-07-07 on 'Family "
        "Market' at 0.0 m with name agreement 1.00. Owner decision 2026-11-18.",
    "0aa4c24d-6a8f-4d54-a1b3-bd684db6bbfc":
        "'Usf Sales', grocery. FSQ OS Places 2025-01-10 carries date_closed=2024-11-04 on 'Usf Sales' "
        "at 0.0 m with name agreement 1.00. Owner decision 2026-11-18.",
    "d3de68dd-7695-47a3-bff5-ece45da1a8b1":
        "'Kroger Pharmacy', pharmacy. FSQ OS Places 2025-01-10 carries date_closed=2019-08-02 on "
        "'Kroger Pharmacy' at 0.0 m with name agreement 1.00. Owner decision 2026-11-18. The pharmacy "
        "counter of the same chain, and the second record corroborating the owner's earlier Kroger "
        "call.",
    "f389d1a5-5f4a-48a5-8055-e00206faba86":
        "'Rite Aid', pharmacy. FSQ OS Places 2025-01-10 carries date_closed=2020-02-11 on 'Rite Aid' at "
        "53.3 m with name agreement 1.00. Owner decision 2026-11-18.",
    "837e9f0d-d5b0-4e16-b3c4-9119c9700e9a":
        "'Walgreens Pharmacy', pharmacy. FSQ OS Places 2025-01-10 carries date_closed=2021-02-08 on "
        "'Walgreens' at 1.2 m with name agreement 1.00. Owner decision 2026-11-18.",
    "6ee316ab-d82f-4890-9a1e-84874d0438c7":
        "'Walgreens', pharmacy. FSQ OS Places 2025-01-10 carries date_closed=2021-03-13 on 'Walgreens' "
        "at 4.8 m with name agreement 1.00. Owner decision 2026-11-18.",
    "13e62ef8-c843-42c7-8be0-7bbaa070a70d":
        "'Rite Aid', pharmacy. FSQ OS Places 2025-01-10 carries date_closed=2024-01-26 on 'Rite Aid' at "
        "45.0 m with name agreement 1.00. Owner decision 2026-11-18.",
    "c7c31e4e-79a8-43d3-aa0c-4c1bf098747e":
        "'Sam's Club', pharmacy candidate. FSQ OS Places 2025-01-10 carries date_closed=2018-02-03 at 37.6 "
        "m with name agreement 1.00. **THE CATEGORY OBJECTION IS NOW RESOLVED, and by evidence from outside "
        "this dataset.** It was this: FSQ files the closed record under `Retail > Warehouse or Wholesale "
        "Store` -- the CLUB, not a pharmacy counter -- and a counter closing inside a club that keeps "
        "trading is indistinguishable in this data from the whole club closing. The answer is that THE "
        "WHOLE CLUB CLOSED. North Carolina's 2018 WARN report records Sam's Club #6668, notice 2018-01-11, "
        "EFFECTIVE 2018-01-26, 187 employees, closure type PERMANENT, at 1101 Shiloh Glenn Dr -- this "
        "record's own address; Walmart closed 63 clubs nationally that month. Contemporary reporting "
        "settles the pharmacy specifically: the pharmacies stayed open about two weeks while prescriptions "
        "were transferred. So the evidence is no longer OSM's SILENCE but an affirmative dated public "
        "filing, and the FSQ date sits five weeks after the effective date rather than standing alone. The "
        "cross-check (`scripts/crosscheck_fsq_closures.py`) still adds only that OSM holds no Sam's Club "
        "within 300 m, nearest tagged retail a Walmart Supercenter at 279.7 m. HISTORY, because the entry "
        "should say how it got here: applied on the owner's second pass 2026-11-18, turned into a flag on "
        "the third while the objection stood, applied again the same day once the third adversarial review "
        "found the WARN filing.",
    # ---- accepted on the second pass the same day, after the cross-check ran ----
    "1937d785-1a98-49c5-9d32-51b7ec7c97af":
        "'Harris Teeter', grocery. FSQ OS Places 2025-01-10 carries date_closed=2017-09-25 on "
        "'Harris Teeter' at 0.0 m with name agreement 1.00. Owner decision 2026-11-18, second "
        "pass. Held for one day because another Kroger in `EXCLUDED_PLACE_IDS` above was dropped "
        "precisely BECAUSE OSM shows a Harris Teeter trading on its site, so a closed Harris "
        "Teeter had to be shown to be a different address before a second store came out. The "
        "cross-check (`scripts/crosscheck_fsq_closures.py`) found it 15,249 m from that Kroger and "
        "23,476 m from the Kroger accepted above -- three different sites, so the hold had no "
        "subject. OSM is silent within 120 m and holds no Harris Teeter within 300 m.",
}


#: **EMPTY, and kept rather than deleted.** For one day this held the two of the twelve that were
#: not applied. The cross-check in `scripts/crosscheck_fsq_closures.py` ran, both went back to the
#: owner with what it found, and both were released -- *"1-4) yes, proceed"*, 2026-11-18. Their
#: entries moved into `FSQ_CONFIRMED_CLOSURES` above and carry the cross-check with them.
#:
#: The name stays so that a later session reads "this was held and then decided" instead of
#: finding nothing and having to reconstruct whether a hold ever existed. The empty dict is also
#: what the tests assert on, which is why it is not a comment.
FSQ_CLOSURES_HELD: dict[str, str] = {}


#: Closures we BELIEVE but do not ACT ON. The record **stays in the layer**; the doubt travels
#: with it as data instead of as a comment in this file.
#:
#: **Owner decision 2026-11-18, third pass: *"1-4) yes, proceed"***, taking the argument an
#: adversarial review made against the second pass. Sam's Club had been applied that morning over
#: a category objection nobody had answered, and the review's point was that the entry then read
#: as settled while `DROPPED_PLACE_IDS` removed the record outright -- *"a publication risk, not a
#: demonstrated false closure"*. A flag keeps the record and keeps the doubt attached to it.
#:
#: **WHAT THIS COSTS, SAID PLAINLY.** Nothing renders this flag yet. Until something does, a
#: household searching for a pharmacy is routed to a place that is probably closed, with no
#: warning -- which is a worse outcome than the drop for that one household, and a better one for
#: the project, because the drop was asserting a fact we do not have. The flag is the honest
#: state; it is not yet the finished feature. `flagged_closure_reason` is the seam a renderer
#: would read, and it exists so that "surface the flag" is a UI change rather than a data change.
#: **EMPTY SINCE 2026-11-18, and kept.** Sam's Club was the one entry, for part of one day. The
#: third adversarial review then produced the thing the flag was waiting for -- a dated state
#: filing -- so the record moved into `FSQ_CONFIRMED_CLOSURES` above, where the doubt it carried
#: is answered rather than deleted.
#:
#: The table and `flagged_closure_reason` stay for the same reason `FSQ_CLOSURES_HELD` stays: the
#: mechanism was right, and the next genuinely uncertain closure belongs here rather than in a
#: comment. A later session reads "this was used and then resolved" instead of having to
#: reconstruct whether it ever existed.
FSQ_FLAGGED_CLOSURES: dict[str, str] = {}

#: Service-point records the service-point screen found, which we are NOT removing, and why.
#:
#: **OWNER DECISION 2026-11-19, reversing ask 3 for these ten.** They were removed in `ae89174`
#: and brought back the same week, after the fifth adversarial review measured what the removal
#: cost: SEVEN of the ten sites were left with no published grocery record at all, one of them with
#: nothing inside 2 km. Three of the ten have a survivor within 150 m; the first report said two,
#: which was wrong because `cee0e25b` sits at 147.9 m, inside the threshold.
#:
#: **THE ARGUMENT THAT WON, and it is not a defect argument.** A collection bay is not a shop you
#: walk round, but it IS a way to get a weekly shop: the household orders the same groceries and
#: collects them. So *"a collection bay is not a weekly shop"* is a policy judgement about which
#: shopping methods count, not a fact about food access. Against that, removing the bay erases the
#: only published record at its site while **the shop it serves is not in the layer to replace
#: it** -- so the removal is correct about the record and wrong about the place.
#:
#: **WHY THE SHOP IS MISSING, which is the real defect under all of this.** Overture files these
#: Walmart stores under `department_store` or `superstore`, and the `grocery` wedge matches only
#: the `grocery_store` hierarchy. Three parents were identified by
#: the fifth review and are named below; they are recorded as plain `Walmart`, which is why the
#: search behind ask 5 -- requiring 'Supercenter' or 'Neighborhood Market' in the name -- could
#: never have found them. The remaining parents are NOT yet identified, and finding them is part of
#: rebuilding ask 5.
#:
#: **SEVEN OF THE TEN WERE REMOVED ON 2026-11-19** once their parent stores were admitted to the
#: layer, which is the condition this table always stated. **THREE REMAIN, AND ALL THREE SIT AT A
#: REAL WALMART SUPERCENTER THAT OVERTURE DOES NOT RECORD AS A STORE.** That is the opposite of
#: what this header said for most of 2026-11-19, and the correction is the point:
#:
#: * The first description -- "no Walmart store record within 6.3, 11.8 and 13.7 km... standalone
#:   collection points" -- had the three figures PAIRED WITH THE WRONG BAYS and read an absence in
#:   ONE source as a fact about the world.
#: * The second description, in `3859f26`, fixed the entries and left this header alone, and still
#:   called `fb500d70` the only genuinely standalone one. The sixth review executed the check: an
#:   FSQ `Walmart Supercenter` record carrying `fb500d70`'s OWN ADDRESS sits 462.9 m away, with a
#:   Walmart bakery and pharmacy at 0.0 m. The FSQ row records no closure, which is not the same as
#:   reporting the store open -- that snapshot is dated 2025-01-10. What carries the conclusion is
#:   WALMART'S OWN LOCATOR, which names Supercenter #1372 at that address and is current.
#: * A third error ran through both: distances to OSM features were measured from their CENTROIDS,
#:   and OSM supermarkets are POLYGONS. By polygon distance `9011ca8b` is INSIDE the Walmart
#:   polygon and `0f2b2452` is 209.0 m from one -- inside the 250 m search that reported neither.
#:
#: So these three are held for one reason: **the store they serve has no Overture record, so there
#: is nothing to admit in its place, and removing the bay would erase the site.** The hold is a
#: TEMPORARY measure pending a store record, NOT a standing argument for publishing a parking bay
#: as a grocery destination. Both sixth-pass reviewers said so independently.
#:
#: Nothing may fold this table into `DROPPED_PLACE_IDS`; a test asserts the two do not intersect.
HELD_SERVICE_POINTS: dict[str, str] = {
    "9011ca8b-301c-40d9-a7c1-a61f6894a42d":
        "'Walmart Grocery Pickup and Delivery', 501 Hampton Pointe B, Hillsborough NC. A COLLECTION BAY, "
        "HELD because the Supercenter it serves has NO OVERTURE STORE RECORD, so nothing can be admitted "
        "in its place. **THE BAY IS INSIDE THE STORE'S OSM POLYGON** -- polygon distance 0.0 m to "
        "`shop=supermarket` named 'Walmart Supercenter' brand Walmart; the 40.0 m first reported was the "
        "distance to that polygon's CENTROID, which is a different quantity. FSQ carries an OPEN "
        "'Walmart Supercenter' at 83.4 m. Nearest Overture Walmart STORE record 13.67 km. Nearest other "
        "published grocery 567.7 m, 'Aldi'. Held as a TEMPORARY stand-in for a missing store record, not "
        "as a grocery destination on its merits. PRELIMINARY.",
    "0f2b2452-b74f-422d-b081-ccbf625ad2fb":
        "'Walmart Grocery Pickup and Delivery', 4431 New Bern Ave, Raleigh NC. A COLLECTION BAY, HELD for "
        "the same reason as `9011ca8b`. **THE CLAIM THAT NO OSM SHOP LAY WITHIN 250 m WAS WRONG**: the "
        "Walmart `shop=supermarket` POLYGON is 209.0 m away, inside that search; only its centroid, at "
        "270.6 m, falls outside, and the search measured centroids. FSQ also carries an OPEN "
        "'Walmart Supercenter' at 229.7 m. Overture records no Walmart store on New Bern Ave at all; its "
        "nearest Walmart STORE record is 6.06 km. Nothing to admit in its place. Nearest other published "
        "grocery 577.7 m, 'Carlie C's IGA'. Held as a TEMPORARY stand-in. PRELIMINARY.",
    "fb500d70-085c-4652-b9bd-fd3545550483":
        "'Walmart Grocery Pickup and Delivery', 4500 Fayetteville Rd, Raleigh NC. A COLLECTION BAY, HELD "
        "for the same reason as the other two. **I CALLED THIS ONE 'GENUINELY STANDALONE' AND IT IS NOT.** "
        "The sixth review executed the check: FSQ carries an OPEN 'Walmart Supercenter' AT THIS RECORD'S "
        "OWN ADDRESS, 4500 Fayetteville Rd, 462.9 m away, with 'Walmart Bakery' and 'Walmart Pharmacy' at "
        "the same address 0.0 m from the bay; the OSM Walmart `shop=supermarket` POLYGON is 413.5 m away "
        "(centroid 485.6 m); and Walmart's own locator calls it Supercenter #1372 at this address with "
        "grocery pickup attached to that store. My search looked 250 m and matched on RADIUS rather than "
        "on the address printed in the record, then promoted a radius-limited absence into a site "
        "classification. Nearest Overture Walmart STORE record 11.78 km. Nearest other published grocery "
        "681.0 m, a second 'Carlie C's IGA' record. Held as a TEMPORARY stand-in. PRELIMINARY.",
}


def flagged_closure_reason(place_id: str) -> str | None:
    """Why this record is doubted, or `None` if it is not.

    The read seam for anything that wants to SHOW the doubt -- a map popup, a result row, an
    export column. It exists so that surfacing a flag is a change to a renderer rather than a
    change to this table, and so that a flag nobody can read is distinguishable from a flag
    nobody has chosen to read yet.
    """
    return FSQ_FLAGGED_CLOSURES.get(place_id)


#: Everything actually removed, from every table that removes anything. One name so a reader can
#: see the whole effect in one place, and so adding a table cannot forget to apply it.
#:
#: `PENDING_CLOSURES`, `FSQ_FLAGGED_CLOSURES` and `HELD_SERVICE_POINTS` are deliberately
#: NOT here. For the held service points that is the owner's 2026-11-19 decision and folding them
#: in would reverse it silently; a test asserts the sets do not intersect. Both record closures
#: we are not acting on, and folding either in would quietly reverse a decision -- for the flag
#: table that reversal is the entire point of it existing, so a test asserts the two sets do not
#: intersect. `FSQ_CLOSURES_HELD` is now empty, so it would contribute nothing; it is still left
#: out, because the day it stops being empty it would otherwise start removing records nobody had
#: agreed to remove.
DROPPED_PLACE_IDS: frozenset[str] = frozenset(EXCLUDED_PLACE_IDS) | frozenset(
    FSQ_CONFIRMED_CLOSURES
)


#: Records an owner decision ADDS to a published wedge, keyed by wedge category.
#:
#: **The mirror of `EXCLUDED_PLACE_IDS`, and the mechanism owner ask 5 had nowhere to land in.**
#: That table removes a record whose taxonomy claims something it is not. This one admits a record
#: whose taxonomy fails to claim something it IS -- Overture files these shops outside the
#: `grocery_store` hierarchy, which is the only hierarchy the `grocery` wedge matches, so a real
#: weekly shop never reaches the layer.
#:
#: **The taxonomy of the 23, MEASURED rather than described.** 11 `department_store`, 6
#: `discount_store`, 4 `superstore`, 2 with NO primary category at all. **No
#: `warehouse_club_store`** -- this comment named that primary and omitted `discount_store`, which
#: is the six ALDIs, until Codex counted the population on 2026-11-22 (owner ask 10). The two
#: uncategorised records are the Publix stores, and absence of a category is absence of
#: information rather than a claim to be something else, which is why they went to a person.
#:
#: **POPULATED 2026-11-19 with 23 records, on the owner's instruction to push through.**
#: All are PRELIMINARY: see [[reference-business-data-is-preliminary]].
#: `scripts/rebuild_missing_grocery_stores.py` proposes the candidates
#: with their evidence and writes `docs/experiments/audit/missing-grocery-stores.csv`; adding any
#: of them moves a published number UPWARD and is an owner decision. The script's `--emit` prints
#: entries in this shape so that applying an approved decision is mechanical rather than retyped.
#:
#: **Why a screen feeds a table here, rather than a rule feeding the wedge.** Widening the wedge to
#: accept `department_store` would admit every department store in the Triangle; narrowing that
#: with the brand tables would change what `grocery` MEANS, which `categories.py` warns against
#: because the published layer is built from it. An id table changes which records, not which rule.
INCLUDED_PLACE_IDS: dict[str, dict[str, str]] = {
    "grocery": {
        "0da6a7a0-a80a-4791-a971-d12369f300c7":
            "Walmart at 7106 Knightdale Blvd, Knightdale, Overture primary=department_store so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: FSQ 'Walmart' at 19.8 m, no "
            "closure recorded in the 2025-01-10 snapshot. Nearest published grocery 250.4 m. Generated by "
            "`scripts/rebuild_missing_grocery_stores.py`. PRELIMINARY.",
        "182dc975-ff2e-4be1-8811-0dc710b42547":
            "Walmart Supercenter at 805 Town Centre Blvd, Clayton, Overture primary=department_store so "
            "outside the `grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM "
            "`shop=supermarket` named 'Walmart Supercenter' at 6.6 m; FSQ 'Walmart Supercenter' at 111.3 m, "
            "no closure recorded in the 2025-01-10 snapshot. Nearest published grocery 110.7 m. Generated by "
            "`scripts/rebuild_missing_grocery_stores.py`. PRELIMINARY.",
        "1e4d47b1-3070-4824-ad66-bdea1e99e688":
            "Aldi at 1770 West Williams Street, Apex, Overture primary=discount_store so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'ALDI' at 0.0 m; FSQ 'ALDI' at 22.6 m, no closure recorded in the 2025-01-10 snapshot. "
            "Nearest published grocery 261.9 m. Generated by `scripts/rebuild_missing_grocery_stores.py`. "
            "PRELIMINARY.",
        "28180454-c72d-495b-a239-5b50dbc3c579":
            "Walmart at 7016 Gb Alford Hwy, Holly Springs, Overture primary=department_store so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'Walmart Supercenter' at 0.0 m; FSQ 'Walmart Supercenter' at 145.1 m, no closure recorded "
            "in the 2025-01-10 snapshot. Nearest published grocery 225.1 m. Generated by "
            "`scripts/rebuild_missing_grocery_stores.py`. PRELIMINARY.",
        "30614a3f-db5b-4c11-94c6-116a59512152":
            "Walmart at 2114 S Main St, Wake Forest, Overture primary=superstore so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'Walmart Supercenter' at 0.0 m; FSQ 'Walmart Supercenter' at 93.6 m, no closure recorded "
            "in the 2025-01-10 snapshot. Nearest published grocery 20.0 m. Generated by "
            "`scripts/rebuild_missing_grocery_stores.py`. PRELIMINARY.",
        "4e8d15fb-950d-40c7-8bd9-7245edfb80d1":
            "Walmart at 1051 E Broad St, Fuquay-Varina, Overture primary=department_store so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'Walmart Supercenter' at 0.0 m; FSQ 'Walmart Supercenter' at 18.2 m, no closure recorded "
            "in the 2025-01-10 snapshot. Nearest published grocery 496.1 m. Generated by "
            "`scripts/rebuild_missing_grocery_stores.py`. PRELIMINARY.",
        "5074229c-e884-4097-8759-4308ddbab7e8":
            "Publix Super Market at **Buffaloe Bend**, 7330 Buffaloe Rd, Raleigh -- not 'Buffaloe Village', "
            "which an earlier version of this entry invented, and that version also said 'same shape as the "
            "record above' when the record above it is a Walmart. Overture carries NO primary category, "
            "which is absence of information rather than a claim to be something else, so the screen listed "
            "it for a person. CORROBORATED INDEPENDENTLY, after the sixth review pointed out that the "
            "original reason cited nothing: `docs/experiments/audit/s3-7-destinations-to-check.csv` already "
            "held an OSM 'Publix At Buffaloe Bend' at this site, and Publix's own locator lists store "
            "#1886 at this address with a grocery department. Nearest published grocery was 2,433.2 m, so "
            "it adds real coverage. PRELIMINARY.",
        "50ada728-6b96-4536-b42b-87c7e192bb8e":
            "Walmart Supercenter at 1015 Lewis St, Oxford, Overture primary=department_store so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'Walmart Supercenter' at 0.0 m; FSQ 'Walmart Supercenter' at 24.7 m, no closure recorded "
            "in the 2025-01-10 snapshot. Nearest published grocery 2732.6 m. Generated by "
            "`scripts/rebuild_missing_grocery_stores.py`. PRELIMINARY.",
        "5a7ca34c-e4b3-4252-b29f-5d72c26469e2":
            "Aldi at 750 Timber Drive, Garner, Overture primary=discount_store so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'ALDI' at 0.0 m; FSQ 'ALDI' at 16.2 m, no closure recorded in the 2025-01-10 snapshot. "
            "Nearest published grocery 138.6 m. Generated by `scripts/rebuild_missing_grocery_stores.py`. "
            "PRELIMINARY.",
        "61939d74-fce6-429f-9681-e33d49507697":
            "Walmart at 1525 Glenn School Rd, Durham, Overture primary=superstore so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'Walmart Supercenter' at 1.1 m; FSQ 'Walmart Supercenter' at 41.8 m, no closure recorded "
            "in the 2025-01-10 snapshot. Nearest published grocery 401.6 m. Generated by "
            "`scripts/rebuild_missing_grocery_stores.py`. PRELIMINARY.",
        "620e6fd2-19b2-4813-b5da-1ce42473f517":
            "Aldi at 4031 Wake Forest Rd, Raleigh, Overture primary=discount_store so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'ALDI' at 13.4 m; FSQ 'ALDI' at 11.5 m, no closure recorded in the 2025-01-10 snapshot. "
            "Nearest published grocery 471.9 m. Generated by `scripts/rebuild_missing_grocery_stores.py`. "
            "PRELIMINARY.",
        "73868d1a-9765-4391-a822-09065645c63b":
            "Aldi at 2132 S Main St, Wake Forest, Overture primary=discount_store so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'ALDI' at 0.0 m; FSQ 'ALDI' at 24.5 m, no closure recorded in the 2025-01-10 snapshot. "
            "Nearest published grocery 466.5 m. Generated by `scripts/rebuild_missing_grocery_stores.py`. "
            "PRELIMINARY.",
        "7cd72bd3-e72b-473c-9205-3465b34d9ac6":
            "Walmart at 8000 Town Dr, Raleigh, Overture primary=department_store so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'Walmart Supercenter' at 9.3 m; FSQ 'Walmart Supercenter' at 25.4 m, no closure recorded "
            "in the 2025-01-10 snapshot. Nearest published grocery 668.0 m. Generated by "
            "`scripts/rebuild_missing_grocery_stores.py`. PRELIMINARY.",
        "84c14b53-6df7-4b18-adc2-a9147ac9b440":
            "Walmart at 1318 Mebane Oaks Rd, Mebane, Overture primary=department_store so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'Walmart Supercenter' at 0.0 m; FSQ 'Walmart Supercenter' at 17.3 m, no closure recorded "
            "in the 2025-01-10 snapshot. Nearest published grocery 812.6 m. Generated by "
            "`scripts/rebuild_missing_grocery_stores.py`. PRELIMINARY.",
        "88f1168d-25de-48ae-b495-73dde8fe674e":
            "Walmart at 3151 Apex Peakway, Apex, Overture primary=department_store so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'Walmart Supercenter' at 0.0 m; FSQ 'Walmart Supercenter' at 19.2 m, no closure recorded "
            "in the 2025-01-10 snapshot. Nearest published grocery 63.4 m. Generated by "
            "`scripts/rebuild_missing_grocery_stores.py`. PRELIMINARY.",
        "8e1fc43f-a5e0-47bc-82e9-3d0766510cbd":
            "Walmart at 6600 Glenwood Ave, Raleigh, Overture primary=department_store so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: FSQ 'Walmart' at 20.0 m, no "
            "closure recorded in the 2025-01-10 snapshot. Nearest published grocery 504.4 m. Generated by "
            "`scripts/rebuild_missing_grocery_stores.py`. PRELIMINARY.",
        "9a9272e3-a667-4207-bce2-88092a86193d":
            "Aldi at 2900 Sunrise Valley Place, Raleigh, Overture primary=discount_store so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'Aldi' at 10.6 m; FSQ 'ALDI' at 31.7 m, no closure recorded in the 2025-01-10 snapshot. "
            "Nearest published grocery 342.8 m. Generated by `scripts/rebuild_missing_grocery_stores.py`. "
            "PRELIMINARY.",
        "aec747a0-3bc4-4b87-81fe-94fae9b03f24":
            "Walmart, 1725 New Hope Church Rd, Raleigh, Overture primary=department_store so outside the "
            "`grocery_store` hierarchy. **THE PARENT STORE OF HELD BAY `cee0e25b`, 27.4 m away.** The screen "
            "put it in REVIEW rather than PROPOSED because brandless 'Total Oriental Foods' sits 133.6 m from "
            "THIS STORE (147.9 m from the bay -- two different pairs, and an earlier version of this entry "
            "quoted the bay's distance in a sentence about the store) and the proximity-doubt gate cannot "
            "tell a different shop from the same shop under a store code. "
            "Looking at it settles it: Total Oriental Foods is a different business, not this Walmart under "
            "another name. Admitted on that judgement, which is exactly what the REVIEW bucket is for. "
            "PRELIMINARY.",
        "c7fee873-a3c5-4691-8b12-f2c76bb101b9":
            "Publix Super Market at **Middle Creek Crossings**, 16100 North Carolina 50, Garner -- not "
            "'Middle Creek Commons', which an earlier version of this entry invented. Overture carries NO "
            "primary category at all, which is absence of information rather than a claim to be something "
            "else, so the screen listed it for a person instead of refusing it. CORROBORATED "
            "INDEPENDENTLY, after the sixth review pointed out that the original reason rested on the brand "
            "name alone: an OSM supermarket polygon sits 71.8 m away, and Publix's own locator lists store "
            "#2031 at this address with a grocery department. Nearest published grocery 320.3 m. "
            "PRELIMINARY.",
        "d3a09343-a70b-4444-a5d8-543fca5b91ec":
            "Walmart Supercenter at 1001 Shiloh Glenn Dr, Morrisville, Overture primary=department_store so "
            "outside the `grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM "
            "`shop=supermarket` named 'Walmart Supercenter' at 0.0 m; FSQ 'Walmart Supercenter' at 21.5 m, "
            "no closure recorded in the 2025-01-10 snapshot. Nearest published grocery 249.3 m. Generated by "
            "`scripts/rebuild_missing_grocery_stores.py`. PRELIMINARY.",
        "dae36e6e-2766-4dfd-95c5-76061fedb1ec":
            "Walmart at 5450 New Hope Commons Dr, Durham, Overture primary=superstore so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'Walmart Supercenter' at 0.0 m; FSQ 'Walmart Supercenter' at 48.5 m, no closure recorded "
            "in the 2025-01-10 snapshot. Nearest published grocery 1450.8 m. Generated by "
            "`scripts/rebuild_missing_grocery_stores.py`. PRELIMINARY.",
        "edb63737-4b7d-4172-9767-cef1f5d91cf9":
            "Aldi at 6300 Creedmoor Rd, Raleigh, Overture primary=discount_store so outside the "
            "`grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM `shop=supermarket` "
            "named 'Aldi' at 9.2 m; FSQ 'ALDI' at 16.1 m, no closure recorded in the 2025-01-10 snapshot. "
            "Nearest published grocery 1491.9 m. Generated by `scripts/rebuild_missing_grocery_stores.py`. "
            "PRELIMINARY.",
        "efdcc3bc-9b12-4a20-9473-2a69a93f4d3c":
            "Walmart Supercenter at 12500 US Hwy 15 501 N, Chapel Hill, Overture primary=superstore so "
            "outside the `grocery_store` hierarchy and invisible to the wedge. Corroborated: OSM "
            "`shop=supermarket` named 'Walmart Supercenter' at 0.0 m; FSQ 'Walmart' at 13.7 m, no closure "
            "recorded in the 2025-01-10 snapshot. Nearest published grocery 1688.7 m. Generated by "
            "`scripts/rebuild_missing_grocery_stores.py`. PRELIMINARY.",
    },
}


def forced_into(category: str) -> frozenset[str]:
    """Ids an owner decision admits to `category`, whatever their taxonomy says.

    Answers cleanly for a category with no inclusions of its own, which is every category but
    `grocery` -- a seam is only worth having if it survives its first user leaving, the same
    reason `flagged_closure_reason` stayed when its table emptied.

    This answers for ONE category name. A category that inherits another's admissions says so
    with `inclusions_from` in `WEDGE_CATEGORIES`, and `select_overture` asks for both; keeping the
    inheritance out of here means a caller reading this table by hand sees exactly what was
    decided, and not a union assembled somewhere else.
    """
    return frozenset(INCLUDED_PLACE_IDS.get(category, {}))


def inclusion_reason(category: str, place_id: str) -> str | None:
    """Why this record was admitted, or `None`. An addition with no reason is unreviewable."""
    return INCLUDED_PLACE_IDS.get(category, {}).get(place_id)


def drop_excluded(gdf):
    """Remove any listed record. A no-op on a frame with no `id` column.

    Frames from `select_named` are built by hand and carry no Overture id, so the absence of the
    column is normal rather than an error worth raising on.
    """
    if "id" not in getattr(gdf, "columns", ()):
        return gdf
    return gdf[~gdf["id"].isin(DROPPED_PLACE_IDS)]
