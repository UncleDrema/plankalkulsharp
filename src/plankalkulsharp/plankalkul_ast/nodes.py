"""AST node definitions for Plankalkül.

Each node is a frozen dataclass with source location info (line, column).
The AST is produced by the frontend's AST builder from the ANTLR4 parse tree.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto, StrEnum


# ---------------------------------------------------------------------------
# Source location
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Loc:
    """Source location."""
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None

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
    """0 — single bit (Boolean)."""
    def __str__(self):
        return "0"


@dataclass(frozen=True)
class BitSeqType(TypeNode):
    """n.0 — bit sequence of length n."""
    length: int
    def __str__(self):
        return f"{self.length}.0"


@dataclass(frozen=True)
class ArrayType(TypeNode):
    """n × T — array of n elements of type T."""
    size: int | None
    element_type: TypeNode
    def __str__(self):
        return f"{self.size if self.size is not None else chr(42)}x{self.element_type}"


@dataclass(frozen=True)
class RecordType(TypeNode):
    """(T1, T2, ...) — tuple/record type."""
    fields: tuple[TypeNode, ...]
    def __str__(self):
        return f"({','.join(map(str, self.fields))})"


@dataclass(frozen=True)
class UserType(TypeNode):
    """<name> — reference to user-defined type."""
    name: str
    def __str__(self):
        return f"{self.name}"


@dataclass(frozen=True)
class RefType(TypeNode):
    """@name — a typed heap reference."""
    target: str

    def __str__(self):
        return f"@{self.target}"


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

class BinOp(StrEnum):
    ADD = '+'
    SUB = '-'
    MUL = '*'
    DIV = '/'
    POW = '**'
    AND = '&'
    OR = '|'
    EQ = '='
    NEQ = '!='
    LT = '<'
    GT = '>'
    LE = '<='
    GE = '>='


class UnOp(StrEnum):
    NOT = '~'
    NEG = '-'


@dataclass(frozen=True)
class ExprNode:
    """Base for all expression AST nodes."""
    loc: Loc


@dataclass(frozen=True)
class IntLiteral(ExprNode):
    """Integer literal (decimal)."""
    value: int

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class BoolLiteral(ExprNode):
    """Boolean literal (L = true, 0 = false in S0 context)."""
    value: bool

    def __str__(self) -> str:
        return "L" if self.value else "0"


@dataclass(frozen=True)
class BitSeqLiteral(ExprNode):
    """Bit sequence literal like L00L."""
    bits: tuple[bool, ...]

    def __str__(self):
        res = ''
        for b in self.bits:
            res += str(BoolLiteral(b))
        return res


@dataclass(frozen=True)
class ListLiteral(ExprNode):
    elements: tuple[ExprNode, ...]


@dataclass(frozen=True)
class RecordLiteral(ExprNode):
    elements: tuple[ExprNode, ...]


@dataclass(frozen=True)
class NilLiteral(ExprNode):
    """NIL — an untyped null reference."""


@dataclass(frozen=True)
class Allocate(ExprNode):
    """@name — allocate a zero-initialized named heap object."""
    target: str


@dataclass(frozen=True)
class VarRef(ExprNode):
    """Variable reference: V0, Z1, R0, C3 etc."""
    kind: str          # 'V', 'Z', 'C', 'R'
    index: int
    type_ann: TypeNode | None = None
    components: tuple[ComponentAccess, ...] = ()
    def __str__(self) -> str:
        if len(self.components) == 0:
            return f"{self.kind}{self.index}"
        return f"{self.kind}{self.index}[{'.'.join(map(str, self.components))}]"


@dataclass(frozen=True)
class ComponentAccess:
    """Single component access step."""
    loc: Loc


@dataclass(frozen=True)
class StaticAccess(ComponentAccess):
    """Static component access: .n"""
    index: int

    def __str__(self):
        return str(self.index)


@dataclass(frozen=True)
class DynamicAccess(ComponentAccess):
    """Dynamic component access: [expr]"""
    expr: ExprNode

    def __str__(self):
        return f'{self.expr}'


@dataclass(frozen=True)
class DereferenceAccess(ComponentAccess):
    """@ — follow a typed heap reference."""

    def __str__(self):
        return '@'


@dataclass(frozen=True)
class BinaryExpr(ExprNode):
    """Binary operation: left op right."""
    op: BinOp
    left: ExprNode
    right: ExprNode

    def __str__(self) -> str:
        return f"{self.left} {self.op} {self.right}"


@dataclass(frozen=True)
class UnaryExpr(ExprNode):
    """Unary operation: op operand."""
    op: UnOp
    operand: ExprNode


@dataclass(frozen=True)
class FuncCall(ExprNode):
    """Function/program call: name(args)."""
    name: str           # function name or "P<n>"
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

    def __str__(self):
        return f"{self.value} => {self.target}"


@dataclass(frozen=True)
class Free(StmtNode):
    """expr => @ — release one heap object."""
    value: ExprNode


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
class IndexRef(ExprNode):
    index: int


@dataclass(frozen=True)
class IndexedLoop(StmtNode):
    variant: int
    index: int
    bounds: tuple[ExprNode, ...]
    body: list[StmtNode]


@dataclass(frozen=True)
class Fin(StmtNode):
    depth: int
    condition: ExprNode | None = None


# ---------------------------------------------------------------------------
# Top-level declarations
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TypeDef:
    """User-defined type: <name> = typeExpr."""
    loc: Loc
    name: str
    type_expr: TypeNode


@dataclass(frozen=True)
class ProgramDef:
    """Program definition: P<n> name (...) -> result ... END."""
    loc: Loc
    number: int
    name: str | None
    params: tuple[VarRef, ...]
    results: tuple[VarRef, ...]
    body: list[StmtNode]


@dataclass(frozen=True)
class Program:
    """Root node: a complete source file."""
    type_defs: list[TypeDef]
    program_defs: list[ProgramDef]
