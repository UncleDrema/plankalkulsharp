"""Build AST from ANTLR4 parse tree (CST → AST).

Uses the visitor pattern to walk the ANTLR4 concrete syntax tree and
produce the plankalkulsharp AST node hierarchy.
"""

from __future__ import annotations

from antlr4 import ParserRuleContext

from plankalkulsharp.my_ast.nodes import (
    ArrayType,
    Assignment,
    BinOp,
    BinaryExpr,
    BitSeqLiteral,
    BitSeqType,
    BitType,
    BoolLiteral,
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
from plankalkulsharp.frontend.generated.PlankalkulParser import PlankalkulParser
from plankalkulsharp.frontend.generated.PlankalkulVisitor import PlankalkulVisitor


def _loc(ctx: ParserRuleContext) -> Loc:
    token = ctx.start
    return Loc(line=token.line, column=token.column)


def _loc_token(token) -> Loc:
    return Loc(line=token.line, column=token.column)


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
        index = int(ctx.INT().getText())
        type_expr = self.visit(ctx.typeExpr())
        return TypeDef(loc=_loc(ctx), index=index, type_expr=type_expr)

    def visitBitType(self, ctx: PlankalkulParser.BitTypeContext) -> BitType:
        return BitType(loc=_loc(ctx))

    def visitBitSeqType(self, ctx: PlankalkulParser.BitSeqTypeContext) -> BitSeqType:
        length = int(ctx.INT().getText())
        return BitSeqType(loc=_loc(ctx), length=length)

    def visitArrayType(self, ctx: PlankalkulParser.ArrayTypeContext) -> ArrayType:
        size = int(ctx.INT().getText())
        element_type = self.visit(ctx.typeExpr())
        return ArrayType(loc=_loc(ctx), size=size, element_type=element_type)

    def visitRecordType(self, ctx: PlankalkulParser.RecordTypeContext) -> RecordType:
        fields = tuple(self.visit(te) for te in ctx.typeExpr())
        return RecordType(loc=_loc(ctx), fields=fields)

    def visitUserType(self, ctx: PlankalkulParser.UserTypeContext) -> UserType:
        index = int(ctx.INT().getText())
        return UserType(loc=_loc(ctx), index=index)

    # ------------------------------------------------------------------
    # Program definitions
    # ------------------------------------------------------------------

    def visitProgramDef(self, ctx: PlankalkulParser.ProgramDefContext) -> ProgramDef:
        pid = ctx.programId()
        ints = pid.INT()
        number = int(ints[0].getText())
        sub_number = int(ints[1].getText()) if len(ints) > 1 else None

        name = ctx.name.text if ctx.name else None
        params = self._visit_param_list(ctx.paramList())
        results = self._visit_result_spec(ctx.resultSpec())
        body = self._visit_statement_list(ctx.statementList())

        return ProgramDef(
            loc=_loc(ctx),
            number=number,
            sub_number=sub_number,
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

    def visitForLoopStmt(self, ctx: PlankalkulParser.ForLoopStmtContext) -> StmtNode:
        return self.visit(ctx.forLoop())

    def visitForLoop(self, ctx: PlankalkulParser.ForLoopContext) -> ForLoop:
        var = self.visitVarRef(ctx.varRef())
        exprs = ctx.expr()
        start = self.visit(exprs[0])
        end = self.visit(exprs[1])
        body = self._visit_statement_list(ctx.statementList())
        return ForLoop(loc=_loc(ctx), var=var, start=start, end=end, body=body)

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

    def visitFuncCallAtom(self, ctx: PlankalkulParser.FuncCallAtomContext) -> ExprNode:
        return self.visit(ctx.funcCall())

    def visitFuncCall(self, ctx: PlankalkulParser.FuncCallContext) -> FuncCall:
        if ctx.ID():
            name = ctx.ID().getText()
        else:
            pid = ctx.programId()
            ints = pid.INT()
            name = f"P{ints[0].getText()}"
            if len(ints) > 1:
                name += f".{ints[1].getText()}"

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
        size = int(ctx.INT().getText())
        element = self.visit(ctx.typeInline())
        return ArrayType(loc=_loc(ctx), size=size, element_type=element)

    def visitInlineRecord(self, ctx: PlankalkulParser.InlineRecordContext) -> RecordType:
        fields = tuple(self.visit(ti) for ti in ctx.typeInline())
        return RecordType(loc=_loc(ctx), fields=fields)

    def visitInlineUserType(self, ctx: PlankalkulParser.InlineUserTypeContext) -> UserType:
        index = int(ctx.INT().getText())
        return UserType(loc=_loc(ctx), index=index)

    def visitInlineTerminal(self, ctx: PlankalkulParser.InlineTerminalContext) -> TypeNode:
        value = int(ctx.INT().getText())
        if value == 0:
            return BitType(loc=_loc(ctx))
        # Non-zero terminal typically means S1·value (bit sequence)
        return BitSeqType(loc=_loc(ctx), length=value)

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
