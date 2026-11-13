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
    assert manifest["encoding"] == "published-v2"
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
