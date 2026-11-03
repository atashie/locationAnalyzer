import pytest

from locfinder.places.licence import UnknownLicence, resolve_licence

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
