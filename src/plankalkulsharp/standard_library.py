"""Specialize packaged PK plans, without giving their P0 user-visible identity."""
from dataclasses import fields, is_dataclass, replace
from importlib.resources import files
import json

from .plankalkul_ast.nodes import (
    ArrayType, BitSeqType, BitType, RecordType, RefType, UserType,
    VarRef, StaticAccess,
)

def catalog():
    content = files("plankalkulsharp").joinpath("stdlib", "catalog.json").read_text(encoding="utf-8")
    return json.loads(content)["plans"]


NAMES = frozenset(catalog())


def template(name):
    from .compiler import parse
    return parse(source(name), f"stdlib/{name}.pk").program_defs[0]


def substitute(node, bindings):
    if isinstance(node, UserType) and node.name in bindings:
        return type_node(bindings[node.name], node.loc)
    if isinstance(node, (tuple, list)):
        return type(node)(substitute(x, bindings) for x in node)
    if not is_dataclass(node):
        return node
    return replace(node, **{f.name: substitute(getattr(node, f.name), bindings) for f in fields(node)})


def bind(pattern, actual, bindings, parameters):
    """Unify a PK type pattern with a concrete argument, recursively.

    A repeated parameter keeps the first inferred type; ordinary assignability
    validates subsequent occurrences after substitution. Shape and length checks
    remain the normal semantic checker's responsibility.
    """
    from .semantic.analyzer import ResolvedArray, ResolvedRecord
    if isinstance(pattern, UserType) and pattern.name in parameters:
        bindings.setdefault(pattern.name, actual)
    elif isinstance(pattern, ArrayType) and isinstance(actual, ResolvedArray):
        bind(pattern.element_type, actual.element, bindings, parameters)
    elif isinstance(pattern, RecordType) and isinstance(actual, ResolvedRecord):
        for p, a in zip(pattern.fields, actual.fields):
            bind(p, a, bindings, parameters)


def unresolved(node, parameters, bindings):
    if isinstance(node, UserType):
        return node.name in parameters and node.name not in bindings
    if isinstance(node, (tuple, list)):
        return any(unresolved(x, parameters, bindings) for x in node)
    if is_dataclass(node):
        return any(unresolved(getattr(node, f.name), parameters, bindings) for f in fields(node))
    return False


def source(name):
    return files("plankalkulsharp").joinpath("stdlib", name + ".pk").read_text(encoding="utf-8")


def type_node(rt, loc):
    from .semantic.analyzer import ResolvedArray, ResolvedRecord, ResolvedRef, ResolvedBit
    if isinstance(rt, ResolvedArray):
        return ArrayType(loc, rt.size, type_node(rt.element, loc))
    if isinstance(rt, ResolvedRecord):
        return RecordType(loc, tuple(type_node(f, loc) for f in rt.fields))
    if isinstance(rt, ResolvedRef):
        return RefType(loc, rt.target)
    return BitType(loc) if isinstance(rt, ResolvedBit) else BitSeqType(loc, rt.length)


def specialize(name, bindings, number, projection=None):
    program = template(name)

    def visit(node):
        if isinstance(node, UserType) and node.name in bindings:
            return type_node(bindings[node.name], node.loc)
        if isinstance(node, (tuple, list)):
            return type(node)(visit(x) for x in node)
        if not is_dataclass(node):
            return node
        result = replace(node, **{f.name: visit(getattr(node, f.name)) for f in fields(node)})
        if (projection is not None and isinstance(result, VarRef) and len(result.components) == 2
                and isinstance(result.components[-1], StaticAccess)
                and result.components[-1].index == catalog()[name]["static"][0]["component"]):
            result = replace(result, components=(result.components[0], StaticAccess(result.components[1].loc, projection)))
        return result

    return replace(visit(program), number=number, name=f"__stdlib_{name}_{number}")


def fingerprint():
    from hashlib import sha256
    digest = sha256()
    root = files("plankalkulsharp").joinpath("stdlib")
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if entry.is_file():
            digest.update(entry.name.encode("utf-8"))
            digest.update(entry.read_bytes())
    return digest.hexdigest()
