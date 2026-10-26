namespace PlankalkulMachine;

public sealed record MachineOptions(string? Python, string? Worker, string? Source)
{
    public static MachineOptions Parse(string[] args)
    {
        string? python = null, worker = null, source = null;
        for (var i = 0; i < args.Length; i++)
        {
            if (args[i] is "--python" && ++i < args.Length) python = args[i];
            else if (args[i] is "--worker" && ++i < args.Length) worker = args[i];
            else if (args[i] is "--source" && ++i < args.Length) source = args[i];
        }
        return new(python, worker, source);
    }
}
