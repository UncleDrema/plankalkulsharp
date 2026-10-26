"""Main compiler pipeline: source → parse → AST → semantic → codegen."""

from __future__ import annotations

from pathlib import Path
from hashlib import sha256

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from plankalkulsharp.plankalkul_ast.nodes import Program
from plankalkulsharp.codegen.emitter import CILEmitter, EmitError
from plankalkulsharp.frontend.ast_builder import ASTBuilder, AstError
from plankalkulsharp.frontend.generated.PlankalkulLexer import PlankalkulLexer
from plankalkulsharp.frontend.generated.PlankalkulParser import PlankalkulParser
from plankalkulsharp.semantic.analyzer import Analyzer, SemanticError

class CompileError(Exception):
    """Raised when compilation fails."""

    def __init__(self, errors: list[str], diagnostics: list[dict] | None = None):
        self.errors = errors
        self.diagnostics = diagnostics if diagnostics is not None else [
            {"stage": "compile", "file": None, "line": None, "column": None, "message": message}
            for message in errors
        ]
        super().__init__("\n".join(errors))


class _ErrorCollector(ErrorListener):
    """Collects parse errors instead of printing them."""

    def __init__(self):
        super().__init__()
        self.errors: list[str] = []
        self.diagnostics: list[dict] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(f"{line}:{column}: {msg}")
        self.diagnostics.append({"stage": "parse", "line": line, "column": column, "message": msg})


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
            [f"{filename}: {e}" for e in error_listener.errors],
            [dict(d, file=filename) for d in error_listener.diagnostics],
        )

    builder = ASTBuilder()
    try:
        return builder.visit(tree)
    except AstError as e:
        raise CompileError(
            [f"{e.loc.line}:{e.loc.column}: {e}"],
            [{"stage": "ast", "file": filename, "line": e.loc.line, "column": e.loc.column, "message": str(e)}],
        )


def check(program: Program, filename: str = "<input>") -> Analyzer:
    """Run semantic analysis on a parsed AST.

    Returns the Analyzer (with type/program info).
    Raises CompileError on semantic errors.
    """
    analyzer = Analyzer()
    analyzer.filename = filename
    try:
        analyzer.analyze(program)
    except SemanticError as e:
        raise CompileError(
            [f"{d.get('file', filename)}:{d['line']}:{d['column']}: {d['message']}" for d in analyzer.diagnostics],
            [dict(d, file=d.get("file", filename)) for d in analyzer.diagnostics],
        ) from e
    return analyzer


def emit_il(program: Program, analyzer: Analyzer) -> str:
    """Generate CIL text assembly from a checked AST."""
    emitter = CILEmitter(analyzer)
    return emitter.emit()


def compile_to_ast(source_path: Path) -> Program:
    """Parse a .pk file into an AST."""
    source = source_path.read_text(encoding="utf-8")
    return parse(source, filename=str(source_path))

def compile_for_analyze(source_path: Path):
    """Parse a .pk file into an AST and check it."""
    source = source_path.read_text(encoding="utf-8")
    filename = str(source_path)
    program = parse(source, filename=filename)
    analyzer = check(program, filename=filename)
    analyzer.report()

def compile_to_il(source_path: Path) -> str:
    """Full pipeline: parse → check → emit IL."""
    source = source_path.read_text(encoding="utf-8")
    return compile_source(source, str(source_path))


def compile_source(source: str, filename: str = "<input>") -> str:
    """Compile one immutable source snapshot, shared by the CLI and monitor."""
    program = parse(source, filename=filename)
    analyzer = check(program, filename=filename)
    analyzer.source_sha256 = sha256(source.encode("utf-8")).hexdigest()
    try:
        return emit_il(program, analyzer)
    except EmitError as e:
        raise CompileError([str(e)]) from e
