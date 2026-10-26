from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
RUNTIME = ROOT / "src" / "plankalkulsharp" / "dotnet_assets" / "runtime" / "PlankalkulRuntime.csproj"

PROGRAM = r'''
using PlankalkulRuntime;
using System;
using System.Reflection;
using System.Linq;
using System.Text.Json;

static class Program
{
    static void Need(bool value, string message) { if (!value) throw new Exception(message); }
    static void Fault(Action action, string message)
    {
        try { action(); throw new Exception("expected fault: " + message); }
        catch (MemoryFault fault) { Need(fault.Message.Contains(message), fault.Message); }
    }
    static HeapSnapshot Snapshot()
    {
        var snapshot = Heap.Snapshot();
        var offset = 0;
        for (var i = 0; i < snapshot.Blocks.Count; i++)
        {
            var block = snapshot.Blocks[i];
            Need(block.Offset == offset && block.Size > 0 && block.Size % 8 == 0, "invalid block partition");
            if (i > 0) Need(!(snapshot.Blocks[i - 1].Free && block.Free), "unmerged neighbours");
            offset += block.Size;
        }
        Need(offset == 64 && snapshot.Stats.UsedBytes + snapshot.Stats.FreeBytes == 64, "heap accounting");
        Need(snapshot.Objects.Sum(o => o.ReservedSize) == snapshot.Stats.UsedBytes, "object accounting");
        return snapshot;
    }
    static void Main()
    {
        Heap.Initialize();
        long a = 0;
        try
        {
            a = Heap.Allocate(1, 9, "A", "a");           // 16 bytes
            var b = Heap.Allocate(1, 8, "A", "b");       // 8 bytes
            Heap.WriteInt32(a, 1, 0, 123, "write");
            Heap.Free(a, 1, "free-a");
            var c = Heap.Allocate(1, 8, "A", "c");       // first-fit split of a
            Need(Snapshot().Objects.Single(o => o.Handle == c.ToString()).Offset == 0, "first-fit address order");
            Need(Heap.ReadInt32(c, 1, 0, "zero") == 0, "allocation was not cleared");
            Fault(() => Heap.ReadByte(a, 1, 0, "stale"), "not live");
            Heap.Free(c, 1, "free-c");
            Heap.Free(b, 1, "free-b");                    // both neighbours coalesce
            var d = Heap.Allocate(2, 24, "B", "d");
            Need(d != a, "handles must not be reused");
            Fault(() => Heap.Free(d, 1, "wrong"), "not expected type");
            Fault(() => Heap.ReadInt64(d, 2, 20, "bounds"), "outside its bounds");
            var p = Heap.Allocate(4, 4, "P", "padding");
            Fault(() => Heap.ReadByte(p, 4, -1, "negative"), "outside its bounds");
            Fault(() => Heap.ReadByte(p, 4, 4, "padding"), "outside its bounds");
            Fault(() => Heap.ReadByte(p, 4, int.MaxValue, "maximum"), "outside its bounds");
            Heap.Free(p, 4, "free-p");
            Heap.Free(0, 2, "nil");
            Heap.Free(d, 2, "free-d");
            Fault(() => Heap.Free(d, 2, "double"), "not live");
            var x = Heap.Allocate(3, 16, "X", "x");
            var y = Heap.Allocate(3, 16, "X", "y");
            var q = Heap.Allocate(3, 16, "X", "q");
            var r = Heap.Allocate(3, 16, "X", "r");
            Heap.Free(x, 3, "free-x");
            Heap.Free(q, 3, "free-q");
            var beforeFailure = JsonSerializer.Serialize(Snapshot());
            Fault(() => Heap.Allocate(3, 24, "X", "fragment"), "out of memory");
            Need(JsonSerializer.Serialize(Snapshot()) == beforeFailure, "failed allocation changed state");
            var z = Heap.Allocate(3, 16, "X", "z");
            Heap.Free(y, 3, "free-y");
            Heap.Free(z, 3, "free-z");
            Heap.Free(r, 3, "free-r");
            Need(Snapshot().Blocks.Count == 1, "coalescing did not restore heap");

            var record = Heap.Allocate(7, 24, "nested", "inspect");
            var target = Heap.Allocate(8, 8, "target", "inspect-target");
            Heap.WriteInt64(record, 7, 0, long.MaxValue, "wide");
            Heap.WriteInt64(record, 7, 8, target, "link");
            var fields = new[] { new HeapField("0.0", 0, 8, "int64"), new HeapField("0.1", 8, 8, "ref", 8), new HeapField("1", 16, 8, "ref", 8) };
            var beforeInspect = JsonSerializer.Serialize(Snapshot());
            var view = Heap.Inspect(record, fields);
            Need(view.Fields[0].Value == "9223372036854775807", "64-bit inspection lost precision");
            Need(view.Fields[1].TargetHandle == target.ToString() && view.Fields[2].Value == "NIL", "reference inspection");
            Need(JsonSerializer.Serialize(Snapshot()) == beforeInspect, "inspection changed counters or heap");
            Heap.Free(target, 8, "free-target");
            Need(Heap.Inspect(record, fields).Fields[1].Value.StartsWith("freed"), "stale reference not identified");
            Need(Heap.Inspect(target, fields).Fields[0].Kind == "stale", "stale inspection faulted");
            Need(Heap.Inspect(0, fields).Fields[0].Value == "NIL", "NIL inspection faulted");
            Heap.Free(record, 7, "free-record");
            var next = typeof(Heap).GetField("_nextHandle", BindingFlags.Static | BindingFlags.NonPublic)!;
            var saved = (long)next.GetValue(null)!;
            next.SetValue(null, long.MaxValue);
            Fault(() => Heap.Allocate(3, 8, "X", "id"), "identifier space");
            next.SetValue(null, saved);
        }
        finally { Heap.Shutdown(); }
        Heap.Initialize();
        try { Fault(() => Heap.ReadByte(a, 1, 0, "after-restart"), "not live"); }
        finally { Heap.Shutdown(); }
        Heap.Initialize(new HeapOptions(520));
        try
        {
            var data = Heap.Allocate(9, 264, "page-test", "page");
            Heap.WriteByte(data, 9, 255, 0xAB, "page");
            Heap.WriteByte(data, 9, 256, 0xCD, "page");
            var before = JsonSerializer.Serialize(Heap.Snapshot());
            var page = Heap.InspectPage(248);
            Need(page.Offset == 248 && page.Size == 520 && page.Bytes.Count == 256, "heap page bounds");
            Need(page.Bytes[7] == 0xAB && page.Bytes[8] == 0xCD && page.Bytes[16] is null, "heap bytes or free-space mask");
            Need(Heap.InspectPage(512).Bytes.Count == 8, "last heap page");
            Need(Heap.InspectPage(-1).Bytes.Count == 0 && Heap.InspectPage(int.MaxValue).Bytes.Count == 0, "invalid heap offset");
            Need(JsonSerializer.Serialize(Heap.Snapshot()) == before, "heap inspection changed state");
            Heap.Free(data, 9, "page");
            Need(Heap.InspectPage(248).Bytes.All(value => value is null), "freed memory exposed");
        }
        finally { Heap.Shutdown(); }
    }
}
'''


@pytest.fixture(scope="module")
def heap_harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("native-heap")
    (directory / "HeapHarness.csproj").write_text(
        f'''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework></PropertyGroup><ItemGroup><ProjectReference Include="{RUNTIME.as_posix()}" /></ItemGroup></Project>''',
        encoding="utf-8",
    )
    (directory / "Program.cs").write_text(PROGRAM, encoding="utf-8")
    result = subprocess.run(
        ["dotnet", "build", "-c", "Release", "--nologo"], cwd=directory, text=True, encoding="utf-8", errors="replace", capture_output=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return directory / "bin" / "Release" / "net10.0" / "HeapHarness.dll"


def test_native_heap_allocator_and_diagnostics(heap_harness: Path) -> None:
    env = os.environ | {"PLANKALKUL_HEAP_SIZE": "64", "PLANKALKUL_MEMORY_TRACE": "1"}
    result = subprocess.run(["dotnet", str(heap_harness)], text=True, capture_output=True, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "memory: split" in result.stderr
    assert "memory: merge" in result.stderr
    assert "allocations=" in result.stderr
    assert "live=0" in result.stderr


@pytest.mark.parametrize("size", ["0", "9", "2147483648", "bad"])
def test_native_heap_rejects_invalid_size(heap_harness: Path, size: str) -> None:
    env = os.environ | {"PLANKALKUL_HEAP_SIZE": size}
    result = subprocess.run(["dotnet", str(heap_harness)], text=True, capture_output=True, env=env)
    assert result.returncode != 0
    assert "PLANKALKUL_HEAP_SIZE" in result.stderr
