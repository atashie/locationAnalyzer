"""Tests for the S3 sampling frames.

**The failure mode these are written against.** Two successive revisions of the frame-C test were
defeated:

* the first admitted points always placed at **cell centres** — reproducible, inside distinct
  sampled cells, satisfying every assertion (pass-16 F18);
* the replacement checked marginal means and spreads, which admits drawing **one** uniform number
  and using it for both offsets: over 100,000 draws both marginals have mean 49.9574 m and sd
  28.8447 m with **correlation 1**, every point on a diagonal (pass-18 F18).

So there are two independent guards, because each catches what the other can miss:

1. an **exact-sequence oracle** against the normatively specified draw, which a `(u, u)`
   implementation cannot match; and
2. a **joint** check — the correlation of the two offsets, which is 1 for the diagonal
   implementation and near 0 for the correct one — at a fixed seed and a declared tolerance.

Pass 18's caveat is taken: an oracle that merely replays the implementation's own calls "does not
independently establish joint uniformity". Guard 1 is therefore written against the draw as
*specified in the design*, and guard 2 tests the property directly.
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

from locfinder.grid import GridSpec
from locfinder.measure.frames import (
    BIT_GENERATOR,
    build_frame_b,
    build_frame_c,
    cell_bounds,
    cell_row_col,
    grid_digest,
    read_frame,
    write_frame,
)

# A toy grid small enough to enumerate: 4 cols x 3 rows of 10 m.
TOY = GridSpec(crs="EPSG:32617", x_min=1000.0, y_max=2000.0, cell_m=10.0, ncols=4, nrows=3)


# --------------------------------------------------------------------------- cell geometry


def test_the_flat_index_runs_downward_from_y_max():
    """The off-by-one this helper exists for: row 0 is the **top** row, at `y_max`."""
    row, col = cell_row_col(np.array([0, 3, 4, 11]), TOY)
    assert list(row) == [0, 0, 1, 2]
    assert list(col) == [0, 3, 0, 3]


def test_the_first_and_last_row_span_the_right_ground():
    first = cell_bounds(np.array([0]), TOY)[0]
    last = cell_bounds(np.array([11]), TOY)[0]
    y_min = TOY.y_max - TOY.nrows * TOY.cell_m
    assert tuple(first) == (1000.0, 1990.0, 1010.0, 2000.0)      # touches y_max
    assert tuple(last) == (1030.0, y_min, 1040.0, y_min + 10.0)  # touches y_min
    assert y_min == 1970.0


def test_every_toy_cell_has_distinct_bounds_covering_the_grid():
    b = cell_bounds(np.arange(12), TOY)
    assert len({tuple(r) for r in b}) == 12
    assert b[:, 0].min() == TOY.x_min
    assert b[:, 2].max() == TOY.x_min + TOY.ncols * TOY.cell_m
    assert b[:, 3].max() == TOY.y_max


def test_an_index_outside_the_grid_is_an_error():
    with pytest.raises(ValueError):
        cell_row_col(np.array([12]), TOY)
    with pytest.raises(ValueError):
        cell_row_col(np.array([-1]), TOY)


# --------------------------------------------------------------------------- frame C: the draw


def specified_draw(grid: GridSpec, n: int, seed: int):
    """The draw exactly as design §1 specifies it, written out here independently of the module.

    This is guard 1. It is deliberately a transcription of the *specification*, so that an
    implementation deviating from the spec fails even if it is internally self-consistent.
    """
    rng = np.random.Generator(BIT_GENERATOR(seed))
    cells = rng.permutation(grid.nrows * grid.ncols)[:n]
    offsets = rng.random((n, 2))
    return cells, offsets


def test_frame_c_matches_the_specified_draw_element_by_element():
    f = build_frame_c(TOY, n=7, seed=20261105)
    cells, offsets = specified_draw(TOY, 7, 20261105)
    assert list(f.source_ids) == list(cells)
    b = cell_bounds(cells, TOY)
    np.testing.assert_allclose(f.points[:, 0], b[:, 0] + offsets[:, 0] * TOY.cell_m, atol=1e-12)
    np.testing.assert_allclose(f.points[:, 1], b[:, 1] + offsets[:, 1] * TOY.cell_m, atol=1e-12)


def test_the_diagonal_implementation_is_rejected():
    """Guard 1 against pass-18 F18's counterexample, stated as code so the hole stays closed.

    The `(u, u)` implementation draws one uniform per point. It cannot reproduce the specified
    `random((n, 2))` sequence, so an exact oracle separates them — and the correlation check below
    separates them on the property itself.
    """
    grid = GridSpec(crs="EPSG:32617", x_min=0.0, y_max=1000.0, cell_m=100.0, ncols=10, nrows=10)
    n, seed = 80, 11

    def diagonal_build():
        """The rejected implementation: one uniform per point, used for both offsets."""
        rng = np.random.Generator(BIT_GENERATOR(seed))
        cells = rng.permutation(grid.nrows * grid.ncols)[:n]
        u = rng.random(n)
        b = cell_bounds(cells, grid)
        return cells, np.column_stack([b[:, 0] + u * grid.cell_m, b[:, 1] + u * grid.cell_m])

    correct = build_frame_c(grid, n=n, seed=seed)
    diag_cells, diag_points = diagonal_build()

    # it picks the same cells -- so a cells-only test would not separate them
    assert list(diag_cells) == list(correct.source_ids)
    # but the points differ, which guard 1's exact oracle detects
    assert not np.allclose(diag_points, correct.points)

    def offsets(points):
        b = cell_bounds(correct.source_ids, grid)
        return ((points[:, 0] - b[:, 0]) / grid.cell_m,
                (points[:, 1] - b[:, 1]) / grid.cell_m)

    dfx, dfy = offsets(diag_points)
    cfx, cfy = offsets(correct.points)
    assert np.corrcoef(dfx, dfy)[0, 1] == pytest.approx(1.0)      # every point on a diagonal
    assert abs(np.corrcoef(cfx, cfy)[0, 1]) < 0.3                 # and the correct draw is not


def test_the_two_within_cell_offsets_are_jointly_independent():
    """Guard 2: the property itself, on a grid large enough to measure it. A fixed seed and a
    declared tolerance, so this is deterministic rather than flaky."""
    grid = GridSpec(crs="EPSG:32617", x_min=0.0, y_max=10_000.0, cell_m=100.0,
                    ncols=100, nrows=100)
    f = build_frame_c(grid, n=5000, seed=4242)
    b = cell_bounds(f.source_ids, grid)
    fx = (f.points[:, 0] - b[:, 0]) / grid.cell_m
    fy = (f.points[:, 1] - b[:, 1]) / grid.cell_m
    assert abs(np.corrcoef(fx, fy)[0, 1]) < 0.05          # 1.0 for the diagonal implementation
    # and the joint distribution covers the cell, which marginals alone cannot show:
    quadrant_counts = np.array([
        np.sum((fx < 0.5) & (fy < 0.5)), np.sum((fx >= 0.5) & (fy < 0.5)),
        np.sum((fx < 0.5) & (fy >= 0.5)), np.sum((fx >= 0.5) & (fy >= 0.5)),
    ])
    assert quadrant_counts.min() > 1000                   # diagonal gives ~0 in two quadrants
    assert fx.min() < 0.02 and fx.max() > 0.98
    assert fy.min() < 0.02 and fy.max() > 0.98


def test_every_frame_c_point_lies_inside_the_cell_its_index_names():
    grid = GridSpec(crs="EPSG:32617", x_min=661900.0, y_max=4003500.0, cell_m=100.0,
                    ncols=643, nrows=514)
    f = build_frame_c(grid, n=2000, seed=99)
    b = cell_bounds(f.source_ids, grid)
    assert np.all(f.points[:, 0] >= b[:, 0]) and np.all(f.points[:, 0] < b[:, 2])
    assert np.all(f.points[:, 1] >= b[:, 1]) and np.all(f.points[:, 1] < b[:, 3])


def test_frame_c_samples_cells_without_replacement_and_can_reach_every_cell():
    """Enumerated-frame inclusion on the toy grid: a full-size draw is a permutation, so no cell is
    unreachable and none is drawn twice."""
    f = build_frame_c(TOY, n=12, seed=5)
    assert sorted(f.source_ids) == list(range(12))
    seen = set()
    for seed in range(40):
        seen.update(build_frame_c(TOY, n=1, seed=seed).source_ids.tolist())
    assert len(seen) >= 10          # 40 single draws reach almost every one of 12 cells


def test_frame_c_is_reproducible_and_seed_sensitive():
    a = build_frame_c(TOY, n=6, seed=1)
    b = build_frame_c(TOY, n=6, seed=1)
    c = build_frame_c(TOY, n=6, seed=2)
    np.testing.assert_array_equal(a.points, b.points)     # bit-for-bit
    assert a.digest == b.digest
    assert a.digest != c.digest


def test_the_digest_changes_when_any_point_changes():
    from locfinder.measure.frames import Frame, frame_digest
    f = build_frame_c(TOY, n=6, seed=1)
    moved = np.array(f.points, copy=True)
    moved[3, 0] += 1e-9
    assert frame_digest(kind=f.kind, points=moved, source_ids=f.source_ids, seed=f.seed,
                        population_n=f.population_n, crs=f.crs,
                        source_digest=f.source_digest) != f.digest
    assert Frame(kind=f.kind, points=f.points, source_ids=f.source_ids, seed=f.seed,
                 population_n=f.population_n, crs=f.crs, source_digest=f.source_digest,
                 digest=f.digest).digest == f.digest


def test_a_frames_points_cannot_be_mutated_out_from_under_its_digest():
    """Pass-19 F7, executed. `frozen=True` prevents rebinding an attribute, not mutating the array
    it points at: the review moved a point 999 m, left `digest` unchanged, and `write_frame` would
    have serialised the moved points under the old identity. A 999 m move can cross a product
    boundary, so an agreement could silently become the second false inclusion of *n* = 500 — a
    PASS turning INCONCLUSIVE **under the same recorded frame identity**.
    """
    f = build_frame_c(TOY, n=6, seed=1)
    with pytest.raises(ValueError):
        f.points[0, 0] = 1000.0
    with pytest.raises(ValueError):
        f.source_ids[0] = 999
    assert f.digest == f.recomputed_digest


def test_a_frame_whose_digest_does_not_describe_it_cannot_be_constructed():
    from locfinder.measure.frames import Frame
    f = build_frame_c(TOY, n=6, seed=1)
    moved = np.array(f.points, copy=True)
    moved[0, 0] += 999.0
    with pytest.raises(ValueError, match="does not describe"):
        Frame(kind=f.kind, points=moved, source_ids=f.source_ids, seed=f.seed,
              population_n=f.population_n, crs=f.crs, source_digest=f.source_digest,
              digest=f.digest)


def test_the_digest_separates_two_frames_that_differ_only_in_crs_or_kind():
    """Pass-19 F7: the first digest omitted `kind` and `crs`, so two frames with identical arrays,
    seed, population size and source digest but `EPSG:32617` against `EPSG:4326` described different
    places on Earth and shared one identity. The public constructor accepts those fields
    independently, so they belong in the identity."""
    from locfinder.measure.frames import frame_digest
    f = build_frame_c(TOY, n=6, seed=1)
    common = dict(points=f.points, source_ids=f.source_ids, seed=f.seed,
                  population_n=f.population_n, source_digest=f.source_digest)
    assert (frame_digest(kind="area", crs="EPSG:32617", **common)
            != frame_digest(kind="area", crs="EPSG:4326", **common))
    assert (frame_digest(kind="area", crs="EPSG:32617", **common)
            != frame_digest(kind="structures", crs="EPSG:32617", **common))


def test_the_digest_is_byte_canonical_and_cannot_run_two_ids_together():
    """Pass-19 F10. Float bytes are written little-endian explicitly, so numerically identical
    points keep one identity across architectures; and ids are length-delimited UTF-8, so
    `("ab", "c")` and `("a", "bc")` cannot collide the way fixed-width native `U64` allowed."""
    from locfinder.measure.frames import frame_digest
    pts = np.array([[1.0, 2.0], [3.0, 4.0]])
    common = dict(points=pts, seed=1, population_n=9, crs="EPSG:32617", kind="structures",
                  source_digest="x")
    assert (frame_digest(source_ids=np.array(["ab", "c"]), **common)
            != frame_digest(source_ids=np.array(["a", "bc"]), **common))

    # and the float layout is the declared one, not whatever this machine happens to use
    assert np.ascontiguousarray(np.array([1.0]), dtype="<f8").tobytes().hex() == \
        "000000000000f03f"


def test_an_oversized_or_empty_draw_is_an_error():
    with pytest.raises(ValueError):
        build_frame_c(TOY, n=13, seed=1)
    with pytest.raises(ValueError):
        build_frame_c(TOY, n=0, seed=1)


def test_the_grid_digest_distinguishes_the_two_candidate_grids():
    """Frame C's population *is* the grid, so its identity must separate the 100 m and 200 m grids —
    which are not nested, and are the whole reason frame C samples ground rather than centres."""
    g100 = GridSpec(crs="EPSG:32617", x_min=661900.0, y_max=4003500.0, cell_m=100.0,
                    ncols=643, nrows=514)
    g200 = GridSpec(crs="EPSG:32617", x_min=661800.0, y_max=4003600.0, cell_m=200.0,
                    ncols=322, nrows=258)
    assert grid_digest(g100) != grid_digest(g200)


# --------------------------------------------------------------------------- frame B


def _fake_population(n: int):
    ids = np.array([f"ovt:{i:06d}" for i in range(n)])
    pts = np.column_stack([np.linspace(1000.0, 1040.0, n), np.linspace(1970.0, 2000.0, n)])
    return ids, pts


def test_frame_b_draws_without_replacement_from_the_supplied_population():
    ids, pts = _fake_population(50)
    f = build_frame_b(None, TOY, n=10, seed=7, population=(ids, pts), source_digest="deadbeef")
    assert f.n == 10
    assert len(set(f.source_ids)) == 10               # no repeats
    assert set(f.source_ids) <= set(ids)
    assert f.population_n == 50
    assert f.kind == "structures"
    assert f.source_digest == "deadbeef"


def test_frame_b_matches_the_specified_permutation_draw():
    ids, pts = _fake_population(50)
    f = build_frame_b(None, TOY, n=10, seed=7, population=(ids, pts), source_digest="x")
    rng = np.random.Generator(BIT_GENERATOR(7))
    idx = rng.permutation(50)[:10]
    assert list(f.source_ids) == list(ids[idx])
    np.testing.assert_array_equal(f.points, pts[idx])


def test_frame_b_does_not_select_a_fixed_subset_across_seeds():
    """Rejects an implementation that always returns the same units — e.g. a head slice. Different
    seeds must select substantially different ids, and over many seeds the selection must reach
    well beyond any fixed half of the frame."""
    ids, pts = _fake_population(50)
    a = set(build_frame_b(None, TOY, n=10, seed=1, population=(ids, pts), source_digest="x")
            .source_ids)
    b = set(build_frame_b(None, TOY, n=10, seed=2, population=(ids, pts), source_digest="x")
            .source_ids)
    assert len(a & b) < 8
    reached = set()
    for seed in range(30):
        reached.update(build_frame_b(None, TOY, n=10, seed=seed, population=(ids, pts),
                                     source_digest="x").source_ids)
    assert len(reached) == 50          # every unit of the enumerated frame is reachable


def test_frame_b_rejects_an_oversized_draw():
    ids, pts = _fake_population(20)
    with pytest.raises(ValueError):
        build_frame_b(None, TOY, n=21, seed=1, population=(ids, pts), source_digest="x")


# --------------------------------------------------------------------------- persistence


def test_a_frame_artifact_is_never_overwritten(tmp_path):
    """Design §1: a new sample is a new digest, so writing over an existing frame is a mistake, not
    an update."""
    f = build_frame_c(TOY, n=6, seed=1)
    data, manifest = write_frame(f, tmp_path)
    assert data.exists() and manifest.exists()
    assert f.digest[:8] in data.name
    with pytest.raises(FileExistsError):
        write_frame(f, tmp_path)


def test_a_written_frame_reads_back_identically(tmp_path):
    """The round trip has to survive the id dtype. Frame C's source ids are integers and frame B's
    are Overture strings; the parquet stores both as text, and `frame_digest` keys on `str(id)`, so
    a frame that could not reproduce its digest through this would have a second identity."""
    for frame in (build_frame_c(TOY, n=6, seed=1),
                  build_frame_b(None, TOY, n=5, seed=2,
                                population=_fake_population(20), source_digest="x")):
        _, manifest = write_frame(frame, tmp_path / frame.kind)
        back = read_frame(manifest)
        assert back.digest == frame.digest
        assert back.kind == frame.kind and back.crs == frame.crs
        assert back.seed == frame.seed and back.population_n == frame.population_n
        assert np.array_equal(back.points, frame.points)
        assert [str(s) for s in back.source_ids] == [str(s) for s in frame.source_ids]


def test_reading_a_frame_whose_points_were_edited_on_disk_fails(tmp_path):
    """`Frame.__post_init__` recomputes the digest, so the read **is** the verification. Design §12:
    the identity a measurement reports has to be checked against the data it actually used, and a
    reader that trusts the manifest provides a way for an edited artifact to keep its name."""
    import pandas as pd

    frame = build_frame_c(TOY, n=6, seed=1)
    data, manifest = write_frame(frame, tmp_path)
    table = pd.read_parquet(data)
    table.loc[0, "x"] = float(table.loc[0, "x"]) + 999.0
    table.to_parquet(data, index=False)
    with pytest.raises(ValueError):
        read_frame(manifest)


def test_reading_a_frame_of_another_digest_version_fails(tmp_path):
    import json

    frame = build_frame_c(TOY, n=6, seed=1)
    _, manifest = write_frame(frame, tmp_path)
    body = json.loads(manifest.read_text(encoding="utf-8"))
    body["digest_version"] = 1
    manifest.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(ValueError):
        read_frame(manifest)


def test_the_frozen_development_frames_still_match_their_digests():
    """The two frames T0 consumes, verified against the artifacts on disk rather than recalled.
    Skipped where `v2/data/` is absent, which is every fresh clone -- nothing under it is tracked."""
    directory = pathlib.Path(__file__).resolve().parents[1] / "data" / "frames" / "development"
    manifests = sorted(directory.glob("frame_*.json")) if directory.exists() else []
    if not manifests:
        pytest.skip("no frozen frames on this machine; v2/data/ is not tracked")
    seen = {}
    for manifest in manifests:
        frame = read_frame(manifest)      # raises unless the contents match the digest
        seen[frame.kind] = (frame.digest[:8], frame.n)
    assert seen.get("structures") == ("51a59463", 500)
    assert seen.get("area") == ("7914e80a", 500)


def test_the_manifest_records_what_is_needed_to_redraw_the_frame(tmp_path):
    import json
    f = build_frame_c(TOY, n=6, seed=123)
    _, manifest = write_frame(f, tmp_path)
    m = json.loads(manifest.read_text(encoding="utf-8"))
    assert m["seed"] == 123
    assert m["population_n"] == 12
    assert m["digest"] == f.digest
    assert m["crs"] == "EPSG:32617"
    assert "permutation" in m["sampling"] and "random((n, 2))" in m["sampling"]


# --------------------------------------------------------------------------- population construction
#
# Pass-19 F4: every frame-B draw test above supplies an already ordered synthetic population, so
# none of them calls `structure_population`. Projection, centroid computation, boundary filtering
# and population ordering could all be broken without a single assertion noticing — the review
# executed the mutation `order = np.arange(len(ids))` in place of the stable argsort and **all 17
# tests passed**. These tests close that.

#: The real grid's origin, cut down to 4 x 3 cells so the population is enumerable.
REAL = GridSpec(crs="EPSG:32617", x_min=661900.0, y_max=4003500.0, cell_m=100.0, ncols=4, nrows=3)
REAL_X_MAX = REAL.x_min + REAL.ncols * REAL.cell_m          # 662300
REAL_Y_MIN = REAL.y_max - REAL.nrows * REAL.cell_m          # 4003200


def _squares(ids, xy, crs="EPSG:32617"):
    """A GeoDataFrame of 2 m squares centred on `xy`, in `crs`. Polygons, not points, so the
    centroid computation is actually exercised."""
    import geopandas as gpd
    from shapely.geometry import box
    geoms = [box(x - 1, y - 1, x + 1, y + 1) for x, y in xy]
    return gpd.GeoDataFrame({"id": list(ids)}, geometry=geoms, crs=crs)


def test_the_population_filter_is_half_open_on_all_four_sides(tmp_path):
    """`[x_min, x_max) x [y_min, y_max)`. A centroid exactly on the west or south edge is **in**;
    exactly on the east or north edge is **out**. Built directly in the grid's CRS so the
    comparisons are exact rather than projection-rounded."""
    from locfinder.measure.frames import structure_population
    cases = {
        "inside":      (661950.0, 4003450.0),
        "on-x-min":    (REAL.x_min, 4003450.0),
        "on-y-min":    (661950.0, REAL_Y_MIN),
        "on-x-max":    (REAL_X_MAX, 4003450.0),
        "on-y-max":    (661950.0, REAL.y_max),
        "west-of":     (REAL.x_min - 0.5, 4003450.0),
        "north-of":    (661950.0, REAL.y_max + 0.5),
    }
    path = tmp_path / "squares.parquet"
    _squares(cases.keys(), cases.values()).to_parquet(path)

    ids, pts, total = structure_population(path, REAL)
    assert total == len(cases)
    assert set(ids) == {"inside", "on-x-min", "on-y-min"}, (
        "half-open on all four sides: west and south edges are in, east and north are out"
    )
    assert len(pts) == 3


def test_the_population_projects_before_taking_centroids(tmp_path):
    """Design §1: "Centroids are computed **projected** (EPSG:32617), never geographically."

    The source is written in EPSG:4326, so `structure_population` must reproject it. A geographic
    centroid would be a degree pair near (-78.9, 36.2) and fall outside every UTM-metre bound,
    giving an empty population rather than a wrong one — which is why this test checks the
    recovered coordinates, not merely the count.
    """
    from locfinder.measure.frames import structure_population
    targets = [(661950.0, 4003450.0), (662150.0, 4003250.0)]
    path = tmp_path / "wgs84.parquet"
    _squares(["a", "b"], targets).to_crs("EPSG:4326").to_parquet(path)

    ids, pts, total = structure_population(path, REAL)
    assert total == 2
    assert list(ids) == ["a", "b"]
    assert pts == pytest.approx(np.array(targets), abs=1e-3)


def test_the_population_order_is_the_id_order_not_the_file_order(tmp_path):
    """Pass-19 F4's counterexample, and S2.5's lesson in a form that can fail.

    Two units written as `[b, a]`. PCG64 seed 7 gives `permutation(2) = [0, 1]`, so at *n* = 1 the
    correct id-sorted population selects **a** and a file-ordered one selects **b** — the same seed
    choosing a different structure. At *n* = 500, replacing one agreement in an otherwise one-error
    sample moves the 1% construction verdict from PASS to INCONCLUSIVE.
    """
    from locfinder.measure.frames import structure_population
    descending = tmp_path / "descending.parquet"
    ascending = tmp_path / "ascending.parquet"
    _squares(["b", "a"], [(661901.0, 4003491.0), (661902.0, 4003492.0)]).to_parquet(descending)
    _squares(["a", "b"], [(661902.0, 4003492.0), (661901.0, 4003491.0)]).to_parquet(ascending)

    for path in (descending, ascending):
        ids, pts, _ = structure_population(path, REAL)
        assert list(ids) == ["a", "b"], "sorted by id, whatever order the file held"
        assert pts[0] == pytest.approx([661902.0, 4003492.0])

    assert list(np.random.Generator(BIT_GENERATOR(7)).permutation(2)) == [0, 1]

    picks = set()
    for path in (descending, ascending):
        ids, pts, _ = structure_population(path, REAL)
        f = build_frame_b(None, REAL, n=1, seed=7, population=(ids, pts), source_digest="same")
        picks.add((str(f.source_ids[0]), f.digest))
    assert len(picks) == 1, f"the file order changed the sample: {picks}"
    assert next(iter(picks))[0] == "a"


def test_deleting_the_population_sort_is_now_caught():
    """The mutation that survived 17 tests, built here so the guard is visible rather than implied.

    It is not caught by any assertion about the *draw*, because the draw is identical. It is caught
    by asserting that the population handed to the draw is in id order.
    """
    from locfinder.measure.frames import validate_population
    ids = np.array(["b", "a"])
    pts = np.array([[661901.0, 4003491.0], [661902.0, 4003492.0]])

    def unsorted_population(ids, pts):
        order = np.arange(len(ids))                 # the mutation
        return ids[order], pts[order]

    assert list(validate_population(ids, pts)[0]) == ["a", "b"]
    assert list(unsorted_population(ids, pts)[0]) == ["b", "a"]

    first = np.random.Generator(BIT_GENERATOR(7)).permutation(2)[0]
    assert str(validate_population(ids, pts)[0][first]) == "a"
    assert str(unsorted_population(ids, pts)[0][first]) == "b"


def test_the_builder_sorts_a_supplied_population_itself():
    """Pass-19 F5: the cached path accepted the caller's order, so the module's claim that "frame
    B's population is sorted by Overture id before any draw" held only on the uncached path.

    The builder now orders what it is given, so both paths agree. Executed consequence of the old
    behaviour: the same grid, seed and source digest returned **different frame digests** depending
    on which way round the caller passed two units.
    """
    ids = np.array(["b", "a"])
    pts = np.array([[661901.0, 4003491.0], [661902.0, 4003492.0]])
    one = build_frame_b(None, REAL, n=1, seed=7, population=(ids, pts), source_digest="same")
    two = build_frame_b(None, REAL, n=1, seed=7, population=(ids[::-1], pts[::-1]),
                        source_digest="same")
    assert one.digest == two.digest
    assert str(one.source_ids[0]) == str(two.source_ids[0]) == "a"


def test_a_population_that_cannot_be_one_is_rejected():
    from locfinder.measure.frames import validate_population
    pts = np.array([[1.0, 2.0], [3.0, 4.0]])
    with pytest.raises(ValueError, match="duplicate"):
        validate_population(np.array(["a", "a"]), pts)
    with pytest.raises(ValueError, match="shapes do not match"):
        validate_population(np.array(["a", "b", "c"]), pts)
    with pytest.raises(ValueError, match="finite"):
        validate_population(np.array(["a", "b"]), np.array([[1.0, 2.0], [np.nan, 4.0]]))
    with pytest.raises(ValueError, match="empty"):
        validate_population(np.array([]), np.zeros((0, 2)))


def test_the_builder_refuses_a_population_that_is_not_the_frozen_one():
    """Pass-19 F5: "a 500-unit cached subset can similarly be sampled exhaustively and labelled as
    the supplied source while omitting 512,133 eligible structures." The guard belongs at the
    builder boundary, because a one-off assertion in a build script cannot protect another call."""
    ids = np.array([f"s{i:03d}" for i in range(20)])
    pts = np.column_stack([np.linspace(661901, 662299, 20), np.full(20, 4003450.0)])
    ok = build_frame_b(None, REAL, n=5, seed=1, population=(ids, pts), source_digest="x",
                       expect_population_n=20)
    assert ok.population_n == 20
    with pytest.raises(ValueError, match="not the expected"):
        build_frame_b(None, REAL, n=5, seed=1, population=(ids, pts), source_digest="x",
                      expect_population_n=512_633)
