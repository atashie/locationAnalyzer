import pytest

from locfinder.places.licence import ALLOWED_LICENCES, UnknownLicence, resolve_licence

RELEASE = "2026-10-21.0"


def test_explicit_allowlisted_licence_wins():
    row = {"sources": [{"dataset": "meta", "license": "CDLA-Permissive-2.0"}]}
    assert resolve_licence(row, release=RELEASE) == "CDLA-Permissive-2.0"


def test_explicit_but_unreviewed_licence_is_quarantined():
    row = {"sources": [{"dataset": "meta", "license": "Some-New-Licence-1.0"}]}
    with pytest.raises(UnknownLicence):
        resolve_licence(row, release=RELEASE)


def test_foursquare_rows_are_apache_via_manifest():
    row = {"sources": [{"dataset": "Foursquare", "license": None}]}
    assert resolve_licence(row, release=RELEASE) == "Apache-2.0"


def test_missing_licence_and_unknown_dataset_is_quarantined():
    row = {"sources": [{"dataset": "someone-new", "license": None}]}
    with pytest.raises(UnknownLicence):
        resolve_licence(row, release=RELEASE)


def test_known_dataset_in_pinned_manifest_resolves():
    row = {"sources": [{"dataset": "meta", "license": None}]}
    assert resolve_licence(row, release=RELEASE) == "CDLA-Permissive-2.0"


def test_unpinned_release_is_quarantined():
    row = {"sources": [{"dataset": "meta", "license": None}]}
    with pytest.raises(UnknownLicence):
        resolve_licence(row, release="9999-01-01.0")


def test_row_without_sources_is_quarantined():
    with pytest.raises(UnknownLicence):
        resolve_licence({"sources": []}, release=RELEASE)
    with pytest.raises(UnknownLicence):
        resolve_licence({}, release=RELEASE)


def test_every_source_must_resolve_not_only_the_first():
    row = {"sources": [{"dataset": "meta", "license": "CDLA-Permissive-2.0"}, {"dataset": "mystery", "license": None}]}
    with pytest.raises(UnknownLicence):
        resolve_licence(row, release=RELEASE)


def test_mixed_valid_sources_return_primary_licence():
    row = {"sources": [{"dataset": "foursquare", "license": None}, {"dataset": "meta", "license": "CDLA-Permissive-2.0"}]}
    assert resolve_licence(row, release=RELEASE) == "Apache-2.0"


def test_custom_manifest_can_be_injected():
    row = {"sources": [{"dataset": "newprovider", "license": None}]}
    assert resolve_licence(row, release="r1", manifests={"r1": {"newprovider": "CC0-1.0"}}) == "CC0-1.0"


def test_sources_may_arrive_as_a_numpy_array_not_a_list():
    """GeoParquet hands this column over as a numpy object array, and `or []` raises on one with
    more than one element ("the truth value of an array ... is ambiguous"). The defect survived
    because the only caller normalised to a list first; the Buildings fetcher did not, and the
    first real payload of 500,592 rows broke on it."""
    import numpy as np

    srcs = np.empty(2, dtype=object)
    srcs[0] = {"dataset": "meta", "license": "CDLA-Permissive-2.0"}
    srcs[1] = {"dataset": "microsoft", "license": "CDLA-Permissive-2.0"}
    assert resolve_licence({"sources": srcs}, release="2026-10-21.0") == "CDLA-Permissive-2.0"

    empty = np.empty(0, dtype=object)
    with pytest.raises(UnknownLicence, match="no sources"):
        resolve_licence({"sources": empty}, release="2026-10-21.0")


def test_one_use_may_widen_the_allowlist_without_widening_it_for_everything():
    """Buildings forced this: all 500,592 Triangle rows quarantined because the theme's sources are
    ODbL-1.0 and a CC BY 4.0 variant. Those are acceptable for a diagnostic that republishes
    nothing and not necessarily for a published dataset, so the caller states the allowlist and the
    strict default stays strict. Mutating the module-level set would have let ODbL rows into every
    other consumer silently."""
    row = {"sources": [{"dataset": "openstreetmap", "license": "ODbL-1.0"}]}
    with pytest.raises(UnknownLicence, match="not on the reviewed allowlist"):
        resolve_licence(row, release="2026-10-21.0")
    widened = ALLOWED_LICENCES | frozenset({"ODbL-1.0"})
    assert resolve_licence(row, release="2026-10-21.0", allowed=widened) == "ODbL-1.0"
    # and the default is untouched afterwards
    with pytest.raises(UnknownLicence):
        resolve_licence(row, release="2026-10-21.0")


def test_a_manifest_resolved_licence_must_also_satisfy_the_allowlist():
    """A dataset with no explicit licence resolves through the pinned manifest, and that answer was
    previously accepted without being checked against the allowlist at all."""
    row = {"sources": [{"dataset": "meta"}]}
    assert resolve_licence(row, release="2026-10-21.0") == "CDLA-Permissive-2.0"
    narrow = frozenset({"CC0-1.0"})
    with pytest.raises(UnknownLicence, match="not on the allowlist for this use"):
        resolve_licence(row, release="2026-10-21.0", allowed=narrow)
