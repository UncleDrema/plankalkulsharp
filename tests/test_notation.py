"""The projection preserves AST grouping, scope and selected-value structure."""
from pathlib import Path

from plankalkulsharp.notation import project


def test_notation_columns_and_current_examples():
    root = Path(__file__).parents[1]
    source = (root / "examples/notation.pk").read_text(encoding="utf-8")
    rows = project(source)["rows"]
    assignments = [r for r in rows if r["kind"] == "Assignment"]
    assert [c["text"] for c in assignments[0]["cells"]] == ["(", "V", "+", "V", ")", "×", "2", "⇒", "R"]
    variables = [c for row in assignments for c in row["cells"] if c["text"] == "V" and c["component"]]
    assert [c["index"] for c in variables] == ["0", "0"]
    assert [c["component"] for c in variables] == ["0", "1"]
    assert all(c["structure"] == "1.32" for c in variables)
    interfaces = [r for r in rows if r["kind"] == "Interface"]
    assert all(r["caption"] == "Входные данные и результаты" for r in interfaces)
    assert not any(c["text"] == "⇒" for r in interfaces for c in r["cells"])
    assert max(r["depth"] for r in rows) >= 5
    guards = [r for r in rows if r["kind"] == "GuardedStmt"]
    assert guards and all(r["cells"][-1]["text"] == "→\u0323" for r in guards)
    for example in ("reverse_list.pk", "fragmentation.pk"):
        rows = project((root / "examples" / example).read_text(encoding="utf-8"))["rows"]
        assert any(c["extension"] and "@" in c["component"] for r in rows for c in r["cells"])
        assert any(r["kind"] == "Free" for r in rows)
    rows = project("P0 f(V0[:4 x 32.0], V1[:32.0]) -> R0[:32.0]\nV0[(V1 + 1)] => R0\nEND")["rows"]
    indexed = next(c for r in rows if r["kind"] == "Assignment" for c in r["cells"] if c["text"] == "V")
    assert indexed["component"] == "[V1 + 1]"
    assert indexed["structure"] == "1.32"

    rows = project("P0 f(V0[:4 x 32.0]) -> R0[:32.0]\nV0 => Z0\n7 => Z0[3]\nZ0[3] => R0\nEND")["rows"]
    cells = [c for r in rows if r["kind"] == "Assignment" for c in r["cells"] if c["text"] == "Z"]
    assert [(c["component"], c["structure"]) for c in cells] == [("", "¤ × 1.32"), ("3", "1.32"), ("3", "1.32")]

    rows = project("P0 f(V0[:(0,32.0)]) -> R0[:32.0]\nV0 => Z0\n1 => Z0[0]\nZ0[1] => R0\nEND")["rows"]
    cells = [c for r in rows if r["kind"] == "Assignment" for c in r["cells"] if c["text"] == "Z"]
    assert [(c["component"], c["structure"]) for c in cells] == [("", "(0, 1.32)"), ("0", "0"), ("1", "1.32")]

    assert indexed["component_cells"][1]["index"] == "1"
    assert indexed["hint"] == "Тип всей переменной: 4 × 1.32"


def test_grouping_calls_and_block_boundaries():
    source = """P0 main(V0[:32.0], V1[:32.0], V2[:32.0]) -> R0[:32.0]
    V0 - (V1 - V2) => Z0
    V0 / (V1 * V2) => Z1
    -(V0 ** V1) => Z2
    (V0 ** V1) ** V2 => Z3
    inc(V0 + V1) => R0
    V0 > 0 -> { W { V1 > 0 -> { 1 => Z4 } } }
    END
    P3 inc(V0[:32.0]) -> R2[:32.0]
    V0 + 1 => R2
    END
    """
    rows = project(source)["rows"]
    expressions = [[c["text"] for c in r["cells"]] for r in rows if r["kind"] == "Assignment"]
    assert expressions[:4] == [
        ["V", "-", "(", "V", "-", "V", ")", "⇒", "Z"],
        ["V", "/", "(", "V", "×", "V", ")", "⇒", "Z"],
        ["−", "(", "V", "**", "V", ")", "⇒", "Z"],
        ["(", "V", "**", "V", ")", "**", "V", "⇒", "Z"],
    ]
    call = next(c for r in rows for c in r["cells"] if c["text"] == "R3")
    assert call["index"] == "2" and "inc" in call["hint"] and not call["extension"]
    assert [r["caption"] for r in rows if r["kind"] == "ProgramDef"] == ["main", "inc"]
    assert sum(r.get("block", False) for r in rows) == 3
    assert sum(r["kind"] == "EndBlock" for r in rows) == 3
    assert not any(c["text"] in ("{", "}", "END") for r in rows for c in r["cells"])

    rows = project("""P0 main(V0[:32.0]) -> R0[:32.0]
    pair(V0) => Z0
    Z0[0] => R0
    END
    P1 pair(V0[:32.0]) -> (R0[:32.0], R1[:32.0])
    V0 => R0
    V0 + 1 => R1
    END""")["rows"]
    calls = [c for r in rows if r["kind"] == "Assignment" for c in r["cells"] if c["text"] == "R1"]
    assert len(calls) == 1 and calls[0]["index"] == "(0, 1)" and calls[0]["extension"]


def test_notation_source_range():
    source = "P0 f() -> R0[:32.0]\nW1 i0 (3) { 7 => R0 }\nEND"
    rows = project(source)["rows"]
    assignment = next(r for r in rows if r["kind"] == "Assignment")
    assert assignment["line"] == assignment["endLine"] == 2
    assert source.splitlines()[1][assignment["column"]:assignment["endColumn"]] == "7 => R0"
    loop = next(r for r in rows if r["kind"] == "IndexedLoop")
    assert source.splitlines()[1][loop["column"]:loop["endColumn"]] == "W1 i0 (3) { 7 => R0 }"
