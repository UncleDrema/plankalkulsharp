"""Tests that verify the generated CIL (.il) assembly for each test program.

These tests compile each .pk test program through the full pipeline
(parse → semantic analysis → codegen) and verify the IL output structure,
instruction sequences, method signatures, and control flow.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from plankalkulsharp.compiler import check, emit_il, parse

PROGRAMS_DIR = Path(__file__).parent / "programs"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compile_file_to_il(name: str) -> str:
    """Parse + check + emit IL for a test program file."""
    source = (PROGRAMS_DIR / name).read_text(encoding="utf-8")
    program = parse(source, filename=name)
    analyzer = check(program, filename=name)
    return emit_il(program, analyzer)


def compile_source_to_il(source: str) -> str:
    """Parse + check + emit IL for inline source code."""
    program = parse(source)
    analyzer = check(program)
    return emit_il(program, analyzer)


def extract_method(il: str, method_name: str) -> str:
    """Extract the body of a single .method block from IL text."""
    pattern = rf"\.method\b[^\n]*\b{re.escape(method_name)}\b[^\n]*\n\s*\{{"
    m = re.search(pattern, il)
    if m is None:
        pytest.fail(f"Method '{method_name}' not found in IL:\n{il}")
    start = m.start()
    # Find matching closing brace
    depth = 0
    i = m.end() - 1  # position of '{'
    for i in range(m.end() - 1, len(il)):
        if il[i] == "{":
            depth += 1
        elif il[i] == "}":
            depth -= 1
            if depth == 0:
                return il[start : i + 1]
    pytest.fail(f"Unmatched brace for method '{method_name}'")
    return ""


def il_instructions(method_body: str) -> list[str]:
    """Return a flat list of non-empty instruction lines from a method body."""
    lines = []
    for line in method_body.splitlines():
        stripped = line.strip()
        # Skip directives, labels, braces, comments
        if not stripped or stripped.startswith((".", "{", "}", "//")):
            continue
        lines.append(stripped)
    return lines


# ---------------------------------------------------------------------------
# Assembly structure
# ---------------------------------------------------------------------------

class TestILAssemblyStructure:
    """Test the overall IL assembly structure."""

    def test_assembly_header(self):
        il = compile_file_to_il("max.pk")
        assert ".assembly extern System.Runtime { }" in il
        assert ".assembly extern System.Console { }" in il
        assert ".assembly PlankalkulProgram { }" in il
        assert ".module PlankalkulProgram.dll" in il

    def test_class_wrapper(self):
        il = compile_file_to_il("max.pk")
        assert ".class public abstract sealed auto ansi PlankalkulProgram" in il

    def test_entrypoint_present(self):
        il = compile_file_to_il("max.pk")
        main = extract_method(il, "Main")
        assert ".entrypoint" in main

    def test_single_program_single_method(self):
        il = compile_file_to_il("max.pk")
        # Should have exactly 2 methods: max + Main
        method_count = il.count(".method ")
        assert method_count == 2, f"Expected 2 methods, got {method_count}"

    def test_multi_program_multiple_methods(self):
        il = compile_file_to_il("max3.pk")
        # max, max3, Main
        method_count = il.count(".method ")
        assert method_count == 3, f"Expected 3 methods, got {method_count}"


# ---------------------------------------------------------------------------
# max.pk — method signature and body
# ---------------------------------------------------------------------------

class TestILMaxProgram:
    """Verify IL generated for max.pk: max(V0, V1) -> R0."""

    @pytest.fixture()
    def il(self):
        return compile_file_to_il("max.pk")

    def test_method_signature(self, il):
        assert ".method public hidebysig static int32 max(int32 V_0, int32 V_1) cil managed" in il

    def test_locals_declared(self, il):
        method = extract_method(il, "max")
        assert ".locals init (" in method
        assert "int32 R_0" in method
        assert "int32 Z_1" in method

    def test_initial_assignment(self, il):
        """V0 -> Z1: load V0, store to Z1."""
        method = extract_method(il, "max")
        instrs = il_instructions(method)
        # First instructions should be: ldarg V_0, stloc Z_1
        assert "ldarg V_0" in instrs
        assert "stloc Z_1" in instrs
        v0_idx = instrs.index("ldarg V_0")
        z1_idx = instrs.index("stloc Z_1")
        assert z1_idx == v0_idx + 1

    def test_guard_comparison(self, il):
        """(Z1 < V1) -> ... should emit clt + brfalse."""
        method = extract_method(il, "max")
        instrs = il_instructions(method)
        assert "clt" in instrs
        # There must be a brfalse to skip the guarded body
        brfalse_instrs = [i for i in instrs if i.startswith("brfalse")]
        assert len(brfalse_instrs) == 1

    def test_guarded_body(self, il):
        """Inside the guard: V1 -> Z1."""
        method = extract_method(il, "max")
        instrs = il_instructions(method)
        clt_idx = instrs.index("clt")
        # After guard: ldarg V_1, stloc Z_1
        remaining = instrs[clt_idx:]
        assert "ldarg V_1" in remaining
        assert "stloc Z_1" in remaining

    def test_final_assignment_and_return(self, il):
        """Z1 -> R0, then ldloc R_0 + ret."""
        method = extract_method(il, "max")
        instrs = il_instructions(method)
        # Last instructions should be: ldloc Z_1, stloc R_0, ldloc R_0, ret
        assert instrs[-1] == "ret"
        assert instrs[-2] == "ldloc R_0"

    def test_main_calls_max(self, il):
        main = extract_method(il, "Main")
        assert "call int32 PlankalkulProgram::max(int32, int32)" in main
        # Main should parse CLI args
        assert "Int32::Parse" in main


# ---------------------------------------------------------------------------
# arithmetic.pk — arithmetic operations
# ---------------------------------------------------------------------------

class TestILArithmetic:
    """Verify IL generated for arithmetic.pk: add, mul, sub."""

    @pytest.fixture()
    def il(self):
        return compile_file_to_il("arithmetic.pk")

    def test_method_signature(self, il):
        assert "int32 arithmetic(int32 V_0, int32 V_1)" in il

    def test_add_instruction(self, il):
        method = extract_method(il, "arithmetic")
        instrs = il_instructions(method)
        assert "add" in instrs

    def test_mul_instruction(self, il):
        method = extract_method(il, "arithmetic")
        instrs = il_instructions(method)
        assert "mul" in instrs

    def test_sub_instruction(self, il):
        method = extract_method(il, "arithmetic")
        instrs = il_instructions(method)
        assert "sub" in instrs

    def test_constant_2(self, il):
        """The expression * 2 should push 2."""
        method = extract_method(il, "arithmetic")
        assert "ldc.i4 2" in method

    def test_constant_1(self, il):
        """The expression - 1 should push 1."""
        method = extract_method(il, "arithmetic")
        assert "ldc.i4 1" in method

    def test_three_locals(self, il):
        """Z0, Z1, R0 should all be declared."""
        method = extract_method(il, "arithmetic")
        assert "Z_0" in method
        assert "Z_1" in method
        assert "R_0" in method

    def test_instruction_order(self, il):
        """The operations must be in order: add, mul, sub."""
        method = extract_method(il, "arithmetic")
        instrs = il_instructions(method)
        add_idx = instrs.index("add")
        mul_idx = instrs.index("mul")
        sub_idx = instrs.index("sub")
        assert add_idx < mul_idx < sub_idx


# ---------------------------------------------------------------------------
# forloop.pk — FOR loop
# ---------------------------------------------------------------------------

class TestILForLoop:
    """Verify IL generated for forloop.pk: sum of 0..n."""

    @pytest.fixture()
    def il(self):
        return compile_file_to_il("forloop.pk")

    def test_method_signature(self, il):
        assert "int32 sum_to(int32 V_0)" in il

    def test_loop_labels(self, il):
        method = extract_method(il, "sum_to")
        # Must have FTOP and FEND labels
        assert re.search(r"FTOP_\d+:", method)
        assert re.search(r"FEND_\d+:", method)

    def test_loop_init(self, il):
        """Loop var Z1 should be initialized from 0."""
        method = extract_method(il, "sum_to")
        instrs = il_instructions(method)
        # Sequence: ldc.i4 0, stloc Z_1 (init Z1 = 0)
        assert "stloc Z_1" in instrs

    def test_loop_condition(self, il):
        """Check: Z1 > V0 → bgt FEND."""
        method = extract_method(il, "sum_to")
        instrs = il_instructions(method)
        bgt_instrs = [i for i in instrs if i.startswith("bgt")]
        assert len(bgt_instrs) >= 1

    def test_loop_increment(self, il):
        """Loop variable should be incremented: ldloc Z_1, ldc.i4.1, add, stloc Z_1."""
        method = extract_method(il, "sum_to")
        instrs = il_instructions(method)
        # There should be ldc.i4.1, add near the end of the loop
        assert "ldc.i4.1" in instrs
        # There should be a br back to the top
        br_instrs = [i for i in instrs if i.startswith("br ")]
        assert len(br_instrs) >= 1

    def test_accumulator_add(self, il):
        """Body: Z0 + Z1 → Z0 should emit add."""
        method = extract_method(il, "sum_to")
        instrs = il_instructions(method)
        assert "add" in instrs


# ---------------------------------------------------------------------------
# loop.pk — W-loop
# ---------------------------------------------------------------------------

class TestILWLoop:
    """Verify IL generated for loop.pk: count up to 10."""

    @pytest.fixture()
    def il(self):
        return compile_file_to_il("loop.pk")

    def test_method_signature(self, il):
        """count() has no params."""
        assert "int32 count() cil managed" in il

    def test_w_loop_structure(self, il):
        method = extract_method(il, "count")
        # WTOP label for loop start
        assert re.search(r"WTOP_\d+:", method)
        # brtrue back to top (at least one guard fires → continue)
        instrs = il_instructions(method)
        brtrue_instrs = [i for i in instrs if i.startswith("brtrue")]
        assert len(brtrue_instrs) >= 1

    def test_guard_in_w_loop(self, il):
        """The guard (Z0 < 10) should emit clt + brfalse."""
        method = extract_method(il, "count")
        instrs = il_instructions(method)
        assert "clt" in instrs
        brfalse_instrs = [i for i in instrs if i.startswith("brfalse")]
        assert len(brfalse_instrs) >= 1

    def test_constant_10(self, il):
        """The comparison < 10 should push 10."""
        method = extract_method(il, "count")
        assert "ldc.i4 10" in method

    def test_increment(self, il):
        """Z0 + 1 should appear as add instruction."""
        method = extract_method(il, "count")
        instrs = il_instructions(method)
        assert "add" in instrs

    def test_flag_based_termination(self, il):
        """W-loop uses a flag: ldc.i4.0 (init), ldc.i4.1 (set), brtrue (check)."""
        method = extract_method(il, "count")
        instrs = il_instructions(method)
        assert "ldc.i4.0" in instrs
        assert "ldc.i4.1" in instrs


# ---------------------------------------------------------------------------
# guard_block.pk — guarded block (absolute value)
# ---------------------------------------------------------------------------

class TestILGuardBlock:
    """Verify IL generated for guard_block.pk: abs(x)."""

    @pytest.fixture()
    def il(self):
        return compile_file_to_il("guard_block.pk")

    def test_method_signature(self, il):
        assert "int32 abs(int32 V_0)" in il

    def test_guard_branch(self, il):
        method = extract_method(il, "abs")
        instrs = il_instructions(method)
        # (Z0 < 0) → clt + brfalse
        assert "clt" in instrs
        brfalse_instrs = [i for i in instrs if i.startswith("brfalse")]
        assert len(brfalse_instrs) == 1

    def test_negation_via_subtraction(self, il):
        """0 - Z0 should push 0, load Z0, sub."""
        method = extract_method(il, "abs")
        instrs = il_instructions(method)
        assert "sub" in instrs

    def test_guard_end_label(self, il):
        method = extract_method(il, "abs")
        assert re.search(r"GEND_\d+:", method)


# ---------------------------------------------------------------------------
# max3.pk — function calls between programs
# ---------------------------------------------------------------------------

class TestILMax3:
    """Verify IL generated for max3.pk: max3 calls max."""

    @pytest.fixture()
    def il(self):
        return compile_file_to_il("max3.pk")

    def test_max_method_present(self, il):
        assert "int32 max(int32 V_0, int32 V_1)" in il

    def test_max3_method_present(self, il):
        assert "int32 max3(int32 V_0, int32 V_1, int32 V_2)" in il

    def test_max3_calls_max(self, il):
        """max3 body should contain two calls to max."""
        method = extract_method(il, "max3")
        calls = re.findall(r"call int32 PlankalkulProgram::max\(int32, int32\)", method)
        assert len(calls) == 2

    def test_max3_uses_intermediate_z1(self, il):
        method = extract_method(il, "max3")
        assert "stloc Z_1" in method
        assert "ldloc Z_1" in method

    def test_main_calls_max_not_max3(self, il):
        """Main should call the first program (max), not max3."""
        main = extract_method(il, "Main")
        assert "call int32 PlankalkulProgram::max(int32, int32)" in main


# ---------------------------------------------------------------------------
# Inline source: edge cases in IL generation
# ---------------------------------------------------------------------------

class TestILEdgeCases:
    def test_bool_literal_true(self):
        il = compile_source_to_il("P1 f () -> R0[:0]\n  L => R0[:0]\nEND")
        method = extract_method(il, "f")
        assert "ldc.i4.1" in method  # true = 1

    def test_bool_literal_false(self):
        il = compile_source_to_il("P1 f () -> R0[:0]\n  0 => R0[:0]\nEND")
        method = extract_method(il, "f")
        assert "ldc.i4 0" in method or "ldc.i4.0" in method

    def test_return_type_bool(self):
        il = compile_source_to_il("P1 f () -> R0[:0]\n  L => R0[:0]\nEND")
        assert "bool f()" in il

    def test_not_operator(self):
        il = compile_source_to_il(
            "P1 f (V0[:0]) -> R0[:0]\n  ~V0[:0] => R0[:0]\nEND"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        # NOT = (x == 0)
        assert "ceq" in instrs

    def test_neq_operator(self):
        il = compile_source_to_il(
            "P1 f (V0[:8.0], V1[:8.0]) -> R0[:0]\n"
            "  (V0[:8.0] != V1[:8.0]) -> L => R0[:0]\n"
            "END"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        # NEQ = ceq + ldc.i4.0 + ceq
        ceq_count = instrs.count("ceq")
        assert ceq_count >= 2

    def test_le_operator(self):
        il = compile_source_to_il(
            "P1 f (V0[:8.0], V1[:8.0]) -> R0[:0]\n"
            "  (V0[:8.0] <= V1[:8.0]) -> L => R0[:0]\n"
            "END"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        # LE = cgt + ldc.i4.0 + ceq (i.e., NOT greater_than)
        assert "cgt" in instrs
        assert "ceq" in instrs

    def test_ge_operator(self):
        il = compile_source_to_il(
            "P1 f (V0[:8.0], V1[:8.0]) -> R0[:0]\n"
            "  (V0[:8.0] >= V1[:8.0]) -> L => R0[:0]\n"
            "END"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        # GE = clt + ldc.i4.0 + ceq (i.e., NOT less_than)
        assert "clt" in instrs
        assert "ceq" in instrs

    def test_neg_operator(self):
        il = compile_source_to_il(
            "P1 f (V0[:8.0]) -> R0[:8.0]\n  0 - V0[:8.0] => R0[:8.0]\nEND"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        assert "sub" in instrs

    def test_no_params_no_args_in_main(self):
        il = compile_source_to_il("P1 f () -> R0[:8.0]\n  42 => R0[:8.0]\nEND")
        main = extract_method(il, "Main")
        assert "call int32 PlankalkulProgram::f()" in main
        # No params → no Int32::Parse calls
        assert "Int32::Parse" not in main

    def test_maxstack_set(self):
        il = compile_source_to_il("P1 f () -> R0[:0]\n  L => R0[:0]\nEND")
        method = extract_method(il, "f")
        assert ".maxstack" in method


# ---------------------------------------------------------------------------
# Array operations
# ---------------------------------------------------------------------------

class TestILArrayOps:
    """Tests for array allocation, element load, and element store."""

    def test_array_local_newarr(self):
        il = compile_source_to_il(
            "P1 f (V0[:8.0]) -> R0[:8.0]\n"
            "  V0[:8.0] => Z0[0 : 10.8.0]\n"
            "  Z0[0 : 10.8.0] => R0[:8.0]\n"
            "END"
        )
        method = extract_method(il, "f")
        assert "int32[] Z_0" in method
        assert "newarr int32" in method

    def test_array_stelem(self):
        il = compile_source_to_il(
            "P1 f () -> R0[:8.0]\n"
            "  42 => Z0[0 : 5.8.0]\n"
            "  Z0[0 : 5.8.0] => R0[:8.0]\n"
            "END"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        assert "stelem.i4" in instrs

    def test_array_ldelem(self):
        il = compile_source_to_il(
            "P1 f () -> R0[:8.0]\n"
            "  7 => Z0[2 : 5.8.0]\n"
            "  Z0[2 : 5.8.0] => R0[:8.0]\n"
            "END"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        assert "ldelem.i4" in instrs

    def test_array_dynamic_index(self):
        il = compile_source_to_il(
            "P1 f (V0[:8.0]) -> R0[:8.0]\n"
            "  99 => Z0[V0 : 10.8.0]\n"
            "  Z0[V0 : 10.8.0] => R0[:8.0]\n"
            "END"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        # Dynamic index loads V0 (ldarg) before stelem/ldelem
        assert "ldarg V_0" in instrs
        assert "stelem.i4" in instrs
        assert "ldelem.i4" in instrs

    def test_two_parallel_arrays(self):
        il = compile_source_to_il(
            "P1 f () -> R0[:8.0]\n"
            "  10 => Z0[0 : 5.8.0]\n"
            "  20 => Z1[0 : 5.8.0]\n"
            "  Z0[0 : 5.8.0] + Z1[0 : 5.8.0] => R0[:8.0]\n"
            "END"
        )
        method = extract_method(il, "f")
        assert "int32[] Z_0" in method
        assert "int32[] Z_1" in method
        newarr_count = method.count("newarr int32")
        assert newarr_count == 2


# ---------------------------------------------------------------------------
# Reverse linked list program
# ---------------------------------------------------------------------------

class TestILReverseList:
    """Tests for the reverse_list.pk program (array of record nodes)."""

    def test_compiles(self):
        il = compile_file_to_il("reverse_list.pk")
        assert ".method" in il
        assert "reverse_list" in il

    def test_method_signature(self):
        il = compile_file_to_il("reverse_list.pk")
        method = extract_method(il, "reverse_list")
        assert "int32 V_0" in method
        assert "int32 V_1" in method
        assert "int32 R_0" in method

    def test_emits_struct_definition(self):
        il = compile_file_to_il("reverse_list.pk")
        assert "Rec_0" in il
        assert ".field public int32 f_0" in il
        assert ".field public int32 f_1" in il

    def test_allocates_record_array(self):
        il = compile_file_to_il("reverse_list.pk")
        method = extract_method(il, "reverse_list")
        assert "Rec_0[] Z_0" in method
        assert "newarr valuetype Rec_0" in method

    def test_has_for_loop(self):
        il = compile_file_to_il("reverse_list.pk")
        method = extract_method(il, "reverse_list")
        instrs = il_instructions(method)
        assert any("bgt" in i for i in instrs)

    def test_has_w_loop(self):
        il = compile_file_to_il("reverse_list.pk")
        method = extract_method(il, "reverse_list")
        instrs = il_instructions(method)
        assert any("brtrue" in i for i in instrs)

    def test_uses_ldelema_and_field_ops(self):
        il = compile_file_to_il("reverse_list.pk")
        method = extract_method(il, "reverse_list")
        instrs = il_instructions(method)
        assert any("ldelema" in i for i in instrs)
        assert any("ldfld" in i for i in instrs)
        assert any("stfld" in i for i in instrs)


# ---------------------------------------------------------------------------
# Records (isolated tests)
# ---------------------------------------------------------------------------

class TestILRecords:
    """Tests for records.pk — basic record field read/write."""

    def test_compiles(self):
        il = compile_file_to_il("records.pk")
        assert ".method" in il

    def test_struct_definition(self):
        il = compile_file_to_il("records.pk")
        assert "Rec_" in il
        assert ".field public int32 f_0" in il
        assert ".field public int32 f_1" in il

    def test_method_signature(self):
        il = compile_file_to_il("records.pk")
        method = extract_method(il, "swap_pair")
        assert "int32 V_0" in method
        assert "int32 V_1" in method

    def test_stfld_for_field_write(self):
        il = compile_file_to_il("records.pk")
        method = extract_method(il, "swap_pair")
        instrs = il_instructions(method)
        stfld_count = sum(1 for i in instrs if "stfld" in i)
        assert stfld_count >= 2  # writes to .0 and .1

    def test_ldfld_for_field_read(self):
        il = compile_file_to_il("records.pk")
        method = extract_method(il, "swap_pair")
        instrs = il_instructions(method)
        assert any("ldfld" in i and "f_1" in i for i in instrs)


# ---------------------------------------------------------------------------
# Complex UDT (nested types)
# ---------------------------------------------------------------------------

class TestILComplexUDT:
    """Tests for complex_udt.pk — array of records, nested access."""

    def test_compiles(self):
        il = compile_file_to_il("complex_udt.pk")
        assert "nested_access" in il

    def test_struct_definition(self):
        il = compile_file_to_il("complex_udt.pk")
        assert "Rec_" in il
        assert ".field public int32 f_0" in il
        assert ".field public int32 f_1" in il

    def test_newarr_of_records(self):
        il = compile_file_to_il("complex_udt.pk")
        method = extract_method(il, "nested_access")
        assert "newarr" in method

    def test_ldelema_for_element_access(self):
        il = compile_file_to_il("complex_udt.pk")
        method = extract_method(il, "nested_access")
        instrs = il_instructions(method)
        assert any("ldelema" in i for i in instrs)

    def test_stfld_for_nested_field_write(self):
        il = compile_file_to_il("complex_udt.pk")
        method = extract_method(il, "nested_access")
        instrs = il_instructions(method)
        stfld_count = sum(1 for i in instrs if "stfld" in i)
        assert stfld_count >= 6  # 6 field writes

    def test_ldfld_for_nested_field_read(self):
        il = compile_file_to_il("complex_udt.pk")
        method = extract_method(il, "nested_access")
        instrs = il_instructions(method)
        assert any("ldfld" in i and "f_1" in i for i in instrs)

    def test_dynamic_index_access(self):
        il = compile_file_to_il("complex_udt.pk")
        method = extract_method(il, "nested_access")
        instrs = il_instructions(method)
        # V0 is used as dynamic index
        assert "ldarg V_0" in instrs


# ---------------------------------------------------------------------------
# C-variables (constants)
# ---------------------------------------------------------------------------

class TestILConstants:
    """Tests for constants.pk — C-variables as locals."""

    def test_compiles(self):
        il = compile_file_to_il("constants.pk")
        assert "use_const" in il

    def test_c_variables_as_locals(self):
        il = compile_file_to_il("constants.pk")
        method = extract_method(il, "use_const")
        assert "C_0" in method
        assert "C_1" in method

    def test_stloc_c_variable(self):
        il = compile_file_to_il("constants.pk")
        method = extract_method(il, "use_const")
        instrs = il_instructions(method)
        assert "stloc C_0" in instrs
        assert "stloc C_1" in instrs

    def test_ldloc_c_variable(self):
        il = compile_file_to_il("constants.pk")
        method = extract_method(il, "use_const")
        instrs = il_instructions(method)
        assert "ldloc C_0" in instrs
        assert "ldloc C_1" in instrs

    def test_add_instruction(self):
        il = compile_file_to_il("constants.pk")
        method = extract_method(il, "use_const")
        instrs = il_instructions(method)
        assert "add" in instrs


# ---------------------------------------------------------------------------
# Operators: division, power, AND, OR, bitseq literals
# ---------------------------------------------------------------------------

class TestILOperators:
    """Tests for operators not yet covered by existing tests."""

    def test_division(self):
        il = compile_source_to_il(
            "P1 f (V0[:8.0], V1[:8.0]) -> R0[:8.0]\n"
            "  V0[:8.0] / V1[:8.0] => R0[:8.0]\n"
            "END"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        assert "div" in instrs

    def test_power(self):
        il = compile_source_to_il(
            "P1 f (V0[:8.0], V1[:8.0]) -> R0[:8.0]\n"
            "  V0[:8.0] ** V1[:8.0] => R0[:8.0]\n"
            "END"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        assert any("Math::Pow" in i for i in instrs)
        assert "conv.i4" in instrs

    def test_boolean_and(self):
        il = compile_source_to_il(
            "P1 f (V0[:0], V1[:0]) -> R0[:0]\n"
            "  V0[:0] & V1[:0] => R0[:0]\n"
            "END"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        assert "and" in instrs

    def test_boolean_or(self):
        il = compile_source_to_il(
            "P1 f (V0[:0], V1[:0]) -> R0[:0]\n"
            "  V0[:0] | V1[:0] => R0[:0]\n"
            "END"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        assert "or" in instrs

    def test_bitseq_literal(self):
        il = compile_source_to_il(
            "P1 f () -> R0[:8.0]\n"
            "  L00L => R0[:8.0]\n"
            "END"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        # L00L = 1001 binary = 9 decimal
        assert "ldc.i4 9" in instrs


# ---------------------------------------------------------------------------
# Nested guards
# ---------------------------------------------------------------------------

class TestILNestedGuards:
    """Tests for nested conditional guards."""

    def test_nested_guard_brfalse(self):
        il = compile_source_to_il(
            "P1 f (V0[:8.0], V1[:8.0]) -> R0[:8.0]\n"
            "  0 => R0[:8.0]\n"
            "  (V0[:8.0] > 0) -> (V1[:8.0] > 0) -> V0[:8.0] + V1[:8.0] => R0[:8.0]\n"
            "END"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        brfalse_count = sum(1 for i in instrs if "brfalse" in i)
        assert brfalse_count >= 2  # two nested guards → two brfalse

    def test_guard_block_with_nested_guard(self):
        il = compile_source_to_il(
            "P1 f (V0[:8.0], V1[:8.0]) -> R0[:8.0]\n"
            "  0 => R0[:8.0]\n"
            "  (V0[:8.0] > 0) -> {\n"
            "    (V1[:8.0] > 0) -> V0[:8.0] + V1[:8.0] => R0[:8.0]\n"
            "  }\n"
            "END"
        )
        method = extract_method(il, "f")
        instrs = il_instructions(method)
        brfalse_count = sum(1 for i in instrs if "brfalse" in i)
        assert brfalse_count >= 2


# ---------------------------------------------------------------------------
# Subprograms (P1.1)
# ---------------------------------------------------------------------------

class TestILSubprograms:
    """Tests for subprograms.pk — P1.1 helper called from P1."""

    def test_compiles(self):
        il = compile_file_to_il("subprograms.pk")
        assert ".method" in il

    def test_both_methods_present(self):
        il = compile_file_to_il("subprograms.pk")
        assert "double" in il
        assert "quad" in il

    def test_double_method_mul(self):
        il = compile_file_to_il("subprograms.pk")
        method = extract_method(il, "double")
        instrs = il_instructions(method)
        assert "mul" in instrs

    def test_quad_calls_double(self):
        il = compile_file_to_il("subprograms.pk")
        method = extract_method(il, "quad")
        instrs = il_instructions(method)
        assert any("call" in i and "double" in i for i in instrs)

    def test_quad_calls_double_twice(self):
        il = compile_file_to_il("subprograms.pk")
        method = extract_method(il, "quad")
        instrs = il_instructions(method)
        call_count = sum(1 for i in instrs if "call" in i and "double" in i)
        assert call_count == 2


# ---------------------------------------------------------------------------
# Multi-return (struct for >1 result)
# ---------------------------------------------------------------------------

class TestILMultiReturn:
    """Tests for multi_return.pk — programs with multiple return values."""

    def test_compiles(self):
        il = compile_file_to_il("multi_return.pk")
        assert "swap" in il

    def test_swap_returns_struct(self):
        il = compile_file_to_il("multi_return.pk")
        method = extract_method(il, "swap")
        assert "valuetype Rec_" in method

    def test_swap_has_ret_local(self):
        il = compile_file_to_il("multi_return.pk")
        method = extract_method(il, "swap")
        assert "_ret" in method

    def test_swap_populates_both_fields(self):
        il = compile_file_to_il("multi_return.pk")
        method = extract_method(il, "swap")
        instrs = il_instructions(method)
        stfld_count = sum(1 for i in instrs if "stfld" in i)
        assert stfld_count == 2  # f_0 and f_1

    def test_caller_receives_struct(self):
        il = compile_file_to_il("multi_return.pk")
        method = extract_method(il, "use_swap")
        instrs = il_instructions(method)
        assert any("call" in i and "swap" in i and "Rec_" in i for i in instrs)

    def test_caller_accesses_field(self):
        il = compile_file_to_il("multi_return.pk")
        method = extract_method(il, "use_swap")
        instrs = il_instructions(method)
        assert any("ldfld" in i and "f_0" in i for i in instrs)

    def test_inline_multi_return(self):
        il = compile_source_to_il(
            "P1 pair (V0[:8.0], V1[:8.0]) -> (R0[:8.0], R1[:8.0])\n"
            "  V0[:8.0] => R0[:8.0]\n"
            "  V1[:8.0] => R1[:8.0]\n"
            "END"
        )
        method = extract_method(il, "pair")
        assert "valuetype Rec_" in method
        instrs = il_instructions(method)
        assert any("ldloca _ret" in i for i in instrs)
        assert any("ldloc _ret" in i for i in instrs)


# ---------------------------------------------------------------------------
# Cross-program R<N>
# ---------------------------------------------------------------------------

class TestILCrossProgram:
    """Tests for cross_program.pk — R<N> refs to parameterless programs."""

    def test_compiles(self):
        il = compile_file_to_il("cross_program.pk")
        assert "get_ten" in il
        assert "use_ten" in il

    def test_cross_program_emits_call(self):
        il = compile_file_to_il("cross_program.pk")
        method = extract_method(il, "use_ten")
        instrs = il_instructions(method)
        assert any("call" in i and "get_ten" in i for i in instrs)

    def test_cross_program_no_local_for_r1(self):
        il = compile_file_to_il("cross_program.pk")
        method = extract_method(il, "use_ten")
        assert "R_1" not in method  # R1 is cross-program, not a local

    def test_cross_program_inline(self):
        il = compile_source_to_il(
            "P1 pi () -> R0[:8.0]\n"
            "  3 => R0[:8.0]\n"
            "END\n"
            "P2 two_pi () -> R0[:8.0]\n"
            "  R1[:8.0] * 2 => R0[:8.0]\n"
            "END"
        )
        method = extract_method(il, "two_pi")
        instrs = il_instructions(method)
        assert any("call" in i and "pi" in i for i in instrs)
        assert "mul" in instrs
