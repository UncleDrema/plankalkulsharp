program
    : (typeDef | programDef)* EOF
    ;

typeDef
    : name=ID '=' typeExpr
    ;

typeExpr
    : INT
    | INT '.' INT
    | INT 'x' typeExpr
    | '(' typeExpr (',' typeExpr)+ ')'
    | name=ID
    ;

programDef
    : programId name=ID? '(' paramList ')' '->' resultSpec
      statementList
      'END'
    ;

statement
    : expr '=>' varRef
    | expr '->' guardBody
    | wLoop
    | forLoop
    ;
