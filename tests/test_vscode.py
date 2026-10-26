"""VS Code protocols and real execution, without opening an editor window."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading

from plankalkulsharp.compiler import compile_source
from plankalkulsharp.dotnet import build_program, ensure_worker
from plankalkulsharp.lsp import Analysis, Document, position

ROOT = Path(__file__).resolve().parents[1]


def test_lsp_types_definitions_and_utf16():
    text = "int = 32.0\nP0 main(V0[:int]) -> R0[:int]\n V0 + 1 => R0\nEND"
    a = Analysis(Document("file:///тест.pk", 1, text))
    assert not a.diagnostics
    assert "V0: int" in a.hover({"line": 2, "character": 2})["contents"]["value"]
    assert a.definitions({"line": 2, "character": 2})[0]["range"]["start"]["line"] == 1
    assert any(i["label"] == "reverse" for i in a.completion({"line": 2, "character": 2}))
    assert position("// 😀 X", 1, 5)["character"] == 6


def test_help_uses_shipped_topics():
    from plankalkulsharp.language_help import topics
    result = topics()
    assert len(result) == 13
    assert any(p["code"] and "W1" in p["text"] for t in result for p in t["paragraphs"])


def test_completion_during_unfinished_expression():
    text = "int = 32.0\nP0 main(V0[:int]) -> R0[:int]\n1 => Z0\nZ0 +\nEND"
    a = Analysis(Document("file:///editing.pk", 1, text))
    assert a.diagnostics
    items = {x["label"]: x for x in a.completion({"line": 3, "character": 4})}
    assert {"V0", "R0", "Z0", "int", "main", "reverse"} <= items.keys()
    assert items["W3"]["insertTextFormat"] == 2
    assert "${" in items["W3"]["insertText"]
    assert items["Z0"]["detail"].startswith("0 ")


def test_hover_keeps_valid_types_with_semantic_error_elsewhere():
    text = "pair = (32.0, 64.0)\nP0 main(V0[:pair]) -> R0[:64.0]\nV0[1] => Z0\nZ9 => R0\nEND"
    a = Analysis(Document("file:///editing.pk", 1, text))
    assert a.diagnostics
    assert "64.0" in a.hover({"line": 2, "character": 4})["contents"]["value"]
    assert "64.0" in a.hover({"line": 2, "character": 10})["contents"]["value"]
    assert "(32.0, 64.0)" in a.hover({"line": 1, "character": 9})["contents"]["value"]


def test_component_completion_and_call_signature_in_unfinished_code():
    a = Analysis(Document("file:///fields.pk", 1,
        "pair = (32.0, 64.0)\nP0 main(V0[:pair]) -> R0[:32.0]\nV0[\nEND"))
    items = a.completion({"line": 2, "character": 3})
    assert [(x["label"], x["detail"]) for x in items] == [("0", "32.0"), ("1", "64.0")]
    text = "P0 main(V0[:32.0]) -> R0[:32.0]\nhelper(V0, \nEND\nP1 helper(V0[:32.0], V1[:64.0]) -> R0[:32.0]\nV0 => R0\nEND"
    a = Analysis(Document("file:///call.pk", 1, text))
    signature = a.signature_help({"line": 1, "character": 11})
    assert signature["activeParameter"] == 1
    assert "V1: 64.0" in signature["signatures"][0]["label"]


def test_markdown_hover_preserves_aliases_fields_and_definition_links():
    text = "int = 32.0\nnumber = int\nnode = (number, @node)\nP1 main(V0[:node]) -> R0[:number]\nV0 => Z0\nZ0[0] => R0\nEND\nP0 entry() -> R0[:32.0]\n0 => R0\nEND"
    a = Analysis(Document("file:///C:/example%20folder/test.pk", 1, text))
    assert not a.diagnostics
    card = a.hover({"line": 4, "character": 7})["contents"]
    assert card["kind"] == "markdown"
    assert "Z0: node" in card["value"]
    assert "node = (number, @node)" in card["value"]
    assert "[number](plankalkul-type:number)" in card["value"]
    field = a.hover({"line": 5, "character": 3})["contents"]["value"]
    assert "Z0[0]: number" in field
    assert "number = int" in field and "int = 32.0" in field
    alias = a.hover({"line": 1, "character": 1})["contents"]["value"]
    assert "number = int" in alias
    assert "[int](" in alias
    completion = {x["label"]: x for x in a.completion({"line": 5, "character": 0})}
    assert completion["Z0"]["detail"] == "node"


def test_equal_structures_do_not_invent_alias_for_unannotated_literal():
    text = "first = 3.0\nsecond = 3.0\nP0 main() -> R0[:32.0]\n7 => Z0\nZ0 => R0\nEND"
    a = Analysis(Document("file:///test.pk", 1, text))
    value = a.hover({"line": 3, "character": 6})["contents"]["value"]
    assert "Z0: 3.0" in value
    assert "Z0: first" not in value and "Z0: second" not in value


def test_plan_parameters_and_nested_types_have_inline_navigation():
    text = "int = 32.0\npair = (int, int)\nP0 main(V0[:pair]) -> R0[:int]\nV0[0] => R0\nEND"
    a = Analysis(Document("file:///functions.pk", 1, text))
    plan = a.hover({"line": 2, "character": 4})["contents"]["value"]
    assert "[pair](plankalkul-type:pair)" in plan
    assert "[int](plankalkul-type:int)" in plan
    card = a.inspect_type("pair")["contents"]["value"]
    assert "| `0` | [int](plankalkul-type:int) |" in card
    assert a.inspect_type("missing") is None
    assert "int = 32.0" in a.inspect_type("int")["contents"]["value"]


def test_stdio_lsp_unsaved_versions_and_notation():
    process = subprocess.Popen([sys.executable, "-m", "plankalkulsharp.lsp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    messages = queue.Queue()
    def read():
        while line := process.stdout.readline():
            size = int(line.split(b":", 1)[1]); process.stdout.readline()
            messages.put(json.loads(process.stdout.read(size)))
    threading.Thread(target=read, daemon=True).start()
    def send(method, params=None, ident=None):
        message = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if ident is not None: message["id"] = ident
        data = json.dumps(message).encode()
        process.stdin.write(f"Content-Length: {len(data)}\r\n\r\n".encode() + data); process.stdin.flush()
    def until(predicate):
        for _ in range(30):
            message = messages.get(timeout=10)
            if predicate(message): return message
        raise AssertionError("No matching response")
    try:
        send("initialize", {}, 1)
        assert until(lambda m: m.get("id") == 1)["result"]["capabilities"]["hoverProvider"]
        uri = "untitled:пример.pk"
        send("textDocument/didOpen", {"textDocument": {"uri": uri, "version": 1, "languageId": "plankalkul", "text": "bad source"}})
        assert until(lambda m: m.get("method") == "textDocument/publishDiagnostics")["params"]["diagnostics"]
        send("textDocument/didChange", {"textDocument": {"uri": uri, "version": 2}, "contentChanges": [{"text": "P0 main() -> R0[:32.0]\n7 => R0\nEND"}]})
        clean = until(lambda m: m.get("params", {}).get("version") == 2)
        assert clean["params"]["diagnostics"] == []
        send("plankalkul/notation", {"textDocument": {"uri": uri}}, 2)
        result = until(lambda m: m.get("id") == 2)["result"]
        assert result["documentVersion"] == 2 and result["rows"]
        send("plankalkul/library", {}, 3)
        assert any(p["name"] == "Sp" for p in until(lambda m: m.get("id") == 3)["result"])
        send("shutdown", {}, 4); until(lambda m: m.get("id") == 4)
        send("exit"); process.wait(timeout=10)
        assert process.returncode == 0
    finally:
        if process.poll() is None: process.kill()


def test_vscode_worker_transport(tmp_path):
    worker = ensure_worker()
    loop = "node = (32.0, @node)\nP0 main() -> R0[:32.0]\n@node => Z0\n7 => Z0[@.0]\nW { 1 => Z1 }\nEND"
    loop_module = build_program(compile_source(loop, "loop.pk"), tmp_path / "цикл")
    list_module = build_program(compile_source((ROOT / "examples/reverse_list.pk").read_text(encoding="utf-8"), "list.pk"), tmp_path / "список")
    result = subprocess.run(["node", "--test", "vscode/test/runtime.test.js"], cwd=ROOT,
                            env={**os.environ, "PK_WORKER": str(worker), "PK_LOOP": str(loop_module), "PK_LIST": str(list_module)},
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
