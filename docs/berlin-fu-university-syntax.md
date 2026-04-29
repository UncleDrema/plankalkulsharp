Appendix A

Syntax of the Plankalkül

In the following we adopt the following conventions: a vertical bar ("|") separates optional syntactical elements, {expr}\* means that expr can be concatenated zero or more times, all identifiers with a defined rule can be expanded, any other characters are included literally in the expanded expressions.

--------- Symbols

digit ::= 0 | 1 | 2 | ... | 9

digits ::=digit {digit}\*

letter ::= a | b | ...| A | B | .... | Z

type-letter ::= a | b | ...h | j | ... | A | B | .... | Z \\ i.e. without the "i"

identifier ::= letter {letter | digit}\*

pos-constant ::= digits

neg-constant ::= - digits

constant ::= pos-constant | neg-constant

dot ::= "."

comma ::= ","

---------- Data types

simple-type ::= 0

tuple-type ::= (type, type {comma type}\*)

type ::= simple-type | tuple-type | digits dot type

var-type ::= type-letter dot type

all-type ::= type | var-type

---------- Variables

v-variable ::= V digits [component: type] | V digits[: all-type]

z-variable ::= Z digits [component: type] | Z digits[: all-type]

r-variable ::= R digits [component: type] | R digits[: all-type]

loop-var ::= "i" | "i" digits

loop-expr ::= loop-var | loop-var + pos-constant | loop-var – pos-constant}

type-var ::= type-letter

type-expr ::= type-var | type-var + pos-constant | type-var – pos-constant | type-expr + type-expr | type-expr – type-expr

component ::= digits | v-variable | z-variable | loop-expr | type-expr | component dot component

---------- Function call

zv-call-arg ::= v-variable | z-variable | call | constant | loop-var | type-var

call-all ::= R digits [:type] ( zv-call-arg {,zv-call-arg}\*)|

identifier [:type] ( zv-call-arg {,zv-call-arg}\*)

call-one ::= R digits [component : type] ( zv-call-arg {,zv-call-arg}\*) |

identifier [component : type] ( zv-call-arg {,zv-call-arg}\*)

call ::= call-all | call-one

---------- Arithmetical operations

arith-argument-left ::= v-variable | z-variable | constant | loop-var | type-var | call | arith-operation | (arith-operation)

arith-argument-right ::= v-variable | z-variable | pos-constant | (neg-constant) | loop-var | type-var | call | arith-operation | (arith-operation)

arith-argument ::= arith-argument-left | arith-argument-right

arith-operation ::= arith-argument-left {+ | - | ´ | / } arith-argument-right

---------- Logical operations

log-constant ::= + | -

condition ::= arith-argument = arith-argument |

arith-argument > arith-argument |

arith-argument < arith-argument |

zv-tuple = zv-tuple

pos-literal ::= v-variable | z-variable | log-constant | call | condition | (condition)

neg-literal ::= !v-variable | !z-variable | !call | ! (condition)

logic-argument ::= pos-literal | neg-literal | logic-operation | (logic-operation)

logic-binary ::= logic-argument { "|" | & | ~ | /~} logic-argument

logic-operation ::= pos-literal | neg-literal | logic-binary | !(logic-binary)

---------- Assignment

assignment0 ::= arith-argument => {z-variable | r-variable}

assignment1 ::= logic-argument => {z-variable | r-variable}

assignment2 ::= zv-tuple => zr-tuple

assignment3 ::= zv-tuple => {z-variable | r-variable}

zv-tuple ::= ( zv-arg, zv-arg {comma zv-arg}\*)

zv-arg ::= v-variable | z-variable | constant | call | loop-var | type-var | zv-tuple

zr-tuple ::= ( zr-arg, zr-arg {comma zr-arg}\*)

zr-arg ::= r-variable | z-variable | zr-tuple

assignment ::= assignment0 | assignment1 | assignment2 | assignment 3

---------- IF-THEN

if-then ::= logic-argument -> statement

---------- While

block ::= [ statement{; statement}*]

while ::= w block | w [digits] block | w1 (arith-arg) block | w1[digits] (arith-arg) block

---------- Statements

built-ins ::= FIN | FIN digits

statement ::= assignment | if-then | while | block | built-ins

---------- Programs

program ::= P digits randauszug {statement }\* END

---------- Randauszug

randauszug ::= identifier v-tuple => r-tuple

v-tuple ::= v-variable | (v-variable {, v-variable}\*)

r-tuple ::= r-variable | (r-variable {, r-variable}\*)

// The variables are numbered sequentially, starting with 0

// constant, indices, N(), have generic type
