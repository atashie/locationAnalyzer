"""Phase 1: the two acquisition hazards, tested without a network.

Both are in the plan's S4.1 and one was demonstrated by Codex pass-10 H5. Neither is reachable by a
happy-path test, which is exactly why they survived: the first needs a *changed request* and the
second needs an *interrupted download*. The downloader is injected so both can be provoked.
"""
import json

import pytest

from locfinder.places.acquire import Acquisition, acquire, read_state, state_path

A = Acquisition(overture_type="place", release="2026-10-21.0", bbox="-79.2,35.7,-78.5,36.15")
B = Acquisition(overture_type="place", release="2026-10-21.0", bbox="-79.35,35.55,-78.35,36.30")


def writer(payload: str):
    def _dl(tmp, want):
        tmp.write_text(payload, encoding="utf-8")
    return _dl


def test_a_fresh_acquisition_downloads_and_records_what_it_fetched(tmp_path):
    raw = tmp_path / "raw.parquet"
    path, downloaded = acquire(raw, A, downloader=writer("A-bytes"), log=lambda *a: None)
    assert downloaded and path.read_text(encoding="utf-8") == "A-bytes"
    assert read_state(raw) == A.as_dict()


def test_the_same_request_reuses_the_file(tmp_path):
    raw = tmp_path / "raw.parquet"
    acquire(raw, A, downloader=writer("A-bytes"), log=lambda *a: None)
    _, downloaded = acquire(raw, A, downloader=writer("SHOULD-NOT-RUN"), log=lambda *a: None)
    assert not downloaded and raw.read_text(encoding="utf-8") == "A-bytes"


def test_a_changed_bbox_forces_a_re_download():
    """The hazard that let an evaluation-extent download back a routing-extent claim: the original
    `fetch_places.fetch_overture` returned any existing raw file regardless of what was asked for."""
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        raw = Path(d) / "raw.parquet"
        acquire(raw, A, downloader=writer("eval-extent"), log=lambda *a: None)
        _, downloaded = acquire(raw, B, downloader=writer("routing-extent"),
                                log=lambda *a: None)
        assert downloaded and raw.read_text(encoding="utf-8") == "routing-extent"
        assert read_state(raw)["bbox"] == B.bbox


def test_a_changed_release_forces_a_re_download(tmp_path):
    raw = tmp_path / "raw.parquet"
    acquire(raw, A, downloader=writer("old"), log=lambda *a: None)
    newer = Acquisition(overture_type="place", release="2026-11-21.0", bbox=A.bbox)
    _, downloaded = acquire(raw, newer, downloader=writer("new"), log=lambda *a: None)
    assert downloaded and read_state(raw)["release"] == "2026-11-21.0"


def test_a_raw_file_with_no_state_is_never_trusted(tmp_path):
    raw = tmp_path / "raw.parquet"
    raw.write_text("mystery", encoding="utf-8")
    _, downloaded = acquire(raw, A, downloader=writer("known"), log=lambda *a: None)
    assert downloaded and raw.read_text(encoding="utf-8") == "known"


def test_an_interrupted_download_leaves_the_previous_pair_intact(tmp_path):
    """Codex pass-10 H5. Writing over the raw file while its state stayed valid meant a failed
    download left the NEW bytes labelled with the OLD release, and the next request for that
    release reused them."""
    raw = tmp_path / "raw.parquet"
    acquire(raw, A, downloader=writer("A-bytes"), log=lambda *a: None)

    def fails(tmp, want):
        tmp.write_text("B-partial", encoding="utf-8")
        raise RuntimeError("connection dropped")

    with pytest.raises(RuntimeError, match="connection dropped"):
        acquire(raw, B, downloader=fails, log=lambda *a: None)

    # the previous file and its label are untouched, and no partial file survives
    assert raw.read_text(encoding="utf-8") == "A-bytes"
    assert read_state(raw) == A.as_dict()
    assert not (tmp_path / "raw.parquet.partial").exists()

    # and asking for A again legitimately reuses A, not B's bytes
    _, downloaded = acquire(raw, A, downloader=writer("SHOULD-NOT-RUN"), log=lambda *a: None)
    assert not downloaded and raw.read_text(encoding="utf-8") == "A-bytes"


def test_an_interrupt_cannot_promote_a_partial_file_either(tmp_path):
    """`BaseException`, not `Exception`: Ctrl-C during a download must behave like a failure."""
    raw = tmp_path / "raw.parquet"

    def interrupted(tmp, want):
        tmp.write_text("partial", encoding="utf-8")
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        acquire(raw, A, downloader=interrupted, log=lambda *a: None)
    assert not raw.exists() and read_state(raw) is None


def test_a_downloader_that_writes_nothing_is_an_error_not_an_empty_success(tmp_path):
    raw = tmp_path / "raw.parquet"
    with pytest.raises(RuntimeError, match="produced no file"):
        acquire(raw, A, downloader=lambda tmp, want: None, log=lambda *a: None)
    assert read_state(raw) is None


def test_a_corrupt_state_file_is_treated_as_unknown(tmp_path):
    raw = tmp_path / "raw.parquet"
    raw.write_text("bytes", encoding="utf-8")
    state_path(raw).write_text("{not json", encoding="utf-8")
    assert read_state(raw) is None
    _, downloaded = acquire(raw, A, downloader=writer("fresh"), log=lambda *a: None)
    assert downloaded


def test_the_state_file_is_readable_json_next_to_the_raw_file(tmp_path):
    raw = tmp_path / "raw.parquet"
    acquire(raw, A, downloader=writer("x"), log=lambda *a: None)
    assert state_path(raw) == tmp_path / "raw.parquet.state"
    assert json.loads(state_path(raw).read_text(encoding="utf-8"))["type"] == "place"
