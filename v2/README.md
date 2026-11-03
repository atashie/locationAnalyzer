# locfinder v2

Phase 0: experiments that choose the architecture. See `../docs/plans/2026-11-03-phase0-experiments.md`
and results in `../docs/experiments/`. Core contracts live in `locfinder/`; one-off spike scripts in `spikes/`.

Setup (Windows, from this directory):

    uv sync --extra dev --extra data
    uv run pytest

Heavy tooling runs in WSL2 Ubuntu (Docker, osmium). The repo is visible there at
`/mnt/c/Users/arikt/documents/github/distanceFinder`.

Large data lives under `data/` (gitignored). Results are committed under `../docs/experiments/`.
