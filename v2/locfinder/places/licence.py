"""Per-row licence resolution that FAILS CLOSED.

Every `sources[]` entry on an Overture row must resolve: an explicit licence must be
on the allowlist of licences we have reviewed; a missing licence is accepted only if
the entry's dataset is listed in the pinned manifest for the release actually
downloaded. Anything else raises UnknownLicence and the row is quarantined (never
silently defaulted, which is what localUpdates' `_license_for_row` did; Codex H4/H5).

Manifests are populated by hand after inspecting a release's observed dataset names
and the Overture release notes; they are data, not evidence. Record the inspection in
docs/experiments/source-registry.md when adding or changing an entry.
"""
from __future__ import annotations


class UnknownLicence(Exception):
    pass


# Licences we have read and accept for storage, display, and commercial use
# (research 04 §3.9). Any other string quarantines the row until reviewed.
ALLOWED_LICENCES: frozenset[str] = frozenset({"CDLA-Permissive-2.0", "Apache-2.0", "CC0-1.0"})

# release -> {dataset name (lowercase) -> licence}. Pin only after inspection.
RELEASE_MANIFESTS: dict[str, dict[str, str]] = {
    # Dataset names seen in the Overture Places guide (meta, microsoft, foursquare);
    # CONFIRM against the downloaded release's observed `sources[].dataset` values
    # (scripts/fetch_places.py writes the observed set) before trusting this table.
    "2026-10-21.0": {"meta": "CDLA-Permissive-2.0", "microsoft": "CDLA-Permissive-2.0", "foursquare": "Apache-2.0"},
}


def resolve_licence(row: dict, *, release: str, manifests: dict | None = None,
                    allowed: frozenset[str] | None = None) -> str:
    """Return the licence of the row's primary (first) source after validating that
    EVERY source entry resolves. Raises UnknownLicence otherwise.

    `allowed` lets one *use* widen the allowlist without widening it for everything else. The
    Buildings theme forced the question: every one of 500,592 Triangle buildings quarantined,
    because its sources are ODbL-1.0 (OpenStreetMap, Microsoft ML Buildings) and a CC BY 4.0
    variant (Esri), none of which is in `ALLOWED_LICENCES`. Those are fine for a **diagnostic**
    that rasterises footprints to counts and republishes nothing, and not necessarily fine for a
    published dataset — so the caller states the allowlist that applies to what it is doing, and
    the strict default stays strict. Mutating `ALLOWED_LICENCES` globally would have let ODbL rows
    into every other consumer silently.
    """
    allowed = ALLOWED_LICENCES if allowed is None else allowed
    manifests = RELEASE_MANIFESTS if manifests is None else manifests
    # `or []` raises on a multi-element numpy array ("truth value is ambiguous"), which is exactly
    # what GeoParquet gives for this column. It survived only because the one caller normalised to
    # a list first; the Buildings fetcher did not, and the first real payload broke it.
    sources = row.get("sources")
    sources = [] if sources is None else list(sources)
    if len(sources) == 0:
        raise UnknownLicence("row has no sources")
    manifest = manifests.get(release)
    resolved: list[str] = []
    for src in sources:
        src = src or {}
        explicit = src.get("license")
        dataset = (src.get("dataset") or "").strip().lower()
        if explicit:
            if explicit not in allowed:
                raise UnknownLicence(f"licence {explicit!r} (dataset={dataset!r}) is not on the reviewed allowlist")
            resolved.append(explicit)
            continue
        if manifest is None:
            raise UnknownLicence(f"release {release!r} has no pinned manifest")
        if dataset not in manifest:
            raise UnknownLicence(f"release {release!r}: dataset {dataset!r} has no licence and is not in the manifest")
        from_manifest = manifest[dataset]
        if from_manifest not in allowed:
            raise UnknownLicence(
                f"release {release!r}: dataset {dataset!r} resolves to {from_manifest!r}, which is "
                "not on the allowlist for this use")
        resolved.append(from_manifest)
    return resolved[0]
