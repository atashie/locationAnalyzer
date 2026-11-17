"""Insert a node part-way along an edge, so a destination can attach to a road rather than
only to a junction.

`g1_own_graph_layer.py` snaps a destination to its nearest graph NODE and drops it when that node
is farther than 300 m. Pass 57 measured what that bound excludes: park record #456 is 356.44 m from
the nearest node and **0.17 m from the nearest edge**. The bound is doing a job it was not designed
for -- it was meant to cap the access leg, and `simplify=True` collapses degree-two nodes, so the
distance to the nearest node is a fact about junction density, not about how far the household
walks.

**Splitting is not free, and pass 56 is why.** `speeds.py` charges the restricted-access penalty
PER EDGE:

    data["cost"] = travel_time + access_penalty_s(data, mode)

so cutting a restricted edge in two charges the penalty twice and makes every journey through it
dearer. That is the counterexample that proved "adding nodes would change nothing" wrong, and one
of the six park edges this fallback would split IS restricted.

The rule here is the one `snap.py` already applies to an origin's partial edge: **prorate the whole
cost by the fraction**. Cutting at `f` gives halves costing `f * cost` and `(1 - f) * cost`, which
sum to the original. A split is then exactly cost-neutral and time-neutral for any journey that
traverses the whole edge, so the fallback cannot move an answer it was not meant to touch. The
`access_restricted` flag is a disclosure about the ground rather than a price, so both halves keep
it.
"""
from __future__ import annotations

import networkx as nx
import shapely
from shapely.geometry import LineString
from shapely.ops import substring

#: Attributes that describe a quantity spread along the edge, and so are shared by the two halves
#: in proportion to their length. Everything else is a property of the way and is copied intact.
_PRORATED = ("length", "travel_time", "cost")


def _geometry(G: nx.MultiDiGraph, u, v, data) -> LineString:
    geom = data.get("geometry")
    if geom is not None:
        return geom
    return LineString([(G.nodes[u]["x"], G.nodes[u]["y"]),
                       (G.nodes[v]["x"], G.nodes[v]["y"])])


def _fresh_node_id(G: nx.MultiDiGraph):
    """A node id that cannot collide with an OSM one."""
    ints = [n for n in G.nodes if isinstance(n, int)]
    if len(ints) == G.number_of_nodes() and ints:
        return max(ints) + 1
    i = 0
    while f"split_{i}" in G.nodes:
        i += 1
    return f"split_{i}"


#: A projection closer than this to either end of an edge is treated as being AT that end, so
#: the edge is left whole rather than cut into a zero-length piece. The CSR rejects a non-positive
#: `travel_time` outright, which is how the real case surfaced.
_INTERIOR_EPS = 1e-9


def split_edge_at(G: nx.MultiDiGraph, u, v, frac: float, *, node_id=None, point=None):
    """Cut every edge between `u` and `v` at `frac` along the u->v geometry. Returns the new node.

    `frac` is the normalised distance from `u`. Both directions are cut, because the walk graph is
    symmetrised and leaving the reverse edge whole would turn a two-way road into a one-way stub
    past the new node. Each directed edge is cut at its OWN projection of the split point, so
    parallel edges with different geometries each conserve their own length.

    Mutates `G` and returns the id of the inserted node.
    """
    if not 0.0 < frac < 1.0:
        raise ValueError(
            f"frac={frac} is an endpoint, which is already a node; a zero-length half would "
            f"make the snapper's `at_start`/`at_end` tests ambiguous")
    if not (G.has_edge(u, v) or G.has_edge(v, u)):
        raise ValueError(f"no edge between {u} and {v} to split")

    if point is None:
        # Only safe when there is ONE way between u and v. With parallel ways `get_edge_data`
        # yields an arbitrary one, and a fraction measured on the MATCHED way applied to a
        # different shape put the point on an endpoint -- which cut a zero-length half and made
        # the CSR raise `non-positive or non-finite travel_time=0.0` on the real graph. Callers
        # that matched a specific geometry pass the point itself.
        ref = (G.get_edge_data(u, v) or G.get_edge_data(v, u))
        ref_data = next(iter(ref.values()))
        point = _geometry(G, u, v, ref_data).interpolate(frac, normalized=True)

    new = _fresh_node_id(G) if node_id is None else node_id
    G.add_node(new, x=float(point.x), y=float(point.y))

    keep: list = []
    for a, b in ((u, v), (v, u)):
        if not G.has_edge(a, b):
            continue
        for _key, data in list(G.get_edge_data(a, b).items()):
            geom = _geometry(G, a, b, data)
            f = float(geom.project(point, normalized=True))
            f = min(max(f, 0.0), 1.0)
            if not _INTERIOR_EPS < f < 1.0 - _INTERIOR_EPS:
                # The point is at an end of THIS way, so there is nothing to cut. Keeping it whole
                # is correct rather than a compromise: `a` and `b` both still exist after the
                # split, so `a -> b` stays a real connection beside `a -> new -> b`.
                keep.append((a, b, dict(data)))
                continue
            for lo, hi, start, end in ((0.0, f, a, new), (f, 1.0, new, b)):
                share = hi - lo
                attrs = {k: val for k, val in data.items() if k != "geometry"}
                for name in _PRORATED:
                    if name in data:
                        attrs[name] = float(data[name]) * share
                if "geometry" in data:
                    piece = substring(geom, lo, hi, normalized=True)
                    if isinstance(piece, LineString) and not piece.is_empty:
                        attrs["geometry"] = piece
                G.add_edge(start, end, **attrs)
        G.remove_edges_from([(a, b, k) for k in list(G.get_edge_data(a, b) or {})])

    for a, b, data in keep:
        G.add_edge(a, b, **data)
    return new


def nearest_edge_within(eidx, point, max_m: float):
    """The index of the nearest edge geometry to `point`, or None beyond `max_m`.

    Separate from the split so the caller can report what it would attach to without changing
    anything -- which is what `scripts/measure_park_edge_fallback.py` does.
    """
    i = int(eidx.tree.nearest(point))
    if float(shapely.distance(point, eidx.geoms[i])) > max_m:
        return None
    return i


def _segments(G: nx.MultiDiGraph):
    """Every directed edge as (geometry, u, v). Both directions are present, which costs memory
    and saves a deduplication rule: `split_edge_at` splits both directions anyway, so which one
    the tree returns does not matter."""
    geoms, pairs = [], []
    for u, v, data in G.edges(data=True):
        geoms.append(_geometry(G, u, v, data))
        pairs.append((u, v))
    return shapely.STRtree(geoms), geoms, pairs


def attach_points_to_edges(G: nx.MultiDiGraph, points, max_m: float, *, at_node_m: float = 1.0):
    """Attach each point to its nearest edge, inserting a node where needed.

    Returns one entry per point: the node it attached to, or `None` if no edge lies within
    `max_m`. A point projecting within `at_node_m` of an existing endpoint uses that endpoint and
    splits nothing, because an extra node a few centimetres from an existing one buys nothing and
    makes the snapper's `at_start`/`at_end` tests ambiguous.

    The graph is only touched for points that attach: a refused point leaves it byte for byte as
    it was, which is what makes this safe to run as a fallback for the records a node bound has
    already dropped.
    """
    tree, geoms, pairs = _segments(G)
    gone: set = set()
    out = []
    for pt in points:
        i = int(tree.nearest(pt))
        if (pairs[i] in gone) or ((pairs[i][1], pairs[i][0]) in gone):
            # An earlier point split this edge, so the tree is stale here. Rebuilding is cheap
            # relative to how rarely two destinations share one edge, and it cannot go subtly
            # wrong the way chasing the halves by arithmetic can.
            tree, geoms, pairs = _segments(G)
            gone.clear()
            i = int(tree.nearest(pt))
        if float(shapely.distance(pt, geoms[i])) > max_m:
            out.append(None)
            continue
        u, v = pairs[i]
        geom = geoms[i]
        f = float(geom.project(pt, normalized=True))
        d_start = shapely.Point(geom.coords[0]).distance(pt)
        d_end = shapely.Point(geom.coords[-1]).distance(pt)
        if d_start <= at_node_m:
            out.append(u)
            continue
        if d_end <= at_node_m:
            out.append(v)
            continue
        out.append(split_edge_at(G, u, v, f, point=geom.interpolate(f, normalized=True)))
        gone.add((u, v))
    return out
