"""CLI entry point for the Plankalkül compiler."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from plankalkulsharp.compiler import CompileError, compile_file, compile_to_il


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="plankalkulsharp",
        description="Plankalkül → CLR compiler",
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- parse ---
    parse_cmd = subparsers.add_parser("parse", help="Parse a .pk file and dump the AST")
    parse_cmd.add_argument("file", type=Path, help="Plankalkül source file (.pk)")

    # --- compile ---
    compile_cmd = subparsers.add_parser("compile", help="Compile a .pk file to CIL")
    compile_cmd.add_argument("file", type=Path, help="Plankalkül source file (.pk)")
    compile_cmd.add_argument("-o", "--output", type=Path, help="Output .il file path")
    compile_cmd.add_argument("--emit-il", action="store_true", help="Stop after emitting .il")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "parse":
        return _cmd_parse(args)
    if args.command == "compile":
        return _cmd_compile(args)

    return 1


def _cmd_parse(args) -> int:
    try:
        ast = compile_file(args.file)
    except CompileError as e:
        for err in e.errors:
            print(f"error: {err}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 1

    print(_dump_ast(ast))
    return 0


def _cmd_compile(args) -> int:
    try:
        il_source = compile_to_il(args.file)
    except CompileError as e:
        for err in e.errors:
            print(f"error: {err}", file=sys.stderr)
        return 1
    except FileNotFoundError:
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 1

    # Determine output path
    out_path = args.output
    if out_path is None:
        out_path = args.file.with_suffix(".il")

    out_path.write_text(il_source, encoding="utf-8")
    print(f"Wrote {out_path}")

    if args.emit_il:
        return 0

    # Build using the helper IL project in ./build.
    return _build_with_helper_project(il_source)


def _build_with_helper_project(il_source: str) -> int:
    """Build generated IL through the helper project in ./build."""
    repo_root = Path(__file__).resolve().parents[2]
    build_dir = repo_root / "build"
    ilproj_path = build_dir / "PlankalkulProgram.ilproj"
    il_path = build_dir / "PlankalkulProgram.il"

    if not ilproj_path.exists():
        print(f"error: build project not found: {ilproj_path}", file=sys.stderr)
        return 1

    dotnet = shutil.which("dotnet")
    if dotnet is None:
        print("error: dotnet not found on PATH", file=sys.stderr)
        return 1

    il_path.write_text(il_source, encoding="utf-8")
    print(f"Wrote {il_path}")

    result = subprocess.run(
        [dotnet, "build", ilproj_path.name, "-c", "Release", "-nologo"],
        cwd=build_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"dotnet build failed:\n{result.stdout}\n{result.stderr}",
            file=sys.stderr,
        )
        return 1

    print("Built build/bin/Release/net10.0/PlankalkulProgram.exe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
