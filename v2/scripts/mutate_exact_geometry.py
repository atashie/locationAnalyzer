"""Does `test_exact_geometry.py` actually catch a wrong geometry arithmetic?

Phase 4a.1 of `docs/plans/2026-11-11-step4-comparator-plan.md`. Every rule in this project that was
trusted on reading has failed -- nine instances in
`docs/engineering-notes/feedback-verify-the-shape-of-the-risk.md`, and the ninth was pass 37 against
the plan these tests implement. So the tests get attacked before they are believed.

**The mutation that matters is `compose by rounding twice`.** It rounds every operand correctly and
composes wrongly, which is precisely what revision 1 of the step 4 plan claimed was sufficient and
what pass 37 F1 refuted. If that mutation survives, these tests do not test the thing the phase
exists to fix.

    python scripts/mutate_exact_geometry.py

Exits non-zero if any mutation survives. The source is restored in a `finally` block and byte
identity is verified by SHA-256 before exiting.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = ROOT / "locfinder" / "measure" / "exact.py"
TESTS = "tests/test_exact_geometry.py"

LF = chr(10)
CRLF = chr(13) + chr(10)

# (label, old, new) -- `old` must appear exactly once in exact.py.
MUTATIONS: list[tuple[str, str, str]] = [
    # --- the one this phase exists for: correct operands, wrong composition.
    (
        "compose by rounding twice instead of once (what revision 1 would have shipped)",
        "    return rational_sqrt(t * t * (dx * dx + dy * dy))",
        "    return float(t) * rational_sqrt(dx * dx + dy * dy)",
    ),
    # --- the projection, which is what W2 and W3 need.
    (
        "project in binary64 instead of exactly",
        "    t = ((Fraction(px) - ax_f) * dx + (Fraction(py) - ay_f) * dy) / denom",
        "    t = Fraction(((px - ax) * float(dx) + (py - ay) * float(dy)) / float(denom))",
    ),
    (
        "clamp on the rounded parameter rather than the exact one",
        "    if t <= 0:\n        return Fraction(0)\n    if t >= 1:\n        return Fraction(1)",
        "    if float(t) <= 0:\n        return Fraction(0)\n    if float(t) >= 1:\n"
        "        return Fraction(1)",
    ),
    # Replacing the degenerate branch with `denom = 1` is an EQUIVALENT mutation, not a survivor:
    # when `dx == dy == 0` the numerator is zero too, so `t` is zero either way and the branch only
    # prevents a ZeroDivisionError. The harness found it "uncaught" and the fault was the harness's.
    # Deleting the branch is the mutation that actually changes behaviour.
    (
        "delete the degenerate-segment branch",
        "    if denom == 0:\n        return Fraction(0)\n",
        "",
    ),
    # --- the correctly rounded root.
    (
        "use math.sqrt of the rounded radicand (rounds twice)",
        "    q = Fraction(q)\n    if q < 0:",
        "    q = Fraction(q)\n    if q >= 0:\n        return math.sqrt(float(q))\n    if q < 0:",
    ),
    (
        "use math.hypot for the segment length",
        "    dx, dy = Fraction(bx) - Fraction(ax), Fraction(by) - Fraction(ay)\n"
        "    return rational_sqrt(dx * dx + dy * dy)",
        "    return math.hypot(bx - ax, by - ay)",
    ),
    (
        "skip the midpoint comparison and always round down",
        "    if cmp > 0:\n        return lo + u",
        "    if False:\n        return lo + u",
    ),
    (
        "break the tie away from even",
        "    return lo if k % 2 == 0 else lo + u",
        "    return lo + u",
    ),
    # Codex pass 38 F3: this mutation used to read `scaled.numerator // scaled.denominator`, and
    # `scaled` is a local of `rational_sqrt`, not of `_decide`. The mutant raised NameError, the
    # subprocess failed, and the harness counted a crash as "caught" -- so the arithmetic it was
    # named after was never tested by it. The floor is now computed locally from `q` and `u`, which
    # is the same quantity, and the mutation fails three fixtures as it always should have.
    (
        "compare the midpoint against the floored scaling instead of the original rational",
        "    cmp = q - midpoint * midpoint",
        "    cmp = ((q / (u * u)).numerator // (q / (u * u)).denominator) * u * u"
        " - midpoint * midpoint",
    ),
    # --- two rules that had no mutation at all until Codex pass 38 F3 found them.
    (
        "drop the y interpolation in exact_position, so a diagonal foot is wrong",
        "    return (ax_f + t * (Fraction(bx) - ax_f), ay_f + t * (Fraction(by) - ay_f))",
        "    return (ax_f + t * (Fraction(bx) - ax_f), ay_f)",
    ),
    (
        "take the complement of the destination's partial in a cross-segment span",
        "    terms.append(_partial(seg_d, t_d))",
        "    terms.append(_partial(seg_d, 1 - t_d))",
    ),
    # Two mutations have been retired from this list after the harness PROVED them equivalent, which
    # is a result rather than a gap:
    #
    #  * "omit the isqrt step-up correction" — the loop was dead code. `floor(sqrt(floor(x)))`
    #    equals `floor(sqrt(x))` for every real `x >= 0`, so it could never fire. It is now gone and
    #    the identity is written down in its place.
    #  * "take the integer root of the rounded scaling" — changes `k` on 12.8% of random radicands
    #    and the answer on none, because `_decide`'s exact midpoint comparison self-corrects an
    #    off-by-one `k`. `test_the_midpoint_comparison_self_corrects_an_off_by_one_lattice_index`
    #    now pins that property instead.
    #
    # What remains attacks the step those proofs depend on: the comparison being against the
    # original rational, at the right lattice.
    (
        "compare the midpoint on the lattice below, so the self-correction stops holding",
        "    midpoint = (Fraction(2 * k + 1) * u) / 2",
        "    midpoint = (Fraction(2 * k + 1) * u) / 4",
    ),
    (
        "ignore the subnormal floor on the lattice unit",
        "    unit_exp = max(exp - (_MANT_BITS - 1), _MIN_SUBNORMAL_EXP)",
        "    unit_exp = exp - (_MANT_BITS - 1)",
    ),
    # --- the summation rules.
    (
        "accumulate the total from the left instead of with fsum",
        "    return math.fsum(_segment_lengths(geometry))",
        "    run = 0.0\n    for seg in _segment_lengths(geometry):\n        run += seg\n    return run",
    ),
    (
        "trust a supplied lengths cache that is wrong, so the cache can change an answer",
        "    lengths = _segment_lengths(geometry) if lengths is None else lengths",
        "    lengths = _segment_lengths(geometry) if lengths is None else [2 * x for x in lengths]",
    ),
    (
        "accumulate the prefix from the left, as toy.py does today",
        "    return math.fsum(lengths[:seg_index] + [partial])",
        "    run = 0.0\n    for seg in lengths[:seg_index]:\n        run += seg\n"
        "    return run + partial",
    ),
    # --- the same-edge span, which is pass 37 F5.
    (
        "measure the same-edge span as a difference of two prefixes",
        "    if seg_o == seg_d:\n        span = _partial(seg_o, abs(t_d - t_o))\n"
        "        return span / total",
        "    if seg_o == seg_d:\n"
        "        s_o = prefix_arclength(geometry, seg_o, t_o)\n"
        "        s_d = prefix_arclength(geometry, seg_d, t_d)\n"
        "        return abs((s_d / total) - (s_o / total))",
    ),
    (
        "take the span from the start of the origin's segment rather than from the occurrence",
        "    terms = [_partial(seg_o, 1 - t_o)]",
        "    terms = [_partial(seg_o, Fraction(1))]",
    ),
    (
        "drop the whole intermediate segments from the span",
        "    terms.extend(lengths[seg_o + 1:seg_d])",
        "    terms.extend([])",
    ),
    # Pass 39 R3: the span's own summation had no mutation. The total had one and the prefix had
    # one, and this third `fsum` -- the one combining the span's terms -- did not, so a left
    # accumulation here passed all 43 fixtures while returning 1.0000000000000002 for a complete
    # traversal whose fraction is exactly 1.0.
    (
        "accumulate the span from the left instead of with fsum",
        "    return math.fsum(terms) / total",
        "    run = 0.0\n    for term in terms:\n        run += term\n    return run / total",
    ),
    (
        "do not orient the span, so the two occurrences are not symmetric",
        "    if (seg_o, t_o) > (seg_d, t_d):\n"
        "        seg_o, t_o, seg_d, t_d = seg_d, t_d, seg_o, t_o",
        "    if False:\n        seg_o, t_o, seg_d, t_d = seg_d, t_d, seg_o, t_o",
    ),
    # --- the zero-length convention.
    (
        "divide by a zero total length instead of returning the normative zero",
        "    if total == 0.0:\n        return 0.0\n    return prefix / total",
        "    return prefix / total if total else float('nan')",
    ),
    # Likewise `total = 1.0` for a zero-length record is EQUIVALENT: every segment has zero length,
    # so the span is zero and `0/1.0` is still `0.0`. The detectable mutation is removing the guard
    # that handles a geometry with no segments at all.
    (
        "drop the no-segment guard, so a single-point geometry raises",
        "    if not lengths:\n        return 0.0\n",
        "",
    ),
    # --- the squared distance.
    (
        "return the squared distance to the segment start, ignoring the projection",
        "    t = exact_projection(px, py, ax, ay, bx, by)\n"
        "    qx, qy = exact_position(ax, ay, bx, by, t)",
        "    qx, qy = Fraction(ax), Fraction(ay)",
    ),
    (
        "return the unsquared distance, so ordering needs a root",
        "    return ex * ex + ey * ey",
        "    return Fraction(rational_sqrt(ex * ex + ey * ey))",
    ),
]


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: pathlib.Path) -> str:
    """Decode without newline translation, so writing it back is byte-faithful."""
    return path.read_bytes().decode("utf-8")


def write(path: pathlib.Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def localise(anchor: str, source: str) -> str:
    """Rewrite a newline-separated anchor to the line ending `source` actually uses."""
    return anchor.replace(LF, CRLF) if CRLF in source else anchor


#: Exercises every public function and **every branch a mutation touches**, on inputs where no
#: intended mutation raises. It prints a digest of what it computed, so a mutant whose line the
#: smoke never reaches can be told from one the smoke reaches and disagrees with.
#:
#: Pass 39 R2: the first version called `same_edge_fraction` only across segments, so the
#: same-segment branch was unprobed and a structurally broken mutant there passed the smoke and
#: would have been banked as caught. The same-segment, degenerate-segment and zero-length cases are
#: now all exercised.
SMOKE = (
    "from fractions import Fraction as F;"
    "import locfinder.measure.exact as e;"
    "g=((0.0,0.0),(3.0,4.0),(3.0,14.0),(9.0,22.0));"
    "z=((5.0,5.0),(5.0,5.0));"
    "out=[];"
    "out.append(e.rational_sqrt(F(2)));"
    "t=e.exact_projection(1.0,2.0,0.0,0.0,3.0,4.0);"
    "out.append(t);"
    "out.append(e.exact_projection(1.0,2.0,7.0,7.0,7.0,7.0));"
    "out.append(e.exact_position(0.0,0.0,3.0,4.0,t));"
    "out.append(e.exact_segment_sq(1.0,2.0,0.0,0.0,3.0,4.0));"
    "out.append(e.segment_length(0.0,0.0,3.0,4.0));"
    "out.append(e.scaled_segment_length(0.0,0.0,3.0,4.0,F(1,3)));"
    "out.append(e.segment_lengths(g));"
    "tot=e.total_length(g);"
    "out.append(tot);"
    "p=e.prefix_arclength(g,1,F(1,3));"
    "out.append(p);"
    "out.append(e.prefix_arclength(g,1,F(1,3),e.segment_lengths(g)));"
    "out.append(e.traversal_fraction(p,tot));"
    "out.append(e.traversal_fraction(0.0,0.0));"
    "out.append(e.same_edge_fraction(g,0,F(1,2),2,F(1,4)));"
    "out.append(e.same_edge_fraction(g,1,F(1,4),1,F(3,4)));"
    "out.append(e.same_edge_fraction(g,2,F(3,4),0,F(1,4)));"
    "out.append(e.same_edge_fraction(z,0,F(0),0,F(1)));"
    "out.append(e.same_edge_fraction(((1.0,1.0),),0,F(0),0,F(0)));"
    "print(repr(out))"
)

#: Errors that mean the MUTATION ITSELF is broken rather than the behaviour changed: the mutated
#: text does not name a thing that exists, or does not parse.
#:
#: Pass 39 R2 removed `TypeError` and `AttributeError` from this list. Replacing an integer floor
#: division with true division is a **legitimate arithmetic defect** and raises
#: `TypeError: 'float' object cannot be interpreted as an integer`, so classifying `TypeError` as
#: broken dismissed a real mutation as invalid. Exception class alone cannot separate "invalid" from
#: "wrong"; what separates them is whether the smoke's *values* move, which is why `smoke()` now
#: returns a digest as well.
BROKEN = ("NameError", "ImportError", "SyntaxError", "IndentationError", "UnboundLocalError")


def smoke() -> tuple[str | None, str | None]:
    """`(broken_error_name, digest)` for the module as it currently stands on disk.

    `broken_error_name` is set when the mutated text does not name something that exists or does not
    parse — a mutant that tests nothing. `digest` is what the smoke computed, or `None` if it did
    not finish; comparing a mutant's digest with the baseline's says whether the smoke **reached**
    the mutated line at all, which an exception class cannot.
    """
    proc = subprocess.run([sys.executable, "-B", "-c", SMOKE],
                          cwd=ROOT, capture_output=True, text=True)
    if proc.returncode == 0:
        return (None, proc.stdout.strip())
    for name in BROKEN:
        if name in proc.stderr:
            return (name, None)
    return (None, None)


def run_tests() -> bool:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", TESTS, "-x", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT, capture_output=True, text=True,
    )
    return proc.returncode == 0


def self_test() -> int:
    """Does the crash detector fire? A detector that cannot is the pass-38 F3 defect one level up.

        python scripts/mutate_exact_geometry.py --self-test
    """
    original = read(TARGET)
    before = digest(TARGET)
    failures = 0
    try:
        if smoke()[0] is not None:
            print("FAIL: the UNMUTATED module is reported broken, so every mutation would be "
                  "INVALID and the harness would report nothing useful")
            failures += 1
        else:
            print("clean source: smoke passes")

        # A mutation referring to a name that exists only in another function -- which is exactly
        # the shape of the mutation pass 38 F3 found counted as caught.
        anchor = localise("    cmp = q - midpoint * midpoint", original)
        if original.count(anchor) != 1:
            print(f"FAIL: the self-test's anchor appears {original.count(anchor)} times")
            failures += 1
        else:
            write(TARGET, original.replace(
                anchor, localise("    cmp = a_name_from_another_scope - midpoint * midpoint",
                                 original), 1))
            got = smoke()[0]
            if got == "NameError":
                print("broken mutant: reported INVALID as NameError, so a crash can no longer be "
                      "banked as a catch")
            else:
                print(f"FAIL: a mutant referencing an undefined name was reported as {got!r}")
                failures += 1
    finally:
        write(TARGET, original)

    if digest(TARGET) != before:
        print(f"FAIL: {TARGET.name} was not restored byte-identically")
        failures += 1
    else:
        print("source restored byte-identically")
    return 1 if failures else 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()
    original = read(TARGET)
    before = digest(TARGET)
    survived: list[str] = []

    try:
        if not run_tests():
            print("FAIL: the unmutated tests do not pass; nothing below would mean anything")
            return 1
        broken, baseline_digest = smoke()
        if broken is not None or baseline_digest is None:
            print(f"FAIL: the unmutated smoke does not run ({broken}); every mutation below would "
                  "be reported INVALID and the harness would say nothing")
            return 1
        print("baseline passes, and its smoke digest is recorded\n")

        for label, old, new in MUTATIONS:
            old_l, new_l = localise(old, original), localise(new, original)
            count = original.count(old_l)
            if count != 1:
                print(f"SKIP         {label}: anchor appears {count} times; the mutation needs "
                      "updating to match the current source")
                survived.append(label)
                continue
            write(TARGET, original.replace(old_l, new_l, 1))
            try:
                broken, digest_now = smoke()
                if broken is not None:
                    print(f"INVALID      {label}: the mutant raises {broken} on ordinary input, so "
                          "it tests nothing and a failing suite would be evidence of a crash "
                          "rather than of a caught defect")
                    survived.append(label)
                    continue
                if digest_now is not None and digest_now == baseline_digest:
                    # The smoke ran and computed exactly what the clean module computes. That means
                    # it did not DISTINGUISH this mutant -- either the line was not reached, or it
                    # was reached on inputs where the two rules agree, which is the usual case here
                    # (left accumulation of three short lengths agrees with `fsum`). Saying "not
                    # reached" would be a claim this check cannot support. Either way the mutation
                    # has no smoke-level probe and its validity rests on the suite alone, which is
                    # pass 39 R2's second half and is reported rather than hidden.
                    print(f"UNSEPARATED  {label}: the smoke computes the same values as the clean "
                          "module, so only the suite distinguishes this mutant")
                if run_tests():
                    print(f"NOT CAUGHT   {label}  <-- no test sees this")
                    survived.append(label)
                else:
                    print(f"caught       {label}")
            finally:
                write(TARGET, original)
    finally:
        write(TARGET, original)

    if digest(TARGET) != before:
        print(f"\nFAIL: {TARGET.name} was not restored byte-identically")
        return 1
    print("\nsource restored byte-identically")

    if survived:
        print(f"{len(survived)} of {len(MUTATIONS)} mutations survived:")
        for label in survived:
            print(f"  - {label}")
        return 1
    print(f"all {len(MUTATIONS)} mutations caught")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
