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

#: Trailing region words a user types that carry no place information inside one metro.
_REGION_NOISE = frozenset({
    "nc", "n c", "north", "carolina", "north carolina", "usa", "us", "united states",
})
_PUNCT = re.compile(r"[^\w\s]+", re.UNICODE)
_WS = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Casefold, strip accents and punctuation, collapse whitespace."""
    if not text:
        return ""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(c for c in s if not unicodedata.combining(c))
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

    @property
    def lonlat(self) -> tuple[float, float]:
        return (self.place.lon, self.place.lat)


@dataclass(frozen=True)
class Resolution:
    """`outcome` is the whole point: a caller must branch on it, not just read `candidates[0]`."""

    query: str
    outcome: str                        # resolved | ambiguous | not_found
    candidates: tuple[Candidate, ...] = ()

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
        # the name is a subset of what was typed: the extra words are usually a locality
        return base * 0.85, f"{kind}:subset"
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

    def _split_locality(self, tokens: list[str]) -> tuple[list[str], list[str]]:
        """Separate trailing words that name a locality in this index from the place name itself.

        Only a *trailing* run is taken, and only if something is left over: "Durham" alone must
        stay a place query, not become an empty name with a locality hint.
        """
        for cut in range(1, len(tokens)):
            tail = " ".join(tokens[cut:])
            if tail in self._localities:
                return tokens[:cut], tokens[cut:]
        return tokens, []

    def resolve(self, query: str, *, limit: int = 8) -> Resolution:
        raw = strip_region_noise(_tokens(query))
        if not raw:
            return Resolution(query=query, outcome="not_found")
        name_tokens, locality_tokens = self._split_locality(raw)
        locality = " ".join(locality_tokens) or None

        # candidate generation: any place sharing a token with the typed name
        pool: set[int] = set()
        for t in name_tokens:
            pool |= self._by_token.get(t, set())
        if not pool:
            return Resolution(query=query, outcome="not_found")

        scored: list[Candidate] = []
        for i in pool:
            p = self.places[i]
            best: tuple[float, str] | None = None
            for kind, text in (("name", p.name), ("brand", p.brand),
                               *(("alias", a) for a in p.aliases)):
                if not text:
                    continue
                got = _score(name_tokens, text, kind=kind)
                if got and (best is None or got[0] > best[0]):
                    best = got
            if best is None:
                continue
            score, how = best
            loc_hit = bool(locality and p.locality and normalise(p.locality) == locality)
            if loc_hit:
                how += "+locality"
            if score >= SCORE_FLOOR:
                scored.append(Candidate(place=p, score=round(score, 4), matched_on=how,
                                        locality_match=loc_hit))

        if not scored:
            return Resolution(query=query, outcome="not_found")
        scored.sort(key=_rank_key)
        merged = _merge_corroborating(scored)[:limit]
        return Resolution(query=query, outcome=_decide(merged, bool(locality)),
                          candidates=tuple(merged))


def _rank_key(c: Candidate):
    """Name score first, then a locality match, then source preference, then a stable name."""
    try:
        src = TIEBREAK_SOURCE_ORDER.index(c.place.source)
    except ValueError:
        src = len(TIEBREAK_SOURCE_ORDER)
    return (-c.score, not c.locality_match, src, c.place.name, c.place.source_id)


def _decide(candidates: list[Candidate], had_locality: bool) -> str:
    """`resolved` only when one candidate is clearly best.

    A typed locality is decisive when exactly one candidate in the leading score tier matches it:
    "Harris Teeter Carrboro" names one shop even though four others match the name exactly. Without
    that rule the margin test alone called it ambiguous and buried the right answer.
    """
    if not candidates:
        return "not_found"
    if len(candidates) == 1:
        return "resolved"
    lead, second = candidates[0], candidates[1]
    if had_locality and lead.locality_match and not second.locality_match:
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


def _merge_corroborating(scored: list[Candidate]) -> list[Candidate]:
    """Collapse the same place found in two sources, preferring the OSM record.

    OSM wins because its geometry is the ODbL truth and it is the contributable one (decision 17);
    the other source is recorded as corroboration rather than discarded, since appearing in both is
    a trust signal.
    """
    out: list[Candidate] = []
    for cand in scored:
        for j, kept in enumerate(out):
            same_name = normalise(kept.place.name) == normalise(cand.place.name)
            if same_name and _metres_between(kept.place, cand.place) <= CORROBORATION_M:
                sources = set(kept.corroborated_by) | {cand.place.source}
                winner = kept
                if kept.place.source != "osm" and cand.place.source == "osm":
                    sources = set(kept.corroborated_by) | {kept.place.source}
                    winner = Candidate(place=cand.place, score=max(kept.score, cand.score),
                                       matched_on=cand.matched_on)
                out[j] = Candidate(place=winner.place,
                                   score=max(kept.score, cand.score),
                                   matched_on=winner.matched_on,
                                   corroborated_by=tuple(sorted(sources - {winner.place.source})),
                                   locality_match=kept.locality_match or cand.locality_match)
                break
        else:
            out.append(cand)
    out.sort(key=_rank_key)
    return out


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

def _first(*values):
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s and s.lower() not in ("nan", "none"):
            return s
    return None


def _common_names(names) -> list[str]:
    """Overture's `names.common` is a language map; keep the values as aliases."""
    if not isinstance(names, dict):
        return []
    common = names.get("common")
    if isinstance(common, dict):
        return [str(v) for v in common.values() if v]
    return []


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
        addrs = row.get("addresses")
        if addrs is not None and len(addrs):
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
        category = _first(row.get("amenity"), row.get("shop"), row.get("leisure"),
                          row.get("healthcare"), row.get("tourism"))
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
