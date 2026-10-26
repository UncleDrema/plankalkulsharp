using System.Text.Json;
using System.Text.Json.Serialization;

namespace PlankalkulRuntime;

/// <summary>Versioned JSON-line contract shared by the Worker and the WPF monitor.</summary>
public static class Protocol
{
    public const int Version = 1;
    public static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };
    public static string Encode(object value) => JsonSerializer.Serialize(value, Json);
}

public sealed record HeapOptions(int Size = 1024 * 1024, bool Stats = false, bool Trace = false, Action<string>? EventSink = null);
public sealed record HeapStats(long Allocations, long Frees, int UsedBytes, int FreeBytes, int PeakUsedBytes, int LargestFreeBlock, int LiveCount);
public sealed record HeapBlock(int Offset, int Size, bool Free);
public sealed record HeapObject(string Handle, int TypeId, string TypeName, int Offset, int Size, int ReservedSize, string Location);
public sealed record HeapSnapshot(HeapStats Stats, IReadOnlyList<HeapBlock> Blocks, IReadOnlyList<HeapObject> Objects);
public sealed record HeapField(string Path, int Offset, int Size, string Kind, int? TargetTypeId = null);
public sealed record HeapValue(string Path, string Kind, string Value, string? TargetHandle = null, int? TargetTypeId = null);
public sealed record HeapInspection(string Handle, IReadOnlyList<HeapValue> Fields);
public sealed record HeapPage(int Offset, int Size, IReadOnlyList<byte?> Bytes);

public sealed class CommandEnvelope
{
    public int Version { get; init; }
    public string Command { get; init; } = "";
    public int? HeapSize { get; init; }
    public int? DelayMs { get; init; }
    public bool StartPaused { get; init; }
    public string[]? Arguments { get; init; }
    public string? Handle { get; init; }
    public int? Offset { get; init; }
}
