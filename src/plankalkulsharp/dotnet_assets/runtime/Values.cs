using System.Globalization;
using System.Reflection;
using System.Text.Json;

namespace PlankalkulRuntime;

/// <summary>Value operations on CLR storage; independent of the explicit @ heap.</summary>
public static class Values
{
    private static FieldInfo[] Fields(Type type) => type.GetFields()
        .Where(f => f.Name.StartsWith("f_", StringComparison.Ordinal))
        .OrderBy(f => int.Parse(f.Name.AsSpan(2), CultureInfo.InvariantCulture)).ToArray();

    public static object Copy(object? value, RuntimeTypeHandle handle, string shape)
    {
        using var document = JsonDocument.Parse(shape);
        try { return CopyValue(value, Type.GetTypeFromHandle(handle)!, document.RootElement); }
        catch (Exception ex) when (ex is ArgumentException or OutOfMemoryException or OverflowException)
        {
            string location = document.RootElement.TryGetProperty("location", out var pos) ? pos.GetString()! : "value";
            throw new ArgumentException($"{location}: {ex.Message}", ex);
        }
    }

    // A fresh container is built before it becomes visible to the caller. Each
    // nested array is copied too; scalar reference handles deliberately stay scalar.
    private static object CopyValue(object? value, Type type, JsonElement shape)
    {
        if (type.IsArray)
        {
            var source = value as Array;
            int? required = shape.GetProperty("size").ValueKind == JsonValueKind.Null
                ? null : shape.GetProperty("size").GetInt32();
            int count = source?.Length ?? required ?? 0;
            if (required is int n && n != count)
                throw new ArgumentException($"list length {count}; expected {n}");
            var element = type.GetElementType()!;
            var result = Array.CreateInstance(element, count);
            for (int i = 0; i < count; i++)
                result.SetValue(CopyValue(source?.GetValue(i), element, shape.GetProperty("element")), i);
            return result;
        }
        var fields = Fields(type);
        if (fields.Length != 0)
        {
            var result = Activator.CreateInstance(type)!;
            var sourceFields = value is null ? null : Fields(value.GetType());
            for (int i = 0; i < fields.Length; i++)
                fields[i].SetValue(result, CopyValue(sourceFields?[i].GetValue(value),
                    fields[i].FieldType, shape.GetProperty("fields")[i]));
            return result;
        }
        if (value is null) return Activator.CreateInstance(type)!;
        if (type == value.GetType()) return value;
        long number = Convert.ToInt64(value, CultureInfo.InvariantCulture);
        if (type == typeof(bool)) return number != 0;
        if (type == typeof(int)) return unchecked((int)number);
        return number;
    }

    public static object Concat(Array left, Array right)
    {
        int count = checked(left.Length + right.Length);
        var result = Array.CreateInstance(left.GetType().GetElementType()!, count);
        Array.Copy(left, result, left.Length);
        Array.Copy(right, 0, result, left.Length, right.Length);
        // The compiler copies the resulting value at its assignment/call boundary.
        return result;
    }

    public static int Index(Array value, long index, string location)
    {
        if (index < 0 || index >= value.Length)
            throw new ArgumentException($"{location}: list index {index} out of range (length {value.Length})");
        return (int)index;
    }

    public static void CheckContract(string contract, object[] args, string location)
    {
        using var document = JsonDocument.Parse(contract);
        var rule = document.RootElement;
        switch (rule.GetProperty("kind").GetString())
        {
            case "equal_length":
                var left = (Array)args[rule.GetProperty("left").GetInt32()];
                var right = (Array)args[rule.GetProperty("right").GetInt32()];
                if (left.Length != right.Length)
                    throw new ArgumentException($"{location}: operation requires equal list lengths");
                break;
            case "position":
                var array = (Array)args[rule.GetProperty("list").GetInt32()];
                long index = Convert.ToInt64(args[rule.GetProperty("index").GetInt32()]);
                bool allowEnd = rule.TryGetProperty("allow_end", out var end) && end.GetBoolean();
                if (index < 0 || index >= (long)array.Length + (allowEnd ? 1 : 0))
                    throw new ArgumentException($"{location}: position {index} out of range");
                break;
            default: throw new ArgumentException("unknown standard-plan contract");
        }
    }

    public static object Parse(string text, RuntimeTypeHandle handle, string shape)
    {
        using var input = JsonDocument.Parse(text);
        using var descriptor = JsonDocument.Parse(shape);
        return Read(input.RootElement, Type.GetTypeFromHandle(handle)!, descriptor.RootElement);
    }

    private static object Read(JsonElement input, Type type, JsonElement shape)
    {
        if (type.IsArray)
        {
            int count = input.GetArrayLength();
            var expected = shape.GetProperty("size");
            if (expected.ValueKind != JsonValueKind.Null && expected.GetInt32() != count)
                throw new ArgumentException($"list length {count}; expected {expected.GetInt32()}");
            var result = Array.CreateInstance(type.GetElementType()!, count);
            for (int i = 0; i < count; i++)
                result.SetValue(Read(input[i], type.GetElementType()!, shape.GetProperty("element")), i);
            return result;
        }
        var fields = Fields(type);
        if (fields.Length != 0)
        {
            if (input.GetArrayLength() != fields.Length)
                throw new ArgumentException($"record requires {fields.Length} fields");
            var result = Activator.CreateInstance(type)!;
            for (int i = 0; i < fields.Length; i++)
                fields[i].SetValue(result, Read(input[i], fields[i].FieldType, shape.GetProperty("fields")[i]));
            return result;
        }
        if (shape.TryGetProperty("reference", out _))
            throw new ArgumentException("references cannot be supplied as program arguments");
        if (type == typeof(bool))
        {
            if (input.ValueKind == JsonValueKind.True) return true;
            if (input.ValueKind == JsonValueKind.False) return false;
            int bit = input.GetInt32();
            if (bit is not (0 or 1)) throw new ArgumentException("bit must be 0 or 1");
            return bit == 1;
        }
        if (type == typeof(int)) return input.GetInt32();
        return input.GetInt64();
    }

    public static string Format(object value) => JsonSerializer.Serialize(Printable(value));

    private static object Printable(object value)
    {
        if (value is Array array) return array.Cast<object>().Select(Printable).ToArray();
        var fields = Fields(value.GetType());
        if (fields.Length != 0) return fields.Select(f => Printable(f.GetValue(value)!)).ToArray();
        return value is bool bit ? (object)(bit ? 1 : 0) : value;
    }

    public static bool Equal(object? left, object? right)
    {
        if (left is Array a && right is Array b)
        {
            if (a.Length != b.Length) return false;
            for (int i = 0; i < a.Length; i++)
                if (!Equal(a.GetValue(i), b.GetValue(i))) return false;
            return true;
        }
        if (left is null || right is null) return left is null && right is null;
        var lf = Fields(left.GetType());
        var rf = Fields(right.GetType());
        if (lf.Length != 0 || rf.Length != 0)
            return lf.Length == rf.Length && lf.Zip(rf).All(p => Equal(p.First.GetValue(left), p.Second.GetValue(right)));
        return Convert.ToInt64(left, CultureInfo.InvariantCulture) == Convert.ToInt64(right, CultureInfo.InvariantCulture);
    }
}
