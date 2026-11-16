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

import inspect
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

CARD = SPIKE / "card_selftest.mjs"
PUBLISHED = SPIKE / "fixtures" / "published" / "manifest.json"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH")
@pytest.mark.skipif(not PUBLISHED.exists(),
                    reason="run scripts/export_published_layers.py to build the bundle")
def test_the_card_says_the_right_thing_including_what_it_declines_to_say():
    """The per-criterion card's **words**, which no message-level check can see.

    `worker_conformance.mjs` checks the `explainAt` reply. A correct reply still becomes a wrong
    disclosure if the rendering prints "no restrictions" where the layer does not disclose, a bare
    "20 min" where the 20 is a lower bound, or one shop where the pipeline chose a node carrying
    three. `card.js` holds those as pure functions for exactly that reason, and
    `card_selftest.mjs` feeds them both hand-built replies and 40,000 real ones from the shipped
    bundle.
    """
    out = subprocess.run(["node", str(CARD)], capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, f"{out.stdout}\n{out.stderr}"
    assert "all card checks passed" in out.stdout
    assert out.stdout.count("PASS  ") >= 15, out.stdout
    # The real-bundle pass is only evidence if the sample reached all three outcomes and a
    # shared-node destination, which that check asserts and prints. A run that silently exercised
    # 40,000 identical passing cells would otherwise look the same from here.
    assert '"PASS":' in out.stdout and '"UNKNOWN":' in out.stdout, out.stdout
    assert "of those a shared node" in out.stdout, out.stdout


CARD_JS = SPIKE / "card.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH")
def test_the_cards_estimate_note_is_the_encoders_own_rounding_rule():
    """**The card makes two claims about this pipeline, and this is what holds them to it.**

    `card_selftest.mjs` pins the sentence as a literal, which is a tautology: the sentence is
    checked against itself. The two claims inside it are checkable against code.

    * "rounded up to the whole minute". `grid.encode_minutes` is `ceil`, so a cell displaying
      12 min holds a model time in `(11, 12]` and the number shown **overstates** by up to 60 s.
      "Rounded" alone reads as "to the nearest", which is a different and flattering claim --
      601 s is 11 minutes to this encoder and 10 to the nearest. The byte is a decision input and
      `ceil` is right; `grid.py` justified its display cost with "nothing displays it", and this
      card displays it, so the word has to carry the direction.
    * "measured from the centre of this cell". `build_layer_surface` evaluates
      `grid.cell_centers_xy()`, not a door and not the pointer. A household standing at an actual
      address is up to half a cell diagonal from the point we answered for.

    Both are read from the running code rather than from a copy: the string comes out of the real
    `card.js` through node, the minute out of the real `encode_minutes`.
    """
    import numpy as np

    from locfinder.grid import ENCODING, encode_minutes
    from locfinder.traveltime.layer import build_layer_surface

    # The encoder, by behaviour and not by name.
    assert int(encode_minutes(np.array([601.0]))[0]) == 11, "encode_minutes no longer rounds up"
    assert int(np.rint(601.0 / 60.0)) == 10, "the control for what 'to the nearest' would claim"
    assert "ceil" in ENCODING, ENCODING

    src = inspect.getsource(build_layer_surface)
    assert "cell_centers_xy()" in src, (
        "the published seconds are no longer evaluated at cell centres, so the card's "
        "'from the centre of this cell' is now a false claim")

    # The card, from the running file rather than a transcription of it.
    script = (
        "require(process.argv[1]);"
        "const C = globalThis.G3Card;"
        "console.log(JSON.stringify({ note: C.ESTIMATE_NOTE, included: C.VERDICT_TEXT.INCLUDED }));"
    )
    out = subprocess.run(["node", "-e", script, str(CARD_JS)],
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, f"{out.stdout}\n{out.stderr}"
    card = json.loads(out.stdout)

    assert "rounded up" in card["note"], (
        f"the encoder rounds up and the card does not say so: {card['note']!r}")
    assert "nearest" not in card["note"], (
        f"the encoder is ceil, so 'nearest' overstates its own accuracy: {card['note']!r}")
    assert "centre of this cell" in card["note"], card["note"]

    # And the headline is a claim about the model, not about the place. The sentence it replaced
    # is recorded here because it is what a reader of `docs/experiments/s3-11/` sees on the
    # screenshot, and a silent revert would otherwise look like the original wording.
    assert card["included"] == "The model estimates this cell meets your limits.", card["included"]
    assert "satisfied here" not in card["included"], (
        "the affirmative headline asserts a fact about the place again; pass 54 asked for a "
        "statement about the model")


CONTROL = SPIKE / "byteswap_control.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH")
@pytest.mark.skipif(not VECTORS.exists(), reason="vectors not generated")
def test_a_recorded_expectation_and_not_a_structural_check_catches_a_byte_swap():
    """**A positive control on a check**, and the reason the byte-swap group exists.

    The destination plane is the only `uint16` plane, so it is the only one with a byte order, and
    read the wrong way round its ordinals are *valid* -- they index real destinations -- and wrong.
    With small ordinals a swap lands out of range and the bounds check fires, which hides the real
    hazard. The `byte-swap survivors` group holds a 300-entry table with cells at ordinals 1 and
    256, which swap into each other, so no structural check can see the difference.

    This runs the big-endian mutation against **only** that group, because the mutation runner
    stops at the first failing check -- a different group's bounds check -- so without this the
    group built for the hazard would never be the thing that caught it.

    **Renamed after pass 49 finding 6**, which withdrew the claim this test used to assert. The
    name comparison is not what catches a byte swap: the vectors record the expected *ordinal*
    too, so the ordinal comparison fires first. What a swap survives is the structural bounds
    check; what catches it is comparing against a recorded expectation at all. The same finding
    showed the control could print `CONFIRMED` without performing an endian mutation, so it now
    requires its mutation to have applied, the baseline to answer completely correctly, and the
    mutated ordinals to be exactly the byte-swaps of the baseline's.
    """
    out = subprocess.run(["node", str(CONTROL)], capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, f"{out.stdout}\n{out.stderr}"
    assert "CONFIRMED" in out.stdout, out.stdout
    assert "became exactly its byte-swap" in out.stdout, out.stdout
    assert "comparing against a recorded expectation" in out.stdout, out.stdout
    # The withdrawn claim must not come back.
    assert "only thing that catches" not in out.stdout, out.stdout


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
    # `or True` made this vacuous in the first version -- a check that cannot fail, in the test
    # written to stop checks that cannot fail. What it has to assert is the property that makes a
    # layer-0 read WRONG: the two layers must name DIFFERENT ordinals at the same cell, or reading
    # layer 0 for layer 1 would be right by accident.
    planes = {}
    for case in two["cases"]:
        for q in case.get("destination_at", []):
            for n in (q.get("names") or []):
                planes.setdefault(q["col"], {})[n["layer"]] = n["ordinal"]
    differing = [col for col, byl in planes.items()
                 if len(byl) > 1 and len(set(byl.values())) > 1]
    assert differing, (
        "no cell has two layers naming different ordinals, so a destination read from layer 0 "
        f"would be correct by accident: {planes}")
    # And one layer must have a cell the other does not publish, which is what makes the per-layer
    # indexing inside the INIT invariant loop load-bearing rather than only the query's.
    assert len(two["dest_tables"]) == 2 and all(two["dest_tables"])
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
