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
    # Establish that the unmodified input PASSES first, so the refusal below is attributable to
    # the exchange and not to the fixture -- pass 50's note on these controls.
    exporter.verify_provenance("tiny", transform, crs, bounds, *value.shape,
                               source={"value": value, "status": status, "destination": dest},
                               published=pub)
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
    exporter.verify_provenance("tiny", transform, crs, bounds, *value.shape,
                               source={"value": value, "status": status}, published=pub)
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
        "Apache-2.0 4(b) requires modified files to carry a notice that they were changed. It "
        "does NOT require a date -- pass 50 finding B2 corrected that invention -- and this file "
        "alone does not discharge 4(b) either, which ATTRIBUTION.md now says.")
    assert "not cleared for redistribution" in attribution.lower(), (
        "the attribution implies Apache 4 compliance the build has not established")
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


def test_every_json_artifact_is_strict_json():
    """**The generalisation of pass 49's release blocker.**

    `json.dumps` writes `NaN`, `Infinity` and `-Infinity` for non-finite floats, and Python's own
    `json.loads` accepts them, so a Python-to-Python round trip never notices. No other consumer
    accepts them: `JSON.parse` throws, which is how the published destination table killed the
    page while every one of 1,431 tests passed.

    So this parses every JSON artifact in the repository the way a browser would, with the
    extension constants refused. It is cheap and it covers artifacts nothing else looks at --
    the class of defect, not the one instance of it.
    """
    def reject(constant):
        raise ValueError(f"not JSON: the bare token {constant}")

    repo = pathlib.Path(__file__).resolve().parents[2]
    # Pass 50 finding G4: the roots were hand-listed and missed `spikes/g3-render/versions.json`,
    # which the page parses before it can finish booting -- so the claim to cover "every JSON
    # artifact a non-Python consumer loads" was false for the one artifact loaded first. The
    # spike directory is now scanned whole rather than one subdirectory of it, because listing
    # the places to look is the step that goes stale.
    roots = [repo / "docs" / "experiments", repo / "docs" / "research",
             repo / "v2" / "spikes"]
    checked, bad = 0, []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            checked += 1
            try:
                json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)
            except Exception as err:                       # noqa: BLE001 - report, do not hide
                bad.append(f"{path.relative_to(repo)}: {type(err).__name__} {err}")
    # A floor, not just "more than zero": a glob pointed at the wrong place, or a renamed
    # directory, would otherwise leave this test passing while checking almost nothing. There
    # were 43 when it was written.
    assert checked >= 20, (
        f"only {checked} JSON artifacts were found under {[str(r) for r in roots]}; this test "
        "is looking in the wrong place and is passing vacuously")
    assert not bad, (
        "these artifacts are not JSON and no browser will load them:\n  " + "\n  ".join(bad))


def test_the_strict_json_check_rejects_what_python_tolerates(tmp_path):
    """**The positive control.** The check above only means something if it can fail.

    `json.loads` accepts `NaN` by default, which is exactly why the blocker survived 1,431 tests.
    This shows that the `parse_constant` refusal is the whole difference, on a file holding the
    same token the published table held.
    """
    doc = tmp_path / "a.json"
    doc.write_text('{"operating_status": NaN}', encoding="utf-8")

    # The default parser accepts it and hands back a float NaN.
    tolerated = json.loads(doc.read_text(encoding="utf-8"))["operating_status"]
    assert tolerated != tolerated, "the default parser did not return a NaN"

    # The parser the check above uses refuses it.
    def reject(constant):
        raise ValueError(constant)
    with pytest.raises(ValueError, match="NaN"):
        json.loads(doc.read_text(encoding="utf-8"), parse_constant=reject)


def test_the_provenance_check_works_where_several_source_cells_feed_one_published_cell():
    """**The case the check exists for, which the controls above do not cover.**

    Every other provenance test here -- and the real export -- is a one-to-one retiling, where a
    published cell has exactly one candidate source cell and planes cannot disagree about which
    one fed it. A check that only ever runs on a one-to-one mapping has not been exercised. So
    this one publishes a 4x4 source onto a 2x2 grid, four candidates per published cell, and then
    mixes a single plane.

    It also settles a hazard I suspected and was wrong about. Every data plane passes its own
    fill as `src_nodata`, and those are in-band values -- the route flag's is `ROUTE_CLEAR`, which
    is 0 and is the common legitimate value. If `src_nodata` excluded those source cells from
    SELECTION, the index plane (whose sentinel cannot occur) and the flag plane would pick
    different source cells and this check would compare the wrong pair. Measured: it does not.
    `Resampling.nearest` picks the same cell either way, and the assertions below hold it to that.
    """
    import rasterio.warp
    from rasterio.transform import array_bounds, from_origin

    crs = "EPSG:32617"
    transform = from_origin(661800.0, 4003600.0, 100.0, 100.0)
    src_shape = (4, 4)
    west, south, east, north = array_bounds(*src_shape, transform)
    bounds = rasterio.warp.transform_bounds(crs, "EPSG:4326", west, south, east, north)
    nrows, ncols = 2, 2                       # four source cells per published cell

    value = np.arange(16, dtype=np.uint8).reshape(src_shape) + 1
    status = np.full(src_shape, wire.OK, dtype=np.uint8)
    dest = np.arange(16, dtype=wire.DEST_DTYPE).reshape(src_shape)
    # ROUTE_CLEAR is 0 and is passed as src_nodata by the exporter: a checkerboard puts eight
    # legitimate zeros in the source, so if src_nodata excluded them the published plane would be
    # all ones.
    flag = (np.indices(src_shape).sum(axis=0) % 2).astype(np.uint8)

    def warp(plane, fill, dtype=np.uint8):
        return exporter.reproject_plane(plane, transform, crs, src_fill=fill, dst_fill=fill,
                                        bounds=bounds, nrows=nrows, ncols=ncols, dtype=dtype)

    pub = {"value": warp(value, wire.VALUE_NONE), "status": warp(status, wire.OUTSIDE),
           "destination": warp(dest, wire.DEST_NONE, wire.DEST_DTYPE),
           "flag": warp(flag, wire.ROUTE_CLEAR)}
    src = {"value": value, "status": status, "destination": dest, "flag": flag}

    # The flag plane did not lose its legitimate zeros to src_nodata.
    assert 0 < int((pub["flag"] == wire.ROUTE_CLEAR).sum()) < pub["flag"].size, (
        "the published flag plane is all one value, so src_nodata=ROUTE_CLEAR excluded the clear "
        "source cells from selection and this check is comparing the wrong pair")

    got = exporter.verify_provenance("coarse", transform, crs, bounds, nrows, ncols,
                                     source=src, published=pub)
    assert got["cells_traced_to_a_source_cell"] == nrows * ncols
    assert got["cells_no_source_covers"] == 0

    # Now the control: one published cell takes a destination that belongs to a DIFFERENT source
    # cell -- a real one, in range, and in a mapping where four source cells were candidates.
    mixed = pub["destination"].copy()
    other = [int(v) for v in np.unique(dest) if v != mixed[0, 0]][0]
    mixed[0, 0] = other
    assert not np.array_equal(mixed, pub["destination"]), "the control changed nothing"
    with pytest.raises(SystemExit, match="not the destination of the source cell"):
        exporter.verify_provenance("coarse", transform, crs, bounds, nrows, ncols,
                                   source=src, published={**pub, "destination": mixed})

    # And on the flag plane, whose src_nodata is the in-band ROUTE_CLEAR.
    flipped = pub["flag"].copy()
    flipped[1, 1] ^= 1
    with pytest.raises(SystemExit, match="not the flag of the source cell"):
        exporter.verify_provenance("coarse", transform, crs, bounds, nrows, ncols,
                                   source=src, published={**pub, "flag": flipped})


# ---------------------------------------------------------------------------------------------
# Pass 50 finding B1: the allowlist checked two levels out of four. These are the three entrances
# it did not guard, each one a way to publish a field decision 17 forbids.


def _publishable_table():
    return {
        "what_this_is": "a table", "built": "now", "mode": "walk", "category": "grocery",
        "licence": {"this_table": ["CC0-1.0"], "source": "Overture test",
                    "why_it_is_a_separate_artifact": "because", "redistribution": "see LICENSES",
                    "fields_deliberately_omitted": ["phones"]},
        "node_is_not_a_shop": "a node is not a shop",
        "destinations": [{"ordinal": 0, "node_index": 11, "place_count": 1,
                          "places": [{"gers_id": "g1", "name": "N", "brand": None,
                                      "category": "grocery", "operating_status": "open",
                                      "licence": "CC0-1.0"}]}],
    }


def test_a_publishable_table_passes_the_allowlist(tmp_path):
    """The baseline. Without this the refusals below could be refusing everything."""
    exporter.check_table_is_publishable(_publishable_table(), tmp_path / "t.json")


def test_a_forbidden_field_at_the_table_root_is_refused(tmp_path):
    t = _publishable_table()
    t["phones"] = ["+1-919-555-0100"]
    with pytest.raises(SystemExit, match=r"the table root carries \['phones'\]"):
        exporter.check_table_is_publishable(t, tmp_path / "t.json")


def test_a_forbidden_field_inside_the_licence_block_is_refused(tmp_path):
    t = _publishable_table()
    t["licence"]["upstream_provider_id"] = "forbidden-provider-id"
    with pytest.raises(SystemExit, match="the root licence block carries"):
        exporter.check_table_is_publishable(t, tmp_path / "t.json")


def test_an_object_inside_a_permitted_place_field_is_refused(tmp_path):
    """A reviewed field holding an unreviewed object is an unreviewed field with a reviewed name.

    This is how a website ships: `brand` is allowed, so `brand = {"website": ...}` passed.
    """
    t = _publishable_table()
    t["destinations"][0]["places"][0]["brand"] = {"website": "https://example.invalid/"}
    with pytest.raises(SystemExit, match="only scalars are published here"):
        exporter.check_table_is_publishable(t, tmp_path / "t.json")


def test_a_place_record_with_no_gers_id_is_refused(tmp_path):
    t = _publishable_table()
    t["destinations"][0]["places"][0]["gers_id"] = ""
    with pytest.raises(SystemExit, match="no GERS id"):
        exporter.check_table_is_publishable(t, tmp_path / "t.json")


def test_an_entry_with_no_places_is_refused(tmp_path):
    """Pass 50 finding C2's stub table, refused at the exporter as well as in the harness."""
    t = _publishable_table()
    t["destinations"][0]["places"] = []
    t["destinations"][0]["place_count"] = 0
    with pytest.raises(SystemExit, match="carries no places"):
        exporter.check_table_is_publishable(t, tmp_path / "t.json")


def test_a_count_that_disagrees_with_its_set_is_refused(tmp_path):
    t = _publishable_table()
    t["destinations"][0]["place_count"] = 3
    with pytest.raises(SystemExit, match="declares 3 places and carries 1"):
        exporter.check_table_is_publishable(t, tmp_path / "t.json")


def test_an_empty_required_notice_is_refused(tmp_path):
    """Pass 50 finding B2: the gate checked that the pathname existed, so an empty file passed.

    A notice requirement discharged by an empty file is not discharged.
    """
    import shutil
    bare = tmp_path / "licences"
    bare.mkdir()
    shutil.copyfile(exporter.LICENCES / "Apache-2.0.txt", bare / "Apache-2.0.txt")
    (bare / "NOTICE-foursquare.txt").write_text("", encoding="utf-8")
    t = _publishable_table()
    t["destinations"][0]["places"][0]["licence"] = "Apache-2.0"
    import unittest.mock
    with unittest.mock.patch.object(exporter, "LICENCES", bare):
        with pytest.raises(SystemExit, match="requires NOTICE-foursquare.txt to carry"):
            exporter.write_licence_bundle(tmp_path / "out", [t], {"r"})
    assert not (tmp_path / "out" / "ATTRIBUTION.md").exists(), (
        "the attribution was written for a bundle that was refused")


def test_the_licence_record_does_not_claim_apache_clearance(tmp_path):
    got = exporter.write_licence_bundle(
        tmp_path, [_publishable_table()], {"Overture test"})
    assert got["apache_records_are_cleared_for_redistribution"] is False
    assert "4(c)" in got["what_this_does_not_establish"]
    assert "4(d)" in got["what_this_does_not_establish"]
