# Грамматика

---------- Символы

digit ::= 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9

digits ::= digit {digit}\*

lower ::= a | b | ... | z

upper ::= A | B | ... | Z

letter ::= lower | upper | \_

name ::= (lower | \_) {letter | digit}\*

integer ::= digits

bitseq ::= L (L | 0) {L | 0} | 0 {0} L {L | 0}

program-id ::= P digits [ . digits ]

type-id ::= A digits

---------- Типы данных

bit-type ::= S0

seq-type ::= S1 . digits

array-type ::= digits x type-expr

tuple-type ::= (type-expr, type-expr {, type-expr}\*)

type-expr ::= bit-type | seq-type | array-type | tuple-type | type-id

inline-bit-type ::= 0

inline-array-type ::= digits . inline-type

inline-tuple-type ::= (inline-type, inline-type {, inline-type}\*)

inline-type ::= inline-bit-type | inline-array-type | inline-tuple-type | type-id

---------- Переменные

var-kind ::= V | Z | C | R

component-atom ::= digits | var-kind digits | (expr)

component ::= component-atom { . component-atom }\*

var-ref ::= var-kind digits
| var-kind digits [: inline-type]
| var-kind digits [component : inline-type]

param-list ::= var-ref {, var-ref}\* | epsilon

result-spec ::= var-ref | (var-ref {, var-ref}\*)

---------- Вызов программы

arg-list ::= expr {, expr}\* | epsilon

call ::= (name | program-id) ( arg-list )

---------- Выражения

compare-op ::= = | != | < | > | <= | >=

atom ::= integer | L | bitseq | call | var-ref | (expr)

unary-expr ::= ~ unary-expr | - unary-expr | atom

pow-expr ::= unary-expr [ ** unary-expr ]

mul-expr ::= pow-expr { (\* | /) pow-expr }\*

add-expr ::= mul-expr { (+ | -) mul-expr }\*

cmp-expr ::= add-expr [ compare-op add-expr ]

and-expr ::= cmp-expr { & cmp-expr }\*

or-expr ::= and-expr { | and-expr }\*

expr ::= or-expr

---------- Присваивания и условные выражения

assignment ::= expr => var-ref

guard-body ::= statement | { statement-list }

guard ::= expr -> guard-body

---------- Циклы

w-loop ::= W { statement-list }

for-loop ::= FOR var-ref FROM expr TO expr { statement-list }

---------- Высказывания

statement ::= assignment | guard | w-loop | for-loop

statement-list ::= {statement}\*

---------- Определение типа

type-def ::= A digits = type-expr

---------- Программа

program-def ::= program-id [name] (param-list) -> result-spec statement-list END

source-file ::= {type-def | program-def}\*
