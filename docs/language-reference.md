# Plankalkül Language Reference

> Compiled from primary sources: Bauer & Wössner (CACM 1972), Zuse (1945/1972),
> Rojas et al. (FU Berlin 2000), Knuth & Pardo (Stanford 1976), Bruines (2010).

## 1. Overview

Plankalkül (German: "Plan Calculus") was designed by Konrad Zuse between 1942–1945
as the first high-level programming language. It is a procedural language with:

- Only local variables (no globals)
- No recursion
- Call by value only
- Composite types built from a single primitive (bit)
- Two-dimensional notation (original) or linear text notation (modern)

## 2. Data Types

### 2.1 Primitive Type

The only primitive is **S0** — a single bit (Boolean / Ja-Nein-Wert).

| Value | Meaning                 |
| ----- | ----------------------- |
| `0`   | false                   |
| `L`   | true (also written `1`) |

### 2.2 Composite Types

All composite types are built from S0 via two constructors:

#### Arrays (sequences)

- `n × T` — array of `n` elements of type `T`
- Example: `8 × S0` — a byte (8-bit sequence)
- Shorthand: `S1·n` ≡ `n × S0` (sequence of `n` bits)
- Multi-dimensional: `m × n × S0` — matrix of `m × n` bits

#### Records (tuples)

- `(T₁, T₂)` — pair of types T₁ and T₂
- `(T₁, T₂, T₃)` — triple (syntactic sugar for nested pairs)

### 2.3 User-Defined Types

Declared with identifier `A` followed by a number:

| ID    | Definition           | Meaning (from Zuse's chess examples)                   |
| ----- | -------------------- | ------------------------------------------------------ |
| `A1`  | `S1·3`               | Board coordinate (3 bits, range 0-7)                   |
| `A2`  | `2 × A1`             | Square (row, column)                                   |
| `A3`  | `S1·4`               | Piece (4 bits)                                         |
| `A4`  | `(A2, A3)`           | Piece on a square                                      |
| `A5`  | `64 × A3`            | Full board (64 squares)                                |
| `A10` | `(A5, S0, S1·4, A2)` | Game state (board, side to move, castling, en passant) |

### 2.4 Type Structure

A type in Plankalkül has three components (Art):

1. **Struktur** — structural definition (as above)
2. **Typ** — pragmatic meaning (informal, for documentation)
3. **Beschränkung** — restriction on allowed values (optional constraint)

## 3. Variables

### 3.1 Variable Kinds

| Kind         | Letter | German                 | Purpose             |
| ------------ | ------ | ---------------------- | ------------------- |
| Input        | `V`    | Eingabewerte/Variablen | Function parameters |
| Intermediate | `Z`    | Zwischenwerte          | Local temporaries   |
| Constant     | `C`    | Constanten             | Named constants     |
| Output       | `R`    | Resultatwerte          | Return values       |

### 3.2 Variable Naming

Variables are identified by kind letter + index number:

- `V0`, `V1`, `V2` — first, second, third input
- `Z0`, `Z1` — first, second intermediate
- `R0` — first (usually only) output
- `C0`, `C1` — constants

### 3.3 Component Access (Komponenten-Index)

Hierarchical access into composite types. Component indices are written
inside brackets before the colon, separated by dots:

Given `V0` of type `A10 = (A5, S0, S1·4, A2)`:

- `V0[0 : A10]` — board state (type A5)
- `V0[0.i : A10]` — piece on square `i` (type A3)
- `V0[0.i.j : A10]` — bit `j` of piece on square `i` (type S0)
- `V0[1 : A10]` — side to move (type S0)
- `V0[3 : A10]` — en passant square (type A2)

Variables can be used as indices (dynamic component access):

- `Z0[V0 : A3]` — element at index V0
- `Z0[Z1.0 : A2]` — field 0 of element at index Z1

### 3.4 Cross-Program Variable Access

Output of program P17 stored in R0 is accessible to other programs as `R17.0`
(reading this value triggers execution of P17 if not yet computed).

## 4. Programs and Subprograms

### 4.1 Program Declaration

Programs identified by `P` + number: `P1`, `P2`, `P13`.
Subprograms: `P5.7` (subprogram 7 of program 5).

A program declaration specifies:

- Input parameters (V variables with types)
- Output values (R variables with types)
- Body (sequence of statements)

### 4.2 Function Signatures

```
P<number> <name> (V0[:<type>], V1[:<type>], ...) -> R0[:<type>]
  <body>
END
```

### 4.3 Invocation

Programs are invoked by name, and their result is captured via assignment:

```
P2(V0[:8.0], V1[:8.0]) -> R0[:8.0]
```

## 5. Expressions

### 5.1 Arithmetic

| Operator | Meaning                             |
| -------- | ----------------------------------- |
| `+`      | Addition                            |
| `-`      | Subtraction                         |
| `*`      | Multiplication                      |
| `/`      | Division                            |
| `**`     | Exponentiation (in linear notation) |

Operands are bit-sequences interpreted as integers.

### 5.2 Boolean (on S0 values)

| Operator    | Meaning     | Zuse's notation |
| ----------- | ----------- | --------------- |
| `&` / `AND` | Conjunction | ∧               |
| `\|` / `OR` | Disjunction | ∨               |
| `~` / `NOT` | Negation    | ¬               |

### 5.3 Comparison

| Operator | Meaning              |
| -------- | -------------------- |
| `=`      | Equal                |
| `!=`     | Not equal (≠)        |
| `<`      | Less than            |
| `>`      | Greater than         |
| `<=`     | Less or equal (≤)    |
| `>=`     | Greater or equal (≥) |

Comparisons return S0 (boolean) values.

### 5.4 Operator Precedence (high to low)

1. `~` / `NOT` (unary negation)
2. `**` (exponentiation)
3. `*`, `/` (multiplicative)
4. `+`, `-` (additive)
5. `=`, `!=`, `<`, `>`, `<=`, `>=` (comparison)
6. `&` / `AND` (boolean and)
7. `|` / `OR` (boolean or)

## 6. Statements

### 6.1 Assignment (Ergibt-Zeichen)

Value flows left-to-right, result variable on the right. The `=>` operator
(Ergibt-Zeichen) is used for assignment:

```
<expression> => <variable>
```

The first assignment to a variable serves as its declaration.

Example:

```
V0[:8.0] + V1[:8.0] => Z0[:8.0]
```

### 6.2 Guarded Conditional

Execute a block only if a boolean condition is true.
The `->` operator is used exclusively for conditionals:

```
(<condition>) -> <statement>
```

Or with a block:

```
(<condition>) -> {
  <statements>
}
```

### 6.3 W-Loop (Iteration)

Repeat while at least one guard is true:

```
W {
  (<guard1>) -> <body1>
  (<guard2>) -> <body2>
}
```

The loop terminates when all guards evaluate to false.

### 6.4 For-Loop

Iterate a variable through a range:

```
FOR Z0[:8.0] = 0 TO 63 {
  <body>
}
```

(Linear notation extension; in Zuse's original, this was expressed via W-loop patterns.)

## 7. Program Structure

A complete Plankalkül source file consists of:

1. Optional type definitions (`A1 = ...`, `A2 = ...`)
2. One or more program definitions (`P1 ... END`, `P2 ... END`)

```
A1 = S1.3
A2 = 2 x A1
A3 = S1.4

P1 max (V0[:8.0], V1[:8.0]) -> R0[:8.0]
  V0[:8.0] => Z1[:8.0]
  (Z1[:8.0] < V1[:8.0]) -> V1[:8.0] => Z1[:8.0]
  Z1[:8.0] => R0[:8.0]
END
```

## 8. Key Semantic Rules

1. **No recursion**: A program cannot call itself directly or indirectly.
2. **Call by value**: Arguments are copied into V-variables of the callee.
3. **Local scope only**: Each program has its own V, Z, C, R namespace.
4. **First assignment = declaration**: Type is established on first `=>` to a variable.
5. **Type compatibility**: Assignment requires structural type match (same S0-based structure).
6. **Boolean as integer**: `FALSE = 0`, `TRUE = 1` (L).

## 9. Original 2D Notation (for reference)

In Zuse's original, each statement spans multiple rows:

| Row | Label                 | Content                      |
| --- | --------------------- | ---------------------------- |
| 1st | (none)                | Variable kind and expression |
| V   | V (Variablen-Index)   | Variable number              |
| K   | K (Komponenten-Index) | Component index              |
| S   | S (Struktur-Index)    | Type annotation              |

Example (2D form of `Z1 + 1 => Z1`):

```
     | Z + 1  =>  Z
  V  | 1          1
```

The linear notation used in this compiler replaces this 2D layout with inline
type annotations and dot/bracket notation for component access.
