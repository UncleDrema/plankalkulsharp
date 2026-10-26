"""Project the existing AST into aligned V/K/S columns, without generating IL.

This is a historical-layout view of our dialect, not a transcription of a
manuscript. Parentheses preserve the AST; modern constructs remain explicit.
"""
from dataclasses import asdict, dataclass, field

from plankalkulsharp.compiler import check, parse
from plankalkulsharp.plankalkul_ast import nodes as n
from plankalkulsharp.semantic import analyzer as t


SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


@dataclass
class Cell:
    text: str
    index: str = ""
    component: str = ""
    structure: str = ""
    extension: bool = False
    hint: str = ""
    component_cells: list["Cell"] = field(default_factory=list)


def structure(value) -> str:
    match value:
        case n.BitType() | t.ResolvedBit():
            return "0"
        case n.BitSeqType(length=length) | t.ResolvedBitSeq(length=length):
            return f"1.{length}"
        case n.ArrayType(size=size, element_type=element) | t.ResolvedArray(size=size, element=element):
            return f"{size if size is not None else chr(164)} × {structure(element)}"
        case n.RecordType(fields=fields) | t.ResolvedRecord(fields=fields):
            return "(" + ", ".join(map(structure, fields)) + ")"
        case n.RefType(target=target) | t.ResolvedRef(target=target):
            return "@" + target
        case n.UserType(name=name):
            return name
        case _:
            raise TypeError(f"Unsupported notation type: {type(value).__name__}")


class Projection:
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.scope = None
        self.rows = []

    @staticmethod
    def precedence(value):
        if isinstance(value, n.BinaryExpr):
            return {"|": 1, "&": 2, "=": 3, "!=": 3, "<": 3, ">": 3,
                    "<=": 3, ">=": 3, "+": 4, "-": 4, "*": 5, "/": 5, "**": 6}[str(value.op)]
        return 7 if isinstance(value, n.UnaryExpr) else 8

    def child(self, value, parent, right=False):
        # Preserve the AST, including right-associated subtraction/division and
        # the grammar's non-chainable comparisons/powers. Unary binds above **.
        level, outer = self.precedence(value), self.precedence(parent)
        wrap = level < outer or (level == outer and (right or outer in (3, 6)))
        cells = self.expr(value)
        return [Cell("(")] + cells + [Cell(")")] if wrap else cells

    def expr(self, value) -> list[Cell]:
        match value:
            case n.VarRef():
                symbol = self.scope.lookup(value.kind, value.index)
                # S describes the value selected by K, including assignment targets.
                declared = self.analyzer.expr_types.get(
                    id(value), symbol.resolved_type if symbol else value.type_ann)
                path = []
                path_cells = []
                for part in value.components:
                    if path_cells: path_cells.append(Cell("."))
                    match part:
                        case n.StaticAccess(index=index):
                            path.append(str(index)); path_cells.append(Cell(str(index)))
                        case n.DereferenceAccess():
                            path.append("@"); path_cells.append(Cell("@", extension=True))
                        case n.DynamicAccess(expr=expr):
                            path.append("[" + self.inline(expr) + "]")
                            path_cells.extend([Cell("(")] + self.expr(expr) + [Cell(")")])
                        case _: raise TypeError(type(part).__name__)
                s = structure(declared) if declared is not None else "?"
                return [Cell(value.kind, str(value.index), ".".join(path), s,
                             "@" in s or any(isinstance(p, n.DereferenceAccess) for p in value.components),
                             "Тип всей переменной: " + structure(symbol.resolved_type) if symbol else "",
                             path_cells if any(isinstance(p, n.DynamicAccess) for p in value.components) else [])]
            case n.IndexRef(index=index):
                return [Cell("i", str(index), structure=structure(self.analyzer.expr_types[id(value)]),
                             hint=f"Индекс цикла i{index}, только для чтения")]
            case n.ListLiteral(elements=elements):
                return [Cell("[", extension=True)] + self.separated(elements) + [Cell("]", extension=True)]
            case n.RecordLiteral(elements=elements):
                return [Cell("(")] + self.separated(elements) + [Cell(")")]
            case n.IntLiteral(value=number): return [Cell(str(number))]
            case n.BoolLiteral(value=bit): return [Cell("L" if bit else "0")]
            case n.BitSeqLiteral(bits=bits): return [Cell("".join("L" if b else "0" for b in bits))]
            case n.NilLiteral(): return [Cell("NIL", extension=True)]
            case n.Allocate(target=target): return [Cell("@" + target, extension=True)]
            case n.BinaryExpr(left=left, op=op, right=right):
                operator = {"*": "×", "!=": "≠", "<=": "≤", ">=": "≥", "&": "∧", "|": "∨"}.get(str(op), str(op))
                return self.child(left, value) + [Cell(operator)] + self.child(right, value, right=True)
            case n.UnaryExpr(op=op, operand=operand):
                return [Cell("¬" if str(op) == "~" else "−")] + self.child(operand, value)
            case n.FuncCall(name=name, args=args):
                if name in ("N", "Lz") or id(value) in self.analyzer.library_calls:
                    return [Cell(name, hint="Стандартная операция списка"), Cell("(")] + self.separated(args) + [Cell(")")]
                symbol = self.analyzer.programs.get(name) or next(s for s in self.analyzer.programs.values() if s.name == name)
                indices = [str(result.index) for result in symbol.ast.results]
                index = indices[0] if len(indices) == 1 else "(" + ", ".join(indices) + ")"
                hint = f"{name}: результат процедуры P{symbol.number}"
                if len(indices) > 1: hint += "; кортеж результатов — адаптация диалекта, один вызов"
                return [Cell(f"R{symbol.number}", index, extension=len(indices) > 1, hint=hint), Cell("(")] + self.separated(args) + [Cell(")")]
            case _:
                raise TypeError(f"Unsupported notation expression: {type(value).__name__}")

    def inline(self, value) -> str:
        """Text fallback for K; the UI uses its nested component cells."""
        return " ".join(c.text + c.index + (f"[{c.component}]" if c.component else "") for c in self.expr(value))

    def separated(self, values) -> list[Cell]:
        cells = []
        for i, value in enumerate(values):
            if i: cells.append(Cell(","))
            cells.extend(self.expr(value))
        return cells

    def row(self, node, cells, depth=0, kind=None, **metadata):
        self.rows.append(dict(line=node.loc.line, column=node.loc.column,
                              endLine=node.loc.end_line, endColumn=node.loc.end_column,
                              depth=depth, kind=kind or type(node).__name__,
                              cells=[asdict(c) for c in cells], **metadata))

    def statements(self, statements, depth=0):
        for stmt in statements:
            match stmt:
                case n.Assignment(value=value, target=target):
                    self.row(stmt, self.expr(value) + [Cell("⇒")] + self.expr(target), depth)
                case n.Free(value=value):
                    self.row(stmt, self.expr(value) + [Cell("⇒"), Cell("@", extension=True)], depth)
                case n.GuardedStmt(condition=condition, body=body):
                    self.row(stmt, self.expr(condition) + [Cell("→\u0323", hint="Если условие истинно, выполнить блок")], depth, block=True)
                    self.statements(body, depth + 1)
                    self.row(stmt, [], depth, "EndBlock")
                case n.WLoop(body=body):
                    self.row(stmt, [Cell("W")], depth, block=True)
                    self.statements(body, depth + 1)
                    self.row(stmt, [], depth, "EndBlock")
                case n.IndexedLoop(variant=variant, index=index, bounds=bounds, body=body):
                    self.row(stmt, [Cell("W" + str(variant).translate(SUPERSCRIPT), str(index)), Cell("(")]
                             + self.separated(bounds) + [Cell(")")], depth, block=True)
                    self.statements(body, depth + 1)
                    self.row(stmt, [], depth, "EndBlock")
                case n.Fin(depth=levels, condition=condition):
                    kind, owner = self.analyzer.fin_targets[id(stmt)]
                    target = {"procedure": "процедуру", "block": "условный блок", "loop": "цикл", "iteration": "итерацию"}[kind]
                    if isinstance(owner, n.IndexedLoop): target += f" W{owner.variant} i{owner.index}"
                    hint = f"Завершает {target}, строка {owner.loc.line}"
                    cells = self.expr(condition) + [Cell("⇒")] if condition is not None else []
                    self.row(stmt, cells + [Cell("Fin" + (str(levels).translate(SUPERSCRIPT) if levels != 1 else ""), hint=hint)], depth)
                case _:
                    raise TypeError(f"Unsupported notation statement: {type(stmt).__name__}")


def project(source: str, filename: str = "<input>") -> dict:
    program = parse(source, filename)
    analyzer = check(program, filename)
    view = Projection(analyzer)
    for typedef in program.type_defs:
        view.row(typedef, [Cell(typedef.name, extension=True), Cell("="), Cell(structure(typedef.type_expr), extension=True)])
    for function in program.program_defs:
        view.scope = analyzer.programs[f"P{function.number}"].scope
        view.row(function, [Cell(f"P{function.number}")], caption=function.name or "Процедура")
        view.row(function, [Cell("R"), Cell("(")] + view.separated(function.params) + [Cell(")"), Cell("   "), Cell("(")] + view.separated(function.results) + [Cell(")")], kind="Interface", caption="Входные данные и результаты")
        view.statements(function.body, 1)
        view.row(function, [], kind="EndProgram")
    from plankalkulsharp.standard_library import source
    libraries = []
    for key, symbol in analyzer.library_specializations.items():
        name, bindings, projection = key
        library = Projection(analyzer)
        library.scope = symbol.scope
        library.row(symbol.ast, [Cell(name)], caption="Стандартный план · " + name)
        library.row(symbol.ast, [Cell("(")] + library.separated(symbol.ast.params) + [Cell(") ⇒ (")] + library.separated(symbol.ast.results) + [Cell(")")], kind="Interface")
        library.statements(symbol.ast.body, 1)
        libraries.append({"name": name, "bindings": {k: structure(v) for k, v in bindings},
                          "projection": projection, "file": analyzer.library_files[symbol.key],
                          "source": source(name), "rows": library.rows})
    return {"version": 1, "rows": view.rows, "libraries": libraries}
