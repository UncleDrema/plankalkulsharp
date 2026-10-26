using System.Diagnostics;
using System.IO;

namespace PlankalkulMachine;

// Shared by compilation and AST projection; neither may silently use a Python
// installation which cannot import the compiler.
public static class CompilerPython
{
    public static async Task<bool> IsAvailableAsync(string python)
    {
        try
        {
            var start = new ProcessStartInfo(python) { UseShellExecute = false, CreateNoWindow = true,
                RedirectStandardOutput = true, RedirectStandardError = true };
            foreach (var arg in new[] { "-m", "plankalkulsharp", "--help" }) start.ArgumentList.Add(arg);
            using var process = Process.Start(start);
            if (process is null) return false;
            var output = process.StandardOutput.ReadToEndAsync(); var error = process.StandardError.ReadToEndAsync();
            var exited = process.WaitForExitAsync();
            if (await Task.WhenAny(exited, Task.Delay(3000)) != exited) { process.Kill(true); await exited; return false; }
            await Task.WhenAll(output, error);
            return process.ExitCode == 0;
        }
        catch { return false; }
    }

    public static async Task<string> ResolveAsync(string preferred, params string[] searchRoots)
    {
        if (await IsAvailableAsync(preferred)) return preferred;
        var tried = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { preferred };
        foreach (var root in searchRoots)
        {
            for (var directory = new DirectoryInfo(root); directory is not null; directory = directory.Parent)
            {
                // Only discover the compiler checkout, not arbitrary source-file directories.
                if (!File.Exists(Path.Combine(directory.FullName, "src", "plankalkulsharp", "__main__.py"))) continue;
                var candidate = Path.Combine(directory.FullName, ".venv", "Scripts", "python.exe");
                if (tried.Add(candidate) && File.Exists(candidate) && await IsAvailableAsync(candidate)) return candidate;
            }
        }
        throw new InvalidOperationException($"Python «{preferred}» не запускает модуль plankalkulsharp. " +
            "Нажмите «Python…» и выберите .venv\\Scripts\\python.exe из каталога проекта, " +
            "либо откройте машину командой uv run plankalkulsharp machine.");
    }
}
