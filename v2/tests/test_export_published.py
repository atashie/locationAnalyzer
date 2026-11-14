"""The product export, after Codex pass 43.

Three of that pass's findings were in this file and none would have been caught by running it:
the transform guard existed only on the branch that did not need it, the v1 size baseline
compressed the wrong bytes, and a rejected candidate shipped inside the product manifest where
every entry starts enabled.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import export_published_layers as exporter                      # noqa: E402
from locfinder import wire                                      # noqa: E402

PUBLISHED = (pathlib.Path(__file__).resolve().parents[1]
             / "spikes" / "g3-render" / "fixtures" / "published")


def test_a_build_record_that_disagrees_with_its_array_is_refused():
    """Pass 43 F8. A transform that disagrees with its array does not fail — it moves every cell,
    silently, and exports the layer under the wrong footprint. The guard was written only on the
    fallback branch, which is the one that already could not get this wrong."""
    build = {"x_min": 661800.0, "y_max": 4003600.0, "cell_m": 200.0,
             "nrows": 258, "ncols": 322, "crs": "EPSG:32617"}
    transform, crs = exporter.source_transform(build, (258, 322))
    assert crs == "EPSG:32617" and transform is not None
    with pytest.raises(SystemExit, match="refusing to export"):
        exporter.source_transform(build, (322, 258))


def test_the_v1_size_baseline_is_the_plane_v1_would_have_written():
    """Pass 43 F5. v1 stored `NODATA` at every missing cell; v2's value plane stores a lower
    bound there. Comparing v2's two planes against v2's own value plane made the baseline too
    large — a constant compresses far better than a bound — and the overhead too small."""
    value = np.array([5, 40, 120, wire.VALUE_NONE], dtype=np.uint8)
    status = np.array([wire.OK, wire.OFF_NETWORK, wire.BEYOND_HORIZON, wire.OUTSIDE],
                      dtype=np.uint8)
    v1 = exporter.v1_plane(value, status)
    assert list(v1) == [5, 255, 255, 255]
    assert (v1[status != wire.OK] == 255).all()


@pytest.mark.skipif(not (PUBLISHED / "manifest.json").exists(),
                    reason="run scripts/export_published_layers.py first")
def test_the_product_manifest_carries_only_the_chosen_grid():
    """Pass 43 F4. Every manifest entry starts enabled in the page, so shipping the rejected
    200 m candidate beside the product made the default answer the intersection of two versions
    of one criterion — which removed 4,022 passing pixels at the default threshold. A candidate
    is exported only when asked for."""
    manifest = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    # Read from `wire` rather than written out: the encoding set lived in five places and a
    # version bump silently missed three of them.
    assert manifest["encoding"] in wire.READABLE_ENCODINGS
    assert [l["cell_m"] for l in manifest["layers"]] == [100.0]
    for layer in manifest["layers"]:
        assert layer["horizon_s"] > 0, "a layer with no horizon cannot decide BEYOND_HORIZON"


@pytest.mark.skipif(not (PUBLISHED / "manifest.json").exists(), reason="not exported")
def test_every_exported_status_code_is_one_the_decoder_defines():
    manifest = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    for layer in manifest["layers"]:
        status = np.frombuffer((PUBLISHED / layer["status_file"]).read_bytes(), dtype=np.uint8)
        assert set(np.unique(status).tolist()) <= set(wire.STATUS_CODES)


@pytest.mark.skipif(not (PUBLISHED / "manifest.json").exists(), reason="not exported")
def test_a_beyond_horizon_cell_in_the_export_matches_the_manifest_horizon():
    """The redundancy that makes the value plane a checksum. `worker.js` refuses a manifest whose
    horizon disagrees with the planes; this asserts the export never produces such a pair."""
    import math
    manifest = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    for layer in manifest["layers"]:
        value = np.frombuffer((PUBLISHED / layer["value_file"]).read_bytes(), dtype=np.uint8)
        status = np.frombuffer((PUBLISHED / layer["status_file"]).read_bytes(), dtype=np.uint8)
        bh = status == wire.BEYOND_HORIZON
        if not bh.any():
            continue
        expected = min(int(math.ceil(layer["horizon_s"] / 60.0)), wire.VALUE_MAX)
        assert (value[bh] == expected).all()


def test_the_regrid_measurement_indexes_pixels_the_way_rasterio_does():
    """`measure_export_regrid.py` re-implements the exported raster's tiling as
    `floor((lon - west) / (east - west) * ncols)`, while the exporter builds its destination with
    `rasterio.transform.from_bounds`. If those two tilings differ, every number in that
    measurement is an artifact of the arithmetic rather than of the reprojection.

    They agree on all 512,633 structures; this checks the same property on a dense synthetic grid
    that includes the edges and the half-open boundaries, which the structure population does not
    reach.
    """
    from rasterio.transform import from_bounds, rowcol

    west, south, east, north = -79.20, 35.70, -78.50, 36.15
    nrows, ncols = 514, 643
    transform = from_bounds(west, south, east, north, ncols, nrows)

    rng = np.random.default_rng(3)
    lon = np.concatenate([rng.uniform(west, east, 20000),
                          np.full(64, west), np.full(64, east),
                          np.linspace(west, east, 2000)])
    lat = np.concatenate([rng.uniform(south, north, 20000),
                          np.linspace(south, north, 64), np.linspace(north, south, 64),
                          np.full(2000, north)])
    mine_col = np.floor((lon - west) / (east - west) * ncols).astype(np.int64)
    mine_row = np.floor((north - lat) / (north - south) * nrows).astype(np.int64)
    rr, cc = rowcol(transform, lon, lat, op=np.floor)
    assert np.array_equal(mine_col, np.asarray(cc, dtype=np.int64))
    assert np.array_equal(mine_row, np.asarray(rr, dtype=np.int64))

def _write_flag_bundle(tmp_path, monkeypatch, shape, *, horizon_s, flagged=None):
    """A `<stem>_restricted_route{,_build}` pair in a temporary layer directory."""
    monkeypatch.setattr(exporter, "LAYERS", tmp_path)
    flag = np.zeros(shape, dtype=np.uint8) if flagged is None else np.asarray(flagged, np.uint8)
    np.save(tmp_path / "s_restricted_route.npy", flag)
    meta = {"built": "2026-11-13", "mode": "walk", "category": "grocery"}
    if horizon_s is not None:
        meta["horizon_s"] = horizon_s
    (tmp_path / "s_restricted_route_build.json").write_text(json.dumps(meta), encoding="utf-8")
    return flag


def test_a_flag_raster_built_under_a_different_horizon_is_refused(tmp_path, monkeypatch):
    """**The 5,145-cell defect was exactly this.** `encode_route_flag` catches a mismatch only
    when it runs one way -- a smaller surface horizon leaves flags where the status is no longer
    OK. A LARGER surface horizon leaves cells newly OK whose flag was never computed, so they ship
    ROUTE_CLEAR, and a clear flag asserts nothing, which is why nothing downstream can notice. So
    the horizons are compared where the two artifacts are paired."""
    _write_flag_bundle(tmp_path, monkeypatch, (2, 3), horizon_s=3600.0)
    with pytest.raises(SystemExit) as excinfo:
        exporter.load_route_flag("s", (2, 3), 7200.0)
    message = str(excinfo.value)
    assert "3600" in message and "7200" in message
    # It has to say which direction the disagreement runs, because the two have different
    # consequences and only one of them is caught anywhere else.
    assert "unflagged" in message or "no longer publishes" in message


def test_a_matching_horizon_is_accepted(tmp_path, monkeypatch):
    flag = _write_flag_bundle(tmp_path, monkeypatch, (2, 3), horizon_s=7200.0,
                              flagged=[[1, 0, 0], [0, 0, 1]])
    got = exporter.load_route_flag("s", (2, 3), 7200.0)
    assert got is not None
    assert np.array_equal(got, flag)


def test_a_flag_raster_with_no_recorded_horizon_is_accepted_but_named(tmp_path, monkeypatch,
                                                                     capsys):
    """The raster in the repository predates the field, so refusing it would make this change a
    rebuild rather than a check. The gap is printed rather than passed over -- *absence is not
    evidence of cleanliness* applies to the build record too."""
    _write_flag_bundle(tmp_path, monkeypatch, (2, 3), horizon_s=None)
    got = exporter.load_route_flag("s", (2, 3), 7200.0)
    assert got is not None
    assert "records no horizon_s" in capsys.readouterr().out


def test_an_absent_flag_raster_is_none_rather_than_a_plane_of_zeros(tmp_path, monkeypatch):
    """`None` means "this layer does not disclose", which is a different statement from "no route
    is restricted" and no consumer may collapse the two."""
    monkeypatch.setattr(exporter, "LAYERS", tmp_path)
    assert exporter.load_route_flag("s", (2, 3), 7200.0) is None


# ---------------------------------------------------------------------------------------------
# Pass 49 finding 1: the provenance check, and the control that makes its result mean something.


def _tiny_grid():
    """A 100 m source grid, small enough that the reprojection is one-to-one.

    With one source cell per published cell, a deliberate mix of planes is the only thing that
    can make the check fail.
    """
    from rasterio.transform import from_origin
    return from_origin(661800.0, 4003600.0, 100.0, 100.0), "EPSG:32617"


def _bounds_for(transform, shape, crs):
    """The WGS84 bounds that put the published grid over the source grid."""
    import rasterio.warp
    from rasterio.transform import array_bounds
    nrows, ncols = shape
    west, south, east, north = array_bounds(nrows, ncols, transform)
    return rasterio.warp.transform_bounds(crs, "EPSG:4326", west, south, east, north)


def _reproject_all(transform, crs, bounds, value, status, dest):
    nrows, ncols = value.shape
    out = {
        "value": exporter.reproject_plane(value, transform, crs, src_fill=wire.VALUE_NONE,
                                          dst_fill=wire.VALUE_NONE, bounds=bounds,
                                          nrows=nrows, ncols=ncols),
        "status": exporter.reproject_plane(status, transform, crs, src_fill=wire.OUTSIDE,
                                           dst_fill=wire.OUTSIDE, bounds=bounds,
                                           nrows=nrows, ncols=ncols),
    }
    if dest is not None:
        out["destination"] = exporter.reproject_plane(
            dest, transform, crs, src_fill=wire.DEST_NONE, dst_fill=wire.DEST_NONE,
            bounds=bounds, nrows=nrows, ncols=ncols, dtype=wire.DEST_DTYPE)
    return out


def test_the_provenance_check_passes_when_every_plane_shares_a_source_cell():
    value = np.array([[5, 6, 7], [8, 9, 10]], dtype=np.uint8)
    status = np.full((2, 3), wire.OK, dtype=np.uint8)
    dest = np.array([[0, 1, 2], [2, 1, 0]], dtype=wire.DEST_DTYPE)
    transform, crs = _tiny_grid()
    bounds = _bounds_for(transform, value.shape, crs)
    pub = _reproject_all(transform, crs, bounds, value, status, dest)
    got = exporter.verify_provenance(
        "tiny", transform, crs, bounds, *value.shape,
        source={"value": value, "status": status, "destination": dest},
        published=pub)
    assert got["cells_traced_to_a_source_cell"] == value.size
    assert got["planes_compared"] == ["destination", "status", "value"]


def test_the_provenance_check_catches_a_destination_from_another_source_cell():
    """**The positive control.** A check never shown to fail says nothing when it passes.

    Two published cells keep their own times and statuses and swap destinations. That is exactly
    the mutation Codex ran on the shipped plane, where both directions of the destination
    invariant held, all three aggregates were unchanged, and two journeys were misidentified.
    This check is the one that has to catch it.
    """
    value = np.array([[5, 6, 7], [8, 9, 10]], dtype=np.uint8)
    status = np.full((2, 3), wire.OK, dtype=np.uint8)
    dest = np.array([[0, 1, 2], [2, 1, 0]], dtype=wire.DEST_DTYPE)
    transform, crs = _tiny_grid()
    bounds = _bounds_for(transform, value.shape, crs)
    pub = _reproject_all(transform, crs, bounds, value, status, dest)
    mixed = pub["destination"].copy()
    mixed[0, 0], mixed[0, 2] = mixed[0, 2], mixed[0, 0]
    assert not np.array_equal(mixed, pub["destination"]), "the control changed nothing"
    # And the exchange passes the invariant it is meant to defeat: presence is untouched.
    assert np.array_equal(mixed == wire.DEST_NONE, pub["destination"] == wire.DEST_NONE)
    with pytest.raises(SystemExit, match="not the destination of the source cell"):
        exporter.verify_provenance(
            "tiny", transform, crs, bounds, *value.shape,
            source={"value": value, "status": status, "destination": dest},
            published={**pub, "destination": mixed})


def test_the_provenance_check_catches_a_status_from_another_source_cell():
    value = np.array([[5, 6, 7], [8, 9, 10]], dtype=np.uint8)
    status = np.array([[wire.OK, wire.OFF_NETWORK, wire.OK],
                       [wire.OK, wire.OK, wire.NO_PATH]], dtype=np.uint8)
    transform, crs = _tiny_grid()
    bounds = _bounds_for(transform, value.shape, crs)
    pub = _reproject_all(transform, crs, bounds, value, status, None)
    shifted = np.roll(pub["status"], 1, axis=1)
    assert not np.array_equal(shifted, pub["status"]), "the control changed nothing"
    with pytest.raises(SystemExit, match="not the status of the source cell"):
        exporter.verify_provenance(
            "tiny", transform, crs, bounds, *value.shape,
            source={"value": value, "status": status},
            published={**pub, "status": shifted})


# ---------------------------------------------------------------------------------------------
# Pass 49 finding 3: the licence bundle, and the controls that show the gate can fail.


def _table(*licences):
    return {"licence": {"source": "Overture 2026-10-21.0"},
            "destinations": [{"ordinal": 0, "node_index": 1, "place_count": len(licences),
                              "places": [{"gers_id": f"x{i}", "name": f"N{i}", "brand": None,
                                          "category": "grocery", "operating_status": "open",
                                          "licence": lic}
                                         for i, lic in enumerate(licences)]}]}


def test_the_licence_bundle_carries_the_text_of_every_licence_it_ships(tmp_path):
    got = exporter.write_licence_bundle(
        tmp_path, [_table("CDLA-Permissive-2.0", "Apache-2.0", "CC0-1.0")],
        {"Overture 2026-10-21.0"})
    assert got["licences_present"] == ["Apache-2.0", "CC0-1.0", "CDLA-Permissive-2.0"]
    for name in ("Apache-2.0.txt", "CC0-1.0.txt", "CDLA-Permissive-2.0.txt"):
        text = (tmp_path / "LICENSES" / name).read_text(encoding="utf-8")
        assert len(text) > 500, f"{name} is too short to be a licence text"
    # Apache-2.0 4(d): the source NOTICE travels with the data.
    assert (tmp_path / "LICENSES" / "NOTICE-foursquare.txt").exists()
    # CDLA 2.1 is about the text of the agreement, so check the text really is the agreement.
    cdla = (tmp_path / "LICENSES" / "CDLA-Permissive-2.0.txt").read_text(encoding="utf-8")
    assert "makes available the text of this agreement with the shared Data" in cdla
    attribution = (tmp_path / "ATTRIBUTION.md").read_text(encoding="utf-8")
    assert "These records have been modified." in attribution, (
        "Apache-2.0 4(b) requires a statement that files were changed, and the date")
    assert "Overture 2026-10-21.0" in attribution
    assert "ODbL" in attribution and "OpenStreetMap contributors" in attribution


def test_a_licence_with_no_text_on_disk_is_refused(tmp_path):
    """**The positive control.** A gate that has never refused anything is decoration.

    This is also the shape of the real hazard: a future Overture release adds a source under a
    licence nobody has reviewed, and the names ship with a label and no text.
    """
    with pytest.raises(SystemExit, match="holds no text for them"):
        exporter.write_licence_bundle(tmp_path, [_table("ODbL-1.0")], {"r"})
    assert not (tmp_path / "ATTRIBUTION.md").exists(), (
        "the attribution was written for a bundle that was refused")


def test_an_apache_record_without_its_notice_is_refused(tmp_path, monkeypatch):
    """Apache-2.0 without the source NOTICE is not Apache-2.0 compliance."""
    import shutil
    bare = tmp_path / "licences-without-the-notice"
    bare.mkdir()
    shutil.copyfile(exporter.LICENCES / "Apache-2.0.txt", bare / "Apache-2.0.txt")
    monkeypatch.setattr(exporter, "LICENCES", bare)
    with pytest.raises(SystemExit, match="requires NOTICE-foursquare.txt"):
        exporter.write_licence_bundle(tmp_path / "out", [_table("Apache-2.0")], {"r"})


def test_the_shipped_bundle_carries_its_licence_texts():
    """And the artifact in the repository, not only the function."""
    if not (PUBLISHED / "manifest.json").exists():
        pytest.skip("no published bundle on disk")
    manifest = json.loads((PUBLISHED / "manifest.json").read_text(encoding="utf-8"))
    licensing = manifest.get("licensing")
    if not any("dest_table" in layer for layer in manifest["layers"]):
        assert licensing is None, (
            "a bundle with no third-party names must say nothing rather than say {}")
        return
    assert licensing, "the bundle ships place names and records no licensing"
    for rel in licensing["files"]:
        assert (PUBLISHED / rel).exists(), f"{rel} is recorded in the manifest and is not there"
    for lic in licensing["licences_present"]:
        assert (PUBLISHED / "LICENSES" / f"{lic}.txt").stat().st_size > 500
