"""Does `test_certify.py` actually catch a wrong certified comparator?

Phase 4a.2. The comparator's whole job is to say when the convention's argmin is **not** the real
one, and every figure it produces is a count. A comparator that quietly answered `AGREES` whenever
its intervals overlapped would report a clean zero divergence rate and read as reassurance — the
same shape as pass 38 F3's crashing mutant and pass 39 R5's dead sentinel. So the tests are attacked
before the rate they justify is believed.

**The mutation that matters is `report AGREES on an overlap`.** If it survives, nothing here
measures what the phase exists to measure.

    python scripts/mutate_certify.py
    python scripts/mutate_certify.py --self-test

Exits non-zero if any mutation survives or is reported invalid. The source is restored in a
`finally` block and byte identity is verified by SHA-256 before exiting.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = ROOT / "locfinder" / "measure" / "certify.py"
TESTS = "tests/test_certify.py"

LF = chr(10)
CRLF = chr(13) + chr(10)

#: Exercises every public entry point, and every branch a mutation below touches, on inputs where no
#: intended mutation raises. Prints a digest so a mutant the smoke does not distinguish can be told
#: from one it does — pass 39 R2's lesson, applied here from the start rather than after a review.
SMOKE = (
    "from fractions import Fraction as F;"
    "import locfinder.measure.certify as c;"
    "out=[];"
    "out.append(c.sqrt_interval(F(2),8));"
    "out.append(c.sqrt_interval(0,8));"
    "i=c.Interval(F(1),F(2));j=c.Interval(F(10),F(11));"
    "out.append(i+j);out.append(i.scaled(F(3)));out.append(i.scaled(F(-3)));"
    "out.append(i.divided_by(j));out.append(i.contains(F(3,2)));"
    "out.append(i.strictly_below(j));"
    "p=c.Partial(geometry=((0.0,0.0),(3.0,4.0),(3.0,14.0)),seg_o=0,t_o=F(1,3),seg_d=1,t_d=F(2,3),"
    "cost=7.0);"
    "out.append(p.fraction_interval(24));"
    "q=c.Partial(geometry=((0.0,0.0),(3.0,4.0)),seg_o=0,t_o=F(1,4),seg_d=0,t_d=F(3,4),cost=7.0);"
    "out.append(q.fraction_interval(24));"
    "z=c.Partial(geometry=((5.0,5.0),(5.0,5.0)),seg_o=0,t_o=F(0),seg_d=0,t_d=F(1),cost=7.0);"
    "out.append(z.fraction_interval(24));"
    "a=c.Journey(full_edge_costs=(0.1,0.2),partials=(p,),connector_sq=(F(4),),label='a');"
    "b=c.Journey(full_edge_costs=(9.0,),label='b');"
    "out.append(a.cost_interval(24));out.append(a.rounded_cost());"
    "out.append(c.certify_cheaper(a,b));"
    "out.append(c.certify_selection([a,b],0).status);"
    "out.append(c.certify_selection([b,a],0).status);"
    "t1=c.Journey(full_edge_costs=(1.5,),label='t1');t2=c.Journey(full_edge_costs=(1.5,),label='t2');"
    "r=c.certify_selection([t1,t2],0,max_precision=32);"
    "out.append((r.status,r.exactly_tied,r.agrees));"
    "print(repr(out))"
)

#: Errors meaning the MUTATION is broken rather than the behaviour changed: the text does not name
#: something that exists, or does not parse. `TypeError` is deliberately absent — pass 39 R2 showed
#: a legitimate arithmetic mutation that raises it.
BROKEN = ("NameError", "ImportError", "SyntaxError", "IndentationError", "UnboundLocalError")

# (label, old, new) -- `old` must appear exactly once in certify.py.
MUTATIONS: list[tuple[str, str, str]] = [
    # --- the one this phase exists for.
    (
        "report the convention's choice as AGREES when the intervals still overlap",
        "    return (None, min(k, max_precision))",
        "    return (a.label, min(k, max_precision))",
    ),
    (
        "treat an undecided comparison as agreement in the status",
        "    if undecided is not None:",
        "    if False:",
    ),
    (
        "count UNRESOLVED as agreement",
        '        return self.status == AGREES',
        '        return self.status in (AGREES, UNRESOLVED)',
    ),
    # --- the interval primitive, where a wrong bound makes every comparison unsound.
    (
        "take the ceiling of the scaled radicand instead of the floor",
        "    n = (q * scale).numerator // (q * scale).denominator      # floor, exactly",
        "    n = -((-(q * scale).numerator) // (q * scale).denominator)",
    ),
    (
        "scale by 2**k instead of 4**k, so the bracket is not on sqrt(q)",
        "    scale = 1 << (2 * k)",
        "    scale = 1 << k",
    ),
    (
        "return the lower bound twice, so an irrational value is claimed exact",
        "    return (s * unit, (s + 1) * unit)",
        "    return (s * unit, s * unit)",
    ),
    (
        "compute the bracket through binary64 instead of exact integers",
        "    s = math.isqrt(n)",
        "    s = int(math.sqrt(float(n)))",
    ),
    # --- interval arithmetic.
    (
        "add the endpoints crosswise",
        "        return Interval(self.lo + other.lo, self.hi + other.hi)",
        "        return Interval(self.lo + other.hi, self.hi + other.lo)",
    ),
    (
        "divide endpoint by matching endpoint instead of crosswise",
        "        return Interval(self.lo / other.hi, self.hi / other.lo)",
        "        return Interval(self.lo / other.lo, self.hi / other.hi)",
    ),
    (
        "ignore the sign when scaling, so a negative scalar inverts the interval",
        "        return Interval(c * self.lo, c * self.hi) if c >= 0 else "
        "Interval(c * self.hi, c * self.lo)",
        "        return Interval(c * self.lo, c * self.hi)",
    ),
    (
        "decide a comparison on a non-strict inequality, so touching intervals decide it",
        "        return self.hi < other.lo",
        "        return self.hi <= other.lo",
    ),
    # Removing this guard entirely is an EQUIVALENT mutation, not a survivor: `Fraction`
    # division by zero raises `ZeroDivisionError` from the very next statement, so a test asserting
    # that exception still passes. The detectable mutation is one that SWALLOWS the condition.
    (
        "pass a zero-reaching denominator through instead of refusing it",
        "        if other.lo <= 0:\n            raise ZeroDivisionError(",
        "        if other.lo <= 0:\n            return self\n        if False:\n"
        "            raise ZeroDivisionError(",
    ),
    # --- the terms §2.4 item 6 names.
    (
        "multiply the connector by the access speed instead of dividing",
        "            out = out + Interval(lo, hi).scaled(Fraction(1) / self.access_speed)",
        "            out = out + Interval(lo, hi).scaled(self.access_speed)",
    ),
    (
        "apportion the partial by the fraction of the wrong record total",
        "        return span.divided_by(total)",
        "        return span",
    ),
    (
        "drop the whole intermediate segments from the span",
        "            for q in qs[seg_o + 1:seg_d]:",
        "            for q in []:",
    ),
    (
        "do not orient the span, so the two occurrences are not symmetric",
        "        seg_o, t_o, seg_d, t_d = self.seg_o, self.t_o, self.seg_d, self.t_d\n"
        "        if (seg_o, t_o) > (seg_d, t_d):",
        "        seg_o, t_o, seg_d, t_d = self.seg_o, self.t_o, self.seg_d, self.t_d\n"
        "        if False:",
    ),
    (
        "decide the zero-length record on the bracketed total rather than the exact radicands",
        "        if all(q == 0 for q in qs):",
        "        if False:",
    ),
    (
        "take the span from the start of the origin's segment rather than from the occurrence",
        "            span = part(seg_o, Fraction(1) - t_o)",
        "            span = part(seg_o, Fraction(1))",
    ),
    # --- the rounded side, which is what the certified side is compared against.
    (
        "sum the convention's terms from the left instead of with fsum",
        "        return math.fsum(terms)",
        "        run = 0.0\n        for term in terms:\n            run += term\n        return run",
    ),
    # --- the guards.
    (
        "accept a non-finite cost instead of refusing it",
        "    if not math.isfinite(value):",
        "    if False:",
    ),
    # Likewise EQUIVALENT: `candidates[chosen]` raises `IndexError` on its own. The detectable
    # mutation silently repairs the index instead of refusing it.
    (
        "silently clamp a selection index outside the candidate set",
        "    if not 0 <= chosen < len(candidates):\n        raise IndexError(",
        "    if not 0 <= chosen < len(candidates):\n        chosen = 0\n    if False:\n"
        "        raise IndexError(",
    ),
]


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: pathlib.Path) -> str:
    return path.read_bytes().decode("utf-8")


def write(path: pathlib.Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def localise(anchor: str, source: str) -> str:
    return anchor.replace(LF, CRLF) if CRLF in source else anchor


def smoke() -> tuple[str | None, str | None]:
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
    """Does the crash detector fire? A detector that cannot is the defect one level up."""
    original = read(TARGET)
    before = digest(TARGET)
    failures = 0
    try:
        if smoke()[0] is not None:
            print("FAIL: the UNMUTATED module is reported broken, so every mutation would be "
                  "INVALID and this harness would report nothing")
            failures += 1
        else:
            print("clean source: smoke passes")
        anchor = localise("    s = math.isqrt(n)", original)
        if original.count(anchor) != 1:
            print(f"FAIL: the self-test anchor appears {original.count(anchor)} times")
            failures += 1
        else:
            write(TARGET, original.replace(
                anchor, localise("    s = a_name_from_another_scope(n)", original), 1))
            got = smoke()[0]
            if got == "NameError":
                print("broken mutant: reported INVALID as NameError, so a crash cannot be banked "
                      "as a catch")
            else:
                print(f"FAIL: a mutant naming an undefined function was reported as {got!r}")
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
            print(f"FAIL: the unmutated smoke does not run ({broken}); every mutation would be "
                  "reported INVALID")
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
                          "it tests nothing")
                    survived.append(label)
                    continue
                if digest_now is not None and digest_now == baseline_digest:
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
