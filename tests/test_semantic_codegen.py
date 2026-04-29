"""Tests for semantic analysis and CIL code generation."""

from __future__ import annotations

import pytest

from plankalkulsharp.compiler import CompileError, check, emit_il, parse
from plankalkulsharp.semantic.analyzer import (
    Analyzer,
    ResolvedBit,
    ResolvedBitSeq,
    ResolvedRecord,
    SemanticError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def analyze(source: str) -> Analyzer:
    program = parse(source)
    return check(program)


def compile_il(source: str) -> str:
    program = parse(source)
    analyzer = check(program)
    return emit_il(program, analyzer)


# ---------------------------------------------------------------------------
# Type resolution
# ---------------------------------------------------------------------------

class TestTypeResolution:
    def test_bit_type(self):
        a = analyze("P1 f (V0[:0]) -> R0[:0]\n  V0[:0] => R0[:0]\nEND")
        assert "P1" in a.programs
        assert a.programs["P1"].params == [ResolvedBit()]

    def test_bitseq_type(self):
        a = analyze("P1 f (V0[:8.0]) -> R0[:8.0]\n  V0[:8.0] => R0[:8.0]\nEND")
        assert a.programs["P1"].params == [ResolvedBitSeq(8)]

    def test_user_type(self):
        a = analyze(
            "A1 = S1.3\n"
            "P1 f (V0[: A1]) -> R0[: A1]\n"
            "  V0[: A1] => R0[: A1]\n"
            "END"
        )
        assert a.programs["P1"].params == [ResolvedBitSeq(3)]

    def test_array_of_bits_becomes_bitseq(self):
        a = analyze("P1 f (V0[:16.0]) -> R0[:16.0]\n  V0[:16.0] => R0[:16.0]\nEND")
        assert a.programs["P1"].params == [ResolvedBitSeq(16)]


# ---------------------------------------------------------------------------
# Semantic errors
# ---------------------------------------------------------------------------

class TestSemanticErrors:
    def test_undefined_type(self):
        with pytest.raises(CompileError):
            analyze("P1 f (V0[: A99]) -> R0[:0]\n  L => R0[:0]\nEND")

    def test_duplicate_type(self):
        with pytest.raises(CompileError):
            analyze(
                "A1 = S1.3\n"
                "A1 = S1.4\n"
                "P1 f () -> R0[:0]\n  L => R0[:0]\nEND"
            )

    def test_duplicate_program(self):
        with pytest.raises(CompileError):
            analyze(
                "P1 f () -> R0[:0]\n  L => R0[:0]\nEND\n"
                "P1 g () -> R0[:0]\n  L => R0[:0]\nEND"
            )

    def test_boolean_guard_required(self):
        with pytest.raises(CompileError):
            analyze(
                "P1 f (V0[:8.0]) -> R0[:8.0]\n"
                "  (V0[:8.0]) -> 0 => R0[:8.0]\n"
                "END"
            )


# ---------------------------------------------------------------------------
# CIL code generation
# ---------------------------------------------------------------------------

class TestCILGeneration:
    def test_basic_structure(self):
        il = compile_il("P1 f (V0[:8.0]) -> R0[:8.0]\n  V0[:8.0] => R0[:8.0]\nEND")
        assert ".assembly PlankalkulProgram" in il
        assert ".class public abstract sealed auto ansi PlankalkulProgram" in il
        assert ".method public hidebysig static int32 f(int32 V_0) cil managed" in il

    def test_assignment_codegen(self):
        il = compile_il("P1 f (V0[:8.0]) -> R0[:8.0]\n  V0[:8.0] => R0[:8.0]\nEND")
        assert "ldarg V_0" in il
        assert "stloc R_0" in il
        assert "ret" in il

    def test_arithmetic_codegen(self):
        il = compile_il(
            "P1 f (V0[:8.0], V1[:8.0]) -> R0[:8.0]\n"
            "  V0[:8.0] + V1[:8.0] => R0[:8.0]\n"
            "END"
        )
        assert "add" in il

    def test_comparison_codegen(self):
        il = compile_il(
            "P1 f (V0[:8.0], V1[:8.0]) -> R0[:0]\n"
            "  (V0[:8.0] < V1[:8.0]) -> L => R0[:0]\n"
            "END"
        )
        assert "clt" in il

    def test_guarded_codegen(self):
        il = compile_il(
            "P1 f (V0[:8.0], V1[:8.0]) -> R0[:8.0]\n"
            "  (V0[:8.0] < V1[:8.0]) -> V1[:8.0] => R0[:8.0]\n"
            "END"
        )
        assert "brfalse" in il

    def test_for_loop_codegen(self):
        il = compile_il(
            "P1 f (V0[:8.0]) -> R0[:8.0]\n"
            "  0 => Z0[:8.0]\n"
            "  FOR Z1[:8.0] FROM 0 TO V0[:8.0] {\n"
            "    Z0[:8.0] + Z1[:8.0] => Z0[:8.0]\n"
            "  }\n"
            "  Z0[:8.0] => R0[:8.0]\n"
            "END"
        )
        assert "FTOP" in il
        assert "FEND" in il
        assert "bgt" in il

    def test_w_loop_codegen(self):
        il = compile_il(
            "P1 f (V0[:8.0]) -> R0[:8.0]\n"
            "  0 => Z0[:8.0]\n"
            "  W {\n"
            "    (Z0[:8.0] < V0[:8.0]) -> Z0[:8.0] + 1 => Z0[:8.0]\n"
            "  }\n"
            "  Z0[:8.0] => R0[:8.0]\n"
            "END"
        )
        assert "WTOP" in il
        assert "brtrue" in il

    def test_main_entry_point(self):
        il = compile_il("P1 f (V0[:8.0]) -> R0[:8.0]\n  V0[:8.0] => R0[:8.0]\nEND")
        assert ".entrypoint" in il
        assert "Main" in il
        assert "Int32::Parse" in il

    def test_func_call_codegen(self):
        il = compile_il(
            "P1 max (V0[:8.0], V1[:8.0]) -> R0[:8.0]\n"
            "  V0[:8.0] => R0[:8.0]\n"
            "END\n"
            "P2 test (V0[:8.0]) -> R0[:8.0]\n"
            "  max(V0[:8.0], 0) => R0[:8.0]\n"
            "END"
        )
        assert "call int32 PlankalkulProgram::max(int32, int32)" in il


# ---------------------------------------------------------------------------
# Record type resolution
# ---------------------------------------------------------------------------

class TestRecordTypeResolution:
    def test_record_type_resolved(self):
        a = analyze(
            "A1 = (S1.8, S1.8)\n"
            "P1 f (V0[: A1]) -> R0[:8.0]\n"
            "  V0[0 : A1] => R0[:8.0]\n"
            "END"
        )
        assert a.programs["P1"].params == [ResolvedRecord((ResolvedBitSeq(8), ResolvedBitSeq(8)))]

    def test_record_field_access_type(self):
        """Accessing .0 of (S1.8, S1.8) should yield S1.8."""
        a = analyze(
            "A1 = (S1.8, S1.8)\n"
            "P1 f (V0[: A1]) -> R0[:8.0]\n"
            "  V0[0 : A1] => R0[:8.0]\n"
            "END"
        )
        # If it analyzed without errors, the field access type was compatible
        assert len(a.errors) == 0

    def test_record_field_out_of_range(self):
        with pytest.raises(CompileError):
            analyze(
                "A1 = (S1.8, S1.8)\n"
                "P1 f (V0[: A1]) -> R0[:8.0]\n"
                "  V0[5 : A1] => R0[:8.0]\n"
                "END"
            )


# ---------------------------------------------------------------------------
# C-variable immutability
# ---------------------------------------------------------------------------

class TestCVariableImmutability:
    def test_single_c_assignment_ok(self):
        """C-variable assigned once should be fine."""
        a = analyze(
            "P1 f () -> R0[:8.0]\n"
            "  10 => C0[:8.0]\n"
            "  C0[:8.0] => R0[:8.0]\n"
            "END"
        )
        assert len(a.errors) == 0

    def test_reassign_c_variable_error(self):
        """C-variable assigned twice should raise an error."""
        with pytest.raises(CompileError):
            analyze(
                "P1 f () -> R0[:8.0]\n"
                "  10 => C0[:8.0]\n"
                "  20 => C0[:8.0]\n"
                "  C0[:8.0] => R0[:8.0]\n"
                "END"
            )

    def test_different_c_variables_ok(self):
        """Different C-variables can each be assigned once."""
        a = analyze(
            "P1 f () -> R0[:8.0]\n"
            "  10 => C0[:8.0]\n"
            "  20 => C1[:8.0]\n"
            "  C0[:8.0] + C1[:8.0] => R0[:8.0]\n"
            "END"
        )
        assert len(a.errors) == 0


# ---------------------------------------------------------------------------
# Multi-return type inference
# ---------------------------------------------------------------------------

class TestMultiReturnTypes:
    def test_multi_result_call_returns_record(self):
        """Calling a multi-result function should yield a ResolvedRecord."""
        a = analyze(
            "A1 = (S1.8, S1.8)\n"
            "P1 swap (V0[:8.0], V1[:8.0]) -> (R0[:8.0], R1[:8.0])\n"
            "  V1[:8.0] => R0[:8.0]\n"
            "  V0[:8.0] => R1[:8.0]\n"
            "END\n"
            "P2 test (V0[:8.0], V1[:8.0]) -> R0[:8.0]\n"
            "  swap(V0[:8.0], V1[:8.0]) => Z0[: A1]\n"
            "  Z0[0 : A1] => R0[:8.0]\n"
            "END"
        )
        assert len(a.errors) == 0

    def test_multi_result_program_has_two_results(self):
        a = analyze(
            "P1 swap (V0[:8.0], V1[:8.0]) -> (R0[:8.0], R1[:8.0])\n"
            "  V1[:8.0] => R0[:8.0]\n"
            "  V0[:8.0] => R1[:8.0]\n"
            "END"
        )
        assert len(a.programs["P1"].results) == 2

    def test_multi_return_codegen(self):
        il = compile_il(
            "P1 swap (V0[:8.0], V1[:8.0]) -> (R0[:8.0], R1[:8.0])\n"
            "  V1[:8.0] => R0[:8.0]\n"
            "  V0[:8.0] => R1[:8.0]\n"
            "END"
        )
        assert "valuetype Rec_" in il
        assert "stfld" in il


# ---------------------------------------------------------------------------
# Cross-program R<N>
# ---------------------------------------------------------------------------

class TestCrossProgramR:
    def test_cross_program_ref_resolves(self):
        a = analyze(
            "P1 pi () -> R0[:8.0]\n"
            "  3 => R0[:8.0]\n"
            "END\n"
            "P2 two_pi () -> R0[:8.0]\n"
            "  R1[:8.0] * 2 => R0[:8.0]\n"
            "END"
        )
        assert len(a.errors) == 0

    def test_cross_program_codegen(self):
        il = compile_il(
            "P1 pi () -> R0[:8.0]\n"
            "  3 => R0[:8.0]\n"
            "END\n"
            "P2 two_pi () -> R0[:8.0]\n"
            "  R1[:8.0] * 2 => R0[:8.0]\n"
            "END"
        )
        assert "call int32 PlankalkulProgram::pi()" in il

    def test_self_reference_not_cross_program(self):
        """R1 in P1 should NOT trigger cross-program to P1 itself."""
        a = analyze(
            "P1 f () -> (R0[:8.0], R1[:8.0])\n"
            "  10 => R0[:8.0]\n"
            "  20 => R1[:8.0]\n"
            "END"
        )
        assert len(a.errors) == 0
