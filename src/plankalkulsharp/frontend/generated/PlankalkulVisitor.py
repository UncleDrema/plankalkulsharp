# Generated from C:/Users/missl/Work/edu/plankalkulsharp/grammar/Plankalkul.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .PlankalkulParser import PlankalkulParser
else:
    from PlankalkulParser import PlankalkulParser

# This class defines a complete generic visitor for a parse tree produced by PlankalkulParser.

class PlankalkulVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by PlankalkulParser#program.
    def visitProgram(self, ctx:PlankalkulParser.ProgramContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#typeDef.
    def visitTypeDef(self, ctx:PlankalkulParser.TypeDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#bitType.
    def visitBitType(self, ctx:PlankalkulParser.BitTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#bitSeqType.
    def visitBitSeqType(self, ctx:PlankalkulParser.BitSeqTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#arrayType.
    def visitArrayType(self, ctx:PlankalkulParser.ArrayTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#recordType.
    def visitRecordType(self, ctx:PlankalkulParser.RecordTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#userType.
    def visitUserType(self, ctx:PlankalkulParser.UserTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#refType.
    def visitRefType(self, ctx:PlankalkulParser.RefTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#programDef.
    def visitProgramDef(self, ctx:PlankalkulParser.ProgramDefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#programId.
    def visitProgramId(self, ctx:PlankalkulParser.ProgramIdContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#paramList.
    def visitParamList(self, ctx:PlankalkulParser.ParamListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#singleResult.
    def visitSingleResult(self, ctx:PlankalkulParser.SingleResultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#multiResult.
    def visitMultiResult(self, ctx:PlankalkulParser.MultiResultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#statementList.
    def visitStatementList(self, ctx:PlankalkulParser.StatementListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#assignStmt.
    def visitAssignStmt(self, ctx:PlankalkulParser.AssignStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#freeStmt.
    def visitFreeStmt(self, ctx:PlankalkulParser.FreeStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#guardStmt.
    def visitGuardStmt(self, ctx:PlankalkulParser.GuardStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#wLoopStmt.
    def visitWLoopStmt(self, ctx:PlankalkulParser.WLoopStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#indexedLoopStmt.
    def visitIndexedLoopStmt(self, ctx:PlankalkulParser.IndexedLoopStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#finStmt.
    def visitFinStmt(self, ctx:PlankalkulParser.FinStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#guardBlock.
    def visitGuardBlock(self, ctx:PlankalkulParser.GuardBlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#guardSingle.
    def visitGuardSingle(self, ctx:PlankalkulParser.GuardSingleContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#wLoop.
    def visitWLoop(self, ctx:PlankalkulParser.WLoopContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#indexedLoop.
    def visitIndexedLoop(self, ctx:PlankalkulParser.IndexedLoopContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#expr.
    def visitExpr(self, ctx:PlankalkulParser.ExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#orExpr.
    def visitOrExpr(self, ctx:PlankalkulParser.OrExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#andExpr.
    def visitAndExpr(self, ctx:PlankalkulParser.AndExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#compExpr.
    def visitCompExpr(self, ctx:PlankalkulParser.CompExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#compOp.
    def visitCompOp(self, ctx:PlankalkulParser.CompOpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#addExpr.
    def visitAddExpr(self, ctx:PlankalkulParser.AddExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#mulExpr.
    def visitMulExpr(self, ctx:PlankalkulParser.MulExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#powExpr.
    def visitPowExpr(self, ctx:PlankalkulParser.PowExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#notExpr.
    def visitNotExpr(self, ctx:PlankalkulParser.NotExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#negExpr.
    def visitNegExpr(self, ctx:PlankalkulParser.NegExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#atomExpr.
    def visitAtomExpr(self, ctx:PlankalkulParser.AtomExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#intLiteral.
    def visitIntLiteral(self, ctx:PlankalkulParser.IntLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#trueLiteral.
    def visitTrueLiteral(self, ctx:PlankalkulParser.TrueLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#bitseqLiteral.
    def visitBitseqLiteral(self, ctx:PlankalkulParser.BitseqLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#nilLiteral.
    def visitNilLiteral(self, ctx:PlankalkulParser.NilLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#allocateAtom.
    def visitAllocateAtom(self, ctx:PlankalkulParser.AllocateAtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#funcCallAtom.
    def visitFuncCallAtom(self, ctx:PlankalkulParser.FuncCallAtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#indexAtom.
    def visitIndexAtom(self, ctx:PlankalkulParser.IndexAtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#varAtom.
    def visitVarAtom(self, ctx:PlankalkulParser.VarAtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#parenExpr.
    def visitParenExpr(self, ctx:PlankalkulParser.ParenExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#listLiteral.
    def visitListLiteral(self, ctx:PlankalkulParser.ListLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#recordLiteral.
    def visitRecordLiteral(self, ctx:PlankalkulParser.RecordLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#funcCall.
    def visitFuncCall(self, ctx:PlankalkulParser.FuncCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#argList.
    def visitArgList(self, ctx:PlankalkulParser.ArgListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#varRef.
    def visitVarRef(self, ctx:PlankalkulParser.VarRefContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#varKind.
    def visitVarKind(self, ctx:PlankalkulParser.VarKindContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#component.
    def visitComponent(self, ctx:PlankalkulParser.ComponentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#staticComponentElem.
    def visitStaticComponentElem(self, ctx:PlankalkulParser.StaticComponentElemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#varComponentElem.
    def visitVarComponentElem(self, ctx:PlankalkulParser.VarComponentElemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#indexComponentElem.
    def visitIndexComponentElem(self, ctx:PlankalkulParser.IndexComponentElemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#exprComponentElem.
    def visitExprComponentElem(self, ctx:PlankalkulParser.ExprComponentElemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#dereferenceComponentElem.
    def visitDereferenceComponentElem(self, ctx:PlankalkulParser.DereferenceComponentElemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#inlineSequence.
    def visitInlineSequence(self, ctx:PlankalkulParser.InlineSequenceContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#inlineArray.
    def visitInlineArray(self, ctx:PlankalkulParser.InlineArrayContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#inlineRecord.
    def visitInlineRecord(self, ctx:PlankalkulParser.InlineRecordContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#inlineUserType.
    def visitInlineUserType(self, ctx:PlankalkulParser.InlineUserTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#inlineBitType.
    def visitInlineBitType(self, ctx:PlankalkulParser.InlineBitTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by PlankalkulParser#inlineRefType.
    def visitInlineRefType(self, ctx:PlankalkulParser.InlineRefTypeContext):
        return self.visitChildren(ctx)



del PlankalkulParser
