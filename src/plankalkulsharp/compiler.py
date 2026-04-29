"""Main compiler pipeline: source → parse → AST → semantic → codegen."""

from __future__ import annotations

from pathlib import Path

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from plankalkulsharp.my_ast.nodes import Program
from plankalkulsharp.codegen.emitter import CILEmitter
from plankalkulsharp.frontend.ast_builder import ASTBuilder
from plankalkulsharp.frontend.generated.PlankalkulLexer import PlankalkulLexer
from plankalkulsharp.frontend.generated.PlankalkulParser import PlankalkulParser
from plankalkulsharp.semantic.analyzer import Analyzer, SemanticError


class CompileError(Exception):
    """Raised when compilation fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


class _ErrorCollector(ErrorListener):
    """Collects parse errors instead of printing them."""

    def __init__(self):
        super().__init__()
        self.errors: list[str] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(f"{line}:{column}: {msg}")


def parse(source: str, filename: str = "<input>") -> Program:
    """Parse source code into an AST.

    Raises CompileError if there are syntax errors.
    """
    input_stream = InputStream(source)
    lexer = PlankalkulLexer(input_stream)

    error_listener = _ErrorCollector()
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)

    token_stream = CommonTokenStream(lexer)
    parser = PlankalkulParser(token_stream)

    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    tree = parser.program()

    if error_listener.errors:
        raise CompileError(
            [f"{filename}: {e}" for e in error_listener.errors]
        )

    builder = ASTBuilder()
    return builder.visit(tree)


def check(program: Program, filename: str = "<input>") -> Analyzer:
    """Run semantic analysis on a parsed AST.

    Returns the Analyzer (with type/program info).
    Raises CompileError on semantic errors.
    """
    analyzer = Analyzer()
    try:
        analyzer.analyze(program)
    except SemanticError as e:
        raise CompileError([f"{filename}: {err}" for err in e.errors]) from e
    return analyzer


def emit_il(program: Program, analyzer: Analyzer) -> str:
    """Generate CIL text assembly from a checked AST."""
    emitter = CILEmitter(analyzer)
    return emitter.emit(program)


def compile_file(source_path: Path) -> Program:
    """Parse a .pk file into an AST."""
    source = source_path.read_text(encoding="utf-8")
    return parse(source, filename=str(source_path))


def compile_to_il(source_path: Path) -> str:
    """Full pipeline: parse → check → emit IL."""
    source = source_path.read_text(encoding="utf-8")
    filename = str(source_path)
    program = parse(source, filename=filename)
    analyzer = check(program, filename=filename)
    return emit_il(program, analyzer)
