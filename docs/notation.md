# Plankalkül Linear Text Notation

> This document defines the linear text notation used as the input format for the
> plankalkulsharp compiler. The notation uses `=>` for assignment (Ergibt-Zeichen)
> and `->` for conditional execution (Bedingung).

## 1. Design Principles

1. **One-dimensional**: All information from Zuse's 2D rows (V/K/S) is inlined.
2. **Unambiguous**: Parseable by an ANTLR4 LL(\*) grammar.
3. **Readable**: Close enough to Zuse's original that programs are recognizable.
4. **Complete**: Can express every Plankalkül construct.

## 2. Type Annotations

Type annotations appear in brackets `[ component : type ]` after variable references.
Component access (if any) appears before the colon, type after:

| Annotation    | Meaning                         | Zuse's notation |
| ------------- | ------------------------------- | --------------- |
| `[:0]`        | Single bit (S0)                 | S0              |
| `[:1.n]`      | Bit sequence of length n (S1·n) | S1·n            |
| `[:8.0]`      | 8-bit integer (8 × S0)          | 8 × S0          |
| `[:m.n.0]`    | m × n bit matrix                | m × n × S0      |
| `[: A1]`      | User-defined type A1            | A1              |
| `[0 : A1]`    | Field 0 of user-defined type A1 | A1, K=0         |
| `[V0.1 : A3]` | Dynamic index + nested field    | K=(V0, 1)       |

General rule: colons separate dimensions, the innermost is the element type.

### Full Type Syntax

```
type       ::= prim_type | array_type | record_type | user_type
prim_type  ::= '0'                          (* S0: single bit *)
array_type ::= INT '.' type                  (* n × T *)
record_type::= '(' type (',' type)+ ')'      (* tuple *)
user_type  ::= 'A' INT                       (* user-defined *)
```

## 3. Variables

### 3.1 Basic Variable Reference

```
<kind><number>             e.g. V0, Z1, R0, C3
```

### 3.2 Variable with Type Annotation

```
<kind><number>[:<type>]    e.g. V0[:8.0], Z1[:1.4], R0[:(A1)]
```

Type annotations are optional after the first occurrence (type is inferred from
the declaration assignment), but can always be provided for clarity.

### 3.3 Component Access

Component access lives **inside** the brackets, before the colon:

```
<kind><number>[<component> : <type>]
```

Static (literal index) components separated by dots:

```
Z0[0 : A1]               first component of Z0 (type A1)
Z0[0.3 : A3]             bit 3 of first component
Z0[1 : A1]               second component
```

Dynamic (variable) index in the component chain:

```
Z0[V0 : 10.8.0]          V0-th element of array
Z0[V0.1 : A3]            field 1 of V0-th element
Z0[Z1.0 : A2]            field 0 of Z1-th element
```

Expression index (arbitrary expression in parentheses):

```
Z0[(V0 + 1) : 10.8.0]   element at V0+1
```

## 4. Type Definitions

User-defined types are declared at the top level before programs:

```
A1 = S1.3
A2 = 2 x A1
A3 = S1.4
A4 = (A2, A3)
A5 = 64 x A3
A10 = (A5, S0, S1.4, A2)
```

Type definition syntax:

```
'A' INT '=' type_expr

type_expr  ::= 'S0'                          (* bit *)
             | 'S1' '.' INT                   (* bit sequence *)
             | INT 'x' type_expr              (* array *)
             | '(' type_expr (',' type_expr)+ ')'  (* record *)
             | 'A' INT                        (* reference to user type *)
```

## 5. Program Definitions

### 5.1 Basic Form

```
P<number> <name> (<params>) -> <result>
  <body>
END
```

### 5.2 Parameters and Result

Parameters are comma-separated V-variables with type annotations:

```
P1 max (V0[:8.0], V1[:8.0]) -> R0[:8.0]
```

Multiple return values:

```
P2 divmod (V0[:8.0], V1[:8.0]) -> (R0[:8.0], R1[:8.0])
```

### 5.3 Subprograms

```
P5.1 helper (V0[:0]) -> R0[:0]
  ...
END
```

## 6. Statements

### 6.1 Assignment (Ergibt-Zeichen)

The `=>` operator (Ergibt-Zeichen) is used for assignment:

```
<expr> => <target>
```

Examples:

```
V0[:8.0] => Z1[:8.0]               simple copy
V0[:8.0] + V1[:8.0] => Z2[:8.0]    arithmetic result
0 => Z0[:8.0]                       assign literal
```

### 6.2 Guarded Conditional (Bedingung)

The `->` operator is used exclusively for conditional execution:

Single statement:

```
(Z1[:8.0] < V1[:8.0]) -> V1[:8.0] => Z1[:8.0]
```

Block form:

```
(Z0[:0] = L) -> {
  V0[:8.0] => Z1[:8.0]
  V1[:8.0] => Z2[:8.0]
}
```

### 6.3 W-Loop

```
W {
  (Z0[:8.0] < 10) -> {
    Z0[:8.0] + 1 => Z0[:8.0]
  }
}
```

Multiple guards:

```
W {
  (guard1) -> { body1 }
  (guard2) -> { body2 }
}
```

### 6.4 For-Loop

```
FOR Z0[:8.0] FROM 0 TO 63 {
  <body>
}
```

## 7. Expressions

### 7.1 Literals

| Syntax   | Meaning                       |
| -------- | ----------------------------- |
| `0`, `1` | Bit literals (S0)             |
| `L`      | True (S0), synonym for `1`    |
| `42`     | Integer literal               |
| `L00L`   | Bit sequence literal (4 bits) |

### 7.2 Operators

Arithmetic: `+`, `-`, `*`, `/`, `**`
Boolean: `&`, `|`, `~`
Comparison: `=`, `!=`, `<`, `>`, `<=`, `>=`
Grouping: `(`, `)`

### 7.3 Function Call (in expression position)

```
max(V0[:8.0], V1[:8.0])
P2(V0[:8.0], V1[:8.0])
```

## 8. Comments

```
// single-line comment
/* multi-line
   comment */
```

(Extension for usability — not in Zuse's original.)

## 9. Complete Example

```
// Type definitions for chess
A1 = S1.3
A2 = 2 x A1
A3 = S1.4

// Maximum of two 8-bit integers
P1 max (V0[:8.0], V1[:8.0]) -> R0[:8.0]
  V0[:8.0] => Z1[:8.0]
  (Z1[:8.0] < V1[:8.0]) -> V1[:8.0] => Z1[:8.0]
  Z1[:8.0] => R0[:8.0]
END

// Maximum of three 8-bit integers
P2 max3 (V0[:8.0], V1[:8.0], V2[:8.0]) -> R0[:8.0]
  max(V0[:8.0], V1[:8.0]) => Z1[:8.0]
  max(Z1[:8.0], V2[:8.0]) => R0[:8.0]
END
```

## 10. Mapping from 2D to Linear

| 2D Row              | Linear Equivalent                      |
| ------------------- | -------------------------------------- |
| Expression row      | Expression text                        |
| V (variable index)  | Encodes as `<kind><number>`            |
| K (component index) | Inside brackets before `:` (`[K : S]`) |
| S (structure index) | Inside brackets after `:` (`[K : S]`)  |
