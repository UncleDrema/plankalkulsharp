"""Native lists and PK library bodies through the actual Worker."""
import json
import subprocess

import pytest

from plankalkulsharp.compiler import CompileError, check, compile_source, parse
from plankalkulsharp.dotnet import build_program, ensure_worker
from plankalkulsharp.notation import project


@pytest.mark.parametrize("body, message", [
    ("[] => Z0", "empty list"),
    ("[2, (3,4)] => Z0", "incompatible list"),
    ("[2,3] => Z0[:3 x 32.0]", "type mismatch"),
    ("[2] => Z0 [1] => Z1 Z0[Z1] => R0", "integer scalar"),
    ("[2] < [3] => R0", "structural"),
    ("Sp([(1,2)], 2) => Z0", "static valid field"),
    ("Qz([1], [2,3]) => Z0", "equal list lengths"),
    ("remove([1], 1) => Z0", "position out of range"),
])
def test_errors(body, message):
    with pytest.raises(CompileError, match=message):
        check(parse(f"P0 () -> R0[:32.0] {body} END"))


SOURCE = """
int = 32.0
node = (int, @node)
P0 (V0[:int], V1[:* x int], V2[:int]) -> (R0[:* x int], R1[:* x (int,int)], R2[:int])
V0 = 0 -> {
    reverse(V1) => R0
    Nr(R0) => R1
}
V0 = 1 -> {
    insert(V1,V2,99) => R0
    remove(R0,V2) => Z0
    Z0 = V1 => R2
}
V0 = 2 -> {
    Qz(V1, [7,8]) => R1
    Sp(R1,1) => R0
}
V0 = 3 -> {
    V1 => Z0
    99 => Z0[0]
    V1 => R0
    change(V1) => Z1
    V1 = Z1 => R2
}
V0 = 4 -> { V1 => Z4[:2 x int] Z4 => R0 }
V0 = 5 -> { V1[V2] => R2 }
V0 = 6 -> { Lz(V1,V1) => V1 V1 => R0 }
V0 = 7 -> {
    ([[2,3], [4]], 7) => Z5
    Z5 => Z6
    99 => Z6[0.0.0]
    Z5[0.0] => R0
    Z5 = Z6 => R2
}
V0 = 8 -> { reverse([]) => R0 Lz([], V1) => R0 }
V0 = 9 -> {
    @node => Z9
    ([2,3], Z9) => Z10
    Z10 => Z11
    77 => Z11[1.@.0]
    Z10[1.@.0] => R2
    Z9 => @
}
V0 = 10 -> { N(Z12[0:2 x * x int]) => R2 }
END
P1 change(V0[:* x int]) -> R0[:* x int]
88 => V0[0]
V0 => R0
END
"""


@pytest.fixture(scope="module")
def program(tmp_path_factory):
    return build_program(compile_source(SOURCE, "lists.pk"), tmp_path_factory.mktemp("списки с пробелами")), ensure_worker()


def run(program, mode, values, index=0):
    dll, worker = program
    return subprocess.run(["dotnet", str(worker), "--module", str(dll), "--", str(mode), json.dumps(values), str(index)],
                          capture_output=True, text=True, timeout=20)


@pytest.mark.parametrize("mode, values, index, expected", [
    (0, [2,3,4], 0, [[4,3,2], [[0,4],[1,3],[2,2]], 0]),
    (0, [], 0, [[], [], 0]),
    (1, [2,3], 2, [[2,3,99], [], 1]),
    (1, [], 0, [[99], [], 1]),
    (2, [2,3], 0, [[7,8], [[2,7],[3,8]], 0]),
    (3, [2,3], 0, [[2,3], [], 0]),
    (4, [2,3], 0, [[2,3], [], 0]),
    (6, [2,3], 0, [[2,3,2,3], [], 0]),
    (7, [], 0, [[2,3], [], 0]),
    (8, [2,3], 0, [[2,3], [], 0]),
    (9, [], 0, [[], [], 77]),
    (10, [], 0, [[], [], 0]),
])
def test_values(program, mode, values, index, expected):
    result = run(program, mode, values, index)
    assert result.returncode == 0, result.stderr
    assert [json.loads(line) for line in result.stdout.splitlines()] == expected


@pytest.mark.parametrize("mode, values, index, message", [
    (1, [2], -1, "position"), (1, [2], 2, "position"),
    (2, [2], 0, "equal list lengths"), (4, [2], 0, "expected 2"),
    (5, [2], -1, "list index"), (5, [2], 1, "list index"),
])
def test_runtime_errors(program, mode, values, index, message):
    result = run(program, mode, values, index)
    assert result.returncode == 1
    assert message in result.stderr


def test_notation_and_internal_identities():
    ast = parse(SOURCE)
    analyzer = check(ast)
    assert "P2" not in analyzer.programs
    assert analyzer.library_calls
    projection = project(SOURCE)
    assert projection["rows"]
    assert {p["name"] for p in projection["libraries"]} == {"reverse", "insert", "remove", "Nr", "Qz", "Sp"}


def test_generic_catalog_extension_and_dependencies(monkeypatch):
    import plankalkulsharp.standard_library as library
    original_source, original_catalog = library.source, library.catalog
    spec = {**original_catalog(), "identitylist": {"types": ["element"]}}
    monkeypatch.setattr(library, "catalog", lambda: spec)
    monkeypatch.setattr(library, "NAMES", frozenset(spec))
    monkeypatch.setattr(library, "source", lambda name: (
        "P0 (V0[:* x element]) -> R0[:* x element] reverse(reverse(V0)) => R0 END"
        if name == "identitylist" else original_source(name)))
    text = "P0 () -> R0[:* x (32.0,64.0)] identitylist([(2,4294967296)]) => R0 END"
    analyzer = check(parse(text))
    assert any(p["name"] == "identitylist" for p in project(text)["libraries"])
    assert len(analyzer.library_specializations) == 2
    assert all(key.startswith("__stdlib_") or key == "P0" for key in analyzer.programs)


def test_library_content_changes_module_metadata(monkeypatch):
    import plankalkulsharp.standard_library as library
    text = "P0 () -> R0[:32.0] 1 => R0 END"
    before = compile_source(text)
    monkeypatch.setattr(library, "fingerprint", lambda: "changed-library")
    assert compile_source(text) != before


def test_structured_wide_cli_and_result_indices(tmp_path):
    source = "P0 (V0[:(64.0, 2 x 32.0)]) -> (R2[:64.0],R5[:2 x 32.0]) V0[0] => R2 V0[1] => R5 END"
    dll = build_program(compile_source(source), tmp_path)
    result = subprocess.run(["dotnet", str(ensure_worker()), "--module", str(dll), "--", "[9223372036854775807,[2,3]]"],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["9223372036854775807", "[2,3]"]
