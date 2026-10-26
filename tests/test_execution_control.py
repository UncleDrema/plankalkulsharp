from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNTIME = ROOT / "src" / "plankalkulsharp" / "dotnet_assets" / "runtime" / "PlankalkulRuntime.csproj"

PROGRAM = r'''
using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using PlankalkulRuntime;

static class Program
{
    static void Need(bool value, string message) { if (!value) throw new Exception(message); }
    static void Main()
    {
        var control = new RunController();
        Execution.Attach(control);
        try
        {
            control.SetDelay(100);
            var snapshots = 0;
            control.SnapshotRequested += (_, _, _) => snapshots++;
            Need(control.RequestHeapInspect(256) && control.HeapOffset == 256, "running heap page selection failed");
            var watch = Stopwatch.StartNew();
            Execution.Checkpoint(1, 0); Execution.Checkpoint(2, 0); Execution.Checkpoint(3, 0);
            Need(watch.ElapsedMilliseconds >= 250, "delay did not slow checkpoints");
            Need(snapshots == 3, "every delayed checkpoint must produce a snapshot");

            control.SetDelay(0); control.Pause();
            var paused = Task.Run(() => Execution.Checkpoint(4, 0));
            Thread.Sleep(80); Need(!paused.IsCompleted && control.IsPaused, "checkpoint did not pause");
            control.Resume(); Need(paused.Wait(500), "resume did not release checkpoint");

            control.Pause();
            var stopped = Task.Run(() => { try { Execution.Checkpoint(5, 0); return false; } catch (StopRequestedException) { return true; } });
            Thread.Sleep(40); control.Stop();
            Need(stopped.Wait(500) && stopped.Result, "stop did not interrupt a pause");
        }
        finally { Execution.Detach(); }

        var delayedControl = new RunController();
        Execution.Attach(delayedControl);
        try
        {
            delayedControl.SetDelay(1000);
            var waiting = Task.Run(() => { try { Execution.Checkpoint(6, 0); return false; } catch (StopRequestedException) { return true; } });
            Thread.Sleep(60);
            var stopWatch = Stopwatch.StartNew(); delayedControl.Stop();
            Need(waiting.Wait(400) && waiting.Result && stopWatch.ElapsedMilliseconds < 400, "stop waited for the delay to expire");
        }
        finally { Execution.Detach(); }
    }
}
'''


def test_execution_delay_pause_resume_and_stop(tmp_path: Path) -> None:
    (tmp_path / "Control.csproj").write_text(
        f'''<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0</TargetFramework></PropertyGroup><ItemGroup><ProjectReference Include="{RUNTIME.as_posix()}" /></ItemGroup></Project>''',
        encoding="utf-8",
    )
    (tmp_path / "Program.cs").write_text(PROGRAM, encoding="utf-8")
    build = subprocess.run(["dotnet", "build", "-c", "Release", "--nologo", "-v:q", "-p:NuGetAudit=false"], cwd=tmp_path, text=True, encoding="utf-8", errors="replace", capture_output=True)
    assert build.returncode == 0, build.stdout + build.stderr
    result = subprocess.run(["dotnet", str(tmp_path / "bin" / "Release" / "net10.0" / "Control.dll")], text=True, encoding="utf-8", errors="replace", capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
