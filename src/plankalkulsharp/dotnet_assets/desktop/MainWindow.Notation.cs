using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace PlankalkulMachine;

public partial class MainWindow
{
    string? _notationSource;
    int _notationRequest;
    System.Threading.CancellationTokenSource? _notationCancellation;
    readonly List<(Button Button, int Line, int Column, string Kind)> _notationRows = [];
    Button? _activeNotation;
    bool _hoveringNotation;
    (int Start, int Length, Brush Brush) _savedSelection;

    void SourceSelection_Changed(object sender, RoutedEventArgs e) => DrawSourceHighlight();

    // Selection remains available for copying, but its visible overlay does not
    // depend on TextBox keyboard focus or the theme's inactive-selection colors.
    void DrawSourceHighlight()
    {
        if (SourceHighlight is null) return;
        SourceHighlight.Children.Clear();
        if (SourceBox.SelectionLength == 0 || SourceBox.ViewportWidth <= 0) return;
        SourceHighlight.Clip = new RectangleGeometry(new Rect(0, 0,
            SourceBox.ViewportWidth, SourceBox.ViewportHeight));
        int start = SourceBox.SelectionStart, end = start + SourceBox.SelectionLength;
        int first = Math.Max(SourceBox.GetLineIndexFromCharacterIndex(start), SourceBox.GetFirstVisibleLineIndex());
        int last = Math.Min(SourceBox.GetLineIndexFromCharacterIndex(end - 1), SourceBox.GetLastVisibleLineIndex());
        for (int line = first; line >= 0 && line <= last; line++)
        {
            int lineStart = SourceBox.GetCharacterIndexFromLineIndex(line);
            int lineEnd = lineStart + SourceBox.GetLineText(line).TrimEnd('\r', '\n').Length;
            int from = Math.Max(start, lineStart), to = Math.Min(end, lineEnd);
            if (to <= from) continue;
            var left = SourceBox.GetRectFromCharacterIndex(from);
            var right = SourceBox.GetRectFromCharacterIndex(to - 1, true);
            if (left.IsEmpty || right.IsEmpty) continue;
            var highlight = new System.Windows.Shapes.Rectangle {
                Width = Math.Max(0, right.Right - left.Left), Height = left.Height,
                Fill = SourceBox.SelectionBrush };
            Canvas.SetLeft(highlight, left.Left); Canvas.SetTop(highlight, left.Top);
            SourceHighlight.Children.Add(highlight);
        }
    }

    void SelectNotationSource(int line, int column, int endLine, int endColumn)
    {
        if (line < 1 || line > SourceBox.LineCount) return;
        int Offset(int l, int c) => SourceBox.GetCharacterIndexFromLineIndex(l - 1)
            + Math.Clamp(c, 0, SourceBox.GetLineText(l - 1).TrimEnd('\r', '\n').Length);
        int start = Offset(line, column);
        int end = endLine >= line && endLine <= SourceBox.LineCount
            ? Offset(endLine, endColumn) : Offset(line, int.MaxValue);
        SourceBox.SelectionBrush = Brushes.LightGreen;
        SourceBox.Select(start, Math.Max(0, end - start));
        SourceBox.ScrollToLine(line - 1);
    }

    void EndNotationHover()
    {
        if (!_hoveringNotation) return;
        _hoveringNotation = false;
        if (Current() is { State: "running" or "paused" } run) Highlight(run);
        else
        {
            SourceBox.SelectionBrush = _savedSelection.Brush;
            SourceBox.Select(_savedSelection.Start, _savedSelection.Length);
        }
    }

    void NotationSource_Changed(object sender, TextChangedEventArgs e)
    {
        if (NotationRows is null || SourceBox.Text == _notationSource) return;
        _hoveringNotation = false;
        _notationSource = null;
        _notationLibraries = [];

        _notationRequest++;
        _notationCancellation?.Cancel();
        NotationRows.Children.Clear(); _notationRows.Clear(); _activeNotation = null;
        if (IsLoaded) _ = LoadNotationAsync();
    }

    void Notation_Refresh(object sender, RoutedEventArgs e)
    {
        _notationSource = null;
        _ = LoadNotationAsync();
    }

    async Task LoadNotationAsync()
    {
        var source = SourceBox.Text;
        if (_notationSource == source) return;
        _notationCancellation?.Cancel();
        using var cancellation = new System.Threading.CancellationTokenSource(TimeSpan.FromSeconds(15));
        _notationCancellation = cancellation;
        var request = ++_notationRequest;
        NotationStatus.Text = "Построение AST…";
        Process? process = null;
        try
        {
            var python = await CompilerPython.ResolveAsync(_python, AppContext.BaseDirectory, Environment.CurrentDirectory);
            if (request != _notationRequest) return;
            cancellation.Token.ThrowIfCancellationRequested();
            _python = python;
            var start = StartInfo(_python, true, "-m", "plankalkulsharp", "notation", "--stdin");
            start.RedirectStandardInput = true;
            start.StandardInputEncoding = new UTF8Encoding(false);
            start.StandardOutputEncoding = Encoding.UTF8; start.StandardErrorEncoding = Encoding.UTF8;
            start.Environment["PYTHONIOENCODING"] = "utf-8";
            process = Process.Start(start) ?? throw new InvalidOperationException("Не удалось запустить Python.");
            var output = process.StandardOutput.ReadToEndAsync(cancellation.Token);
            var error = process.StandardError.ReadToEndAsync(cancellation.Token);
            await process.StandardInput.WriteAsync(source.AsMemory(), cancellation.Token);
            process.StandardInput.Close();
            await Task.WhenAll(process.WaitForExitAsync(cancellation.Token), output, error);
            if (request != _notationRequest) return;
            if (process.ExitCode != 0) throw new InvalidOperationException(error.Result.Trim());
            using var document = JsonDocument.Parse(output.Result);
            RenderNotation(document.RootElement);
            _notationSource = source;
            NotationStatus.Text = "Построено из AST и типов; программа не запускалась. Скобки сохраняют группировку выражений.";
            if (Current() is { } run && run.State is "running" or "paused") HighlightNotation(run);
        }
        catch (OperationCanceledException)
        {
            if (request == _notationRequest) NotationStatus.Text = "Построение отменено или превысило 15 секунд. Нажмите «Обновить» для повтора.";
        }
        catch (Exception ex)
        {
            if (request == _notationRequest) NotationStatus.Text = "Не удалось построить нотацию: " + ex.Message;
        }
        finally
        {
            try { if (process is { HasExited: false }) process.Kill(true); } catch { }
            process?.Dispose();
            if (ReferenceEquals(_notationCancellation, cancellation)) _notationCancellation = null;
        }
    }

    // Each expression owns aligned columns; a dynamic K contains another such
    // grid, so its variable indices and types never become ambiguous flat text.
    static Grid NotationGrid(JsonElement cells, bool nested = false)
    {
        var items = cells.EnumerateArray().ToArray();
        var grid = new Grid();
        var keys = new[] { "text", "index", "component", "structure" };
        var labels = new[] { "", "V", "K", "S" };
        var visible = keys.Select((key, r) => r == 0 || items.Any(c =>
            !string.IsNullOrEmpty(c.GetProperty(key).GetString()))).ToArray();
        for (int r = 0; r < 4; r++)
            grid.RowDefinitions.Add(new RowDefinition { Height = visible[r] ? GridLength.Auto : new GridLength(0) });
        void Add(string text, int r, int c, Brush brush, string? hint = null)
        {
            if (!visible[r]) return;
            var label = new TextBlock { Text = text, Foreground = brush, FontFamily = new FontFamily("Cambria"),
                FontSize = (r == 0 ? 20 : 14) * (nested ? 0.8 : 1),
                MinHeight = (r == 0 ? 28 : 20) * (nested ? 0.8 : 1), ToolTip = hint,
                Margin = new Thickness(4, 0, 4, 0), HorizontalAlignment = HorizontalAlignment.Center };
            FrameworkElement element = label;
            if (r == 0 && text == "→\u0323")
            {
                // Draw the dot separately: combining-mark placement varies by font.
                label.Text = "→";
                var sign = new Grid { ToolTip = hint };
                sign.Children.Add(label);
                double scale = nested ? 0.8 : 1;
                sign.Children.Add(new System.Windows.Shapes.Ellipse { Width = 3 * scale, Height = 3 * scale,
                    Fill = brush, HorizontalAlignment = HorizontalAlignment.Center,
                    VerticalAlignment = VerticalAlignment.Bottom, Margin = new Thickness(0, 0, 0, 3 * scale) });
                element = sign;
            }
            Grid.SetRow(element, r); Grid.SetColumn(element, c); grid.Children.Add(element);
        }
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        for (int r = 0; r < 4; r++) Add(labels[r], r, 0, Brushes.SlateGray);
        int column = 1;
        foreach (var cell in items)
        {
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            var brush = cell.GetProperty("extension").GetBoolean() ? Brushes.DarkGoldenrod : Brushes.Black;
            var hint = cell.GetProperty("hint").GetString();
            for (int r = 0; r < 4; r++)
            {
                if (r == 2 && cell.GetProperty("component_cells").GetArrayLength() > 0)
                {
                    var component = NotationGrid(cell.GetProperty("component_cells"), true);
                    var frame = new Border { Child = component, BorderBrush = Brushes.LightSlateGray,
                        BorderThickness = new Thickness(0, 1, 0, 0), Margin = new Thickness(3),
                        HorizontalAlignment = HorizontalAlignment.Center, ToolTip = "Выражение компонента K" };
                    Grid.SetRow(frame, r); Grid.SetColumn(frame, column); grid.Children.Add(frame);
                }
                else Add(cell.GetProperty(keys[r]).GetString() ?? "", r, column, brush, hint);
            }
            column++;
        }
        return grid;
    }

    void RenderNotation(JsonElement document)
    {
        _notationLibraries = document.TryGetProperty("libraries", out var libraries) ? libraries.EnumerateArray().Select(item => item.Clone()).ToArray() : [];

        NotationRows.Children.Clear(); _notationRows.Clear(); _activeNotation = null;
        var panels = new Stack<StackPanel>();
        panels.Push(NotationRows);
        foreach (var row in document.GetProperty("rows").EnumerateArray())
        {
            int line = row.GetProperty("line").GetInt32(), column = row.GetProperty("column").GetInt32();
            var kind = row.GetProperty("kind").GetString() ?? "";
            if (kind == "EndBlock") { panels.Pop(); continue; }
            if (kind == "EndProgram")
            {
                panels.Peek().Children.Add(new Separator { Margin = new Thickness(0, 12, 0, 12) });
                continue;
            }
            var content = new StackPanel();
            if (row.TryGetProperty("caption", out var caption))
                content.Children.Add(new TextBlock { Text = caption.GetString(), Foreground = Brushes.SlateGray,
                    Margin = new Thickness(5, 0, 0, 4), FontWeight = kind == "ProgramDef" ? FontWeights.Bold : FontWeights.Normal });
            content.Children.Add(NotationGrid(row.GetProperty("cells")));
            var button = new Button { Content = content, HorizontalAlignment = HorizontalAlignment.Left,
                Background = Brushes.Transparent, BorderBrush = Brushes.LightGray, BorderThickness = new Thickness(0, 0, 0, 1),
                Padding = new Thickness(5), Margin = new Thickness(0, 4, 0, 4),
                ToolTip = $"{kind} · строка {line}, столбец {column + 1} · перейти к исходнику" };
            int endLine = row.TryGetProperty("endLine", out var el) && el.ValueKind == JsonValueKind.Number && el.TryGetInt32(out var lastLine) ? lastLine : line;
            int endColumn = row.TryGetProperty("endColumn", out var ec) && ec.ValueKind == JsonValueKind.Number && ec.TryGetInt32(out var lastColumn) ? lastColumn : int.MaxValue;
            button.MouseEnter += (_, _) =>
            {
                _savedSelection = (SourceBox.SelectionStart, SourceBox.SelectionLength, SourceBox.SelectionBrush);
                _hoveringNotation = true;
                SelectNotationSource(line, column, endLine, endColumn);
            };
            button.MouseLeave += (_, _) => EndNotationHover();
            button.Click += (_, _) =>
            {
                SelectNotationSource(line, column, endLine, endColumn);
                _savedSelection = (SourceBox.SelectionStart, SourceBox.SelectionLength, SourceBox.SelectionBrush);
            };
            panels.Peek().Children.Add(button); _notationRows.Add((button, line, column, kind));
            if (row.TryGetProperty("block", out var block) && block.GetBoolean())
            {
                // Borders stretch with the entire nested body, including empty blocks.
                var body = new StackPanel { MinHeight = 20, Margin = new Thickness(8, 3, 8, 3) };
                var brackets = new Grid { Margin = new Thickness(22, 0, 0, 4), HorizontalAlignment = HorizontalAlignment.Left };
                brackets.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(6) });
                brackets.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
                brackets.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(6) });
                var left = new Border { BorderBrush = Brushes.Black, BorderThickness = new Thickness(1, 1, 0, 1) };
                var right = new Border { BorderBrush = Brushes.Black, BorderThickness = new Thickness(0, 1, 1, 1) };
                Grid.SetColumn(body, 1); Grid.SetColumn(right, 2);
                brackets.Children.Add(left); brackets.Children.Add(body); brackets.Children.Add(right);
                panels.Peek().Children.Add(brackets); panels.Push(body);
            }
        }
    }

    void HighlightNotation(RunRecord run)
    {
        var next = _notationRows.FirstOrDefault(r => r.Line == run.Line && r.Column == run.Column
            && r.Kind is not "EndBlock" and not "EndProgram").Button;
        if (_activeNotation != next)
        {
            if (_activeNotation is not null) _activeNotation.Background = Brushes.Transparent;
            _activeNotation = next;
            if (!_hoveringNotation) next?.BringIntoView();
        }
        if (next is not null) next.Background = run.State == "running" ? Brushes.LightSkyBlue : Brushes.Gold;
    }
}
