using System.ComponentModel;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Data;
using Central.Desktop.Models;

namespace Central.Desktop.Views;

public partial class ProjectsView : UserControl
{
    public event EventHandler<ProjectModel>? ProjectOpened;

    public ProjectsView()
    {
        InitializeComponent();
    }

    private void SearchBox_TextChanged(object sender, TextChangedEventArgs e)
    {
        if (ProjectList is null)
        {
            return;
        }

        var view = CollectionViewSource.GetDefaultView(ProjectList.ItemsSource);
        var query = SearchBox.Text.Trim();
        view.Filter = item =>
        {
            if (item is not ProjectModel project)
            {
                return false;
            }

            return string.IsNullOrWhiteSpace(query)
                || project.Name.Contains(query, StringComparison.OrdinalIgnoreCase)
                || project.Id.Contains(query, StringComparison.OrdinalIgnoreCase)
                || project.Modules.Any(module => module.Contains(query, StringComparison.OrdinalIgnoreCase));
        };
        view.Refresh();

        var resultCount = ProjectList.Items.Cast<object>().Count();
        ProjectCountText.Text = string.IsNullOrWhiteSpace(query)
            ? $"{resultCount} projetos no catálogo local"
            : $"{resultCount} resultado(s) para a busca";
        var showEmptyState = resultCount == 0;
        EmptyStateBorder.Visibility = showEmptyState ? Visibility.Visible : Visibility.Collapsed;
        AutomationProperties.SetIsOffscreenBehavior(
            EmptyStateBorder,
            showEmptyState ? IsOffscreenBehavior.Onscreen : IsOffscreenBehavior.Offscreen);
    }

    private void ClearSearch_Click(object sender, RoutedEventArgs e) => SearchBox.Clear();

    private void OpenProject_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.DataContext is ProjectModel project)
        {
            ProjectOpened?.Invoke(this, project);
        }
    }

}
