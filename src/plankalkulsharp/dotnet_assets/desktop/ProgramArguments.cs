using System.Text;
using System.Text.Json;

namespace PlankalkulMachine;

internal static class ProgramArguments
{
    // JSON values are separated by whitespace, while spaces inside arrays stay
    // inside that argument. The compiler's declared parameter types do validation.
    public static string[] Parse(string text)
    {
        var bytes = Encoding.UTF8.GetBytes(text);
        var values = new List<string>();
        int offset = 0;
        while (offset < bytes.Length)
        {
            while (offset < bytes.Length && bytes[offset] is 9 or 10 or 13 or 32) offset++;
            if (offset == bytes.Length) break;
            var reader = new Utf8JsonReader(bytes.AsSpan(offset), isFinalBlock: true, state: default);
            using var value = JsonDocument.ParseValue(ref reader);
            values.Add(value.RootElement.GetRawText());
            offset += checked((int)reader.BytesConsumed);
            if (offset < bytes.Length && bytes[offset] is not (9 or 10 or 13 or 32))
                throw new FormatException("Разделяйте аргументы пробелами.");
        }
        return values.ToArray();
    }
}
