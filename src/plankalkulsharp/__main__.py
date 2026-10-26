"""CLI entry point for the Plankalkül compiler."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from plankalkulsharp.compiler import CompileError, compile_for_analyze, compile_source, compile_to_ast, compile_to_il
from plankalkulsharp.dotnet import BuildError, build_program, ensure_machine, ensure_worker, run_program


def _heap_size(value: str) -> int:
    try:
        size = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("heap size must be an integer") from error
    if size <= 0 or size > 2_147_483_647 or size % 8:
        raise argparse.ArgumentTypeError("heap size must be positive, a multiple of 8, and at most 2147483647")
    return size


def _dump_ast(node, indent: int = 0) -> str:
    """Simple recursive AST printer."""
    prefix = "  " * indent
    lines = [f"{prefix}{type(node).__name__}"]
    if hasattr(node, "__dataclass_fields__"):
        for field_name in node.__dataclass_fields__:
            value = getattr(node, field_name)
            if field_name == "loc":
                continue
            if isinstance(value, (list, tuple)):
                lines.append(f"{prefix}  {field_name}:")
                for item in value:
                    if hasattr(item, "__dataclass_fields__"):
                        lines.append(_dump_ast(item, indent + 2))
                    else:
                        lines.append(f"{prefix}    {item!r}")
            elif hasattr(value, "__dataclass_fields__"):
                lines.append(f"{prefix}  {field_name}:")
                lines.append(_dump_ast(value, indent + 2))
            else:
                lines.append(f"{prefix}  {field_name}: {value!r}")
    return "\n".join(lines)


def _require_suffix(path: Path, suffixes: tuple[str, ...], description: str) -> None:
    if path.suffix.lower() not in suffixes:
        allowed = " or ".join(suffixes)
        raise OSError(f"{description} accepts {allowed} files")


def _source_info(file: Path, text: str) -> dict[str, str]:
    return {
        "path": str(file.resolve()),
        "text": text,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def _diagnostics(error: Exception, stage: str, file: Path) -> list[dict[str, object]]:
    """Keep structured compiler diagnostics structured; old errors get a safe fallback."""
    items = getattr(error, "diagnostics", None)
    if items:
        result = []
        for item in items:
            if isinstance(item, dict):
                result.append({"stage": stage, "file": str(file), **item})
            else:
                result.append({
                    "stage": getattr(item, "stage", stage),
                    "file": str(getattr(item, "file", file)),
                    "line": getattr(item, "line", None),
                    "column": getattr(item, "column", None),
                    "message": getattr(item, "message", str(item)),
                })
        return result
    return [{"stage": stage, "file": str(file), "line": None, "column": None, "message": str(error)}]


def _build_response(file: Path, output: Path, source_text: str) -> dict[str, object]:
    if file.resolve() == (output / "PlankalkulProgram.il").resolve():
        raise OSError("output directory would overwrite the input IL file")
    il_source = source_text if file.suffix.lower() == ".il" else compile_source(source_text, str(file.resolve()))
    worker = ensure_worker()
    assembly = build_program(il_source, output)
    return {
        "ok": True,
        "artifact": {"assemblyPath": str(assembly), "workerPath": str(worker)},
        "source": _source_info(file, source_text),
        "diagnostics": [],
    }


def main(argv: list[str] | None = None) -> int:
    # Keep diagnostics printable when Windows redirects output using a legacy code page.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")

    parser = argparse.ArgumentParser(
        prog="plankalkulsharp",
        description="Plankalkul to CLR compiler",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("library", help="List packaged standard plans and their source as JSON")

    parse_cmd = subparsers.add_parser("parse", help="Parse a .pk file and dump the AST")
    parse_cmd.add_argument("file", type=Path, help="Plankalkul source file (.pk)")

    compile_cmd = subparsers.add_parser("compile", help="Compile a .pk file to CIL")
    compile_cmd.add_argument("file", type=Path, help="Plankalkul source file (.pk)")
    compile_cmd.add_argument("-o", "--output", type=Path, help="Output .il file path (default: build/<stem>.il)")

    build_cmd = subparsers.add_parser("build", help="Build a .pk or .il module for the shared executor")
    build_cmd.add_argument("file", type=Path, help="Plankalkul source (.pk) or generated IL (.il)")
    build_cmd.add_argument("-o", "--output", type=Path, required=True, metavar="DIRECTORY", help="Output directory for the module")
    build_cmd.add_argument("--json", action="store_true", help="Write one structured build result to stdout")
    build_cmd.add_argument("--stdin", action="store_true", help="Build an editor snapshot from UTF-8 stdin; file supplies its source identity")

    analyze_cmd = subparsers.add_parser("analyze", help="Analyze a .pk file")
    analyze_cmd.add_argument("file", type=Path, help="Plankalkul source file (.pk)")

    notation_cmd = subparsers.add_parser("notation", help="Project the AST into historical E/V/K/S rows (JSON; no .NET build)")
    notation_cmd.add_argument("file", type=Path, nargs="?", help="Plankalkul source file (.pk)")
    notation_cmd.add_argument("--stdin", action="store_true", help="Read a source snapshot from standard input")

    run_cmd = subparsers.add_parser("run", help="Compile, build and run a .pk file")
    run_cmd.add_argument(
        "--heap-size",
        type=_heap_size,
        default=1_048_576,
        metavar="BYTES",
        help="native heap size in bytes (default: 1048576)",
    )
    run_cmd.add_argument("--memory-stats", action="store_true", help="print heap statistics to stderr")
    run_cmd.add_argument("--memory-trace", action="store_true", help="trace heap operations to stderr")
    run_cmd.add_argument("file", type=Path, help="Plankalkul source file (.pk)")
    run_cmd.add_argument("program_args", nargs=argparse.REMAINDER, help="Program arguments after --")

    machine_cmd = subparsers.add_parser("machine", help="Open the Plankalkul Windows monitor")
    machine_cmd.add_argument("file", type=Path, nargs="?", help="Optional .pk source file to show")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1

    try:
        if args.command == "library":
            from plankalkulsharp.standard_library import catalog, source
            print(json.dumps({"plans": [{"name": name, "source": source(name), **spec}
                                        for name, spec in catalog().items()]}))
        elif args.command == "notation":
            from plankalkulsharp.notation import project
            if args.stdin:
                sys.stdin.reconfigure(encoding="utf-8")
                source = sys.stdin.read()
            else:
                if args.file is None:
                    raise OSError("notation requires a .pk file or --stdin")
                _require_suffix(args.file, (".pk",), "notation")
                source = args.file.read_text(encoding="utf-8")
            print(json.dumps(project(source, str(args.file or "<input>"))))
        elif args.command == "parse":
            _require_suffix(args.file, (".pk",), "parse")
            print(_dump_ast(compile_to_ast(args.file)))
        elif args.command == "analyze":
            _require_suffix(args.file, (".pk",), "analyze")
            compile_for_analyze(args.file)
        elif args.command == "compile":
            _require_suffix(args.file, (".pk",), "compile")
            il_source = compile_to_il(args.file)
            out_path = args.output or Path("build") / f"{args.file.stem}.il"
            if out_path.resolve() == args.file.resolve():
                raise OSError("output path must differ from source file")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(il_source, encoding="utf-8")
            print(f"Wrote {out_path}", file=sys.stderr)
        elif args.command == "build":
            snapshot = None
            try:
                _require_suffix(args.file, (".pk", ".il"), "build")
                if args.stdin:
                    sys.stdin.reconfigure(encoding="utf-8")
                snapshot = _source_info(args.file, sys.stdin.read() if args.stdin else args.file.read_text(encoding="utf-8"))
                response = _build_response(args.file, args.output, snapshot["text"])
            except (CompileError, BuildError, OSError, UnicodeError) as error:
                if args.json:
                    print(json.dumps({"ok": False, "artifact": None, "source": snapshot, "diagnostics": _diagnostics(error, "build", args.file)}))
                    return 1
                raise
            if args.json:
                # JSON must survive legacy Windows console encodings too.
                print(json.dumps(response))
            else:
                print(f"Built {response['artifact']['assemblyPath']}", file=sys.stderr)
        elif args.command == "machine":
            if args.file is not None:
                _require_suffix(args.file, (".pk",), "machine")
            if args.file is not None and not args.file.is_file():
                raise OSError(f"source file not found: {args.file}")
            dotnet = shutil.which("dotnet")
            if dotnet is None:
                raise BuildError("dotnet not found on PATH; install the .NET 10 SDK")
            command = [dotnet, str(ensure_machine()), "--python", str(Path(sys.executable).resolve()), "--worker", str(ensure_worker())]
            if args.file is not None:
                command.extend(["--source", str(args.file.resolve())])
            return subprocess.run(command).returncode
        elif args.command == "run":
            _require_suffix(args.file, (".pk",), "run")
            program_args = args.program_args
            if program_args[:1] == ["--"]:
                program_args = program_args[1:]
            return run_program(
                compile_to_il(args.file),
                program_args,
                heap_size=args.heap_size,
                memory_stats=args.memory_stats or args.memory_trace,
                memory_trace=args.memory_trace,
            )
    except CompileError as e:
        for err in e.errors:
            print(f"error: {err}", file=sys.stderr)
        return 1
    except (BuildError, OSError, UnicodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
