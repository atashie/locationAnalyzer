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
    from locfinder.measure.frames import Frame, _digest_points
    f = build_frame_c(TOY, n=6, seed=1)
    moved = f.points.copy()
    moved[3, 0] += 1e-9
    assert _digest_points(moved, f.source_ids, f.seed, f.population_n,
                          f.source_digest) != f.digest
    assert Frame(kind=f.kind, points=f.points, source_ids=f.source_ids, seed=f.seed,
                 population_n=f.population_n, crs=f.crs, source_digest=f.source_digest,
                 digest=f.digest).digest == f.digest


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
