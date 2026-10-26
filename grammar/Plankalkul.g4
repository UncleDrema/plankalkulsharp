// ANTLR4 grammar for the implemented PlankalkulSharp text notation.
//
// Syntax:
//     expr => varRef          assignment (Ergibt-Zeichen)
//     expr -> guardBody       guard / conditional (Bedingung)
//
// The grammar is the current syntax source of truth. Historical descriptions
// in docs/ may cover notation or language features that the compiler does not
// implement. Keep generated frontend files in sync with this file via
// scripts/generate_parser.py (ANTLR 4.13.2).
//
// Types use lowercase aliases and numeric forms such as 0 and 8.0.
// Uppercase single letters (V, Z, C, R, P, W, L) are
// implicit tokens; IDs start with lowercase; BITSEQ has at least two
// characters and contains at least one L.

grammar Plankalkul;

// ============================================================
// Parser Rules
// ============================================================

program
    : (typeDef | programDef)* EOF
    ;

// --- Type Definitions (top-level) ---

typeDef
    : name=ID '=' typeExpr
    ;

typeExpr
    : INT                                        # bitType
    | INT '.' INT                                # bitSeqType
    | (INT | '*') 'x' typeExpr                           # arrayType
    | '(' typeExpr (',' typeExpr)+ ')'           # recordType
    | name=ID                                    # userType
    | '@' name=ID                                # refType
    ;

// --- Program Definitions ---

programDef
    : programId name=ID? '(' paramList ')' '->' resultSpec
      statementList
      'END'
    ;

programId
    : 'P' INT
    ;

paramList
    : varRef (',' varRef)*
    |
    ;

resultSpec
    : varRef                                     # singleResult
    | '(' varRef (',' varRef)+ ')'               # multiResult
    ;

// --- Statements ---
// Assignment (=>) and guard/conditional (->) syntax:
//   expr => varRef                    = assignment
//   expr -> { block }                 = guard with block body
//   expr -> expr => varRef            = conditional assignment
//   expr -> expr -> { block }         = nested guard

statementList
    : statement*
    ;

statement
    : expr '=>' varRef                           # assignStmt
    | expr '=>' '@'                              # freeStmt
    | expr '->' guardBody                        # guardStmt
    | wLoop                                      # wLoopStmt
    | indexedLoop                                # indexedLoopStmt
    | (expr '=>')? FIN                         # finStmt
    ;

guardBody
    : '{' statementList '}'                      # guardBlock
    | statement                                  # guardSingle
    ;

wLoop
    : 'W' '{' statement+ '}'
    ;

indexedLoop
    : INDEXED_W INDEX '(' expr (',' expr)? ')' '{' statementList '}'
    ;

// --- Expressions (precedence climbing, low to high) ---

expr
    : orExpr
    ;

orExpr
    : andExpr ('|' andExpr)*
    ;

andExpr
    : compExpr ('&' compExpr)*
    ;

compExpr
    : addExpr (compOp addExpr)?
    ;

compOp
    : '=' | '!=' | '<' | '>' | '<=' | '>='
    ;

addExpr
    : mulExpr (('+' | '-') mulExpr)*
    ;

mulExpr
    : powExpr (('*' | '/') powExpr)*
    ;

powExpr
    : unaryExpr ('**' unaryExpr)?
    ;

unaryExpr
    : '~' unaryExpr                              # notExpr
    | '-' unaryExpr                              # negExpr
    | atom                                       # atomExpr
    ;

atom
    : INT                                        # intLiteral
    | 'L'                                        # trueLiteral
    | BITSEQ                                     # bitseqLiteral
    | 'NIL'                                      # nilLiteral
    | '@' name=ID                                # allocateAtom
    | funcCall                                   # funcCallAtom
    | INDEX                                      # indexAtom
    | varRef                                     # varAtom
    | '(' expr ')'                               # parenExpr
    | '[' argList ']'                            # listLiteral
    | '(' expr (',' expr)+ ')'                   # recordLiteral
    ;

// --- Function Call ---
// Must come before varRef in atom alternatives — funcCall starts with
// ID or programId ('P'), neither of which matches varKind (V/Z/C/R).

funcCall
    : (ID | LIST_OP | programId) '(' argList ')'
    ;

argList
    : expr (',' expr)*
    |
    ;

// --- Variable Reference ---
// Berlin-style syntax: V0[component : type]
//   V0[: 8.0]       — no component, just type
//   V0[0 : A1]      — static component + type
//   V0[0.1 : A3]    — component chain + type
//   V0[Z1.0 : A2]   — dynamic component chain + type

varRef
    : varKind INT ('[' component? (':' typeInline)? ']')?
    ;

varKind
    : 'V' | 'Z' | 'C' | 'R'
    ;

component
    : componentElem ('.' componentElem)*
    ;

componentElem
    : INT                                        # staticComponentElem
    | varKind INT                                # varComponentElem
    | INDEX                                      # indexComponentElem
    | '(' expr ')'                               # exprComponentElem
    | '@'                                        # dereferenceComponentElem
    ;

typeInline
    : INT '.' INT                                # inlineSequence
    | (INT | '*') 'x' typeInline                         # inlineArray
    | '(' typeInline (',' typeInline)+ ')'       # inlineRecord
    | name=ID                                    # inlineUserType
    | INT                                        # inlineBitType
    | '@' name=ID                                # inlineRefType
    ;


// ============================================================
// Lexer Rules
// ============================================================

// Keywords (all uppercase — cannot conflict with ID which starts lowercase)
LIST_OP : 'N' | 'Lz' | 'Qz' | 'Sp' | 'Nr';
END   : 'END' ;
INDEXED_W : 'W' [1-5] ;
INDEX : 'i' [0-9]+ ;
FIN : 'FIN' [0-9]* ;
NIL   : 'NIL' ;

// Identifiers and numbers
// INT must come before BITSEQ so pure digits match INT (longest match still applies)
INT   : [0-9]+ ;
ID    : [a-z_][a-zA-Z0-9_]* ;

// Bit sequence literal: ≥2 characters from {L, 0}, containing at least one L.
// First alt: starts with L (e.g. L0, LL, L00L)
// Second alt: starts with 0s then L (e.g. 0L, 00L, 0L0)
// Single 'L' does NOT match (requires 2+ chars) — matched by implicit 'L' token.
// Pure digits do NOT match (no 'L') — matched by INT.
BITSEQ : 'L' [L0]+ | '0'+ 'L' [L0]* ;

// Comments
LINE_COMMENT  : '//' ~[\r\n]* -> skip ;
BLOCK_COMMENT : '/*' .*? '*/' -> skip ;

// Whitespace
WS : [ \t\r\n]+ -> skip ;
