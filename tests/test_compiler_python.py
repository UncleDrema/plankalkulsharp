"""Exercise interpreter selection and actual notation subprocesses without WPF."""
import subprocess
import venv
from pathlib import Path
from xml.sax.saxutils import escape


def test_compiler_python_fallback(tmp_path):
    root = Path(__file__).parents[1]
    helper = root / "src/plankalkulsharp/dotnet_assets/desktop/CompilerPython.cs"
    # This is a real Python installation without plankalkulsharp, like system Python.
    venv.EnvBuilder(with_pip=False).create(tmp_path / "empty-python")
    empty_python = tmp_path / "empty-python/Scripts/python.exe"
    (tmp_path / "global.json").write_text('{"sdk":{"version":"10.0.100","rollForward":"latestFeature"}}')
    (tmp_path / "Check.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType>'
        '<TargetFramework>net10.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings>'
        '</PropertyGroup><ItemGroup>'
        f'<Compile Include="{escape(str(helper))}"/>'
        '</ItemGroup></Project>', encoding="utf-8")
    (tmp_path / "Program.cs").write_text(r'''
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using PlankalkulMachine;
if (await CompilerPython.IsAvailableAsync(args[0])) throw new Exception("Empty Python unexpectedly has compiler");
var expected = Path.Combine(args[1], ".venv", "Scripts", "python.exe");
var resolved = await CompilerPython.ResolveAsync(args[0], Path.Combine(args[1], "src", "plankalkulsharp"));
if (resolved != expected) throw new Exception("Checkout interpreter was not selected");
if (await CompilerPython.ResolveAsync(expected, Environment.CurrentDirectory) != expected)
    throw new Exception("Explicit valid interpreter must win");
try {
    await CompilerPython.ResolveAsync(args[0], Environment.CurrentDirectory);
    throw new Exception("Missing compiler was accepted");
} catch (InvalidOperationException ex) {
    if (!ex.Message.Contains("Python…") || !ex.Message.Contains(args[0])) throw;
}
var start = new ProcessStartInfo(resolved) { RedirectStandardInput = true,
    RedirectStandardOutput = true, RedirectStandardError = true, UseShellExecute = false,
    CreateNoWindow = true, StandardInputEncoding = new UTF8Encoding(false) };
foreach (var arg in new[] { "-m", "plankalkulsharp", "notation", "--stdin" }) start.ArgumentList.Add(arg);
start.Environment["PYTHONIOENCODING"] = "utf-8";
using var process = Process.Start(start)!;
var output = process.StandardOutput.ReadToEndAsync(); var error = process.StandardError.ReadToEndAsync();
await process.StandardInput.WriteAsync("// Проверка\nP0 f(V0[:32.0]) -> R0[:32.0]\nV0 + 1 => R0\nEND");
process.StandardInput.Close();
await process.WaitForExitAsync();
if (process.ExitCode != 0) throw new Exception(await error);
using var document = JsonDocument.Parse(await output);
if (!document.RootElement.GetProperty("rows").EnumerateArray().Any(r => r.GetProperty("kind").GetString() == "Assignment"))
    throw new Exception("Notation subprocess did not produce AST rows");
''', encoding="utf-8")
    result = subprocess.run(
        ["dotnet", "run", "--project", str(tmp_path / "Check.csproj"),
         "-p:NuGetAudit=false", "-v:q", "--", str(empty_python), str(root)],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
