using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using Microsoft.Win32;

namespace PlankalkulMachine;

public partial class MainWindow
{
    public sealed record SourceFile(string Path) { public string Name => System.IO.Path.GetFileName(Path); }
    readonly List<string> _recentFiles = [];
    string? _folder;
    bool _refreshingFiles;
    double _memoryWidth = 300;

    void InitializeNavigation()
    {
        try
        {
            var path = Path.Combine(Path.GetDirectoryName(SettingsPath())!, "recent.json");
            if (File.Exists(path)) _recentFiles.AddRange((JsonSerializer.Deserialize<string[]>(File.ReadAllText(path)) ?? [])
                .Where(p => Path.IsPathFullyQualified(p) && p.EndsWith(".pk", StringComparison.OrdinalIgnoreCase)).Take(20));
        }
        catch { /* A broken preferences file must not prevent opening a program. */ }
        RefreshFiles();
    }

    void RememberSource(string path)
    {
        _recentFiles.RemoveAll(p => string.Equals(p, path, StringComparison.OrdinalIgnoreCase));
        _recentFiles.Insert(0, path);
        if (_recentFiles.Count > 20) _recentFiles.RemoveRange(20, _recentFiles.Count - 20);
        _folder = Path.GetDirectoryName(path);
        try { File.WriteAllText(Path.Combine(Path.GetDirectoryName(SettingsPath())!, "recent.json"), JsonSerializer.Serialize(_recentFiles)); }
        catch (Exception ex) { Append(DiagnosticBox, "Не удалось сохранить недавние файлы: " + ex.Message + "\n"); }
        RefreshFiles();
        ShowWorkspace();
        UpdateFileHeading(false);
        SetButtons();
    }

    void UpdateFileHeading(bool snapshot)
    {
        FileTitle.Text = _sourcePath is null ? "Откройте программу .pk" : Path.GetFileName(_sourcePath);
        FilePathText.Text = (_sourcePath ?? "Перетащите .pk в окно или выберите файл слева")
            + (snapshot ? " · снимок запуска" : " · только чтение");
    }

    void RefreshFiles()
    {
        _refreshingFiles = true;
        try
        {
            string query = FileFilter.Text.Trim();
            bool Matches(string path) => Path.GetFileName(path).Contains(query, StringComparison.OrdinalIgnoreCase);
            RecentList.ItemsSource = _recentFiles.Where(Matches).Select(p => new SourceFile(p)).ToArray();
            FolderText.Text = _folder ?? "Папка не выбрана";
            FilesList.ItemsSource = _folder is null ? Array.Empty<SourceFile>() : Directory.EnumerateFiles(_folder)
                .Where(p => p.EndsWith(".pk", StringComparison.OrdinalIgnoreCase) && Matches(p))
                .OrderBy(Path.GetFileName, StringComparer.OrdinalIgnoreCase).Select(p => new SourceFile(p)).ToArray();
        }
        catch (Exception ex) { FilesList.ItemsSource = null; FolderText.Text = "Не удалось прочитать папку: " + ex.Message; }
        finally { _refreshingFiles = false; }
    }

    void FileFilter_Changed(object sender, TextChangedEventArgs e) { if (FilesList is not null) RefreshFiles(); }
    void File_Selected(object sender, SelectionChangedEventArgs e)
    {
        if (!_refreshingFiles && sender is ListBox { SelectedItem: SourceFile file }) LoadSource(file.Path);
    }
    void Folder_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFolderDialog { Title = "Папка с программами .pk" };
        if (dialog.ShowDialog(this) == true) { _folder = dialog.FolderName; RefreshFiles(); }
    }
    void Reload_Click(object sender, RoutedEventArgs e) { if (_sourcePath is not null) LoadSource(_sourcePath); }
    void ShowWorkspace()
    {
        HelpHost.Visibility = LibraryHost.Visibility = Visibility.Collapsed;
        WorkspacePanel.Visibility = Visibility.Visible;
        HelpButton.Content = "Справка по языку";
        SetButtons();
    }
    void Workspace_Click(object sender, RoutedEventArgs e) => ShowWorkspace();
    void Memory_Toggle(object sender, RoutedEventArgs e)
    {
        bool visible = MemoryToggle.IsChecked == true;
        if (!visible) _memoryWidth = Math.Max(220, MemoryColumn.ActualWidth);
        MemoryColumn.Width = new GridLength(visible ? _memoryWidth : 0);
        MemoryDivider.Width = new GridLength(visible ? 8 : 0);
        MemoryPanel.Visibility = MemorySplitter.Visibility = visible ? Visibility.Visible : Visibility.Collapsed;
    }
    void Window_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.O && Keyboard.Modifiers == ModifierKeys.Control) { Open_Click(sender, e); e.Handled = true; }
        else if (e.Key == Key.F1) { Help_Click(sender, e); e.Handled = true; }
        else if (e.Key == Key.F5 && RunButton.IsEnabled) { Run_Click(sender, e); e.Handled = true; }
    }
    void Files_DragOver(object sender, DragEventArgs e)
    {
        e.Effects = e.Data.GetData(DataFormats.FileDrop) is string[] { Length: 1 } paths
            && paths[0].EndsWith(".pk", StringComparison.OrdinalIgnoreCase) ? DragDropEffects.Copy : DragDropEffects.None;
        e.Handled = true;
    }
    void Files_Drop(object sender, DragEventArgs e)
    {
        if (e.Data.GetData(DataFormats.FileDrop) is string[] { Length: 1 } paths) LoadSource(paths[0]);
        e.Handled = true;
    }
}
