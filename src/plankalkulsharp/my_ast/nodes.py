"""AST node definitions for Plankalkül.

Each node is a frozen dataclass with source location info (line, column).
The AST is produced by the frontend's AST builder from the ANTLR4 parse tree.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


# ---------------------------------------------------------------------------
# Source location
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Loc:
    """Source location."""
    line: int
    column: int

    def __str__(self) -> str:
        return f"{self.line}:{self.column}"


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TypeNode:
    """Base for all type AST nodes."""
    loc: Loc


@dataclass(frozen=True)
class BitType(TypeNode):
    """S0 — single bit (Boolean)."""
    pass


@dataclass(frozen=True)
class BitSeqType(TypeNode):
    """S1·n — bit sequence of length n."""
    length: int


@dataclass(frozen=True)
class ArrayType(TypeNode):
    """n × T — array of n elements of type T."""
    size: int
    element_type: TypeNode


@dataclass(frozen=True)
class RecordType(TypeNode):
    """(T1, T2, ...) — tuple/record type."""
    fields: tuple[TypeNode, ...]


@dataclass(frozen=True)
class UserType(TypeNode):
    """A<n> — reference to user-defined type."""
    index: int


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

class BinOp(Enum):
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    POW = auto()
    AND = auto()
    OR = auto()
    EQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()


class UnOp(Enum):
    NOT = auto()
    NEG = auto()


@dataclass(frozen=True)
class ExprNode:
    """Base for all expression AST nodes."""
    loc: Loc


@dataclass(frozen=True)
class IntLiteral(ExprNode):
    """Integer literal (decimal)."""
    value: int


@dataclass(frozen=True)
class BoolLiteral(ExprNode):
    """Boolean literal (L = true, 0 = false in S0 context)."""
    value: bool


@dataclass(frozen=True)
class BitSeqLiteral(ExprNode):
    """Bit sequence literal like L00L."""
    bits: tuple[bool, ...]


@dataclass(frozen=True)
class VarRef(ExprNode):
    """Variable reference: V0, Z1, R0, C3 etc."""
    kind: str          # 'V', 'Z', 'C', 'R'
    index: int
    type_ann: TypeNode | None = None
    components: tuple[ComponentAccess, ...] = ()


@dataclass(frozen=True)
class ComponentAccess:
    """Single component access step."""
    loc: Loc


@dataclass(frozen=True)
class StaticAccess(ComponentAccess):
    """Static component access: .n"""
    index: int


@dataclass(frozen=True)
class DynamicAccess(ComponentAccess):
    """Dynamic component access: [expr]"""
    expr: ExprNode


@dataclass(frozen=True)
class BinaryExpr(ExprNode):
    """Binary operation: left op right."""
    op: BinOp
    left: ExprNode
    right: ExprNode


@dataclass(frozen=True)
class UnaryExpr(ExprNode):
    """Unary operation: op operand."""
    op: UnOp
    operand: ExprNode


@dataclass(frozen=True)
class FuncCall(ExprNode):
    """Function/program call: name(args)."""
    name: str           # function name or "P<n>" / "P<n>.<m>"
    args: tuple[ExprNode, ...]


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StmtNode:
    """Base for all statement AST nodes."""
    loc: Loc


@dataclass(frozen=True)
class Assignment(StmtNode):
    """Assignment: expr -> varRef."""
    value: ExprNode
    target: VarRef


@dataclass(frozen=True)
class GuardedStmt(StmtNode):
    """Guarded conditional: (condition) -> body."""
    condition: ExprNode
    body: list[StmtNode]


@dataclass(frozen=True)
class WLoop(StmtNode):
    """W-loop: repeat while at least one guard is true."""
    body: list[StmtNode]


@dataclass(frozen=True)
class ForLoop(StmtNode):
    """For-loop: FOR var FROM start TO end { body }."""
    var: VarRef
    start: ExprNode
    end: ExprNode
    body: list[StmtNode]


# ---------------------------------------------------------------------------
# Top-level declarations
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TypeDef:
    """User-defined type: A<n> = typeExpr."""
    loc: Loc
    index: int
    type_expr: TypeNode


@dataclass(frozen=True)
class ProgramDef:
    """Program definition: P<n> name (...) -> result ... END."""
    loc: Loc
    number: int
    sub_number: int | None   # for subprograms P5.7
    name: str | None
    params: tuple[VarRef, ...]
    results: tuple[VarRef, ...]
    body: list[StmtNode]


@dataclass(frozen=True)
class Program:
    """Root node: a complete source file."""
    type_defs: list[TypeDef]
    program_defs: list[ProgramDef]
