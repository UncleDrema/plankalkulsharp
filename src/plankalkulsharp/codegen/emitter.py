"""CIL text assembly emitter for Plankalkül programs.

Produces .il files that can be assembled by ilasm into .NET executables.
Each Plankalkül program becomes a static method. Types are mapped to
appropriate CLR types.
"""

from __future__ import annotations

from io import StringIO

from plankalkulsharp.plankalkul_ast.nodes import (
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
    ResolvedType, ProgramSymbol,
)


# ---------------------------------------------------------------------------
# CIL type mapping
# ---------------------------------------------------------------------------

_record_struct_map: dict[ResolvedRecord, str] = {}

class EmitError(Exception):
    pass

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
    return "int32" # fallback


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

    def emit(self) -> str:
        """Generate the full .il source for a program."""
        global _record_struct_map
        _record_struct_map = self._collect_all_records()

        self._emit_header()
        self._emit_line()

        # Emit struct definitions for record types
        for rt, name in _record_struct_map.items():
            self._emit_struct_def(rt, name)

        self._emit_line(".class public abstract sealed PlankalkulProgram")
        self._emit_line("{")
        self._indent += 1

        # Register method names first (for forward calls)
        for key, program in self._analyzer.programs.items():
            method_name = program.name or key
            self._program_methods[key] = method_name

        for program in self._analyzer.programs.values():
            self._emit_program(program)
            self._emit_line()

        # Emit Main entry point that calls the first program
        min_program = min(
            self._analyzer.programs.values(),
            key=lambda p: p.number
        )
        self._emit_main(min_program)

        self._indent -= 1
        self._emit_line("}")
        return self._out.getvalue()

    # -- output helpers -----------------------------------------------------

    def _comment(self, msg: str) -> None:
        self._out.write("    " * self._indent + "// " + msg + "\n")

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
            for var in psym.scope.vars.values():
                visit(var.resolved_type)
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
        self._comment("Auto-generated CIL assembly from Plankalkül source")
        self._emit_line(".assembly extern System.Runtime { }")
        self._emit_line(".assembly extern System.Console { }")
        self._emit_line(".assembly PlankalkulProgram { }")
        self._emit_line(".module PlankalkulProgram.dll")

    # -- program → static method -------------------------------------------

    def _emit_program(self, program: ProgramSymbol) -> None:
        pd = program.ast
        key = program.key
        method_name = self._program_methods[key]
        self._current_psym = program

        # Build parameter and return type strings
        param_strs = []
        for i, pt in enumerate(program.params):
            param_strs.append(f"{cil_type(pt)} V_{i}")

        if len(program.results) > 1:
            ret_record = ResolvedRecord(tuple(program.results))
            ret_type = cil_type(ret_record)
        elif program.results:
            ret_type = cil_type(program.results[0])
        else:
            ret_type = "void"

        sig = ", ".join(param_strs)
        self._comment(f"program {program}")
        self._emit_line(
            f".method private static {ret_type} {method_name}({sig})"
        )
        self._emit_line("{")
        self._indent += 1
        self._emit_line(".maxstack 16")

        # Reset locals for this method
        self._locals = {}
        self._local_index = 0
        self._labels = _LabelGen()

        # Pre-scan body to collect local variables
        self._collect_locals(program)

        # Emit .locals init
        if self._locals:
            local_decls = []
            for var_key in sorted(self._locals, key=lambda k: self._locals[k][0]):
                _, rt = self._locals[var_key]
                local_decls.append(f"{cil_type(rt)} {var_key}")
            self._emit_line(f".locals init ({', '.join(local_decls)})")

        # Emit newarr for array-typed locals
        for var_key in sorted(self._locals, key=lambda k: self._locals[k][0]):
            rt = self._locals[var_key][1]
            if isinstance(rt, ResolvedArray):
                self._comment(f"local array {rt.element}[{rt.size}] {var_key}")
                self._emit_line(f"ldc.i4 {rt.size}")
                self._emit_line(f"newarr {cil_type(rt.element)}")
                self._emit_line(f"stloc {var_key}")

        # Emit body
        for stmt in pd.body:
            self._emit_stmt(stmt)

        self._comment("return result")
        # Return result(s)
        if len(program.results) > 1:
            # Multi-result: populate the return struct and return it
            ret_record = ResolvedRecord(tuple(program.results))
            for i, rt in enumerate(program.results):
                self._emit_line("ldloca _ret")
                self._emit_line(f"ldloc R_{i}")
                self._emit_line(
                    f"stfld {cil_type(rt)} {cil_type(ret_record)}::f_{i}"
                )
            self._emit_line("ldloc _ret")
            self._emit_line("ret")
        elif program.results:
            result_index = list(filter(lambda v: v.kind == 'R', program.scope.vars.values()))[0].index
            result_key = f'R_{result_index}'
            if result_key in self._locals:
                self._emit_line(f"ldloc {result_key}")
            else:
                self._emit_line("ldc.i4.0")
            self._emit_line("ret")
        else:
            self._emit_line("ret")

        self._indent -= 1
        self._emit_line("}")

    def _collect_locals(self, program: ProgramSymbol) -> None:
        """Pre-scan to allocate local variable slots for Z and R variables."""
        # V variables are method arguments (accessed via ldarg)
        # Z, C variables → locals
        # R variables → locals (returned at end)
        for key, var in program.scope.vars.items():
            if var.kind == "V":
                continue
            elif var.kind == "C" or var.kind == "Z" or var.kind == "R":
                self._locals[f'{var.kind}_{var.index}'] = (self._local_index, var.resolved_type)
                self._local_index += 1

        # For multi-result programs, add a return struct local
        if len(program.results) > 1:
            ret_record = ResolvedRecord(tuple(program.results))
            self._locals["_ret"] = (self._local_index, ret_record)
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
        self._comment(f"assign {stmt.value} to {stmt.target}")
        if stmt.target.components:
            self._emit_component_store(stmt)
        else:
            # Push value onto stack
            self._emit_push_expr_on_stack(stmt.value)
            # Store to target variable
            self._emit_store_from_stack_to_var(stmt.target)

    def _emit_component_store(self, stmt: Assignment) -> None:
        """Emit store through a component chain (arrays and/or record fields)."""
        target = stmt.target
        current_type = self._get_var_base_type(target)
        if current_type is None:
            return
        key = f"{target.kind}_{target.index}"
        # Load the base variable
        if target.kind == "V":
            self._comment(f"load argument {key}")
            self._emit_line(f"ldarg {key}")
        elif isinstance(current_type, ResolvedArray):
            self._comment(f"load array {key}")
            self._emit_line(f"ldloc {key}")
        else:
            self._comment(f"load variable address {key}")
            self._emit_line(f"ldloca {key}")



        components = target.components
        for i, comp in enumerate(components):
            self._comment(f"store component {i}: {comp} of type {current_type}")
            is_last = i == len(components) - 1


            if isinstance(current_type, ResolvedArray):
                elem = current_type.element
                self._comment(f"\tcalculate array index: {comp}")
                if isinstance(comp, StaticAccess):
                    self._emit_line(f"ldc.i4 {comp.index}")
                elif isinstance(comp, DynamicAccess):
                    self._emit_push_expr_on_stack(comp.expr)

                if is_last:
                    self._comment(f"\tcalculate value: {stmt.value} of type {elem}")
                    self._emit_push_expr_on_stack(stmt.value)
                    self._comment("\tstore element in array")
                    self._emit_stelem(elem)
                    return
                else:
                    # Navigate: ldelema for value-type elements, ldelem for ref
                    self._comment(f"load element {elem}")
                    if isinstance(elem, ResolvedRecord):
                        self._emit_line(f"ldelema {cil_type(elem)}")
                    else:
                        self._emit_ldelem(elem)
                    current_type = elem
            elif isinstance(current_type, ResolvedRecord):
                if not isinstance(comp, StaticAccess):
                    raise EmitError("Can only reference record members by static index")
                if comp.index < 0 or comp.index >= len(current_type.fields):
                    raise EmitError("Record index out of range")
                field_type = current_type.fields[comp.index]
                field_name = f"f_{comp.index}"
                if is_last:
                    self._emit_push_expr_on_stack(stmt.value)
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
                if issubclass(current_type, ResolvedBitSeq):
                    self._emit_line(f"ldc.i4 {comp.index}")
                elif isinstance(comp, DynamicAccess):
                    self._emit_push_expr_on_stack(comp.expr)
                if is_last:
                    self._emit_push_expr_on_stack(stmt.value)
                    self._emit_line("stelem.i4")
                    return
                else:
                    self._emit_line("ldelem.i4")
                    current_type = ResolvedBit()

    def _emit_guarded(self, stmt: GuardedStmt) -> None:
        lbl_end = self._labels.next("GEND")
        # Push condition
        self._emit_push_expr_on_stack(stmt.condition)
        self._emit_line(f"brfalse {lbl_end}")
        # Body
        for s in stmt.body:
            self._emit_stmt(s)
        self._emit_line(f"{lbl_end}:")

    def _emit_w_loop(self, stmt: WLoop) -> None:
        lbl_top = self._labels.next("WTOP")
        lbl_end = self._labels.next("WEND")
        self._emit_line(f"{lbl_top}:")

        # Частный случай для тела с одним оператором
        if len(stmt.body) == 1 and isinstance(stmt.body[0], GuardedStmt):
            s = stmt.body[0]
            self._comment("check guard condition")
            self._emit_push_expr_on_stack(s.condition)
            self._comment("if false exit loop")
            self._emit_line(f"brfalse {lbl_end}")
            for inner in s.body:
                self._emit_stmt(inner)
            self._emit_line(f"br {lbl_top}")
            self._emit_line(f"{lbl_end}:")
        # Общий случай
        else:
            self._comment("any_fired = false")
            self._emit_line("ldc.i4.0")  # any_fired = false
            for s in stmt.body:
                if isinstance(s, GuardedStmt):
                    lbl_skip = self._labels.next("WSKIP")
                    # Save current "any_fired" on stack, eval condition
                    self._comment("check guard condition")
                    self._emit_push_expr_on_stack(s.condition)
                    self._comment("if false skip guard body")
                    self._emit_line(f"brfalse {lbl_skip}")
                    # Guard fired — set any_fired = true
                    self._comment("any_fired = true")
                    self._emit_line("pop")       # pop old flag
                    self._emit_line("ldc.i4.1")  # push true
                    for inner in s.body:
                        self._emit_stmt(inner)
                    self._emit_line(f"{lbl_skip}:")
                else:
                    # Non-guarded statement in W-loop (always executes, always "fires")
                    self._comment("any_fired = true")
                    self._emit_line("pop")       # pop old flag
                    self._emit_line("ldc.i4.1")  # set flag = true
                    self._emit_stmt(s)

            # If any_fired is true, loop again
            self._emit_line(f"brtrue {lbl_top}")
            self._emit_line(f"{lbl_end}:")

    def _emit_for_loop(self, stmt: ForLoop) -> None:
        lbl_top = self._labels.next("FTOP")
        lbl_end = self._labels.next("FEND")

        # Initialize loop variable
        self._comment(f"start for {stmt.var} from {stmt.start} to {stmt.end}")
        self._emit_push_expr_on_stack(stmt.start)
        self._emit_store_from_stack_to_var(stmt.var)

        self._emit_line(f"{lbl_top}:")
        # Check: var <= end
        self._emit_load_var(stmt.var)
        self._emit_push_expr_on_stack(stmt.end)
        self._emit_line(f"bgt {lbl_end}")

        # Body
        for s in stmt.body:
            self._emit_stmt(s)

        # Increment loop variable
        self._emit_load_var(stmt.var)
        self._emit_line("ldc.i4.1")
        self._emit_line("add")
        self._emit_store_from_stack_to_var(stmt.var)

        self._emit_line(f"br {lbl_top}")
        self._comment(f"end for {stmt.var} from {stmt.start} to {stmt.end}")
        self._emit_line(f"{lbl_end}:")

    # -- expression emission ------------------------------------------------

    def _emit_push_expr_on_stack(self, expr: ExprNode) -> None:
        if isinstance(expr, IntLiteral):
            self._emit_line(f"ldc.i4 {expr}")
        elif isinstance(expr, BoolLiteral):
            self._emit_line("ldc.i4.1" if expr.value else "ldc.i4.0")
        elif isinstance(expr, BitSeqLiteral):
            # Convert bit sequence to integer
            val = 0
            for b in expr.bits:
                val = (val << 1) | (1 if b else 0)
            self._emit_line(f"ldc.i4 {val}")
        elif isinstance(expr, VarRef):
            self._emit_load_var(expr)
        elif isinstance(expr, BinaryExpr):
            self._emit_binop(expr)
        elif isinstance(expr, UnaryExpr):
            self._emit_push_expr_on_stack(expr.operand)
            if expr.op == UnOp.NOT:
                self._emit_line("ldc.i4.0")
                self._emit_line("ceq")
            elif expr.op == UnOp.NEG:
                self._emit_line("neg")
        elif isinstance(expr, FuncCall):
            self._emit_func_call(expr)

    def _emit_binop(self, expr: BinaryExpr) -> None:
        if expr.op != BinOp.POW:
            self._emit_push_expr_on_stack(expr.left)
            self._emit_push_expr_on_stack(expr.right)
        match expr.op:
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
                self._emit_push_expr_on_stack(expr.left)
                self._emit_line("conv.r8")
                self._emit_push_expr_on_stack(expr.right)
                self._emit_line("conv.r8")
                self._emit_line("call float64 [System.Runtime]System.Math::Pow(float64, float64)")
                self._emit_line("conv.i4")

    def _emit_func_call(self, expr: FuncCall) -> None:
        # Push arguments
        for arg in expr.args:
            self._emit_push_expr_on_stack(arg)

        # Resolve method name
        method_name = self._program_methods.get(expr.name, expr.name)

        # Build method signature
        psym = self._analyzer.programs.get(expr.name)
        if psym is None:
            # Try by name
            for key, sym in self._analyzer.programs.items():
                if sym.name == expr.name:
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
            self._emit_line(f"// WARNING: unresolved call to {expr.name}")

    # -- load/store helpers -------------------------------------------------

    def _emit_load_var(self, ref: VarRef) -> None:
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
                            self._emit_push_expr_on_stack(comp.expr)
                        # Use ldelema if next access is a record field
                        if isinstance(elem, ResolvedRecord) and i + 1 < len(ref.components):
                            self._emit_line(f"ldelema {cil_type(elem)}")
                        else:
                            self._emit_ldelem(elem)
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
                            self._emit_push_expr_on_stack(comp.expr)
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

    def _emit_store_from_stack_to_var(self, ref: VarRef) -> None:
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
    def _emit_ldelem(self, elem_type: ResolvedType) -> None:
        cil_elem_type = cil_type(elem_type)
        if cil_elem_type == 'bool':
            self._emit_line("ldelem.i1")
        elif cil_elem_type == 'int32':
            self._emit_line("ldelem.i4")
        elif cil_elem_type == 'int64':
            self._emit_line("ldelem.i8")
        else:
            self._emit_line(f"ldelem {cil_elem_type}")

    def _emit_stelem(self, elem_type: ResolvedType) -> None:
        cil_elem_type = cil_type(elem_type)
        if cil_elem_type == 'bool':
            self._emit_line("stelem.i1")
        elif cil_elem_type == 'int32':
            self._emit_line("stelem.i4")
        elif cil_elem_type == 'int64':
            self._emit_line("stelem.i8")
        else:
            self._emit_line(f"stelem {cil_elem_type}")

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

    def _emit_main(self, program: ProgramSymbol) -> None:
        """Emit a Main method that calls the first program.

        Parses command-line args as int32 arguments. If not enough args
        are provided, uses 0 as default.
        """
        key = program.key

        method_name = self._program_methods[key]

        self._emit_line(f".method public static void Main(string[] args)")
        self._emit_line("{")
        self._indent += 1
        self._emit_line(".entrypoint")
        self._emit_line(".maxstack 16")

        # Declare locals if needed for multi-result
        if len(program.results) > 1:
            ret_record = ResolvedRecord(tuple(program.results))
            self._emit_line(f".locals init ({cil_type(ret_record)} _mret)")

        # For each parameter, try to parse args[i]; fallback to 0
        for i, pt in enumerate(program.params):
            lbl_ok = self._labels.next("AROK")
            lbl_default = self._labels.next("ARDF")
            # if (i < args.Length) goto parse; else goto default
            self._comment(f"if {i} >= args.length goto {lbl_default}")
            self._emit_line(f"ldc.i4 {i}")
            self._emit_line("ldarg.0")
            self._emit_line("ldlen")
            self._emit_line("conv.i4")
            self._emit_line(f"bge {lbl_default}")
            # parse: Int32.Parse(args[i])
            self._comment(f"parse argument {i} by loading arg and parsing it")
            self._emit_line("ldarg.0")
            self._emit_line(f"ldc.i4 {i}")
            self._emit_line("ldelem.ref")
            self._emit_line("call int32 [System.Runtime]System.Int32::Parse(string)")
            self._emit_line(f"br {lbl_ok}")
            # default: push 0
            self._emit_line(f"{lbl_default}:")
            self._emit_line("ldc.i4.0")
            self._emit_line(f"{lbl_ok}:")

        param_types_str = ", ".join(cil_type(pt) for pt in program.params)
        if len(program.results) > 1:
            ret_record = ResolvedRecord(tuple(program.results))
            ret_type = cil_type(ret_record)
        elif program.results:
            ret_type = cil_type(program.results[0])
        else:
            ret_type = "void"
        self._emit_line(f"call {ret_type} PlankalkulProgram::{method_name}({param_types_str})")

        # Print result if there is one
        if len(program.results) > 1:
            # Multi-result: print first field of the struct
            ret_record = ResolvedRecord(tuple(program.results))
            self._emit_line("stloc _mret")
            self._emit_line("ldloca _mret")
            self._emit_line(
                f"ldfld {cil_type(program.results[0])} {cil_type(ret_record)}::f_0"
            )
            self._emit_line(
                "call void [System.Console]System.Console::WriteLine(int32)"
            )
        elif program.results:
            self._emit_line(
                "call void [System.Console]System.Console::WriteLine(int32)"
            )
        self._emit_line("ret")

        self._indent -= 1
        self._emit_line("}")
