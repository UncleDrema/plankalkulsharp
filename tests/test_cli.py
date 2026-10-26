"""CLI behaviour without requiring a real .NET build for every case."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

import plankalkulsharp.__main__ as cli
from plankalkulsharp.compiler import CompileError
from plankalkulsharp.dotnet import BuildError


def test_library_catalog_works_outside_repository(tmp_path, monkeypatch, capsys):
    from plankalkulsharp.standard_library import catalog, source
    monkeypatch.chdir(tmp_path)
    assert cli.main(["library"]) == 0
    plans = json.loads(capsys.readouterr().out)["plans"]
    assert {p["name"] for p in plans} == set(catalog())
    assert all(p["source"] == source(p["name"]) for p in plans)
    assert next(p for p in plans if p["name"] == "Sp")["static"][0]["kind"] == "field"


def test_parse_and_analyze_accept_a_current_program(tmp_path: Path, capsys):
    source = tmp_path / "program.pk"
    source.write_text("P1 f() -> R0[:8.0]\n 0 => R0\nEND\n", encoding="utf-8")

    assert cli.main(["parse", str(source)]) == 0
    assert "Program" in capsys.readouterr().out
    assert cli.main(["analyze", str(source)]) == 0


def test_compile_writes_default_il_under_build(tmp_path: Path, monkeypatch):
    source = tmp_path / "program.pk"
    source.write_text("P1 f() -> R0[:8.0]\n 0 => R0\nEND\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "compile_to_il", lambda _: "// generated IL\n")

    assert cli.main(["compile", str(source)]) == 0
    assert (tmp_path / "build" / "program.il").read_text(encoding="utf-8") == "// generated IL\n"


def test_compile_creates_requested_parent_directory(tmp_path: Path, monkeypatch):
    source = tmp_path / "program.pk"
    source.write_text("source", encoding="utf-8")
    output = tmp_path / "nested" / "out.il"
    monkeypatch.setattr(cli, "compile_to_il", lambda _: "IL")

    assert cli.main(["compile", str(source), "-o", str(output)]) == 0
    assert output.read_text(encoding="utf-8") == "IL"


def test_compile_does_not_overwrite_its_source(tmp_path: Path, monkeypatch, capsys):
    source = tmp_path / "program.pk"
    source.write_text("original", encoding="utf-8")
    monkeypatch.setattr(cli, "compile_to_il", lambda _: "IL")

    assert cli.main(["compile", str(source), "-o", str(source)]) == 1
    assert source.read_text(encoding="utf-8") == "original"
    assert "must differ" in capsys.readouterr().err


def test_compile_rejects_removed_emit_il_flag(tmp_path: Path, capsys):
    source = tmp_path / "program.pk"
    source.write_text("source", encoding="utf-8")

    with pytest.raises(SystemExit) as error:
        cli.main(["compile", str(source), "--emit-il"])
    assert error.value.code == 2
    assert "unrecognized arguments: --emit-il" in capsys.readouterr().err


def test_run_forwards_program_arguments_and_exit_code(tmp_path: Path, monkeypatch):
    source = tmp_path / "program.pk"
    source.write_text("source", encoding="utf-8")
    called: dict[str, object] = {}
    monkeypatch.setattr(cli, "compile_to_il", lambda _: "IL")

    def fake_run(il_source: str, args: list[str], **options: object) -> int:
        called.update(il_source=il_source, args=args, options=options)
        return 7

    monkeypatch.setattr(cli, "run_program", fake_run)
    assert cli.main(["run", str(source), "--", "5", "3"]) == 7
    assert called == {
        "il_source": "IL",
        "args": ["5", "3"],
        "options": {"heap_size": 1_048_576, "memory_stats": False, "memory_trace": False},
    }


def test_run_passes_memory_options_before_source(tmp_path: Path, monkeypatch):
    source = tmp_path / "program.pk"
    source.write_text("source", encoding="utf-8")
    called: dict[str, object] = {}
    monkeypatch.setattr(cli, "compile_to_il", lambda _: "IL")

    def fake_run(_: str, args: list[str], **options: object) -> int:
        called.update(args=args, options=options)
        return 0

    monkeypatch.setattr(cli, "run_program", fake_run)
    assert cli.main(["run", "--heap-size", "104", "--memory-trace", str(source), "--", "5", "3"]) == 0
    assert called == {
        "args": ["5", "3"],
        "options": {"heap_size": 104, "memory_stats": True, "memory_trace": True},
    }


@pytest.mark.parametrize("size", ["0", "7", "2147483648", "nope"])
def test_run_rejects_invalid_heap_size(tmp_path: Path, capsys, size: str):
    source = tmp_path / "program.pk"
    source.write_text("source", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        cli.main(["run", "--heap-size", size, str(source)])
    assert error.value.code == 2
    assert "heap size" in capsys.readouterr().err


def test_errors_are_reported_without_traceback(tmp_path: Path, monkeypatch, capsys):
    missing = tmp_path / "missing.pk"
    assert cli.main(["compile", str(missing)]) == 1
    assert "error:" in capsys.readouterr().err

    source = tmp_path / "program.pk"
    source.write_text("source", encoding="utf-8")
    def fail_compile(_: Path) -> str:
        raise CompileError(["bad source"])

    monkeypatch.setattr(cli, "compile_to_il", fail_compile)
    assert cli.main(["run", str(source)]) == 1
    captured = capsys.readouterr()
    assert "bad source" in captured.err
    assert "Traceback" not in captured.err


def test_run_does_not_start_after_a_compile_failure(tmp_path: Path, monkeypatch):
    source = tmp_path / "program.pk"
    source.write_text("source", encoding="utf-8")
    called = False

    def fail_compile(_: Path) -> str:
        raise CompileError(["bad source"])

    def unexpected_run(*_: object) -> int:
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(cli, "compile_to_il", fail_compile)
    monkeypatch.setattr(cli, "run_program", unexpected_run)
    assert cli.main(["run", str(source)]) == 1
    assert not called


@pytest.mark.parametrize("failure", [OSError("dotnet not found"), BuildError("build failed")])
def test_run_reports_dotnet_failures(tmp_path: Path, monkeypatch, capsys, failure: Exception):
    source = tmp_path / "program.pk"
    source.write_text("source", encoding="utf-8")
    monkeypatch.setattr(cli, "compile_to_il", lambda _: "IL")

    def fail_run(*_: object, **__: object) -> int:
        raise failure

    monkeypatch.setattr(cli, "run_program", fail_run)

    assert cli.main(["run", str(source)]) == 1
    assert str(failure) in capsys.readouterr().err


def test_compile_reports_output_write_errors(tmp_path: Path, monkeypatch, capsys):
    source = tmp_path / "program.pk"
    source.write_text("source", encoding="utf-8")
    blocked = tmp_path / "file"
    blocked.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(cli, "compile_to_il", lambda _: "IL")

    assert cli.main(["compile", str(source), "-o", str(blocked / "out.il")]) == 1
    assert "error:" in capsys.readouterr().err


def test_build_json_returns_one_machine_readable_response(tmp_path: Path, monkeypatch, capsys):
    source = tmp_path / "программа.pk"
    source.write_text("source", encoding="utf-8")
    output = tmp_path / "module"
    monkeypatch.setattr(cli, "_build_response", lambda file, directory, text: {
        "ok": True,
        "artifact": {"assemblyPath": str(directory / "PlankalkulProgram.dll"), "workerPath": "worker.dll"},
        "source": {"path": str(file), "text": "source", "sha256": "hash"},
        "diagnostics": [],
    })

    assert cli.main(["build", str(source), "-o", str(output), "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "ok": True,
        "artifact": {"assemblyPath": str(output / "PlankalkulProgram.dll"), "workerPath": "worker.dll"},
        "source": {"path": str(source), "text": "source", "sha256": "hash"},
        "diagnostics": [],
    }


def test_build_json_returns_structured_failure(tmp_path: Path, monkeypatch, capsys):
    source = tmp_path / "program.pk"
    source.write_text("source", encoding="utf-8")
    monkeypatch.setattr(cli, "_build_response", lambda *_: (_ for _ in ()).throw(BuildError("SDK unavailable")))

    assert cli.main(["build", str(source), "-o", str(tmp_path / "out"), "--json"]) == 1
    response = json.loads(capsys.readouterr().out)
    assert response["ok"] is False
    assert response["diagnostics"][0]["stage"] == "build"
    assert response["diagnostics"][0]["message"] == "SDK unavailable"
    assert response["source"]["text"] == "source"


def test_build_compiles_the_single_source_snapshot(tmp_path: Path, monkeypatch):
    source = tmp_path / "program.pk"
    source.write_text("first", encoding="utf-8")
    seen: list[tuple[str, str]] = []

    def fake_compile(text: str, filename: str) -> str:
        seen.append((text, filename))
        source.write_text("second", encoding="utf-8")
        return "IL"

    monkeypatch.setattr(cli, "compile_source", fake_compile)
    monkeypatch.setattr(cli, "ensure_worker", lambda: tmp_path / "worker.dll")
    monkeypatch.setattr(cli, "build_program", lambda *_: tmp_path / "module.dll")
    response = cli._build_response(source, tmp_path / "out", source.read_text(encoding="utf-8"))

    assert seen == [("first", str(source.resolve()))]
    assert response["source"]["text"] == "first"


@pytest.mark.parametrize("command", ["parse", "analyze", "compile", "run"])
def test_source_commands_accept_only_pk(tmp_path: Path, capsys, command: str):
    source = tmp_path / "program.pl"
    source.write_text("anything", encoding="utf-8")
    assert cli.main([command, str(source)]) == 1
    assert ".pk" in capsys.readouterr().err


def test_build_rejects_unknown_source_suffix_with_json(tmp_path: Path, capsys):
    source = tmp_path / "program.pl"
    source.write_text("anything", encoding="utf-8")
    assert cli.main(["build", str(source), "-o", str(tmp_path / "out"), "--json"]) == 1
    response = json.loads(capsys.readouterr().out)
    assert response["source"] is None
    assert ".pk or .il" in response["diagnostics"][0]["message"]


def test_help_works_with_cp1251_stdout(monkeypatch):
    raw = io.BytesIO()
    stdout = io.TextIOWrapper(raw, encoding="cp1251")
    monkeypatch.setattr(cli.sys, "stdout", stdout)
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--help"])
    assert exc_info.value.code == 0


def test_build_stdin_uses_unsaved_snapshot_without_touching_file(tmp_path, monkeypatch, capsys):
    source = tmp_path / "пример.pk"
    source.write_text("old", encoding="utf-8")
    monkeypatch.setattr(cli.sys, "stdin", io.TextIOWrapper(io.BytesIO("новый снимок".encode("utf-8")), encoding="utf-8"))
    monkeypatch.setattr(cli, "_build_response", lambda file, out, text: {"ok": True, "source": {"text": text}})
    assert cli.main(["build", str(source), "--stdin", "--json", "-o", str(tmp_path / "out")]) == 0
    assert json.loads(capsys.readouterr().out)["source"]["text"] == "новый снимок"
    assert source.read_text(encoding="utf-8") == "old"
