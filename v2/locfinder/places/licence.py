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


def resolve_licence(row: dict, *, release: str, manifests: dict | None = None) -> str:
    """Return the licence of the row's primary (first) source after validating that
    EVERY source entry resolves. Raises UnknownLicence otherwise."""
    manifests = RELEASE_MANIFESTS if manifests is None else manifests
    sources = row.get("sources") or []
    if not sources:
        raise UnknownLicence("row has no sources")
    manifest = manifests.get(release)
    resolved: list[str] = []
    for src in sources:
        src = src or {}
        explicit = src.get("license")
        dataset = (src.get("dataset") or "").strip().lower()
        if explicit:
            if explicit not in ALLOWED_LICENCES:
                raise UnknownLicence(f"licence {explicit!r} (dataset={dataset!r}) is not on the reviewed allowlist")
            resolved.append(explicit)
            continue
        if manifest is None:
            raise UnknownLicence(f"release {release!r} has no pinned manifest")
        if dataset not in manifest:
            raise UnknownLicence(f"release {release!r}: dataset {dataset!r} has no licence and is not in the manifest")
        resolved.append(manifest[dataset])
    return resolved[0]
