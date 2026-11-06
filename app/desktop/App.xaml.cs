using System.IO;
using System.Windows;

namespace Central.Desktop;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        try
        {
            var window = new MainWindow();
            MainWindow = window;
            window.Show();
        }
        catch (Exception exception)
        {
            var diagnosticPath = Path.Combine(AppContext.BaseDirectory, "startup-error.log");
            File.WriteAllText(diagnosticPath, exception.ToString());
            Shutdown(1);
        }
    }
}
