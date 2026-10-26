using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace PlankalkulMachine;

public partial class MainWindow
{
    JsonElement[] _notationLibraries = [];
    int _libraryRequest;

    async void Library_Click(object sender, RoutedEventArgs e)
    {
        int request = ++_libraryRequest;
        HelpHost.Visibility = WorkspacePanel.Visibility = Visibility.Collapsed;
        LibraryHost.Visibility = Visibility.Visible;
        HelpButton.Content = "Справка по языку";
        SetButtons();
        LibraryHost.Content = new TextBlock { Text = "Загрузка стандартных планов…", Margin = new Thickness(16) };
        Process? process = null;
        try
        {
            // Ask the installed compiler: the cached desktop has no repository-relative paths.
            using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(15));
            var python = await CompilerPython.ResolveAsync(_python, AppContext.BaseDirectory, Environment.CurrentDirectory);
            if (request != _libraryRequest) return;
            var start = StartInfo(python, true, "-m", "plankalkulsharp", "library");
            start.Environment["PYTHONIOENCODING"] = "utf-8";
            start.StandardOutputEncoding = start.StandardErrorEncoding = Encoding.UTF8;
            process = Process.Start(start) ?? throw new InvalidOperationException("Не удалось запустить Python.");
            var stdout = process.StandardOutput.ReadToEndAsync(timeout.Token);
            var stderr = process.StandardError.ReadToEndAsync(timeout.Token);
            await Task.WhenAll(process.WaitForExitAsync(timeout.Token), stdout, stderr);
            if (request != _libraryRequest) return;
            if (process.ExitCode != 0) throw new InvalidOperationException(stderr.Result.Trim());
            using var document = JsonDocument.Parse(stdout.Result);
            LibraryHost.Content = BuildLibraryBrowser(document.RootElement.GetProperty("plans").EnumerateArray().Select(p => p.Clone()).ToArray(), _notationLibraries);
        }
        catch (Exception ex)
        {
            if (request != _libraryRequest) return;
            var panel = new StackPanel { Margin = new Thickness(16) };
            panel.Children.Add(new TextBlock { Text = "Не удалось загрузить планы. " + ex.Message, TextWrapping = TextWrapping.Wrap });
            var retry = new Button { Content = "Повторить", HorizontalAlignment = HorizontalAlignment.Left };
            retry.Click += Library_Click; panel.Children.Add(retry); LibraryHost.Content = panel;
        }
        finally { try { if (process is { HasExited: false }) process.Kill(true); } catch { } process?.Dispose(); }
    }

    FrameworkElement BuildLibraryBrowser(JsonElement[] catalog, JsonElement[] specializations)
    {
        var root = new DockPanel();
        var heading = new StackPanel { Margin = new Thickness(8, 0, 8, 12) };
        heading.Children.Add(new TextBlock { Text = "Стандартные планы", FontSize = 22, FontWeight = FontWeights.SemiBold });
        heading.Children.Add(new TextBlock { Text = "Алгоритмы на .pk · шаблоны типов и подстановки из текущей программы", Margin = new Thickness(0, 4, 0, 0), TextWrapping = TextWrapping.Wrap });
        DockPanel.SetDock(heading, Dock.Top); root.Children.Add(heading);
        var navigation = new DockPanel { Width = 175, Margin = new Thickness(0, 0, 12, 0) };
        var search = new TextBox { ToolTip = "Поиск стандартного плана", Margin = new Thickness(0, 0, 0, 8) };
        System.Windows.Automation.AutomationProperties.SetName(search, "Поиск стандартного плана");
        DockPanel.SetDock(search, Dock.Top); navigation.Children.Add(search);
        var choices = new ListBox(); navigation.Children.Add(choices);
        DockPanel.SetDock(navigation, Dock.Left); root.Children.Add(navigation);
        var detail = new DockPanel(); root.Children.Add(detail);
        var variants = new ComboBox { Margin = new Thickness(4), MinHeight = 30 };
        System.Windows.Automation.AutomationProperties.SetName(variants, "Шаблон или подстановка типов");
        var explanation = new TextBlock { Margin = new Thickness(8), TextWrapping = TextWrapping.Wrap };
        DockPanel.SetDock(variants, Dock.Top); detail.Children.Add(variants);
        DockPanel.SetDock(explanation, Dock.Top); detail.Children.Add(explanation);
        var summary = new TextBlock { Margin = new Thickness(8), TextWrapping = TextWrapping.Wrap, FontWeight = FontWeights.SemiBold };
        DockPanel.SetDock(summary, Dock.Top); detail.Children.Add(summary);
        var code = new TextBox { IsReadOnly = true, AcceptsReturn = true, FontFamily = new FontFamily("Consolas"),
            HorizontalScrollBarVisibility = ScrollBarVisibility.Auto, VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
        var rows = new StackPanel { Margin = new Thickness(12) };
        var grid = new Grid();
        grid.ColumnDefinitions.Add(new ColumnDefinition()); grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(6) }); grid.ColumnDefinitions.Add(new ColumnDefinition());
        grid.Children.Add(code);
        var splitter = new GridSplitter { Width = 6, HorizontalAlignment = HorizontalAlignment.Stretch };
        Grid.SetColumn(splitter, 1); grid.Children.Add(splitter);
        var scroll = new ScrollViewer { Content = rows, HorizontalScrollBarVisibility = ScrollBarVisibility.Auto, VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
        Grid.SetColumn(scroll, 2); grid.Children.Add(scroll); detail.Children.Add(grid);
        JsonElement[] current = [];
        void Render()
        {
            if (choices.SelectedItem is not string name) return;
            var plan = catalog.First(p => p.GetProperty("name").GetString() == name);
            summary.Text = (plan.TryGetProperty("description", out var description) ? description.GetString() : name)
                + (plan.TryGetProperty("example", out var example) ? "\n" + example.GetString() : "");
            code.Text = plan.GetProperty("source").GetString(); rows.Children.Clear();
            if (variants.SelectedIndex <= 0)
            {
                explanation.Text = "Шаблон .pk · параметры типов: " + string.Join(", ", plan.GetProperty("types").EnumerateArray().Select(t => t.GetString()));
                rows.Children.Add(new TextBlock { Text = "Для нотации нужны конкретные типы. Откройте программу, которая вызывает этот план: после анализа здесь появятся её подстановки. Шаблон доступен для чтения независимо от программы.", TextWrapping = TextWrapping.Wrap, MaxWidth = 420, HorizontalAlignment = HorizontalAlignment.Left });
                return;
            }
            var library = current[variants.SelectedIndex - 1];
            explanation.Text = "Слева — общий шаблон, справа — AST с подставленными типами текущей программы. Параметры шаблона не являются пользовательскими объявлениями.";
            if (library.GetProperty("projection").ValueKind == JsonValueKind.Number)
                explanation.Text += " Поле 0 заменено в AST на поле " + library.GetProperty("projection").GetInt32() + ".";
            foreach (var row in library.GetProperty("rows").EnumerateArray())
            {
                if (row.GetProperty("kind").GetString() == "EndBlock") continue;
                var formula = NotationGrid(row.GetProperty("cells"));
                formula.Margin = new Thickness(row.GetProperty("depth").GetInt32() * 18, 5, 5, 5); rows.Children.Add(formula);
            }
        }
        choices.SelectionChanged += (_, _) =>
        {
            if (choices.SelectedItem is not string name) { code.Clear(); summary.Text = ""; rows.Children.Clear(); variants.Items.Clear(); explanation.Text = "План не найден. Измените поисковый запрос."; return; }
            current = specializations.Where(p => p.GetProperty("name").GetString() == name).ToArray();
            variants.Items.Clear(); variants.Items.Add("Общий шаблон");
            foreach (var library in current) variants.Items.Add("Типы: " + library.GetProperty("bindings").GetRawText());
            variants.SelectedIndex = current.Length > 0 ? 1 : 0;
        };
        variants.SelectionChanged += (_, _) => Render();
        void Filter() { choices.ItemsSource = catalog.Select(p => p.GetProperty("name").GetString()!).Where(n => n.Contains(search.Text, StringComparison.OrdinalIgnoreCase)).ToArray(); choices.SelectedIndex = 0; }
        search.TextChanged += (_, _) => Filter(); Filter();
        return root;
    }
}
