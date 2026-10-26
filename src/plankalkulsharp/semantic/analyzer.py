"""Semantic analysis: symbol resolution, type checking, and validation.

Walks the AST produced by the parser, resolves user-defined types,
checks type compatibility, and attaches resolved type info to nodes.
Reports all errors without stopping at the first one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from plankalkulsharp.plankalkul_ast.nodes import (
    ArrayType, ListLiteral, RecordLiteral,
    Assignment,
    Allocate,
    BinOp,
    BinaryExpr,
    BitSeqType,
    BitType,
    BoolLiteral,
    BitSeqLiteral,
    ComponentAccess,
    DereferenceAccess,
    DynamicAccess,
    ExprNode,
    IndexedLoop, IndexRef, Fin,
    FuncCall,
    Free,
    GuardedStmt,
    IntLiteral,
    NilLiteral,
    Loc,
    Program,
    ProgramDef,
    RecordType,
    RefType,
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
    """0 — single bit."""

    def __str__(self) -> str:
        return "0"


@dataclass(frozen=True)
class ResolvedBitSeq:
    """n.0 — bit sequence."""
    length: int

    def __str__(self) -> str:
        return f"{self.length}.0"


@dataclass(frozen=True)
class ResolvedArray:
    """n x T."""
    size: int | None
    element: ResolvedType

    def __str__(self) -> str:
        return f"{self.size if self.size is not None else chr(42)}x{self.element}"


@dataclass(frozen=True)
class ResolvedRecord:
    """(T1, T2, ...)."""
    fields: tuple[ResolvedType, ...]

    def __str__(self) -> str:
        inner = ", ".join(str(f) for f in self.fields)
        return f"({inner})"


@dataclass(frozen=True)
class ResolvedRef:
    """An opaque reference to the canonical named heap type."""
    target: str

    def __str__(self) -> str:
        return f"@{self.target}"


@dataclass(frozen=True)
class ResolvedNil:
    """The untyped NIL literal; only assignable to a reference."""

    def __str__(self) -> str:
        return "NIL"


ResolvedType = ResolvedBit | ResolvedBitSeq | ResolvedArray | ResolvedRecord | ResolvedRef
ExpressionType = ResolvedType | ResolvedNil

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
    key: str
    number: int
    name: str | None
    params: list[ResolvedType]
    results: list[ResolvedType]
    ast: ProgramDef
    scope: Scope

    def __repr__(self):
        return f"P{self.number} {self.name} takes {self.params} results in {self.results} uses {self.scope.vars}"


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
        self.diagnostics: list[dict] = []
        self.warnings: list[str] = []
        self.type_defs: dict[str, ResolvedType] = {}
        self.canonical_names: dict[str, str] = {}
        self.heap_types: dict[str, ResolvedType] = {}
        self.expr_types: dict[int, ExpressionType] = {}
        self.index_bindings: dict[int, IndexedLoop] = {}
        self.loop_types: dict[int, ResolvedBitSeq] = {}
        self.fin_targets: dict[int, tuple[str, object]] = {}
        self._indices = {}
        self._exits = []
        self._after_fin = False
        self.programs: dict[str, ProgramSymbol] = {}
        self._scope: Scope | None = None
        self._type_asts: dict[str, TypeDef] = {}
        self._resolving_types: set[str] = set()
        self._ref_liveness: dict[str, str | None] = {}
        self._dead_refs: set[str] = set()
        self.library_calls = {}
        self.library_specializations = {}
        self.library_files = {}
        self._entry_number: int | None = None

    # -- public interface ---------------------------------------------------

    def report(self) -> None:
        """Print the analyzer report."""
        print('Errors:', self.errors)
        print('Warnings:', self.warnings)
        print('Type defs:', self.type_defs)
        print('Programs:', self.programs)

    def analyze(self, program: Program) -> None:
        """Run semantic analysis. Raises SemanticError on failure."""
        # Register every name before resolving bodies so references may be recursive.
        for td in program.type_defs:
            if td.name in self._type_asts:
                self._error(td.loc, f"duplicate type definition {td.name}")
            else:
                self._type_asts[td.name] = td
                self.canonical_names[td.name] = td.name
        for name, td in self._type_asts.items():
            self.canonical_names[name] = self._canonical_name(name, td.loc)
        for td in self._type_asts.values():
            self._resolve_named_type(td.name, td.loc)
        for td in self._type_asts.values():
            resolved = self.type_defs.get(td.name)
            if resolved is not None:
                self._collect_heap_refs(resolved, td.loc)
        # Phase 2: register all program signatures (for forward calls)
        self._entry_number = min((pd.number for pd in program.program_defs), default=None)
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
        self.diagnostics.append({"stage": "semantic", "line": loc.line, "column": loc.column, "message": msg})

    def _warn(self, loc: Loc, msg: str) -> None:
        self.warnings.append(f"{loc}: {msg}")

    # -- type resolution ----------------------------------------------------

    def resolve_type_node(self, tn: TypeNode) -> ResolvedType | None:
        """Convert an AST TypeNode to a ResolvedType."""
        if isinstance(tn, BitType):
            return ResolvedBit()
        if isinstance(tn, BitSeqType):
            return ResolvedBitSeq(tn.length)
        if isinstance(tn, ArrayType):
            if tn.size is not None and not 0 <= tn.size <= 2147483647:
                self._error(tn.loc, "list length exceeds Int32 range")
                return None
            elem = self.resolve_type_node(tn.element_type)
            if elem is None:
                return None
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
            if tn.name not in self._type_asts:
                self._error(tn.loc, f"undefined type {tn.name}")
                return None
            return self._resolve_named_type(tn.name, tn.loc)
        if isinstance(tn, RefType):
            if tn.target not in self._type_asts:
                self._error(tn.loc, f"undefined type {tn.target}")
                return None
            return ResolvedRef(self._canonical_name(tn.target, tn.loc))
        self._error(tn.loc, f"unknown type node: {type(tn).__name__}")
        return None

    # -- Phase 1: type definitions ------------------------------------------

    def _canonical_name(self, name: str, loc: Loc, seen: set[str] | None = None) -> str:
        """Direct aliases share their target's identity; other names are nominal."""
        seen = set() if seen is None else seen
        if name in seen:
            self._error(loc, f"cyclic type alias involving {name}")
            return name
        td = self._type_asts.get(name)
        if td is not None and isinstance(td.type_expr, UserType):
            seen.add(name)
            return self._canonical_name(td.type_expr.name, loc, seen)
        return name

    def _resolve_named_type(self, name: str, loc: Loc) -> ResolvedType | None:
        canonical = self._canonical_name(name, loc)
        if canonical in self.type_defs:
            return self.type_defs[canonical]
        if canonical in self._resolving_types:
            self._error(loc, f"recursive type by value involving {canonical}")
            return None
        td = self._type_asts.get(canonical)
        if td is None:
            self._error(loc, f"undefined type {canonical}")
            return None
        self._resolving_types.add(canonical)
        resolved = self.resolve_type_node(td.type_expr)
        self._resolving_types.remove(canonical)
        if resolved is not None:
            self.type_defs[canonical] = resolved
            for alias, target in self.canonical_names.items():
                if target == canonical:
                    self.type_defs[alias] = resolved
        return resolved

    def _collect_heap_refs(self, rt: ResolvedType, loc: Loc) -> None:
        if isinstance(rt, ResolvedRef):
            target = self._resolve_named_type(rt.target, loc)
            if target is not None:
                self._ensure_heap_type(rt.target, target, loc)
        elif isinstance(rt, ResolvedRecord):
            for field in rt.fields:
                self._collect_heap_refs(field, loc)
        elif isinstance(rt, ResolvedArray):
            self._collect_heap_refs(rt.element, loc)

    def _ensure_heap_type(self, name: str, rt: ResolvedType, loc: Loc) -> None:
        from .layout import heap_layout

        if name in self.heap_types:
            return
        try:
            heap_layout(rt)
        except ValueError as exc:
            self._error(loc, f"type {name} cannot be allocated: {exc}")
            return
        self.heap_types[name] = rt

    # -- Phase 2: program signatures ----------------------------------------

    def _program_key(self, pd: ProgramDef) -> str:
        return f"P{pd.number}"

    def _register_program_sig(self, pd: ProgramDef, *, internal=False) -> None:
        from plankalkulsharp.standard_library import NAMES
        key = self._program_key(pd)
        if not internal and (pd.name in NAMES or pd.name in ("N", "Lz") or (pd.name or "").startswith("__stdlib_")):
            self._error(pd.loc, f"reserved standard plan name {pd.name}")
        if key in self.programs:
            self._error(pd.loc, f"duplicate program definition {key}")
            return

        param_types: list[ResolvedType] = []
        for v in pd.params:
            if v.kind != 'V':
                self._error(v.loc, f"param {v.kind}{v.index} should be of kind V")
                continue
            if v.type_ann is None:
                self._error(v.loc, f"parameter {v.kind}{v.index} missing type annotation")
                continue
            rt = self.resolve_type_node(v.type_ann)
            if rt is not None:
                param_types.append(rt)

        result_types: list[ResolvedType] = []
        for v in pd.results:
            if v.kind != 'R':
                self._error(v.loc, f"param {v.kind}{v.index} should be of kind R")
                continue
            if v.type_ann is None:
                self._error(v.loc, f"result {v.kind}{v.index} missing type annotation")
                continue
            rt = self.resolve_type_node(v.type_ann)
            if rt is not None:
                result_types.append(rt)

        self.programs[key] = ProgramSymbol(
            key=key,
            number=pd.number,
            name=pd.name,
            params=param_types,
            results=result_types,
            ast=pd,
            scope=None
        )
        if pd.number == self._entry_number:
            for rt in [*param_types, *result_types]:
                if self._contains_ref(rt):
                    self._error(pd.loc, "entry program cannot expose references in command-line inputs or printed results")
        for rt in [*param_types, *result_types]:
            self._collect_heap_refs(rt, pd.loc)

    @staticmethod
    def _contains_ref(rt: ResolvedType) -> bool:
        if isinstance(rt, ResolvedRef):
            return True
        if isinstance(rt, ResolvedRecord):
            return any(Analyzer._contains_ref(field) for field in rt.fields)
        if isinstance(rt, ResolvedArray):
            return Analyzer._contains_ref(rt.element)
        return False

    # -- Phase 3: program body check ----------------------------------------

    def _check_program(self, pd: ProgramDef) -> None:
        scope = Scope()
        self._indices = {}
        self._exits = [("procedure", pd)]
        self._after_fin = False
        self._scope = scope
        self._ref_liveness = {}
        self._dead_refs = set()
        self.programs[self._program_key(pd)].scope = scope

        # Define params (V variables)
        for v in pd.params:
            rt = self.resolve_type_node(v.type_ann)
            if rt is not None:
                scope.define(v.kind, v.index, rt)

        # Define results (R variables)
        for v in pd.results:
            rt = self.resolve_type_node(v.type_ann)
            if rt is not None:
                scope.define(v.kind, v.index, rt)

        # Check body statements
        for stmt in pd.body:
            self._check_stmt(stmt)

        self._scope = None

    # -- statement checking -------------------------------------------------

    def _check_stmt(self, stmt: StmtNode) -> None:
        # After nonlocal exits, lexical traversal no longer proves reachability.
        # Keep type checking, but leave reference lifetime checks to Runtime.
        if self._after_fin:
            self._ref_liveness.clear()
            self._dead_refs.clear()
        if isinstance(stmt, Assignment):
            self._check_assignment(stmt)
        elif isinstance(stmt, Free):
            self._check_free(stmt)
        elif isinstance(stmt, GuardedStmt):
            self._check_guarded(stmt)
        elif isinstance(stmt, WLoop):
            self._ref_liveness.clear()
            self._dead_refs.clear()
            self._exits.extend([("loop", stmt), ("iteration", stmt)])
            for s in stmt.body:
                self._check_stmt(s)
            del self._exits[-2:]
            self._ref_liveness.clear()
            self._dead_refs.clear()
        elif isinstance(stmt, IndexedLoop):
            self._check_indexed_loop(stmt)
        elif isinstance(stmt, Fin):
            if stmt.condition is not None:
                rt = self._check_expr(stmt.condition)
                if rt is not None and not isinstance(rt, ResolvedBit):
                    self._error(stmt.loc, "FIN condition must be a bit")
            if stmt.depth < 1 or stmt.depth > len(self._exits):
                self._error(stmt.loc, "FIN depth exceeds available nesting or is zero")
            else:
                self.fin_targets[id(stmt)] = self._exits[-stmt.depth]
            self._after_fin = True
            self._ref_liveness.clear()
            self._dead_refs.clear()

    def _check_assignment(self, stmt: Assignment) -> None:
        value = stmt.value
        target = stmt.target
        tgt_type = self._resolve_var_type(target)
        val_type = self._check_expr(value, tgt_type)

        # C-variable immutability: only one assignment allowed
        if target.kind == "C" and self._scope is not None:
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
        if isinstance(val_type, ResolvedNil) and tgt_type is None:
            self._error(stmt.loc, "NIL needs a reference type annotation on its first assignment")
        elif val_type is not None and tgt_type is None:
            self._scope.define(target.kind, target.index, self._variable_type(val_type))
        self._track_assignment(target, value, val_type)

    def _check_free(self, stmt: Free) -> None:
        value_type = self._check_expr(stmt.value)
        if isinstance(value_type, ResolvedNil):
            return
        if not isinstance(value_type, ResolvedRef):
            self._error(stmt.loc, f"only a reference can be freed, got {value_type}")
            return
        token = self._reference_token(stmt.value)
        if token is not None:
            if token in self._dead_refs:
                self._error(stmt.loc, "reference has already been freed")
            else:
                self._dead_refs.add(token)

    @staticmethod
    def _var_key(ref: VarRef) -> str:
        return f"{ref.kind}{ref.index}"

    def _reference_token(self, expr: ExprNode) -> str | None:
        if isinstance(expr, VarRef) and not expr.components:
            return self._ref_liveness.get(self._var_key(expr))
        return None

    def _track_assignment(
        self, target: VarRef, value: ExprNode, value_type: ExpressionType | None
    ) -> None:
        if target.components or not isinstance(value_type, (ResolvedRef, ResolvedNil)):
            return
        key = self._var_key(target)
        if isinstance(value, Allocate):
            self._ref_liveness[key] = f"{value.loc.line}:{value.loc.column}"
        elif isinstance(value, NilLiteral):
            self._ref_liveness[key] = None
        else:
            self._ref_liveness[key] = self._reference_token(value)

    def _check_guarded(self, stmt: GuardedStmt) -> None:
        cond_type = self._check_expr(stmt.condition)
        if cond_type is not None and not isinstance(cond_type, ResolvedBit):
            self._error(
                stmt.condition.loc,
                f"guard condition must be 0 (bit/boolean), got {cond_type}",
            )
        before_liveness, before_dead = self._ref_liveness.copy(), self._dead_refs.copy()
        self._exits.append(("block", stmt))
        for s in stmt.body:
            self._check_stmt(s)
        self._exits.pop()
        if self._after_fin:
            self._ref_liveness.clear()
            self._dead_refs.clear()
            return
        after_liveness, after_dead = self._ref_liveness, self._dead_refs
        # A guarded body might not run: retain only equal facts from both paths.
        self._ref_liveness = {
            key: token for key, token in before_liveness.items()
            if after_liveness.get(key) == token
        }
        self._dead_refs = before_dead & after_dead

    @staticmethod
    def literal_integer(expr):
        if isinstance(expr, IntLiteral): return expr.value
        if isinstance(expr, UnaryExpr) and expr.op == UnOp.NEG and isinstance(expr.operand, IntLiteral):
            return -expr.operand.value
        return None

    def _check_indexed_loop(self, stmt: IndexedLoop) -> None:
        expected = 1 if stmt.variant <= 2 else 2
        if len(stmt.bounds) != expected:
            self._error(stmt.loc, f"W{stmt.variant} expects {expected} bounds")
        types = [self._check_expr(e) for e in stmt.bounds]
        for rt in types:
            if not isinstance(rt, (ResolvedBit, ResolvedBitSeq)) or isinstance(rt, ResolvedBitSeq) and rt.length > 64:
                self._error(stmt.loc, "W bounds must be integer scalars up to 64 bits")
        values = [self.literal_integer(e) for e in stmt.bounds]
        width = 64 if any(isinstance(rt, ResolvedBitSeq) and rt.length > 32 for rt in types) or any(
            v is not None and not -(1 << 31) <= v < (1 << 31) for v in values) else 32
        for value in values:
            if value is not None and not -(1 << 63) <= value < (1 << 63):
                self._error(stmt.loc, "W literal bound is outside signed 64-bit range")
        self.loop_types[id(stmt)] = ResolvedBitSeq(width)
        if len(values) == expected and all(v is not None for v in values):
            invalid = (stmt.variant <= 2 and values[0] < 0
                       or stmt.variant == 3 and values[0] > values[1]
                       or stmt.variant == 4 and values[0] < values[1])
            if invalid: self._error(stmt.loc, f"invalid W{stmt.variant} bounds")
        previous = self._indices.get(stmt.index)
        if previous is not None:
            self._error(stmt.loc, f"index i{stmt.index} is already active")
        self._indices[stmt.index] = stmt
        self._exits.extend([("loop", stmt), ("iteration", stmt)])
        self._ref_liveness.clear(); self._dead_refs.clear()
        for child in stmt.body: self._check_stmt(child)
        del self._exits[-2:]
        if previous is None: self._indices.pop(stmt.index)
        else: self._indices[stmt.index] = previous
        self._ref_liveness.clear(); self._dead_refs.clear()

    # -- expression type inference ------------------------------------------

    @staticmethod
    def _variable_type(rt):
        # Inferred variables may grow; literal lengths remain known on expressions.
        if isinstance(rt, ResolvedArray):
            return ResolvedArray(None, Analyzer._variable_type(rt.element))
        if isinstance(rt, ResolvedRecord):
            return ResolvedRecord(tuple(Analyzer._variable_type(f) for f in rt.fields))
        return rt

    def _check_expr(self, expr: ExprNode, expected=None) -> ExpressionType | None:
        if isinstance(expr, NilLiteral) and isinstance(expected, ResolvedRef):
            result = expected
        elif isinstance(expr, (ListLiteral, RecordLiteral)):
            result = self._check_literal(expr, expected)
        elif isinstance(expr, FuncCall):
            result = self._check_func_call(expr, expected)
        else:
            result = self._check_expr_impl(expr)
        if result is not None:
            self.expr_types[id(expr)] = result
        return result

    def _check_literal(self, expr, expected):
        if isinstance(expr, RecordLiteral):
            fields = expected.fields if isinstance(expected, ResolvedRecord) else ()
            types = [self._check_expr(e, fields[i] if i < len(fields) else None)
                     for i, e in enumerate(expr.elements)]
            if any(isinstance(t, ResolvedNil) for t in types):
                self._error(expr.loc, "NIL in a record needs a reference type from context")
                return None
            return ResolvedRecord(tuple(types)) if all(t is not None for t in types) else None
        element = expected.element if isinstance(expected, ResolvedArray) else None
        if not expr.elements and element is None:
            self._error(expr.loc, "empty list needs an element type from context")
            return None
        types = [self._check_expr(e, element) for e in expr.elements]
        if any(t is None for t in types):
            return None
        if element is None:
            element = types[0]
            for other in types[1:]:
                element = self._common_type(element, other)
                if element is None:
                    self._error(expr.loc, "incompatible list elements")
                    return None
        if isinstance(element, ResolvedNil):
            self._error(expr.loc, "NIL in a list needs a reference element type")
            return None
        if any(not self._types_compatible(t, element) for t in types):
            self._error(expr.loc, "incompatible list element type")
        return ResolvedArray(len(types), element)

    @staticmethod
    def _common_type(a, b):
        if isinstance(a, (ResolvedBit, ResolvedBitSeq)) and isinstance(b, (ResolvedBit, ResolvedBitSeq)):
            return ResolvedBitSeq(max(getattr(a, 'length', 1), getattr(b, 'length', 1)))
        if isinstance(a, ResolvedArray) and isinstance(b, ResolvedArray):
            element = Analyzer._common_type(a.element, b.element)
            return ResolvedArray(a.size if a.size == b.size else None, element) if element else None
        if isinstance(a, ResolvedRecord) and isinstance(b, ResolvedRecord) and len(a.fields) == len(b.fields):
            fields = tuple(Analyzer._common_type(x, y) for x, y in zip(a.fields, b.fields))
            return ResolvedRecord(fields) if all(fields) else None
        if isinstance(a, ResolvedNil) and isinstance(b, ResolvedRef):
            return b
        if isinstance(b, ResolvedNil) and isinstance(a, ResolvedRef):
            return a
        return a if a == b else None

    def _check_expr_impl(self, expr: ExprNode) -> ExpressionType | None:
        if isinstance(expr, IndexRef):
            loop = self._indices.get(expr.index)
            if loop is None:
                self._error(expr.loc, f"index i{expr.index} is not active")
                return None
            self.index_bindings[id(expr)] = loop
            return self.loop_types[id(loop)]
        if isinstance(expr, IntLiteral):
            value = expr.value
            if value == 0 or value == 1:
                return ResolvedBit()
            return ResolvedBitSeq(value.bit_length())
        if isinstance(expr, BoolLiteral):
            return ResolvedBit()
        if isinstance(expr, BitSeqLiteral):
            return ResolvedBitSeq(len(expr.bits))
        if isinstance(expr, NilLiteral):
            return ResolvedNil()
        if isinstance(expr, Allocate):
            if expr.target not in self._type_asts:
                self._error(expr.loc, f"undefined type {expr.target}")
                return None
            target = self._canonical_name(expr.target, expr.loc)
            resolved = self._resolve_named_type(target, expr.loc)
            if resolved is not None:
                self._ensure_heap_type(target, resolved, expr.loc)
                return ResolvedRef(target)
        if isinstance(expr, VarRef):
            res = self._resolve_var_type(expr)
            if res is None:
                self._error(expr.loc, f"unknown variable type: {expr}")
            return res
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

        if isinstance(left, (ResolvedArray, ResolvedRecord)) or isinstance(right, (ResolvedArray, ResolvedRecord)):
            if expr.op not in (BinOp.EQ, BinOp.NEQ) or self._common_type(left, right) is None:
                self._error(expr.loc, "composite values only support structural = and != with compatible values")
            return ResolvedBit()

        # Comparison operators always return S0
        if expr.op in (BinOp.EQ, BinOp.NEQ, BinOp.LT, BinOp.GT, BinOp.LE, BinOp.GE):
            if isinstance(left, (ResolvedRef, ResolvedNil)) or isinstance(right, (ResolvedRef, ResolvedNil)):
                if expr.op not in (BinOp.EQ, BinOp.NEQ):
                    self._error(expr.loc, "references only support = and !=")
                elif not (
                    isinstance(left, ResolvedNil) and isinstance(right, ResolvedRef)
                    or isinstance(right, ResolvedNil) and isinstance(left, ResolvedRef)
                    or isinstance(left, ResolvedRef) and isinstance(right, ResolvedRef) and left.target == right.target
                ):
                    self._error(expr.loc, f"incompatible reference comparison: {left} vs {right}")
            return ResolvedBit()

        # Boolean operators require 0 operands, return 0
        if expr.op in (BinOp.AND, BinOp.OR):
            if not isinstance(left, ResolvedBit):
                self._error(expr.left.loc, f"boolean operator requires 0, got {left}")
            if not isinstance(right, ResolvedBit):
                self._error(expr.right.loc, f"boolean operator requires 0, got {right}")
            return ResolvedBit()

        both_bit_seqs = True
        if not isinstance(left, ResolvedBitSeq) and not isinstance(left, ResolvedBit):
            self._error(expr.left.loc, f"arithmetic operator requires bit sequence or bit, got {left}")
            both_bit_seqs = False
        if not isinstance(right, ResolvedBitSeq) and not isinstance(right, ResolvedBit):
            self._error(expr.right.loc, f"arithmetic operator requires bit sequence or bit, got {right}")
            both_bit_seqs = False
        if not both_bit_seqs:
            return None
        left_size = left.length if isinstance(left, ResolvedBitSeq) else 1
        right_size = right.length if isinstance(right, ResolvedBitSeq) else 1
        return ResolvedBitSeq(self._arithmetic_result_size(expr, left_size, right_size))

    def _arithmetic_result_size(self, expr: BinaryExpr, left_size: int, right_size: int) -> int:
        """Определяет размер результата арифметической операции в битах.

        Все операции беззнаковые, с сохранением полного результата.
        При присваивании в переменную меньшего размера будет происходить
        автоматическое обрезание (маскирование).
        """
        op = expr.op

        if op == BinOp.ADD:
            # Беззнаковое сложение: может быть перенос в старший бит
            # Пример: 0xFF + 0xFF = 0x1FE (нужно 9 бит для 8-битных операндов)
            return max(left_size, right_size) + 1

        elif op == BinOp.SUB:
            # Беззнаковое вычитание: результат всегда в диапазоне [0, max(A,B)]
            # Нужен дополнительный бит для представления заимствования
            # Пример: 0 - 1 = 255 в 8 битах, но для полного результата нужно 9 бит
            return max(left_size, right_size) + 1

        elif op == BinOp.MUL:
            # Беззнаковое умножение: размер = сумма размеров
            # Пример: 3 бита * 3 бита = максимум 7*7=49, что требует 6 бит
            return left_size + right_size

        elif op == BinOp.DIV:
            # Деление: размер частного равен размеру делимого
            # Делитель может быть меньше, но результат не превышает делимое
            return left_size

        elif op == BinOp.POW:
            # Возведение в степень: left_size * right_size бит (теоретически)
            # Пример: 2 бита (основание) ^ 3 бита (степень) = макс 3^7=2187 = 12 бит
            # Но на практике это много, ограничиваем разумным пределом в 64 бита
            result = left_size * right_size
            if result > 64:
                self._warn(expr.loc, f"Power operation result size {result} bits exceeds 64, truncating")
                return 64
            return result

        else:
            self._error(expr.loc, f"Unsupported arithmetic operation: {op}")
            return 0

    def _check_unary(self, expr: UnaryExpr) -> ResolvedType | None:
        operand = self._check_expr(expr.operand)
        if operand is None:
            return None
        if expr.op == UnOp.NOT:
            if not isinstance(operand, ResolvedBit):
                self._error(expr.operand.loc, f"NOT requires 0, got {operand}")
            return ResolvedBit()
        if expr.op == UnOp.NEG:
            if isinstance(operand, (ResolvedRef, ResolvedNil)):
                self._error(expr.operand.loc, f"NEG requires a bit sequence or bit, got {operand}")
                return None
            return operand
        return None

    def _check_func_call(self, expr: FuncCall, expected=None) -> ResolvedType | None:
        from plankalkulsharp.standard_library import NAMES
        if expr.name in NAMES:
            return self._check_library_call(expr, expected)
        if expr.name in ("N", "Lz"):
            count = 1 if expr.name == "N" else 2
            if len(expr.args) != count:
                self._error(expr.loc, f"{expr.name} expects {count} arguments")
                return None
            context = expected if isinstance(expected, ResolvedArray) else None
            types = [None] * len(expr.args)
            # An empty literal gets its element type from the other list or target.
            for i, arg in enumerate(expr.args):
                if not isinstance(arg, ListLiteral) or arg.elements:
                    types[i] = self._check_expr(arg, context)
                    if context is None and isinstance(types[i], ResolvedArray):
                        context = types[i]
            for i, arg in enumerate(expr.args):
                if types[i] is None:
                    types[i] = self._check_expr(arg, context)
            if not all(isinstance(t, ResolvedArray) for t in types):
                self._error(expr.loc, f"{expr.name} requires lists")
                return None
            if expr.name == "N":
                return ResolvedBitSeq(32)
            element = self._common_type(types[0].element, types[1].element)
            if element is None:
                self._error(expr.loc, "Lz requires compatible element types")
                return None
            sizes = [t.size for t in types]
            return ResolvedArray(sum(sizes) if None not in sizes else None, element)
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
            self._error(expr.loc, f"undefined program '{name}'")
            return None

        # Check argument count
        if len(expr.args) != len(psym.params):
            self._error(
                expr.loc,
                f"'{name}' expects {len(psym.params)} argument(s), got {len(expr.args)}",
            )

        # Check argument types
        for i, arg in enumerate(expr.args):
            arg_type = self._check_expr(arg, psym.params[i] if i < len(psym.params) else None)
            if arg_type is not None and i < len(psym.params):
                if not self._types_compatible(arg_type, psym.params[i]):
                    self._error(
                        arg.loc,
                        f"argument {i} type mismatch: {arg_type} vs {psym.params[i]}",
                    )

        # A call can retain or free an alias; facts beyond its boundary are unknown.
        self._ref_liveness.clear()

        # Return type: single result directly, multi-result as record
        if len(psym.results) > 1:
            return ResolvedRecord(tuple(psym.results))
        return psym.results[0]

    def _check_library_call(self, expr, expected=None):
        from plankalkulsharp.standard_library import catalog, template, bind, substitute, unresolved, specialize
        name = expr.name
        spec = catalog()[name]
        pattern = template(name)
        static = spec.get("static", [])
        static_positions = {p["argument"] for p in static}
        arguments = [arg for i, arg in enumerate(expr.args) if i not in static_positions]
        if len(expr.args) != len(pattern.params) + len(static):
            self._error(expr.loc, f"{name} expects {len(pattern.params) + len(static)} arguments")
            return None
        bindings = {}
        parameters = spec["types"]
        if expected is not None:
            bind(pattern.results[0].type_ann, expected, bindings, parameters)
        actual_types = []
        for formal, argument in zip(pattern.params, arguments):
            context = None
            if not unresolved(formal.type_ann, parameters, bindings):
                context = self.resolve_type_node(substitute(formal.type_ann, bindings))
            actual = self._check_expr(argument, context)
            if actual is None:
                return None
            bind(formal.type_ann, actual, bindings, parameters)
            actual_types.append(actual)
        projection = None
        for parameter in static:
            if parameter["kind"] != "field":
                self._error(expr.loc, "unsupported static template parameter")
                return None
            projection = self.literal_integer(expr.args[parameter["argument"]])
            record = bindings.get(parameter["record"])
            if not isinstance(record, ResolvedRecord) or projection is None or not 0 <= projection < len(record.fields):
                self._error(expr.loc, f"{name} requires a record list and a static valid field number")
                return None
            bindings[parameter["bind"]] = record.fields[projection]
        if set(parameters) - bindings.keys():
            self._error(expr.loc, f"cannot infer template types for {name}")
            return None
        for formal, actual in zip(pattern.params, actual_types):
            target = self.resolve_type_node(substitute(formal.type_ann, bindings))
            if target is None or not self._types_compatible(actual, target):
                self._error(expr.loc, f"{name} argument type mismatch: {actual} vs {target}")
        for contract in spec.get("contracts", []):
            if contract["kind"] == "equal_length":
                left, right = (actual_types[contract[k]] for k in ("left", "right"))
                if isinstance(left, ResolvedArray) and isinstance(right, ResolvedArray) and left.size is not None and right.size is not None and left.size != right.size:
                    self._error(expr.loc, f"{name} requires equal list lengths")
            elif contract["kind"] == "position":
                container = actual_types[contract["list"]]
                index_type = actual_types[contract["index"]]
                if not isinstance(index_type, (ResolvedBit, ResolvedBitSeq)) or getattr(index_type, "length", 1) > 64:
                    self._error(expr.loc, "position must be an integer scalar up to 64 bits")
                value = self.literal_integer(arguments[contract["index"]])
                if isinstance(container, ResolvedArray) and value is not None and (value < 0 or container.size is not None and value >= container.size + contract.get("allow_end", False)):
                    self._error(expr.loc, f"{name} position out of range")
        key = (name, tuple(sorted(bindings.items())), projection)
        psym = self.library_specializations.get(key)
        if psym is None:
            number = max((p.number for p in self.programs.values()), default=0) + 1
            pd = specialize(name, bindings, number, projection)
            self._register_program_sig(pd, internal=True)
            psym = self.programs[f"P{number}"]
            self.library_specializations[key] = psym
            self.library_files[psym.key] = f"stdlib/{name}.pk"
            # A specialized body uses the same checker, in its own procedure scope.
            attrs = ("_scope", "_indices", "_exits", "_after_fin", "_ref_liveness", "_dead_refs")
            saved = {a: getattr(self, a) for a in attrs}
            before = len(self.diagnostics)
            self._check_program(pd)
            for diagnostic in self.diagnostics[before:]:
                diagnostic.setdefault("file", self.library_files[psym.key])
            for a, value in saved.items():
                setattr(self, a, value)
            # The temporary numeric key exists only while checking this body.
            self.programs.pop(psym.key)
            filename = self.library_files.pop(psym.key)
            psym.key = psym.name
            self.programs[psym.key] = psym
            self.library_files[psym.key] = filename
        self.library_calls[id(expr)] = psym
        return psym.results[0]

    # -- variable type resolution -------------------------------------------

    def _resolve_var_type(self, ref: VarRef) -> ResolvedType | None:
        assert self._scope is not None
        token = self._ref_liveness.get(self._var_key(ref))
        if ref.components and any(isinstance(comp, DereferenceAccess) for comp in ref.components) and token is not None and token in self._dead_refs:
            self._error(ref.loc, "reference has been freed")
        sym = self._scope.lookup(ref.kind, ref.index)

        # Если символ не найден
        if sym is None:
            # При первом обращении смотрим указанный inline тип
            if ref.type_ann is not None:
                rt = self.resolve_type_node(ref.type_ann)
                if rt is not None:
                    self._scope.define(ref.kind, ref.index, rt)
                    self._collect_heap_refs(rt, ref.loc)
                    return self._apply_component_access(rt, ref)
                return None
            return None
        elif ref.type_ann is not None:
            rt = self.resolve_type_node(ref.type_ann)
            if rt != sym.resolved_type:
                self._warn(ref.loc, f"ignore type {rt} because type {sym.resolved_type} was previously resolved")

        base_type = sym.resolved_type
        return self._apply_component_access(base_type, ref)

    def _apply_component_access(
        self,
        base: ResolvedType,
        ref: VarRef,
    ) -> ResolvedType | None:
        components = ref.components
        current = base
        after_dereference = False
        for comp in components:
            if isinstance(comp, DereferenceAccess):
                if not isinstance(current, ResolvedRef):
                    self._error(comp.loc, f"cannot dereference {current}")
                    return None
                target = self.type_defs.get(current.target)
                if target is None:
                    self._error(comp.loc, f"undefined type {current.target}")
                    return None
                current = target
                after_dereference = True
            elif isinstance(comp, StaticAccess):
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
                    if current.size is not None and not 0 <= comp.index < current.size:
                        self._error(comp.loc, "list index out of range")
                    if after_dereference:
                        self._error(comp.loc, "arrays cannot be accessed through a heap reference")
                        return None
                    current = current.element
                elif isinstance(current, ResolvedBitSeq):
                    if after_dereference:
                        self._error(comp.loc, "bit components cannot be accessed through a heap reference")
                        return None
                    current = ResolvedBit()
                else:
                    self._error(comp.loc, f"cannot access component of {current}")
                    return None
            elif isinstance(comp, DynamicAccess):
                index_type = self._check_expr(comp.expr)
                if not isinstance(index_type, (ResolvedBit, ResolvedBitSeq)) or getattr(index_type, 'length', 1) > 64:
                    self._error(comp.loc, "list index must be an integer scalar up to 64 bits")
                if after_dereference:
                    self._error(comp.loc, "dynamic components cannot be accessed through a heap reference")
                    return None
                if isinstance(current, ResolvedArray):
                    current = current.element
                elif isinstance(current, ResolvedBitSeq):
                    current = ResolvedBit()
                else:
                    self._error(comp.loc, f"cannot index into {current}")
                    return None
        # Keep selected types for both reads and assignment targets.
        self.expr_types[id(ref)] = current
        return current

    # -- type compatibility -------------------------------------------------

    @staticmethod
    def _types_compatible(source: ExpressionType, target: ResolvedType) -> bool:
        """Check structural type compatibility for assignment."""
        if isinstance(source, ResolvedNil):
            return isinstance(target, ResolvedRef)
        if isinstance(source, ResolvedRef) or isinstance(target, ResolvedRef):
            return isinstance(source, ResolvedRef) and isinstance(target, ResolvedRef) and source.target == target.target
        # Последовательности бит совместимы
        if isinstance(source, ResolvedBitSeq) and isinstance(target, ResolvedBitSeq):
            return True
        # 0 <-> S
        if isinstance(source, ResolvedBit) and isinstance(target, ResolvedBit):
            return True
        # Последовательности бит и биты совместимы
        if isinstance(source, ResolvedBitSeq) and isinstance(target, ResolvedBit):
            return True
        # Биты и послледовательности бит совместимы
        if isinstance(source, ResolvedBit) and isinstance(target, ResolvedBitSeq):
            return True
        # Массивы одного размера и совместимых типов совместимы
        if isinstance(source, ResolvedArray) and isinstance(target, ResolvedArray):
            return (source.size is None or target.size is None or source.size == target.size) and Analyzer._types_compatible(
                source.element, target.element
            )
        # Структуры одного размера и с совместимыми типами совместимы
        if isinstance(source, ResolvedRecord) and isinstance(target, ResolvedRecord):
            if len(source.fields) != len(target.fields):
                return False
            return all(
                Analyzer._types_compatible(s, t)
                for s, t in zip(source.fields, target.fields)
            )
        return False
