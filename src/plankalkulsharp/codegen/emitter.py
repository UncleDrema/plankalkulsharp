"""CIL text assembly emitter for Plankalkül programs.

Produces .il files that can be assembled by ilasm into .NET executables.
Each Plankalkül program becomes a static method. Types are mapped to
appropriate CLR types.
"""

from __future__ import annotations

from io import StringIO

from plankalkulsharp.my_ast.nodes import (
    Assignment,
    BinOp,
    BinaryExpr,
    BitSeqLiteral,
    BoolLiteral,
    DynamicAccess,
    ExprNode,
    ForLoop,
    FuncCall,
    GuardedStmt,
    IntLiteral,
    Program,
    ProgramDef,
    StaticAccess,
    StmtNode,
    TypeDef,
    UnOp,
    UnaryExpr,
    VarRef,
    WLoop,
)
from plankalkulsharp.semantic.analyzer import (
    Analyzer,
    ResolvedArray,
    ResolvedBit,
    ResolvedBitSeq,
    ResolvedRecord,
    ResolvedType,
)


# ---------------------------------------------------------------------------
# CIL type mapping
# ---------------------------------------------------------------------------

_record_struct_map: dict[ResolvedRecord, str] = {}


def cil_type(rt: ResolvedType) -> str:
    """Map a resolved Plankalkül type to a CIL type name."""
    if isinstance(rt, ResolvedBit):
        return "bool"
    if isinstance(rt, ResolvedBitSeq):
        if rt.length <= 32:
            return "int32"
        return "int64"
    if isinstance(rt, ResolvedArray):
        return f"{cil_type(rt.element)}[]"
    if isinstance(rt, ResolvedRecord):
        name = _record_struct_map.get(rt)
        if name:
            return f"valuetype {name}"
        return "int32"  # fallback
    return "int32"


# ---------------------------------------------------------------------------
# Label generator
# ---------------------------------------------------------------------------

class _LabelGen:
    def __init__(self) -> None:
        self._counter = 0

    def next(self, prefix: str = "L") -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}"


# ---------------------------------------------------------------------------
# CIL Emitter
# ---------------------------------------------------------------------------

class CILEmitter:
    """Emits CIL text assembly (.il) from a type-checked AST."""

    def __init__(self, analyzer: Analyzer) -> None:
        self._analyzer = analyzer
        self._out = StringIO()
        self._indent = 0
        self._labels = _LabelGen()
        self._locals: dict[str, tuple[int, ResolvedType]] = {}
        self._local_index = 0
        self._program_methods: dict[str, str] = {}  # key → CIL method name
        self._current_psym = None  # current ProgramSymbol being emitted

    # -- public interface ---------------------------------------------------

    def emit(self, program: Program) -> str:
        """Generate the full .il source for a program."""
        global _record_struct_map
        _record_struct_map = self._collect_all_records()

        self._emit_header()
        self._emit_line()

        # Emit struct definitions for record types
        for rt, name in _record_struct_map.items():
            self._emit_struct_def(rt, name)

        self._emit_line(".class public abstract sealed auto ansi PlankalkulProgram")
        self._emit_line("{")
        self._indent += 1

        # Register method names first (for forward calls)
        for pd in program.program_defs:
            key = self._program_key(pd)
            method_name = pd.name or f"P{pd.number}"
            self._program_methods[key] = method_name
            # Also register by name for lookup
            if pd.name:
                self._program_methods[pd.name] = method_name

        for pd in program.program_defs:
            self._emit_program(pd)
            self._emit_line()

        # Emit Main entry point that calls the first program
        if program.program_defs:
            self._emit_main(program.program_defs[0])

        self._indent -= 1
        self._emit_line("}")
        return self._out.getvalue()

    # -- output helpers -----------------------------------------------------

    def _emit_line(self, line: str = "") -> None:
        if line:
            self._out.write("    " * self._indent + line + "\n")
        else:
            self._out.write("\n")

    # -- record struct helpers ----------------------------------------------

    def _collect_all_records(self) -> dict[ResolvedRecord, str]:
        """Find all unique ResolvedRecord types and assign struct names."""
        records: dict[ResolvedRecord, str] = {}
        counter = [0]

        def visit(rt: ResolvedType) -> None:
            if isinstance(rt, ResolvedRecord):
                if rt not in records:
                    records[rt] = f"Rec_{counter[0]}"
                    counter[0] += 1
                    for f in rt.fields:
                        visit(f)
            elif isinstance(rt, ResolvedArray):
                visit(rt.element)

        for rt in self._analyzer.type_defs.values():
            visit(rt)
        for psym in self._analyzer.programs.values():
            for pt in psym.params:
                visit(pt)
            for rt in psym.results:
                visit(rt)
            # Multi-result programs return a combined record struct
            if len(psym.results) > 1:
                visit(ResolvedRecord(tuple(psym.results)))
        return records

    def _emit_struct_def(self, rt: ResolvedRecord, name: str) -> None:
        """Emit a CIL value type (struct) for a Plankalkül record."""
        self._emit_line(
            f".class sequential sealed public {name}"
            f" extends [System.Runtime]System.ValueType"
        )
        self._emit_line("{")
        self._indent += 1
        for i, field_type in enumerate(rt.fields):
            self._emit_line(f".field public {cil_type(field_type)} f_{i}")
        self._indent -= 1
        self._emit_line("}")
        self._emit_line()

    # -- header -------------------------------------------------------------

    def _emit_header(self) -> None:
        self._emit_line("// Auto-generated CIL assembly from Plankalkül source")
        self._emit_line(".assembly extern System.Runtime { }")
        self._emit_line(".assembly extern System.Console { }")
        self._emit_line(".assembly PlankalkulProgram { }")
        self._emit_line(".module PlankalkulProgram.dll")

    # -- program → static method -------------------------------------------

    def _program_key(self, pd: ProgramDef) -> str:
        if pd.sub_number is not None:
            return f"P{pd.number}.{pd.sub_number}"
        return f"P{pd.number}"

    def _emit_program(self, pd: ProgramDef) -> None:
        key = self._program_key(pd)
        method_name = self._program_methods[key]
        psym = self._analyzer.programs.get(key)
        if psym is None:
            return
        self._current_psym = psym

        # Build parameter and return type strings
        param_strs = []
        for i, pt in enumerate(psym.params):
            param_strs.append(f"{cil_type(pt)} V_{i}")

        if len(psym.results) > 1:
            ret_record = ResolvedRecord(tuple(psym.results))
            ret_type = cil_type(ret_record)
        elif psym.results:
            ret_type = cil_type(psym.results[0])
        else:
            ret_type = "void"

        sig = ", ".join(param_strs)
        self._emit_line(
            f".method public hidebysig static {ret_type} {method_name}({sig}) cil managed"
        )
        self._emit_line("{")
        self._indent += 1
        self._emit_line(".maxstack 16")

        # Reset locals for this method
        self._locals = {}
        self._local_index = 0
        self._labels = _LabelGen()

        # Pre-scan body to collect local variables
        self._collect_locals(pd)

        # Emit .locals init
        if self._locals:
            local_decls = []
            for var_key in sorted(self._locals, key=lambda k: self._locals[k][0]):
                idx, rt = self._locals[var_key]
                local_decls.append(f"{cil_type(rt)} {var_key}")
            self._emit_line(f".locals init ({', '.join(local_decls)})")

        # Emit newarr for array-typed locals
        for var_key in sorted(self._locals, key=lambda k: self._locals[k][0]):
            idx, rt = self._locals[var_key]
            if isinstance(rt, ResolvedArray):
                self._emit_line(f"ldc.i4 {rt.size}")
                self._emit_line(f"newarr {cil_type(rt.element)}")
                self._emit_line(f"stloc {var_key}")

        # Emit body
        for stmt in pd.body:
            self._emit_stmt(stmt)

        # Return result(s)
        if len(psym.results) > 1:
            # Multi-result: populate the return struct and return it
            ret_record = ResolvedRecord(tuple(psym.results))
            for i, rt in enumerate(psym.results):
                self._emit_line("ldloca _ret")
                self._emit_line(f"ldloc R_{i}")
                self._emit_line(
                    f"stfld {cil_type(rt)} {cil_type(ret_record)}::f_{i}"
                )
            self._emit_line("ldloc _ret")
            self._emit_line("ret")
        elif psym.results:
            r0_key = "R_0"
            if r0_key in self._locals:
                self._emit_line(f"ldloc {r0_key}")
            else:
                self._emit_line("ldc.i4.0")
            self._emit_line("ret")
        else:
            self._emit_line("ret")

        self._indent -= 1
        self._emit_line("}")

    def _collect_locals(self, pd: ProgramDef) -> None:
        """Pre-scan to allocate local variable slots for Z and R variables."""
        psym = self._analyzer.programs.get(self._program_key(pd))
        if psym is None:
            return

        # V variables are method arguments (accessed via ldarg)
        # Z, C variables → locals
        # R variables → locals (returned at end)

        # Register R variables first
        for i, rt in enumerate(psym.results):
            key = f"R_{i}"
            self._locals[key] = (self._local_index, rt)
            self._local_index += 1

        # For multi-result programs, add a return struct local
        if len(psym.results) > 1:
            ret_record = ResolvedRecord(tuple(psym.results))
            self._locals["_ret"] = (self._local_index, ret_record)
            self._local_index += 1

        # Walk the body to find all Z/C variable references
        self._scan_stmt_list_for_locals(pd.body)

    def _scan_stmt_list_for_locals(self, stmts: list[StmtNode]) -> None:
        for stmt in stmts:
            if isinstance(stmt, Assignment):
                self._maybe_register_local(stmt.target)
                self._scan_expr_for_locals(stmt.value)
            elif isinstance(stmt, GuardedStmt):
                self._scan_expr_for_locals(stmt.condition)
                self._scan_stmt_list_for_locals(stmt.body)
            elif isinstance(stmt, WLoop):
                self._scan_stmt_list_for_locals(stmt.body)
            elif isinstance(stmt, ForLoop):
                self._maybe_register_local(stmt.var)
                self._scan_expr_for_locals(stmt.start)
                self._scan_expr_for_locals(stmt.end)
                self._scan_stmt_list_for_locals(stmt.body)

    def _scan_expr_for_locals(self, expr: ExprNode) -> None:
        if isinstance(expr, VarRef):
            if expr.kind in ("Z", "C"):
                self._maybe_register_local(expr)
        elif isinstance(expr, BinaryExpr):
            self._scan_expr_for_locals(expr.left)
            self._scan_expr_for_locals(expr.right)
        elif isinstance(expr, UnaryExpr):
            self._scan_expr_for_locals(expr.operand)
        elif isinstance(expr, FuncCall):
            for arg in expr.args:
                self._scan_expr_for_locals(arg)

    def _maybe_register_local(self, ref: VarRef) -> None:
        if ref.kind == "V":
            return  # V variables are method arguments
        key = f"{ref.kind}_{ref.index}"
        if key not in self._locals:
            # Resolve type from annotation or scope
            rt: ResolvedType = ResolvedBitSeq(8)  # default
            if ref.type_ann is not None:
                resolved = self._analyzer.resolve_type_node(ref.type_ann)
                if resolved is not None:
                    rt = resolved
            self._locals[key] = (self._local_index, rt)
            self._local_index += 1

    # -- statement emission -------------------------------------------------

    def _emit_stmt(self, stmt: StmtNode) -> None:
        if isinstance(stmt, Assignment):
            self._emit_assignment(stmt)
        elif isinstance(stmt, GuardedStmt):
            self._emit_guarded(stmt)
        elif isinstance(stmt, WLoop):
            self._emit_w_loop(stmt)
        elif isinstance(stmt, ForLoop):
            self._emit_for_loop(stmt)

    def _emit_assignment(self, stmt: Assignment) -> None:
        if stmt.target.components:
            self._emit_array_store(stmt)
        else:
            # Push value onto stack
            self._emit_expr(stmt.value)
            # Store to target variable
            self._emit_store(stmt.target)

    def _emit_array_store(self, stmt: Assignment) -> None:
        """Emit store through a component chain (arrays and/or record fields)."""
        target = stmt.target
        # Load the base variable
        if target.kind == "V":
            self._emit_line(f"ldarg V_{target.index}")
        else:
            key = f"{target.kind}_{target.index}"
            self._emit_line(f"ldloc {key}")

        current_type = self._get_var_base_type(target)
        if current_type is None:
            return

        components = target.components
        for i, comp in enumerate(components):
            is_last = i == len(components) - 1

            if isinstance(current_type, ResolvedArray):
                elem = current_type.element
                # Push index
                if isinstance(comp, StaticAccess):
                    self._emit_line(f"ldc.i4 {comp.index}")
                elif isinstance(comp, DynamicAccess):
                    self._emit_expr(comp.expr)

                if is_last:
                    self._emit_expr(stmt.value)
                    self._emit_line(self._stelem_op(elem))
                    return
                else:
                    # Navigate: ldelema for value-type elements, ldelem for ref
                    if isinstance(elem, ResolvedRecord):
                        self._emit_line(f"ldelema {cil_type(elem)}")
                    else:
                        self._emit_line(self._ldelem_op(elem))
                    current_type = elem

            elif isinstance(current_type, ResolvedRecord):
                if isinstance(comp, StaticAccess) and 0 <= comp.index < len(current_type.fields):
                    field_type = current_type.fields[comp.index]
                    field_name = f"f_{comp.index}"
                    if is_last:
                        self._emit_expr(stmt.value)
                        self._emit_line(
                            f"stfld {cil_type(field_type)} {cil_type(current_type)}::{field_name}"
                        )
                        return
                    else:
                        self._emit_line(
                            f"ldflda {cil_type(field_type)} {cil_type(current_type)}::{field_name}"
                        )
                        current_type = field_type

            elif isinstance(current_type, ResolvedBitSeq):
                if isinstance(comp, StaticAccess):
                    self._emit_line(f"ldc.i4 {comp.index}")
                elif isinstance(comp, DynamicAccess):
                    self._emit_expr(comp.expr)
                if is_last:
                    self._emit_expr(stmt.value)
                    self._emit_line("stelem.i4")
                    return
                else:
                    self._emit_line("ldelem.i4")
                    current_type = ResolvedBit()

    def _emit_guarded(self, stmt: GuardedStmt) -> None:
        lbl_end = self._labels.next("GEND")
        # Push condition
        self._emit_expr(stmt.condition)
        self._emit_line(f"brfalse {lbl_end}")
        # Body
        for s in stmt.body:
            self._emit_stmt(s)
        self._emit_line(f"{lbl_end}:")

    def _emit_w_loop(self, stmt: WLoop) -> None:
        lbl_top = self._labels.next("WTOP")
        lbl_end = self._labels.next("WEND")
        self._emit_line(f"{lbl_top}:")

        # Each iteration: check if any guard fires
        # We emit all guarded statements; if none fire, break
        # Use a flag local to track if any guard was true
        flag_key = self._labels.next("wflag")
        flag_idx = self._local_index
        # We don't add to .locals init since we've already emitted it.
        # Instead, use the stack-based approach:
        # Push 0 (flag=false), iterate guards, if flag still false, break

        # Simpler approach: just re-emit the guarded statements in a loop
        # and check an "any_fired" flag

        # Allocate a temp in already-declared locals
        # Actually, for simplicity, just rely on structured execution:
        # Each guard checks condition and may execute body.
        # We need to know if at least one guard was true.
        # Use: push 0, for each guard { dup; if cond push 1 or pop/push },
        # after all guards brtrue WTOP.

        # Simplified W-loop: keep looping, each guard body is gated by its condition.
        # Exit when none of the guards fires.
        # We'll use ldc.i4.0 as a "any_fired" flag on the stack.
        self._emit_line("ldc.i4.0")  # any_fired = false

        for s in stmt.body:
            if isinstance(s, GuardedStmt):
                lbl_skip = self._labels.next("WSKIP")
                # Save current "any_fired" on stack, eval condition
                self._emit_expr(s.condition)
                self._emit_line(f"brfalse {lbl_skip}")
                # Guard fired — set any_fired = true
                self._emit_line("pop")       # pop old flag
                self._emit_line("ldc.i4.1")  # push true
                for inner in s.body:
                    self._emit_stmt(inner)
                self._emit_line(f"{lbl_skip}:")
            else:
                # Non-guarded statement in W-loop (always executes, always "fires")
                self._emit_line("pop")       # pop old flag
                self._emit_line("ldc.i4.1")  # set flag = true
                self._emit_stmt(s)

        # If any_fired is true, loop again
        self._emit_line(f"brtrue {lbl_top}")

    def _emit_for_loop(self, stmt: ForLoop) -> None:
        lbl_top = self._labels.next("FTOP")
        lbl_end = self._labels.next("FEND")

        # Initialize loop variable
        self._emit_expr(stmt.start)
        self._emit_store(stmt.var)

        self._emit_line(f"{lbl_top}:")
        # Check: var <= end
        self._emit_load(stmt.var)
        self._emit_expr(stmt.end)
        self._emit_line(f"bgt {lbl_end}")

        # Body
        for s in stmt.body:
            self._emit_stmt(s)

        # Increment loop variable
        self._emit_load(stmt.var)
        self._emit_line("ldc.i4.1")
        self._emit_line("add")
        self._emit_store(stmt.var)

        self._emit_line(f"br {lbl_top}")
        self._emit_line(f"{lbl_end}:")

    # -- expression emission ------------------------------------------------

    def _emit_expr(self, expr: ExprNode) -> None:
        if isinstance(expr, IntLiteral):
            self._emit_line(f"ldc.i4 {expr.value}")
        elif isinstance(expr, BoolLiteral):
            self._emit_line("ldc.i4.1" if expr.value else "ldc.i4.0")
        elif isinstance(expr, BitSeqLiteral):
            # Convert bit sequence to integer
            val = 0
            for b in expr.bits:
                val = (val << 1) | (1 if b else 0)
            self._emit_line(f"ldc.i4 {val}")
        elif isinstance(expr, VarRef):
            self._emit_load(expr)
        elif isinstance(expr, BinaryExpr):
            self._emit_expr(expr.left)
            self._emit_expr(expr.right)
            self._emit_binop(expr.op)
        elif isinstance(expr, UnaryExpr):
            self._emit_expr(expr.operand)
            if expr.op == UnOp.NOT:
                self._emit_line("ldc.i4.0")
                self._emit_line("ceq")
            elif expr.op == UnOp.NEG:
                self._emit_line("neg")
        elif isinstance(expr, FuncCall):
            self._emit_func_call(expr)

    def _emit_binop(self, op: BinOp) -> None:
        match op:
            case BinOp.ADD:
                self._emit_line("add")
            case BinOp.SUB:
                self._emit_line("sub")
            case BinOp.MUL:
                self._emit_line("mul")
            case BinOp.DIV:
                self._emit_line("div")
            case BinOp.AND:
                self._emit_line("and")
            case BinOp.OR:
                self._emit_line("or")
            case BinOp.EQ:
                self._emit_line("ceq")
            case BinOp.NEQ:
                self._emit_line("ceq")
                self._emit_line("ldc.i4.0")
                self._emit_line("ceq")
            case BinOp.LT:
                self._emit_line("clt")
            case BinOp.GT:
                self._emit_line("cgt")
            case BinOp.LE:
                self._emit_line("cgt")
                self._emit_line("ldc.i4.0")
                self._emit_line("ceq")
            case BinOp.GE:
                self._emit_line("clt")
                self._emit_line("ldc.i4.0")
                self._emit_line("ceq")
            case BinOp.POW:
                # CIL has no pow instruction; use a call to Math.Pow
                self._emit_line("conv.r8")
                # Need to swap — operands are [base, exp] on stack
                # Actually they're already in order: left=base, right=exp
                self._emit_line("call float64 [System.Runtime]System.Math::Pow(float64, float64)")
                self._emit_line("conv.i4")

    def _emit_func_call(self, expr: FuncCall) -> None:
        # Push arguments
        for arg in expr.args:
            self._emit_expr(arg)

        # Resolve method name
        name = expr.name
        method_name = self._program_methods.get(name, name)

        # Build method signature
        psym = self._analyzer.programs.get(name)
        if psym is None:
            # Try by name
            for key, sym in self._analyzer.programs.items():
                if sym.name == name:
                    psym = sym
                    break

        if psym is not None:
            param_types_str = ", ".join(cil_type(pt) for pt in psym.params)
            if len(psym.results) > 1:
                ret_record = ResolvedRecord(tuple(psym.results))
                ret_type = cil_type(ret_record)
            elif psym.results:
                ret_type = cil_type(psym.results[0])
            else:
                ret_type = "void"
            self._emit_line(
                f"call {ret_type} PlankalkulProgram::{method_name}({param_types_str})"
            )
        else:
            self._emit_line(f"// WARNING: unresolved call to {name}")

    # -- load/store helpers -------------------------------------------------

    def _emit_load(self, ref: VarRef) -> None:
        cross_program_type: ResolvedType | None = None
        if ref.kind == "V":
            self._emit_line(f"ldarg V_{ref.index}")
        else:
            key = f"{ref.kind}_{ref.index}"
            if key in self._locals:
                self._emit_line(f"ldloc {key}")
            elif ref.kind == "R":
                cross_program_type = self._emit_cross_program_load(ref)
            else:
                self._emit_line(f"// WARNING: cannot load {ref.kind}{ref.index}")
                self._emit_line("ldc.i4.0")

        # Handle component access chain with type tracking
        if ref.components:
            current_type = cross_program_type or self._get_var_base_type(ref)
            if current_type is not None:
                for i, comp in enumerate(ref.components):
                    if isinstance(current_type, ResolvedArray):
                        elem = current_type.element
                        if isinstance(comp, StaticAccess):
                            self._emit_line(f"ldc.i4 {comp.index}")
                        elif isinstance(comp, DynamicAccess):
                            self._emit_expr(comp.expr)
                        # Use ldelema if next access is a record field
                        if isinstance(elem, ResolvedRecord) and i + 1 < len(ref.components):
                            self._emit_line(f"ldelema {cil_type(elem)}")
                        else:
                            self._emit_line(self._ldelem_op(elem))
                        current_type = elem

                    elif isinstance(current_type, ResolvedRecord):
                        if isinstance(comp, StaticAccess) and 0 <= comp.index < len(current_type.fields):
                            field_type = current_type.fields[comp.index]
                            field_name = f"f_{comp.index}"
                            self._emit_line(
                                f"ldfld {cil_type(field_type)} {cil_type(current_type)}::{field_name}"
                            )
                            current_type = field_type

                    elif isinstance(current_type, ResolvedBitSeq):
                        if isinstance(comp, StaticAccess):
                            self._emit_line(f"ldc.i4 {comp.index}")
                        elif isinstance(comp, DynamicAccess):
                            self._emit_expr(comp.expr)
                        self._emit_line("ldelem.i4")
                        current_type = ResolvedBit()

    def _emit_cross_program_load(self, ref: VarRef) -> ResolvedType | None:
        """Emit a call for cross-program R<N> reference. Returns the base type."""
        program_key = f"P{ref.index}"
        psym = self._analyzer.programs.get(program_key)
        if psym is None or len(psym.params) != 0:
            self._emit_line(f"// WARNING: cannot load {ref.kind}{ref.index}")
            self._emit_line("ldc.i4.0")
            return None

        method_name = self._program_methods.get(program_key, program_key)
        if len(psym.results) > 1:
            ret_record = ResolvedRecord(tuple(psym.results))
            ret_type = cil_type(ret_record)
            base = ret_record
        elif psym.results:
            ret_type = cil_type(psym.results[0])
            base = psym.results[0]
        else:
            self._emit_line("ldc.i4.0")
            return None

        self._emit_line(f"call {ret_type} PlankalkulProgram::{method_name}()")
        return base

    def _emit_store(self, ref: VarRef) -> None:
        if ref.kind == "V":
            self._emit_line(f"starg V_{ref.index}")
        else:
            key = f"{ref.kind}_{ref.index}"
            if key in self._locals:
                self._emit_line(f"stloc {key}")
            else:
                self._emit_line(f"// WARNING: cannot store {ref.kind}{ref.index}")
                self._emit_line("pop")

    # -- type-aware array helpers -------------------------------------------

    def _ldelem_op(self, elem_type: ResolvedType | None) -> str:
        """Return the appropriate ldelem instruction for the element type."""
        if elem_type is None:
            return "ldelem.ref"
        if isinstance(elem_type, ResolvedBit):
            return "ldelem.i4"
        if isinstance(elem_type, ResolvedBitSeq):
            ct = cil_type(elem_type)
            return "ldelem.i8" if ct == "int64" else "ldelem.i4"
        if isinstance(elem_type, ResolvedArray):
            return "ldelem.ref"
        return "ldelem.i4"

    def _stelem_op(self, elem_type: ResolvedType | None) -> str:
        """Return the appropriate stelem instruction for the element type."""
        if elem_type is None:
            return "stelem.i4"
        if isinstance(elem_type, ResolvedBit):
            return "stelem.i4"
        if isinstance(elem_type, ResolvedBitSeq):
            ct = cil_type(elem_type)
            return "stelem.i8" if ct == "int64" else "stelem.i4"
        if isinstance(elem_type, ResolvedArray):
            return "stelem.ref"
        return "stelem.i4"

    def _get_var_base_type(self, ref: VarRef) -> ResolvedType | None:
        """Get the resolved type of a variable (without walking components)."""
        if ref.kind == "V":
            if self._current_psym and ref.index < len(self._current_psym.params):
                return self._current_psym.params[ref.index]
            return None
        key = f"{ref.kind}_{ref.index}"
        if key in self._locals:
            _, base = self._locals[key]
            return base
        return None

    # -- main entry point ---------------------------------------------------

    def _emit_main(self, first_program: ProgramDef) -> None:
        """Emit a Main method that calls the first program.

        Parses command-line args as int32 arguments. If not enough args
        are provided, uses 0 as default.
        """
        key = self._program_key(first_program)
        psym = self._analyzer.programs.get(key)
        if psym is None:
            return

        method_name = self._program_methods[key]

        self._emit_line(f".method public hidebysig static void Main(string[] args) cil managed")
        self._emit_line("{")
        self._indent += 1
        self._emit_line(".entrypoint")
        self._emit_line(".maxstack 16")

        # Declare locals if needed for multi-result
        if len(psym.results) > 1:
            ret_record = ResolvedRecord(tuple(psym.results))
            self._emit_line(f".locals init ({cil_type(ret_record)} _mret)")

        # For each parameter, try to parse args[i]; fallback to 0
        for i, pt in enumerate(psym.params):
            lbl_ok = self._labels.next("AROK")
            lbl_default = self._labels.next("ARDF")
            # if (i < args.Length) goto parse; else goto default
            self._emit_line(f"ldc.i4 {i}")
            self._emit_line("ldarg.0")          # args
            self._emit_line("ldlen")
            self._emit_line("conv.i4")
            self._emit_line(f"bge {lbl_default}")
            # parse: Int32.Parse(args[i])
            self._emit_line("ldarg.0")
            self._emit_line(f"ldc.i4 {i}")
            self._emit_line("ldelem.ref")
            self._emit_line("call int32 [System.Runtime]System.Int32::Parse(string)")
            self._emit_line(f"br {lbl_ok}")
            # default: push 0
            self._emit_line(f"{lbl_default}:")
            self._emit_line("ldc.i4.0")
            self._emit_line(f"{lbl_ok}:")

        param_types_str = ", ".join(cil_type(pt) for pt in psym.params)
        if len(psym.results) > 1:
            ret_record = ResolvedRecord(tuple(psym.results))
            ret_type = cil_type(ret_record)
        elif psym.results:
            ret_type = cil_type(psym.results[0])
        else:
            ret_type = "void"
        self._emit_line(f"call {ret_type} PlankalkulProgram::{method_name}({param_types_str})")

        # Print result if there is one
        if len(psym.results) > 1:
            # Multi-result: print first field of the struct
            ret_record = ResolvedRecord(tuple(psym.results))
            self._emit_line("stloc _mret")
            self._emit_line("ldloca _mret")
            self._emit_line(
                f"ldfld {cil_type(psym.results[0])} {cil_type(ret_record)}::f_0"
            )
            self._emit_line(
                "call void [System.Console]System.Console::WriteLine(int32)"
            )
        elif psym.results:
            self._emit_line(
                "call void [System.Console]System.Console::WriteLine(int32)"
            )
        self._emit_line("ret")

        self._indent -= 1
        self._emit_line("}")
