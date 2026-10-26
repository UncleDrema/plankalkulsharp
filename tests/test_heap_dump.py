"""Check the actual WPF hex document without starting a program or Worker."""
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape


def test_heap_dump_object_backgrounds(tmp_path):
    desktop = Path(__file__).parents[1] / "src/plankalkulsharp/dotnet_assets/desktop/PlankalkulMachine.csproj"
    (tmp_path / "Check.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType>'
        '<TargetFramework>net10.0-windows</TargetFramework><UseWPF>true</UseWPF>'
        '<ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup>'
        f'<ProjectReference Include="{escape(str(desktop))}"/></ItemGroup></Project>', encoding="utf-8")
    (tmp_path / "Program.cs").write_text(r'''
using PlankalkulMachine;
using System.Reflection;
using System.Text.Json;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;
class Check {
    [STAThread] static void Main() {
        var log = new EventLog();
        log.Append("heap 64 bytes"); log.Append("split 0: 16 + 48\r\n"); log.Append("allocate #1");
        if (log.ToString() != "heap 64 bytes\nsplit 0: 16 + 48\nallocate #1\n")
            throw new Exception("Memory events must have exactly one newline between them");
        var window = new MainWindow(new MachineOptions(null, null, null));
        var sourceBox = (TextBox)window.FindName("SourceBox");
        sourceBox.Text = "first\n  7 => R0; tail";
        sourceBox.Measure(new System.Windows.Size(500, 300));
        sourceBox.Arrange(new System.Windows.Rect(0, 0, 500, 300));
        typeof(MainWindow).GetMethod("SelectNotationSource", BindingFlags.NonPublic | BindingFlags.Instance)!
            .Invoke(window, new object[] { 2, 2, 2, 9 });
        if (sourceBox.SelectedText != "7 => R0" || sourceBox.SelectionBrush != Brushes.LightGreen)
            throw new Exception("Notation must select only its source range");
        var overlay = (Canvas)window.FindName("SourceHighlight");
        if (sourceBox.IsKeyboardFocused || overlay.Children.Count != 1)
            throw new Exception("Unfocused source must have a visible highlight rectangle");
        var mark = (System.Windows.Shapes.Rectangle)overlay.Children[0];
        if (mark.Width <= 0 || mark.Height <= 0 || mark.Fill != Brushes.LightGreen || overlay.IsHitTestVisible)
            throw new Exception("Highlight must be colored, nonempty and not intercept input");
        sourceBox.Select(0, 0);
        if (overlay.Children.Count != 0) throw new Exception("Clearing selection must clear the overlay");
        var toggleHelp = typeof(MainWindow).GetMethod("Help_Click", BindingFlags.NonPublic | BindingFlags.Instance)!;
        toggleHelp.Invoke(window, new object[] { window, new System.Windows.RoutedEventArgs() });
        var helpHost = (ContentControl)window.FindName("HelpHost");
        var workspace = (Grid)window.FindName("WorkspacePanel");
        if (helpHost.Visibility != System.Windows.Visibility.Visible || workspace.Visibility != System.Windows.Visibility.Collapsed)
            throw new Exception("Help must replace the workspace");
        var help = (LanguageHelp)helpHost.Content;
        var topics = (ListBox)help.FindName("Contents");
        if (topics.Items.Count != 13) throw new Exception("All language topics must be available");
        ((TextBox)help.FindName("TopicSearch")).Text = "несуществующаяконструкция";
        if (topics.Items.OfType<ListBoxItem>().Any(i => i.Visibility == System.Windows.Visibility.Visible))
            throw new Exception("Help search must filter topic contents");
        ((TextBox)help.FindName("TopicSearch")).Clear();
        if (topics.Items.OfType<ListBoxItem>().Count(i => i.Visibility == System.Windows.Visibility.Visible) != 13)
            throw new Exception("Clearing search must restore topics");
        var toggleMemory = typeof(MainWindow).GetMethod("Memory_Toggle", BindingFlags.NonPublic | BindingFlags.Instance)!;
        var memoryToggle = (CheckBox)window.FindName("MemoryToggle");
        memoryToggle.IsChecked = false;
        toggleMemory.Invoke(window, new object[] { window, new System.Windows.RoutedEventArgs() });
        if (((Grid)window.FindName("MemoryPanel")).Visibility != System.Windows.Visibility.Collapsed)
            throw new Exception("Hidden memory must release workspace space");
        memoryToggle.IsChecked = true;
        toggleMemory.Invoke(window, new object[] { window, new System.Windows.RoutedEventArgs() });
        var catalog = JsonSerializer.SerializeToElement(new[] { new { name = "sample", source = "P0 template", types = new[] { "element" } } });
        var browser = (DockPanel)typeof(MainWindow).GetMethod("BuildLibraryBrowser", BindingFlags.NonPublic | BindingFlags.Instance)!
            .Invoke(window, new object[] { catalog.EnumerateArray().ToArray(), Array.Empty<JsonElement>() })!;
        var navigation = browser.Children.OfType<DockPanel>().First();
        var libraryChoices = navigation.Children.OfType<ListBox>().Single();
        if ((string)libraryChoices.SelectedItem != "sample") throw new Exception("Catalog must work without a program or specialization");
        navigation.Children.OfType<TextBox>().Single().Text = "missing";
        if (libraryChoices.Items.Count != 0) throw new Exception("Catalog search must filter plans");
        var argumentType = typeof(MainWindow).Assembly.GetType("PlankalkulMachine.ProgramArguments")!;
        var parseArguments = argumentType.GetMethod("Parse", BindingFlags.Public | BindingFlags.Static)!;
        var arguments = (string[])parseArguments.Invoke(null, new object[] { "5 [1, 2] [[3,4], 7]" })!;
        if (arguments.Length != 3 || arguments[1] != "[1, 2]") throw new Exception("Structured arguments must stay intact");
        topics.SelectedIndex = 7;
        toggleHelp.Invoke(window, new object[] { window, new System.Windows.RoutedEventArgs() });
        if (workspace.Visibility != System.Windows.Visibility.Visible || sourceBox.Text != "first\n  7 => R0; tail")
            throw new Exception("Returning from help must preserve the source");
        ObjectRow Obj(int id, int offset) => new(JsonSerializer.SerializeToElement(new {
            handle = id.ToString(), typeId = 1, typeName = "word", offset, size = 8, location = "test" }));
        var objects = new[] { Obj(1, 8), Obj(2, 16) };
        var page = JsonSerializer.SerializeToElement(new { offset = 0, size = 32, snapshotSequence = 1,
            bytes = Enumerable.Range(0, 32).Select(i => i >= 8 && i < 24 ? (byte?)i : null).ToArray() });
        var format = typeof(MainWindow).GetMethod("FormatHeapPage", BindingFlags.NonPublic | BindingFlags.Static)!;
        var render = typeof(MainWindow).GetMethod("RenderHeapDump", BindingFlags.NonPublic | BindingFlags.Instance)!;
        var run = new RunRecord("test", "", "test.pk") { HeapDumpObjects = objects,
            HexDump = (string)format.Invoke(null, new object[] { page })! };
        var grid = (DataGrid)window.FindName("ObjectsGrid");
        var box = (RichTextBox)window.FindName("HexDumpBox");
        grid.ItemsSource = objects;
        Run[] Cells() => ((Paragraph)box.Document.Blocks.FirstBlock).Inlines.OfType<Run>()
            .Where(r => r.Text.Length == 3).ToArray();
        render.Invoke(window, new object[] { run });
        var cells = Cells();
        if (cells.Length != 32 || cells[0].Background != null || cells[24].Background != null
            || cells[8].Background == null || cells[8].Background == cells[16].Background)
            throw new Exception("Incorrect object/free byte boundaries or colors");
        grid.SelectedItem = objects[1];
        render.Invoke(window, new object[] { run });
        cells = Cells();
        if (cells.Skip(16).Take(8).Any(c => c.Background != Brushes.Gold)
            || cells[15].Background == Brushes.Gold || cells[24].Background == Brushes.Gold)
            throw new Exception("Selection must highlight exactly the selected object's bytes");
    }
}
''', encoding="utf-8")
    # Isolate outputs so an open desktop app cannot lock the test's build.
    output = tmp_path / "check-bin"
    result = subprocess.run(["dotnet", "build", str(tmp_path / "Check.csproj"), "-o", str(output),
                             "-p:NuGetAudit=false", "-v:q"], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run(["dotnet", str(output / "Check.dll")], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
