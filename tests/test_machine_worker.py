from __future__ import annotations

import subprocess
from pathlib import Path

from plankalkulsharp.compiler import compile_source
from plankalkulsharp.dotnet import build_program


ROOT = Path(__file__).parents[1]
RUNTIME = ROOT / "src" / "plankalkulsharp" / "dotnet_assets" / "runtime" / "PlankalkulRuntime.csproj"
WORKER = ROOT / "src" / "plankalkulsharp" / "dotnet_assets" / "worker" / "PlankalkulWorker.csproj"

MODULE = r'''
using PlankalkulRuntime;
public static class PlankalkulProgram {
  public static string GetMetadata() => "{\"abi\":1,\"compilerVersion\":\"test\",\"source\":{},\"heapTypes\":[{\"id\":1,\"name\":\"node\",\"size\":16,\"layout\":{\"kind\":\"record\",\"size\":16,\"fields\":[{\"index\":0,\"offset\":0,\"layout\":{\"kind\":\"int32\",\"size\":4}},{\"index\":1,\"offset\":8,\"layout\":{\"kind\":\"ref\",\"size\":8,\"targetTypeId\":1}}]}}]}";
  public static void Execute(string[] args) {
    if (args.Length > 0 && args[0] == "hang") while (true) { }
    if (args.Length > 0 && args[0] == "fault") { Heap.Allocate(1, 16, "node", "fault:1"); throw new System.Exception("planned fault"); }
    if (args.Length > 0 && args[0] == "oom") { Heap.Allocate(1, 16, "node", "oom:1"); Heap.Allocate(1, 16, "node", "oom:2"); return; }
    if (args.Length > 0 && args[0] == "slow") { var h=Heap.Allocate(1,16,"node","slow:1"); for(var i=0;i<200;i++) Execution.Checkpoint(30+i,0); Heap.Free(h,1,"slow:2"); return; }
    if (args.Length > 0 && args[0] == "flood") { System.Console.Write(new string('\u0416',700000)); for(var i=0;i<2600;i++) { var h=Heap.Allocate(1,16,"node","flood:1"); Heap.Free(h,1,"flood:2"); System.Console.Write(new string('x',512)); } return; }
    var a = Heap.Allocate(1, 16, "node", "test:1"); var b = Heap.Allocate(1, 16, "node", "test:2");
    Heap.WriteInt32(a, 1, 0, 7, "test:3"); Heap.WriteInt64(a, 1, 8, b, "test:4");
    for (var i = 0; i < 80; i++) Execution.Checkpoint(10 + i, 0); System.Console.WriteLine("small-output");
    Heap.Free(a, 1, "test:5"); Heap.Free(b, 1, "test:6");
  }
}
'''

HARNESS = r'''
using System; using System.Diagnostics; using System.IO; using System.IO.Pipes; using System.Text; using System.Text.Json;
class Program {
 static void Send(StreamWriter w, object v) => w.WriteLine(JsonSerializer.Serialize(v));
 static int Main(string[] a) {
  var pipeName = "pk-test-" + Guid.NewGuid().ToString("N");
  using var pipe = new NamedPipeServerStream(pipeName, PipeDirection.InOut, 1, PipeTransmissionMode.Byte, PipeOptions.Asynchronous);
  using var process = Process.Start(new ProcessStartInfo("dotnet", $"\"{a[0]}\" --module \"{a[1]}\" --pipe {pipeName}") { UseShellExecute=false })!;
  pipe.WaitForConnection(); using var r = new StreamReader(pipe, Encoding.UTF8, false, 4096, true); using var w = new StreamWriter(pipe, new UTF8Encoding(false), 4096, true) { AutoFlush=true };
  var mode = a.Length > 2 ? a[2] : ""; var loss = mode == "loss"; var cooperative = mode == "cooperative"; var fault = mode == "fault"; var flood=mode=="flood";
  Send(w, new { version=1, command="start", heapSize=1024, delayMs=flood ? 0 : 20, arguments=loss ? new[]{"hang"} : fault ? new[]{"fault"} : flood ? new[]{"flood"} : Array.Empty<string>() });
  if (loss) { pipe.Close(); if (!process.WaitForExit(4000) || process.ExitCode != 130) throw new Exception("lost pipe did not force-stop uncooperative Worker"); Environment.Exit(0); }
  if(flood) System.Threading.Thread.Sleep(400);
  var paused=false; var inspected=false; var completed=false; var final=false; var exact=false; var diagnostic=false; var stopSent=false; var output=""; var last=""; var memory=0; var dropped=false; var deadline=DateTime.UtcNow.AddSeconds(15);
  while (DateTime.UtcNow < deadline && !completed) {
   var line=r.ReadLine(); if (line is null) break; using var d=JsonDocument.Parse(line); var root=d.RootElement; var e=root.GetProperty("event").GetString();
   last=e!;
   if (e == "output" && root.GetProperty("stream").GetString()=="stdout") output += root.GetProperty("text").GetString();
   if (e == "memory") { memory++; if(root.TryGetProperty("droppedCount",out var drop) && drop.GetInt64()>0) dropped=true; }
   if (e == "diagnostic") diagnostic=true;
   if (e == "snapshot" && !paused) {
    if (!flood && !fault && !cooperative) {
     var page=root.GetProperty("heapPage");
     if(page.GetProperty("snapshotSequence").GetInt64()!=root.GetProperty("sequence").GetInt64()
       || page.GetProperty("bytes")[0].GetByte()!=7) throw new Exception("live heap bytes missing or inconsistent");
    }
    Send(w, new {version=1,command="pause"});
   }
   if (e == "state" && root.GetProperty("state").GetString()=="paused") { paused=true; if(cooperative && !stopSent) { stopSent=true; Send(w,new {version=1,command="stop"}); } }
   if (e == "snapshot" && paused && root.GetProperty("exact").GetBoolean() && !inspected) Send(w, new {version=1,command="inspect",handle="1"});
   if (e == "inspection") { var fields=root.GetProperty("fields"); if (fields.GetArrayLength()!=2 || fields[1].GetProperty("targetHandle").GetString()!="2") throw new Exception("typed reference inspection failed"); inspected=true; Send(w,new {version=1,command="resume"}); }
   if (e == "snapshot" && root.GetProperty("exact").GetBoolean()) { exact=true; if(root.GetProperty("snapshot").GetProperty("stats").GetProperty("liveCount").GetInt32()==0) final=true; }
   if (e == "completed") { if(root.GetProperty("exitCode").GetInt32()!=(cooperative ? 130 : fault ? 1 : 0)) throw new Exception("bad exit"); completed=true; if(flood) { var retained=output.Replace("\n[output truncated]\n",""); if(memory>5001 || !dropped || !output.Contains("[output truncated]") || Encoding.UTF8.GetByteCount(retained)>1048576 || !final || last!="completed") throw new Exception($"flood limits memory={memory} dropped={dropped} output={output.Length} final={final} last={last}"); return 0; } if(cooperative) { if(!paused) throw new Exception("generated loop never paused"); return 0; } if(fault && diagnostic && exact) return 0; }
  }
  if (!paused || !inspected || !completed || !final || !output.Contains("small-output") || !output.Contains("\n") || last != "completed") throw new Exception($"missing Worker protocol event p={paused} i={inspected} c={completed} f={final} output={output} last={last}"); return 0;
 }
}
'''

PARALLEL_HARNESS = r'''
using System; using System.Diagnostics; using System.IO; using System.IO.Pipes; using System.Text; using System.Text.Json;
class P { public NamedPipeServerStream Pipe=null!; public StreamReader R=null!; public StreamWriter W=null!; public Process Process=null!; }
class Program {
 static void Send(StreamWriter w, object v) => w.WriteLine(JsonSerializer.Serialize(v));
 static P Start(string worker,string module,string name) { var p=new P(); p.Pipe=new NamedPipeServerStream(name,PipeDirection.InOut,1,PipeTransmissionMode.Byte,PipeOptions.Asynchronous); p.Process=Process.Start(new ProcessStartInfo("dotnet", $"\"{worker}\" --module \"{module}\" --pipe {name}"){UseShellExecute=false})!; p.Pipe.WaitForConnection(); p.R=new StreamReader(p.Pipe,Encoding.UTF8,false,4096,true); p.W=new StreamWriter(p.Pipe,new UTF8Encoding(false),4096,true){AutoFlush=true}; return p; }
 static JsonDocument Next(P p) { var line=p.R.ReadLine(); if(line is null) throw new Exception("lost worker pipe"); return JsonDocument.Parse(line); }
 static int Main(string[] a) {
  var bad=Start(a[0],a[1],"pk-a-"+Guid.NewGuid().ToString("N")); var good=Start(a[0],a[1],"pk-b-"+Guid.NewGuid().ToString("N"));
  Send(bad.W,new{version=1,command="start",heapSize=16,delayMs=0,arguments=new[]{"oom"}}); Send(good.W,new{version=1,command="start",heapSize=1024,delayMs=20,arguments=new[]{"slow"}});
  var paused=false; var inspected=false; var deadline=DateTime.UtcNow.AddSeconds(8);
  while(DateTime.UtcNow<deadline && !inspected) using(var d=Next(good)) { var r=d.RootElement; var e=r.GetProperty("event").GetString(); if(e=="snapshot"&&!paused) Send(good.W,new{version=1,command="pause"}); if(e=="state"&&r.GetProperty("state").GetString()=="paused") paused=true; if(e=="snapshot"&&paused&&r.GetProperty("exact").GetBoolean()) Send(good.W,new{version=1,command="inspect",handle="1"}); if(e=="inspection") { if(r.GetProperty("fields").GetArrayLength()!=2) throw new Exception("other Worker heap was corrupted"); inspected=true; } }
  if(!paused||!inspected) throw new Exception("second Worker did not pause independently");
  var badDone=false; while(DateTime.UtcNow<deadline&&!badDone) using(var d=Next(bad)) { var r=d.RootElement; if(r.GetProperty("event").GetString()=="completed") { if(r.GetProperty("exitCode").GetInt32()!=1) throw new Exception("OOM worker exit"); badDone=true; } }
  if(!badDone) throw new Exception("OOM worker never completed");
  Send(good.W,new{version=1,command="resume"}); var goodDone=false; var final=false; while(DateTime.UtcNow<deadline&&!goodDone) using(var d=Next(good)) { var r=d.RootElement; if(r.GetProperty("event").GetString()=="snapshot"&&r.GetProperty("exact").GetBoolean()&&r.GetProperty("snapshot").GetProperty("stats").GetProperty("liveCount").GetInt32()==0) final=true; if(r.GetProperty("event").GetString()=="completed") { if(r.GetProperty("exitCode").GetInt32()!=0) throw new Exception("healthy worker exit"); goodDone=true; } }
  if(!goodDone||!final) throw new Exception("healthy Worker was affected by OOM"); return 0;
 }
}
'''


def build(project: Path, name: str) -> Path:
    result = subprocess.run(["dotnet", "build", "-c", "Release", "--nologo", "-v:q"], cwd=project, text=True, encoding="utf-8", errors="replace", capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return project / "bin" / "Release" / "net10.0" / name


def test_worker_pipe_pause_snapshot_and_typed_inspection(tmp_path: Path) -> None:
    module = tmp_path / "module"; module.mkdir()
    (module / "Module.csproj").write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup><ItemGroup><ProjectReference Include="{RUNTIME.as_posix()}" /></ItemGroup></Project>', encoding="utf-8")
    (module / "Program.cs").write_text(MODULE, encoding="utf-8")
    module_dll = build(module, "Module.dll")
    worker_dll = build(WORKER.parent, "PlankalkulWorker.dll")
    harness = tmp_path / "harness"; harness.mkdir()
    (harness / "Harness.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework></PropertyGroup></Project>', encoding="utf-8")
    (harness / "Program.cs").write_text(HARNESS, encoding="utf-8")
    harness_dll = build(harness, "Harness.dll")
    result = subprocess.run(["dotnet", str(harness_dll), str(worker_dll), str(module_dll)], text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr

    lost = subprocess.run(["dotnet", str(harness_dll), str(worker_dll), str(module_dll), "loss"], text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=10)
    assert lost.returncode == 0, lost.stdout + lost.stderr

    fault = subprocess.run(["dotnet", str(harness_dll), str(worker_dll), str(module_dll), "fault"], text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=10)
    assert fault.returncode == 0, fault.stdout + fault.stderr

    no_heap = "P1 spin() -> R0[:8.0]\n W { W1 i0 (3) { FIN } FIN }\nEND\n"
    generated = build_program(compile_source(no_heap, "spin.pk"), tmp_path / "generated")
    stopped = subprocess.run(["dotnet", str(harness_dll), str(worker_dll), str(generated), "cooperative"], text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=10)
    assert stopped.returncode == 0, stopped.stdout + stopped.stderr

    flood = subprocess.run(["dotnet", str(harness_dll), str(worker_dll), str(module_dll), "flood"], text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=20)
    assert flood.returncode == 0, flood.stdout + flood.stderr


def test_parallel_workers_have_isolated_heaps(tmp_path: Path) -> None:
    module = tmp_path / "module"; module.mkdir()
    (module / "Module.csproj").write_text(f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup><ItemGroup><ProjectReference Include="{RUNTIME.as_posix()}" /></ItemGroup></Project>', encoding="utf-8")
    (module / "Program.cs").write_text(MODULE, encoding="utf-8")
    module_dll = build(module, "Module.dll")
    worker_dll = build(WORKER.parent, "PlankalkulWorker.dll")
    harness = tmp_path / "parallel"; harness.mkdir()
    (harness / "Parallel.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework></PropertyGroup></Project>', encoding="utf-8")
    (harness / "Program.cs").write_text(PARALLEL_HARNESS, encoding="utf-8")
    harness_dll = build(harness, "Parallel.dll")
    result = subprocess.run(["dotnet", str(harness_dll), str(worker_dll), str(module_dll)], text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr


def test_live_snapshots_coalesce_without_crossing_exact_views(tmp_path: Path) -> None:
    worker_source = WORKER.parent / "Program.cs"
    (tmp_path / "Queue.csproj").write_text(
        f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable><StartupObject>QueueCheck</StartupObject></PropertyGroup><ItemGroup><ProjectReference Include="{RUNTIME.as_posix()}"/><Compile Include="{worker_source.as_posix()}" Link="Worker.cs"/></ItemGroup></Project>', encoding="utf-8")
    (tmp_path / "Check.cs").write_text(r'''
using System.Text.Json;
using PlankalkulWorker;
class BlockingWriter() : StreamWriter(new MemoryStream()) {
 public TaskCompletionSource Entered = new(TaskCreationOptions.RunContinuationsAsynchronously);
 public TaskCompletionSource Release = new(TaskCreationOptions.RunContinuationsAsynchronously);
 public List<string> Lines = [];
 public override async Task WriteLineAsync(string? value) { Entered.TrySetResult(); await Release.Task; Lines.Add(value!); }
}
class QueueCheck {
 static async Task Main() {
  using var writer = new BlockingWriter(); var events = new EventWriter(writer);
  await events.Reliable(new { @event="blocked" }); await writer.Entered.Task;
  events.TrySend(new { @event="snapshot", sequence=1 }, snapshot:true);
  await events.Reliable(new { @event="paused" });
  events.TrySend(new { @event="snapshot", sequence=2, exact=true });
  for (var i=3;i<=200;i++) events.TrySend(new { @event="snapshot", sequence=i }, snapshot:true);
  events.TrySend(new { @event="snapshot", sequence=201, exact=true });
  await events.Reliable(new { @event="completed" });
  writer.Release.TrySetResult(); await events.DisposeAsync();
  var labels = writer.Lines.Select(line => { using var d=JsonDocument.Parse(line); var r=d.RootElement; return r.TryGetProperty("sequence",out var n) ? n.GetInt32().ToString() : r.GetProperty("event").GetString(); }).ToArray();
  if (string.Join(",",labels)!="blocked,paused,2,200,201,completed") throw new Exception("incorrect coalescing/order: "+string.Join(",",labels));
 }
}
''', encoding="utf-8")
    harness = build(tmp_path, "Queue.dll")
    result = subprocess.run(["dotnet", str(harness)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
