"""The module boundary exposes enough truth to inspect native objects safely."""

from hashlib import sha256

import pytest

from plankalkulsharp.codegen.emitter import CILEmitter
from plankalkulsharp.compiler import CompileError, check, compile_source, parse


def test_metadata_describes_nested_values_and_nominal_recursive_references():
    source = """inner = (0, 64.0)
node = (inner, @node)
alias = node
other = (inner, @other)
P0 main() -> R0[:32.0]
  @alias => Z0
  @other => Z1
  Z0 => @
  Z1 => @
  0 => R0
END
"""
    analyzer = check(parse(source), "снимок.pk")
    analyzer.source_sha256 = sha256(source.encode()).hexdigest()
    metadata = CILEmitter(analyzer).module_metadata()
    assert metadata["abi"] == 1
    assert metadata["source"] == {"path": "снимок.pk", "sha256": sha256(source.encode()).hexdigest()}
    types = {item["name"]: item for item in metadata["heapTypes"]}
    assert "alias" not in types
    node, other = types["node"], types["other"]
    assert node["id"] != other["id"]
    assert node["size"] == 24
    inner, link = node["layout"]["fields"]
    assert inner["offset"] == 0
    assert [(field["offset"], field["layout"]["kind"]) for field in inner["layout"]["fields"]] == [(0, "bit"), (8, "int64")]
    assert link["offset"] == 16
    assert link["layout"]["targetTypeId"] == node["id"]
    assert other["layout"]["fields"][1]["layout"]["targetTypeId"] == other["id"]


@pytest.mark.parametrize("source,stage,line,column", [
    ("P0 f() -> R0[:32.0]\n  ? => R0\nEND", "parse", 2, 2),
    ("P0 f() -> R0[:32.0]\n  Z9 => R0\nEND", "semantic", 2, 2),
])
def test_gui_diagnostics_keep_structured_source_positions(source, stage, line, column):
    with pytest.raises(CompileError) as error:
        compile_source(source, "путь с пробелом/исходник.pk")
    diagnostic = error.value.diagnostics[0]
    assert diagnostic["stage"] == stage
    assert diagnostic["file"] == "путь с пробелом/исходник.pk"
    assert (diagnostic["line"], diagnostic["column"]) == (line, column)
    assert diagnostic["message"]
