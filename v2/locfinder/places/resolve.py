"""Resolve a typed place name to a candidate anchor, bounded to one metro. Phase 1 stage S2.1.

Decision D4 chose the provider split — street addresses from the Census geocoder, place *names*
from our own index — and recorded that the name resolver, the candidate chooser and the correction
flow were **unbuilt**. This is that resolver. It matters because no amount of routing repair fixes a
workplace resolved to the wrong entity, and the measured failures are not subtle:

| query | Census | unbounded Nominatim |
|---|---|---|
| UNC Hospitals | no match | UNC Health Blue Ridge, **Morganton** — 180 km away |
| Southpoint | no match | Southpoint, **Kenosha, Wisconsin** |

Census resolved **none** of ten place-name queries. Nominatim resolved most but, without a region
bias, silently returned a confident wrong answer. Both failure modes are addressed by the same two
decisions: bound the search to the metro, and never auto-pick when the match is ambiguous.

## Decisions, because several are judgement calls

**Bounded by the ROUTING bbox, not the evaluation bbox.** A household's workplace can legitimately
sit outside the area we grid — you commute *into* a metro, or to an office just past its edge. The
routing bbox is the set of places we can actually route to, so it is the honest bound. Using the
evaluation bbox would reject valid anchors; using no bound reproduces the Morganton failure.

**Ambiguity is surfaced, never resolved silently.** When the runner-up is within
`AMBIGUITY_MARGIN` of the leader, the outcome is `ambiguous` and the caller must show a chooser.
"Whole Foods" in this metro is several shops; picking one for the user is how you end up routing to
the wrong side of town. A single confident answer is returned only when it is clearly best.

**Locality words rank, they do not filter.** "Whole Foods Durham" should put the Durham shop first
*and* still offer Chapel Hill, because the typed locality may be the user's mistake rather than the
index's. It ranks as an explicit **tiebreaker** rather than a score bonus — as a bonus it was
silently useless, because the cap that kept scores at most 1.0 erased it for exactly the common case
of several exact name matches.

**OSM outranks Overture on a tie.** An OSM POI is a surveyed feature; Overture's places include a
great deal of business-listing noise, and on the real index that noise competes directly with real
answers — "Unc Hospitals- Accounts" in Durham scored level with the Chapel Hill clinics, and
"Amazon Hub Counter+ (durham - Whole Foods)" placed second for "Whole Foods Durham". This is a
preference, not a quality claim about either source.

**Source-native identity only.** A candidate carries the Overture id or the OSM element id, never a
synthesised key, so the same anchor can be re-resolved and checked after a source refresh (S4.1).

**Licence travels with the candidate.** Decision 17 permits publishing OSM-derived work under ODbL
but forbids OSM contributions sourced from Overture, so an anchor's provenance has to survive
resolution rather than being flattened here.

**Areas and neighbourhoods are out of scope, and that is a measured gap, not an oversight.** On the
real index "RTP" cannot resolve to Research Triangle Park: **no place carries the alias "RTP"**, and
the 35 places whose names contain "Research Triangle Park" are all businesses situated in it. The
index is built from *POIs*; districts, neighbourhoods and campuses are OSM `place=*`/`landuse=*`
polygons and boundary relations, which are not in `osm_pois.parquet`. Area queries therefore return
businesses with the area in their name, which is wrong rather than merely incomplete. Adding an area
index is the fix; pretending a scoring change would help it is not.

**Corroboration is reported.** The same shop usually appears in both Overture and OSM. Those are
merged into one candidate, preferring the **OSM** record — its geometry is the ODbL truth and it is
the contributable one — while recording that the other source agreed. Appearing in both sources is a
useful trust signal and is not available if the two indexes are searched separately.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field

#: A runner-up within this much of the leader's score makes the result ambiguous.
AMBIGUITY_MARGIN = 0.08
#: Candidates of the same normalised name within this distance are one place in two sources.
CORROBORATION_M = 60.0
#: Below this score a match is not worth showing.
SCORE_FLOOR = 0.45
#: Ties on the name score are broken by locality, then by source. Locality is deliberately NOT a
#: score bonus: when it was, `min(1.0, score + bonus)` capped it away for exact matches, so
#: "Harris Teeter Carrboro" tied four exact matches at 1.000 and the Carrboro shop was not even in
#: the top four. Ranking signals that can be neutralised by a cap are worse than none, because they
#: look like they are working.
TIEBREAK_SOURCE_ORDER = ("osm", "overture")

#: Raw source category -> semantic **role**. Comparing raw categories across sources has now gone
#: wrong three times, which is enough to stop doing it: Overture and OSM use different vocabularies,
#: so `supermarket`/`grocery_store` are the same thing, and so are `station`/`train_station` and
#: `fuel`/`gas_station`. Demanding equality broke de-duplication (pass-10 H4); membership of a raw
#: set then broke it again for stations and fuel sites (pass-11 M1), because only the OSM spelling
#: was listed. Roles are compared instead.
_ROLE_BY_CATEGORY = {
    # Somewhere you board, named after the place it serves. Never the destination itself.
    "bus_stop": "stop", "platform": "stop", "stop_position": "stop", "tram_stop": "stop",
    "bus_stop_position": "stop",
    # A whole station, which *is* a destination. `halt` belongs here, not with the platforms: a
    # railway halt is a small station, and classing it as a `stop` stopped one real station
    # recorded as OSM `halt` and Overture `train_station` from corroborating itself (pass-13 M7).
    "halt": "station",
    "station": "station", "train_station": "station", "bus_station": "station",
    "subway_station": "station", "transit_station": "station", "light_rail_station": "station",
    # Fixtures attached to a parent, borrowing its name.
    "atm": "fixture", "vending_machine": "fixture", "entrance": "fixture",
    "parking_entrance": "fixture", "post_box": "fixture", "toilets": "fixture",
    "bicycle_parking": "fixture",
    # Look subsidiary, are standalone destinations in their own right.
    "parking": "parking", "parking_lot": "parking", "parking_garage": "parking",
    "parking_space": "parking",
    "fuel": "fuel", "gas_station": "fuel", "charging_station": "fuel",
    "ev_charging_station": "fuel",
    # Counters and desks *inside* a parent. `pharmacy_counter` was separated by the old raw-category
    # set and fell through to `facility` when roles replaced it, so a pharmacy counter started
    # corroborating the pharmacy it sits in (Codex pass-12 H4).
    #
    # `kiosk` and `information` were in this list and have been removed (pass-13 M7): both are
    # routinely **standalone destinations** — `shop=kiosk` is an ordinary small shop, and an
    # information or visitor centre is somewhere you go — so calling them fixtures stopped a news
    # kiosk recorded as `kiosk`/`newsstand`, and a visitor centre recorded as
    # `information`/`visitor_center`, from corroborating themselves across sources. Adding a batch
    # of plausible-sounding categories at once was the over-correction; these two are destinations.
    "pharmacy_counter": "fixture", "service_desk": "fixture", "ticket_office": "fixture",
}

#: Roles whose features merely *refer* to a place. A bus platform named "Duke Hospital" is how you
#: get to the hospital, not the hospital — which is exactly what the resolver confidently returned
#: before this existed (pass-10 H1: `node/6509747409`, `highway=bus_stop`,
#: `public_transport=platform`, `network=Duke`).
REFERENCE_ROLES = frozenset({"stop"})

#: Phrases that make a stop the *subject* of the query rather than the way to reach something else.
#: "Duke Hospital" wants the hospital; "Franklin Street bus stop" wants the stop, and abstaining
#: there is a false ambiguity (Codex pass-12 M5).
#:
#: **Phrases, not words.** The first version listed single nouns including `bus`, `stand`, `shelter`
#: and `bay`, every one of which is an ordinary part of a business name: a bus stop called "Bay Leaf
#: Indian Cuisine" then beat the restaurant of that name 1.0 to 0.83 *and* suppressed the
#: abstention, so the resolver confidently returned the stop. Codex reproduced the same failure for
#: "Bus Boys and Poets" and "Shelter Club" (pass-13 M6). A single ambiguous noun is not evidence of
#: intent; an explicit transport phrase is.
STOP_INTENT_PHRASES = frozenset({
    "bus stop", "bus stops", "bus station", "bus stand", "bus shelter", "bus bay", "bus terminal",
    "tram stop", "train station", "rail station", "railway station", "subway station",
    "metro station", "light rail station", "light rail stop", "transit center", "transit centre",
    "transit station", "park and ride", "taxi stand", "taxi rank", "bus platform",
    "train platform", "station platform",
})
#: The longest phrase above, in tokens — how far the scan has to look.
_STOP_PHRASE_MAX_N = max(len(q.split()) for q in STOP_INTENT_PHRASES)


def names_a_stop(tokens) -> bool:
    """Did the query itself ask for a stop? Used only to suppress the mixed-reference abstention.

    The phrase must be the **tail** of the query. Phrases rather than words was not enough on its
    own: a business genuinely called "The Bus Stop Cafe Company" contains "bus stop" and would have
    suppressed the abstention exactly as `bay` did. In English the transport noun is the head of the
    phrase and the head comes last, so "Franklin Street bus stop" names a stop while "The Bus Stop
    Cafe Company" does not.

    This also puts the residual error in the safe direction. Missing a genuine intent costs an
    abstention, which shows the user a chooser; inventing one costs a confident wrong answer.
    """
    toks = list(tokens)
    for n in range(2, _STOP_PHRASE_MAX_N + 1):
        if len(toks) >= n and " ".join(toks[-n:]) in STOP_INTENT_PHRASES:
            return True
    return False

#: Roles that sit inside or beside a named parent and borrow its name, so must never be merged with
#: a non-subsidiary record — the cross-source form of the bank-and-its-ATM collapse (pass-10 H4).
#: Deliberately **narrower** than before: a whole station, a car park and a filling station can all
#: be somebody's destination, and treating them as subsidiaries blocked legitimate merges.
SUBSIDIARY_ROLES = frozenset({"stop", "fixture"})


def role_of(category: str | None) -> str:
    """The semantic role of a raw source category. Unknown categories are plain facilities."""
    return _ROLE_BY_CATEGORY.get((category or "").strip().lower(), "facility")

#: Trailing region words a user types that carry no place information inside one metro.
_REGION_NOISE = frozenset({
    "nc", "n c", "north", "carolina", "north carolina", "usa", "us", "united states",
})
#: Words that join a name to a locality and belong to neither.
_CONNECTIVES = frozenset({"the", "in", "at", "on", "near", "of", "a"})
_PUNCT = re.compile(r"[^\w\s]+", re.UNICODE)
_WS = re.compile(r"\s+")
#: Deleted rather than replaced by a space. An apostrophe sits *inside* a word in the possessive
#: form that business names are full of, so spacing it splits the word: "Trader Joe's" became
#: `['trader', 'joe', 's']` while "Trader Joes" became `['trader', 'joes']`, and the two spellings
#: of one query returned different leading candidates. The existing test only covered a *trailing*
#: apostrophe ("Carrboro Farmers' Market"), where adding a space is harmless, which is why this
#: survived — found by the expanded benchmark.
_INTRAWORD = re.compile(r"[\u0027\u2019\u02bc\u0060\u00b4]+")


def normalise(text: str) -> str:
    """Casefold, strip accents and punctuation, collapse whitespace.

    Apostrophes are **deleted**; every other punctuation mark becomes a space. The distinction
    matters because an apostrophe is intra-word in the possessive, so spacing it splits the word and
    "Trader Joe's" stops matching "Trader Joes".
    """
    if not text:
        return ""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = _INTRAWORD.sub("", s)
    s = _PUNCT.sub(" ", s).casefold()
    return _WS.sub(" ", s).strip()


def _tokens(text: str) -> list[str]:
    return [t for t in normalise(text).split() if t]


def strip_region_noise(tokens: list[str]) -> list[str]:
    """Drop trailing state/country words. `['whole','foods','chapel','hill','nc'] -> ...'hill'`."""
    out = list(tokens)
    while out and out[-1] in _REGION_NOISE:
        out.pop()
    # "north carolina" as a pair at the end
    if len(out) >= 2 and " ".join(out[-2:]) in _REGION_NOISE:
        out = out[:-2]
    return out


@dataclass(frozen=True)
class Place:
    """One indexed place, from whichever source."""

    source: str                 # "overture" | "osm"
    source_id: str
    name: str
    lon: float
    lat: float
    aliases: tuple[str, ...] = ()
    brand: str | None = None
    locality: str | None = None
    category: str | None = None
    licence: str | None = None
    #: Street address, so a chooser can tell two same-named candidates apart. On the real index
    #: "Harris Teeter [Wake Forest]" appeared twice and nothing on screen distinguished them.
    address: str | None = None


@dataclass(frozen=True)
class Candidate:
    place: Place
    score: float
    matched_on: str
    corroborated_by: tuple[str, ...] = ()
    #: Whether a locality typed in the query matches this candidate's locality.
    locality_match: bool = False
    #: Which reading of the query this match used; 0 is the intact query. A match on the whole
    #: query as a name is stronger evidence than a match on a truncated query plus a locality, and
    #: ranking by locality first made the destructive reading win (pass-11 H2): "Durham Coffee"
    #: scored 1.000 for a place called "Coffee" on the stripped reading and 1.000 for the real
    #: "Durham Coffee" on the intact one, and the locality tie-break chose the wrong one.
    reading: int = 0

    @property
    def lonlat(self) -> tuple[float, float]:
        return (self.place.lon, self.place.lat)


@dataclass(frozen=True)
class Resolution:
    """`outcome` is the whole point: a caller must branch on it, not just read `candidates[0]`."""

    query: str
    outcome: str                        # resolved | ambiguous | not_found
    candidates: tuple[Candidate, ...] = ()
    #: How many candidates matched before the presentation limit, so a caller can say "and N more"
    #: instead of silently hiding them.
    n_matched: int = 0

    @property
    def anchor(self) -> Candidate | None:
        """The single answer, or None. Deliberately None when ambiguous."""
        return self.candidates[0] if self.outcome == "resolved" and self.candidates else None


def _score(query_tokens: list[str], text: str, *, kind: str) -> tuple[float, str] | None:
    """Score one query against one name/alias/brand string."""
    cand = _tokens(text)
    if not cand or not query_tokens:
        return None
    q, c = set(query_tokens), set(cand)
    base = {"name": 1.0, "alias": 0.95, "brand": 0.90}[kind]
    if query_tokens == cand:
        return base, f"{kind}:exact"
    if q <= c:
        # every typed word appears in the name: "southpoint" in "the streets at southpoint"
        return base * (0.55 + 0.35 * len(q) / len(c)), f"{kind}:contains"
    if c <= q:
        # The name is a subset of what was typed. A flat score here was a serious defect
        # (Codex pass-10 H2): "Durham Whole Foods" resolved confidently to **"Durham", the Amtrak
        # station**, because a one-word name scored 0.85 however much of the query it ignored.
        # Scale by the share of the query the name actually accounts for, so a name covering one
        # word of three cannot outrank one covering all three.
        return base * 0.85 * (len(c) / len(q)), f"{kind}:subset"
    if normalise(text).startswith(" ".join(query_tokens)):
        return base * 0.75, f"{kind}:prefix"
    inter = len(q & c)
    if inter:
        return base * 0.6 * inter / len(q | c), f"{kind}:overlap"
    return None


class PlaceIndex:
    """An inverted token index over the metro's places, so a query scores only plausible rows."""

    def __init__(self, places: list[Place]):
        self.places = places
        self._by_token: dict[str, set[int]] = defaultdict(set)
        self._localities: set[str] = set()
        for i, p in enumerate(places):
            for text in (p.name, p.brand, *p.aliases):
                for t in _tokens(text or ""):
                    self._by_token[t].add(i)
            if p.locality:
                self._localities.add(normalise(p.locality))

    def __len__(self) -> int:
        return len(self.places)

    @property
    def localities(self) -> frozenset[str]:
        return frozenset(self._localities)

    def _readings(self, tokens: list[str]) -> list[tuple[list[str], str | None]]:
        """Every plausible `(name tokens, locality)` reading of the query, intact one first.

        The intact query is always a reading, because a locality word is often part of the name —
        "Durham Coffee", "Carrboro Farmers Market", "The Streets At Southpoint". Stripping it and
        scoring only the remainder produced confident wrong answers (pass-11 H2).
        """
        out: list[tuple[list[str], str | None]] = [(list(tokens), None)]
        name, loc, locality_is_prefix = self._split_locality(tokens)
        locality = " ".join(loc) if loc else None
        if loc and name != tokens:
            out.append((name, locality))
            # The connective between a name and a locality is noise, but the same word can *begin*
            # the name. Stripping it inside `_split_locality` meant the ladder never offered the
            # name with the word still attached: "Durham The Coffee" produced only "Coffee", which
            # matched a different shop exactly while "The Coffee" was never scored intact at all
            # (Codex pass-12 H3). So it is a further, more destructive rung instead.
            # The split side comes from the split itself. Reconstructing it by comparing tokens —
            # `tokens[:len(loc)] != loc` — misread a query whose remaining name *begins* with the
            # same words as the locality it removed from the end: "Durham Coffee in Durham" dropped
            # the trailing "Durham", then decided the locality had been a prefix, never produced the
            # trimmed "Durham Coffee" reading, and resolved to a different place called "Durham
            # Coffee In" (pass-13 M5). Preserving the raw remainder was right; inferring where it
            # came from was a new defect.
            at_end = not locality_is_prefix
            trimmed = self._strip_boundary_connective(name, at_end=at_end)
            if trimmed != name:
                out.append((trimmed, locality))
        # A leading "the" is genuinely ambiguous: part of a name in "The Streets At Southpoint",
        # filler in "the Whole Foods in Durham". Removing it unconditionally broke the first case
        # and keeping it broke the second, so it becomes one more reading — more destructive, so it
        # only wins when nothing less destructive scores as well.
        base = out[-1][0]
        if base and base[0] in _CONNECTIVES and len(base) > 1:
            out.append((base[1:], locality))
        return out

    @staticmethod
    def _strip_boundary_connective(tokens: list[str], *, at_end: bool) -> list[str]:
        """Drop a connective **only** where the locality was removed.

        Stripping both ends destroyed names that begin with one: "The Streets At Southpoint
        Durham" became "Streets At Southpoint", which then matched a *different* record exactly
        (pass-11 H2). The word between a name and a locality is noise; a word at the far end of the
        name is part of the name.
        """
        out = list(tokens)
        if at_end:
            while len(out) > 1 and out[-1] in _CONNECTIVES:
                out.pop()
        else:
            while len(out) > 1 and out[0] in _CONNECTIVES:
                out.pop(0)
        return out or list(tokens)

    def _split_locality(self, tokens: list[str]) -> tuple[list[str], list[str], bool]:
        """`(name tokens, locality tokens, locality_is_prefix)` with the name left **raw**.

        It used to strip a boundary connective here, which silently removed a rung from
        `_readings`' ladder (pass-12 H3). Splitting and trimming are separate readings of the same
        query, so they are separate steps.

        The third element is returned rather than inferred: the caller needs to know which end the
        locality came off, and deriving that from token equality fails whenever the remaining name
        starts with the same words as the locality removed from the other end (pass-13 M5).
        """
        """Separate words that name a locality in this index from the place name itself.

        A **leading** locality counts too: "Durham Whole Foods" is as natural as "Whole Foods
        Durham", and handling only the trailing form is what let the Amtrak station win (pass-10
        H2). Connective words between the two are dropped, so "the Whole Foods in Durham" parses
        rather than returning nothing.

        Only ever a prefix or a suffix, and only if something is left over: "Durham" alone must stay
        a place query, not become an empty name with a locality hint that matches everything there.
        """
        # locality as a SUFFIX: the boundary is at the end of the name
        for cut in range(1, len(tokens)):
            if " ".join(tokens[cut:]) in self._localities:
                return tokens[:cut], tokens[cut:], False
        # locality as a PREFIX: the boundary is at the start of the name
        for cut in range(len(tokens) - 1, 0, -1):
            if " ".join(tokens[:cut]) in self._localities:
                return tokens[cut:], tokens[:cut], True
        return tokens, [], False

    def resolve(self, query: str, *, limit: int = 8) -> Resolution:
        raw = strip_region_noise(_tokens(query))
        if not raw:
            return Resolution(query=query, outcome="not_found")
        # Every plausible reading of the query is scored and the best explanation wins. Committing
        # to one parse before scoring was a confident-wrong-answer generator (Codex pass-11 H2):
        # "Durham Coffee" stripped "Durham" as a locality and then resolved to a place called
        # "Coffee" at 1.000, beating the actual "Durham Coffee" at 0.725. A locality word can be
        # part of a name, and only the scores can tell.
        readings = self._readings(raw)

        pool: set[int] = set()
        for name_tokens, _ in readings:
            for t in name_tokens:
                pool |= self._by_token.get(t, set())
        if not pool:
            return Resolution(query=query, outcome="not_found")

        scored: list[Candidate] = []
        for i in pool:
            p = self.places[i]
            best: tuple[float, int, str, bool] | None = None
            for r_idx, (name_tokens, locality) in enumerate(readings):
                loc_hit = bool(locality and p.locality and normalise(p.locality) == locality)
                for kind, text in (("name", p.name), ("brand", p.brand),
                                   *(("alias", a) for a in p.aliases)):
                    if not text:
                        continue
                    got = _score(name_tokens, text, kind=kind)
                    if got is None:
                        continue
                    # Best score wins; on a tie the **less destructive** reading wins, so an exact
                    # match on the whole query beats an exact match on a truncated one.
                    cand_key = (got[0], -r_idx)
                    if best is None or cand_key > (best[0], -best[1]):
                        best = (got[0], r_idx, got[1], loc_hit)
            if best is None:
                continue
            score, r_idx, how, loc_hit = best
            if loc_hit:
                how += "+locality"
            if score >= SCORE_FLOOR:
                scored.append(Candidate(place=p, score=round(score, 4), matched_on=how,
                                        locality_match=loc_hit, reading=r_idx))
        locality = any(loc for _, loc in readings[1:]) if len(readings) > 1 else None

        if not scored:
            return Resolution(query=query, outcome="not_found")
        if limit < 1:
            raise ValueError("limit must be at least 1")
        scored.sort(key=_rank_key)
        merged = _merge_corroborating(scored)
        # Decide on the COMPLETE ranking, then truncate for presentation. Deciding after the cut
        # let `limit=1` turn an ambiguous pair into a confident answer (Codex pass-10 H3).
        outcome = _decide(merged, bool(locality), stop_intent=names_a_stop(raw))
        # A query that IS a locality name cannot be answered confidently by an index of POIs.
        # This generalises the area gap recorded in the module docstring for "RTP". The mechanism
        # the expanded benchmark exposed: Overture's listing noise contains records whose *name* is
        # exactly a place name — a gym called "Chapel Hill" 6.2 km from Chapel Hill — and a sole
        # exact match scores 1.000 and wins outright, so the resolver confidently returned the gym.
        # "Durham" was passing its benchmark assertion only because the record of that name happens
        # to sit 520 m from the reference, which is luck rather than correctness.
        #
        # Downgrading to `ambiguous` keeps the candidates, which are worth showing, and withholds a
        # confidence the index cannot support. Areas need an area index; until then this is the
        # honest outcome.
        if outcome == "resolved" and " ".join(raw) in self._localities:
            outcome = "ambiguous"
        return Resolution(query=query, outcome=outcome, candidates=tuple(merged[:limit]),
                          n_matched=len(merged))


def is_reference_feature(place: "Place") -> bool:
    """A stop or platform named after somewhere else, rather than that place."""
    return role_of(place.category) in REFERENCE_ROLES


def is_subsidiary_feature(place: "Place") -> bool:
    """A feature that sits inside or beside a named parent and borrows its name — an ATM at a bank,
    a platform at a hospital. Never merged with a non-subsidiary record, however close and however
    similarly named."""
    return role_of(place.category) in SUBSIDIARY_ROLES


def _rank_key(c: Candidate):
    """Name score, then the intact-query reading, then locality, then not being a transport stop,
    then source, then the name.

    The transport demotion is deliberately narrow. It is not an inference about what the user
    meant — that would need a query-intent model this does not have — but the observation that a
    platform named "Duke Hospital" is a reference to the hospital. On a tie the hospital wins; if
    the stop is the only candidate it still resolves, because a transit anchor is a real query.
    """
    try:
        src = TIEBREAK_SOURCE_ORDER.index(c.place.source)
    except ValueError:
        src = len(TIEBREAK_SOURCE_ORDER)
    return (-c.score, c.reading, not c.locality_match, is_reference_feature(c.place), src,
            c.place.name, c.place.source_id)


def _decide(candidates: list[Candidate], had_locality: bool, *, stop_intent: bool = False) -> str:
    """`resolved` only when one candidate is clearly best.

    A typed locality is decisive when **exactly one candidate in the leading score tier** matches
    it: "Harris Teeter Carrboro" names one shop even though four others match the name exactly.
    Comparing only the leader against the *second* candidate was not enough (Codex pass-10 M1) —
    score sorts before locality, so a third candidate in the same tier can match the locality too,
    and then nothing has been disambiguated.
    """
    if not candidates:
        return "not_found"
    if len(candidates) == 1:
        return "resolved"
    lead, second = candidates[0], candidates[1]
    # A stop or platform may win on name, but it is a *reference* to a place. Where a
    # non-reference candidate also matches, the resolver does not know which the household meant,
    # and the honest answer is a chooser. Demotion alone could not help here (Codex pass-11 H4):
    # it is only a tie-break, and the Duke Hospital platform scores 1.000 against hospitals at
    # 0.7833, so it won outright and was presented as the single answer to a hospital query.
    # A stop leading a field that also contains the place it is named after is the pass-10 H1
    # failure, and abstaining is right — unless the user asked for the stop, in which case the
    # abstention invents an ambiguity that is not there (pass-12 M5).
    if not stop_intent and is_reference_feature(lead.place) and any(
            not is_reference_feature(c.place) for c in candidates):
        return "ambiguous"
    if had_locality and lead.locality_match:
        tier = [c for c in candidates if lead.score - c.score < AMBIGUITY_MARGIN]
        if sum(1 for c in tier if c.locality_match) == 1:
            return "resolved"
    if lead.score - second.score >= AMBIGUITY_MARGIN:
        return "resolved"
    return "ambiguous"


def _metres_between(a: Place, b: Place) -> float:
    """Rough planar metres. Adequate for a 60 m corroboration test inside one metro."""
    import math
    lat = math.radians((a.lat + b.lat) / 2.0)
    dx = (a.lon - b.lon) * 111_320.0 * math.cos(lat)
    dy = (a.lat - b.lat) * 110_540.0
    return math.hypot(dx, dy)


def _mergeable(a: Place, b: Place) -> bool:
    """Is this the same physical place seen twice, rather than two places sharing a name?

    Two conditions, and the second took two attempts to get right.

    **Different sources.** Cross-source agreement is the evidence that justifies collapsing two
    records into one; two records from the same source are two records. This alone kills the case
    Codex pass-10 H4 demonstrated: a bank and its own ATM 9 m apart, both OSM, both called Acme,
    which merged into the ATM and made the ambiguity vanish.

    **The same role.** This took three attempts. Demanding *equal categories* was wrong and broke
    real de-duplication immediately: the two sources use different vocabularies, so the single
    Harris Teeter in Carrboro arrives as OSM `supermarket` and Overture `grocery_store` and stopped
    merging, which made "Harris Teeter Carrboro" ambiguous between one shop counted twice.
    Replacing that with a *subsidiary-vs-parent* boolean was too coarse in the other direction
    (Codex pass-12 H4): `parking` and `fuel` are deliberately not subsidiary, because a car park is
    a destination in its own right, so OSM's **RDU** car park and Overture's **RDU** airport both
    answered "not subsidiary" and merged into one confidently resolved car park.

    Roles are the right granularity: coarse enough to span two taxonomies, fine enough that a car
    park is not an airport. Equality is also the honest test — there is no pair of *different* roles
    that should collapse, and a compatibility matrix would only be a place to hide one.
    """
    if a.source == b.source:
        return False
    if role_of(a.category) != role_of(b.category):
        return False
    return _metres_between(a, b) <= CORROBORATION_M


def _merge_corroborating(scored: list[Candidate]) -> list[Candidate]:
    """Collapse the same place found in two sources, preferring the OSM record.

    OSM wins because its geometry is the ODbL truth and it is the contributable one (decision 17);
    the other source is recorded as corroboration rather than discarded, since appearing in both is
    a trust signal. Candidates are grouped by normalised name first, so the scan no longer compares
    every candidate against every other one regardless of name.
    """
    out: list[Candidate] = []
    by_name: dict[str, list[int]] = {}
    # Which sources each merged cluster already holds. Checking only the surviving representative's
    # source let one OSM record absorb any number of Overture records (Codex pass-11 H3): after the
    # first merge the representative was still OSM, so the next Overture record passed the same
    # test and two independent places vanished into one confident answer.
    members: dict[int, set[str]] = {}
    for cand in scored:
        key = normalise(cand.place.name)
        for j in by_name.get(key, ()):
            kept = out[j]
            if cand.place.source in members.get(j, {kept.place.source}):
                continue
            if _mergeable(kept.place, cand.place):
                sources = set(kept.corroborated_by) | {cand.place.source}
                winner = kept
                if kept.place.source != "osm" and cand.place.source == "osm":
                    sources = set(kept.corroborated_by) | {kept.place.source}
                    winner = Candidate(place=cand.place, score=max(kept.score, cand.score),
                                       matched_on=cand.matched_on)
                # The reading has to come from the member that supplied the evidence, not from the
                # member that supplied the geometry, and it must not be allowed to default. It did
                # default to 0 — the intact-query value — so merging two records that only matched
                # a *stripped* reading manufactured an intact match and let it outrank a genuine
                # one (Codex pass-12 H2): "Durham Coffee" was correctly ambiguous between a Durham
                # Coffee in Raleigh and a Coffee in Durham until an Overture copy of the latter
                # arrived within 60 m, at which point it resolved confidently to "Coffee".
                evidence = max((kept, cand), key=lambda c: (c.score, -c.reading))
                # `matched_on` explains the score, so it has to come from the member that earned
                # it, not from the member that supplied the geometry. Both sources naming a place
                # "Northside Coffee Roasters" with only Overture carrying the alias "Northside"
                # produced a candidate scored 0.95 from that exact alias while reporting
                # `name:contains` from the OSM representative (pass-13 L2).
                out[j] = Candidate(place=winner.place,
                                   score=max(kept.score, cand.score),
                                   matched_on=evidence.matched_on,
                                   corroborated_by=tuple(sorted(sources - {winner.place.source})),
                                   locality_match=kept.locality_match or cand.locality_match,
                                   reading=evidence.reading)
                members.setdefault(j, {kept.place.source}).add(cand.place.source)
                break
        else:
            by_name.setdefault(key, []).append(len(out))
            members[len(out)] = {cand.place.source}
            out.append(cand)
    out.sort(key=_rank_key)
    return _promote_real_places_within_the_leading_tier(out)


def _promote_real_places_within_the_leading_tier(ranked: list[Candidate]) -> list[Candidate]:
    """Within the leading score tier, a real place outranks a feature that merely refers to one.

    `_rank_key` already carries `is_reference_feature`, but it sits *after* the score, so it only
    decides an **exact** tie, and exact ties are rare. Widening that to the ambiguity tier means a
    near-tie the resolver has already declared it cannot separate on score is broken on identity
    instead.

    **It does not rescue "Duke Hospital", and I first wrote that it did.** On the real index the bus
    platform is the only *exact* match at 1.000 and the nearest real hospital record scores 0.7833 —
    a 0.22 gap, far outside any sane tier. No reordering can promote a 0.78 over a 1.00 without
    abandoning exact matching, so that query is the naming gap pass 10 identified, not a ranking
    defect. This rule is for the genuine near-tie, and the test below constructs one.

    The tier is `AMBIGUITY_MARGIN`, the same width that decides ambiguity: inside it the resolver
    has already declared it cannot separate the candidates on score, so breaking that near-tie on
    identity is using the evidence it has rather than inventing any. Outside the tier nothing moves,
    which is why an explicit "Franklin Street bus stop" query — where the stop leads by 0.17 — is
    unaffected, and a stop that is the only candidate still resolves.

    Found by the expanded benchmark (`benchmarks/resolver_queries.json`), not by a review.
    """
    if len(ranked) < 2:
        return ranked
    lead_score = ranked[0].score
    tier_end = 0
    while tier_end < len(ranked) and lead_score - ranked[tier_end].score < AMBIGUITY_MARGIN:
        tier_end += 1
    tier = ranked[:tier_end]
    if not any(is_reference_feature(c.place) for c in tier):
        return ranked
    if all(is_reference_feature(c.place) for c in tier):
        return ranked
    # stable: the existing order is preserved within each group
    tier = [c for c in tier if not is_reference_feature(c.place)] + \
           [c for c in tier if is_reference_feature(c.place)]
    return tier + ranked[tier_end:]


def pin(lon: float, lat: float, *, label: str = "dropped pin") -> Candidate:
    """The correction flow's end state: the user put the anchor here, so nothing is inferred.

    A corrected pin still has to pass S2.2's routability check before it can be used, which is why
    this returns a `Candidate` rather than a coordinate pair.
    """
    return Candidate(
        place=Place(source="user_pin", source_id="pin", name=label, lon=float(lon), lat=float(lat)),
        score=1.0, matched_on="user_pin")


# ---------------------------------------------------------------------------------------------
# Loading the metro index from the acquired sources.
#
# `geopandas` is imported lazily so the resolver itself stays importable (and testable) without it.
# Both loaders bound by the metro's **routing** bbox, for the reason in the module docstring.
# ---------------------------------------------------------------------------------------------

def _missing(v) -> bool:
    """Is this a *scalar* missing value?

    Deliberately not `pandas.isna`, which returns an array for a list-like field and then raises
    when that array is used as a condition. `pandas.NA` is recognised by name so this module does
    not import pandas.
    """
    if v is None:
        return True
    if isinstance(v, float) and v != v:                      # NaN
        return True
    return type(v).__name__ == "NAType"


def _first(*values):
    """First usable string. Recognises `pandas.NA` and NaN as missing (Codex pass-10 M5: `pd.NA`
    was being stringified into the literal name `<NA>`)."""
    for v in values:
        if _missing(v):
            continue
        s = str(v).strip()
        if s and s.lower() not in ("nan", "none", "<na>"):
            return s
    return None


def _as_sequence(v) -> list:
    """A list-like nested field as a list, or empty. Guards the `len()`/indexing that a scalar
    NaN turns into a TypeError (pass-10 M5)."""
    if _missing(v):
        return []
    if isinstance(v, (str, bytes, dict)):
        return []
    try:
        return list(v)
    except TypeError:
        return []


def _common_names(names) -> list[str]:
    """Overture's `names.common` is a `map<string,string>`, which Arrow hands to pandas as a
    **list of key/value tuples**, not a dict — so a dict-only reader silently dropped every alias
    (Codex pass-10 M4). Both forms are accepted."""
    if not isinstance(names, dict):
        return []
    common = names.get("common")
    if isinstance(common, dict):
        return [str(v) for v in common.values() if not _missing(v)]
    out = []
    for item in _as_sequence(common):
        if isinstance(item, dict):
            val = item.get("value", item.get("1"))
            if not _missing(val):
                out.append(str(val))
        elif isinstance(item, (tuple, list)) and len(item) == 2 and not _missing(item[1]):
            out.append(str(item[1]))
    return out


def from_overture(gdf, *, bbox=None) -> list[Place]:
    """Places from an `overture_places_accepted.parquet` frame."""
    out: list[Place] = []
    pts = gdf.geometry.representative_point()
    for (_, row), pt in zip(gdf.iterrows(), pts):
        if pt is None or pt.is_empty:
            continue
        lon, lat = float(pt.x), float(pt.y)
        if bbox is not None and not bbox.contains(lat, lon):
            continue
        names = row.get("names") if isinstance(row.get("names"), dict) else {}
        primary = _first(names.get("primary"))
        brand = None
        b = row.get("brand")
        if isinstance(b, dict) and isinstance(b.get("names"), dict):
            brand = _first(b["names"].get("primary"))
        if not primary and not brand:
            continue
        locality = address = None
        addrs = _as_sequence(row.get("addresses"))
        if addrs:
            a0 = addrs[0]
            if isinstance(a0, dict):
                locality = _first(a0.get("locality"))
                address = _first(a0.get("freeform"))
        tax = row.get("taxonomy")
        category = _first(tax.get("primary")) if isinstance(tax, dict) else None
        out.append(Place(
            source="overture", source_id=str(row.get("id")),
            name=primary or brand, lon=lon, lat=lat,
            aliases=tuple(_common_names(names)), brand=brand, locality=locality,
            category=category or _first(row.get("basic_category")),
            licence=_first(row.get("licence")), address=address,
        ))
    return out


def from_osm(gdf, *, bbox=None, licence: str = "ODbL-1.0") -> list[Place]:
    """Places from an `osm_pois.parquet` frame, whose index is the `feature_id` (`way/123`)."""
    out: list[Place] = []
    cols = set(gdf.columns)
    alias_cols = [c for c in ("alt_name", "short_name", "official_name", "loc_name", "name:en")
                  if c in cols]
    pts = gdf.geometry.representative_point()
    for (fid, row), pt in zip(gdf.iterrows(), pts):
        if pt is None or pt.is_empty:
            continue
        lon, lat = float(pt.x), float(pt.y)
        if bbox is not None and not bbox.contains(lat, lon):
            continue
        name = _first(row.get("name"))
        brand = _first(row.get("brand"), row.get("operator"))
        if not name and not brand:
            continue
        aliases = tuple(a for a in (_first(row.get(c)) for c in alias_cols) if a)
        # `highway`, `public_transport` and `railway` were missing, so a bus platform arrived with
        # no category at all and could not be told from a hospital (Codex pass-10 H1).
        category = _first(row.get("amenity"), row.get("shop"), row.get("leisure"),
                          row.get("healthcare"), row.get("tourism"), row.get("public_transport"),
                          row.get("highway"), row.get("railway"), row.get("office"),
                          row.get("building"))
        house, street = _first(row.get("addr:housenumber")), _first(row.get("addr:street"))
        address = " ".join(x for x in (house, street) if x) or _first(row.get("addr:full"))
        out.append(Place(
            source="osm", source_id=str(fid), name=name or brand, lon=lon, lat=lat,
            aliases=aliases, brand=brand, locality=_first(row.get("addr:city")),
            category=category, licence=licence, address=address,
        ))
    return out


def build_metro_index(overture_gdf=None, osm_gdf=None, *, bbox=None) -> PlaceIndex:
    """One index over both sources, so corroboration can be detected (see the module docstring)."""
    places: list[Place] = []
    if osm_gdf is not None:
        places += from_osm(osm_gdf, bbox=bbox)
    if overture_gdf is not None:
        places += from_overture(overture_gdf, bbox=bbox)
    return PlaceIndex(places)
