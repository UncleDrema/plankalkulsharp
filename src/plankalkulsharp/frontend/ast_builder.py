"""Build AST from ANTLR4 parse tree (CST → AST).

Uses the visitor pattern to walk the ANTLR4 concrete syntax tree and
produce the plankalkulsharp AST node hierarchy.
"""

from __future__ import annotations

from typing import Any

from antlr4 import ParserRuleContext, RecognitionException

from plankalkulsharp.plankalkul_ast.nodes import (
    ArrayType, ListLiteral, RecordLiteral,
    Assignment,
    BinOp,
    BinaryExpr,
    BitSeqLiteral,
    BitSeqType,
    BitType,
    BoolLiteral,
    ComponentAccess,
    DereferenceAccess,
    DynamicAccess,
    ExprNode,
    IndexedLoop, IndexRef, Fin,
    FuncCall,
    GuardedStmt,
    IntLiteral,
    Allocate,
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
    NilLiteral,
    VarRef,
    WLoop,
    Free,
)
from plankalkulsharp.frontend.generated.PlankalkulParser import PlankalkulParser
from plankalkulsharp.frontend.generated.PlankalkulVisitor import PlankalkulVisitor


class AstError(Exception):
    """Raised when compilation fails."""

    def __init__(self, msg: str, loc: Loc):
        self.loc = loc
        super().__init__(msg)

def _loc(ctx: ParserRuleContext) -> Loc:
    token = ctx.start
    stop = ctx.stop or token
    return Loc(line=token.line, column=token.column,
               end_line=stop.line, end_column=stop.column + len(stop.text or ""))


# Mapping from comparison operator text to BinOp
_COMP_OPS: dict[str, BinOp] = {
    "=": BinOp.EQ,
    "!=": BinOp.NEQ,
    "<": BinOp.LT,
    ">": BinOp.GT,
    "<=": BinOp.LE,
    ">=": BinOp.GE,
}


class ASTBuilder(PlankalkulVisitor):
    """Visitor that transforms the ANTLR4 CST into a plankalkulsharp AST."""

    def visit(self, ctx: Any) -> Any:
        return super().visit(ctx)

    # ------------------------------------------------------------------
    # Program (root)
    # ------------------------------------------------------------------

    def visitProgram(self, ctx: PlankalkulParser.ProgramContext) -> Program:
        type_defs: list[TypeDef] = []
        program_defs: list[ProgramDef] = []
        for child in ctx.children:
            if isinstance(child, PlankalkulParser.TypeDefContext):
                type_defs.append(self.visitTypeDef(child))
            elif isinstance(child, PlankalkulParser.ProgramDefContext):
                program_defs.append(self.visitProgramDef(child))
        return Program(type_defs=type_defs, program_defs=program_defs)

    # ------------------------------------------------------------------
    # Type definitions (top-level)
    # ------------------------------------------------------------------

    def visitTypeDef(self, ctx: PlankalkulParser.TypeDefContext) -> TypeDef:
        type_expr = self.visit(ctx.typeExpr())
        return TypeDef(loc=_loc(ctx), name=ctx.name.text, type_expr=type_expr)

    def visitBitType(self, ctx: PlankalkulParser.BitTypeContext) -> BitType:
        return BitType(loc=_loc(ctx))

    def visitBitSeqType(self, ctx: PlankalkulParser.BitSeqTypeContext) -> BitSeqType:
        length = int(ctx.INT(0).getText())
        bit_marker = int(ctx.INT(1).getText())
        if bit_marker != 0:
            raise AstError(f"Expected bit type '0' but got '{bit_marker}'", loc=_loc(ctx))
        return BitSeqType(loc=_loc(ctx), length=length)

    def visitArrayType(self, ctx: PlankalkulParser.ArrayTypeContext) -> ArrayType:
        size = int(ctx.INT().getText()) if ctx.INT() else None
        element_type = self.visit(ctx.typeExpr())
        return ArrayType(loc=_loc(ctx), size=size, element_type=element_type)

    def visitListLiteral(self, ctx):
        return ListLiteral(_loc(ctx), tuple(self.visit(e) for e in ctx.argList().expr()))

    def visitRecordLiteral(self, ctx):
        return RecordLiteral(_loc(ctx), tuple(self.visit(e) for e in ctx.expr()))

    def visitRecordType(self, ctx: PlankalkulParser.RecordTypeContext) -> RecordType:
        fields = tuple(self.visit(te) for te in ctx.typeExpr())
        return RecordType(loc=_loc(ctx), fields=fields)

    def visitUserType(self, ctx: PlankalkulParser.UserTypeContext) -> UserType:
        return UserType(loc=_loc(ctx), name=ctx.name.text)

    def visitRefType(self, ctx: PlankalkulParser.RefTypeContext) -> RefType:
        return RefType(loc=_loc(ctx), target=ctx.name.text)

    # ------------------------------------------------------------------
    # Program definitions
    # ------------------------------------------------------------------

    def visitProgramDef(self, ctx: PlankalkulParser.ProgramDefContext) -> ProgramDef:
        pid = ctx.programId()
        number = int(pid.INT().getText())

        name = ctx.name.text if ctx.name else None
        params = self._visit_param_list(ctx.paramList())
        results = self._visit_result_spec(ctx.resultSpec())
        body = self._visit_statement_list(ctx.statementList())

        return ProgramDef(
            loc=_loc(ctx),
            number=number,
            name=name,
            params=tuple(params),
            results=tuple(results),
            body=body,
        )

    def _visit_param_list(self, ctx: PlankalkulParser.ParamListContext) -> list[VarRef]:
        if ctx.varRef():
            return [self.visitVarRef(vr) for vr in ctx.varRef()]
        return []

    def _visit_result_spec(self, ctx: PlankalkulParser.ResultSpecContext) -> list[VarRef]:
        if isinstance(ctx, PlankalkulParser.SingleResultContext):
            return [self.visitVarRef(ctx.varRef())]
        elif isinstance(ctx, PlankalkulParser.MultiResultContext):
            return [self.visitVarRef(vr) for vr in ctx.varRef()]
        return []

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _visit_statement_list(self, ctx: PlankalkulParser.StatementListContext) -> list[StmtNode]:
        return [self.visit(s) for s in ctx.statement()]

    def visitAssignStmt(self, ctx: PlankalkulParser.AssignStmtContext) -> Assignment:
        value = self.visit(ctx.expr())
        target = self.visitVarRef(ctx.varRef())
        return Assignment(loc=_loc(ctx), value=value, target=target)

    def visitFreeStmt(self, ctx: PlankalkulParser.FreeStmtContext) -> Free:
        return Free(loc=_loc(ctx), value=self.visit(ctx.expr()))

    def visitGuardStmt(self, ctx: PlankalkulParser.GuardStmtContext) -> GuardedStmt:
        condition = self.visit(ctx.expr())
        guard_body = ctx.guardBody()
        body = self._visit_guard_body(guard_body)
        return GuardedStmt(loc=_loc(ctx), condition=condition, body=body)

    def _visit_guard_body(self, ctx) -> list[StmtNode]:
        if isinstance(ctx, PlankalkulParser.GuardBlockContext):
            return self._visit_statement_list(ctx.statementList())
        # GuardSingleContext — contains a single statement
        stmt = self.visit(ctx.statement())
        return [stmt]

    def visitWLoopStmt(self, ctx: PlankalkulParser.WLoopStmtContext) -> StmtNode:
        return self.visit(ctx.wLoop())

    def visitWLoop(self, ctx: PlankalkulParser.WLoopContext) -> WLoop:
        body = [self.visit(s) for s in ctx.statement()]
        return WLoop(loc=_loc(ctx), body=body)

    def visitIndexedLoopStmt(self, ctx):
        return self.visit(ctx.indexedLoop())

    def visitIndexedLoop(self, ctx):
        return IndexedLoop(loc=_loc(ctx), variant=int(ctx.INDEXED_W().getText()[1:]),
                           index=int(ctx.INDEX().getText()[1:]),
                           bounds=tuple(self.visit(e) for e in ctx.expr()),
                           body=self._visit_statement_list(ctx.statementList()))

    def visitIndexAtom(self, ctx):
        return IndexRef(loc=_loc(ctx), index=int(ctx.INDEX().getText()[1:]))

    def visitIndexComponentElem(self, ctx):
        return DynamicAccess(loc=_loc(ctx), expr=self.visitIndexAtom(ctx))

    def visitFinStmt(self, ctx):
        digits = ctx.FIN().getText()[3:].lstrip('0')
        # A depth with more digits than source length cannot fit its nesting.
        if len(digits) > len(str(len(ctx.start.getInputStream().strdata))):
            raise AstError("FIN depth exceeds available nesting", _loc(ctx))
        depth = int(digits or '0') if ctx.FIN().getText()[3:] else 1
        return Fin(loc=_loc(ctx), depth=depth,
                   condition=self.visit(ctx.expr()) if ctx.expr() else None)

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def visitExpr(self, ctx: PlankalkulParser.ExprContext) -> ExprNode:
        return self.visit(ctx.orExpr())

    def visitOrExpr(self, ctx: PlankalkulParser.OrExprContext) -> ExprNode:
        exprs = ctx.andExpr()
        result = self.visit(exprs[0])
        for i in range(1, len(exprs)):
            right = self.visit(exprs[i])
            result = BinaryExpr(loc=result.loc, op=BinOp.OR, left=result, right=right)
        return result

    def visitAndExpr(self, ctx: PlankalkulParser.AndExprContext) -> ExprNode:
        exprs = ctx.compExpr()
        result = self.visit(exprs[0])
        for i in range(1, len(exprs)):
            right = self.visit(exprs[i])
            result = BinaryExpr(loc=result.loc, op=BinOp.AND, left=result, right=right)
        return result

    def visitCompExpr(self, ctx: PlankalkulParser.CompExprContext) -> ExprNode:
        add_exprs = ctx.addExpr()
        left = self.visit(add_exprs[0])
        if len(add_exprs) > 1:
            op_text = ctx.compOp().getText()
            op = _COMP_OPS[op_text]
            right = self.visit(add_exprs[1])
            return BinaryExpr(loc=left.loc, op=op, left=left, right=right)
        return left

    def visitAddExpr(self, ctx: PlankalkulParser.AddExprContext) -> ExprNode:
        children = list(ctx.getChildren())
        result = self.visit(ctx.mulExpr(0))
        mul_idx = 1
        for child in children:
            text = child.getText() if hasattr(child, 'getText') else ''
            if text == '+':
                mul_idx_val = mul_idx
                mul_idx += 1
                right = self.visit(ctx.mulExpr(mul_idx_val))
                result = BinaryExpr(loc=result.loc, op=BinOp.ADD, left=result, right=right)
            elif text == '-':
                mul_idx_val = mul_idx
                mul_idx += 1
                right = self.visit(ctx.mulExpr(mul_idx_val))
                result = BinaryExpr(loc=result.loc, op=BinOp.SUB, left=result, right=right)
        return result

    def visitMulExpr(self, ctx: PlankalkulParser.MulExprContext) -> ExprNode:
        children = list(ctx.getChildren())
        result = self.visit(ctx.powExpr(0))
        pow_idx = 1
        for child in children:
            text = child.getText() if hasattr(child, 'getText') else ''
            if text == '*':
                idx = pow_idx
                pow_idx += 1
                right = self.visit(ctx.powExpr(idx))
                result = BinaryExpr(loc=result.loc, op=BinOp.MUL, left=result, right=right)
            elif text == '/':
                idx = pow_idx
                pow_idx += 1
                right = self.visit(ctx.powExpr(idx))
                result = BinaryExpr(loc=result.loc, op=BinOp.DIV, left=result, right=right)
        return result

    def visitPowExpr(self, ctx: PlankalkulParser.PowExprContext) -> ExprNode:
        unaries = ctx.unaryExpr()
        base = self.visit(unaries[0])
        if len(unaries) > 1:
            exp = self.visit(unaries[1])
            return BinaryExpr(loc=base.loc, op=BinOp.POW, left=base, right=exp)
        return base

    def visitNotExpr(self, ctx: PlankalkulParser.NotExprContext) -> UnaryExpr:
        operand = self.visit(ctx.unaryExpr())
        return UnaryExpr(loc=_loc(ctx), op=UnOp.NOT, operand=operand)

    def visitNegExpr(self, ctx: PlankalkulParser.NegExprContext) -> UnaryExpr:
        operand = self.visit(ctx.unaryExpr())
        return UnaryExpr(loc=_loc(ctx), op=UnOp.NEG, operand=operand)

    def visitAtomExpr(self, ctx: PlankalkulParser.AtomExprContext) -> ExprNode:
        return self.visit(ctx.atom())

    # ------------------------------------------------------------------
    # Atoms
    # ------------------------------------------------------------------

    def visitIntLiteral(self, ctx: PlankalkulParser.IntLiteralContext) -> IntLiteral:
        return IntLiteral(loc=_loc(ctx), value=int(ctx.INT().getText()))

    def visitTrueLiteral(self, ctx: PlankalkulParser.TrueLiteralContext) -> BoolLiteral:
        return BoolLiteral(loc=_loc(ctx), value=True)

    def visitBitseqLiteral(self, ctx: PlankalkulParser.BitseqLiteralContext) -> BitSeqLiteral:
        text = ctx.BITSEQ().getText()
        bits = tuple(ch == 'L' for ch in text)
        return BitSeqLiteral(loc=_loc(ctx), bits=bits)

    def visitNilLiteral(self, ctx: PlankalkulParser.NilLiteralContext) -> NilLiteral:
        return NilLiteral(loc=_loc(ctx))

    def visitAllocateAtom(self, ctx: PlankalkulParser.AllocateAtomContext) -> Allocate:
        return Allocate(loc=_loc(ctx), target=ctx.name.text)

    def visitFuncCallAtom(self, ctx: PlankalkulParser.FuncCallAtomContext) -> ExprNode:
        return self.visit(ctx.funcCall())

    def visitFuncCall(self, ctx: PlankalkulParser.FuncCallContext) -> FuncCall:
        if ctx.ID() or ctx.LIST_OP():
            name = (ctx.ID() or ctx.LIST_OP()).getText()
        else:
            pid = ctx.programId()
            number = int(pid.INT().getText())
            name = f"P{number}"

        arg_list = ctx.argList()
        args = tuple(self.visit(e) for e in arg_list.expr()) if arg_list.expr() else ()
        return FuncCall(loc=_loc(ctx), name=name, args=args)

    def visitVarAtom(self, ctx: PlankalkulParser.VarAtomContext) -> VarRef:
        return self.visitVarRef(ctx.varRef())

    def visitParenExpr(self, ctx: PlankalkulParser.ParenExprContext) -> ExprNode:
        return self.visit(ctx.expr())

    # ------------------------------------------------------------------
    # Variable references
    # ------------------------------------------------------------------

    def visitVarRef(self, ctx: PlankalkulParser.VarRefContext) -> VarRef:
        kind = ctx.varKind().getText()
        index = int(ctx.INT().getText())

        type_ann = None
        if ctx.typeInline():
            type_ann = self.visit(ctx.typeInline())

        components: list[ComponentAccess] = []
        if ctx.component():
            for elem in ctx.component().componentElem():
                components.append(self.visit(elem))

        return VarRef(
            loc=_loc(ctx),
            kind=kind,
            index=index,
            type_ann=type_ann,
            components=tuple(components),
        )

    # ------------------------------------------------------------------
    # Inline type annotations
    # ------------------------------------------------------------------

    def visitInlineArray(self, ctx: PlankalkulParser.InlineArrayContext) -> ArrayType:
        size = int(ctx.INT().getText()) if ctx.INT() else None
        element = self.visit(ctx.typeInline())
        return ArrayType(loc=_loc(ctx), size=size, element_type=element)

    def visitInlineRecord(self, ctx: PlankalkulParser.InlineRecordContext) -> RecordType:
        fields = tuple(self.visit(ti) for ti in ctx.typeInline())
        return RecordType(loc=_loc(ctx), fields=fields)

    def visitInlineUserType(self, ctx: PlankalkulParser.InlineUserTypeContext) -> UserType:
        return UserType(loc=_loc(ctx), name=ctx.name.text)

    def visitInlineRefType(self, ctx: PlankalkulParser.InlineRefTypeContext) -> RefType:
        return RefType(loc=_loc(ctx), target=ctx.name.text)

    def visitInlineSequence(self, ctx:PlankalkulParser.InlineSequenceContext):
        size = int(ctx.INT(0).getText())
        bit_marker = int(ctx.INT(1).getText())
        if bit_marker != 0:
            raise AstError(f"Expected bit type '0' but got '{bit_marker}'", loc=_loc(ctx))
        return BitSeqType(loc=_loc(ctx), length=size)

    def visitInlineBitType(self, ctx: PlankalkulParser.InlineBitTypeContext) -> TypeNode:
        return BitType(loc=_loc(ctx))

    def visitBitType(self, ctx: PlankalkulParser.BitTypeContext | PlankalkulParser.InlineBitTypeContext) -> BitType:
        value = int(ctx.INT().getText())
        if value != 0:
            raise AstError(f"Expected bit type '0' but got '{value}'", loc=_loc(ctx))
        return BitType(loc=_loc(ctx))

    # ------------------------------------------------------------------
    # Component access (Berlin-style: inside brackets)
    # ------------------------------------------------------------------

    def visitStaticComponentElem(self, ctx: PlankalkulParser.StaticComponentElemContext) -> StaticAccess:
        index = int(ctx.INT().getText())
        return StaticAccess(loc=_loc(ctx), index=index)

    def visitVarComponentElem(self, ctx: PlankalkulParser.VarComponentElemContext) -> DynamicAccess:
        kind = ctx.varKind().getText()
        index = int(ctx.INT().getText())
        var = VarRef(loc=_loc(ctx), kind=kind, index=index, type_ann=None, components=())
        return DynamicAccess(loc=_loc(ctx), expr=var)

    def visitExprComponentElem(self, ctx: PlankalkulParser.ExprComponentElemContext) -> DynamicAccess:
        expr = self.visit(ctx.expr())
        return DynamicAccess(loc=_loc(ctx), expr=expr)

    def visitDereferenceComponentElem(
        self, ctx: PlankalkulParser.DereferenceComponentElemContext
    ) -> DereferenceAccess:
        return DereferenceAccess(loc=_loc(ctx))
