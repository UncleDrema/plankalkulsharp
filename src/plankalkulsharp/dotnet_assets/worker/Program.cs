using System.IO.Pipes;
using System.Reflection;
using System.Runtime.ExceptionServices;
using System.Text;
using System.Text.Json;
using PlankalkulRuntime;

namespace PlankalkulWorker;

internal static class Program
{
    private const int DefaultHeap = 1024 * 1024;

    public static async Task<int> Main(string[] args)
    {
        try
        {
            var options = WorkerOptions.Parse(args);
            return options.Pipe is null
                ? await RunConsole(options)
                : await RunPipe(options);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"worker: {ex.Message}");
            return 1;
        }
    }

    private static async Task<int> RunConsole(WorkerOptions options)
    {
        var controller = new RunController();
        ConsoleCancelEventHandler cancel = (_, eventArgs) => { eventArgs.Cancel = true; controller.Stop(); };
        Console.CancelKeyPress += cancel;
        try
        {
            _ = ReadMetadata(options.Module);
            Heap.Initialize();
            Execution.Attach(controller);
            return Invoke(options.Module, options.Arguments);
        }
        catch (MemoryFault fault) { Heap.Report(fault); return 1; }
        catch (StopRequestedException) { return 130; }
        catch (Exception ex) { Console.Error.WriteLine($"worker: {ex.Message}"); return 1; }
        finally { Console.CancelKeyPress -= cancel; Execution.Detach(); Heap.Shutdown(); }
    }

    private static async Task<int> RunPipe(WorkerOptions options)
    {
        using var pipe = new NamedPipeClientStream(".", options.Pipe!, PipeDirection.InOut, PipeOptions.Asynchronous);
        await pipe.ConnectAsync(5_000);
        using var reader = new StreamReader(pipe, Encoding.UTF8, false, 4096, true);
        using var writer = new StreamWriter(pipe, new UTF8Encoding(false), 4096, true) { AutoFlush = true };
        await using var events = new EventWriter(writer);
        await events.Reliable(new { version = Protocol.Version, @event = "state", state = "waiting", line = 0, column = 0, timestampUtc = DateTimeOffset.UtcNow });

        var first = await ReadCommand(reader);
        if (first?.Version != Protocol.Version || first.Command != "start")
        {
            await events.Reliable(new { version = Protocol.Version, @event = "diagnostic", message = "first pipe command must be start" });
            return 1;
        }
        var heapSize = first.HeapSize ?? DefaultHeap;
        if (heapSize <= 0 || heapSize % 8 != 0)
        {
            await events.Reliable(new { version = Protocol.Version, @event = "diagnostic", message = "heapSize must be a positive multiple of 8" });
            await events.Reliable(new { version = Protocol.Version, @event = "completed", exitCode = 1, forced = false, timestampUtc = DateTimeOffset.UtcNow });
            return 1;
        }
        ModuleMetadata metadata;
        try { metadata = ReadMetadata(options.Module); }
        catch (Exception ex)
        {
            await events.Reliable(new { version = Protocol.Version, @event = "diagnostic", message = Unwrap(ex).Message });
            await events.Reliable(new { version = Protocol.Version, @event = "completed", exitCode = 1, forced = false, timestampUtc = DateTimeOffset.UtcNow });
            return 1;
        }
        var controller = new RunController();
        try { controller.SetDelay(first.DelayMs ?? 0); }
        catch (ArgumentOutOfRangeException)
        {
            await events.Reliable(new { version = Protocol.Version, @event = "diagnostic", message = "delayMs must be 0..1000" });
            await events.Reliable(new { version = Protocol.Version, @event = "completed", exitCode = 1, forced = false, timestampUtc = DateTimeOffset.UtcNow });
            return 1;
        }
        if (first.StartPaused) controller.Pause();
        long sequence = 0;
        void State(string state, int line, int column) => events.TrySend(new { version = Protocol.Version, @event = "state", state, line, column, timestampUtc = DateTimeOffset.UtcNow });
        void Snapshot(int line, int column, bool exact)
        {
            using var process = System.Diagnostics.Process.GetCurrentProcess();
            var revision = Interlocked.Increment(ref sequence);
            // Bytes and ownership travel together, including when a slow UI skips snapshots.
            var page = exact || controller.DelayMs > 0 ? Heap.InspectPage(controller.HeapOffset) : null;
            events.TrySend(new { version = Protocol.Version, @event = "snapshot", sequence = revision, exact, line, column,
                timestampUtc = DateTimeOffset.UtcNow, snapshot = Heap.Snapshot(),
                process = new { workingSetBytes = process.WorkingSet64, cpuMilliseconds = process.TotalProcessorTime.TotalMilliseconds },
                heapPage = page is null ? null : new { offset = page.Offset, size = page.Size, bytes = page.Bytes, snapshotSequence = revision }
            }, snapshot: !exact);
        }
        controller.StateChanged += State;
        controller.SnapshotRequested += Snapshot;
        controller.InspectionRequested += handle => Inspect(handle, metadata, events, sequence);
        controller.HeapInspectionRequested += offset =>
        {
            var page = Heap.InspectPage(offset);
            events.TrySend(new { version = Protocol.Version, @event = "heapPage", snapshotSequence = sequence, offset = page.Offset, size = page.Size, bytes = page.Bytes });
        };

        var originalOut = Console.Out;
        var originalErr = Console.Error;
        Console.SetOut(new EventTextWriter("stdout", events));
        Console.SetError(new EventTextWriter("stderr", events));
        var runTask = Task.Run(() =>
        {
            try
            {
                Heap.Initialize(new HeapOptions(heapSize, true, false, memory => events.TrySend(new { version = Protocol.Version, @event = "memory", text = memory }, memory: true)));
                Execution.Attach(controller);
                State("running", 0, 0);
                var result = Invoke(options.Module, first.Arguments ?? options.Arguments, metadata);
                return result;
            }
            finally
            {
                // The final consistent view is emitted before Shutdown releases native memory.
                Snapshot(controller.LastLine, controller.LastColumn, true);
                Execution.Detach();
                Heap.Shutdown();
            }
        });
        var completed = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var receiver = ReceiveCommands(reader, controller, events, async () =>
        {
            // An uncooperative module is isolated in this Worker process only.
            if (await Task.WhenAny(completed.Task, Task.Delay(2_000)) != completed.Task)
                Environment.Exit(130);
        });
        var exit = 1;
        try { exit = await runTask; }
        catch (MemoryFault fault) { await events.Reliable(new { version = Protocol.Version, @event = "diagnostic", message = fault.Message }); }
        catch (StopRequestedException) { exit = 130; }
        catch (Exception ex) { await events.Reliable(new { version = Protocol.Version, @event = "diagnostic", message = Unwrap(ex).Message }); }
        finally
        {
            controller.Stop();
            completed.TrySetResult();
            Console.SetOut(originalOut);
            Console.SetError(originalErr);
        }
        await events.Reliable(new { version = Protocol.Version, @event = "completed", exitCode = exit, forced = false, timestampUtc = DateTimeOffset.UtcNow });
        return exit;
    }

    private static async Task ReceiveCommands(StreamReader reader, RunController controller, EventWriter events, Func<Task> onPipeLoss)
    {
        try
        {
            while (await ReadCommand(reader) is { } command)
            {
                if (command.Version != Protocol.Version) { events.TrySend(new { version = Protocol.Version, @event = "diagnostic", message = "unsupported protocol version" }); continue; }
                switch (command.Command)
                {
                    case "pause": controller.Pause(); break;
                    case "resume": controller.Resume(); break;
                    case "step": controller.Step(); break;
                    case "stop": controller.Stop(); break;
                    case "delay": if (command.DelayMs is >= 0 and <= 1000) controller.SetDelay(command.DelayMs.Value); else events.TrySend(new { version = Protocol.Version, @event = "diagnostic", message = "delayMs must be 0..1000" }); break;
                    case "inspect":
                        if (command.Handle is not null && !controller.RequestInspect(command.Handle))
                            await events.Reliable(new { version = Protocol.Version, @event = "inspection", handle = command.Handle, snapshotSequence = 0L, message = "inspection is available only while paused", fields = Array.Empty<HeapValue>() });
                        break;
                    case "inspectHeap":
                        if (command.Offset is not { } offset || offset < 0 || !controller.RequestHeapInspect(offset))
                            await events.Reliable(new { version = Protocol.Version, @event = "diagnostic", message = "heap offset must be nonnegative" });
                        break;
                }
            }
            controller.Stop(); // GUI disappeared: request a cooperative exit.
            _ = onPipeLoss();
        }
        catch { controller.Stop(); _ = onPipeLoss(); }
    }

    private static void Inspect(string handle, ModuleMetadata metadata, EventWriter events, long sequence)
    {
        if (!long.TryParse(handle, out var value))
        {
            events.TrySend(new { version = Protocol.Version, @event = "inspection", handle, snapshotSequence = sequence, message = "invalid handle", fields = Array.Empty<HeapValue>() });
            return;
        }
        var obj = Heap.Snapshot().Objects.FirstOrDefault(item => item.Handle == handle);
        var fields = obj is not null && metadata.Types.TryGetValue(obj.TypeId, out var layout)
            ? FlattenFields(layout, 0, "")
            : Array.Empty<HeapField>();
        var inspection = Heap.Inspect(value, fields);
        events.TrySend(new { version = Protocol.Version, @event = "inspection", handle, snapshotSequence = sequence, fields = inspection.Fields });
    }

    private static int Invoke(string module, string[] args, ModuleMetadata? validated = null)
    {
        var assembly = Assembly.LoadFrom(Path.GetFullPath(module));
        var type = assembly.GetType("PlankalkulProgram") ?? throw new InvalidOperationException("module does not define PlankalkulProgram");
        _ = validated ?? ReadMetadata(assembly, type);
        var execute = type.GetMethod("Execute", BindingFlags.Public | BindingFlags.Static) ?? throw new InvalidOperationException("module does not define Execute");
        var executeParameters = execute.GetParameters();
        if (execute.ReturnType != typeof(void) || executeParameters.Length != 1 || executeParameters[0].ParameterType != typeof(string[]))
            throw new InvalidOperationException("module Execute signature is incompatible; rebuild the program");
        try
        {
            var result = execute.Invoke(null, [args]);
            // ABI 1 uses void Execute; accepting an int here keeps early modules usable.
            return result is int exitCode ? exitCode : 0;
        }
        catch (TargetInvocationException ex) when (ex.InnerException is not null) { ExceptionDispatchInfo.Capture(ex.InnerException).Throw(); throw; }
    }

    private static ModuleMetadata ReadMetadata(string module)
    {
        var assembly = Assembly.LoadFrom(Path.GetFullPath(module));
        var type = assembly.GetType("PlankalkulProgram") ?? throw new InvalidOperationException("module does not define PlankalkulProgram");
        return ReadMetadata(assembly, type);
    }

    private static ModuleMetadata ReadMetadata(Assembly assembly, Type type)
    {
        try
        {
            var getter = type.GetMethod("GetMetadata", BindingFlags.Public | BindingFlags.Static) ?? throw new InvalidOperationException("module does not define GetMetadata");
            if (getter.ReturnType != typeof(string) || getter.GetParameters().Length != 0) throw new InvalidOperationException("module GetMetadata signature is incompatible; rebuild the program");
            using var document = JsonDocument.Parse((string?)getter.Invoke(null, null) ?? "");
            if (!document.RootElement.TryGetProperty("abi", out var abi) || abi.GetInt32() != Protocol.Version)
                throw new InvalidOperationException("module ABI is incompatible; rebuild the program");
            var types = new Dictionary<int, Layout>();
            if (document.RootElement.TryGetProperty("heapTypes", out var heapTypes))
                foreach (var item in heapTypes.EnumerateArray())
                    types.Add(item.GetProperty("id").GetInt32(), Layout.Parse(item.GetProperty("layout")));
            foreach (var layout in types.Values) ValidateLayout(layout, types);
            return new ModuleMetadata(types);
        }
        catch (JsonException) { throw new InvalidOperationException("module metadata is invalid; rebuild the program"); }
    }

    private static async Task<CommandEnvelope?> ReadCommand(StreamReader reader)
    {
        var line = await reader.ReadLineAsync();
        if (line is null) return null;
        return JsonSerializer.Deserialize<CommandEnvelope>(line, Protocol.Json);
    }

    private static Exception Unwrap(Exception ex) => ex is AggregateException aggregate ? aggregate.GetBaseException() : ex;

    private static HeapField[] FlattenFields(Layout layout, int baseOffset, string path)
    {
        if (layout.Kind != "record") return [new HeapField(path, baseOffset, layout.Size, layout.Kind, layout.TargetTypeId)];
        return layout.Fields.SelectMany(field => FlattenFields(field.Layout, baseOffset + field.Offset,
            string.IsNullOrEmpty(path) ? field.Index.ToString() : $"{path}.{field.Index}")).ToArray();
    }

    private static void ValidateLayout(Layout layout, IReadOnlyDictionary<int, Layout> types)
    {
        if (layout.Kind is not ("bit" or "int32" or "int64" or "ref" or "record"))
            throw new InvalidOperationException("module layout has an unknown kind");
        if (layout.Kind == "bit" && layout.Size != 1 || layout.Kind == "int32" && layout.Size != 4 || layout.Kind == "int64" && layout.Size != 8 || layout.Kind == "ref" && (layout.Size != 8 || layout.TargetTypeId is null || !types.ContainsKey(layout.TargetTypeId.Value)))
            throw new InvalidOperationException("module layout is incompatible");
        var used = new HashSet<int>();
        foreach (var field in layout.Fields)
        {
            if (!used.Add(field.Index) || field.Offset < 0 || field.Offset > layout.Size - field.Layout.Size)
                throw new InvalidOperationException("module record field is outside its layout");
            ValidateLayout(field.Layout, types);
        }
    }
}

internal sealed record ModuleMetadata(IReadOnlyDictionary<int, Layout> Types);
internal sealed record Layout(string Kind, int Size, int? TargetTypeId, IReadOnlyList<LayoutField> Fields)
{
    public static Layout Parse(JsonElement value)
    {
        var kind = value.GetProperty("kind").GetString() ?? throw new InvalidOperationException("layout kind missing");
        var size = value.GetProperty("size").GetInt32();
        if (size is < 1 or > int.MaxValue) throw new InvalidOperationException("layout size is invalid");
        int? target = value.TryGetProperty("targetTypeId", out var targetValue) ? targetValue.GetInt32() : null;
        var fields = new List<LayoutField>();
        if (value.TryGetProperty("fields", out var values))
            foreach (var field in values.EnumerateArray())
                fields.Add(new LayoutField(field.GetProperty("index").GetInt32(), field.GetProperty("offset").GetInt32(), Parse(field.GetProperty("layout"))));
        return new Layout(kind, size, target, fields);
    }
}
internal sealed record LayoutField(int Index, int Offset, Layout Layout);

internal sealed class EventWriter : IAsyncDisposable
{
    // One ordered queue preserves output-before-completed. Only a pending live
    // snapshot is replaceable; memory trace events are capped separately.
    private readonly LinkedList<string> _queue = [];
    private LinkedListNode<string>? _pendingSnapshot;
    private readonly SemaphoreSlim _signal = new(0);
    private readonly object _gate = new();
    private bool _complete;
    private int _memoryCount;
    private long _droppedMemory;
    private readonly Task _writer;
    public EventWriter(StreamWriter writer) => _writer = Task.Run(async () =>
    {
        while (true)
        {
            await _signal.WaitAsync();
            string? line;
            lock (_gate)
            {
                var item = _queue.First;
                line = item?.Value;
                if (item is not null)
                {
                    if (item == _pendingSnapshot) _pendingSnapshot = null;
                    _queue.RemoveFirst();
                }
                if (line is null && _complete) return;
            }
            if (line is not null) await writer.WriteLineAsync(line);
        }
    });
    public void TrySend(object value, bool snapshot = false, bool memory = false)
    {
        var line = Protocol.Encode(value);
        var added = true;
        lock (_gate)
        {
            if (memory && _memoryCount >= 5_000) { _droppedMemory++; return; }
            if (snapshot && _pendingSnapshot is not null)
            {
                // Move the replacement to its chronological position. Updating the
                // old slot could send a newer revision ahead of an exact pause view.
                _queue.Remove(_pendingSnapshot);
                added = false;
            }
            var item = _queue.AddLast(line);
            if (snapshot) _pendingSnapshot = item;
            if (memory) _memoryCount++;
        }
        if (added) _signal.Release();
    }
    public Task Reliable(object value)
    {
        var line = Protocol.Encode(value);
        lock (_gate)
        {
            // The terminal event must remain last. Publish the accounting marker
            // immediately before it, rather than from DisposeAsync afterwards.
            if (line.Contains("\"event\":\"completed\"", StringComparison.Ordinal) && _droppedMemory > 0)
            {
                _queue.AddLast(Protocol.Encode(new { version = Protocol.Version, @event = "memory", text = $"[memory events dropped: {_droppedMemory}]", droppedCount = _droppedMemory }));
                _droppedMemory = 0;
                _signal.Release();
            }
            _queue.AddLast(line);
        }
        _signal.Release();
        return Task.CompletedTask;
    }
    public async ValueTask DisposeAsync()
    {
        lock (_gate)
        {
            _complete = true;
        }
        _signal.Release();
        await _writer;
        _signal.Dispose();
    }
}

internal sealed class EventTextWriter(string stream, EventWriter events) : TextWriter
{
    private const int Limit = 1024 * 1024;
    private int _written;
    private bool _truncated;
    public override Encoding Encoding => Encoding.UTF8;
    public override void Write(char value) => Write(value.ToString());
    public override void Write(char[] buffer, int index, int count) => Write(new string(buffer, index, count));
    public override void Write(string? value)
    {
        if (string.IsNullOrEmpty(value) || _truncated) return;
        var room = Limit - _written;
        if (room <= 0) { _truncated = true; events.TrySend(new { version = Protocol.Version, @event = "output", stream, text = "\n[output truncated]\n", truncated = true }); return; }
        var bytes = Encoding.UTF8.GetByteCount(value);
        var length = value.Length;
        if (bytes > room)
        {
            bytes = 0; length = 0;
            foreach (var rune in value.EnumerateRunes())
            {
                if (bytes + rune.Utf8SequenceLength > room) break;
                bytes += rune.Utf8SequenceLength; length += rune.Utf16SequenceLength;
            }
        }
        var text = value[..length];
        _written += bytes;
        events.TrySend(new { version = Protocol.Version, @event = "output", stream, text });
        if (text.Length != value.Length) { _truncated = true; events.TrySend(new { version = Protocol.Version, @event = "output", stream, text = "\n[output truncated]\n", truncated = true }); }
    }
}

internal sealed record WorkerOptions(string Module, string? Pipe, string[] Arguments)
{
    public static WorkerOptions Parse(string[] args)
    {
        string? module = null, pipe = null;
        var values = new List<string>();
        for (var i = 0; i < args.Length; i++)
        {
            if (args[i] == "--") { values.AddRange(args[(i + 1)..]); break; }
            if (args[i] == "--module" && ++i < args.Length) module = args[i];
            else if (args[i] == "--pipe" && ++i < args.Length) pipe = args[i];
            else throw new ArgumentException("usage: PlankalkulWorker --module PATH [--pipe NAME] -- args");
        }
        if (string.IsNullOrWhiteSpace(module) || !File.Exists(module)) throw new ArgumentException("--module must name an existing DLL");
        return new WorkerOptions(module, pipe, [.. values]);
    }
}
