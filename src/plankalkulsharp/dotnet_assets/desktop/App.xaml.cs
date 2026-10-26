using System.Windows;

namespace PlankalkulMachine;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        if (e.Args.Any(a => a is "--help" or "-h"))
        {
            MessageBox.Show("Plankalkül Machine\n\n--python <путь>  путь к Python\n--worker <путь>  PlankalkulWorker.dll\n--source <файл.pk>  открыть программу", "Справка");
            Shutdown();
            return;
        }
        var options = MachineOptions.Parse(e.Args);
        new MainWindow(options).Show();
    }
}
