"""Stdio LSP adapter. Compiler objects never cross document revisions.

The reader keeps accepting changes/cancellations while one analysis worker runs.
Full-text synchronization is intentional; ranges use LSP's UTF-16 coordinates.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, fields, is_dataclass
from functools import lru_cache
import json
import re
import sys
import threading
from urllib.parse import quote, urldefrag

from .compiler import CompileError, parse
from .plankalkul_ast import nodes as n
from .notation import project, structure
from .standard_library import catalog, source as library_source, template
from .semantic.analyzer import Analyzer, SemanticError, ResolvedRecord, ResolvedRef


def type_text(value):
    return re.sub(r",\s*", ", ", str(value))


@lru_cache(maxsize=1)
def library_completions():
    items = []
    for name, spec in catalog().items():
        params = template(name).params
        arguments = ", ".join("${" + str(i + 1) + ":V" + str(p.index) + "}" for i, p in enumerate(params))
        items.append({"label": name, "kind": 3, "detail": spec.get("description", "Стандартный план"),
                      "documentation": spec.get("example", ""), "insertTextFormat": 2,
                      "insertText": name + "(" + arguments + ")"})
    return items


def walk(value):
    if is_dataclass(value):
        yield value
        for field in fields(value):
            if field.name != "loc":
                yield from walk(getattr(value, field.name))
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from walk(child)


def position(text, line, column):
    lines = text.splitlines() or [""]
    line = min(max(0, line - 1), len(lines) - 1)
    return {"line": line, "character": len(lines[line][:max(0, column)].encode("utf-16-le")) // 2}


def span(text, loc):
    return {"start": position(text, loc.line, loc.column),
            "end": position(text, loc.end_line or loc.line, loc.end_column if loc.end_column is not None else loc.column + 1)}


@dataclass(frozen=True)
class Document:
    uri: str
    version: int
    text: str


class Analysis:
    def __init__(self, doc, recover=True):
        self.doc = doc
        self.ast = None
        self.analyzer = None
        self.diagnostics = []
        self.recover = recover
        self.recovered = {}
        try:
            self.ast = parse(doc.text, doc.uri)
            # Keep successfully resolved symbols even when a different expression
            # has a semantic error. The strict compiler still rejects this text.
            self.analyzer = Analyzer()
            self.analyzer.filename = doc.uri
            try:
                self.analyzer.analyze(self.ast)
            except SemanticError:
                raise CompileError(self.analyzer.errors, self.analyzer.diagnostics)
        except CompileError as error:
            for d in error.diagnostics:
                loc = n.Loc(d.get("line") or 1, d.get("column") or 0)
                self.diagnostics.append({"range": span(doc.text, loc), "severity": 1,
                                         "source": "Plankalkül", "message": d["message"]})

    def editing_analysis(self, pos):
        """A bounded, cursor-local fallback; never used for diagnostics or codegen."""
        if self.ast or not self.recover:
            return self
        key = pos["line"]
        if key in self.recovered:
            return self.recovered[key]
        candidates = [key] + [d["range"]["start"]["line"] for d in self.diagnostics[:2]]
        for line in dict.fromkeys(candidates):
            lines = self.doc.text.splitlines(keepends=True)
            if not 0 <= line < len(lines): continue
            value = lines[line].strip()
            # Never remove declarations or block boundaries to manufacture scope.
            if re.match(r"(?:P\d+\b|END\b|W\d*\b)", value) or any(c in value for c in "{}"):
                continue
            lines[line] = " " * len(lines[line].rstrip("\r\n")) + "\n"
            result = Analysis(Document(self.doc.uri, self.doc.version, "".join(lines)), recover=False)
            if result.ast:
                self.recovered[key] = result
                return result
        self.recovered[key] = self
        return self

    def variable_type(self, pos, token):
        function = self.function(pos)
        if not function or not self.analyzer: return None
        if re.fullmatch(r"i\d+", token):
            loops = [loop for loop in walk(function.body) if isinstance(loop, n.IndexedLoop)
                     and loop.index == int(token[1:]) and loop.loc.line - 1 <= pos["line"] <= (loop.loc.end_line or loop.loc.line) - 1]
            if loops: return self.analyzer.loop_types.get(id(loops[-1]))
        symbol = self.analyzer.programs.get(f"P{function.number}")
        scope = symbol.scope if symbol else None
        var = scope.vars.get(token) if scope else None
        return var.resolved_type if var else None

    def token(self, pos):
        lines = self.doc.text.splitlines()
        if pos["line"] >= len(lines):
            return ""
        line = lines[pos["line"]]
        col = len(line.encode("utf-16-le")[:pos["character"] * 2].decode("utf-16-le", errors="ignore"))
        return next((m.group() for m in re.finditer(r"[A-Za-z_][A-Za-z_0-9]*", line)
                     if m.start() <= col < m.end()), "")

    def function(self, pos):
        if not self.ast:
            return None
        return next((p for p in self.ast.program_defs if p.loc.line - 1 <= pos["line"]
                     <= (p.loc.end_line or p.loc.line) - 1), None)

    def definitions(self, pos):
        token = self.token(pos)
        if token in catalog():
            return [{"uri": "plankalkul-library:/" + token + ".pk", "range": span(library_source(token), n.Loc(2, 0))}]
        if not self.ast:
            return []
        target = next((t for t in self.ast.type_defs if t.name == token), None)
        target = target or next((p for p in self.ast.program_defs if token in (p.name, f"P{p.number}")), None)
        function = self.function(pos)
        if target is None and function:
            if re.fullmatch(r"[VZCR]\d+", token):
                declarations = list(function.params) + list(function.results)
                declarations += [x.target for x in walk(function.body) if isinstance(x, n.Assignment)]
                target = next((x for x in declarations if f"{x.kind}{x.index}" == token and not x.components), None)
            elif self.analyzer and re.fullmatch(r"i\d+", token):
                for ref in walk(function):
                    if isinstance(ref, n.IndexRef) and ref.index == int(token[1:]):
                        r = span(self.doc.text, ref.loc)
                        if r["start"]["line"] == pos["line"] and r["start"]["character"] <= pos["character"] < r["end"]["character"]:
                            target = self.analyzer.index_bindings.get(id(ref))
                            break
        return [{"uri": self.doc.uri, "range": span(self.doc.text, target.loc)}] if target else []

    def declared_type(self, pos, value, seen=frozenset()):
        """Retain written aliases through assignments, without guessing aliases
        from structural equality (distinct named references must stay distinct)."""
        if isinstance(value, n.Allocate): return n.RefType(value.loc, value.target)
        if isinstance(value, n.FuncCall) and self.ast:
            plan = next((p for p in self.ast.program_defs if value.name in (p.name, f"P{p.number}")), None)
            if plan and len(plan.results) == 1: return plan.results[0].type_ann
        function = self.function(pos)
        if not function: return None
        if isinstance(value, str):
            key, components, annotation = value, (), None
        elif isinstance(value, n.VarRef):
            key, components, annotation = f"{value.kind}{value.index}", value.components, value.type_ann
        else: return None
        if key in seen: return None
        seen = seen | {key}
        typ = annotation
        for ref in list(function.params) + list(function.results):
            if f"{ref.kind}{ref.index}" == key and ref.type_ann:
                typ = typ or ref.type_ann
        if typ is None:
            for stmt in walk(function.body):
                if isinstance(stmt, n.Assignment) and not stmt.target.components and f"{stmt.target.kind}{stmt.target.index}" == key:
                    typ = stmt.target.type_ann or self.declared_type(pos, stmt.value, seen)
                    if typ is not None: break
        for component in components:
            typ = self.unwrap_type(typ)
            if isinstance(component, n.DereferenceAccess) and isinstance(typ, n.RefType):
                typ = n.UserType(typ.loc, typ.target)
            elif isinstance(typ, n.RecordType) and isinstance(component, n.StaticAccess) and component.index < len(typ.fields):
                typ = typ.fields[component.index]
            elif isinstance(typ, n.ArrayType): typ = typ.element_type
            else: return None
        return typ

    def unwrap_type(self, typ):
        visited = set()
        while isinstance(typ, n.UserType) and typ.name not in visited:
            visited.add(typ.name)
            definition = next((t for t in self.ast.type_defs if t.name == typ.name), None)
            if definition is None: break
            typ = definition.type_expr
        return typ

    def type_card(self, title, resolved=None, written=None):
        display = type_text(written if written is not None else resolved)
        parts = [f"```plankalkul\n{title}: {display}\n```"]
        if written is not None:
            expanded = self.unwrap_type(written)
            chain, visited, current = [], set(), written
            while isinstance(current, n.UserType) and current.name not in visited:
                visited.add(current.name)
                td = next((t for t in self.ast.type_defs if t.name == current.name), None)
                if td is None: break
                chain.append(f"{td.name} = {type_text(td.type_expr)}")
                current = td.type_expr
            if title.startswith("Тип ") and chain:
                parts[0] = "```plankalkul\n" + chain[0] + "\n```"
                chain = chain[1:]
            if chain:
                parts.append("**Определение типа**\n\n```plankalkul\n" + "\n".join(chain) + "\n```")
            if isinstance(expanded, n.RecordType):
                parts.append("**Поля записи**\n\n| Компонент | Тип |\n|---|---|\n" + "\n".join(f"| `{i}` | {self.type_links(field)} |" for i, field in enumerate(expanded.fields)))
            names = {x.name for x in walk(written) if isinstance(x, n.UserType)} | {x.target for x in walk(written) if isinstance(x, n.RefType)}
            names |= {x.name for x in walk(expanded) if isinstance(x, n.UserType)} | {x.target for x in walk(expanded) if isinstance(x, n.RefType)}
            names |= visited
            links = []
            for td in self.ast.type_defs:
                if td.name in names:
                    links.append(f"[{td.name}](plankalkul-type:{td.name})")
            if links: parts.append("**Раскрыть тип:** " + " · ".join(links))
            if title.startswith("Тип ") and isinstance(written, n.UserType):
                td = next((t for t in self.ast.type_defs if t.name == written.name), None)
                if td:
                    uri = quote(urldefrag(self.doc.uri)[0], safe=":/%?=&")
                    parts.append(f"[Открыть определение в редакторе](<{uri}#L{td.loc.line},{td.loc.column + 1}>)")
        if resolved is not None:
            try: parts.append(f"**Структура S:** `{structure(resolved)}`")
            except TypeError: pass
        return {"contents": {"kind": "markdown", "value": "\n\n".join(parts)}}

    def type_links(self, typ):
        names = {t.name for t in self.ast.type_defs} if self.ast else set()
        return re.sub(r"[A-Za-z_]\w*", lambda m: f"[{m[0]}](plankalkul-type:{m[0]})" if m[0] in names else m[0], type_text(typ))

    def inspect_type(self, name):
        if not self.ast or not self.analyzer or name not in self.analyzer.type_defs: return None
        td = next(t for t in self.ast.type_defs if t.name == name)
        return self.type_card("Тип " + name, self.analyzer.type_defs[name], n.UserType(td.loc, name))

    def plan_card(self, plan):
        signature = f"P{plan.number} {plan.name or ''} ({', '.join(str(v.type_ann) for v in plan.params)}) -> ({', '.join(str(v.type_ann) for v in plan.results)})"
        rows = [("Аргумент", p) for p in plan.params] + [("Результат", p) for p in plan.results]
        table = "| Роль | Переменная | Тип |\n|---|---|---|\n" + "\n".join(f"| {role} | `{p.kind}{p.index}` | {self.type_links(p.type_ann)} |" for role, p in rows)
        return {"contents": {"kind": "markdown", "value": f"**План**\n\n```plankalkul\n{signature}\n```\n\n{table}"}}

    def hover(self, pos):
        token = self.token(pos)
        recovered = self.editing_analysis(pos)
        if recovered is not self:
            result = recovered.hover(pos)
            typ = recovered.variable_type(pos, token)
            if result is None and typ is not None:
                result = recovered.type_card(token, typ, recovered.declared_type(pos, token))
            if result:
                result["contents"]["value"] += "\n\n*По завершённой части кода; текущая строка ещё не проверена.*"
            return result
        if not self.analyzer:
            return self.library_hover(token)
        if token in self.analyzer.type_defs:
            td = next(t for t in self.ast.type_defs if t.name == token)
            return self.type_card("Тип " + token, self.analyzer.type_defs[token], n.UserType(td.loc, token))
        # Prefer the smallest expression containing the cursor, including fields.
        matches = []
        for node in walk(self.ast):
            typ = self.analyzer.expr_types.get(id(node))
            if typ is not None and hasattr(node, "loc"):
                r = span(self.doc.text, node.loc)
                point = (pos["line"], pos["character"])
                if (r["start"]["line"], r["start"]["character"]) <= point < (r["end"]["line"], r["end"]["character"]):
                    matches.append((node, typ, r))
        if matches:
            node, typ, r = min(matches, key=lambda item: (item[2]["end"]["line"] - item[2]["start"]["line"], item[2]["end"]["character"] - item[2]["start"]["character"], not isinstance(item[0], (n.VarRef, n.IndexRef, n.IntLiteral))))
            label = token or type(node).__name__
            if isinstance(node, n.VarRef) and node.components:
                lines = self.doc.text.splitlines()
                if node.loc.line == node.loc.end_line:
                    label = lines[node.loc.line - 1][node.loc.column:node.loc.end_column]
            extra = self.library_hover(token)
            result = self.type_card(label, typ, self.declared_type(pos, node))
            result["range"] = r
            if extra: result["contents"]["value"] += "\n\n---\n\n" + extra["contents"]["value"]
            return result
        typ = self.variable_type(pos, token)
        if typ is not None:
            return self.type_card(token, typ, self.declared_type(pos, token))
        symbol = next((s for s in self.analyzer.programs.values() if token in (s.name, f"P{s.number}")), None)
        if symbol:
            plan = next(p for p in self.ast.program_defs if p.number == symbol.number)
            return self.plan_card(plan)
        return self.library_hover(token)

    @staticmethod
    def library_hover(token):
        if token in catalog():
            spec = catalog()[token]
            return {"contents": {"kind": "markdown", "value": f"**Стандартный план `{token}`**\n\n" + spec.get("description", "Стандартный план") + "\n\n```plankalkul\n" + spec.get("example", "") + "\n```"}}
        return None

    def prefix(self, pos):
        lines = self.doc.text.splitlines()
        if pos["line"] >= len(lines): return ""
        return lines[pos["line"]].encode("utf-16-le")[:pos["character"] * 2].decode("utf-16-le", errors="ignore")

    def component_completion(self, pos, analysis):
        prefix = self.prefix(pos)
        match = re.search(r"\b([VZCR]\d+)\[((?:@|\d+)(?:\.(?:@|\d+))*\.)?([0-9]*)$", prefix)
        if not match: return None
        typ = analysis.variable_type(pos, match[1])
        for part in (match[2] or "").rstrip(".").split("."):
            if not part: continue
            if part == "@" and isinstance(typ, ResolvedRef):
                typ = analysis.analyzer.type_defs.get(typ.target)
            elif part.isdigit() and isinstance(typ, ResolvedRecord) and int(part) < len(typ.fields):
                typ = typ.fields[int(part)]
            else: return None
        if isinstance(typ, ResolvedRef):
            return [{"label": "@", "kind": 5, "detail": f"Разыменовать {typ}", "insertText": "@"}]
        if isinstance(typ, ResolvedRecord):
            return [{"label": str(i), "kind": 5, "detail": str(field),
                     "textEdit": {"range": {"start": {"line": pos["line"], "character": pos["character"] - len(match[3])}, "end": pos}, "newText": str(i)}}
                    for i, field in enumerate(typ.fields)]
        return None

    def signature_help(self, pos):
        # Track nested delimiters so commas inside records/lists do not advance
        # the outer call's parameter. No execution or speculative type coercion.
        text = "\n".join(self.doc.text.splitlines()[:pos["line"]] + [self.prefix(pos)])
        text = re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S)
        stack = []
        for i, c in enumerate(text):
            if c in "([{":
                name = re.search(r"([A-Za-z_]\w*)\s*$", text[:i]) if c == "(" else None
                stack.append([name[1] if name else None, 0])
            elif c in ")]}":
                if stack: stack.pop()
            elif c == "," and stack: stack[-1][1] += 1
        call = next((x for x in reversed(stack) if x[0]), None)
        if not call: return None
        name, active = call
        analysis = self.editing_analysis(pos)
        plan = template(name) if name in catalog() else next((p for p in analysis.ast.program_defs if name in (p.name, f"P{p.number}")), None) if analysis.ast else None
        if plan:
            params = [f"{p.kind}{p.index}: {p.type_ann}" for p in plan.params]
            results = ", ".join(str(p.type_ann) for p in plan.results)
            label = f"{name}({', '.join(params)}) -> ({results})"
        elif name in ("N", "Lz"):
            params = ["список"] if name == "N" else ["левый список", "правый список"]
            label = f"{name}({', '.join(params)})"
        else: return None
        return {"signatures": [{"label": label, "parameters": [{"label": p} for p in params]}],
                "activeSignature": 0, "activeParameter": min(active, max(0, len(params) - 1))}

    def completion(self, pos):
        recovered = self.editing_analysis(pos)
        components = self.component_completion(pos, recovered)
        if components is not None: return components
        if recovered is not self:
            items = recovered.completion(pos)
            for item in items:
                if item.get("kind") == 6: item["detail"] = item.get("detail", "") + " (по завершённой части кода)"
            return items
        items = [{"label": k, "kind": 14} for k in ("W", "W1", "W2", "W3", "W4", "W5", "FIN", "FIN2", "FIN3", "END", "NIL", "N", "Lz")]
        items += library_completions()
        if self.ast:
            items += [{"label": t.name, "kind": 7} for t in self.ast.type_defs]
            for p in self.ast.program_defs:
                name = p.name or f"P{p.number}"
                args = ", ".join("${" + str(i + 1) + ":V" + str(v.index) + "}" for i, v in enumerate(p.params))
                items.append({"label": name, "kind": 3, "detail": f"({', '.join(str(v.type_ann) for v in p.params)}) -> ({', '.join(str(v.type_ann) for v in p.results)})",
                              "insertTextFormat": 2, "insertText": name + "(" + args + ")"})
        function = self.function(pos)
        if function and self.analyzer:
            symbol = self.analyzer.programs.get(f"P{function.number}")
            scope = symbol.scope if symbol else None
            for key, var in (scope.vars.items() if scope else []):
                written = self.declared_type(pos, key)
                items.append({"label": key, "kind": 6, "detail": type_text(written or var.resolved_type),
                              "documentation": {"kind": "markdown", "value": re.sub(r"\[([^]]+)\]\(plankalkul-type:[^)]+\)", r"`\1`", self.type_card(key, var.resolved_type, written)["contents"]["value"])}})
            for loop in walk(function.body):
                if isinstance(loop, n.IndexedLoop) and loop.loc.line - 1 <= pos["line"] <= (loop.loc.end_line or loop.loc.line) - 1:
                    items.append({"label": f"i{loop.index}", "kind": 6, "detail": f"{self.analyzer.loop_types.get(id(loop), 'тип не определён')} · индекс цикла (только чтение)"})
        # Editing usually leaves an unfinished expression. Offer lexical names
        # from the current plan even when the strict compiler cannot build an
        # AST; these suggestions deliberately do not claim inferred types.
        text = re.sub(r"//[^\n]*|/\*.*?\*/", lambda m: "\n" * m.group().count("\n"), self.doc.text, flags=re.S)
        lines = text.splitlines()
        before = "\n".join(lines[:pos["line"] + 1])
        headers = list(re.finditer(r"(?m)^\s*P\d+\b", before))
        local = before[headers[-1].start():] if headers else ""
        if not self.analyzer:
            items += [{"label": name, "kind": 6, "detail": "Имя в текущем плане (тип ещё не проверен)"}
                      for name in sorted(set(re.findall(r"\b[VZCR]\d+\b", local)))]
        items += [{"label": name, "kind": 7, "detail": "Объявленный тип"}
                  for name in re.findall(r"(?m)^\s*([A-Za-z_]\w*)\s*=", text)]
        for number, name in re.findall(r"\bP(\d+)\s*(\w+)?\s*\(", text):
            items.append({"label": name or "P" + number, "kind": 3, "detail": "План P" + number})
        snippets = {
            "W": ("W {\n    ${1:V0 > 0} -> {\n        $0\n    }\n}", "Повторять, пока срабатывают условия"),
            "W1": ("W1 i${1:0} (${2:N(V0)}) {\n    $0\n}", "Индекс от 0 до n, не включая n"),
            "W2": ("W2 i${1:0} (${2:N(V0)}) {\n    $0\n}", "Индекс от n−1 до 0"),
            "W3": ("W3 i${1:0} (${2:0}, ${3:10}) {\n    $0\n}", "Возрастающий диапазон [n, m)"),
            "W4": ("W4 i${1:0} (${2:10}, ${3:0}) {\n    $0\n}", "Убывающий диапазон, m не включается"),
            "W5": ("W5 i${1:0} (${2:0}, ${3:10}) {\n    $0\n}", "Направление выбирается по границам"),
            "FIN": ("FIN", "Завершить ближайшую область; в теле цикла — итерацию"),
            "N": ("N(${1:V0})", "Число элементов списка"),
            "Lz": ("Lz(${1:V0}, ${2:V1})", "Соединение списков"),
        }
        unique = {item["label"]: item for item in reversed(items)}
        for label, (insert, description) in snippets.items():
            unique[label] = {"label": label, "kind": 15, "insertText": insert,
                             "insertTextFormat": 2, "detail": description, "documentation": description}
        if re.search(r"\[:[A-Za-z_0-9]*$", self.prefix(pos)):
            return [item for item in unique.values() if item.get("kind") == 7] + [
                {"label": name, "kind": 7, "detail": description} for name, description in
                [("0", "Бит"), ("32.0", "32-битная последовательность"), ("64.0", "64-битная последовательность")]]
        return list(unique.values())


class Server:
    def __init__(self, output):
        self.output = output
        self.lock = threading.RLock()
        self.documents = {}
        self.cache = {}
        self.cancelled = set()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.shutdown = False

    def send(self, payload):
        data = json.dumps({"jsonrpc": "2.0", **payload}, ensure_ascii=False).encode("utf-8")
        with self.lock:
            self.output.write(f"Content-Length: {len(data)}\r\n\r\n".encode("ascii") + data)
            self.output.flush()

    def analysis(self, doc):
        if self.cache.get(doc.uri, (None,))[0] != doc:
            self.cache[doc.uri] = (doc, Analysis(doc))
        return self.cache[doc.uri][1]

    def current(self, doc):
        return self.documents.get(doc.uri) == doc

    def diagnose(self, doc):
        if not self.current(doc):
            return
        analysis = self.analysis(doc)
        with self.lock:
            if self.current(doc):
                self.send({"method": "textDocument/publishDiagnostics", "params": {"uri": doc.uri, "version": doc.version, "diagnostics": analysis.diagnostics}})

    def request(self, message, doc):
        ident, method = message["id"], message["method"]
        params = message.get("params", {})
        try:
            if ident in self.cancelled:
                self.send({"id": ident, "error": {"code": -32800, "message": "Request cancelled"}}); return
            if doc and not self.current(doc):
                self.send({"id": ident, "error": {"code": -32801, "message": "Document changed"}}); return
            a = self.analysis(doc) if doc else None
            if method == "initialize":
                result = {"capabilities": {"positionEncoding": "utf-16", "textDocumentSync": {"openClose": True, "change": 1}, "hoverProvider": True, "definitionProvider": True, "documentSymbolProvider": True, "completionProvider": {"resolveProvider": False, "triggerCharacters": ["[", ".", "@", ":"]}, "signatureHelpProvider": {"triggerCharacters": ["(", ","]}}, "serverInfo": {"name": "PlankalkulSharp", "version": "0.1.0"}}
            elif method == "shutdown": self.shutdown = True; result = None
            elif method == "plankalkul/library":
                result = [{"name": name, "source": library_source(name), **spec} for name, spec in catalog().items()]
            elif method == "plankalkul/help":
                from .language_help import topics
                result = topics()
            elif method == "plankalkul/notation" and doc:
                result = {"uri": doc.uri, "documentVersion": doc.version, **project(doc.text, doc.uri)}
                # AST locations count Unicode code points; editors count UTF-16.
                for row in result["rows"]:
                    row["column"] = position(doc.text, row["line"], row["column"])["character"]
                    if row.get("endColumn") is not None:
                        row["endColumn"] = position(doc.text, row.get("endLine") or row["line"], row["endColumn"])["character"]
            elif method == "plankalkul/type": result = a.editing_analysis(params.get("position", {"line": 0, "character": 0})).inspect_type(params.get("name")) if a else None
            elif method == "textDocument/hover": result = a.hover(params["position"]) if a else None
            elif method == "textDocument/signatureHelp": result = a.signature_help(params["position"]) if a else None
            elif method == "textDocument/definition": result = a.definitions(params["position"]) if a else []
            elif method == "textDocument/completion": result = a.completion(params["position"]) if a else []
            elif method == "textDocument/documentSymbol":
                result = [{"name": getattr(node, "name", None) or f"P{node.number}", "kind": 12 if isinstance(node, n.ProgramDef) else 5,
                           "range": span(doc.text, node.loc), "selectionRange": {"start": span(doc.text, node.loc)["start"], "end": span(doc.text, node.loc)["start"]}}
                          for node in [*a.ast.type_defs, *a.ast.program_defs]] if a and a.ast else []
            else:
                self.send({"id": ident, "error": {"code": -32601, "message": f"Unsupported method: {method}"}}); return
            with self.lock:
                if ident in self.cancelled or (doc and not self.current(doc)):
                    self.send({"id": ident, "error": {"code": -32801, "message": "Request superseded"}})
                else: self.send({"id": ident, "result": result})
        except CompileError as error:
            self.send({"id": ident, "error": {"code": -32001, "message": str(error), "data": error.diagnostics}})
        except Exception as error:
            self.send({"id": ident, "error": {"code": -32603, "message": str(error)}})
        finally: self.cancelled.discard(ident)

    def receive(self, message):
        method, params = message.get("method"), message.get("params", {})
        if method == "exit": return False
        if method == "$/cancelRequest": self.cancelled.add(params["id"])
        elif method in ("textDocument/didOpen", "textDocument/didChange"):
            item = params["textDocument"]
            text = item["text"] if method.endswith("didOpen") else params["contentChanges"][-1]["text"]
            doc = Document(item["uri"], item["version"], text)
            with self.lock:
                if doc.uri in self.documents and self.documents[doc.uri].version >= doc.version: return True
                self.documents[doc.uri] = doc
            self.pool.submit(self.diagnose, doc)
        elif method == "textDocument/didClose":
            uri = params["textDocument"]["uri"]
            with self.lock:
                self.documents.pop(uri, None)
                self.cache.pop(uri, None)
                self.send({"method": "textDocument/publishDiagnostics", "params": {"uri": uri, "diagnostics": []}})
        elif "id" in message:
            doc = self.documents.get(params.get("textDocument", {}).get("uri"))
            self.pool.submit(self.request, message, doc)
        return True


def main():
    server = Server(sys.stdout.buffer)
    stream = sys.stdin.buffer
    try:
        while True:
            headers = {}
            while line := stream.readline():
                if line in (b"\r\n", b"\n"): break
                key, value = line.decode("ascii").split(":", 1)
                headers[key.lower()] = value.strip()
            if not line: break
            size = int(headers["content-length"])
            if size < 0 or size > 16 * 1024 * 1024: raise ValueError("LSP frame too large")
            payload = stream.read(size)
            if len(payload) != size: break
            if not server.receive(json.loads(payload)): break
    finally:
        server.pool.shutdown(wait=True, cancel_futures=True)


if __name__ == "__main__": main()
