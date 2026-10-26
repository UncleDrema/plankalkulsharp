"""End-to-end wheel acceptance check for PlankalkulSharp on Windows.

Run only after the working tree is stable.  The JSON report is intentionally
kept under build/package-verification so a GUI check can reuse its installed
Python, Worker and sample source paths.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "reverse_list.pk"
REPORT_ROOT = ROOT / "build" / "package-verification"


def call(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}\n{result.stderr}")
    return result


def cli(python: Path, args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return call([str(python), "-m", "plankalkulsharp", *args], cwd=cwd, env=env)


def wheel_resources(wheel: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        source_root = ROOT / "src" / "plankalkulsharp" / "dotnet_assets"
        for source in source_root.rglob("*"):
            if not source.is_file() or {"bin", "obj"}.intersection(source.relative_to(source_root).parts):
                continue
            packaged = f"plankalkulsharp/dotnet_assets/{source.relative_to(source_root).as_posix()}"
            if packaged not in names or archive.read(packaged) != source.read_bytes():
                raise RuntimeError(f"wheel resource differs from current source: {packaged}")
    required = (
        "plankalkulsharp/dotnet_assets/runtime/Heap.cs",
        "plankalkulsharp/stdlib/catalog.json",
        "plankalkulsharp/stdlib/reverse.pk",
        "plankalkulsharp/dotnet_assets/worker/PlankalkulWorker.csproj",
        "plankalkulsharp/dotnet_assets/desktop/PlankalkulMachine.csproj",
    )
    missing = [name for name in required if name not in names]
    if missing:
        raise RuntimeError(f"wheel misses packaged .NET resources: {', '.join(missing)}")
    generated = [name for name in names if "/bin/" in name or "/obj/" in name]
    if generated:
        raise RuntimeError(f"wheel contains generated .NET output: {generated[0]}")


def installed_distributions(python: Path, cwd: Path) -> list[str]:
    code = "import importlib.metadata as m; print('\\n'.join(sorted(d.metadata['Name'].lower() for d in m.distributions())))"
    return [name for name in call([str(python), "-I", "-c", code], cwd=cwd).stdout.splitlines() if name]


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the installed PlankalkulSharp wheel")
    parser.add_argument("--wheel", type=Path, help="Existing wheel; default builds one into dist")
    parser.add_argument("--report", type=Path, default=REPORT_ROOT / "report.json")
    options = parser.parse_args()
    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("uv not found on PATH")
    if not EXAMPLE.is_file():
        raise SystemExit(f"example not found: {EXAMPLE}")

    wheel = options.wheel.resolve() if options.wheel else None
    if wheel is None:
        call([uv, "build", "--wheel", "--out-dir", str(ROOT / "dist")], cwd=ROOT)
        wheels = sorted((ROOT / "dist").glob("plankalkulsharp-*.whl"), key=lambda path: path.stat().st_mtime)
        if not wheels:
            raise RuntimeError("uv build did not produce a wheel")
        wheel = wheels[-1]
    if not wheel.is_file():
        raise SystemExit(f"wheel not found: {wheel}")
    wheel_resources(wheel)

    report_path = options.report.resolve()
    report_root = report_path.parent
    if report_root == ROOT / "build" or not report_root.is_relative_to(ROOT / "build"):
        raise RuntimeError("verification output must be a subdirectory of this project's build directory")
    if report_root.exists():
        shutil.rmtree(report_root)
    report_root.mkdir(parents=True)
    environment = report_root / "environment"
    call([uv, "venv", str(environment), "--python", sys.executable], cwd=ROOT)
    python = environment / "Scripts" / "python.exe"
    call([uv, "pip", "install", "--python", str(python), str(wheel)], cwd=ROOT)
    distributions = installed_distributions(python, ROOT)
    expected = {"plankalkulsharp", "antlr4-python3-runtime"}
    if set(distributions) != expected:
        raise RuntimeError(f"isolated environment has unexpected distributions: {distributions}")

    work = report_root / "чистый запуск с пробелом"
    source = work / "разворот списка.pk"
    source.parent.mkdir(parents=True)
    shutil.copyfile(EXAMPLE, source)
    cache = report_root / "shared-cache"
    run_env = {**os.environ, "PLANKALKUL_CACHE_DIR": str(cache)}
    cli(python, ["--help"], cwd=work)
    plans = json.loads(cli(python, ["library"], cwd=work).stdout)
    if not any(p["name"] == "reverse" for p in plans["plans"]):
        raise RuntimeError("installed standard library catalog is missing")
    call([str(python), "-c", "from plankalkulsharp.lsp import Analysis, Document; from plankalkulsharp.language_help import topics; a=Analysis(Document('untitled:example.pk',1,'P0 main() -> R0[:32.0]\\n7 => R0\\nEND')); assert not a.diagnostics; assert len(topics()) == 13"], cwd=work)
    cli(python, ["parse", str(source)], cwd=work)
    cli(python, ["analyze", str(source)], cwd=work)
    cli(python, ["compile", str(source)], cwd=work)
    default_il = work / "build" / "разворот списка.il"
    if not default_il.is_file():
        raise RuntimeError("compile did not create its default IL output")
    explicit_il = work / "явный вывод" / "список.il"
    cli(python, ["compile", str(source), "-o", str(explicit_il)], cwd=work)
    if not explicit_il.is_file():
        raise RuntimeError("compile did not create its requested IL output")

    build_pk = cli(python, ["build", str(source), "-o", str(work / "модуль pk"), "--json"], cwd=work, env=run_env)
    pk_info = json.loads(build_pk.stdout)
    build_il = cli(python, ["build", str(explicit_il), "-o", str(work / "модуль il"), "--json"], cwd=work, env=run_env)
    il_info = json.loads(build_il.stdout)
    for info in (pk_info, il_info):
        if not info.get("ok") or not Path(info["artifact"]["assemblyPath"]).is_file():
            raise RuntimeError("build --json did not report an existing assembly")
        module_dir = Path(info["artifact"]["assemblyPath"]).parent
        if (module_dir / "PlankalkulRuntime.dll").exists() or any(module_dir.rglob("Heap.cs")):
            raise RuntimeError("program module carries Runtime sources or DLL")

    worker = Path(pk_info["artifact"]["workerPath"])
    runtime = worker.parent / "PlankalkulRuntime.dll"
    before = (worker.stat().st_mtime_ns, runtime.stat().st_mtime_ns)
    run = cli(python, ["run", "--memory-stats", str(source), "--", "5", "3"], cwd=work, env=run_env)
    if run.stdout.strip() != "2" or "allocations=5 frees=5" not in run.stderr or "live=0" not in run.stderr:
        raise RuntimeError(f"unexpected run result:\nstdout={run.stdout}\nstderr={run.stderr}")
    list_source = work / "нативные списки.pk"
    shutil.copyfile(ROOT / "examples" / "lists.pk", list_source)
    lists = cli(python, ["run", str(list_source), "--", "[2,3,4]"], cwd=work, env=run_env)
    expected_lists = [[4,3,2], [[0,4],[1,3],[2,2]], [7,8], [2,3,4], 3]
    if [json.loads(line) for line in lists.stdout.splitlines()] != expected_lists:
        raise RuntimeError(f"unexpected packaged list result: {lists.stdout}")
    tiny = subprocess.run([str(python), "-m", "plankalkulsharp", "run", "--heap-size", "8", str(source), "--", "5", "3"], cwd=work, env=run_env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if tiny.returncode != 1 or "Memory error" not in tiny.stderr or "Traceback" in tiny.stderr:
        raise RuntimeError(f"tiny heap did not fail cleanly:\n{tiny.stdout}\n{tiny.stderr}")
    after = (worker.stat().st_mtime_ns, runtime.stat().st_mtime_ns)
    if before != after:
        raise RuntimeError("Worker or Runtime was rebuilt during ordinary execution")

    machine = cli(python, ["machine", "--help"], cwd=work, env=run_env)
    if "machine" not in machine.stdout:
        raise RuntimeError("machine help is unavailable")
    machine_path = Path(call(
        [str(python), "-I", "-c", "from plankalkulsharp.dotnet import ensure_machine; print(ensure_machine())"],
        cwd=work,
        env=run_env,
    ).stdout.strip())
    if not machine_path.is_file():
        raise RuntimeError("ensure_machine did not build the WPF application")
    manifest = {
        "wheel": str(wheel),
        "python": str(python),
        "worker": str(worker),
        "runtime": str(runtime),
        "machine": str(machine_path),
        "source": str(source),
        "module": pk_info["artifact"]["assemblyPath"],
        "cache": str(cache),
        "distributions": distributions,
        "machineCommand": [str(python), "-m", "plankalkulsharp", "machine", str(source)],
    }
    report_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
