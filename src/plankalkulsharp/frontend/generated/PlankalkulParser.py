# Generated from C:/Users/missl/Work/edu/plankalkulsharp/grammar/Plankalkul.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,43,312,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,1,0,1,0,5,0,61,8,0,10,0,12,0,64,9,0,1,0,1,0,
        1,1,1,1,1,1,1,1,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,4,2,
        83,8,2,11,2,12,2,84,1,2,1,2,1,2,3,2,90,8,2,1,3,1,3,3,3,94,8,3,1,
        3,1,3,1,3,1,3,1,3,1,3,1,3,1,3,1,4,1,4,1,4,1,5,1,5,1,5,5,5,110,8,
        5,10,5,12,5,113,9,5,1,5,3,5,116,8,5,1,6,1,6,1,6,1,6,1,6,4,6,123,
        8,6,11,6,12,6,124,1,6,1,6,3,6,129,8,6,1,7,5,7,132,8,7,10,7,12,7,
        135,9,7,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,1,8,3,8,147,8,8,1,9,
        1,9,1,9,1,9,1,9,3,9,154,8,9,1,10,1,10,1,10,4,10,159,8,10,11,10,12,
        10,160,1,10,1,10,1,11,1,11,1,11,1,11,1,11,1,11,1,11,1,11,1,11,1,
        11,1,12,1,12,1,13,1,13,1,13,5,13,180,8,13,10,13,12,13,183,9,13,1,
        14,1,14,1,14,5,14,188,8,14,10,14,12,14,191,9,14,1,15,1,15,1,15,1,
        15,3,15,197,8,15,1,16,1,16,1,17,1,17,1,17,5,17,204,8,17,10,17,12,
        17,207,9,17,1,18,1,18,1,18,5,18,212,8,18,10,18,12,18,215,9,18,1,
        19,1,19,1,19,3,19,220,8,19,1,20,1,20,1,20,1,20,1,20,3,20,227,8,20,
        1,21,1,21,1,21,1,21,1,21,1,21,1,21,1,21,1,21,3,21,238,8,21,1,22,
        1,22,3,22,242,8,22,1,22,1,22,1,22,1,22,1,23,1,23,1,23,5,23,251,8,
        23,10,23,12,23,254,9,23,1,23,3,23,257,8,23,1,24,1,24,1,24,1,24,3,
        24,263,8,24,1,24,1,24,3,24,267,8,24,1,24,3,24,270,8,24,1,25,1,25,
        1,26,1,26,1,26,5,26,277,8,26,10,26,12,26,280,9,26,1,27,1,27,1,27,
        1,27,1,27,1,27,1,27,1,27,3,27,290,8,27,1,28,1,28,1,28,1,28,1,28,
        1,28,1,28,1,28,1,28,1,28,4,28,302,8,28,11,28,12,28,303,1,28,1,28,
        1,28,1,28,3,28,310,8,28,1,28,0,0,29,0,2,4,6,8,10,12,14,16,18,20,
        22,24,26,28,30,32,34,36,38,40,42,44,46,48,50,52,54,56,0,4,2,0,1,
        1,15,19,1,0,20,21,1,0,22,23,1,0,30,33,327,0,62,1,0,0,0,2,67,1,0,
        0,0,4,89,1,0,0,0,6,91,1,0,0,0,8,103,1,0,0,0,10,115,1,0,0,0,12,128,
        1,0,0,0,14,133,1,0,0,0,16,146,1,0,0,0,18,153,1,0,0,0,20,155,1,0,
        0,0,22,164,1,0,0,0,24,174,1,0,0,0,26,176,1,0,0,0,28,184,1,0,0,0,
        30,192,1,0,0,0,32,198,1,0,0,0,34,200,1,0,0,0,36,208,1,0,0,0,38,216,
        1,0,0,0,40,226,1,0,0,0,42,237,1,0,0,0,44,241,1,0,0,0,46,256,1,0,
        0,0,48,258,1,0,0,0,50,271,1,0,0,0,52,273,1,0,0,0,54,289,1,0,0,0,
        56,309,1,0,0,0,58,61,3,2,1,0,59,61,3,6,3,0,60,58,1,0,0,0,60,59,1,
        0,0,0,61,64,1,0,0,0,62,60,1,0,0,0,62,63,1,0,0,0,63,65,1,0,0,0,64,
        62,1,0,0,0,65,66,5,0,0,1,66,1,1,0,0,0,67,68,5,39,0,0,68,69,5,1,0,
        0,69,70,3,4,2,0,70,3,1,0,0,0,71,90,5,38,0,0,72,73,5,38,0,0,73,74,
        5,2,0,0,74,90,5,38,0,0,75,76,5,38,0,0,76,77,5,3,0,0,77,90,3,4,2,
        0,78,79,5,4,0,0,79,82,3,4,2,0,80,81,5,5,0,0,81,83,3,4,2,0,82,80,
        1,0,0,0,83,84,1,0,0,0,84,82,1,0,0,0,84,85,1,0,0,0,85,86,1,0,0,0,
        86,87,5,6,0,0,87,90,1,0,0,0,88,90,5,39,0,0,89,71,1,0,0,0,89,72,1,
        0,0,0,89,75,1,0,0,0,89,78,1,0,0,0,89,88,1,0,0,0,90,5,1,0,0,0,91,
        93,3,8,4,0,92,94,5,39,0,0,93,92,1,0,0,0,93,94,1,0,0,0,94,95,1,0,
        0,0,95,96,5,4,0,0,96,97,3,10,5,0,97,98,5,6,0,0,98,99,5,7,0,0,99,
        100,3,12,6,0,100,101,3,14,7,0,101,102,5,34,0,0,102,7,1,0,0,0,103,
        104,5,8,0,0,104,105,5,38,0,0,105,9,1,0,0,0,106,111,3,48,24,0,107,
        108,5,5,0,0,108,110,3,48,24,0,109,107,1,0,0,0,110,113,1,0,0,0,111,
        109,1,0,0,0,111,112,1,0,0,0,112,116,1,0,0,0,113,111,1,0,0,0,114,
        116,1,0,0,0,115,106,1,0,0,0,115,114,1,0,0,0,116,11,1,0,0,0,117,129,
        3,48,24,0,118,119,5,4,0,0,119,122,3,48,24,0,120,121,5,5,0,0,121,
        123,3,48,24,0,122,120,1,0,0,0,123,124,1,0,0,0,124,122,1,0,0,0,124,
        125,1,0,0,0,125,126,1,0,0,0,126,127,5,6,0,0,127,129,1,0,0,0,128,
        117,1,0,0,0,128,118,1,0,0,0,129,13,1,0,0,0,130,132,3,16,8,0,131,
        130,1,0,0,0,132,135,1,0,0,0,133,131,1,0,0,0,133,134,1,0,0,0,134,
        15,1,0,0,0,135,133,1,0,0,0,136,137,3,24,12,0,137,138,5,9,0,0,138,
        139,3,48,24,0,139,147,1,0,0,0,140,141,3,24,12,0,141,142,5,7,0,0,
        142,143,3,18,9,0,143,147,1,0,0,0,144,147,3,20,10,0,145,147,3,22,
        11,0,146,136,1,0,0,0,146,140,1,0,0,0,146,144,1,0,0,0,146,145,1,0,
        0,0,147,17,1,0,0,0,148,149,5,10,0,0,149,150,3,14,7,0,150,151,5,11,
        0,0,151,154,1,0,0,0,152,154,3,16,8,0,153,148,1,0,0,0,153,152,1,0,
        0,0,154,19,1,0,0,0,155,156,5,12,0,0,156,158,5,10,0,0,157,159,3,16,
        8,0,158,157,1,0,0,0,159,160,1,0,0,0,160,158,1,0,0,0,160,161,1,0,
        0,0,161,162,1,0,0,0,162,163,5,11,0,0,163,21,1,0,0,0,164,165,5,35,
        0,0,165,166,3,48,24,0,166,167,5,36,0,0,167,168,3,24,12,0,168,169,
        5,37,0,0,169,170,3,24,12,0,170,171,5,10,0,0,171,172,3,14,7,0,172,
        173,5,11,0,0,173,23,1,0,0,0,174,175,3,26,13,0,175,25,1,0,0,0,176,
        181,3,28,14,0,177,178,5,13,0,0,178,180,3,28,14,0,179,177,1,0,0,0,
        180,183,1,0,0,0,181,179,1,0,0,0,181,182,1,0,0,0,182,27,1,0,0,0,183,
        181,1,0,0,0,184,189,3,30,15,0,185,186,5,14,0,0,186,188,3,30,15,0,
        187,185,1,0,0,0,188,191,1,0,0,0,189,187,1,0,0,0,189,190,1,0,0,0,
        190,29,1,0,0,0,191,189,1,0,0,0,192,196,3,34,17,0,193,194,3,32,16,
        0,194,195,3,34,17,0,195,197,1,0,0,0,196,193,1,0,0,0,196,197,1,0,
        0,0,197,31,1,0,0,0,198,199,7,0,0,0,199,33,1,0,0,0,200,205,3,36,18,
        0,201,202,7,1,0,0,202,204,3,36,18,0,203,201,1,0,0,0,204,207,1,0,
        0,0,205,203,1,0,0,0,205,206,1,0,0,0,206,35,1,0,0,0,207,205,1,0,0,
        0,208,213,3,38,19,0,209,210,7,2,0,0,210,212,3,38,19,0,211,209,1,
        0,0,0,212,215,1,0,0,0,213,211,1,0,0,0,213,214,1,0,0,0,214,37,1,0,
        0,0,215,213,1,0,0,0,216,219,3,40,20,0,217,218,5,24,0,0,218,220,3,
        40,20,0,219,217,1,0,0,0,219,220,1,0,0,0,220,39,1,0,0,0,221,222,5,
        25,0,0,222,227,3,40,20,0,223,224,5,21,0,0,224,227,3,40,20,0,225,
        227,3,42,21,0,226,221,1,0,0,0,226,223,1,0,0,0,226,225,1,0,0,0,227,
        41,1,0,0,0,228,238,5,38,0,0,229,238,5,26,0,0,230,238,5,40,0,0,231,
        238,3,44,22,0,232,238,3,48,24,0,233,234,5,4,0,0,234,235,3,24,12,
        0,235,236,5,6,0,0,236,238,1,0,0,0,237,228,1,0,0,0,237,229,1,0,0,
        0,237,230,1,0,0,0,237,231,1,0,0,0,237,232,1,0,0,0,237,233,1,0,0,
        0,238,43,1,0,0,0,239,242,5,39,0,0,240,242,3,8,4,0,241,239,1,0,0,
        0,241,240,1,0,0,0,242,243,1,0,0,0,243,244,5,4,0,0,244,245,3,46,23,
        0,245,246,5,6,0,0,246,45,1,0,0,0,247,252,3,24,12,0,248,249,5,5,0,
        0,249,251,3,24,12,0,250,248,1,0,0,0,251,254,1,0,0,0,252,250,1,0,
        0,0,252,253,1,0,0,0,253,257,1,0,0,0,254,252,1,0,0,0,255,257,1,0,
        0,0,256,247,1,0,0,0,256,255,1,0,0,0,257,47,1,0,0,0,258,259,3,50,
        25,0,259,269,5,38,0,0,260,262,5,27,0,0,261,263,3,52,26,0,262,261,
        1,0,0,0,262,263,1,0,0,0,263,266,1,0,0,0,264,265,5,28,0,0,265,267,
        3,56,28,0,266,264,1,0,0,0,266,267,1,0,0,0,267,268,1,0,0,0,268,270,
        5,29,0,0,269,260,1,0,0,0,269,270,1,0,0,0,270,49,1,0,0,0,271,272,
        7,3,0,0,272,51,1,0,0,0,273,278,3,54,27,0,274,275,5,2,0,0,275,277,
        3,54,27,0,276,274,1,0,0,0,277,280,1,0,0,0,278,276,1,0,0,0,278,279,
        1,0,0,0,279,53,1,0,0,0,280,278,1,0,0,0,281,290,5,38,0,0,282,283,
        3,50,25,0,283,284,5,38,0,0,284,290,1,0,0,0,285,286,5,4,0,0,286,287,
        3,24,12,0,287,288,5,6,0,0,288,290,1,0,0,0,289,281,1,0,0,0,289,282,
        1,0,0,0,289,285,1,0,0,0,290,55,1,0,0,0,291,292,5,38,0,0,292,293,
        5,2,0,0,293,310,5,38,0,0,294,295,5,38,0,0,295,296,5,3,0,0,296,310,
        3,56,28,0,297,298,5,4,0,0,298,301,3,56,28,0,299,300,5,5,0,0,300,
        302,3,56,28,0,301,299,1,0,0,0,302,303,1,0,0,0,303,301,1,0,0,0,303,
        304,1,0,0,0,304,305,1,0,0,0,305,306,5,6,0,0,306,310,1,0,0,0,307,
        310,5,39,0,0,308,310,5,38,0,0,309,291,1,0,0,0,309,294,1,0,0,0,309,
        297,1,0,0,0,309,307,1,0,0,0,309,308,1,0,0,0,310,57,1,0,0,0,31,60,
        62,84,89,93,111,115,124,128,133,146,153,160,181,189,196,205,213,
        219,226,237,241,252,256,262,266,269,278,289,303,309
    ]

class PlankalkulParser ( Parser ):

    grammarFileName = "Plankalkul.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'='", "'.'", "'x'", "'('", "','", "')'", 
                     "'->'", "'P'", "'=>'", "'{'", "'}'", "'W'", "'|'", 
                     "'&'", "'!='", "'<'", "'>'", "'<='", "'>='", "'+'", 
                     "'-'", "'*'", "'/'", "'**'", "'~'", "'L'", "'['", "':'", 
                     "']'", "'V'", "'Z'", "'C'", "'R'", "'END'", "'FOR'", 
                     "'FROM'", "'TO'" ]

    symbolicNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "END", "FOR", "FROM", "TO", 
                      "INT", "ID", "BITSEQ", "LINE_COMMENT", "BLOCK_COMMENT", 
                      "WS" ]

    RULE_program = 0
    RULE_typeDef = 1
    RULE_typeExpr = 2
    RULE_programDef = 3
    RULE_programId = 4
    RULE_paramList = 5
    RULE_resultSpec = 6
    RULE_statementList = 7
    RULE_statement = 8
    RULE_guardBody = 9
    RULE_wLoop = 10
    RULE_forLoop = 11
    RULE_expr = 12
    RULE_orExpr = 13
    RULE_andExpr = 14
    RULE_compExpr = 15
    RULE_compOp = 16
    RULE_addExpr = 17
    RULE_mulExpr = 18
    RULE_powExpr = 19
    RULE_unaryExpr = 20
    RULE_atom = 21
    RULE_funcCall = 22
    RULE_argList = 23
    RULE_varRef = 24
    RULE_varKind = 25
    RULE_component = 26
    RULE_componentElem = 27
    RULE_typeInline = 28

    ruleNames =  [ "program", "typeDef", "typeExpr", "programDef", "programId", 
                   "paramList", "resultSpec", "statementList", "statement", 
                   "guardBody", "wLoop", "forLoop", "expr", "orExpr", "andExpr", 
                   "compExpr", "compOp", "addExpr", "mulExpr", "powExpr", 
                   "unaryExpr", "atom", "funcCall", "argList", "varRef", 
                   "varKind", "component", "componentElem", "typeInline" ]

    EOF = Token.EOF
    T__0=1
    T__1=2
    T__2=3
    T__3=4
    T__4=5
    T__5=6
    T__6=7
    T__7=8
    T__8=9
    T__9=10
    T__10=11
    T__11=12
    T__12=13
    T__13=14
    T__14=15
    T__15=16
    T__16=17
    T__17=18
    T__18=19
    T__19=20
    T__20=21
    T__21=22
    T__22=23
    T__23=24
    T__24=25
    T__25=26
    T__26=27
    T__27=28
    T__28=29
    T__29=30
    T__30=31
    T__31=32
    T__32=33
    END=34
    FOR=35
    FROM=36
    TO=37
    INT=38
    ID=39
    BITSEQ=40
    LINE_COMMENT=41
    BLOCK_COMMENT=42
    WS=43

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class ProgramContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EOF(self):
            return self.getToken(PlankalkulParser.EOF, 0)

        def typeDef(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.TypeDefContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.TypeDefContext,i)


        def programDef(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.ProgramDefContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.ProgramDefContext,i)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_program

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitProgram" ):
                return visitor.visitProgram(self)
            else:
                return visitor.visitChildren(self)




    def program(self):

        localctx = PlankalkulParser.ProgramContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_program)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 62
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==8 or _la==39:
                self.state = 60
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [39]:
                    self.state = 58
                    self.typeDef()
                    pass
                elif token in [8]:
                    self.state = 59
                    self.programDef()
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 64
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 65
            self.match(PlankalkulParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeDefContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.name = None # Token

        def typeExpr(self):
            return self.getTypedRuleContext(PlankalkulParser.TypeExprContext,0)


        def ID(self):
            return self.getToken(PlankalkulParser.ID, 0)

        def getRuleIndex(self):
            return PlankalkulParser.RULE_typeDef

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTypeDef" ):
                return visitor.visitTypeDef(self)
            else:
                return visitor.visitChildren(self)




    def typeDef(self):

        localctx = PlankalkulParser.TypeDefContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_typeDef)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 67
            localctx.name = self.match(PlankalkulParser.ID)
            self.state = 68
            self.match(PlankalkulParser.T__0)
            self.state = 69
            self.typeExpr()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PlankalkulParser.RULE_typeExpr

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class ArrayTypeContext(TypeExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.TypeExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INT(self):
            return self.getToken(PlankalkulParser.INT, 0)
        def typeExpr(self):
            return self.getTypedRuleContext(PlankalkulParser.TypeExprContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArrayType" ):
                return visitor.visitArrayType(self)
            else:
                return visitor.visitChildren(self)


    class RecordTypeContext(TypeExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.TypeExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def typeExpr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.TypeExprContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.TypeExprContext,i)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRecordType" ):
                return visitor.visitRecordType(self)
            else:
                return visitor.visitChildren(self)


    class BitSeqTypeContext(TypeExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.TypeExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INT(self, i:int=None):
            if i is None:
                return self.getTokens(PlankalkulParser.INT)
            else:
                return self.getToken(PlankalkulParser.INT, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBitSeqType" ):
                return visitor.visitBitSeqType(self)
            else:
                return visitor.visitChildren(self)


    class UserTypeContext(TypeExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.TypeExprContext
            super().__init__(parser)
            self.name = None # Token
            self.copyFrom(ctx)

        def ID(self):
            return self.getToken(PlankalkulParser.ID, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUserType" ):
                return visitor.visitUserType(self)
            else:
                return visitor.visitChildren(self)


    class BitTypeContext(TypeExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.TypeExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INT(self):
            return self.getToken(PlankalkulParser.INT, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBitType" ):
                return visitor.visitBitType(self)
            else:
                return visitor.visitChildren(self)



    def typeExpr(self):

        localctx = PlankalkulParser.TypeExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_typeExpr)
        self._la = 0 # Token type
        try:
            self.state = 89
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,3,self._ctx)
            if la_ == 1:
                localctx = PlankalkulParser.BitTypeContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 71
                self.match(PlankalkulParser.INT)
                pass

            elif la_ == 2:
                localctx = PlankalkulParser.BitSeqTypeContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 72
                self.match(PlankalkulParser.INT)
                self.state = 73
                self.match(PlankalkulParser.T__1)
                self.state = 74
                self.match(PlankalkulParser.INT)
                pass

            elif la_ == 3:
                localctx = PlankalkulParser.ArrayTypeContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 75
                self.match(PlankalkulParser.INT)
                self.state = 76
                self.match(PlankalkulParser.T__2)
                self.state = 77
                self.typeExpr()
                pass

            elif la_ == 4:
                localctx = PlankalkulParser.RecordTypeContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 78
                self.match(PlankalkulParser.T__3)
                self.state = 79
                self.typeExpr()
                self.state = 82 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 80
                    self.match(PlankalkulParser.T__4)
                    self.state = 81
                    self.typeExpr()
                    self.state = 84 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==5):
                        break

                self.state = 86
                self.match(PlankalkulParser.T__5)
                pass

            elif la_ == 5:
                localctx = PlankalkulParser.UserTypeContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 88
                localctx.name = self.match(PlankalkulParser.ID)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ProgramDefContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.name = None # Token

        def programId(self):
            return self.getTypedRuleContext(PlankalkulParser.ProgramIdContext,0)


        def paramList(self):
            return self.getTypedRuleContext(PlankalkulParser.ParamListContext,0)


        def resultSpec(self):
            return self.getTypedRuleContext(PlankalkulParser.ResultSpecContext,0)


        def statementList(self):
            return self.getTypedRuleContext(PlankalkulParser.StatementListContext,0)


        def END(self):
            return self.getToken(PlankalkulParser.END, 0)

        def ID(self):
            return self.getToken(PlankalkulParser.ID, 0)

        def getRuleIndex(self):
            return PlankalkulParser.RULE_programDef

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitProgramDef" ):
                return visitor.visitProgramDef(self)
            else:
                return visitor.visitChildren(self)




    def programDef(self):

        localctx = PlankalkulParser.ProgramDefContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_programDef)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 91
            self.programId()
            self.state = 93
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==39:
                self.state = 92
                localctx.name = self.match(PlankalkulParser.ID)


            self.state = 95
            self.match(PlankalkulParser.T__3)
            self.state = 96
            self.paramList()
            self.state = 97
            self.match(PlankalkulParser.T__5)
            self.state = 98
            self.match(PlankalkulParser.T__6)
            self.state = 99
            self.resultSpec()
            self.state = 100
            self.statementList()
            self.state = 101
            self.match(PlankalkulParser.END)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ProgramIdContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def INT(self):
            return self.getToken(PlankalkulParser.INT, 0)

        def getRuleIndex(self):
            return PlankalkulParser.RULE_programId

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitProgramId" ):
                return visitor.visitProgramId(self)
            else:
                return visitor.visitChildren(self)




    def programId(self):

        localctx = PlankalkulParser.ProgramIdContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_programId)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 103
            self.match(PlankalkulParser.T__7)
            self.state = 104
            self.match(PlankalkulParser.INT)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ParamListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def varRef(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.VarRefContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.VarRefContext,i)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_paramList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParamList" ):
                return visitor.visitParamList(self)
            else:
                return visitor.visitChildren(self)




    def paramList(self):

        localctx = PlankalkulParser.ParamListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_paramList)
        self._la = 0 # Token type
        try:
            self.state = 115
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [30, 31, 32, 33]:
                self.enterOuterAlt(localctx, 1)
                self.state = 106
                self.varRef()
                self.state = 111
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==5:
                    self.state = 107
                    self.match(PlankalkulParser.T__4)
                    self.state = 108
                    self.varRef()
                    self.state = 113
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                pass
            elif token in [6]:
                self.enterOuterAlt(localctx, 2)

                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ResultSpecContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PlankalkulParser.RULE_resultSpec

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class SingleResultContext(ResultSpecContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.ResultSpecContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def varRef(self):
            return self.getTypedRuleContext(PlankalkulParser.VarRefContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSingleResult" ):
                return visitor.visitSingleResult(self)
            else:
                return visitor.visitChildren(self)


    class MultiResultContext(ResultSpecContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.ResultSpecContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def varRef(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.VarRefContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.VarRefContext,i)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMultiResult" ):
                return visitor.visitMultiResult(self)
            else:
                return visitor.visitChildren(self)



    def resultSpec(self):

        localctx = PlankalkulParser.ResultSpecContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_resultSpec)
        self._la = 0 # Token type
        try:
            self.state = 128
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [30, 31, 32, 33]:
                localctx = PlankalkulParser.SingleResultContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 117
                self.varRef()
                pass
            elif token in [4]:
                localctx = PlankalkulParser.MultiResultContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 118
                self.match(PlankalkulParser.T__3)
                self.state = 119
                self.varRef()
                self.state = 122 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 120
                    self.match(PlankalkulParser.T__4)
                    self.state = 121
                    self.varRef()
                    self.state = 124 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==5):
                        break

                self.state = 126
                self.match(PlankalkulParser.T__5)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StatementListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def statement(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.StatementContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.StatementContext,i)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_statementList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStatementList" ):
                return visitor.visitStatementList(self)
            else:
                return visitor.visitChildren(self)




    def statementList(self):

        localctx = PlankalkulParser.StatementListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_statementList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 133
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 1974713979152) != 0):
                self.state = 130
                self.statement()
                self.state = 135
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class StatementContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PlankalkulParser.RULE_statement

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class GuardStmtContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self):
            return self.getTypedRuleContext(PlankalkulParser.ExprContext,0)

        def guardBody(self):
            return self.getTypedRuleContext(PlankalkulParser.GuardBodyContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGuardStmt" ):
                return visitor.visitGuardStmt(self)
            else:
                return visitor.visitChildren(self)


    class AssignStmtContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self):
            return self.getTypedRuleContext(PlankalkulParser.ExprContext,0)

        def varRef(self):
            return self.getTypedRuleContext(PlankalkulParser.VarRefContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAssignStmt" ):
                return visitor.visitAssignStmt(self)
            else:
                return visitor.visitChildren(self)


    class WLoopStmtContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def wLoop(self):
            return self.getTypedRuleContext(PlankalkulParser.WLoopContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitWLoopStmt" ):
                return visitor.visitWLoopStmt(self)
            else:
                return visitor.visitChildren(self)


    class ForLoopStmtContext(StatementContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.StatementContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def forLoop(self):
            return self.getTypedRuleContext(PlankalkulParser.ForLoopContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitForLoopStmt" ):
                return visitor.visitForLoopStmt(self)
            else:
                return visitor.visitChildren(self)



    def statement(self):

        localctx = PlankalkulParser.StatementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_statement)
        try:
            self.state = 146
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,10,self._ctx)
            if la_ == 1:
                localctx = PlankalkulParser.AssignStmtContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 136
                self.expr()
                self.state = 137
                self.match(PlankalkulParser.T__8)
                self.state = 138
                self.varRef()
                pass

            elif la_ == 2:
                localctx = PlankalkulParser.GuardStmtContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 140
                self.expr()
                self.state = 141
                self.match(PlankalkulParser.T__6)
                self.state = 142
                self.guardBody()
                pass

            elif la_ == 3:
                localctx = PlankalkulParser.WLoopStmtContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 144
                self.wLoop()
                pass

            elif la_ == 4:
                localctx = PlankalkulParser.ForLoopStmtContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 145
                self.forLoop()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class GuardBodyContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PlankalkulParser.RULE_guardBody

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class GuardSingleContext(GuardBodyContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.GuardBodyContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def statement(self):
            return self.getTypedRuleContext(PlankalkulParser.StatementContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGuardSingle" ):
                return visitor.visitGuardSingle(self)
            else:
                return visitor.visitChildren(self)


    class GuardBlockContext(GuardBodyContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.GuardBodyContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def statementList(self):
            return self.getTypedRuleContext(PlankalkulParser.StatementListContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitGuardBlock" ):
                return visitor.visitGuardBlock(self)
            else:
                return visitor.visitChildren(self)



    def guardBody(self):

        localctx = PlankalkulParser.GuardBodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_guardBody)
        try:
            self.state = 153
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [10]:
                localctx = PlankalkulParser.GuardBlockContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 148
                self.match(PlankalkulParser.T__9)
                self.state = 149
                self.statementList()
                self.state = 150
                self.match(PlankalkulParser.T__10)
                pass
            elif token in [4, 8, 12, 21, 25, 26, 30, 31, 32, 33, 35, 38, 39, 40]:
                localctx = PlankalkulParser.GuardSingleContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 152
                self.statement()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class WLoopContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def statement(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.StatementContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.StatementContext,i)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_wLoop

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitWLoop" ):
                return visitor.visitWLoop(self)
            else:
                return visitor.visitChildren(self)




    def wLoop(self):

        localctx = PlankalkulParser.WLoopContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_wLoop)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 155
            self.match(PlankalkulParser.T__11)
            self.state = 156
            self.match(PlankalkulParser.T__9)
            self.state = 158 
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while True:
                self.state = 157
                self.statement()
                self.state = 160 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if not ((((_la) & ~0x3f) == 0 and ((1 << _la) & 1974713979152) != 0)):
                    break

            self.state = 162
            self.match(PlankalkulParser.T__10)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ForLoopContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def FOR(self):
            return self.getToken(PlankalkulParser.FOR, 0)

        def varRef(self):
            return self.getTypedRuleContext(PlankalkulParser.VarRefContext,0)


        def FROM(self):
            return self.getToken(PlankalkulParser.FROM, 0)

        def expr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.ExprContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.ExprContext,i)


        def TO(self):
            return self.getToken(PlankalkulParser.TO, 0)

        def statementList(self):
            return self.getTypedRuleContext(PlankalkulParser.StatementListContext,0)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_forLoop

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitForLoop" ):
                return visitor.visitForLoop(self)
            else:
                return visitor.visitChildren(self)




    def forLoop(self):

        localctx = PlankalkulParser.ForLoopContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_forLoop)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 164
            self.match(PlankalkulParser.FOR)
            self.state = 165
            self.varRef()
            self.state = 166
            self.match(PlankalkulParser.FROM)
            self.state = 167
            self.expr()
            self.state = 168
            self.match(PlankalkulParser.TO)
            self.state = 169
            self.expr()
            self.state = 170
            self.match(PlankalkulParser.T__9)
            self.state = 171
            self.statementList()
            self.state = 172
            self.match(PlankalkulParser.T__10)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def orExpr(self):
            return self.getTypedRuleContext(PlankalkulParser.OrExprContext,0)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_expr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExpr" ):
                return visitor.visitExpr(self)
            else:
                return visitor.visitChildren(self)




    def expr(self):

        localctx = PlankalkulParser.ExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_expr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 174
            self.orExpr()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class OrExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def andExpr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.AndExprContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.AndExprContext,i)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_orExpr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOrExpr" ):
                return visitor.visitOrExpr(self)
            else:
                return visitor.visitChildren(self)




    def orExpr(self):

        localctx = PlankalkulParser.OrExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_orExpr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 176
            self.andExpr()
            self.state = 181
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==13:
                self.state = 177
                self.match(PlankalkulParser.T__12)
                self.state = 178
                self.andExpr()
                self.state = 183
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AndExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def compExpr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.CompExprContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.CompExprContext,i)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_andExpr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAndExpr" ):
                return visitor.visitAndExpr(self)
            else:
                return visitor.visitChildren(self)




    def andExpr(self):

        localctx = PlankalkulParser.AndExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_andExpr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 184
            self.compExpr()
            self.state = 189
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==14:
                self.state = 185
                self.match(PlankalkulParser.T__13)
                self.state = 186
                self.compExpr()
                self.state = 191
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CompExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def addExpr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.AddExprContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.AddExprContext,i)


        def compOp(self):
            return self.getTypedRuleContext(PlankalkulParser.CompOpContext,0)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_compExpr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCompExpr" ):
                return visitor.visitCompExpr(self)
            else:
                return visitor.visitChildren(self)




    def compExpr(self):

        localctx = PlankalkulParser.CompExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_compExpr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 192
            self.addExpr()
            self.state = 196
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if (((_la) & ~0x3f) == 0 and ((1 << _la) & 1015810) != 0):
                self.state = 193
                self.compOp()
                self.state = 194
                self.addExpr()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CompOpContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PlankalkulParser.RULE_compOp

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCompOp" ):
                return visitor.visitCompOp(self)
            else:
                return visitor.visitChildren(self)




    def compOp(self):

        localctx = PlankalkulParser.CompOpContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_compOp)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 198
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 1015810) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AddExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def mulExpr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.MulExprContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.MulExprContext,i)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_addExpr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAddExpr" ):
                return visitor.visitAddExpr(self)
            else:
                return visitor.visitChildren(self)




    def addExpr(self):

        localctx = PlankalkulParser.AddExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_addExpr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 200
            self.mulExpr()
            self.state = 205
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==20 or _la==21:
                self.state = 201
                _la = self._input.LA(1)
                if not(_la==20 or _la==21):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 202
                self.mulExpr()
                self.state = 207
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class MulExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def powExpr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.PowExprContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.PowExprContext,i)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_mulExpr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMulExpr" ):
                return visitor.visitMulExpr(self)
            else:
                return visitor.visitChildren(self)




    def mulExpr(self):

        localctx = PlankalkulParser.MulExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_mulExpr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 208
            self.powExpr()
            self.state = 213
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==22 or _la==23:
                self.state = 209
                _la = self._input.LA(1)
                if not(_la==22 or _la==23):
                    self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 210
                self.powExpr()
                self.state = 215
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PowExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def unaryExpr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.UnaryExprContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.UnaryExprContext,i)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_powExpr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPowExpr" ):
                return visitor.visitPowExpr(self)
            else:
                return visitor.visitChildren(self)




    def powExpr(self):

        localctx = PlankalkulParser.PowExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_powExpr)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 216
            self.unaryExpr()
            self.state = 219
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==24:
                self.state = 217
                self.match(PlankalkulParser.T__23)
                self.state = 218
                self.unaryExpr()


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class UnaryExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PlankalkulParser.RULE_unaryExpr

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class NotExprContext(UnaryExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.UnaryExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def unaryExpr(self):
            return self.getTypedRuleContext(PlankalkulParser.UnaryExprContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNotExpr" ):
                return visitor.visitNotExpr(self)
            else:
                return visitor.visitChildren(self)


    class NegExprContext(UnaryExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.UnaryExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def unaryExpr(self):
            return self.getTypedRuleContext(PlankalkulParser.UnaryExprContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNegExpr" ):
                return visitor.visitNegExpr(self)
            else:
                return visitor.visitChildren(self)


    class AtomExprContext(UnaryExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.UnaryExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def atom(self):
            return self.getTypedRuleContext(PlankalkulParser.AtomContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAtomExpr" ):
                return visitor.visitAtomExpr(self)
            else:
                return visitor.visitChildren(self)



    def unaryExpr(self):

        localctx = PlankalkulParser.UnaryExprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_unaryExpr)
        try:
            self.state = 226
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [25]:
                localctx = PlankalkulParser.NotExprContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 221
                self.match(PlankalkulParser.T__24)
                self.state = 222
                self.unaryExpr()
                pass
            elif token in [21]:
                localctx = PlankalkulParser.NegExprContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 223
                self.match(PlankalkulParser.T__20)
                self.state = 224
                self.unaryExpr()
                pass
            elif token in [4, 8, 26, 30, 31, 32, 33, 38, 39, 40]:
                localctx = PlankalkulParser.AtomExprContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 225
                self.atom()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AtomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PlankalkulParser.RULE_atom

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class VarAtomContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def varRef(self):
            return self.getTypedRuleContext(PlankalkulParser.VarRefContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVarAtom" ):
                return visitor.visitVarAtom(self)
            else:
                return visitor.visitChildren(self)


    class IntLiteralContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INT(self):
            return self.getToken(PlankalkulParser.INT, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIntLiteral" ):
                return visitor.visitIntLiteral(self)
            else:
                return visitor.visitChildren(self)


    class FuncCallAtomContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def funcCall(self):
            return self.getTypedRuleContext(PlankalkulParser.FuncCallContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFuncCallAtom" ):
                return visitor.visitFuncCallAtom(self)
            else:
                return visitor.visitChildren(self)


    class TrueLiteralContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTrueLiteral" ):
                return visitor.visitTrueLiteral(self)
            else:
                return visitor.visitChildren(self)


    class BitseqLiteralContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def BITSEQ(self):
            return self.getToken(PlankalkulParser.BITSEQ, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBitseqLiteral" ):
                return visitor.visitBitseqLiteral(self)
            else:
                return visitor.visitChildren(self)


    class ParenExprContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self):
            return self.getTypedRuleContext(PlankalkulParser.ExprContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParenExpr" ):
                return visitor.visitParenExpr(self)
            else:
                return visitor.visitChildren(self)



    def atom(self):

        localctx = PlankalkulParser.AtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_atom)
        try:
            self.state = 237
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [38]:
                localctx = PlankalkulParser.IntLiteralContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 228
                self.match(PlankalkulParser.INT)
                pass
            elif token in [26]:
                localctx = PlankalkulParser.TrueLiteralContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 229
                self.match(PlankalkulParser.T__25)
                pass
            elif token in [40]:
                localctx = PlankalkulParser.BitseqLiteralContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 230
                self.match(PlankalkulParser.BITSEQ)
                pass
            elif token in [8, 39]:
                localctx = PlankalkulParser.FuncCallAtomContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 231
                self.funcCall()
                pass
            elif token in [30, 31, 32, 33]:
                localctx = PlankalkulParser.VarAtomContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 232
                self.varRef()
                pass
            elif token in [4]:
                localctx = PlankalkulParser.ParenExprContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 233
                self.match(PlankalkulParser.T__3)
                self.state = 234
                self.expr()
                self.state = 235
                self.match(PlankalkulParser.T__5)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FuncCallContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def argList(self):
            return self.getTypedRuleContext(PlankalkulParser.ArgListContext,0)


        def ID(self):
            return self.getToken(PlankalkulParser.ID, 0)

        def programId(self):
            return self.getTypedRuleContext(PlankalkulParser.ProgramIdContext,0)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_funcCall

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFuncCall" ):
                return visitor.visitFuncCall(self)
            else:
                return visitor.visitChildren(self)




    def funcCall(self):

        localctx = PlankalkulParser.FuncCallContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_funcCall)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 241
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [39]:
                self.state = 239
                self.match(PlankalkulParser.ID)
                pass
            elif token in [8]:
                self.state = 240
                self.programId()
                pass
            else:
                raise NoViableAltException(self)

            self.state = 243
            self.match(PlankalkulParser.T__3)
            self.state = 244
            self.argList()
            self.state = 245
            self.match(PlankalkulParser.T__5)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ArgListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def expr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.ExprContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.ExprContext,i)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_argList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitArgList" ):
                return visitor.visitArgList(self)
            else:
                return visitor.visitChildren(self)




    def argList(self):

        localctx = PlankalkulParser.ArgListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_argList)
        self._la = 0 # Token type
        try:
            self.state = 256
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [4, 8, 21, 25, 26, 30, 31, 32, 33, 38, 39, 40]:
                self.enterOuterAlt(localctx, 1)
                self.state = 247
                self.expr()
                self.state = 252
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==5:
                    self.state = 248
                    self.match(PlankalkulParser.T__4)
                    self.state = 249
                    self.expr()
                    self.state = 254
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                pass
            elif token in [6]:
                self.enterOuterAlt(localctx, 2)

                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class VarRefContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def varKind(self):
            return self.getTypedRuleContext(PlankalkulParser.VarKindContext,0)


        def INT(self):
            return self.getToken(PlankalkulParser.INT, 0)

        def component(self):
            return self.getTypedRuleContext(PlankalkulParser.ComponentContext,0)


        def typeInline(self):
            return self.getTypedRuleContext(PlankalkulParser.TypeInlineContext,0)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_varRef

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVarRef" ):
                return visitor.visitVarRef(self)
            else:
                return visitor.visitChildren(self)




    def varRef(self):

        localctx = PlankalkulParser.VarRefContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_varRef)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 258
            self.varKind()
            self.state = 259
            self.match(PlankalkulParser.INT)
            self.state = 269
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==27:
                self.state = 260
                self.match(PlankalkulParser.T__26)
                self.state = 262
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (((_la) & ~0x3f) == 0 and ((1 << _la) & 290984034320) != 0):
                    self.state = 261
                    self.component()


                self.state = 266
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la==28:
                    self.state = 264
                    self.match(PlankalkulParser.T__27)
                    self.state = 265
                    self.typeInline()


                self.state = 268
                self.match(PlankalkulParser.T__28)


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class VarKindContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PlankalkulParser.RULE_varKind

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVarKind" ):
                return visitor.visitVarKind(self)
            else:
                return visitor.visitChildren(self)




    def varKind(self):

        localctx = PlankalkulParser.VarKindContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_varKind)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 271
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 16106127360) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ComponentContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def componentElem(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.ComponentElemContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.ComponentElemContext,i)


        def getRuleIndex(self):
            return PlankalkulParser.RULE_component

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitComponent" ):
                return visitor.visitComponent(self)
            else:
                return visitor.visitChildren(self)




    def component(self):

        localctx = PlankalkulParser.ComponentContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_component)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 273
            self.componentElem()
            self.state = 278
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==2:
                self.state = 274
                self.match(PlankalkulParser.T__1)
                self.state = 275
                self.componentElem()
                self.state = 280
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ComponentElemContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PlankalkulParser.RULE_componentElem

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class StaticComponentElemContext(ComponentElemContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.ComponentElemContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INT(self):
            return self.getToken(PlankalkulParser.INT, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStaticComponentElem" ):
                return visitor.visitStaticComponentElem(self)
            else:
                return visitor.visitChildren(self)


    class ExprComponentElemContext(ComponentElemContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.ComponentElemContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self):
            return self.getTypedRuleContext(PlankalkulParser.ExprContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExprComponentElem" ):
                return visitor.visitExprComponentElem(self)
            else:
                return visitor.visitChildren(self)


    class VarComponentElemContext(ComponentElemContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.ComponentElemContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def varKind(self):
            return self.getTypedRuleContext(PlankalkulParser.VarKindContext,0)

        def INT(self):
            return self.getToken(PlankalkulParser.INT, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitVarComponentElem" ):
                return visitor.visitVarComponentElem(self)
            else:
                return visitor.visitChildren(self)



    def componentElem(self):

        localctx = PlankalkulParser.ComponentElemContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_componentElem)
        try:
            self.state = 289
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [38]:
                localctx = PlankalkulParser.StaticComponentElemContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 281
                self.match(PlankalkulParser.INT)
                pass
            elif token in [30, 31, 32, 33]:
                localctx = PlankalkulParser.VarComponentElemContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 282
                self.varKind()
                self.state = 283
                self.match(PlankalkulParser.INT)
                pass
            elif token in [4]:
                localctx = PlankalkulParser.ExprComponentElemContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 285
                self.match(PlankalkulParser.T__3)
                self.state = 286
                self.expr()
                self.state = 287
                self.match(PlankalkulParser.T__5)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TypeInlineContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return PlankalkulParser.RULE_typeInline

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class InlineBitTypeContext(TypeInlineContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.TypeInlineContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INT(self):
            return self.getToken(PlankalkulParser.INT, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitInlineBitType" ):
                return visitor.visitInlineBitType(self)
            else:
                return visitor.visitChildren(self)


    class InlineUserTypeContext(TypeInlineContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.TypeInlineContext
            super().__init__(parser)
            self.name = None # Token
            self.copyFrom(ctx)

        def ID(self):
            return self.getToken(PlankalkulParser.ID, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitInlineUserType" ):
                return visitor.visitInlineUserType(self)
            else:
                return visitor.visitChildren(self)


    class InlineSequenceContext(TypeInlineContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.TypeInlineContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INT(self, i:int=None):
            if i is None:
                return self.getTokens(PlankalkulParser.INT)
            else:
                return self.getToken(PlankalkulParser.INT, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitInlineSequence" ):
                return visitor.visitInlineSequence(self)
            else:
                return visitor.visitChildren(self)


    class InlineArrayContext(TypeInlineContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.TypeInlineContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def INT(self):
            return self.getToken(PlankalkulParser.INT, 0)
        def typeInline(self):
            return self.getTypedRuleContext(PlankalkulParser.TypeInlineContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitInlineArray" ):
                return visitor.visitInlineArray(self)
            else:
                return visitor.visitChildren(self)


    class InlineRecordContext(TypeInlineContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a PlankalkulParser.TypeInlineContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def typeInline(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(PlankalkulParser.TypeInlineContext)
            else:
                return self.getTypedRuleContext(PlankalkulParser.TypeInlineContext,i)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitInlineRecord" ):
                return visitor.visitInlineRecord(self)
            else:
                return visitor.visitChildren(self)



    def typeInline(self):

        localctx = PlankalkulParser.TypeInlineContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_typeInline)
        self._la = 0 # Token type
        try:
            self.state = 309
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,30,self._ctx)
            if la_ == 1:
                localctx = PlankalkulParser.InlineSequenceContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 291
                self.match(PlankalkulParser.INT)
                self.state = 292
                self.match(PlankalkulParser.T__1)
                self.state = 293
                self.match(PlankalkulParser.INT)
                pass

            elif la_ == 2:
                localctx = PlankalkulParser.InlineArrayContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 294
                self.match(PlankalkulParser.INT)
                self.state = 295
                self.match(PlankalkulParser.T__2)
                self.state = 296
                self.typeInline()
                pass

            elif la_ == 3:
                localctx = PlankalkulParser.InlineRecordContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 297
                self.match(PlankalkulParser.T__3)
                self.state = 298
                self.typeInline()
                self.state = 301 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 299
                    self.match(PlankalkulParser.T__4)
                    self.state = 300
                    self.typeInline()
                    self.state = 303 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==5):
                        break

                self.state = 305
                self.match(PlankalkulParser.T__5)
                pass

            elif la_ == 4:
                localctx = PlankalkulParser.InlineUserTypeContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 307
                localctx.name = self.match(PlankalkulParser.ID)
                pass

            elif la_ == 5:
                localctx = PlankalkulParser.InlineBitTypeContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 308
                self.match(PlankalkulParser.INT)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





