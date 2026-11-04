"""Acquiring an Overture theme safely. Phase 1, shared by `scripts/fetch_places.py` and
`scripts/fetch_buildings.py`.

Two hazards live here, both named in the plan's S4.1 and one of them demonstrated by Codex pass-10
H5. Keeping them in one tested function means neither script can reintroduce them.

**A raw file must not be reused for a request it does not answer.** `fetch_places.py` originally
returned any existing `overture_places_raw.parquet` regardless of the release *or the bounding box*
asked for, after which `partition_by_licence` labelled it with the **requested** release. That is
how an evaluation-extent download came to back a resolver that claims a routing-extent bound. A
state file records exactly what was fetched, and a mismatch forces a re-download.

**An interrupted download must not inherit the previous label.** Writing straight over the raw file
while its state file stayed valid meant a failed or cancelled download left the *new* bytes on disk
still described by the *old* state — and the next request for that old release reused them. So the
download goes to a temporary file, the state is removed, the bytes are moved into place, and only
then is the new state written. A failure at any point leaves the previous pair intact or no state at
all, never a lie.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

STATE_SUFFIX = ".state"


def state_path(raw: Path) -> Path:
    return raw.with_suffix(raw.suffix + STATE_SUFFIX)


@dataclass(frozen=True)
class Acquisition:
    """What a raw file is, so a later run can tell whether it answers the question being asked."""

    overture_type: str
    release: str
    bbox: str

    def as_dict(self) -> dict:
        return {"type": self.overture_type, "release": self.release, "bbox": self.bbox}


def describes(state: dict | None, want: Acquisition) -> bool:
    if not state:
        return False
    return {k: state.get(k) for k in want.as_dict()} == want.as_dict()


def read_state(raw: Path) -> dict | None:
    sp = state_path(raw)
    if not sp.exists():
        return None
    try:
        return json.loads(sp.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def default_downloader(tmp: Path, want: Acquisition) -> None:
    cmd = [sys.executable, "-m", "overturemaps.cli", "download", f"--bbox={want.bbox}",
           "-f", "geoparquet", f"--type={want.overture_type}", "-o", str(tmp),
           "--release", want.release]
    print("running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def acquire(raw: Path, want: Acquisition, *, downloader=default_downloader,
            log=print) -> tuple[Path, bool]:
    """Ensure `raw` holds exactly `want`. Returns `(path, downloaded)`.

    `downloader` is injectable so the reuse and failure-safety rules can be tested without a
    network — which is the point, because the failure they prevent only happens on interruption.
    """
    have = read_state(raw)
    if raw.exists() and describes(have, want):
        log(f"reusing {raw.name}: release {want.release}, bbox {want.bbox}")
        return raw, False
    if raw.exists():
        if have:
            log(f"re-downloading {raw.name}: it holds release {have.get('release')} / bbox "
                f"{have.get('bbox')}, not {want.release} / {want.bbox}")
        else:
            log(f"re-downloading {raw.name}: no state file, so what it holds is unknown")

    tmp = raw.with_name(raw.name + ".partial")
    tmp.unlink(missing_ok=True)
    try:
        downloader(tmp, want)
    except BaseException:
        # BaseException so a KeyboardInterrupt cannot promote a partial file either.
        tmp.unlink(missing_ok=True)
        raise
    if not tmp.exists():
        raise RuntimeError(f"downloader produced no file at {tmp}")
    # Commit. State goes first, so there is no instant at which new bytes carry an old label.
    state_path(raw).unlink(missing_ok=True)
    tmp.replace(raw)
    state_path(raw).write_text(json.dumps(want.as_dict(), indent=1), encoding="utf-8")
    return raw, True
