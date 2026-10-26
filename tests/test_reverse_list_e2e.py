"""The maintained reverse-list example on the real .NET runtime."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from plankalkulsharp.compiler import compile_to_il
from plankalkulsharp.dotnet import build_program, ensure_worker


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "reverse_list.pk"


@pytest.fixture(scope="module")
def reverse_list_dll(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if shutil.which("dotnet") is None:
        pytest.skip("dotnet is not available on PATH")
    il_source = compile_to_il(EXAMPLE)
    return build_program(il_source, tmp_path_factory.mktemp("reverse-list"))


def run_dll(
    dll: Path, *args: int, memory_stats: bool = False, heap_size: int | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    environment = None
    if memory_stats or heap_size is not None:
        environment = dict(os.environ)
        if memory_stats:
            environment["PLANKALKUL_MEMORY_STATS"] = "1"
        if heap_size is not None:
            environment["PLANKALKUL_HEAP_SIZE"] = str(heap_size)
    result = subprocess.run(
        [shutil.which("dotnet"), str(ensure_worker()), "--module", str(dll), "--", *(str(arg) for arg in args)],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    if check:
        assert result.returncode == 0, result.stderr
    return result


@pytest.mark.parametrize("value,expected", [(1, 0), (2, 1), (3, 2), (4, 3), (5, 4)])
def test_reverse_list_all_five_links(reverse_list_dll: Path, value: int, expected: int):
    assert run_dll(reverse_list_dll, 5, value).stdout.strip() == str(expected)


def test_reverse_list_single_node(reverse_list_dll: Path):
    assert run_dll(reverse_list_dll, 1, 1).stdout.strip() == "0"


@pytest.mark.parametrize(("value", "expected"), [(1, 0), (1000, 999)])
def test_reverse_list_handles_a_thousand_nodes(reverse_list_dll: Path, value: int, expected: int):
    assert run_dll(reverse_list_dll, 1000, value).stdout.strip() == str(expected)


def test_reverse_list_frees_all_nodes(reverse_list_dll: Path):
    result = run_dll(reverse_list_dll, 5, 3, memory_stats=True)
    assert result.stdout.strip() == "2"
    assert "live=0" in result.stderr


def test_reverse_list_frees_a_thousand_nodes(reverse_list_dll: Path):
    result = run_dll(reverse_list_dll, 1000, 1000, memory_stats=True)
    assert result.stdout.strip() == "999"
    assert "live=0" in result.stderr


@pytest.mark.parametrize("args", [(-1, 1), (0, 1), (5, -1), (5, 0), (5, 6)])
def test_reverse_list_rejects_invalid_values_without_allocations(reverse_list_dll: Path, args: tuple[int, int]):
    result = run_dll(reverse_list_dll, *args, memory_stats=True)
    assert result.stdout.strip() == "-1"
    assert "allocations=0" in result.stderr


def test_tiny_heap_reports_memory_error_without_a_clr_stack(reverse_list_dll: Path):
    result = run_dll(reverse_list_dll, 5, 3, heap_size=8, check=False)
    assert result.returncode == 1
    assert "Memory error" in result.stderr
    assert "Unhandled exception" not in result.stderr
    assert "Stack trace" not in result.stderr


def test_cli_runs_source_from_a_path_with_spaces_and_cyrillic(tmp_path: Path):
    if shutil.which("dotnet") is None:
        pytest.skip("dotnet is not available on PATH")
    source_dir = tmp_path / "путь с пробелом"
    source_dir.mkdir()
    source = source_dir / "список.pk"
    source.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "plankalkulsharp", "run", "--memory-stats", str(source), "--", "5", "3"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "2"
    assert "live=0" in result.stderr
