"""Small current-language checks, deliberately independent of IL layout."""

from __future__ import annotations

import pytest

from plankalkulsharp.compiler import CompileError, check, emit_il, parse
from plankalkulsharp.plankalkul_ast.nodes import DynamicAccess, IndexedLoop, GuardedStmt, StaticAccess, WLoop
from plankalkulsharp.semantic.analyzer import ResolvedArray, ResolvedBitSeq, ResolvedRecord


def analyze(source: str):
    return check(parse(source))


def test_current_syntax_analyzes_components_calls_and_loops():
    program = parse(
        "int = 8.0\n"
        "pair = (int, int)\n"
        "pairs = 3 x pair\n"
        "P1 identity(V0[:int]) -> R0[:int]\n"
        "  V0 => R0\n"
        "END\n"
        "P2 exercise(V0[:int]) -> R0[:int]\n"
        "  1 => Z0[0.0:pairs]\n"
        "  V0 => Z0[V0.1:pairs]\n"
        "  V0 < 3 -> { identity(V0) => Z1[:int] }\n"
        "  W1 i0 (3) { i0 => Z3[:int] }\n"
        "  W { Z3 < 3 -> Z3 + 1 => Z3 }\n"
        "  Z0[V0.1:pairs] => R0\n"
        "END\n"
    )

    body = program.program_defs[1].body
    assert isinstance(body[0].target.components[0], StaticAccess)
    assert isinstance(body[1].target.components[0], DynamicAccess)
    assert isinstance(body[2], GuardedStmt)
    assert isinstance(body[3], IndexedLoop)
    assert isinstance(body[4], WLoop)
    assert len(program.program_defs) == 2
    analyzer = check(program)
    assert analyzer.type_defs["pairs"] == ResolvedArray(
        3, ResolvedRecord((ResolvedBitSeq(8), ResolvedBitSeq(8)))
    )
    assert analyzer.programs["P2"].params == [ResolvedBitSeq(8)]


def test_current_syntax_analyzes_and_emits_il():
    source = (
        "int = 8.0\n"
        "P1 inc(V0[:int]) -> R0[:int]\n"
        "  V0 + 1 => R0\n"
        "END\n"
        "P2 main(V0[:int]) -> R0[:int]\n"
        "  inc(V0) => R0\n"
        "END\n"
    )
    program = parse(source)
    analyzer = check(program)
    assert analyzer.errors == []
    assert emit_il(program, analyzer)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("P1 broken( -> R0[:8.0] END", r"1:"),
        ("unknown = 8.0\nP1 f(V0[:missing]) -> R0[:8.0]\n V0 => R0\nEND", "undefined type missing"),
        ("int = 8.0\nint = 4.0\nP1 f() -> R0[:int]\n 0 => R0\nEND", "duplicate type definition int"),
        ("P1 f() -> R0[:8.0]\n 0 => R0\nEND\nP1 g() -> R0[:8.0]\n 0 => R0\nEND", "duplicate program definition P1"),
        ("P1 f(V0[:8.0]) -> R0[:8.0]\n V0 -> 0 => R0\nEND", "guard condition must be 0"),
        ("pair = (8.0, 8.0)\nP1 f() -> R0[:8.0]\n 0 => Z0[2:pair]\n Z0[2:pair] => R0\nEND", "record field index 2 out of range"),
        ("P1 f() -> R0[:8.0]\n 1 => C0[:8.0]\n 2 => C0\n C0 => R0\nEND", "constant C0 has already been assigned"),
    ],
)
def test_invalid_programs_are_rejected(source: str, message: str):
    with pytest.raises(CompileError, match=message):
        analyze(source)
