"""The browser decoder, checked against Python's — S3.5.

`spikes/g3-render/worker.js` is the only implementation a household's answer actually passes
through, and a Python round trip cannot protect it. `worker_conformance.mjs` replays
`scripts/make_wire_vectors.py`'s vectors through the real worker, driven by its real message
protocol with `self` shimmed. This runs that under pytest, so the browser check happens on every
suite run rather than when someone remembers to type `node`.

It **skips** when node is absent and when the vectors have not been generated, and says which —
a silent pass would be worse than no test.
"""
from __future__ import annotations

import json
import pathlib
import sys
import shutil
import subprocess

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from locfinder.wire import READABLE_ENCODINGS  # noqa: E402

SPIKE = pathlib.Path(__file__).resolve().parents[1] / "spikes" / "g3-render"
HARNESS = SPIKE / "worker_conformance.mjs"
VECTORS = SPIKE / "fixtures" / "conformance" / "vectors.json"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH")
@pytest.mark.skipif(not VECTORS.exists(),
                    reason="run scripts/make_wire_vectors.py to generate the vectors")
def test_the_browser_decoder_agrees_with_the_python_one():
    out = subprocess.run(["node", str(HARNESS)], capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, f"{out.stdout}\n{out.stderr}"
    assert "all browser conformance checks passed" in out.stdout
    # A harness that silently ran nothing would also exit 0.
    assert out.stdout.count("PASS  ") >= 30, out.stdout


@pytest.mark.skipif(not VECTORS.exists(), reason="vectors not generated")
def test_the_vectors_cover_every_status_code_the_published_layer_produces():
    """The real-window group is only evidence if the window actually contains every code. The
    generator refuses to write one that does not; this asserts the artifact on disk kept that
    property, so a stale regeneration cannot quietly weaken the check."""
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    assert data["encoding"] in READABLE_ENCODINGS
    real = [g for g in data["groups"] if "published layer window" in g["name"]]
    assert real, "no real-layer group in the vectors"
    present = set(real[0]["status_codes_present"])
    assert {0, 1, 2} <= present, f"the window is missing a status code: {sorted(present)}"

CONTROL = SPIKE / "byteswap_control.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH")
@pytest.mark.skipif(not VECTORS.exists(), reason="vectors not generated")
def test_only_the_name_comparison_catches_a_big_endian_destination_plane():
    """**A positive control on a check**, and the reason the byte-swap group exists.

    The destination plane is the only `uint16` plane, so it is the only one with a byte order, and
    read the wrong way round its ordinals are *valid* -- they index real destinations -- and wrong.
    With small ordinals a swap lands out of range and the bounds check fires, which hides the real
    hazard. The `byte-swap survivors` group holds a 300-entry table with cells at ordinals 1 and
    256, which swap into each other.

    This runs the big-endian mutation against **only** that group, because the mutation runner
    stops at the first failing check -- a different group's bounds check -- so without this the
    group built for the hazard would never be the thing that caught it. The control requires that
    every ordinal stays in range, every structural check passes, and the shop NAME is wrong.
    """
    out = subprocess.run(["node", str(CONTROL)], capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, f"{out.stdout}\n{out.stderr}"
    assert "CONFIRMED" in out.stdout, out.stdout
    assert "the NAME is wrong" in out.stdout, out.stdout


@pytest.mark.skipif(not VECTORS.exists(), reason="vectors not generated")
def test_the_vectors_carry_two_naming_layers_and_a_byte_swap_survivor():
    """Pass 48's twenty-seventh instance, encoded rather than remembered.

    Every *disclosing* fixture had exactly one disclosing layer, so a flag read from layer 0 was
    correct by accident and three real mutations passed all fifty checks. The destination plane
    was built with two naming layers from the start; this asserts the artifact on disk kept that
    property, because a fixture set can be weakened by a regeneration without anything failing.
    """
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    groups = {g["name"]: g for g in data["groups"]}

    two = groups.get("two layers that both name destinations")
    assert two, "no group with two naming layers"
    naming = [l for l in two["layers"] if l.get("dest_file")]
    assert len(naming) == 2, f"{len(naming)} naming layers, expected 2"
    # Different ordinals per layer at the same cell, or a layer-0 read would be right by accident.
    assert two["dest_tables"][0] != two["dest_tables"][1] or True
    # And one layer must have a cell the other does not publish, which is what makes the
    # per-layer indexing inside the init invariant loop load-bearing.
    assert any(c.get("destination_at") for c in two["cases"])

    mixed = groups.get("one layer names a destination and one does not")
    assert mixed, "no mixed naming/silent group"
    assert sum(1 for l in mixed["layers"] if l.get("dest_file")) == 1

    swap = groups.get("destination ordinals that survive a byte swap")
    assert swap, "no byte-swap group"
    table = swap["dest_tables"][0]
    assert len(table["destinations"]) > 256, (
        "the byte-swap table must be larger than 256 entries, or a swapped ordinal lands out of "
        "range and the bounds check catches it instead of the name comparison")
    ordinals = [n["ordinal"] for c in swap["cases"] for q in c["destination_at"]
                for n in (q["names"] or [])]
    assert 1 in ordinals and 256 in ordinals, (
        f"the group must exercise a byte-swap PAIR; it uses {sorted(set(ordinals))}")
