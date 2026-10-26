"""CIL text assembly emitter for Plankalkül programs.

Produces .il libraries loaded by the shared Plankalkül worker.
Each Plankalkül program becomes a static method. Types are mapped to
appropriate CLR types.
"""

from __future__ import annotations

from io import StringIO
from dataclasses import replace
import json
from importlib.metadata import version, PackageNotFoundError

from plankalkulsharp.plankalkul_ast.nodes import (
    Assignment, ListLiteral, RecordLiteral,
    Allocate,
    BinOp,
    BinaryExpr,
    BitSeqLiteral,
    BoolLiteral,
    DynamicAccess,
    DereferenceAccess,
    ExprNode,
    IndexedLoop, IndexRef, Fin,
    FuncCall,
    Free,
    GuardedStmt,
    IntLiteral,
    NilLiteral,
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
    ResolvedRef,
    ResolvedNil,
    ResolvedType, ProgramSymbol,
)
from plankalkulsharp.semantic.layout import heap_layout


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
    if isinstance(rt, (ResolvedRef, ResolvedNil)):
        return "int64"
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
        self._heap_ids = {name: i + 1 for i, name in enumerate(sorted(analyzer.heap_types))}

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

        # The worker owns the heap and invokes this module's public entry point.
        min_program = min(
            self._analyzer.programs.values(),
            key=lambda p: p.number
        )
        self._emit_metadata()
        self._emit_entry_body(min_program)

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
        for rt in self._analyzer.expr_types.values():
            visit(rt)
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
        self._emit_line(".assembly extern PlankalkulRuntime { }")
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
            param_strs.append(f"{cil_type(pt)} V_{pd.params[i].index}")

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
        self._exit_labels = {}
        self._index_locals = {}
        return_label = self._labels.next("RETURN")
        self._exit_labels[("procedure", id(pd))] = return_label

        # Pre-scan body to collect local variables
        self._collect_locals(program)

        # Render instructions first so heap reads/copies can declare their scratch locals.
        outer_output = self._out
        self._out = StringIO()
        self._emit_checkpoint(pd.loc)
        for stmt in pd.body:
            self._emit_stmt(stmt)
        body_output = self._out.getvalue()
        self._out = outer_output

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
            if isinstance(rt, (ResolvedArray, ResolvedRecord)) and not var_key.startswith("_tmp"):
                self._emit_line("ldnull")
                self._emit_value_copy(rt)
                self._emit_line(f"stloc {var_key}")

        # Emit body
        self._out.write(body_output)

        self._emit_line(f"{return_label}:")
        self._comment("return result")
        # Return result(s)
        if len(program.results) > 1:
            # Multi-result: populate the return struct and return it
            ret_record = ResolvedRecord(tuple(program.results))
            for i, rt in enumerate(program.results):
                self._emit_line("ldloca _ret")
                self._emit_line(f"ldloc R_{pd.results[i].index}")
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
        self._emit_checkpoint(stmt.loc)
        if isinstance(stmt, Assignment):
            self._emit_assignment(stmt)
        elif isinstance(stmt, GuardedStmt):
            self._emit_guarded(stmt)
        elif isinstance(stmt, WLoop):
            self._emit_w_loop(stmt)
        elif isinstance(stmt, IndexedLoop):
            self._emit_indexed_loop(stmt)
        elif isinstance(stmt, Fin):
            kind, owner = self._analyzer.fin_targets[id(stmt)]
            target = self._exit_labels[(kind, id(owner))]
            if stmt.condition is None:
                self._emit_line(f"br {target}")
            else:
                self._emit_push_expr_on_stack(stmt.condition)
                self._emit_line(f"brtrue {target}")
        elif isinstance(stmt, Free):
            self._emit_push_expr_on_stack(stmt.value)
            rt = self._expr_type(stmt.value)
            self._emit_line(f"ldc.i4 {self._heap_ids[rt.target] if isinstance(rt, ResolvedRef) else 0}")
            self._emit_location(stmt.loc)
            self._emit_line("call void [PlankalkulRuntime]PlankalkulRuntime.Heap::Free(int64, int32, string)")

    def _emit_assignment(self, stmt: Assignment) -> None:
        self._comment(f"assign {stmt.value} to {stmt.target}")
        if any(isinstance(c, DereferenceAccess) for c in stmt.target.components):
            handle, target, offset, rt = self._emit_heap_path(stmt.target)
            self._emit_expr_as(stmt.value, rt)
            self._emit_heap_write(handle, target, offset, rt, stmt.loc)
        elif stmt.target.components:
            self._emit_component_store(stmt)
        else:
            # Push value onto stack
            self._emit_expr_as(stmt.value, self._get_var_base_type(stmt.target))
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
            self._emit_line(f"{'ldarga' if isinstance(current_type, ResolvedRecord) else 'ldarg'} {key}")
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
                self._emit_list_index(comp)

                if is_last:
                    self._comment(f"\tcalculate value: {stmt.value} of type {elem}")
                    self._emit_expr_as(stmt.value, elem)
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
                    self._emit_expr_as(stmt.value, field_type)
                    self._emit_line(
                        f"stfld {cil_type(field_type)} {cil_type(current_type)}::{field_name}"
                    )
                    return
                else:
                    instruction = "ldflda" if isinstance(field_type, ResolvedRecord) else "ldfld"
                    self._emit_line(f"{instruction} {cil_type(field_type)} {cil_type(current_type)}::{field_name}")
                    current_type = field_type
            elif isinstance(current_type, ResolvedBitSeq):
                if issubclass(current_type, ResolvedBitSeq):
                    self._emit_line(f"ldc.i4 {comp.index}")
                elif isinstance(comp, DynamicAccess):
                    self._emit_push_expr_on_stack(comp.expr)
                    self._emit_line("conv.i")
                if is_last:
                    self._emit_push_expr_on_stack(stmt.value)
                    self._emit_line("stelem.i4")
                    return
                else:
                    self._emit_line("ldelem.i4")
                    current_type = ResolvedBit()

    def _emit_guarded(self, stmt: GuardedStmt, fired: str | None = None) -> None:
        end = self._labels.next("GEND")
        self._exit_labels[("block", id(stmt))] = end
        self._emit_push_expr_on_stack(stmt.condition)
        self._emit_line(f"brfalse {end}")
        if fired:
            self._emit_line("ldc.i4.1")
            self._emit_line(f"stloc {fired}")
        for child in stmt.body: self._emit_stmt(child)
        self._emit_line(f"{end}:")

    def _emit_w_loop(self, stmt: WLoop) -> None:
        top, end = self._labels.next("WTOP"), self._labels.next("WEND")
        self._exit_labels[("loop", id(stmt))] = end
        self._exit_labels[("iteration", id(stmt))] = top
        fired = self._temp(ResolvedBit())
        self._emit_line(f"{top}:")
        self._emit_checkpoint(stmt.loc)
        # No state is carried on the evaluation stack across statements: FIN
        # may jump past any number of blocks/loops to an empty-stack label.
        self._emit_line("ldc.i4.0")
        self._emit_line(f"stloc {fired}")
        for child in stmt.body:
            if isinstance(child, GuardedStmt):
                self._emit_checkpoint(child.loc)
                self._emit_guarded(child, fired)
            elif isinstance(child, Fin):
                # A false conditional FIN neither fires nor adds an exit scope.
                self._emit_stmt(child)
            else:
                self._emit_line("ldc.i4.1")
                self._emit_line(f"stloc {fired}")
                self._emit_stmt(child)
        self._emit_line(f"ldloc {fired}")
        self._emit_line(f"brtrue {top}")
        self._emit_line(f"{end}:")

    def _emit_indexed_loop(self, stmt: IndexedLoop) -> None:
        rt = self._analyzer.loop_types[id(stmt)]
        bounds = []
        for expr in stmt.bounds:
            local = self._temp(rt)
            literal = self._analyzer.literal_integer(expr)
            if literal is None:
                self._emit_expr_as(expr, rt)
            else:
                self._emit_line(f"ldc.i{8 if rt.length == 64 else 4} {literal}")
            self._emit_line(f"stloc {local}")
            bounds.append(local)
        index, step = self._temp(rt), self._temp(rt)
        self._index_locals[id(stmt)] = index
        top, advance, end, valid = [self._labels.next(p) for p in ("ITOP", "INEXT", "IEND", "IVALID")]
        self._exit_labels[("loop", id(stmt))] = end
        self._exit_labels[("iteration", id(stmt))] = advance
        def number(n):
            self._emit_line(f"ldc.i4 {n}")
            if rt.length == 64: self._emit_line("conv.i8")
        if stmt.variant <= 4:
            self._emit_line(f"ldloc {bounds[0]}")
            if stmt.variant <= 2: number(0)
            else: self._emit_line(f"ldloc {bounds[1]}")
            branch = "bge" if stmt.variant in (1, 2, 4) else "ble"
            self._emit_line(f"{branch} {valid}")
            self._emit_string(f"{self._analyzer.filename}:{stmt.loc.line}:{stmt.loc.column + 1}: invalid W{stmt.variant} bounds")
            self._emit_line("newobj instance void [System.Runtime]System.InvalidOperationException::.ctor(string)")
            self._emit_line("throw")
            self._emit_line(f"{valid}:")
        if stmt.variant == 1: number(0)
        else:
            self._emit_line(f"ldloc {bounds[0]}")
            if stmt.variant == 2:
                number(1); self._emit_line("sub")
        self._emit_line(f"stloc {index}")
        number(-1 if stmt.variant in (2, 4) else 1)
        self._emit_line(f"stloc {step}")
        if stmt.variant == 5:
            ascending = self._labels.next("IASC")
            self._emit_line(f"ldloc {bounds[0]}")
            self._emit_line(f"ldloc {bounds[1]}")
            self._emit_line(f"ble {ascending}")
            number(-1); self._emit_line(f"stloc {step}")
            self._emit_line(f"{ascending}:")
        self._emit_line(f"{top}:")
        self._emit_checkpoint(stmt.loc)
        self._emit_line(f"ldloc {index}")
        if stmt.variant == 2:
            number(0); self._emit_line(f"blt {end}")
        else:
            self._emit_line(f"ldloc {bounds[-1]}")
            self._emit_line(f"beq {end}")
        for child in stmt.body: self._emit_stmt(child)
        self._emit_line(f"{advance}:")
        self._emit_line(f"ldloc {index}")
        self._emit_line(f"ldloc {step}")
        self._emit_line("add")
        self._emit_line(f"stloc {index}")
        self._emit_line(f"br {top}")
        self._emit_line(f"{end}:")

    # -- expression emission ------------------------------------------------

    def _emit_push_expr_on_stack(self, expr: ExprNode) -> None:
        if isinstance(expr, ListLiteral):
            rt = self._expr_type(expr)
            self._emit_line(f"ldc.i4 {len(expr.elements)}")
            self._emit_line(f"newarr {cil_type(rt.element)}")
            for i, element in enumerate(expr.elements):
                self._emit_line("dup")
                self._emit_line(f"ldc.i4 {i}")
                self._emit_expr_as(element, rt.element)
                self._emit_stelem(rt.element)
        elif isinstance(expr, RecordLiteral):
            rt = self._expr_type(expr)
            local = self._temp(rt)
            for i, (element, field) in enumerate(zip(expr.elements, rt.fields)):
                self._emit_line(f"ldloca {local}")
                self._emit_expr_as(element, field)
                self._emit_line(f"stfld {cil_type(field)} {cil_type(rt)}::f_{i}")
            self._emit_line(f"ldloc {local}")
        elif isinstance(expr, Allocate):
            name = self._analyzer.canonical_names[expr.target]
            self._emit_line(f"ldc.i4 {self._heap_ids[name]}")
            self._emit_line(f"ldc.i4 {heap_layout(self._analyzer.heap_types[name]).size}")
            self._emit_string(name)
            self._emit_location(expr.loc)
            self._emit_line("call int64 [PlankalkulRuntime]PlankalkulRuntime.Heap::Allocate(int32, int32, string, string)")
        elif isinstance(expr, NilLiteral):
            self._emit_line("ldc.i8 0")
        elif isinstance(expr, IntLiteral):
            self._emit_integer(expr.value)
        elif isinstance(expr, BoolLiteral):
            self._emit_line("ldc.i4.1" if expr.value else "ldc.i4.0")
        elif isinstance(expr, BitSeqLiteral):
            # Convert bit sequence to integer
            val = 0
            for b in expr.bits:
                val = (val << 1) | (1 if b else 0)
            self._emit_integer(val)
        elif isinstance(expr, IndexRef):
            loop = self._analyzer.index_bindings[id(expr)]
            self._emit_line(f"ldloc {self._index_locals[id(loop)]}")
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
        if isinstance(self._expr_type(expr.left), (ResolvedArray, ResolvedRecord)):
            for operand in (expr.left, expr.right):
                self._emit_push_expr_on_stack(operand)
                self._box(self._expr_type(operand))
            self._emit_line("call bool [PlankalkulRuntime]PlankalkulRuntime.Values::Equal(object, object)")
            if expr.op == BinOp.NEQ:
                self._emit_line("ldc.i4.0")
                self._emit_line("ceq")
            return
        if expr.op != BinOp.POW:
            # CIL arithmetic/comparisons need operands of the same stack width.
            types = [self._expr_type(expr.left), self._expr_type(expr.right)]
            if expr.op in (BinOp.ADD, BinOp.SUB, BinOp.MUL, BinOp.DIV):
                types.append(self._expr_type(expr))
            width = ResolvedBitSeq(64 if any(cil_type(t) == "int64" for t in types) else 32)
            self._emit_expr_as(expr.left, width)
            self._emit_expr_as(expr.right, width)
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
        if expr.name == "N":
            self._emit_push_expr_on_stack(expr.args[0])
            self._emit_line("ldlen")
            self._emit_line("conv.i4")
            return
        if expr.name == "Lz":
            rt = self._expr_type(expr)
            for arg in expr.args:
                self._emit_expr_as(arg, ResolvedArray(None, rt.element))
            self._emit_line("call object [PlankalkulRuntime]PlankalkulRuntime.Values::Concat(class [System.Runtime]System.Array, class [System.Runtime]System.Array)")
            self._emit_line(f"castclass {cil_type(rt)}")
            return
        library = self._analyzer.library_calls.get(id(expr))
        if library is not None:
            from plankalkulsharp.standard_library import catalog
            specification = catalog()[expr.name]
            static_positions = {p["argument"] for p in specification.get("static", [])}
            arguments = [a for i, a in enumerate(expr.args) if i not in static_positions]
            temps = []
            for argument, target in zip(arguments, library.params):
                self._emit_expr_as(argument, target)
                temp = self._temp(target)
                self._emit_line(f"stloc {temp}")
                temps.append(temp)
            for contract in specification.get("contracts", []):
                self._emit_string(json.dumps(contract))
                self._emit_line(f"ldc.i4 {len(temps)}")
                self._emit_line("newarr [System.Runtime]System.Object")
                for i, (temp, rt) in enumerate(zip(temps, library.params)):
                    self._emit_line("dup")
                    self._emit_line(f"ldc.i4 {i}")
                    self._emit_line(f"ldloc {temp}")
                    self._box(rt)
                    self._emit_line("stelem.ref")
                self._emit_location(expr.loc)
                self._emit_line("call void [PlankalkulRuntime]PlankalkulRuntime.Values::CheckContract(string, object[], string)")
            for temp in temps:
                self._emit_line(f"ldloc {temp}")
            signature = ", ".join(cil_type(t) for t in library.params)
            self._emit_line(f"call {cil_type(library.results[0])} PlankalkulProgram::{library.name}({signature})")
            return
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
            for arg, target_type in zip(expr.args, psym.params):
                self._emit_expr_as(arg, target_type)
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
        if any(isinstance(c, DereferenceAccess) for c in ref.components):
            handle, target, offset, rt = self._emit_heap_path(ref)
            self._emit_heap_read(handle, target, offset, rt, ref.loc)
            return
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
                        self._emit_list_index(comp)
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
                            self._emit_line("conv.i")
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
    def _emit_list_index(self, comp):
        self._emit_line("dup")
        if isinstance(comp, StaticAccess):
            self._emit_line(f"ldc.i8 {comp.index}")
        else:
            self._emit_expr_as(comp.expr, ResolvedBitSeq(64))
        self._emit_location(comp.loc)
        self._emit_line("call int32 [PlankalkulRuntime]PlankalkulRuntime.Values::Index(class [System.Runtime]System.Array, int64, string)")

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
            if self._current_psym:
                symbol = self._current_psym.scope.lookup(ref.kind, ref.index)
                if symbol:
                    return symbol.resolved_type
            return None
        key = f"{ref.kind}_{ref.index}"
        if key in self._locals:
            _, base = self._locals[key]
            return base
        return None

    # -- checked native heap access -----------------------------------------

    def _temp(self, rt: ResolvedType) -> str:
        name = f"_tmp{self._local_index}"
        self._locals[name] = (self._local_index, rt)
        self._local_index += 1
        return name

    def _emit_string(self, value: str) -> None:
        escaped = value.replace('\\', '\\\\').replace('"', '\\"')
        escaped = escaped.replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t')
        self._emit_line(f'ldstr "{escaped}"')

    def _emit_location(self, loc) -> None:
        filename = self._analyzer.library_files.get(self._current_psym.key, getattr(self._analyzer, "filename", "<input>")) if self._current_psym else getattr(self._analyzer, "filename", "<input>")
        self._emit_string(f"{filename}:{loc.line}:{loc.column}")

    def _expr_type(self, expr: ExprNode) -> ResolvedType:
        return self._analyzer.expr_types[id(expr)]

    def _emit_integer(self, value: int) -> None:
        if value.bit_length() > 64:
            raise EmitError("integer literal exceeds 64 bits")
        width = 32 if value.bit_length() <= 32 else 64
        signed = value if value < (1 << (width - 1)) else value - (1 << width)
        self._emit_line(f"ldc.i{width // 8} {signed}")

    def _emit_expr_as(self, expr: ExprNode, target: ResolvedType) -> None:
        self._emit_push_expr_on_stack(expr)
        self._convert_stack(self._expr_type(expr), target, expr.loc)

    @staticmethod
    def _shape(rt):
        if isinstance(rt, ResolvedArray):
            return {"size": rt.size, "element": CILEmitter._shape(rt.element)}
        if isinstance(rt, ResolvedRecord):
            return {"fields": [CILEmitter._shape(f) for f in rt.fields]}
        return {"reference": rt.target} if isinstance(rt, ResolvedRef) else {}

    def _box(self, rt):
        if not isinstance(rt, ResolvedArray):
            self._emit_line(f"box {cil_type(rt)}")

    def _emit_value_copy(self, target, loc=None):
        shape = self._shape(target)
        if self._current_psym:
            position = loc or self._current_psym.ast.loc
            filename = self._analyzer.library_files.get(self._current_psym.key, getattr(self._analyzer, "filename", "<input>"))
            shape["location"] = f"{filename}:{position.line}:{position.column}"
        self._emit_line(f"ldtoken {cil_type(target)}")
        self._emit_string(json.dumps(shape, separators=(",", ":")))
        self._emit_line("call object [PlankalkulRuntime]PlankalkulRuntime.Values::Copy(object, valuetype [System.Runtime]System.RuntimeTypeHandle, string)")
        self._emit_line(f"unbox.any {cil_type(target)}")

    def _convert_stack(self, source: ResolvedType, target: ResolvedType, loc=None) -> None:
        if isinstance(target, (ResolvedArray, ResolvedRecord)):
            self._box(source)
            self._emit_value_copy(target, loc)
            return
        if cil_type(source) == cil_type(target):
            return
        if cil_type(target) == "int64":
            self._emit_line("conv.i8")
        elif cil_type(source) == "int64":
            self._emit_line("conv.i4")

    def _var_type(self, ref: VarRef) -> ResolvedType:
        rt = self._get_var_base_type(ref)
        for comp in ref.components:
            if isinstance(comp, DereferenceAccess):
                rt = self._analyzer.heap_types[rt.target]
            elif isinstance(rt, ResolvedRecord):
                rt = rt.fields[comp.index]
            elif isinstance(rt, ResolvedArray):
                rt = rt.element
            else:
                rt = ResolvedBit()
        return rt

    def _emit_heap_path(self, ref: VarRef) -> tuple[str, str, int, ResolvedType]:
        first = next(i for i, c in enumerate(ref.components) if isinstance(c, DereferenceAccess))
        prefix = replace(ref, components=ref.components[:first])
        rt = self._var_type(prefix)
        self._emit_load_var(prefix)
        handle = self._temp(rt)
        self._emit_line(f"stloc {handle}")
        target = rt.target
        rt = self._analyzer.heap_types[target]
        offset = 0
        for comp in ref.components[first + 1:]:
            if isinstance(comp, DereferenceAccess):
                self._emit_heap_read(handle, target, offset, rt, comp.loc)
                target = rt.target
                handle = self._temp(rt)
                self._emit_line(f"stloc {handle}")
                rt = self._analyzer.heap_types[target]
                offset = 0
            else:
                offset += heap_layout(rt).offsets[comp.index]
                rt = rt.fields[comp.index]
        return handle, target, offset, rt

    def _emit_heap_args(self, handle: str, target: str, offset: int) -> None:
        self._emit_line(f"ldloc {handle}")
        self._emit_line(f"ldc.i4 {self._heap_ids[target]}")
        self._emit_line(f"ldc.i4 {offset}")

    @staticmethod
    def _heap_scalar(rt: ResolvedType) -> tuple[str, str]:
        if isinstance(rt, ResolvedBit):
            return "Byte", "int32"
        return ("Int64", "int64") if cil_type(rt) == "int64" else ("Int32", "int32")

    def _emit_heap_read(self, handle: str, target: str, offset: int, rt: ResolvedType, loc) -> None:
        if isinstance(rt, ResolvedRecord):
            result = self._temp(rt)
            layout = heap_layout(rt)
            for i, field in enumerate(rt.fields):
                self._emit_line(f"ldloca {result}")
                self._emit_heap_read(handle, target, offset + layout.offsets[i], field, loc)
                self._emit_line(f"stfld {cil_type(field)} {cil_type(rt)}::f_{i}")
            self._emit_line(f"ldloc {result}")
        else:
            suffix, stack_type = self._heap_scalar(rt)
            self._emit_heap_args(handle, target, offset)
            self._emit_location(loc)
            self._emit_line(f"call {stack_type} [PlankalkulRuntime]PlankalkulRuntime.Heap::Read{suffix}(int64, int32, int32, string)")

    def _emit_heap_write(self, handle: str, target: str, offset: int, rt: ResolvedType, loc) -> None:
        # Keep only the opaque handle across expression evaluation, never a native address.
        value = self._temp(rt)
        self._emit_line(f"stloc {value}")
        if isinstance(rt, ResolvedRecord):
            layout = heap_layout(rt)
            for i, field in enumerate(rt.fields):
                self._emit_line(f"ldloca {value}")
                self._emit_line(f"ldfld {cil_type(field)} {cil_type(rt)}::f_{i}")
                self._emit_heap_write(handle, target, offset + layout.offsets[i], field, loc)
        else:
            suffix, stack_type = self._heap_scalar(rt)
            self._emit_heap_args(handle, target, offset)
            self._emit_line(f"ldloc {value}")
            self._emit_location(loc)
            self._emit_line(f"call void [PlankalkulRuntime]PlankalkulRuntime.Heap::Write{suffix}(int64, int32, int32, {stack_type}, string)")

    # -- main entry point ---------------------------------------------------

    def _emit_checkpoint(self, loc) -> None:
        if self._current_psym and self._current_psym.key in self._analyzer.library_files:
            # Zero is an explicit non-user location. Control still works in loops,
            # without highlighting an unrelated line in the user's document.
            loc = replace(loc, line=0, column=0)
        # No native address survives this call. The worker may wait, inspect, or stop.
        self._emit_line(f"ldc.i4 {loc.line}")
        self._emit_line(f"ldc.i4 {loc.column}")
        self._emit_line("call void [PlankalkulRuntime]PlankalkulRuntime.Execution::Checkpoint(int32, int32)")

    def _describe_heap_layout(self, rt: ResolvedType) -> dict:
        layout = heap_layout(rt)
        result = {"size": layout.size}
        if isinstance(rt, ResolvedBit):
            return dict(result, kind="bit")
        if isinstance(rt, ResolvedBitSeq):
            return dict(result, kind="int32" if rt.length <= 32 else "int64", bits=rt.length)
        if isinstance(rt, ResolvedRef):
            return dict(result, kind="ref", targetTypeId=self._heap_ids[rt.target])
        if isinstance(rt, ResolvedRecord):
            return dict(result, kind="record", fields=[
                {"index": index, "offset": layout.offsets[index], "layout": self._describe_heap_layout(field)}
                for index, field in enumerate(rt.fields)
            ])
        raise EmitError(f"unsupported heap layout: {rt}")

    def module_metadata(self) -> dict:
        """Describe the native layout, never the CLR's physical struct layout."""
        try:
            compiler_version = version("plankalkulsharp")
        except PackageNotFoundError:
            compiler_version = "0.1.0"
        from plankalkulsharp.standard_library import fingerprint
        return {
            "standardLibrarySha256": fingerprint(),
            "abi": 1,
            "compilerVersion": compiler_version,
            "source": {
                "path": getattr(self._analyzer, "filename", "<input>"),
                "sha256": getattr(self._analyzer, "source_sha256", ""),
            },
            "heapTypes": [
                {"id": type_id, "name": name, "size": heap_layout(rt).size, "layout": self._describe_heap_layout(rt)}
                for name, type_id in self._heap_ids.items()
                for rt in [self._analyzer.heap_types[name]]
            ],
        }

    def _emit_metadata(self) -> None:
        self._emit_line(".method public static string GetMetadata()")
        self._emit_line("{")
        self._indent += 1
        self._emit_line(".maxstack 1")
        self._emit_string(json.dumps(self.module_metadata(), ensure_ascii=False, separators=(",", ":")))
        self._emit_line("ret")
        self._indent -= 1
        self._emit_line("}")

    def _emit_entry_body(self, program: ProgramSymbol) -> None:
        """Convert CLI JSON using declared types, then print every result."""
        self._current_psym = program
        self._emit_line(".method public static void Execute(string[] args)")
        self._emit_line("{")
        self._indent += 1
        self._emit_line(".maxstack 32")
        result = ResolvedRecord(tuple(program.results)) if len(program.results) > 1 else program.results[0]
        self._emit_line(f".locals init ({cil_type(result)} _result)")
        for i, pt in enumerate(program.params):
            fallback = self._labels.next("DEFAULT")
            done = self._labels.next("ARGUMENT")
            self._emit_line("ldarg.0")
            self._emit_line("ldlen")
            self._emit_line("conv.i4")
            self._emit_line(f"ldc.i4 {i}")
            self._emit_line(f"ble {fallback}")
            self._emit_line("ldarg.0")
            self._emit_line(f"ldc.i4 {i}")
            self._emit_line("ldelem.ref")
            self._emit_line(f"ldtoken {cil_type(pt)}")
            self._emit_string(json.dumps(self._shape(pt), separators=(",", ":")))
            self._emit_line("call object [PlankalkulRuntime]PlankalkulRuntime.Values::Parse(string, valuetype [System.Runtime]System.RuntimeTypeHandle, string)")
            self._emit_line(f"unbox.any {cil_type(pt)}")
            self._emit_line(f"br {done}")
            self._emit_line(f"{fallback}:")
            self._emit_line("ldnull")
            self._emit_value_copy(pt)
            self._emit_line(f"{done}:")
        signature = ", ".join(cil_type(pt) for pt in program.params)
        self._emit_line(f"call {cil_type(result)} PlankalkulProgram::{self._program_methods[program.key]}({signature})")
        self._emit_line("stloc _result")
        for i, rt in enumerate(program.results):
            if len(program.results) > 1:
                self._emit_line("ldloca _result")
                self._emit_line(f"ldfld {cil_type(rt)} {cil_type(result)}::f_{i}")
            else:
                self._emit_line("ldloc _result")
            self._box(rt)
            self._emit_line("call string [PlankalkulRuntime]PlankalkulRuntime.Values::Format(object)")
            self._emit_line("call void [System.Console]System.Console::WriteLine(string)")
        self._emit_line("ret")
        self._indent -= 1
        self._emit_line("}")
