// Plankalkül Grammar for ANTLR4
// Linear text notation for the plankalkulsharp compiler
//
// Syntax:
//     expr => varRef          assignment (Ergibt-Zeichen)
//     expr -> guardBody       guard / conditional (Bedingung)
// - Two type syntaxes: verbose (top-level defs) and compact (inline annotations).
// - Lexer: uppercase single letters (V,Z,C,R,P,A,W,L,S) are implicit tokens;
//   ID starts with lowercase only; BITSEQ requires ≥2 chars with at least one L.

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
    | INT 'x' typeExpr                           # arrayType
    | '(' typeExpr (',' typeExpr)+ ')'           # recordType
    | name=ID                                    # userType
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
    | expr '->' guardBody                        # guardStmt
    | wLoop                                      # wLoopStmt
    | forLoop                                    # forLoopStmt
    ;

guardBody
    : '{' statementList '}'                      # guardBlock
    | statement                                  # guardSingle
    ;

wLoop
    : 'W' '{' statement+ '}'
    ;

forLoop
    : 'FOR' varRef 'FROM' expr 'TO' expr '{' statementList '}'
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
    | funcCall                                   # funcCallAtom
    | varRef                                     # varAtom
    | '(' expr ')'                               # parenExpr
    ;

// --- Function Call ---
// Must come before varRef in atom alternatives — funcCall starts with
// ID or programId ('P'), neither of which matches varKind (V/Z/C/R).

funcCall
    : (ID | programId) '(' argList ')'
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
    | '(' expr ')'                               # exprComponentElem
    ;

typeInline
    : INT '.' INT                                # inlineSequence
    | INT 'x' typeInline                         # inlineArray
    | '(' typeInline (',' typeInline)+ ')'       # inlineRecord
    | name=ID                                    # inlineUserType
    | INT                                        # inlineBitType
    ;


// ============================================================
// Lexer Rules
// ============================================================

// Keywords (all uppercase — cannot conflict with ID which starts lowercase)
END   : 'END' ;
FOR   : 'FOR' ;
FROM  : 'FROM' ;
TO    : 'TO' ;

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
