"""Semantic analysis: symbol resolution, type checking, and validation.

Walks the AST produced by the parser, resolves user-defined types,
checks type compatibility, and attaches resolved type info to nodes.
Reports all errors without stopping at the first one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from plankalkulsharp.my_ast.nodes import (
    ArrayType,
    Assignment,
    BinOp,
    BinaryExpr,
    BitSeqType,
    BitType,
    BoolLiteral,
    BitSeqLiteral,
    ComponentAccess,
    DynamicAccess,
    ExprNode,
    ForLoop,
    FuncCall,
    GuardedStmt,
    IntLiteral,
    Loc,
    Program,
    ProgramDef,
    RecordType,
    StaticAccess,
    StmtNode,
    TypeDef,
    TypeNode,
    UnOp,
    UnaryExpr,
    UserType,
    VarRef,
    WLoop,
)


# ---------------------------------------------------------------------------
# Semantic error
# ---------------------------------------------------------------------------

class SemanticError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


# ---------------------------------------------------------------------------
# Resolved type representation (structural equality)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResolvedBit:
    """S0 — single bit."""
    pass

    def __str__(self) -> str:
        return "S0"


@dataclass(frozen=True)
class ResolvedBitSeq:
    """S1·n — bit sequence."""
    length: int

    def __str__(self) -> str:
        return f"S1.{self.length}"


@dataclass(frozen=True)
class ResolvedArray:
    """n × T."""
    size: int
    element: ResolvedType

    def __str__(self) -> str:
        return f"{self.size}x{self.element}"


@dataclass(frozen=True)
class ResolvedRecord:
    """(T1, T2, ...)."""
    fields: tuple[ResolvedType, ...]

    def __str__(self) -> str:
        inner = ", ".join(str(f) for f in self.fields)
        return f"({inner})"


ResolvedType = ResolvedBit | ResolvedBitSeq | ResolvedArray | ResolvedRecord

# Integer type is syntactic sugar for a bit-sequence of appropriate width.
# We treat integers as bit-sequences during type checking.


# ---------------------------------------------------------------------------
# Symbol table
# ---------------------------------------------------------------------------

@dataclass
class VarSymbol:
    kind: str       # V, Z, C, R
    index: int
    resolved_type: ResolvedType


@dataclass
class ProgramSymbol:
    number: int
    sub_number: int | None
    name: str | None
    params: list[ResolvedType]
    results: list[ResolvedType]


@dataclass
class Scope:
    """Per-program scope with local variable bindings."""
    vars: dict[str, VarSymbol] = field(default_factory=dict)
    _assigned_constants: set[str] = field(default_factory=set)

    def lookup(self, kind: str, index: int) -> VarSymbol | None:
        return self.vars.get(f"{kind}{index}")

    def define(self, kind: str, index: int, rtype: ResolvedType) -> VarSymbol:
        key = f"{kind}{index}"
        sym = VarSymbol(kind, index, rtype)
        self.vars[key] = sym
        return sym

    def mark_c_assigned(self, index: int) -> bool:
        """Mark a C-variable as assigned. Returns False if already assigned."""
        key = f"C{index}"
        if key in self._assigned_constants:
            return False
        self._assigned_constants.add(key)
        return True


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class Analyzer:
    """Single-pass semantic analyzer over a parsed AST."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.type_defs: dict[int, ResolvedType] = {}
        self.programs: dict[str, ProgramSymbol] = {}  # key: "P<n>" or "P<n>.<m>"
        self._scope: Scope | None = None
        self._current_program_key: str | None = None

    # -- public interface ---------------------------------------------------

    def analyze(self, program: Program) -> None:
        """Run semantic analysis. Raises SemanticError on failure."""
        # Phase 1: register all type definitions
        for td in program.type_defs:
            self._register_type_def(td)
        # Phase 2: register all program signatures (for forward calls)
        for pd in program.program_defs:
            self._register_program_sig(pd)
        # Phase 3: check each program body
        for pd in program.program_defs:
            self._check_program(pd)

        if self.errors:
            raise SemanticError(self.errors)

    # -- error reporting ----------------------------------------------------

    def _error(self, loc: Loc, msg: str) -> None:
        self.errors.append(f"{loc}: {msg}")

    # -- type resolution ----------------------------------------------------

    def resolve_type_node(self, tn: TypeNode) -> ResolvedType | None:
        """Convert an AST TypeNode to a ResolvedType."""
        if isinstance(tn, BitType):
            return ResolvedBit()
        if isinstance(tn, BitSeqType):
            return ResolvedBitSeq(tn.length)
        if isinstance(tn, ArrayType):
            elem = self.resolve_type_node(tn.element_type)
            if elem is None:
                return None
            # n × S0 ≡ S1·n (Plankalkül convention)
            if isinstance(elem, ResolvedBit):
                return ResolvedBitSeq(tn.size)
            return ResolvedArray(tn.size, elem)
        if isinstance(tn, RecordType):
            fields: list[ResolvedType] = []
            for f in tn.fields:
                r = self.resolve_type_node(f)
                if r is None:
                    return None
                fields.append(r)
            return ResolvedRecord(tuple(fields))
        if isinstance(tn, UserType):
            if tn.index not in self.type_defs:
                self._error(tn.loc, f"undefined type A{tn.index}")
                return None
            return self.type_defs[tn.index]
        self._error(tn.loc, f"unknown type node: {type(tn).__name__}")
        return None

    # -- Phase 1: type definitions ------------------------------------------

    def _register_type_def(self, td: TypeDef) -> None:
        if td.index in self.type_defs:
            self._error(td.loc, f"duplicate type definition A{td.index}")
            return
        resolved = self.resolve_type_node(td.type_expr)
        if resolved is not None:
            self.type_defs[td.index] = resolved

    # -- Phase 2: program signatures ----------------------------------------

    def _program_key(self, pd: ProgramDef) -> str:
        if pd.sub_number is not None:
            return f"P{pd.number}.{pd.sub_number}"
        return f"P{pd.number}"

    def _register_program_sig(self, pd: ProgramDef) -> None:
        key = self._program_key(pd)
        if key in self.programs:
            self._error(pd.loc, f"duplicate program definition {key}")
            return

        param_types: list[ResolvedType] = []
        for v in pd.params:
            if v.type_ann is None:
                self._error(v.loc, f"parameter {v.kind}{v.index} missing type annotation")
                continue
            rt = self.resolve_type_node(v.type_ann)
            if rt is not None:
                param_types.append(rt)

        result_types: list[ResolvedType] = []
        for v in pd.results:
            if v.type_ann is None:
                self._error(v.loc, f"result {v.kind}{v.index} missing type annotation")
                continue
            rt = self.resolve_type_node(v.type_ann)
            if rt is not None:
                result_types.append(rt)

        self.programs[key] = ProgramSymbol(
            number=pd.number,
            sub_number=pd.sub_number,
            name=pd.name,
            params=param_types,
            results=result_types,
        )

    # -- Phase 3: program body check ----------------------------------------

    def _check_program(self, pd: ProgramDef) -> None:
        scope = Scope()
        self._scope = scope
        self._current_program_key = self._program_key(pd)

        # Define params (V variables)
        for v in pd.params:
            if v.type_ann is None:
                continue
            rt = self.resolve_type_node(v.type_ann)
            if rt is not None:
                scope.define(v.kind, v.index, rt)

        # Define results (R variables)
        for v in pd.results:
            if v.type_ann is None:
                continue
            rt = self.resolve_type_node(v.type_ann)
            if rt is not None:
                scope.define(v.kind, v.index, rt)

        # Check body statements
        for stmt in pd.body:
            self._check_stmt(stmt)

        self._scope = None
        self._current_program_key = None

    # -- statement checking -------------------------------------------------

    def _check_stmt(self, stmt: StmtNode) -> None:
        if isinstance(stmt, Assignment):
            self._check_assignment(stmt)
        elif isinstance(stmt, GuardedStmt):
            self._check_guarded(stmt)
        elif isinstance(stmt, WLoop):
            for s in stmt.body:
                self._check_stmt(s)
        elif isinstance(stmt, ForLoop):
            self._check_for_loop(stmt)

    def _check_assignment(self, stmt: Assignment) -> None:
        val_type = self._check_expr(stmt.value)
        tgt_type = self._resolve_var_type(stmt.target)

        # C-variable immutability: only one assignment allowed
        if stmt.target.kind == "C" and self._scope is not None:
            if not self._scope.mark_c_assigned(stmt.target.index):
                self._error(
                    stmt.loc,
                    f"constant C{stmt.target.index} has already been assigned "
                    f"(C-variables are immutable)",
                )

        if val_type is not None and tgt_type is not None:
            if not self._types_compatible(val_type, tgt_type):
                self._error(
                    stmt.loc,
                    f"type mismatch in assignment: {val_type} cannot be assigned to {tgt_type}",
                )

    def _check_guarded(self, stmt: GuardedStmt) -> None:
        cond_type = self._check_expr(stmt.condition)
        if cond_type is not None and not isinstance(cond_type, ResolvedBit):
            self._error(
                stmt.condition.loc,
                f"guard condition must be S0 (bit/boolean), got {cond_type}",
            )
        for s in stmt.body:
            self._check_stmt(s)

    def _check_for_loop(self, stmt: ForLoop) -> None:
        # The loop variable must be an integer type (bit-sequence)
        var_type = self._resolve_var_type(stmt.var)

        start_type = self._check_expr(stmt.start)
        end_type = self._check_expr(stmt.end)

        for s in stmt.body:
            self._check_stmt(s)

    # -- expression type inference ------------------------------------------

    def _check_expr(self, expr: ExprNode) -> ResolvedType | None:
        if isinstance(expr, IntLiteral):
            # Integer literals: infer as S1·8 (byte) by default
            return ResolvedBitSeq(8)
        if isinstance(expr, BoolLiteral):
            return ResolvedBit()
        if isinstance(expr, BitSeqLiteral):
            return ResolvedBitSeq(len(expr.bits))
        if isinstance(expr, VarRef):
            return self._resolve_var_type(expr)
        if isinstance(expr, BinaryExpr):
            return self._check_binary(expr)
        if isinstance(expr, UnaryExpr):
            return self._check_unary(expr)
        if isinstance(expr, FuncCall):
            return self._check_func_call(expr)
        self._error(expr.loc, f"unsupported expression: {type(expr).__name__}")
        return None

    def _check_binary(self, expr: BinaryExpr) -> ResolvedType | None:
        left = self._check_expr(expr.left)
        right = self._check_expr(expr.right)

        if left is None or right is None:
            return None

        # Comparison operators always return S0
        if expr.op in (BinOp.EQ, BinOp.NEQ, BinOp.LT, BinOp.GT, BinOp.LE, BinOp.GE):
            return ResolvedBit()

        # Boolean operators require S0 operands, return S0
        if expr.op in (BinOp.AND, BinOp.OR):
            if not isinstance(left, ResolvedBit):
                self._error(expr.left.loc, f"boolean operator requires S0, got {left}")
            if not isinstance(right, ResolvedBit):
                self._error(expr.right.loc, f"boolean operator requires S0, got {right}")
            return ResolvedBit()

        # Arithmetic operators: operands should be bit-sequences (integers)
        return left  # result has same type as left operand

    def _check_unary(self, expr: UnaryExpr) -> ResolvedType | None:
        operand = self._check_expr(expr.operand)
        if operand is None:
            return None
        if expr.op == UnOp.NOT:
            if not isinstance(operand, ResolvedBit):
                self._error(expr.operand.loc, f"NOT requires S0, got {operand}")
            return ResolvedBit()
        if expr.op == UnOp.NEG:
            return operand
        return None

    def _check_func_call(self, expr: FuncCall) -> ResolvedType | None:
        # Resolve the called program
        name = expr.name
        psym: ProgramSymbol | None = None

        # Try direct program reference: P<n>
        if name in self.programs:
            psym = self.programs[name]
        else:
            # Try matching by name
            for key, sym in self.programs.items():
                if sym.name == name:
                    psym = sym
                    break

        if psym is None:
            self._error(expr.loc, f"undefined program or function '{name}'")
            return None

        # Check argument count
        if len(expr.args) != len(psym.params):
            self._error(
                expr.loc,
                f"'{name}' expects {len(psym.params)} argument(s), got {len(expr.args)}",
            )

        # Check argument types
        for i, arg in enumerate(expr.args):
            arg_type = self._check_expr(arg)
            if arg_type is not None and i < len(psym.params):
                if not self._types_compatible(arg_type, psym.params[i]):
                    self._error(
                        arg.loc,
                        f"argument {i} type mismatch: {arg_type} vs {psym.params[i]}",
                    )

        # Return type: single result directly, multi-result as record
        if len(psym.results) > 1:
            return ResolvedRecord(tuple(psym.results))
        if psym.results:
            return psym.results[0]
        return ResolvedBit()

    # -- variable type resolution -------------------------------------------

    def _resolve_var_type(self, ref: VarRef) -> ResolvedType | None:
        assert self._scope is not None
        sym = self._scope.lookup(ref.kind, ref.index)

        if sym is None:
            # Cross-program R<N>: reference to a parameterless program's result
            if ref.kind == "R":
                program_key = f"P{ref.index}"
                if (
                    program_key != self._current_program_key
                    and program_key in self.programs
                ):
                    cprog = self.programs[program_key]
                    if len(cprog.params) == 0 and cprog.results:
                        if len(cprog.results) > 1:
                            base = ResolvedRecord(tuple(cprog.results))
                        else:
                            base = cprog.results[0]
                        return self._apply_component_access(
                            base, ref.components, ref.loc
                        )

            # First assignment = declaration: define with type annotation
            if ref.type_ann is not None:
                rt = self.resolve_type_node(ref.type_ann)
                if rt is not None:
                    self._scope.define(ref.kind, ref.index, rt)
                    return self._apply_component_access(rt, ref.components, ref.loc)
                return None
            self._error(ref.loc, f"undefined variable {ref.kind}{ref.index} (no type annotation)")
            return None

        base_type = sym.resolved_type
        return self._apply_component_access(base_type, ref.components, ref.loc)

    def _apply_component_access(
        self,
        base: ResolvedType,
        components: tuple[ComponentAccess, ...],
        loc: Loc,
    ) -> ResolvedType | None:
        current = base
        for comp in components:
            if isinstance(comp, StaticAccess):
                if isinstance(current, ResolvedRecord):
                    if 0 <= comp.index < len(current.fields):
                        current = current.fields[comp.index]
                    else:
                        self._error(
                            comp.loc,
                            f"record field index {comp.index} out of range "
                            f"(0..{len(current.fields) - 1})",
                        )
                        return None
                elif isinstance(current, ResolvedArray):
                    current = current.element
                elif isinstance(current, ResolvedBitSeq):
                    current = ResolvedBit()
                else:
                    self._error(comp.loc, f"cannot access component of {current}")
                    return None
            elif isinstance(comp, DynamicAccess):
                self._check_expr(comp.expr)
                if isinstance(current, ResolvedArray):
                    current = current.element
                elif isinstance(current, ResolvedBitSeq):
                    current = ResolvedBit()
                else:
                    self._error(comp.loc, f"cannot index into {current}")
                    return None
        return current

    # -- type compatibility -------------------------------------------------

    @staticmethod
    def _types_compatible(source: ResolvedType, target: ResolvedType) -> bool:
        """Check structural type compatibility for assignment."""
        # Integer literals (S1·n) are compatible with any bit-sequence
        if isinstance(source, ResolvedBitSeq) and isinstance(target, ResolvedBitSeq):
            return True
        # S0 ↔ S0
        if isinstance(source, ResolvedBit) and isinstance(target, ResolvedBit):
            return True
        # Integer literal or bit-sequence → S0 (0/1 are valid bit values)
        if isinstance(source, ResolvedBitSeq) and isinstance(target, ResolvedBit):
            return True
        # S0 → bit-sequence (widen bit to integer)
        if isinstance(source, ResolvedBit) and isinstance(target, ResolvedBitSeq):
            return True
        # Array: same size and compatible elements
        if isinstance(source, ResolvedArray) and isinstance(target, ResolvedArray):
            return source.size == target.size and Analyzer._types_compatible(
                source.element, target.element
            )
        # Record: same number of fields, each compatible
        if isinstance(source, ResolvedRecord) and isinstance(target, ResolvedRecord):
            if len(source.fields) != len(target.fields):
                return False
            return all(
                Analyzer._types_compatible(s, t)
                for s, t in zip(source.fields, target.fields)
            )
        return False
