"""Tests for the Plankalkül parser and AST builder."""

from __future__ import annotations

from pathlib import Path

import pytest

from plankalkulsharp.plankalkul_ast.nodes import (
    ArrayType,
    Assignment,
    BinOp,
    BinaryExpr,
    BitSeqType,
    BitType,
    BoolLiteral,
    DynamicAccess,
    ForLoop,
    FuncCall,
    GuardedStmt,
    IntLiteral,
    Program,
    ProgramDef,
    RecordType,
    StaticAccess,
    TypeDef,
    UserType,
    VarRef,
    WLoop,
)
from plankalkulsharp.compiler import CompileError, parse

PROGRAMS_DIR = Path(__file__).parent / "programs"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def parse_file(name: str) -> Program:
    source = (PROGRAMS_DIR / name).read_text(encoding="utf-8")
    return parse(source, filename=name)


# ---------------------------------------------------------------------------
# Parsing test programs
# ---------------------------------------------------------------------------

class TestParsePrograms:
    """Test that all example .pk files parse without errors."""

    def test_max(self):
        ast = parse_file("max.pk")
        assert len(ast.program_defs) == 1
        p = ast.program_defs[0]
        assert p.number == 1
        assert p.name == "max"
        assert len(p.params) == 2
        assert len(p.results) == 1
        assert len(p.body) == 3

    def test_max3(self):
        ast = parse_file("max3.pk")
        assert len(ast.type_defs) == 3
        assert len(ast.program_defs) == 2

    def test_arithmetic(self):
        ast = parse_file("arithmetic.pk")
        p = ast.program_defs[0]
        assert p.name == "arithmetic"
        assert len(p.body) == 3

    def test_loop(self):
        ast = parse_file("loop.pk")
        p = ast.program_defs[0]
        assert p.name == "count"
        # body: assignment, W-loop, assignment
        assert len(p.body) == 3
        assert isinstance(p.body[1], WLoop)

    def test_forloop(self):
        ast = parse_file("forloop.pk")
        p = ast.program_defs[0]
        assert len(p.body) == 3
        assert isinstance(p.body[1], ForLoop)

    def test_guard_block(self):
        ast = parse_file("guard_block.pk")
        p = ast.program_defs[0]
        # body: assignment, guarded block, assignment
        assert len(p.body) == 3
        assert isinstance(p.body[1], GuardedStmt)


# ---------------------------------------------------------------------------
# Type definitions
# ---------------------------------------------------------------------------

class TestTypeDefs:
    def test_bit_seq_type(self):
        ast = parse_file("max3.pk")
        # A1 = S1.3
        td = ast.type_defs[0]
        assert td.index == 1
        assert isinstance(td.type_expr, BitSeqType)
        assert td.type_expr.length == 3

    def test_array_type(self):
        ast = parse_file("max3.pk")
        # A2 = 2 x A1
        td = ast.type_defs[1]
        assert td.index == 2
        assert isinstance(td.type_expr, ArrayType)
        assert td.type_expr.size == 2
        assert isinstance(td.type_expr.element_type, UserType)
        assert td.type_expr.element_type.index == 1

    def test_another_bit_seq(self):
        ast = parse_file("max3.pk")
        # A3 = S1.4
        td = ast.type_defs[2]
        assert td.index == 3
        assert isinstance(td.type_expr, BitSeqType)
        assert td.type_expr.length == 4


# ---------------------------------------------------------------------------
# Inline parsing
# ---------------------------------------------------------------------------

class TestInlineParsing:
    def test_simple_assignment(self):
        ast = parse("P1 f (V0[:8.0]) -> R0[:8.0]\n  V0[:8.0] => R0[:8.0]\nEND")
        p = ast.program_defs[0]
        assert len(p.body) == 1
        stmt = p.body[0]
        assert isinstance(stmt, Assignment)
        assert isinstance(stmt.value, VarRef)
        assert stmt.value.kind == "V"
        assert stmt.value.index == 0
        assert isinstance(stmt.target, VarRef)
        assert stmt.target.kind == "R"

    def test_binary_expression(self):
        ast = parse("P1 f (V0[:8.0], V1[:8.0]) -> R0[:8.0]\n  V0[:8.0] + V1[:8.0] => R0[:8.0]\nEND")
        stmt = ast.program_defs[0].body[0]
        assert isinstance(stmt, Assignment)
        assert isinstance(stmt.value, BinaryExpr)
        assert stmt.value.op == BinOp.ADD

    def test_guarded_statement(self):
        ast = parse(
            "P1 f (V0[:8.0], V1[:8.0]) -> R0[:8.0]\n"
            "  (V0[:8.0] < V1[:8.0]) -> V1[:8.0] => R0[:8.0]\n"
            "END"
        )
        stmt = ast.program_defs[0].body[0]
        assert isinstance(stmt, GuardedStmt)
        assert isinstance(stmt.condition, BinaryExpr)
        assert stmt.condition.op == BinOp.LT
        assert len(stmt.body) == 1
        assert isinstance(stmt.body[0], Assignment)

    def test_func_call(self):
        ast = parse(
            "P1 f (V0[:8.0]) -> R0[:8.0]\n"
            "  max(V0[:8.0], 5) => R0[:8.0]\n"
            "END"
        )
        stmt = ast.program_defs[0].body[0]
        assert isinstance(stmt, Assignment)
        assert isinstance(stmt.value, FuncCall)
        assert stmt.value.name == "max"
        assert len(stmt.value.args) == 2

    def test_bool_literal(self):
        ast = parse("P1 f () -> R0[:0]\n  L => R0[:0]\nEND")
        stmt = ast.program_defs[0].body[0]
        assert isinstance(stmt, Assignment)
        assert isinstance(stmt.value, BoolLiteral)
        assert stmt.value.value is True

    def test_type_annotation_bit(self):
        ast = parse("P1 f (V0[:0]) -> R0[:0]\n  V0[:0] => R0[:0]\nEND")
        p = ast.program_defs[0]
        assert isinstance(p.params[0].type_ann, BitType)

    def test_type_annotation_array(self):
        ast = parse("P1 f (V0[:8.0]) -> R0[:8.0]\n  V0[:8.0] => R0[:8.0]\nEND")
        p = ast.program_defs[0]
        ta = p.params[0].type_ann
        assert isinstance(ta, ArrayType)
        assert ta.size == 8
        assert isinstance(ta.element_type, BitType)

    def test_empty_params(self):
        ast = parse("P1 f () -> R0[:8.0]\n  42 => R0[:8.0]\nEND")
        p = ast.program_defs[0]
        assert len(p.params) == 0

    def test_program_call(self):
        ast = parse(
            "P1 f (V0[:8.0]) -> R0[:8.0]\n"
            "  P1(V0[:8.0]) => R0[:8.0]\n"
            "END"
        )
        stmt = ast.program_defs[0].body[0]
        assert isinstance(stmt, Assignment)
        assert isinstance(stmt.value, FuncCall)
        assert stmt.value.name == "P1"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrors:
    def test_syntax_error(self):
        with pytest.raises(CompileError) as exc_info:
            parse("P1 f (V0[:8.0]) -> R0[:8.0]\n  V0 => \nEND")
        assert len(exc_info.value.errors) > 0

    def test_missing_end(self):
        with pytest.raises(CompileError):
            parse("P1 f (V0[:8.0]) -> R0[:8.0]\n  V0[:8.0] => R0[:8.0]\n")


# ---------------------------------------------------------------------------
# Record types and component access
# ---------------------------------------------------------------------------

class TestRecordParsing:
    def test_record_type_def(self):
        ast = parse("A1 = (S1.8, S1.8)\nP1 f () -> R0[:8.0]\n  0 => R0[:8.0]\nEND")
        td = ast.type_defs[0]
        assert isinstance(td.type_expr, RecordType)
        assert len(td.type_expr.fields) == 2
        assert isinstance(td.type_expr.fields[0], BitSeqType)

    def test_static_component_access(self):
        ast = parse(
            "A1 = (S1.8, S1.8)\n"
            "P1 f () -> R0[:8.0]\n"
            "  42 => Z0[0 : A1]\n"
            "  Z0[0 : A1] => R0[:8.0]\n"
            "END"
        )
        stmt = ast.program_defs[0].body[0]
        assert isinstance(stmt, Assignment)
        assert isinstance(stmt.target.components[0], StaticAccess)
        assert stmt.target.components[0].index == 0

    def test_dynamic_component_access(self):
        ast = parse(
            "P1 f (V0[:8.0]) -> R0[:8.0]\n"
            "  42 => Z0[V0 : 10.8.0]\n"
            "  Z0[V0 : 10.8.0] => R0[:8.0]\n"
            "END"
        )
        stmt = ast.program_defs[0].body[0]
        assert isinstance(stmt.target.components[0], DynamicAccess)

    def test_records_pk_parses(self):
        ast = parse_file("records.pk")
        assert len(ast.type_defs) == 1
        assert isinstance(ast.type_defs[0].type_expr, RecordType)
        p = ast.program_defs[0]
        assert p.name == "swap_pair"

    def test_complex_udt_pk_parses(self):
        ast = parse_file("complex_udt.pk")
        assert len(ast.type_defs) == 3
        p = ast.program_defs[0]
        assert p.name == "nested_access"
        assert len(p.body) == 7


# ---------------------------------------------------------------------------
# C-variables
# ---------------------------------------------------------------------------

class TestConstantsParsing:
    def test_c_variable(self):
        ast = parse(
            "P1 f () -> R0[:8.0]\n"
            "  42 => C0[:8.0]\n"
            "  C0[:8.0] => R0[:8.0]\n"
            "END"
        )
        stmt0 = ast.program_defs[0].body[0]
        assert isinstance(stmt0, Assignment)
        assert stmt0.target.kind == "C"
        assert stmt0.target.index == 0

    def test_constants_pk_parses(self):
        ast = parse_file("constants.pk")
        p = ast.program_defs[0]
        assert p.name == "use_const"
        assert len(p.body) == 3


# ---------------------------------------------------------------------------
# Subprograms
# ---------------------------------------------------------------------------

class TestSubprogramParsing:
    def test_subprogram_id(self):
        ast = parse(
            "P1.1 helper (V0[:8.0]) -> R0[:8.0]\n"
            "  V0[:8.0] * 2 => R0[:8.0]\n"
            "END"
        )
        p = ast.program_defs[0]
        assert p.number == 1
        assert p.sub_number == 1
        assert p.name == "helper"

    def test_subprograms_pk_parses(self):
        ast = parse_file("subprograms.pk")
        assert len(ast.program_defs) == 2
        assert ast.program_defs[0].sub_number == 1
        assert ast.program_defs[1].sub_number is None


# ---------------------------------------------------------------------------
# Nested guards
# ---------------------------------------------------------------------------

class TestNestedGuardsParsing:
    def test_nested_guard(self):
        ast = parse(
            "P1 f (V0[:8.0], V1[:8.0]) -> R0[:8.0]\n"
            "  (V0[:8.0] > 0) -> (V1[:8.0] > 0) -> V0[:8.0] + V1[:8.0] => R0[:8.0]\n"
            "END"
        )
        stmt = ast.program_defs[0].body[0]
        assert isinstance(stmt, GuardedStmt)
        inner = stmt.body[0]
        assert isinstance(inner, GuardedStmt)  # nested guard
        assert len(inner.body) == 1
        assert isinstance(inner.body[0], Assignment)
