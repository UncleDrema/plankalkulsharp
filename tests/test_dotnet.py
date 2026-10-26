"""Behaviour of the small .NET build/run boundary, without an SDK."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import json

import plankalkulsharp.dotnet as dotnet


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("PLANKALKUL_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(dotnet, "_asset_fingerprint", lambda _: "test-sdk")


class FakeTemporaryDirectory:
    def __init__(self, path: Path):
        self.path = path

    def __enter__(self) -> str:
        self.path.mkdir()
        return str(self.path)

    def __exit__(self, *_: object) -> None:
        import shutil

        shutil.rmtree(self.path)


def test_sdk_selection_uses_packaged_policy_outside_repository(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "global.json").write_text('{"sdk":{"version":"11.0.100"}}')
    def version(command, **kwargs):
        assert command == ["dotnet", "--version"]
        policy = json.loads((kwargs["cwd"] / "global.json").read_text())
        assert policy["sdk"] == {"version": "10.0.100", "rollForward": "latestFeature", "allowPrerelease": False}
        return SimpleNamespace(returncode=0, stdout="10.0.103\n")
    monkeypatch.setattr(dotnet.subprocess, "run", version)
    assert dotnet._sdk_version("dotnet") == "10.0.103"


def test_build_streams_output_before_completion(monkeypatch, tmp_path, capsys):
    def lines():
        yield "Восстановление пакетов...\n"
        assert capsys.readouterr().err == "Восстановление пакетов...\n"
        yield "build error\n"

    class Process:
        stdout = lines()

        def __enter__(self): return self
        def __exit__(self, *_): pass
        def wait(self):
            captured = capsys.readouterr()
            assert captured.out == ""
            assert captured.err == "build error\n"
            return 1

    def start(command, **kwargs):
        assert command == ["dotnet", "build", "-p:NuGetAudit=false"]
        assert kwargs["stderr"] == dotnet.subprocess.STDOUT
        return Process()

    monkeypatch.setattr(dotnet.subprocess, "Popen", start)
    with pytest.raises(dotnet.BuildError, match="build error"):
        dotnet._run_build(["dotnet", "build"], cwd=tmp_path)


def test_build_requires_dotnet(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(dotnet.shutil, "which", lambda _: None)
    with pytest.raises(dotnet.BuildError, match="dotnet not found"):
        dotnet.build_program("IL", tmp_path / "build")


def test_failed_build_reports_diagnostics_and_does_not_run(tmp_path: Path, monkeypatch):
    temporary = tmp_path / "temporary"
    calls: list[list[str]] = []
    monkeypatch.setattr(dotnet.shutil, "which", lambda _: "dotnet")
    monkeypatch.setattr(dotnet, "_require_dotnet", lambda: "dotnet")
    monkeypatch.setattr(dotnet, "TemporaryDirectory", lambda *_, **__: FakeTemporaryDirectory(temporary))
    worker = tmp_path / "worker" / "PlankalkulWorker.dll"
    runtime = worker.parent / "PlankalkulRuntime.dll"
    runtime.parent.mkdir(parents=True)
    worker.write_bytes(b"worker")
    runtime.write_bytes(b"runtime")
    monkeypatch.setattr(dotnet, "ensure_worker", lambda: worker)

    def failed_build(command: list[str], **_: object) -> SimpleNamespace:
        calls.append(command)
        raise dotnet.BuildError("build output\nbuild error")

    monkeypatch.setattr(dotnet, "_run_build", failed_build)
    with pytest.raises(dotnet.BuildError, match="build output") as error:
        dotnet.run_program("IL", ["5"])
    assert "build error" in str(error.value)
    assert calls[0][:6] == ["dotnet", "build", "PlankalkulProgram.ilproj", "-c", "Release", "-nologo"]
    assert not temporary.exists()


def test_module_cache_reuses_output_and_invalidates_build_inputs(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(dotnet, "_require_dotnet", lambda: "dotnet")
    runtime = tmp_path / "Runtime.dll"
    runtime.write_bytes(b"runtime-v1")
    builds = []

    def build(command, **kwargs):
        builds.append(command)
        assert json.loads((Path(kwargs["cwd"]) / "global.json").read_text())["sdk"]["allowPrerelease"] is False
        output = Path(kwargs["cwd"]) / "bin/Release/net10.0/PlankalkulProgram.dll"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(f"module-{len(builds)}".encode())
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(dotnet, "_run_build", build)
    first = dotnet.build_program("IL-v1", tmp_path / "first", runtime_dll=runtime)
    second = dotnet.build_program("IL-v1", tmp_path / "second", runtime_dll=runtime)
    assert first.read_bytes() == second.read_bytes() == b"module-1"
    assert len(builds) == 1
    dotnet.build_program("IL-v2", tmp_path / "second", runtime_dll=runtime)
    runtime.write_bytes(b"runtime-v2")
    dotnet.build_program("IL-v2", tmp_path / "second", runtime_dll=runtime)
    monkeypatch.setattr(dotnet, "_asset_fingerprint", lambda _: "new-sdk")
    dotnet.build_program("IL-v2", tmp_path / "second", runtime_dll=runtime)
    assert len(builds) == 4


def test_run_uses_built_dll_preserves_cwd_and_cleans_temporary_dir(tmp_path: Path, monkeypatch):
    temporary = tmp_path / "temporary"
    original_cwd = tmp_path / "caller"
    original_cwd.mkdir()
    calls: list[tuple[list[str], dict[str, object], Path]] = []
    monkeypatch.chdir(original_cwd)
    monkeypatch.setattr(dotnet.shutil, "which", lambda _: "dotnet")
    monkeypatch.setattr(dotnet, "_require_dotnet", lambda: "dotnet")
    monkeypatch.setattr(dotnet, "TemporaryDirectory", lambda *_, **__: FakeTemporaryDirectory(temporary))
    worker = tmp_path / "worker" / "PlankalkulWorker.dll"
    runtime = worker.parent / "PlankalkulRuntime.dll"
    runtime.parent.mkdir(parents=True)
    worker.write_bytes(b"worker")
    runtime.write_bytes(b"runtime")
    monkeypatch.setattr(dotnet, "ensure_worker", lambda: worker)

    def successful_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((command, kwargs, Path.cwd()))
        if command[1] == "build":
            assembly = Path(kwargs["cwd"]) / "bin" / "Release" / "net10.0" / "PlankalkulProgram.dll"
            assembly.parent.mkdir(parents=True)
            assembly.write_bytes(b"dll")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        raise AssertionError("the Worker is started with Popen")

    class SuccessfulProcess:
        def __init__(self, command: list[str], **kwargs: object):
            calls.append((command, kwargs, Path.cwd()))

        def wait(self, timeout: float | None = None) -> int:
            return 12

    monkeypatch.setattr(dotnet, "_run_build", successful_run)
    monkeypatch.setattr(dotnet.subprocess, "Popen", SuccessfulProcess)
    assert dotnet.run_program("IL", ["5", "3"], heap_size=104, memory_trace=True, memory_stats=True) == 12
    assembly = temporary / "bin" / "Release" / "net10.0" / "PlankalkulProgram.dll"
    command, kwargs, cwd = calls[1]
    assert command == ["dotnet", str(worker), "--module", str(assembly), "--", "5", "3"]
    assert cwd == original_cwd
    assert kwargs["env"]["PLANKALKUL_HEAP_SIZE"] == "104"
    assert kwargs["env"]["PLANKALKUL_MEMORY_STATS"] == "1"
    assert kwargs["env"]["PLANKALKUL_MEMORY_TRACE"] == "1"
    assert not temporary.exists()
