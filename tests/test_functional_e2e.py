"""End-to-end functional tests for the full compiler/runtime pipeline.

Each test case compiles a Plankalkul program from ``tests/programs`` into
``PlankalkulProgram.il``, builds it via the IL .NET project, runs the produced
 executable with CLI arguments, and verifies the printed result.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from plankalkulsharp.compiler import compile_to_il

REPO_ROOT = Path(__file__).resolve().parents[1]
PROGRAMS_DIR = REPO_ROOT / "tests" / "programs"
BUILD_TEMPLATE_DIR = REPO_ROOT / "build"


CASES = [
    ("max.pk", ["3", "7"], "7"),
    ("max3.pk", ["3", "7"], "7"),
    ("arithmetic.pk", ["3", "4"], "13"),
    ("forloop.pk", ["5"], "15"),
    ("guard_block.pk", ["-42"], "42"),
    ("loop.pk", [], "10"),
    ("constants.pk", [], "13"),
    ("cross_program.pk", [], "10"),
    ("fibonacci.pk", ["10"], "55"),
    ("demo.pk", ["3", "7"], "7"),
    ("subprograms.pk", ["5"], "10"),
    ("multi_return.pk", ["3", "9"], "9"),
    pytest.param(
        "records.pk",
        ["2", "9"],
        "9",
        marks=pytest.mark.xfail(
            reason="Known runtime issue in record field assignment codegen (NullReferenceException)",
            strict=False,
        ),
    ),
    ("complex_udt.pk", ["1"], "40"),
    ("reverse_list.pk", ["5", "1"], "3"),
]


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def _require_dotnet() -> str:
    dotnet = shutil.which("dotnet")
    if dotnet is None:
        pytest.skip("dotnet is not available on PATH")
    return dotnet


def _prepare_build_dir(tmp_path: Path, il_source: str) -> Path:
    build_dir = tmp_path / "build"
    build_dir.mkdir(parents=True, exist_ok=True)

    (build_dir / "PlankalkulProgram.il").write_text(il_source, encoding="utf-8")
    shutil.copy2(BUILD_TEMPLATE_DIR / "PlankalkulProgram.ilproj", build_dir / "PlankalkulProgram.ilproj")

    nuget_config = BUILD_TEMPLATE_DIR / "nuget.config"
    if nuget_config.exists():
        shutil.copy2(nuget_config, build_dir / "nuget.config")

    return build_dir


def _run_built_program(dotnet: str, build_dir: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    exe_path = build_dir / "bin" / "Release" / "net10.0" / "PlankalkulProgram.exe"
    dll_path = build_dir / "bin" / "Release" / "net10.0" / "PlankalkulProgram.dll"

    if sys.platform.startswith("win"):
        assert exe_path.exists(), f"Expected executable was not produced: {exe_path}"
        cmd = [str(exe_path), *args]
    else:
        assert dll_path.exists(), f"Expected assembly was not produced: {dll_path}"
        cmd = [dotnet, str(dll_path), *args]

    return _run(cmd, cwd=build_dir)


@pytest.mark.parametrize("program_name,args,expected_output", CASES)
def test_program_pipeline(program_name: str, args: list[str], expected_output: str, tmp_path: Path):
    dotnet = _require_dotnet()
    il_source = compile_to_il(PROGRAMS_DIR / program_name)
    build_dir = _prepare_build_dir(tmp_path, il_source)

    build = _run(
        [dotnet, "build", "PlankalkulProgram.ilproj", "-c", "Release", "-nologo"],
        cwd=build_dir,
    )
    assert build.returncode == 0, (
        f"dotnet build failed for {program_name}\n"
        f"stdout:\n{build.stdout}\n"
        f"stderr:\n{build.stderr}"
    )

    run_result = _run_built_program(dotnet, build_dir, args)
    assert run_result.returncode == 0, (
        f"Executable failed for {program_name} with args={args}\n"
        f"stdout:\n{run_result.stdout}\n"
        f"stderr:\n{run_result.stderr}"
    )

    output_lines = [line.strip() for line in run_result.stdout.splitlines() if line.strip()]
    assert output_lines, f"Program produced no stdout for {program_name}"
    assert output_lines[-1] == expected_output
