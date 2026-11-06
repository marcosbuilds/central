using System.Windows;
using System.Windows.Controls;
using Central.Desktop.Models;
using Central.Desktop.ViewModels;

namespace Central.Desktop.Views;

public partial class DashboardView : UserControl
{
    public event EventHandler<string>? NavigateRequested;
    public event EventHandler<ProjectModel>? ProjectRequested;

    public DashboardView()
    {
        InitializeComponent();
        Loaded += (_, _) => SelectUsageRange(RangeDayButton);
        SizeChanged += (_, _) => ApplyResponsiveLayout();
    }

    public void SetReducedMotion(bool reducedMotion) => UsageChart.SetReducedMotion(reducedMotion);

    private void OpenProjects_Click(object sender, RoutedEventArgs e)
        => NavigateRequested?.Invoke(this, "Projects");

    private void OpenFeaturedProject_Click(object sender, RoutedEventArgs e)
    {
        if (DataContext is CentralViewModel viewModel && viewModel.FeaturedProject is not null)
        {
            ProjectRequested?.Invoke(this, viewModel.FeaturedProject);
        }
    }

    private void UsageRange_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button)
        {
            SelectUsageRange(button);
        }
    }

    private void SelectUsageRange(Button selected)
    {
        var range = selected.Tag as string ?? "1 dia";
        UsageChart.SetRange(range);
        UsageRangeLabel.Text = $"Período selecionado: {range} · dados N/D";

        foreach (var button in new[] { RangeDayButton, RangeWeekButton, RangeMonthButton })
        {
            button.ClearValue(BackgroundProperty);
            button.ClearValue(ForegroundProperty);
        }

        selected.Background = (System.Windows.Media.Brush)FindResource("AccentSoftBrush");
        selected.Foreground = (System.Windows.Media.Brush)FindResource("AccentBrush");
    }

    private void HomeSplit_SizeChanged(object sender, SizeChangedEventArgs e) => ApplyResponsiveLayout();

    private void ApplyResponsiveLayout()
    {
        if (!IsInitialized || HomeSplit is null)
        {
            return;
        }

        // Keep the two functional regions in one surface on desktop, then stack
        // them before the content becomes cramped. The surrounding surface owns
        // the hierarchy; the regions use only a divider, not nested cards.
        var compact = ActualWidth > 0 && ActualWidth < 900;

        HomeSplit.RowDefinitions[1].Height = compact ? GridLength.Auto : new GridLength(0);
        HomeSplit.ColumnDefinitions[0].Width = new GridLength(1, GridUnitType.Star);
        HomeSplit.ColumnDefinitions[1].Width = compact ? new GridLength(1, GridUnitType.Star) : new GridLength(0.84, GridUnitType.Star);

        Grid.SetRow(UsagePanel, compact ? 1 : 0);
        Grid.SetColumn(UsagePanel, compact ? 0 : 1);
        FocusPanel.Margin = new Thickness(0);
        UsagePanel.Margin = compact ? new Thickness(0, 18, 0, 0) : new Thickness(0);
        FocusPanel.BorderThickness = compact ? new Thickness(0) : new Thickness(0, 0, 1, 0);
        FocusPanel.Padding = compact ? new Thickness(0, 0, 0, 0) : new Thickness(0, 0, 18, 0);
        UsagePanel.Padding = compact ? new Thickness(0) : new Thickness(18, 0, 0, 0);
    }
}
