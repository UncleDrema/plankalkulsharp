using System.Threading;
using System.Collections.Concurrent;
using System.Diagnostics;

namespace PlankalkulRuntime;

/// <summary>Cooperative execution controls injected by the Worker around generated statements.</summary>
public static class Execution
{
    private static RunController? _controller;

    public static void Attach(RunController controller) => _controller = controller;
    public static void Detach() => _controller = null;
    public static void Checkpoint(int line, int column) => _controller?.Checkpoint(line, column);
}

public sealed class StopRequestedException : Exception { }

public sealed class RunController
{
    private readonly AutoResetEvent _changed = new(false);
    private readonly object _gate = new();
    private bool _pause;
    private bool _step;
    private bool _stop;
    private int _delayMs;
    private int _heapOffset;
    public int DelayMs => Volatile.Read(ref _delayMs);
    public int HeapOffset => Volatile.Read(ref _heapOffset);
    private readonly ConcurrentQueue<string> _inspections = [];
    private readonly ConcurrentQueue<int> _heapInspections = [];
    private long _lastSnapshotTick;

    public event Action<string, int, int>? StateChanged;
    public event Action<int, int, bool>? SnapshotRequested;
    public event Action<string>? InspectionRequested;
    public event Action<int>? HeapInspectionRequested;
    public bool IsPaused { get; private set; }
    public int LastLine { get; private set; }
    public int LastColumn { get; private set; }

    public void Pause()
    {
        lock (_gate) _pause = true;
        _changed.Set();
    }

    public void Resume()
    {
        lock (_gate) { _pause = false; _step = false; }
        _changed.Set();
    }

    // Release exactly this checkpoint, then pause at the next one. Requests
    // while running are ignored rather than queued as unexpected future steps.
    public void Step()
    {
        lock (_gate) { if (!IsPaused) return; _step = true; }
        _changed.Set();
    }

    public void Stop()
    {
        lock (_gate) _stop = true;
        _changed.Set();
        StateChanged?.Invoke("stopping", LastLine, LastColumn);
    }

    public void SetDelay(int milliseconds)
    {
        if (milliseconds is < 0 or > 1000) throw new ArgumentOutOfRangeException(nameof(milliseconds));
        lock (_gate) _delayMs = milliseconds;
        _changed.Set();
    }

    public bool RequestInspect(string handle)
    {
        if (!IsPaused)
            return false;
        _inspections.Enqueue(handle);
        _changed.Set();
        return true;
    }

    public bool RequestHeapInspect(int offset)
    {
        if (offset < 0) return false;
        Volatile.Write(ref _heapOffset, offset);
        if (IsPaused) _heapInspections.Enqueue(offset);
        _changed.Set();
        return true;
    }

    public void Checkpoint(int line, int column)
    {
        LastLine = line;
        LastColumn = column;
        if (Volatile.Read(ref _stop)) throw new StopRequestedException();
        var now = Stopwatch.GetTimestamp();
        var delay = DelayMs;
        if (delay > 0 || now - Interlocked.Read(ref _lastSnapshotTick) >= Stopwatch.Frequency / 5)
        {
            Interlocked.Exchange(ref _lastSnapshotTick, now);
            SnapshotRequested?.Invoke(line, column, false);
        }
        var deadline = Environment.TickCount64 + delay;
        while (delay > 0 && !Volatile.Read(ref _pause))
        {
            if (Volatile.Read(ref _stop)) throw new StopRequestedException();
            var remaining = deadline - Environment.TickCount64;
            if (remaining <= 0) break;
            _changed.WaitOne((int)Math.Min(remaining, 50));
        }
        if (Volatile.Read(ref _stop)) throw new StopRequestedException();

        if (!Volatile.Read(ref _pause)) return;
        IsPaused = true;
        StateChanged?.Invoke("paused", line, column);
        SnapshotRequested?.Invoke(line, column, true);
        while (Volatile.Read(ref _pause))
        {
            while (_inspections.TryDequeue(out var handle)) InspectionRequested?.Invoke(handle);
            while (_heapInspections.TryDequeue(out var offset)) HeapInspectionRequested?.Invoke(offset);
            lock (_gate)
            {
                if (_step) { _step = false; IsPaused = false; break; }
            }
            _changed.WaitOne(50);
            if (Volatile.Read(ref _stop)) throw new StopRequestedException();
        }
        IsPaused = false;
        StateChanged?.Invoke("running", LastLine, LastColumn);
    }
}
