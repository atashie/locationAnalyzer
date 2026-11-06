"""Build the S3 **development** frame artifacts.

Run from `v2/`:  `python scripts/build_dev_frames.py`

Design §10 separates development from certification: these are the **development** frames, their
observations are never substituted for certification estimates, and the **certification draw happens
after the freeze** under §10's registration. They use *n* = 500 — the certification size — so the
timing measured on them is the timing certification will cost, and no new allocation is introduced.

**Why this file is tracked.** The build record claimed "both counts are asserted in the build script,
so a future re-acquisition that changes them fails loudly". Pass-19 F5 looked for that script and
found none: it lived in a scratch directory, so it protected one invocation on one afternoon and
nothing else. A one-off assertion outside the repository cannot protect another construction path.
The counts are now also enforced inside `build_frame_b` through `expect_population_n`, which is the
guard that actually travels with the code; this script passes them and is kept so the development
frames can be rebuilt and compared.
"""

from pathlib import Path

from locfinder.measure.frames import (
    build_frame_b,
    build_frame_c,
    file_digest,
    structure_population,
    write_frame,
)
from locfinder.metros import get_metro

DEV_SEED_B = 20261105_001          # declared development seeds, recorded in the manifests
DEV_SEED_C = 20261105_002
N = 500
OUT = Path("data/frames/development")
PARQUET = Path("data/triangle/overture_buildings_accepted.parquet")

#: Design §1, verified against the artifact and independently reproduced at pass 17.
EXPECT_ROWS = 522_160
EXPECT_POPULATION = 512_633


def main() -> None:
    grid = get_metro("triangle").grid(100.0)
    print(f"grid {grid.ncols} x {grid.nrows} = {grid.ncols * grid.nrows:,} cells, {grid.crs}")

    print("hashing the building source ...")
    source_digest = file_digest(PARQUET)
    print(f"  sha256 {source_digest}")

    print("projecting centroids and building the structure population ...")
    ids, pts, total = structure_population(PARQUET, grid)
    print(f"  rows {total:,}  ->  in-grid structure population {len(ids):,}")
    if total != EXPECT_ROWS:
        raise SystemExit(f"source has {total:,} rows, not design §1's {EXPECT_ROWS:,}")
    if len(ids) != EXPECT_POPULATION:
        raise SystemExit(f"population is {len(ids):,}, not design §1's {EXPECT_POPULATION:,}")
    print("  both match design §1")

    frames = (
        build_frame_b(PARQUET, grid, n=N, seed=DEV_SEED_B, population=(ids, pts),
                      source_digest=source_digest, expect_population_n=EXPECT_POPULATION),
        build_frame_c(grid, n=N, seed=DEV_SEED_C),
    )
    for f in frames:
        data, manifest = write_frame(f, OUT)
        print(f"\n{f.kind}: n={f.n}, population={f.population_n:,}, seed={f.seed}")
        print(f"  digest        {f.digest}")
        print(f"  source digest {f.source_digest}")
        print(f"  -> {data}")
        print(f"  -> {manifest}")
        print(f"  x range {f.points[:, 0].min():.1f} .. {f.points[:, 0].max():.1f}")
        print(f"  y range {f.points[:, 1].min():.1f} .. {f.points[:, 1].max():.1f}")


if __name__ == "__main__":
    main()
