"""Semantic analysis: symbol resolution, type checking, and validation.

Walks the AST produced by the parser, resolves user-defined types,
checks type compatibility, and attaches resolved type info to nodes.
Reports all errors without stopping at the first one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pluggy import Result

from plankalkulsharp.plankalkul_ast.nodes import (
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
        self.warnings: list[str] = []
        self.type_defs: dict[str, ResolvedType] = {}
        self.programs: dict[str, ProgramSymbol] = {}
        self._scope: Scope | None = None

    # -- public interface ---------------------------------------------------

    def report(self) -> None:
        """Print the analyzer report."""
        print('Errors:', self.errors)
        print('Warnings:', self.warnings)
        print('Type defs:', self.type_defs)
        print('Programs:', self.programs)

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
            if tn.name not in self.type_defs:
                self._error(tn.loc, f"undefined type {tn.name}")
                return None
            return self.type_defs[tn.name]
        self._error(tn.loc, f"unknown type node: {type(tn).__name__}")
        return None

    # -- Phase 1: type definitions ------------------------------------------

    def _register_type_def(self, td: TypeDef) -> None:
        if td.name in self.type_defs:
            self._error(td.loc, f"duplicate type definition {td.name}")
            return
        resolved = self.resolve_type_node(td.type_expr)
        if resolved is not None:
            self.type_defs[td.name] = resolved

    # -- Phase 2: program signatures ----------------------------------------

    def _program_key(self, pd: ProgramDef) -> str:
        return f"P{pd.number}"

    def _register_program_sig(self, pd: ProgramDef) -> None:
        key = self._program_key(pd)
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

    # -- Phase 3: program body check ----------------------------------------

    def _check_program(self, pd: ProgramDef) -> None:
        scope = Scope()
        self._scope = scope
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
        value = stmt.value
        target = stmt.target
        val_type = self._check_expr(value)
        tgt_type = self._resolve_var_type(target)

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
        if val_type is not None and tgt_type is None:
            self._scope.define(target.kind, target.index, val_type)

    def _check_guarded(self, stmt: GuardedStmt) -> None:
        cond_type = self._check_expr(stmt.condition)
        if cond_type is not None and not isinstance(cond_type, ResolvedBit):
            self._error(
                stmt.condition.loc,
                f"guard condition must be 0 (bit/boolean), got {cond_type}",
            )
        for s in stmt.body:
            self._check_stmt(s)

    def _check_for_loop(self, stmt: ForLoop) -> None:
        # The loop variable must be a new variable
        looked_up = self._scope.lookup(stmt.var.kind, stmt.var.index)
        if looked_up is not None:
            self._error(
                stmt.loc,
                "forloop variable is already declared previously",
            )

        start_type = self._check_expr(stmt.start)
        end_type = self._check_expr(stmt.end)
        if start_type is None or end_type is None:
            if start_type is None:
                self._error(stmt.loc, f"start type is undefined in {stmt.start}")
            if end_type is None:
                self._error(stmt.loc, f"end type is undefined in {stmt.end}")
        else:
            both_bitseq = True
            if not isinstance(start_type, ResolvedBitSeq) and not isinstance(start_type, ResolvedBit):
                both_bitseq = False
                self._error(stmt.loc, f"forloop range must be a bit sequence or bit in {stmt.start}, but is {start_type}")
            if not isinstance(end_type, ResolvedBitSeq) and not isinstance(end_type, ResolvedBit):
                both_bitseq = False
                self._error(stmt.loc, f"forloop range must be a bit sequence or bit in {stmt.end}, but is {end_type}")
            if both_bitseq:
                start_len = 1 if isinstance(start_type, ResolvedBit) else start_type.length
                end_len = 1 if isinstance(end_type, ResolvedBit) else end_type.length
                self._scope.define(stmt.var.kind, stmt.var.index, ResolvedBitSeq(max(start_len, end_len)))

        for s in stmt.body:
            self._check_stmt(s)

    # -- expression type inference ------------------------------------------

    def _check_expr(self, expr: ExprNode) -> ResolvedType | None:
        if isinstance(expr, IntLiteral):
            value = expr.value
            if value == 0 or value == 1:
                return ResolvedBit()
            return ResolvedBitSeq(value.bit_length())
        if isinstance(expr, BoolLiteral):
            return ResolvedBit()
        if isinstance(expr, BitSeqLiteral):
            return ResolvedBitSeq(len(expr.bits))
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

        # Comparison operators always return S0
        if expr.op in (BinOp.EQ, BinOp.NEQ, BinOp.LT, BinOp.GT, BinOp.LE, BinOp.GE):
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
        return psym.results[0]

    # -- variable type resolution -------------------------------------------

    def _resolve_var_type(self, ref: VarRef) -> ResolvedType | None:
        assert self._scope is not None
        sym = self._scope.lookup(ref.kind, ref.index)

        # Если символ не найден
        if sym is None:
            # При первом обращении смотрим указанный inline тип
            if ref.type_ann is not None:
                rt = self.resolve_type_node(ref.type_ann)
                if rt is not None:
                    self._scope.define(ref.kind, ref.index, rt)
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
            return source.size == target.size and Analyzer._types_compatible(
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
