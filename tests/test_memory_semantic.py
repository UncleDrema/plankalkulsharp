from __future__ import annotations

import pytest

from plankalkulsharp.compiler import CompileError, check, parse
from plankalkulsharp.semantic.analyzer import ResolvedRef
from plankalkulsharp.semantic.layout import heap_layout


def analyze(source: str):
    return check(parse(source))


def test_recursive_reference_type_allocation_nil_and_dereference():
    analyzer = analyze(
        "int = 8.0\n"
        "node = (int, @node)\n"
        "P1(V0[:int]) -> R0[:int]\n"
        "  @node => Z0\n"
        "  NIL => Z2[:@node]\n"
        "  7 => Z0[@.0]\n"
        "  NIL => Z0[@.1]\n"
        "  Z0 => Z1\n"
        "  Z1[@.0] => R0\n"
        "  Z0 => @\n"
        "END\n"
    )
    assert analyzer.type_defs["node"].fields[1] == ResolvedRef("node")
    assert analyzer.heap_types["node"] == analyzer.type_defs["node"]
    assert heap_layout(analyzer.heap_types["node"]).offsets == (0, 8)


def test_mutual_references_aliases_are_nominal_and_clr_arrays_can_hold_refs():
    analyzer = analyze(
        "a = (@b, 8.0)\n"
        "b = (@a, 8.0)\n"
        "alias = a\n"
        "left = (8.0, 8.0)\n"
        "right = (8.0, 8.0)\n"
        "refs = 2x@a\n"
        "P0() -> R0[:0]\n 0 => R0\nEND\n"
        "P1(V0[:@alias], V1[:@left], V2[:@right]) -> R0[:0]\n"
        "  V0 => Z0[:@a]\n"
        "  NIL => Z1[0:refs]\n"
        "  Z0 = Z1[0] => R0\n"
        "END\n"
    )
    assert analyzer.canonical_names["alias"] == "a"
    assert analyzer.heap_types["a"] == analyzer.type_defs["a"]
    assert analyzer.heap_types["b"] == analyzer.type_defs["b"]

    with pytest.raises(CompileError, match="type mismatch"):
        analyze(
            "left = (8.0, 8.0)\nright = (8.0, 8.0)\n"
            "P0() -> R0[:8.0]\n0 => R0\nEND\n"
            "P1(V0[:@left]) -> R0[:@right]\n V0 => R0\nEND"
        )


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("a = (b, 8.0)\nb = (a, 8.0)\nP1() -> R0[:8.0]\n0 => R0\nEND", "recursive type by value"),
        ("wide = 65.0\nP1() -> R0[:8.0]\n@wide => Z0\n0 => R0\nEND", "outside 1..64"),
        ("bag = (2 x 8.0, 8.0)\nP1() -> R0[:8.0]\n@bag => Z0\n0 => R0\nEND", "arrays cannot be stored"),
        ("node = 8.0\nP1() -> R0[:8.0]\n@node => Z0\n-Z0 => R0\nEND", "NEG requires"),
        ("node = 8.0\nP1() -> R0[:8.0]\nNIL + 1 => R0\nEND", "arithmetic operator requires"),
        ("node = (8.0, @node)\nP1() -> R0[:8.0]\n@node => Z0\nZ0[@.0.0] => R0\nEND", "bit components"),
        ("node = (8.0, @node)\nP1() -> R0[:8.0]\n@node => Z0\nZ0[@.(0)] => R0\nEND", "dynamic components"),
        ("node = 8.0\nP5(V0[:@node]) -> R0[:8.0]\n0 => R0\nEND", "entry program cannot expose references"),
    ],
)
def test_rejected_heap_types_and_operations(source: str, message: str):
    with pytest.raises(CompileError, match=message):
        analyze(source)


def test_nil_needs_annotation_and_deref_of_freed_copy_is_rejected():
    with pytest.raises(CompileError, match="NIL needs"):
        analyze("node = 8.0\nP1() -> R0[:8.0]\nNIL => Z0\n0 => R0\nEND")
    with pytest.raises(CompileError, match="reference has been freed"):
        analyze(
            "node = (8.0, @node)\nP1() -> R0[:8.0]\n"
            "@node => Z0\nZ0 => Z1\nZ0 => @\nZ1[@.0] => R0\nEND"
        )
    with pytest.raises(CompileError, match="reference has been freed"):
        analyze(
            "node = (8.0, @node)\nP1() -> R0[:8.0]\n"
            "@node => Z0\nZ0 => Z1\nZ0 => @\n0 => Z1[@.0]\n0 => R0\nEND"
        )


def test_liveness_is_conservative_across_guards_loops_and_calls():
    analyze(
        "node = (8.0, @node)\n"
        "P0() -> R0[:8.0]\n 0 => R0\nEND\n"
        "P1 destroy(V0[:@node]) -> R0[:8.0]\n V0 => @\n 0 => R0\nEND\n"
        "P2() -> R0[:8.0]\n"
        "@node => Z0\n"
        "L -> Z0 => @\n"
        "W { Z0 => @ }\n"
        "destroy(Z0) => Z1\n"
        "Z0[@.0] => R0\nEND"
    )


def test_liveness_allows_overwrite_and_forgetful_control_flow_and_nil_free():
    analyze(
        "node = (8.0, @node)\n"
        "P1() -> R0[:8.0]\n"
        "@node => Z0\n"
        "Z0 => @\n"
        "@node => Z0\n"
        "NIL => Z1[:@node]\n"
        "Z1 => @\n"
        "L -> { @node => Z0 }\n"
        "W { @node => Z0 }\n"
        "Z0[@.0] => R0\nEND"
    )


def test_reference_types_used_only_by_helper_signatures_still_get_heap_metadata():
    analyzer = analyze(
        "int = 32.0\n"
        "P0() -> R0[:int]\n0 => R0\nEND\n"
        "P1 unused(V0[:@int]) -> R0[:int]\nV0 => @\n0 => R0\nEND"
    )
    assert analyzer.heap_types["int"] == analyzer.type_defs["int"]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("node = (8.0, node)\nP1() -> R0[:8.0]\n 0 => R0\nEND", "recursive type by value"),
        ("node = 8.0\nP1() -> R0[:8.0]\n NIL => Z0\n 0 => R0\nEND", "NIL needs"),
        ("node = 8.0\nP1() -> R0[:8.0]\n @node => Z0\n Z0 => @\n Z0 => @\n 0 => R0\nEND", "already been freed"),
        ("node = 8.0\nP1() -> R0[:8.0]\n @node => Z0\n Z0 + 1 => R0\nEND", "arithmetic operator requires"),
    ],
)
def test_memory_semantic_errors(source: str, message: str):
    with pytest.raises(CompileError, match=message):
        analyze(source)
