"""Compile a single module and exercise range/exit behavior through real Worker runs."""
import subprocess

import pytest

from plankalkulsharp.compiler import CompileError, check, compile_source, parse
from plankalkulsharp.dotnet import build_program, ensure_worker
from plankalkulsharp.notation import project


CASES = [
    ("W1 i0 (4) { R0 * 10 + i0 => R0 }", 123),
    ("W2 i0 (4) { R0 * 10 + i0 => R0 }", 3210),
    ("W3 i0 (2, 5) { R0 * 10 + i0 => R0 }", 234),
    ("W4 i0 (5, 2) { R0 * 10 + i0 => R0 }", 543),
    ("W5 i0 (2, 5) { R0 * 10 + i0 => R0 }", 234),
    ("W5 i0 (5, 2) { R0 * 10 + i0 => R0 }", 543),
    ("W1 i0 (0) { 9 => R0 } W2 i0 (0) { 9 => R0 } W3 i0 (2,2) { 9 => R0 } W4 i0 (2,2) { 9 => R0 } W5 i0 (2,2) { 9 => R0 }", 0),
    ("5 => Z0 W1 i0 (Z0) { R0 + 1 => R0 2 => Z0 }", 5),
    ("W1 i0 (3) { W1 i1 (i0) { R0 + 1 => R0 } }", 3),
    ("W1 i0 (3) { i0 => Z0[i0:3 x 32.0] } W2 i0 (3) { R0 + Z0[i0] => R0 }", 3),
    ("W1 i0 (10) { i0 = 2 => FIN i0 = 5 => FIN2 R0 + i0 => R0 }", 8),
    ("W1 i0 (10) { i0 = 5 -> { i0 => R0 FIN3 } }", 5),
    ("W1 i0 (3) { L -> { R0 + 1 => R0 FIN 99 => R0 } R0 + 10 => R0 }", 33),
    ("W1 i0 (3) { L -> { R0 + 1 => R0 FIN2 } 99 => R0 }", 3),
    ("W1 i0 (3) { W1 i1 (3) { R0 + 1 => R0 FIN4 } 99 => R0 }", 1),
    ("W1 i0 (3) { W1 i1 (3) { R0 + 1 => R0 FIN5 } } 99 => R0", 1),
    ("FIN 99 => R0", 0),
    ("0 => FIN 7 => R0 L => FIN1 99 => R0", 7),
    ("W { R0 < 3 -> R0 + 1 => R0 R0 = 3 -> R0 + 2 => R0 }", 5),
    ("W { 0 => FIN }", 0),
    ("W { R0 + 1 => R0 R0 = 3 => FIN2 FIN 99 => R0 }", 3),
    ("W3 i0 (2147483646,2147483647) { R0 + 1 => R0 } W4 i0 (-2147483647,-2147483648) { R0 + 1 => R0 }", 2),
    ("W3 i0 (9223372036854775806,9223372036854775807) { R0 + 1 => R0 } W4 i0 (-9223372036854775807,-9223372036854775808) { R0 + 1 => R0 }", 2),
    ("W5 i0 (-2,1) { R0 + 1 => R0 } W5 i0 (1,-2) { R0 + 1 => R0 }", 6),
    ("W3 i0 (0,2147483648) { 7 => Z0[i0:2 x 32.0] Z0[i0] => R0 FIN2 }", 7),
    ("W1 i0 (V0) { R0 + 1 => R0 }", None),
    ("W3 i0 (0,V0) { R0 + 1 => R0 }", None),
    ("W4 i0 (V0,0) { R0 + 1 => R0 }", None),
]


def test_index_scope_fin_validation_and_notation():
    invalid = [
        "i0 => R0", "W1 i0 (3) {} i0 => R0", "W1 i0 (3) { W2 i0 (2) {} }",
        "W1 i0 (3) { 1 => i0 }", "W1 i0[:32.0] (3) {}", "W1 i0 (3) { i0[0] => R0 }",
        "FIN0", "FIN2", "2 => FIN", "W1 i0 (-1) {}", "W2 i0 (-1) {}",
        "W3 i0 (3,2) {}", "W4 i0 (2,3) {}", "W1 i0 (2,3) {}", "W5 i0 (2) {}",
        "FOR Z0 FROM 0 TO 2 {}", "W0(2) {}", "W6 i0 (2) {}",
    ]
    for body in invalid:
        with pytest.raises(CompileError):
            compile_source(f"P0 main() -> R0[:32.0]\n{body}\nEND")
    for signature in ("P0 f(i0[:32.0]) -> R0[:32.0]", "P0 f() -> i0[:32.0]"):
        with pytest.raises(CompileError): parse(signature + "\nEND")
    source = "P0 main() -> R0[:32.0]\nW1 i0 (3) { L -> { i0 => R0 FIN3 } }\nEND"
    rows = project(source)["rows"]
    fin = next(r for r in rows if r["kind"] == "Fin")["cells"][0]
    assert fin["text"] == "Fin³" and "W1 i0" in fin["hint"]
    assert any(c["text"] == "W¹" and c["index"] == "0" for r in rows for c in r["cells"])
    # An exit can bypass the free; do not propagate the skipped lifetime fact.
    check(parse("int=32.0\nP0 f(V0[:0]) -> R0[:32.0]\n@int => Z0\nL -> { V0 => FIN Z0 => @ }\nZ0[@] => R0\nEND"))


def test_ranges_and_fin_in_real_worker(tmp_path):
    source = "P0 main(V0[:32.0], V1[:32.0]) -> R0[:32.0]\n"
    source += "\n".join(f"V0 = {i} -> case{i}(V1) => R0" for i in range(len(CASES))) + "\nEND\n"
    for i, (body, _) in enumerate(CASES):
        source += f"P{i+1} case{i}(V0[:32.0]) -> R0[:32.0]\n{body}\nEND\n"
    assembly = build_program(compile_source(source, "циклы.pk"), tmp_path / "циклы с пробелами")
    worker = ensure_worker()
    for i, (_, expected) in enumerate(CASES):
        result = subprocess.run(["dotnet", str(worker), "--module", str(assembly), "--", str(i), "-1"],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
        if expected is None:
            assert result.returncode == 1 and "invalid W" in result.stderr and "циклы.pk:" in result.stderr, result.stderr
            assert not result.stdout
        else:
            assert result.returncode == 0, f"case {i}: {result.stderr}"
            assert result.stdout.strip() == str(expected), f"case {i}: {result.stdout}"
