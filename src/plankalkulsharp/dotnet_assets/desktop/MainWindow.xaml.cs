using System.Collections.ObjectModel;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
using Microsoft.Win32;

namespace PlankalkulMachine;

public partial class MainWindow : Window
{
    const int MaxText = 1_048_576;
    readonly MachineOptions _options;
    readonly ObservableCollection<RunRecord> _runs = [];
    string? _sourcePath;
    string _python;
    bool _closing;
    bool _closePending;
    bool _updatingObjects;
    readonly System.Windows.Threading.DispatcherTimer _clock = new() { Interval = TimeSpan.FromMilliseconds(250) };

    public MainWindow(MachineOptions options)
    {
        InitializeComponent();
        SourceBox.AddHandler(ScrollViewer.ScrollChangedEvent,
            new ScrollChangedEventHandler((_, _) => DrawSourceHighlight()));
        SourceBox.SizeChanged += (_, _) => DrawSourceHighlight();
        System.ComponentModel.DependencyPropertyDescriptor.FromProperty(
            System.Windows.Controls.Primitives.TextBoxBase.SelectionBrushProperty, typeof(TextBox))
            .AddValueChanged(SourceBox, (_, _) => DrawSourceHighlight());
        var workArea = SystemParameters.WorkArea;
        Width = Math.Min(Width, workArea.Width); Height = Math.Min(Height, workArea.Height);
        Left = workArea.Left + (workArea.Width - Width) / 2; Top = workArea.Top + (workArea.Height - Height) / 2;
        _options = options;
        _python = options.Python ?? LoadPython() ?? "python";
        RunsList.ItemsSource = _runs;
        _clock.Tick += (_, _) => { foreach (var item in _runs) { item.SampleProcess(); item.RefreshTitle(); } RunsList.Items.Refresh(); if (Current() is { } selected) Show(selected); };
        _clock.Start();
        CleanupOldSessions();
        InitializeNavigation();
        if (options.Source is not null) LoadSource(options.Source);
        Loaded += (_, _) => _ = LoadNotationAsync();
        SetButtons();
    }

    void Help_Click(object sender, RoutedEventArgs e)
    {
        bool show = HelpHost.Visibility != Visibility.Visible;
        if (show) HelpHost.Content ??= new LanguageHelp();
        LibraryHost.Visibility = Visibility.Collapsed;
        HelpHost.Visibility = show ? Visibility.Visible : Visibility.Collapsed;
        WorkspacePanel.Visibility = show ? Visibility.Collapsed : Visibility.Visible;
        HelpButton.Content = show ? "К программе" : "Справка по языку";
        SetButtons();
    }

    void Open_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog { Filter = "Программы Plankalkül (*.pk)|*.pk", CheckFileExists = true };
        if (dialog.ShowDialog(this) == true) LoadSource(dialog.FileName);
    }
    async void Python_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog { Filter = "Python (python.exe)|python.exe|Исполняемые файлы (*.exe)|*.exe", CheckFileExists = true };
        if (dialog.ShowDialog(this) == true)
        {
            try
            {
                if (!await CompilerPython.IsAvailableAsync(dialog.FileName)) { MessageBox.Show(this, "Этот Python не запускает plankalkulsharp.", Title); return; }
                _python = dialog.FileName; File.WriteAllText(SettingsPath(), _python); Append(DiagnosticBox, $"Выбран Python: {_python}\n");
                _notationSource = null;
                _ = LoadNotationAsync();
            }
            catch (Exception ex) { MessageBox.Show(this, "Не удалось сохранить настройку Python: " + ex.Message, Title); }
        }
    }
    void LoadSource(string path)
    {
        if (!path.EndsWith(".pk", StringComparison.OrdinalIgnoreCase)) { MessageBox.Show(this, "Поддерживаются только исходные файлы .pk.", Title); return; }
        try
        {
            var absolute = Path.GetFullPath(path); var text = File.ReadAllText(absolute);
            _sourcePath = absolute; RunsList.SelectedItem = null; SourceBox.Text = text; StatusText.Text = absolute;
            OutputBox.Clear(); DiagnosticBox.Clear(); MemoryBox.Clear(); StatsText.Text = "Нет запуска";
            HexDumpBox.Document.Blocks.Clear();
            _renderedHeap = default;
            MemoryMap.ItemsSource = null; ObjectsGrid.ItemsSource = null; InspectorGrid.ItemsSource = null; DiagnosticsList.ItemsSource = null; DrawMap(null);
            RememberSource(absolute);
        }
        catch (Exception ex) { MessageBox.Show(this, ex.Message, Title); }
    }
    async void Run_Click(object sender, RoutedEventArgs e)
    {
        if (_sourcePath is null) { MessageBox.Show(this, "Сначала откройте программу .pk.", Title); return; }
        ShowWorkspace();
        if (!TrySettings(out var heap, out var delay, out var args)) return;
        var run = new RunRecord(Path.GetFileName(_sourcePath), SourceBox.Text, _sourcePath) { State = "сборка", HeapSize = heap, StartedUtc = DateTime.UtcNow };
        _runs.Add(run); RunsList.SelectedItem = run; SetButtons();
        try
        {
            var built = await BuildAsync(run);
            if (run.StopRequested) { run.State = "отменён"; Show(run); return; }
            run.AssemblyPath = built.AssemblyPath;
            run.WorkerPath = built.WorkerPath ?? _options.Worker ?? FindWorker();
            run.SourceText = built.SourceText;
            run.SourcePath = built.SourcePath;
            if (Current() == run) SourceBox.Text = run.SourceText;
            if (run.WorkerPath is null) throw new InvalidOperationException("Не найден PlankalkulWorker.dll. Откройте машину через plankalkulsharp machine.");
            await StartWorkerAsync(run, args, heap, delay);
        }
        catch (Exception ex) { run.State = run.StopRequested ? "отменён" : "ошибка сборки"; run.FinishedUtc = DateTime.UtcNow; run.AddDiagnostic(ex.Message); CleanupRun(run); Show(run); SetButtons(); }
    }
    bool TrySettings(out int heap, out int delay, out string[] args)
    {
        args = []; 
        if (!int.TryParse(HeapBox.Text, out heap) || heap <= 0 || heap % 8 != 0) { MessageBox.Show(this, "Размер кучи — положительное число байт, кратное 8.", Title); delay = 0; return false; }
        if (!int.TryParse(DelayBox.Text, out delay) || delay is < 0 or > 1000) { MessageBox.Show(this, "Задержка должна быть от 0 до 1000 мс.", Title); return false; }
        try { args = ProgramArguments.Parse(ArgumentsBox.Text); }
        catch (Exception ex) { MessageBox.Show(this, "Проверьте аргументы: " + ex.Message + "\nПример: 5 [1, 2, 3] (запись в JSON тоже передаётся как [1,2]).", Title); return false; }
        return true;
    }
    async Task<BuildResult> BuildAsync(RunRecord run)
    {
        _python = await CompilerPython.ResolveAsync(_python, AppContext.BaseDirectory, Environment.CurrentDirectory);
        var session = CreateSession(); run.SessionDir = session;
        var start = StartInfo(_python, true, "-m", "plankalkulsharp", "build", run.SourcePath, "-o", session, "--json");
        start.Environment["PYTHONIOENCODING"] = "utf-8";
        start.StandardOutputEncoding = Encoding.UTF8; start.StandardErrorEncoding = Encoding.UTF8;
        using var process = Process.Start(start) ?? throw new InvalidOperationException("Не удалось запустить Python.");
        run.BuildProcess = process;
        var stdoutTask = process.StandardOutput.ReadToEndAsync(); var stderrTask = ReadBuildOutputAsync(run, process.StandardError);
        await Task.WhenAll(process.WaitForExitAsync(), stdoutTask, stderrTask);
        run.BuildProcess = null;
        var stdout = stdoutTask.Result;
        using var doc = JsonDocument.Parse(stdout); var root = doc.RootElement;
        if (!root.TryGetProperty("ok", out var ok) || !ok.GetBoolean())
        {
            if (root.TryGetProperty("source", out var failedSource) && failedSource.ValueKind == JsonValueKind.Object) { run.SourceText = failedSource.TryGetProperty("text", out var text) ? text.GetString() ?? run.SourceText : run.SourceText; run.SourcePath = failedSource.TryGetProperty("path", out var path) ? path.GetString() ?? run.SourcePath : run.SourcePath; if (Current() == run) SourceBox.Text = run.SourceText; }
            if (root.TryGetProperty("diagnostics", out var ds)) foreach (var d in ds.EnumerateArray()) run.AddDiagnostic(FormatDiagnostic(d), d);
            throw new InvalidOperationException("Сборка не выполнена.");
        }
        var artifact = root.GetProperty("artifact"); var source = root.GetProperty("source");
        return new(artifact.GetProperty("assemblyPath").GetString() ?? throw new InvalidOperationException("Нет модуля."), artifact.TryGetProperty("workerPath", out var w) ? w.GetString() : null, source.GetProperty("text").GetString() ?? "", source.GetProperty("path").GetString() ?? run.SourcePath);
    }
    async Task ReadBuildOutputAsync(RunRecord run, StreamReader reader)
    {
        string? line;
        while ((line = await reader.ReadLineAsync()) is not null)
        {
            run.Diagnostics.Append(line + "\n");
            if (Current() == run) { DiagnosticBox.Text = run.Diagnostics.ToString(); DiagnosticBox.ScrollToEnd(); }
        }
    }
    async Task StartWorkerAsync(RunRecord run, string[] args, int heap, int delay)
    {
        var pipeName = "plankalkul-" + Guid.NewGuid().ToString("N");
        run.Pipe = new NamedPipeServerStream(pipeName, PipeDirection.InOut, 1, PipeTransmissionMode.Byte, PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);
        run.Process = Process.Start(StartInfo("dotnet", false, run.WorkerPath!, "--module", run.AssemblyPath!, "--pipe", pipeName)) ?? throw new InvalidOperationException("Не удалось запустить исполнитель.");
        _ = WatchProcessAsync(run);
        using var connectTimeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var connected = run.Pipe.WaitForConnectionAsync(connectTimeout.Token);
        var winner = await Task.WhenAny(connected, run.Process.WaitForExitAsync(), Task.Delay(Timeout.Infinite, connectTimeout.Token));
        try
        {
            if (winner != connected) throw new OperationCanceledException();
            await connected;
        }
        catch (OperationCanceledException)
        {
            if (!run.Process.HasExited) run.Process.Kill(true);
            throw new InvalidOperationException("Исполнитель не подключился к каналу за 10 секунд.");
        }
        run.Writer = new StreamWriter(run.Pipe, new UTF8Encoding(false), leaveOpen: true) { AutoFlush = true }; run.Reader = new StreamReader(run.Pipe, Encoding.UTF8, false, leaveOpen: true);
        run.ReaderTask = ReadWorkerAsync(run);
        await SendAsync(run, new { version = 1, command = "start", heapSize = heap, delayMs = delay, arguments = args });
        run.State = "запуск"; Show(run); SetButtons();
    }
    async Task ReadWorkerAsync(RunRecord run)
    {
        try { string? line; while ((line = await run.Reader!.ReadLineAsync()) is not null) Dispatcher.Invoke(() => HandleEvent(run, line)); }
        catch (Exception ex) { Dispatcher.Invoke(() => run.Diagnostics.Append("Канал исполнителя: " + ex.Message + "\n")); }
    }
    void HandleEvent(RunRecord run, string line)
    {
        try
        {
            using var doc = JsonDocument.Parse(line); var root = doc.RootElement;
            if (root.GetProperty("version").GetInt32() != 1) throw new InvalidOperationException("Несовместимая версия протокола.");
            switch (root.GetProperty("event").GetString())
            {
                case "state":
                    run.State = root.GetProperty("state").GetString() ?? "неизвестно";
                    run.Line = root.TryGetProperty("line", out var lineNo) ? lineNo.GetInt32() : 0;
                    run.Column = root.TryGetProperty("column", out var column) ? column.GetInt32() : 0;
                    if (run.State is "running" or "paused") Highlight(run);
                    else if (Current() == run) SourceBox.Select(0, 0);
                    if (run.State == "paused") _ = RequestHeapPageAsync(run, run.HeapOffset);
                    break;
                case "output":
                    var text = root.GetProperty("text").GetString() ?? "";
                    if (root.TryGetProperty("stream", out var stream) && stream.GetString() == "stderr") run.AddDiagnostic(text); else run.Output.Append(text);
                    break;
                case "memory": run.Memory.Append(root.GetProperty("text").GetString() ?? ""); break;
                case "diagnostic": run.AddDiagnostic(root.GetProperty("message").GetString() ?? "", root); break;
                case "snapshot":
                    ReadSnapshot(run, root);
                    if (root.TryGetProperty("heapPage", out var page) && page.ValueKind == JsonValueKind.Object) ReadHeapPage(run, page);
                    break;
                case "heapPage":
                    ReadHeapPage(run, root);
                    break;
                case "inspection": run.Fields = root.GetProperty("fields").EnumerateArray().Select(f => new FieldRow(f)).ToList(); run.InspectionSequence = root.TryGetProperty("snapshotSequence", out var ir) ? ir.GetInt64() : run.LastSequence; break;
                case "completed":
                    run.ExitCode = root.GetProperty("exitCode").GetInt32();
                    run.SnapshotIncomplete = root.TryGetProperty("forced", out var forced) && forced.GetBoolean();
                    run.State = run.SnapshotIncomplete ? "принудительно остановлен" : run.ExitCode == 0 ? "завершён успешно" : run.ExitCode == 130 ? "остановлен" : "ошибка выполнения";
                    run.FinishedUtc = DateTime.UtcNow;
                    if (Current() == run) SourceBox.Select(0, 0);
                    run.Completed.TrySetResult(); break;
            }
        }
        catch (Exception ex) { run.Diagnostics.Append("Некорректное событие: " + ex.Message + "\n"); }
        Show(run); SetButtons();
    }
    static void ReadHeapPage(RunRecord run, JsonElement root)
    {
                    if (root.GetProperty("offset").GetInt32() == run.HeapOffset)
                    {
                        run.HeapDumpSequence = root.GetProperty("snapshotSequence").GetInt64();
                        run.HexDump = FormatHeapPage(root);
                        run.HeapDumpOffset = run.HeapOffset;
                        // Keep ownership from this snapshot, even after memory is reused.
                        run.HeapDumpObjects = run.Objects.ToArray();
                    }
    }
    void ReadSnapshot(RunRecord run, JsonElement root)
    {
        var sequence = root.TryGetProperty("sequence", out var se) ? se.GetInt64() : run.LastSequence + 1;
        if (sequence < run.LastSequence) return;
        run.LastSequence = sequence; run.Line = root.TryGetProperty("line", out var line) ? line.GetInt32() : run.Line; run.Column = root.TryGetProperty("column", out var column) ? column.GetInt32() : run.Column;
        var snapshot = root.GetProperty("snapshot"); var stats = snapshot.GetProperty("stats");
        run.Stats = $"Выделений: {stats.GetProperty("allocations").GetInt64()}  Освобождений: {stats.GetProperty("frees").GetInt64()}\nЗанято: {stats.GetProperty("usedBytes").GetInt64()}  Свободно: {stats.GetProperty("freeBytes").GetInt64()}\nПик: {stats.GetProperty("peakUsedBytes").GetInt64()}  Крупный блок: {stats.GetProperty("largestFreeBlock").GetInt64()}\nЖивых объектов: {stats.GetProperty("liveCount").GetInt64()}" + (root.TryGetProperty("exact", out var e) && e.GetBoolean() ? " (точный)" : "");
        run.Stats += $"\nСнимок {sequence}" + (root.TryGetProperty("exact", out var ex) && ex.GetBoolean() ? " — точный" : "");
        run.Blocks = snapshot.GetProperty("blocks").EnumerateArray().Select(b => new BlockRow(b.GetProperty("offset").GetInt64(), b.GetProperty("size").GetInt64(), b.GetProperty("free").GetBoolean())).ToList();
        run.Objects = snapshot.GetProperty("objects").EnumerateArray().Select(o => new ObjectRow(o)).ToList();
        if (run.State is "running" or "paused") Highlight(run);
    }
    async void Pause_Click(object s, RoutedEventArgs e) => await CommandAsync("pause");
    async void Resume_Click(object s, RoutedEventArgs e) => await CommandAsync("resume");
    async void Stop_Click(object s, RoutedEventArgs e) => await StopAsync(Current());
    async void Delay_TextChanged(object s, TextChangedEventArgs e)
    {
        if (Current() is not { State: "running" or "paused", Writer: not null } run || !int.TryParse(DelayBox.Text, out var delay) || delay is < 0 or > 1000) return;
        await SendAsync(run, new { version = 1, command = "delay", delayMs = delay });
    }
    async Task CommandAsync(string command) { if (Current() is { Writer: not null } run) await SendAsync(run, new { version = 1, command }); }
    static async Task SendAsync(RunRecord run, object value)
    {
        try { await run.WriteGate.WaitAsync(); await run.Writer!.WriteLineAsync(JsonSerializer.Serialize(value)); }
        catch (Exception ex) { run.AddDiagnostic("Команда исполнителю: " + ex.Message); }
        finally { if (run.WriteGate.CurrentCount == 0) run.WriteGate.Release(); }
    }
    async Task StopAsync(RunRecord? run)
    {
        if (run is null || run.IsTerminal) return;
        run.StopRequested = true;
        if (run.BuildProcess is { HasExited: false } build) { build.Kill(true); run.State = "отмена сборки"; Show(run); return; }
        if (run.Process is null || run.Process.HasExited) return; run.State = "остановка"; Show(run);
        if (run.Writer is not null) await SendAsync(run, new { version = 1, command = "stop" });
        if (!await WaitExit(run.Process, 2000)) { run.Process.Kill(true); run.State = "принудительно остановлен"; run.ExitCode = 130; run.SnapshotIncomplete = true; run.FinishedUtc = DateTime.UtcNow; }
        Show(run); SetButtons();
    }
    static async Task<bool> WaitExit(Process p, int ms)
    {
        var exited = p.WaitForExitAsync();
        return await Task.WhenAny(exited, Task.Delay(ms)) == exited;
    }
    async Task WatchProcessAsync(RunRecord run)
    {
        try { await run.Process!.WaitForExitAsync(); await Task.WhenAny(run.Completed.Task, Task.Delay(500)); if (run.ReaderTask is not null) await Task.WhenAny(run.ReaderTask, Task.Delay(500)); Dispatcher.Invoke(() => { if (!run.IsTerminal) { run.ExitCode = run.Process.ExitCode; run.State = run.ExitCode == 130 ? "остановлен" : "исполнитель завершился"; run.FinishedUtc = DateTime.UtcNow; } try { run.Cpu = run.Process.TotalProcessorTime; run.WorkingSet = Math.Max(run.WorkingSet, run.Process.PeakWorkingSet64); } catch { } CleanupRun(run); Show(run); SetButtons(); }); } catch { }
    }
    RunRecord? Current() => RunsList.SelectedItem as RunRecord;
    void Runs_SelectionChanged(object s, SelectionChangedEventArgs e) { if (Current() is { } run) { _sourcePath = run.SourcePath; SourceBox.Text = run.SourceText; ShowWorkspace(); UpdateFileHeading(true); HeapOffsetBox.Text = run.HeapOffset.ToString("X8"); Show(run); if (run.State is "running" or "paused") Highlight(run); else SourceBox.Select(0, 0); } SetButtons(); }
    void Show(RunRecord run)
    {
        if (Current() != run) return; StatusText.Text = $"{run.DisplayState}; строка {run.Line}, столбец {run.Column}; код {run.ExitCode}; CPU {run.Cpu.TotalMilliseconds:F0} мс; пик процесса {(run.WorkingSet > 0 ? run.WorkingSet + " байт" : "н/д")}";
        OutputBox.Text = run.Output.ToString(); DiagnosticBox.Text = run.Diagnostics.ToString(); MemoryBox.Text = run.Memory.ToString(); StatsText.Text = run.Stats + (run.SnapshotIncomplete ? "\nПоследний снимок неполный" : "") + (run.Fields.Count == 0 ? "\nИнспектор: выберите объект на паузе" : run.InspectionSequence < run.LastSequence ? "\nИнспектор: снимок устарел" : "");
        var selected = (ObjectsGrid.SelectedItem as ObjectRow)?.Handle;
        if (!ReferenceEquals(MemoryMap.ItemsSource, run.Blocks)) MemoryMap.ItemsSource = run.Blocks;
        if (!ReferenceEquals(ObjectsGrid.ItemsSource, run.Objects))
        {
            _updatingObjects = true;
            try { ObjectsGrid.ItemsSource = run.Objects; if (selected is not null) ObjectsGrid.SelectedItem = run.Objects.FirstOrDefault(x => x.Handle == selected); }
            finally { _updatingObjects = false; }
        }
        if (!ReferenceEquals(InspectorGrid.ItemsSource, run.Fields)) InspectorGrid.ItemsSource = run.Fields;
        RenderHeapDump(run);
        HeapDumpStatusText.Text = run.HeapDumpSequence == 0 ? "Дамп обновляется при задержке или на паузе. -- означает свободную память."
            : run.State == "paused" && run.HeapDumpSequence == run.LastSequence ? "Точный снимок на паузе. -- означает свободную память."
            : run.State == "running" && run.HeapDumpSequence == run.LastSequence ? "Дамп последней контрольной точки. -- означает свободную память."
            : "Сохранённые данные предыдущего снимка; это не текущее содержимое кучи.";
        if (!ReferenceEquals(DiagnosticsList.ItemsSource, run.DiagnosticRows)) DiagnosticsList.ItemsSource = run.DiagnosticRows;
        DrawMap(run);
    }
    void SetButtons()
    {
        var run = Current(); var s = run?.State ?? "";
        RunButton.IsEnabled = _sourcePath is not null && WorkspacePanel.Visibility == Visibility.Visible;
        PauseButton.IsEnabled = s == "running"; ResumeButton.IsEnabled = s == "paused";
        StopButton.IsEnabled = s is "сборка" or "running" or "paused" or "waiting" or "запуск" or "остановка";
        HeapGoButton.IsEnabled = HeapOffsetBox.IsEnabled = s is "paused" or "running";
        HeapPreviousButton.IsEnabled = (s is "paused" or "running") && run!.HeapOffset > 0;
        HeapNextButton.IsEnabled = (s is "paused" or "running") && run!.HeapOffset < run.HeapSize - 256;
    }
    async void Block_SelectionChanged(object s, SelectionChangedEventArgs e)
    {
        if (MemoryMap.SelectedItem is not BlockRow block || Current() is not { } run) return;
        ObjectsGrid.SelectedItem = run.Objects.FirstOrDefault(o => o.Offset >= block.Offset && o.Offset < block.Offset + block.Size);
        await RequestHeapPageAsync(run, (int)block.Offset);
    }
    async Task RequestHeapPageAsync(RunRecord run, int offset)
    {
        if (run.State is not ("paused" or "running") || run.Writer is null || offset < 0 || offset >= run.HeapSize) return;
        run.HeapOffset = offset;
        if (Current() == run) HeapOffsetBox.Text = offset.ToString("X8");
        await SendAsync(run, new { version = 1, command = "inspectHeap", offset });
        SetButtons();
    }
    async void HeapGo_Click(object s, RoutedEventArgs e)
    {
        if (Current() is not { } run) return;
        if (!int.TryParse(HeapOffsetBox.Text.Trim(), System.Globalization.NumberStyles.HexNumber, System.Globalization.CultureInfo.InvariantCulture, out var offset) || offset < 0 || offset >= run.HeapSize)
        { MessageBox.Show(this, "Введите hex-смещение внутри кучи, например 00000100.", Title); return; }
        await RequestHeapPageAsync(run, offset);
    }
    async void HeapPrevious_Click(object s, RoutedEventArgs e) { if (Current() is { } run) await RequestHeapPageAsync(run, Math.Max(0, run.HeapOffset - 256)); }
    async void HeapNext_Click(object s, RoutedEventArgs e) { if (Current() is { } run && run.HeapOffset < run.HeapSize - 256) await RequestHeapPageAsync(run, run.HeapOffset + 256); }
    static readonly Brush[] HeapColors = [Brushes.Lavender, Brushes.Honeydew, Brushes.MistyRose, Brushes.LightCyan, Brushes.LemonChiffon, Brushes.PeachPuff];
    (RunRecord? Run, string? Text, string? Selected) _renderedHeap;
    void RenderHeapDump(RunRecord run)
    {
        var selected = (ObjectsGrid.SelectedItem as ObjectRow)?.Handle;
        if (_renderedHeap == (run, run.HexDump, selected)) return;
        _renderedHeap = (run, run.HexDump, selected);
        var paragraph = new Paragraph { Margin = new Thickness(0) };
        var lines = run.HexDump.Split('\n');
        for (var line = 0; line < lines.Length; line++)
        {
            var text = lines[line].TrimEnd('\r');
            if (line == 0 || text.Length < 10) paragraph.Inlines.Add(new Run(text));
            else
            {
                paragraph.Inlines.Add(new Run(text[..10]));
                // Each row has 16 hex cells (three characters each), then ASCII.
                for (var cell = 0; cell < 16 && 10 + cell * 3 < text.Length; cell++)
                {
                    var start = 10 + cell * 3;
                    var address = run.HeapDumpOffset + (line - 1) * 16L + cell;
                    var owner = run.HeapDumpObjects.FirstOrDefault(o => address >= o.Offset && address - o.Offset < o.Size);
                    var token = new Run(text.Substring(start, Math.Min(3, text.Length - start)));
                    if (owner is not null)
                    {
                        var index = ulong.Parse(owner.Handle, System.Globalization.CultureInfo.InvariantCulture) % (ulong)HeapColors.Length;
                        token.Background = owner.Handle == selected ? Brushes.Gold : HeapColors[(int)index];
                        token.ToolTip = $"#{owner.Handle} {owner.TypeName}: [{owner.Offset}, {owner.Offset + owner.Size})";
                    }
                    paragraph.Inlines.Add(token);
                }
                if (text.Length > 58) paragraph.Inlines.Add(new Run(text[58..]));
            }
            if (line < lines.Length - 1) paragraph.Inlines.Add(new LineBreak());
        }
        var scroll = HexDumpBox.VerticalOffset;
        HexDumpBox.Document.Blocks.Clear();
        HexDumpBox.Document.Blocks.Add(paragraph);
        HexDumpBox.ScrollToVerticalOffset(scroll);
    }
    static string FormatHeapPage(JsonElement root)
    {
        var offset = root.GetProperty("offset").GetInt32();
        var bytes = root.GetProperty("bytes").EnumerateArray().Select(b => b.ValueKind == JsonValueKind.Null ? (byte?)null : b.GetByte()).ToArray();
        var text = new StringBuilder($"Куча: {root.GetProperty("size").GetInt32()} байт; снимок {root.GetProperty("snapshotSequence").GetInt64()}\n");
        for (var row = 0; row < bytes.Length; row += 16)
        {
            var values = bytes.Skip(row).Take(16).ToArray();
            var hex = string.Join(" ", values.Select(b => b?.ToString("X2") ?? "--"));
            var ascii = new string(values.Select(b => b is >= 32 and <= 126 ? (char)b.Value : '.').ToArray());
            text.AppendLine($"{offset + row:X8}  {hex.PadRight(47)}  |{ascii}|");
        }
        return text.ToString();
    }
    void HeapCanvas_SizeChanged(object sender, SizeChangedEventArgs e) => DrawMap(Current());
    void DrawMap(RunRecord? run)
    {
        HeapCanvas.Children.Clear();
        if (run is null || run.Blocks.Count == 0 || HeapCanvas.ActualWidth <= 0) return;
        var total = run.Blocks.Max(b => b.Offset + b.Size);
        foreach (var block in run.Blocks)
        {
            var rectangle = new System.Windows.Shapes.Rectangle { Width = Math.Max(1, HeapCanvas.ActualWidth * block.Size / total), Height = HeapCanvas.ActualHeight, Fill = block.Free ? Brushes.LightGray : Brushes.SteelBlue, ToolTip = block.Description, Tag = block };
            rectangle.MouseLeftButtonDown += (_, _) => MemoryMap.SelectedItem = block;
            Canvas.SetLeft(rectangle, HeapCanvas.ActualWidth * block.Offset / total); HeapCanvas.Children.Add(rectangle);
        }
    }
    void Grid_AutoGeneratingColumn(object sender, DataGridAutoGeneratingColumnEventArgs e)
    {
        e.Column.Header = e.PropertyName switch { "Handle" => "Ссылка", "TypeId" => "Тип", "TypeName" => "Имя типа", "Offset" => "Смещение", "Size" => "Размер", "Location" => "Создан", "Path" => "Поле", "Kind" => "Вид", "Value" => "Значение", "TargetHandle" => "Ссылка", _ => e.PropertyName };
    }
    void Diagnostic_SelectionChanged(object s, SelectionChangedEventArgs e)
    {
        if (DiagnosticsList.SelectedItem is not DiagnosticRow row || Current() is not { } run || row.Line < 1) return;
        SourceBox.Text = run.SourceText; run.Line = row.Line; run.Column = row.Column; Highlight(run);
    }
    async void Object_SelectionChanged(object s, SelectionChangedEventArgs e)
    {
        if (_updatingObjects) return;
        if (Current() is not { } run) return;
        RenderHeapDump(run);
        if (ObjectsGrid.SelectedItem is not ObjectRow row || run.State is not ("paused" or "running") || run.Writer is null) return;
        if (run.State == "paused") await SendAsync(run, new { version = 1, command = "inspect", handle = row.Handle });
        // Keep nearby objects visible; only navigate when the object is off-page.
        if (run.HeapDumpSequence != run.LastSequence || row.Offset < run.HeapDumpOffset || row.Offset >= run.HeapDumpOffset + 256L)
            await RequestHeapPageAsync(run, (int)(row.Offset / 256 * 256));
    }
    async void Inspector_DoubleClick(object s, System.Windows.Input.MouseButtonEventArgs e) { if (InspectorGrid.SelectedItem is FieldRow { TargetHandle: { } target } && Current() is { Writer: not null } run) { var found = run.Objects.FirstOrDefault(o => o.Handle == target); if (found is not null) ObjectsGrid.SelectedItem = found; await SendAsync(run, new { version = 1, command = "inspect", handle = target }); } }
    async void Window_Closing(object? sender, System.ComponentModel.CancelEventArgs e)
    {
        if (_closing) return;
        e.Cancel = true;
        if (_closePending) return;
        _closePending = true;
        foreach (var run in _runs.ToArray()) await StopAsync(run);
        _ = Dispatcher.BeginInvoke(() => { _closing = true; _closePending = false; Close(); });
    }
    void Highlight(RunRecord run)
    {
        if (Current() != run || run.Line < 1 || run.Line > SourceBox.LineCount) return;
        HighlightNotation(run);
        if (_hoveringNotation) return;
        SourceBox.SelectionBrush = run.State == "running" ? Brushes.LightSkyBlue : Brushes.Gold;
        SourceBox.ToolTip = run.State == "running"
            ? "Голубой: последняя полученная позиция исполнения (обновляется до 5 раз в секунду)."
            : "Жёлтый: следующий участок после продолжения с паузы или выбранная диагностика.";
        var lineStart = SourceBox.GetCharacterIndexFromLineIndex(run.Line - 1);
        var end = lineStart + SourceBox.GetLineText(run.Line - 1).TrimEnd('\r', '\n').Length;
        var start = Math.Min(lineStart + Math.Max(0, run.Column), end);
        if (SourceBox.SelectionStart != start || SourceBox.SelectionLength != end - start)
        {
            SourceBox.Select(start, end - start);
            SourceBox.ScrollToLine(run.Line - 1);
        }
    }
    static ProcessStartInfo StartInfo(string file, bool redirect, params string[] args)
    {
        var info = new ProcessStartInfo(file) { UseShellExecute = false, RedirectStandardOutput = redirect, RedirectStandardError = redirect, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden };
        foreach (var arg in args) info.ArgumentList.Add(arg);
        return info;
    }
    static void CleanupRun(RunRecord run)
    {
        try { run.Reader?.Dispose(); run.Reader = null; run.Writer?.Dispose(); run.Writer = null; run.Pipe?.Dispose(); run.Pipe = null; run.Process?.Dispose(); run.Process = null; run.BuildProcess?.Dispose(); run.BuildProcess = null; if (run.SessionDir is { } d && File.Exists(Path.Combine(d, ".plankalkul-machine"))) Directory.Delete(d, true); run.SessionDir = null; } catch { }
    }
    string? FindWorker() { var c = Path.Combine(AppContext.BaseDirectory, "PlankalkulWorker.dll"); return File.Exists(c) ? c : null; }
    static string SettingsPath() { var p = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "PlankalkulMachine"); Directory.CreateDirectory(p); return Path.Combine(p, "python.txt"); }
    static string? LoadPython() { try { return File.Exists(SettingsPath()) ? File.ReadAllText(SettingsPath()).Trim() : null; } catch { return null; } }
    static string CreateSession()
    {
        var root = Path.Combine(Path.GetTempPath(), "PlankalkulMachine"); Directory.CreateDirectory(root); var d = Path.Combine(root, Guid.NewGuid().ToString("N")); Directory.CreateDirectory(d);
        using var self = Process.GetCurrentProcess(); File.WriteAllText(Path.Combine(d, ".plankalkul-machine"), JsonSerializer.Serialize(new SessionOwner(self.Id, self.StartTime.ToUniversalTime()))); return d;
    }
    static void CleanupOldSessions()
    {
        var root = Path.Combine(Path.GetTempPath(), "PlankalkulMachine"); if (!Directory.Exists(root)) return;
        foreach (var d in Directory.EnumerateDirectories(root)) try { var marker = Path.Combine(d, ".plankalkul-machine"); if (File.Exists(marker) && !OwnerAlive(JsonSerializer.Deserialize<SessionOwner>(File.ReadAllText(marker)))) Directory.Delete(d, true); } catch { }
    }
    static bool OwnerAlive(SessionOwner? owner)
    {
        if (owner is null) return false;
        try { using var p = Process.GetProcessById(owner.ProcessId); return Math.Abs((p.StartTime.ToUniversalTime() - owner.StartUtc).TotalSeconds) < 1; } catch { return false; }
    }
    static string FormatDiagnostic(JsonElement d) => $"{(d.TryGetProperty("stage", out var s) ? s.GetString() : "")}: {(d.TryGetProperty("message", out var m) ? m.GetString() : "")}";
    static void Append(TextBox box, string value) => box.AppendText(value);
}

public sealed class RunRecord(string title, string sourceText, string sourcePath)
{
    public int HeapDumpOffset { get; set; }
    public ObjectRow[] HeapDumpObjects { get; set; } = [];
    public int HeapOffset { get; set; }
    public long HeapDumpSequence { get; set; }
    public string HexDump { get; set; } = "Поставьте программу на паузу для просмотра кучи.";
    public string Title { get; private set; } = title; public string SourceText { get; set; } = sourceText; public string SourcePath { get; set; } = sourcePath; public string State { get; set; } = "ожидание"; public int ExitCode { get; set; } = -1; public int HeapSize { get; set; } public int Line { get; set; } public int Column { get; set; } public DateTime StartedUtc { get; set; } public DateTime? FinishedUtc { get; set; } public long LastSequence { get; set; } public long InspectionSequence { get; set; } public bool SnapshotIncomplete { get; set; } public bool IsTerminal => State is "завершён успешно" or "ошибка выполнения" or "остановлен" or "принудительно остановлен" or "отменён" or "ошибка сборки";
    public string? SessionDir { get; set; } public string? AssemblyPath { get; set; } public string? WorkerPath { get; set; } public Process? Process { get; set; } public Process? BuildProcess { get; set; } public bool StopRequested { get; set; } public TaskCompletionSource Completed { get; } = new(); public Task? ReaderTask { get; set; } public SemaphoreSlim WriteGate { get; } = new(1, 1); public NamedPipeServerStream? Pipe { get; set; } public StreamReader? Reader { get; set; } public StreamWriter? Writer { get; set; }
    public BoundedText Output { get; } = new(); public BoundedText Diagnostics { get; } = new(); public EventLog Memory { get; } = new(); public ObservableCollection<DiagnosticRow> DiagnosticRows { get; } = []; public string Stats { get; set; } = "Ожидание снимка памяти"; public List<BlockRow> Blocks { get; set; } = []; public List<ObjectRow> Objects { get; set; } = []; public List<FieldRow> Fields { get; set; } = []; public TimeSpan Cpu { get; set; } public long WorkingSet { get; set; }
    public string DisplayState => State switch { "running" => "выполняется", "paused" => "пауза", "waiting" => "ожидание", "stopping" => "остановка", _ => State };
    public void RefreshTitle() { var elapsed = StartedUtc == default ? TimeSpan.Zero : (FinishedUtc ?? DateTime.UtcNow) - StartedUtc; Title = $"{Path.GetFileName(SourcePath)} — {DisplayState} ({elapsed:mm\\:ss})"; }
    public void SampleProcess() { try { if (Process is { HasExited: false } process) { Cpu = process.TotalProcessorTime; WorkingSet = Math.Max(WorkingSet, process.WorkingSet64); } } catch { } }
    public void AddDiagnostic(string text, JsonElement? source = null)
    {
        var line = 0; var column = 0;
        if (source is { } item) { if (item.TryGetProperty("line", out var l) && l.ValueKind == JsonValueKind.Number) l.TryGetInt32(out line); if (item.TryGetProperty("column", out var c) && c.ValueKind == JsonValueKind.Number) c.TryGetInt32(out column); }
        Diagnostics.Append(text + (text.EndsWith('\n') ? "" : "\n")); DiagnosticRows.Add(new DiagnosticRow(text.Trim(), line, column));
    }
}
public sealed class BoundedText
{
    readonly StringBuilder _text = new(); int _bytes; bool _cut;
    public void Append(string s)
    {
        _text.Append(s); _bytes += Encoding.UTF8.GetByteCount(s);
        if (_bytes <= 1_048_576) return;
        var removed = 0;
        foreach (var rune in _text.ToString().EnumerateRunes())
        {
            _bytes -= rune.Utf8SequenceLength; removed += rune.Utf16SequenceLength;
            if (_bytes <= 1_048_576) break;
        }
        _text.Remove(0, removed); _cut = true;
    }
    public override string ToString() => (_cut ? "[начало удалено: лимит 1 МиБ]\n" : "") + _text;
}
public sealed class EventLog { readonly Queue<string> _events = new(); bool _cut; public void Append(string text) { _events.Enqueue(text.TrimEnd('\r', '\n') + "\n"); if (_events.Count > 5000) { _events.Dequeue(); _cut = true; } } public override string ToString() => (_cut ? "[старые события удалены: лимит 5000]\n" : "") + string.Concat(_events); }
public sealed record DiagnosticRow(string Text, int Line, int Column);
public sealed record BuildResult(string AssemblyPath, string? WorkerPath, string SourceText, string SourcePath);
public sealed record SessionOwner(int ProcessId, DateTime StartUtc);
public sealed record BlockRow(long Offset, long Size, bool Free) { public string Description => $"{(Free ? "свободен" : "занят")} [{Offset}, {Offset + Size}) {Size} байт"; }
public sealed class ObjectRow { public ObjectRow(JsonElement o) { Handle = o.GetProperty("handle").ToString(); TypeId = o.GetProperty("typeId").GetInt32(); TypeName = o.GetProperty("typeName").GetString() ?? ""; Offset = o.GetProperty("offset").GetInt64(); Size = o.GetProperty("size").GetInt64(); Location = o.GetProperty("location").GetString() ?? ""; } public string Handle { get; } public int TypeId { get; } public string TypeName { get; } public long Offset { get; } public long Size { get; } public string Location { get; } }
public sealed class FieldRow { public FieldRow(JsonElement f) { Path = f.GetProperty("path").GetString() ?? ""; Kind = f.GetProperty("kind").GetString() ?? ""; Value = f.GetProperty("value").ToString(); TargetHandle = f.TryGetProperty("targetHandle", out var h) ? h.ToString() : null; } public string Path { get; } public string Kind { get; } public string Value { get; } public string? TargetHandle { get; } }
