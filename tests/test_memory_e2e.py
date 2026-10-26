"""Behavior of compiled heap operations, including faults invisible to local analysis."""

import os
import subprocess

import pytest

from plankalkulsharp.compiler import compile_to_il
from plankalkulsharp.dotnet import build_program, ensure_worker


CASES = [
    (
        "record_copy",
        """
inner = (0, 64.0)
node = (inner, @node)
P0 main() -> R0[:32.0]
  @node => Z0
  L => Z0[@.0.0]
  4294967296 => Z0[@.0.1]
  Z0[@] => Z1
  @node => Z2
  Z1 => Z2[@]
  9 => Z0[@.0.1]
  0 => R0
  (Z2[@.0.0] & Z2[@.0.1] = 4294967296) -> 1 => R0
  Z0 => Z2[@.1]
  R0 + Z2[@.1.@.0.1] => R0
  Z2 => @
  Z0 => @
END
""",
        "10", None, 0,
    ),
    (
        "scalar_call",
        """
int = 32.0
P0 main() -> R0[:int]
  @int => Z0
  change(Z0) => Z1
  Z1[@] => R0
  Z0 => @
  NIL => @
END
P1 change(V0[:@int]) -> R0[:@int]
  42 => V0[@]
  V0 => R0
END
""",
        "42", None, 0,
    ),
    (
        "array_of_references",
        """
int = 32.0
refs = 2 x @int
P0 main() -> R0[:int]
  @int => Z0[0:refs]
  42 => Z0[0.@]
  Z0[0] => Z0[1]
  Z0[1.@] => R0
  Z0[0] => @
END
""",
        "42", None, 0,
    ),
    (
        "stale_field_after_reuse",
        """
node = (32.0, @node)
P0 main() -> R0[:32.0]
  @node => Z0
  @node => Z1
  Z1 => Z0[@.1]
  Z1 => @
  @node => Z1
  Z0[@.1.@.0] => R0
END
""",
        "", "not live", 2,
    ),
    (
        "free_during_store_value",
        """
int = 32.0
P0 main() -> R0[:int]
  @int => Z0
  release_node(Z0) => Z0[@]
  0 => R0
END
P1 release_node(V0[:@int]) -> R0[:int]
  V0 => @
  3 => R0
END
""",
        "", "not live", 0,
    ),
    (
        "nil_dereference",
        """
int = 32.0
P0 main() -> R0[:int]
  NIL => Z0[:@int]
  Z0[@] => R0
END
""",
        "", "cannot dereference NIL", 0,
    ),
    (
        "double_free_across_call",
        """
int = 32.0
P0 main() -> R0[:int]
  @int => Z0
  release_node(Z0) => R0
  Z0 => @
END
P1 release_node(V0[:@int]) -> R0[:int]
  V0 => @
  0 => R0
END
""",
        "", "not live", 0,
    ),
    (
        "leak_report",
        """
int = 32.0
P0 main() -> R0[:int]
  @int => Z0
  0 => R0
END
""",
        "0", None, 1,
    ),
]


@pytest.mark.parametrize("name,source,stdout,fault,live", CASES, ids=[c[0] for c in CASES])
def test_compiled_memory_behavior(tmp_path, name, source, stdout, fault, live):
    path = tmp_path / f"{name}.pk"
    path.write_text(source, encoding="utf-8")
    assembly = build_program(compile_to_il(path), tmp_path / "assembly")
    environment = os.environ | {
        "PLANKALKUL_HEAP_SIZE": "1048576",
        "PLANKALKUL_MEMORY_STATS": "1",
        "PLANKALKUL_MEMORY_TRACE": "0",
    }
    result = subprocess.run(["dotnet", str(ensure_worker()), "--module", str(assembly)], capture_output=True, text=True, env=environment)
    assert result.returncode == (1 if fault else 0), result.stderr
    assert result.stdout.strip() == stdout
    assert f"live={live}" in result.stderr
    if fault:
        assert fault in result.stderr
        assert path.name in result.stderr
        assert "Unhandled exception" not in result.stderr
    elif live:
        assert "allocated at" in result.stderr and path.name in result.stderr
