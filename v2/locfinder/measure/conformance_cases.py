"""The conformance corpus. Design §12 artifact 3.

Every case here was derived from design revision 5 and from the executed counterexamples of Codex
passes 15–18. **No expected value in this file was produced by the reference comparator**, which does
not exist yet: each is hand arithmetic, shown in `derivation`, and each is independently reproduced by
the exhaustive oracle in `toy.py`. The suite asserts the two agree.

`rejects` names the wrong answer the case exists to exclude, with its number where a review pass
executed one. That field is the reason this corpus is not merely a regression baseline: a case that
cannot name a wrong answer it separates is not evidence of anything.

One case is **absent on purpose** and recorded here rather than silently omitted: there is no case
pinning the *independent engine's* connector charge (design §2.6), because that quantity depends on
the engine's correlation position, which is observed from Valhalla rather than constructed. Its case
belongs to T6's manifest work, where the correlation position is recorded. Asserting it here would
require inventing the engine's answer.
"""

from __future__ import annotations

from .conformance import Case, Expected
from .toy import ACCESS_SPEED_MPS, ToyEdge, ToyGraph

# --------------------------------------------------------------------------------------------------
# §2.3 — objective-specific views, correctly paired
# --------------------------------------------------------------------------------------------------

OBJECTIVE_VIEWS = Case(
    name="objective_views_are_never_hybrid",
    rule="§2.3 objective-specific views",
    graph=ToyGraph(edges=(
        ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=1.0, cost_base=100.0, osmid=(1,)),
        ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=10.0, cost_base=10.0, osmid=(2,)),
        ToyEdge(1, 2, ((100, 0), (200, 0)), time_s=1.0, cost_base=100.0, osmid=(3,)),
        ToyEdge(1, 2, ((100, 0), (200, 0)), time_s=10.0, cost_base=10.0, osmid=(4,)),
    )),
    origin=(50.0, 0.0),
    destinations=((200.0, 0.0),),
    expected=Expected(objective1_s=1.5, objective2_s=15.0, objective2_cost=15.0,
                      origin_candidates=2,
                      rejected_objective1_s=(10.5, 6.0),
                      rejected_objective2_s=(10.5, 6.0)),
    derivation=(
        "Two consecutive 100 m segments, each with a coincident parallel alternative: fast/expensive "
        "(time 1, cost 100) and slow/cheap (time 10, cost 10). Origin halfway along the first, "
        "destination at the far node; both connectors are zero.\n"
        "Objective 1 minimises TIME, so it takes the fast alternative on both: 0.5 x 1 + 1 = 1.5 s.\n"
        "Objective 2 minimises COST and then reports that journey's time, so it takes the cheap "
        "alternative on both: cost 0.5 x 10 + 10 = 15, time 0.5 x 10 + 10 = 15 s.\n"
        "Both alternatives are coincident, so §2.2's tie rule retains both attachment candidates: 2."
    ),
    provenance="design §2.3's executed table, revision 4",
    rejects=(
        "10.5 s — a time-selected index paired with cost-selected nodes (0.5 x 1 + 10); and "
        "6 s — a cost-selected index paired with time-selected nodes (0.5 x 10 + 1). Both are "
        "hybrids: each leg is individually legal and the pairing is not."
    ),
)

# --------------------------------------------------------------------------------------------------
# §2.2 — attachment, geometric ties
# --------------------------------------------------------------------------------------------------

ATTACHMENT_TIE = Case(
    name="geometric_attachment_tie_keeps_every_minimiser",
    rule="§2.2 geometric ties",
    graph=ToyGraph(edges=(
        ToyEdge(0, 1, ((0, 1), (100, 1)), time_s=100.0, cost_base=100.0, osmid=(1,)),
        ToyEdge(2, 3, ((0, -1), (100, -1)), time_s=1000.0, cost_base=1000.0, osmid=(2,)),
    )),
    origin=(0.0, 0.0),
    destinations=((100.0, 0.0),),
    expected=Expected(objective1_s=100.0 + 2.0 / ACCESS_SPEED_MPS,
                      objective2_s=100.0 + 2.0 / ACCESS_SPEED_MPS,
                      origin_candidates=2,
                      rejected_objective1_s=(1000.0 + 2.0 / ACCESS_SPEED_MPS,),
                      rejected_objective2_s=(1000.0 + 2.0 / ACCESS_SPEED_MPS,)),
    derivation=(
        "Two DISCONNECTED roads from x=0 to x=100, at y=+1 and y=-1. The origin (0,0) is exactly "
        "1 m from both, and so is the destination (100,0). Each connector costs 1 / 1.26 = "
        "0.7936507936507936 s, so both connectors together cost 1.5873015873015872 s.\n"
        "The north road takes 100 s: total 101.5873015873015872 s.\n"
        "The south road takes 1000 s: total 1001.5873015873015872 s.\n"
        "Because the roads are disconnected, a north origin can only reach a north destination. "
        "Retaining BOTH minimisers and minimising over them gives 101.587... — a property of the "
        "geometry. Retaining one gives whichever the convention picked."
    ),
    provenance="design §2.2, pass-18 F7's executed counterexample",
    rejects=(
        "1001.5873015873015872 s — the south road, which satisfies nearest-position, the access cap, "
        "connector charging, direction and objective minimisation just as well as the north road. "
        "At T = 10 min (600 s) the two answers are PASS and FAIL."
    ),
)

# --------------------------------------------------------------------------------------------------
# §2.4 — ties on the selection weight
# --------------------------------------------------------------------------------------------------

COST_TIE_RANKS_BY_TIME = Case(
    name="equal_cost_alternatives_rank_by_travel_time",
    rule="§2.4 ranking",
    graph=ToyGraph(edges=(
        ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=10.0, cost_base=50.0, osmid=(1,)),
        ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=1.0, cost_base=50.0, osmid=(2,)),
    )),
    origin=(0.0, 0.0),
    destinations=((100.0, 0.0),),
    expected=Expected(objective1_s=1.0, objective2_s=1.0, objective2_cost=50.0,
                      origin_candidates=2, rejected_objective2_s=(10.0,)),
    derivation=(
        "Two coincident alternatives tied on cost at 50, with times 10 and 1. Objective 2's "
        "selection weight cannot separate them, so §2.4's first ranking key applies: smallest "
        "TRAVEL TIME. The answer is 1 s, and it does not depend on which alternative was inserted "
        "first. Objective 1 minimises time directly and also gives 1 s."
    ),
    provenance="design §2.4's executed counterexample",
    rejects=(
        "10 s — what the CSR collapse and the edge index both return when the insertion order is "
        "reversed. The defect is not that 10 is far from 1; it is that the reported value is a "
        "property of the input ordering rather than of the graph."
    ),
)

# --------------------------------------------------------------------------------------------------
# §2.2 — penalty apportionment
# --------------------------------------------------------------------------------------------------

PENALTY_APPORTIONED = Case(
    name="edge_penalties_are_apportioned_not_charged_on_entry",
    rule="§2.2 apportionment",
    graph=ToyGraph(edges=(
        # restricted: base cost 1, plus access.py's fixed 120 s per restricted walking edge
        ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=1000.0, cost_base=1.0, penalty=120.0, osmid=(1,)),
        ToyEdge(0, 2, ((0, 0), (0, 50)), time_s=5.0, cost_base=5.0, osmid=(2,)),
    )),
    origin=(0.0, 0.0),
    destinations=((1.0, 0.0), (0.0, 50.0)),
    expected=Expected(objective1_s=5.0, objective1_destination=1,
                      objective2_s=10.0, objective2_cost=1.21, objective2_destination=0,
                      origin_candidates=2, rejected_objective2_s=(5.0,)),
    derivation=(
        "A restricted edge of time 1000, base cost 1 and penalty 120 (total cost 121), and an open "
        "bypass of time 5 and cost 5. Destination 0 sits at x=1, which is fraction 0.01 along the "
        "restricted edge; destination 1 is the bypass's far node.\n"
        "Apportionment charges the SAME fraction to time, base cost and penalty, with no "
        "exceptions: 0.01 x 121 = 1.21 cost, 0.01 x 1000 = 10 s.\n"
        "Objective 1 minimises time: 5 s via the bypass to destination 1, beating 10 s.\n"
        "Objective 2 minimises cost: 1.21 beats 5, so it selects destination 0 and reports ITS "
        "time, 10 s. The two objectives select different destinations here, which is the point."
    ),
    provenance="design §2.2, the restricted-access case",
    rejects=(
        "5 s for objective 2 — the entry-charge model, which bills the whole 120 s on touching the "
        "edge: 0.01 x 1 + 120 = 120.01, losing to the bypass's 5. Design §2.2 names apportionment "
        "as the existing attachment model and makes changing it a semantic amendment under §13."
    ),
)

# --------------------------------------------------------------------------------------------------
# §2.2 — direction legality on a partial edge
# --------------------------------------------------------------------------------------------------

_ONEWAY = ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=100.0, cost_base=100.0, osmid=(1,), oneway=True)

ONEWAY_WITH_RETURN = Case(
    name="oneway_partial_edge_routes_the_long_way_round",
    rule="§2.2 direction legality",
    graph=ToyGraph(edges=(
        _ONEWAY,
        ToyEdge(1, 2, ((100, 0), (100, 10)), time_s=100.0, cost_base=100.0, osmid=(2,),
                oneway=True),
        ToyEdge(2, 0, ((100, 10), (0, 0)), time_s=100.0, cost_base=100.0, osmid=(3,), oneway=True),
    )),
    origin=(80.0, 0.0),
    destinations=((20.0, 0.0),),
    expected=Expected(objective1_s=240.0, objective2_s=240.0, origin_candidates=1,
                      rejected_objective1_s=(60.0,), rejected_objective2_s=(60.0,)),
    derivation=(
        "A one-way u->v edge of time 100 from (0,0) to (100,0), with a one-way return v->w->u of "
        "100 + 100 s. The origin at x=80 is fraction 0.8 along it; the destination at x=20 is "
        "fraction 0.2. Both connectors are zero.\n"
        "The direct traversal would need to go BACKWARD from 0.8 to 0.2, which the edge forbids, so "
        "it is not a candidate at all.\n"
        "The only legal journey leaves forward to node 1 (0.2 x 100 = 20 s), returns 1->2->0 "
        "(100 + 100 = 200 s), and re-enters forward to fraction 0.2 (0.2 x 100 = 20 s): 240 s.\n"
        "The origin is 7.96 m from the return edge 2->0 and the destination 1.99 m from it, both "
        "well outside the 0.01 m tie window, so there is exactly one attachment candidate.\n"
        "THE RETURN ROUTE IS DELIBERATELY SLOW. It was first written at 5 + 5 s, giving 50 s, and "
        "the wrong-implementation test showed that such a case separates nothing: an implementation "
        "ignoring the one-way flag takes the 60 s direct reverse, loses to 50 s, and so returns the "
        "CORRECT answer. The rule is only decision-relevant where the illegal shortcut would win, "
        "so the legal journey must cost more than 60 s."
    ),
    provenance="design §2.2's one-way counterexample",
    rejects=(
        "60 s — the direct reverse partial traversal (0.6 x 100), which is illegal. Walk "
        "symmetrisation supplies the pedestrian reverse; bike and drive do not inherit it, so this "
        "case is the one that must keep working when the gate re-runs per mode in S6."
    ),
)

ONEWAY_NO_RETURN = Case(
    name="oneway_with_no_return_is_no_path_not_off_network",
    rule="§2.2 direction legality / §2.5 NO_PATH",
    graph=ToyGraph(edges=(_ONEWAY,)),
    origin=(80.0, 0.0),
    destinations=((20.0, 0.0),),
    expected=Expected(no_finite_time=True, origin_candidates=1),
    derivation=(
        "The same one-way edge with the return removed. No legal journey exists: the direct reverse "
        "traversal is forbidden and node 1 has no outgoing edge.\n"
        "The oracle enumerates exhaustively and UNBOUNDED, so its empty result is a genuine "
        "NO_PATH. The origin still has ONE attachment candidate, which is how NO_PATH is told apart "
        "from OFF_NETWORK: off-network means zero candidates within max_access_m, and the two have "
        "different remedies (design §3 — searching further answers one and not the other)."
    ),
    provenance="design §2.5, status.py's NO_PATH producibility table",
    rejects=(
        "OFF_NETWORK — which would be wrong here because the origin is ON the network, and which "
        "would carry a bound of access_m / max_speed_mps rather than an unconditional failure."
    ),
)

# --------------------------------------------------------------------------------------------------
# §2.2 — same-edge traversal competes, and can lose
# --------------------------------------------------------------------------------------------------

SAME_EDGE_COMPETES = Case(
    name="same_edge_direct_traversal_is_a_candidate_and_loses",
    rule="§2.2 competition",
    graph=ToyGraph(edges=(
        ToyEdge(0, 1, ((0, 0), (300, 0)), time_s=800.0, cost_base=800.0, osmid=(1,)),
        ToyEdge(0, 4, ((0, 0), (0, 50)), time_s=100.0, cost_base=100.0, osmid=(2,)),
        ToyEdge(4, 5, ((0, 50), (300, 50)), time_s=1.0, cost_base=1.0, osmid=(3,)),
        ToyEdge(5, 1, ((300, 50), (300, 0)), time_s=100.0, cost_base=100.0, osmid=(4,)),
    )),
    origin=(0.0, 0.0),
    destinations=((300.0, 0.0),),
    expected=Expected(objective1_s=201.0, objective2_s=201.0, objective2_cost=201.0,
                      origin_candidates=2, rejected_objective1_s=(800.0,),
                      rejected_objective2_s=(800.0,)),
    derivation=(
        "Origin and destination are the two ends of one slow 800 s edge, and a three-edge bypass "
        "joins the same pair at 100 + 1 + 100 = 201 s. The direct same-edge traversal is a "
        "CANDIDATE and competes under each objective; here it loses, 201 < 800.\n"
        "Costs are equal to times on every edge, so objective 2 selects the same route and reports "
        "201 s.\n"
        "TWO origin candidates, not one: the origin sits on node 0, which is incident to both the "
        "slow edge and the bypass's first edge, so both attach at distance 0 and both are inside the "
        "tie window. This hand count was first written as 1 and the oracle rejected it — recorded "
        "here because it is the clearest evidence that the two routes are independent, and because "
        "'the attachment' reads as singular while a node origin always has one candidate per "
        "incident edge."
    ),
    provenance="design §2.2's executed competition case",
    rejects=(
        "800 s — treating a same-physical-edge attachment pair as settling the route rather than "
        "offering one candidate. The error is 4x here and is not bounded in general."
    ),
)

# --------------------------------------------------------------------------------------------------
# §2.1 — the objective-2 functional
# --------------------------------------------------------------------------------------------------

COST_ARGMIN_THEN_ITS_TIME = Case(
    name="objective2_is_cost_argmin_then_that_pairs_time",
    rule="§2.1 the objective-2 functional",
    graph=ToyGraph(edges=(
        ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=10.0, cost_base=10.0, osmid=(1,)),
        ToyEdge(0, 2, ((0, 0), (0, 100)), time_s=1.0, cost_base=100.0, osmid=(2,)),
    )),
    origin=(0.0, 0.0),
    destinations=((100.0, 0.0), (0.0, 100.0)),
    expected=Expected(objective1_s=1.0, objective1_destination=1,
                      objective2_s=10.0, objective2_cost=10.0, objective2_destination=0,
                      origin_candidates=2, rejected_objective2_s=(1.0,)),
    derivation=(
        "Two destinations reached by one edge each: destination 0 at (cost 10, time 10) and "
        "destination 1 at (cost 100, time 1).\n"
        "Objective 1 minimises time over destinations: 1 s, destination 1.\n"
        "Objective 2 takes the cost-ARGMIN — destination 0 at cost 10 — and reports THAT pair's "
        "time: 10 s."
    ),
    provenance="design §2.1, revision 3's phantom-disagreement counterexample",
    rejects=(
        "1 s — the minimum over the TIMES of cost-optimal paths, a different functional. With "
        "identical engines on both sides it reports 10 - 1 = -9 s of 'engine disagreement' where "
        "there is none, which is how revision 3 would have manufactured an E2 result out of nothing."
    ),
)

OBJECTIVE2_RISES_WITH_A_CHEAPER_DESTINATION = Case(
    name="adding_a_cheaper_destination_raises_objective2",
    rule="§2.1 monotonicity is objective-specific",
    graph=ToyGraph(edges=(
        ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=10.0, cost_base=10.0, osmid=(1,)),
        ToyEdge(0, 2, ((0, 0), (0, 100)), time_s=100.0, cost_base=5.0, osmid=(2,)),
    )),
    origin=(0.0, 0.0),
    destinations=((100.0, 0.0), (0.0, 100.0)),
    expected=Expected(objective1_s=10.0, objective1_destination=0,
                      objective2_s=100.0, objective2_cost=5.0, objective2_destination=1,
                      origin_candidates=2, rejected_objective2_s=(10.0,)),
    derivation=(
        "Destination 0 costs 10 and takes 10 s. Destination 1 is CHEAPER (cost 5) and SLOWER "
        "(100 s). Objective 2 follows cost, so adding destination 1 moves the selection to it and "
        "the reported time RISES from 10 s to 100 s.\n"
        "Objective 1 is unaffected at 10 s: adding a destination can only lower a minimum over "
        "times, and here it does not lower it."
    ),
    provenance="design §2.1, executed",
    rejects=(
        "any property test asserting that objective 2 is monotone non-increasing in the destination "
        "set. It is not, and a suite that asserted it would enforce a defect rather than catch one. "
        "This case exists so that the property is recorded as FALSE in executable form."
    ),
)

# --------------------------------------------------------------------------------------------------
# §2 — the two caps, which are different quantities
# --------------------------------------------------------------------------------------------------

DESTINATION_ELIGIBILITY = Case(
    name="destination_eligibility_is_the_300_m_cap",
    rule="§2 destination eligibility",
    graph=ToyGraph(edges=(
        ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=100.0, cost_base=100.0, osmid=(1,)),
    )),
    origin=(0.0, 0.0),
    destinations=((50.0, 250.0), (50.0, 350.0)),
    expected=Expected(objective1_s=50.0 + 250.0 / ACCESS_SPEED_MPS,
                      objective1_destination=0,
                      eligible=(0,), ineligible=(1,), origin_candidates=1),
    derivation=(
        "One 100 m edge. Destination 0 is 250 m from it and destination 1 is 350 m from it, against "
        "poi_snap_max_m = 300 m: destination 0 is ELIGIBLE and destination 1 is not. An ineligible "
        "destination is excluded from both sides, not scored as unreachable.\n"
        "The journey to destination 0: the origin is at node 0 (fraction 0, zero connector); the "
        "nearest position to (50,250) is (50,0) at fraction 0.5, so 0.5 x 100 = 50 s of edge, then "
        "the 250 m residual connector at the access speed, 250 / 1.26 = 198.41269841269843 s. "
        "Total 248.41269841269843 s.\n"
        "Design §2 records that under nearest-EDGE attachment exactly one of the real 550 grocery "
        "places is ineligible, giving an eligible set of 549 recorded by identity."
    ),
    provenance="design §2's destination-eligibility row",
    rejects=(
        "conflating poi_snap_max_m = 300 m with max_access_m = 200 m — different quantities on "
        "different sides of the journey — which the eligible/ineligible identities pin directly.\n"
        "What this case does NOT separate, recorded because the first version of it claimed "
        "otherwise: treating the ineligible destination as merely unreachable. A minimum over "
        "{248.4126984127, inf} is still 248.4126984127, so no time assertion can see the "
        "difference. Only the explicitly checked eligible and ineligible tuples do (pass-20)."
    ),
)

OFF_NETWORK_ORIGIN = Case(
    name="origin_beyond_max_access_m_is_off_network_not_no_path",
    rule="§2 origin attachment / §2.5 statuses",
    graph=ToyGraph(edges=(
        ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=100.0, cost_base=100.0, osmid=(1,)),
    )),
    origin=(50.0, 250.0),
    destinations=((100.0, 0.0),),
    expected=Expected(no_finite_time=True, origin_candidates=0, eligible=(0,)),
    derivation=(
        "The origin is 250 m from the only edge, against max_access_m = 200 m, so there is NO "
        "attachment candidate and no journey. 'No network within the cap is a status, not a missing "
        "value' (design §2).\n"
        "Zero origin candidates is what separates this from NO_PATH, where the origin is attached "
        "and the network simply does not connect. The destination remains eligible at 0 m: "
        "eligibility is a property of the destination alone."
    ),
    provenance="design §2's origin-attachment row; status.py's OFF_NETWORK",
    rejects=(
        "NO_PATH — which carries an unconditional failure, whereas OFF_NETWORK carries the sound "
        "bound access_m / max_speed_mps = 250 / 1.4 = 178.57 s. Reporting NO_PATH here would turn a "
        "cell that is UNKNOWN at T = 10 min into a FAIL."
    ),
)

# --------------------------------------------------------------------------------------------------
# §2.2 — fraction arithmetic across a multi-segment polyline
# --------------------------------------------------------------------------------------------------

MULTI_SEGMENT_POLYLINE = Case(
    name="fraction_is_measured_along_the_whole_polyline",
    rule="§2.2 partial edges",
    graph=ToyGraph(edges=(
        ToyEdge(0, 1, ((0, 0), (100, 0), (100, 100)), time_s=200.0, cost_base=200.0, osmid=(1,)),
    )),
    origin=(0.0, 0.0),
    destinations=((100.0, 50.0),),
    expected=Expected(objective1_s=150.0, objective2_s=150.0, objective1_destination=0,
                      origin_candidates=1, rejected_objective1_s=(100.0,),
                      rejected_objective2_s=(100.0,)),
    derivation=(
        "One L-shaped edge of two 100 m segments, total length 200 m, total time 200 s. The "
        "destination (100,50) lies on the second segment, 50 m into it, so 150 m along the whole "
        "polyline: fraction 0.75.\n"
        "From node 0 the journey traverses 0.75 x 200 = 150 s, with zero connectors.\n"
        "This case exists because the fraction must be measured along the WHOLE polyline by length, "
        "not within the segment that happens to contain the nearest position."
    ),
    provenance="design §2.2; the oracle's per-segment candidate convention",
    rejects=(
        "100 s — using the within-segment fraction 0.5 instead of the along-polyline fraction 0.75, "
        "a 50 s error on a 150 s journey. The verdicts differ at T = 2 min (120 s), where 100 "
        "PASSES and 150 FAILS. An earlier note here said 2.5 min, which is wrong: at 150 s both "
        "values pass an inclusive threshold (pass-20). Neither is a published threshold, so this "
        "case separates arithmetic rather than a current published verdict."
    ),
    reading="per-segment minima",
)

# --------------------------------------------------------------------------------------------------
# Pass-20's counterexamples. Every one of these exposed a defect that the twelve cases above did
# **not** separate, which is why each arrives with the wrong answer it rejects.
# --------------------------------------------------------------------------------------------------

CONNECTORS_IN_BOTH_OBJECTIVES = Case(
    name="connectors_enter_objective_2s_selection_cost",
    rule="§2.1 both objectives include both connectors",
    graph=ToyGraph(edges=(
        ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=10.0, cost_base=10.0, osmid=(1,)),
        ToyEdge(0, 2, ((0, 0), (0, -100)), time_s=650.0, cost_base=20.0, osmid=(2,)),
    )),
    origin=(0.0, 0.0),
    destinations=((100.0, 100.0), (0.0, -100.0)),
    expected=Expected(objective1_s=10.0 + 100.0 / ACCESS_SPEED_MPS, objective1_destination=0,
                      objective2_s=650.0, objective2_cost=20.0, objective2_destination=1,
                      origin_candidates=2,
                      rejected_objective2_s=(10.0 + 100.0 / ACCESS_SPEED_MPS,)),
    derivation=(
        "Two edges leaving the origin node. A reaches (100,0) at time 10 and cost 10; B reaches "
        "(0,-100) at time 650 and cost 20. Destination 0 sits at (100,100), which is 100 m from A's "
        "far end, so it carries a 100 m connector; destination 1 is B's far node, with none.\n"
        "The connector is charged at the access speed in BOTH totals: 100 / 1.26 = "
        "79.3650793651 s, and the same number in cost, since our cost is in seconds — access.py "
        "adds 120 s per restricted edge to it.\n"
        "Objective 1 minimises time: 10 + 79.3650793651 = 89.3650793651 s to destination 0, against "
        "650 s to destination 1.\n"
        "Objective 2 minimises cost: destination 0 costs 10 + 79.3650793651 = 89.3650793651 and "
        "destination 1 costs 20, so it selects destination 1 and reports ITS time, 650 s."
    ),
    provenance="pass-20 F1, executed",
    rejects=(
        "89.3650793651 s for objective 2 — omitting the connector from the selection cost, which "
        "makes destination 0 cost 10 against destination 1's 20. FAIL becomes PASS at ten minutes. "
        "This defect passed all twelve earlier cases: only UNEQUAL connectors on DIFFERENT "
        "destinations separate it, and none of them had both."
    ),
)

SELF_CROSSING_OCCURRENCES = Case(
    name="two_occurrences_at_one_position_are_two_candidates",
    rule="§2.2 candidate occurrences",
    graph=ToyGraph(edges=(
        ToyEdge(0, 1, ((-100, 0), (0, 0), (0, 100), (100, 100), (100, 0), (0, 0), (0, -100)),
                time_s=1000.0, cost_base=1000.0, osmid=(1,), oneway=True),
    )),
    origin=(0.0, 0.0),
    destinations=((0.0, -100.0),),
    expected=Expected(objective1_s=1000.0 / 6.0, objective2_s=1000.0 / 6.0,
                      origin_candidates=2,
                      rejected_objective1_s=(5000.0 / 6.0,),
                      rejected_objective2_s=(5000.0 / 6.0,)),
    derivation=(
        "One one-way edge whose geometry crosses itself: it reaches (0,0) at arclength 100 m, loops "
        "away through (0,100), (100,100), (100,0), returns to (0,0) at arclength 500 m, and ends at "
        "(0,-100) at arclength 600 m. Total length 600 m, total time 1000 s.\n"
        "The origin (0,0) therefore has TWO zero-distance occurrences, at arclengths 100 and 500. "
        "They are the same place and not the same decision: from the second, only 100 m of edge "
        "remains.\n"
        "Attaching at arclength 500 gives (600 - 500)/600 x 1000 = 166.6666666667 s.\n"
        "Attaching at arclength 100 gives (600 - 100)/600 x 1000 = 833.3333333333 s."
    ),
    provenance="pass-20 F2, executed",
    rejects=(
        "833.3333333333 s — what a candidate key on the rounded XY position returns, because it "
        "merges the two occurrences and keeps one. PASS becomes FAIL at ten minutes, from discarding "
        "400 m of route choice between two points with zero spatial separation. Revision 6 specified "
        "exactly that key; revision 7 keys on along-edge arclength instead."
    ),
    reading="per-segment minima",
)

_SQUARE_FORWARD = ((0, 0), (100, 0), (100, 100), (0, 100), (0, 0))
_SQUARE_REVERSE = ((0, 0), (0, 100), (100, 100), (100, 0), (0, 0))

CLOSED_EDGE_DIRECTION = Case(
    name="the_two_directions_of_a_closed_edge_are_distinct",
    rule="§2.4 canonical directed identity",
    graph=ToyGraph(edges=(
        ToyEdge(0, 0, _SQUARE_FORWARD, time_s=4000.0, cost_base=4000.0, osmid=(7,), oneway=True),
        ToyEdge(0, 0, _SQUARE_REVERSE, time_s=4000.0, cost_base=4000.0, osmid=(7,), oneway=True),
    )),
    origin=(10.0, 0.0),
    destinations=((0.0, 10.0),),
    expected=Expected(objective1_s=200.0, objective2_s=200.0, origin_candidates=2,
                      rejected_objective1_s=(3800.0,), rejected_objective2_s=(3800.0,)),
    derivation=(
        "Two one-way self-loops at node 0, the same square ring traversed in opposite directions. "
        "Perimeter 400 m, time 4000 s, so 10 s per metre.\n"
        "On the REVERSE loop the origin (10,0) lies on the closing segment at arclength 390 "
        "(fraction 0.975) and the destination (0,10) on the opening segment at arclength 10 "
        "(fraction 0.025). Going forward from 0.975 reaches node 0 for 0.025 x 4000 = 100 s, and "
        "continuing forward to 0.025 costs another 100 s: 200 s total.\n"
        "On the FORWARD loop the same two points are at fractions 0.025 and 0.975, so the direct "
        "traversal is 0.95 x 4000 = 3800 s."
    ),
    provenance="pass-20 F3, executed",
    rejects=(
        "3800 s — what results when the two loops share an identity and attachment dedup discards "
        "one of them. For a closed edge `u == v` the endpoints cannot separate the directions and "
        "canonicalising the geometry against reversal removes the only remaining information, so "
        "revision 6's identity made them equal. The answer then depended entirely on insertion "
        "order: 3800 s with the forward loop first, 200 s with the reverse first. PASS/FAIL at ten "
        "minutes decided by input order."
    ),
)

DUPLICATE_IDENTITY_WEIGHTS = Case(
    name="same_identity_alternatives_still_compete_on_weights",
    rule="§2.4 identity and grouping are separate from ranking",
    graph=ToyGraph(edges=(
        ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=2000.0, cost_base=2000.0, osmid=(7,)),
        ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=2.0, cost_base=2.0, osmid=(7,)),
    )),
    origin=(20.0, 0.0),
    destinations=((80.0, 0.0),),
    expected=Expected(objective1_s=1.2, objective2_s=1.2, objective2_cost=1.2,
                      origin_candidates=2,
                      rejected_objective1_s=(802.0,), rejected_objective2_s=(802.0,)),
    derivation=(
        "Two parallel 0 -> 1 edges with the SAME geometry, osmid and length, so the same canonical "
        "directed identity — but weights 2000/2000 and 2/2. Design §2.4 freezes identity and "
        "grouping separately from ranking precisely so that grouping cannot answer a ranking "
        "question.\n"
        "Origin at x=20 is fraction 0.2 along either; destination at x=80 is fraction 0.8. Both "
        "objectives should use the fast alternative: 0.6 x 2 = 1.2 s, cost 1.2.\n"
        "Resolving the duplicate identity to the SLOW edge gives 0.2 x 2000 = 400 s back to node 0, "
        "the fast edge for 2 s, and 0.2 x 2000 = 400 s out again: 802 s."
    ),
    provenance="pass-20 F4, executed",
    rejects=(
        "802 s — what a candidate key on the canonical identity returns when it discards one record "
        "by input order before either objective competes. Identity excludes time and cost, so two "
        "records can share it and differ in exactly the quantity being minimised. FAIL/PASS flips at "
        "ten minutes on insertion order."
    ),
)

CAP_IS_INCLUSIVE = Case(
    name="a_destination_exactly_at_the_cap_is_eligible",
    rule="§2 destination eligibility",
    graph=ToyGraph(edges=(
        ToyEdge(0, 1, ((0, 0), (100, 0)), time_s=100.0, cost_base=100.0, osmid=(1,)),
    )),
    origin=(0.0, 0.0),
    destinations=((100.0, 300.0),),
    expected=Expected(objective1_s=100.0 + 300.0 / ACCESS_SPEED_MPS,
                      objective1_destination=0, eligible=(0,), ineligible=(),
                      origin_candidates=1),
    derivation=(
        "One 100 m edge. The destination is EXACTLY poi_snap_max_m = 300 m from its far end, so it "
        "is eligible: the cap is `<= 300`, not `< 300`.\n"
        "The journey traverses the whole edge for 100 s and then the 300 m connector at the access "
        "speed, 300 / 1.26 = 238.0952380952 s. Total 338.0952380952 s, a ten-minute PASS."
    ),
    provenance="pass-20 F5, executed",
    rejects=(
        "no finite journey at all — which is what a `< cap` comparator returns here, excluding the "
        "destination and leaving an empty eligible set. Read as exhaustion that is a FAIL where the "
        "answer is a 338 s PASS. A mutant replacing each cap with its next float down passed all 78 "
        "tests, because every earlier case used 250 m or 350 m and none sat on a boundary."
    ),
)


# --------------------------------------------------------------------------------------------------

#: The frozen corpus. Order is part of the digest.
CASES: tuple[Case, ...] = (
    OBJECTIVE_VIEWS,
    ATTACHMENT_TIE,
    COST_TIE_RANKS_BY_TIME,
    PENALTY_APPORTIONED,
    ONEWAY_WITH_RETURN,
    ONEWAY_NO_RETURN,
    SAME_EDGE_COMPETES,
    COST_ARGMIN_THEN_ITS_TIME,
    OBJECTIVE2_RISES_WITH_A_CHEAPER_DESTINATION,
    DESTINATION_ELIGIBILITY,
    OFF_NETWORK_ORIGIN,
    MULTI_SEGMENT_POLYLINE,
    CONNECTORS_IN_BOTH_OBJECTIVES,
    SELF_CROSSING_OCCURRENCES,
    CLOSED_EDGE_DIRECTION,
    DUPLICATE_IDENTITY_WEIGHTS,
    CAP_IS_INCLUSIVE,
)

#: Each design rule the plan's T3 table names, mapped to the cases that cover it. A rule with no
#: case is a gap, and a test asserts there are none — the plan requires "every rule of §2".
RULE_COVERAGE: dict[str, tuple[str, ...]] = {
    "objective-specific views, never hybrid": ("objective_views_are_never_hybrid",),
    "the normative tie rule": ("geometric_attachment_tie_keeps_every_minimiser",
                               "equal_cost_alternatives_rank_by_travel_time",
                               "two_occurrences_at_one_position_are_two_candidates",
                               "the_two_directions_of_a_closed_edge_are_distinct",
                               "same_identity_alternatives_still_compete_on_weights"),
    "partial-edge time, cost and penalty apportionment": (
        "edge_penalties_are_apportioned_not_charged_on_entry",
        "fraction_is_measured_along_the_whole_polyline"),
    "direction legality": ("oneway_partial_edge_routes_the_long_way_round",
                           "oneway_with_no_return_is_no_path_not_off_network"),
    "same-edge traversal as a candidate": (
        "same_edge_direct_traversal_is_a_candidate_and_loses",),
    "destination eligibility at 300 m": ("destination_eligibility_is_the_300_m_cap",
                                        "a_destination_exactly_at_the_cap_is_eligible"),
    "origin attachment at 200 m": (
        "origin_beyond_max_access_m_is_off_network_not_no_path",),
    "objective 2 is cost-argmin then its time": (
        "objective2_is_cost_argmin_then_that_pairs_time",
        "adding_a_cheaper_destination_raises_objective2",
        "connectors_enter_objective_2s_selection_cost"),
}

#: Rules of §2 and §2.5 that are **not** graph cases, with where they are tested instead. Recorded
#: so that "every rule of §2" can be checked rather than believed.
RULES_TESTED_WITHOUT_A_GRAPH: dict[str, str] = {
    "bound metric, strictness and soundness (§2.5)":
        "test_conformance.py, against conformance.comparator_outcome — a cost limit is not a time "
        "bound, so it cannot produce a known failure",
    "NO_PATH only from an unbounded search (§2.5)":
        "test_conformance.py, against conformance.comparator_outcome's search_bounded argument",
    "canonical directed-edge identity and reverse pairing (§2.4)":
        "test_conformance.py, against ToyEdge.identity and ToyEdge.geometry_key directly",
    "the complete §7 cross-tab":
        "test_conformance.py, against conformance.CROSS_TAB and conformance.tally",
    "the independent engine's connector charge (§2.6)":
        "NOT TESTED HERE — it depends on Valhalla's observed correlation position, so its case "
        "belongs to T6 where that position is recorded. See this module's docstring.",
}
