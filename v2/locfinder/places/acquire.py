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

**And two writers must not interleave.** Removing the state before replacing the bytes makes a
single writer's interruption safe but says nothing about concurrency, and the first version claimed
more than it delivered (Codex pass-11 H1): with a shared `raw.partial` filename and no lock, the
schedule "A replaces raw → B downloads and commits B → A writes state A" leaves B's bytes labelled
A, and both calls return success. Reproduced deterministically rather than by timing luck. So each
acquisition now uses a **process-unique** temporary file, and the whole check-download-commit
sequence is serialised by an exclusive lock file beside the raw file.

**And the downloader writes files we did not ask for.** The `overturemaps` CLI drops a sidecar
beside its output named `<output>.state` — exactly the convention this module uses for its own state
file. With the download going straight to `raw` that sidecar lands *on* our state file, and it
parses as valid JSON with different keys, so `describes()` returns False and the pair re-downloads
on every run forever: a silent permanent cache miss, found on disk in `data/slice/`. With a
process-unique temp file it merely orphans one sidecar per download. Patching the one filename would
leave the collision class open, so the download now goes into a **temporary directory** that is
removed wholesale: whatever the downloader writes beside its output is contained and cannot collide
with anything this module owns.

The lock is advisory and local: it serialises acquisitions on one machine, which is what the build
does. It does **not** make the *consumer* safe — a caller that acquires and then reads is still
racing anything that replaces the file in between — and the durable answer to that is S4.1's
immutable release bundles with an atomic manifest switch, not a longer-held lock.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

STATE_SUFFIX = ".state"
LOCK_SUFFIX = ".lock"
#: Seconds to wait for another acquisition to finish before giving up. Generous, because the thing
#: being waited for is a multi-minute download.
LOCK_TIMEOUT_S = 1800.0
#: Seconds after which a lock whose owner has vanished is considered abandoned.
LOCK_STALE_S = 3600.0


@contextmanager
def _exclusive(raw: Path, *, timeout_s: float | None = None):
    """Serialise the whole check-download-commit sequence for one raw file.

    `O_CREAT | O_EXCL` is the portable atomic test-and-set. A lock older than `LOCK_STALE_S` is
    broken, because a crashed download must not block the build forever.

    The timeouts are read from the module globals at call time, not bound as default arguments:
    binding them made the values un-overridable and a test that lowered `LOCK_TIMEOUT_S` waited the
    full 1800 s instead.
    """
    lock = raw.with_suffix(raw.suffix + LOCK_SUFFIX)
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + (LOCK_TIMEOUT_S if timeout_s is None else timeout_s)
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {time.time():.0f}".encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                age = time.time() - lock.stat().st_mtime
            except OSError:
                continue
            if age > LOCK_STALE_S:
                lock.unlink(missing_ok=True)
                continue
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"another acquisition has held {lock.name} for {age:.0f} s; "
                    "remove it if that process is gone")
            time.sleep(0.2)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


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
    with _exclusive(raw):
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

        # A directory, process-unique: one acquisition's cleanup cannot delete another's download,
        # and any sidecar the downloader writes beside its output is contained rather than left in
        # a namespace this module also uses.
        tmp_dir = raw.with_name(f".{raw.name}.{os.getpid()}.partial")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir.mkdir(parents=True)
        tmp = tmp_dir / raw.name
        try:
            downloader(tmp, want)
            if not tmp.exists():
                raise RuntimeError(f"downloader produced no file at {tmp}")
            # Commit. State goes first, so there is no instant at which new bytes carry an old
            # label. `os.replace` is atomic within a volume, and the temp directory is a sibling of
            # the target, so the two are always on one volume.
            state_path(raw).unlink(missing_ok=True)
            tmp.replace(raw)
            state_path(raw).write_text(json.dumps(want.as_dict(), indent=1), encoding="utf-8")
        finally:
            # `finally`, so a KeyboardInterrupt cannot leave a partial directory behind either.
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return raw, True
