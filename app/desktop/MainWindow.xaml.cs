using System.ComponentModel;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Media.Media3D;
using System.Windows.Threading;
using Central.Desktop.Models;
using Central.Desktop.ViewModels;
using Central.Desktop.Views;

namespace Central.Desktop;

public partial class MainWindow : Window
{
    private readonly CentralViewModel _viewModel;
    private readonly DashboardView _dashboardView;
    private readonly ProjectsView _projectsView;
    private readonly ProjectView _projectView;
    private bool _isSidebarCollapsed = true;
    private bool _isSettingsOpen;
    private bool _reduceMotion;
    private Button? _settingsInvoker;

    public MainWindow()
    {
        InitializeComponent();

        _viewModel = new CentralViewModel();
        DataContext = _viewModel;

        _dashboardView = new DashboardView { DataContext = _viewModel };
        _projectsView = new ProjectsView { DataContext = _viewModel };
        _projectView = new ProjectView { DataContext = _viewModel };

        _dashboardView.NavigateRequested += (_, page) => ShowPage(page);
        _dashboardView.ProjectRequested += (_, project) => OpenProject(project);
        _projectsView.ProjectOpened += (_, project) => OpenProject(project);

        _reduceMotion = !SystemParameters.ClientAreaAnimation;
        ReducedMotionCheckBox.IsChecked = _reduceMotion;
        _dashboardView.SetReducedMotion(_reduceMotion);

        _viewModel.PropertyChanged += ViewModel_PropertyChanged;
        PreviewKeyDown += MainWindow_PreviewKeyDown;
        Closing += MainWindow_Closing;

        SidebarColumn.Width = new GridLength(78);
        SetSidebarCollapsedVisual(true);
        ShowPage("Dashboard");
        _ = _viewModel.CheckGatewayAsync();
    }

    private void ViewModel_PropertyChanged(object? sender, PropertyChangedEventArgs e)
    {
        if (e.PropertyName is nameof(CentralViewModel.IsToastVisible)
            or nameof(CentralViewModel.ToastMessage)
            or nameof(CentralViewModel.ToastState))
        {
            ToastText.Text = _viewModel.ToastMessage;
            ToastBorder.Visibility = _viewModel.IsToastVisible ? Visibility.Visible : Visibility.Collapsed;
            UpdateToastChrome();
        }
    }

    private void UpdateToastChrome()
    {
        var (background, border, dot) = _viewModel.ToastState switch
        {
            OperationState.Pending => ("AmberSoftBrush", "AmberBrush", "AmberBrush"),
            OperationState.Denied or OperationState.Error => ("RedSoftBrush", "RedBrush", "RedBrush"),
            _ => ("SuccessSoftBrush", "SuccessBrush", "SuccessBrush")
        };

        ToastBorder.Background = (System.Windows.Media.Brush)FindResource(background);
        ToastBorder.BorderBrush = (System.Windows.Media.Brush)FindResource(border);
        ToastDot.Fill = (System.Windows.Media.Brush)FindResource(dot);
    }

    private void Navigation_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.Tag is string page)
        {
            ShowPage(page);
        }
    }

    private void ShowPage(string page)
    {
        var (view, title) = page switch
        {
            "Projects" => (_projectsView as UserControl, "Projetos"),
            "Project" when _viewModel.SelectedProject is not null => (_projectView as UserControl, _viewModel.SelectedProject.Name),
            _ => (_dashboardView as UserControl, "Home")
        };

        ContentHost.Content = view;
        HeaderTitle.Text = title;
        AutomationProperties.SetName(ContentHost, $"Página {title}");
        ProjectLabel.Text = _viewModel.SelectedProject?.Name ?? "Projeto";
        ProjectNav.Visibility = _viewModel.SelectedProject is null ? Visibility.Collapsed : Visibility.Visible;
        ProjectNav.IsEnabled = _viewModel.SelectedProject is not null;
        SetActiveNav(page == "Project" && _viewModel.SelectedProject is null ? "Dashboard" : page);
        ContentHost.Focus();
        if (page == "Project")
        {
            _projectView.RefreshView();
        }
    }

    private void OpenProject(ProjectModel project)
    {
        _viewModel.SelectProject(project);
        ShowPage("Project");
    }

    private void SetActiveNav(string page)
    {
        var buttons = new[] { DashboardNav, ProjectsNav, ProjectNav };
        foreach (var button in buttons)
        {
            button.ClearValue(BackgroundProperty);
            button.ClearValue(ForegroundProperty);
            AutomationProperties.SetItemStatus(button, string.Empty);
        }

        var active = page switch
        {
            "Projects" => ProjectsNav,
            "Project" => ProjectNav,
            _ => DashboardNav
        };
        active.Background = (System.Windows.Media.Brush)FindResource("AccentSoftBrush");
        active.Foreground = (System.Windows.Media.Brush)FindResource("AccentBrush");
        AutomationProperties.SetItemStatus(active, "Página atual");
    }

    private void ToggleSidebar_Click(object sender, RoutedEventArgs e)
    {
        _isSidebarCollapsed = !_isSidebarCollapsed;
        var target = _isSidebarCollapsed ? 78d : 238d;
        var current = SidebarColumn.ActualWidth > 0 ? SidebarColumn.ActualWidth : SidebarColumn.Width.Value;

        if (_reduceMotion)
        {
            SidebarColumn.Width = new GridLength(target);
        }
        else
        {
            var animation = new GridLengthAnimation
            {
                From = new GridLength(current),
                To = new GridLength(target),
                Duration = new Duration(TimeSpan.FromMilliseconds(170))
            };
            SidebarColumn.BeginAnimation(ColumnDefinition.WidthProperty, animation);
        }

        var toggleRotation = SidebarToggleIcon.RenderTransform as System.Windows.Media.RotateTransform;
        if (toggleRotation is null)
        {
            toggleRotation = new System.Windows.Media.RotateTransform(0, 0.5, 0.5);
            SidebarToggleIcon.RenderTransform = toggleRotation;
        }

        var rotationTarget = _isSidebarCollapsed ? 180d : 0d;
        if (_reduceMotion)
        {
            toggleRotation.BeginAnimation(System.Windows.Media.RotateTransform.AngleProperty, null);
            toggleRotation.Angle = rotationTarget;
        }
        else
        {
            var rotation = new DoubleAnimation
            {
                To = rotationTarget,
                Duration = new Duration(TimeSpan.FromMilliseconds(170)),
                EasingFunction = new QuadraticEase()
            };
            toggleRotation.BeginAnimation(System.Windows.Media.RotateTransform.AngleProperty, rotation);
        }

        CollapseSidebarButton.ToolTip = _isSidebarCollapsed ? "Expandir menu lateral" : "Recolher menu lateral";
        AutomationProperties.SetName(CollapseSidebarButton, _isSidebarCollapsed ? "Expandir menu lateral" : "Recolher menu lateral");
        SetSidebarCollapsedVisual(_isSidebarCollapsed);
    }

    private void SetSidebarCollapsedVisual(bool collapsed)
    {
        var visibility = collapsed ? Visibility.Collapsed : Visibility.Visible;
        SidebarContent.Margin = collapsed ? new Thickness(10, 14, 10, 12) : new Thickness(14, 14, 14, 12);
        BrandIdentity.Visibility = visibility;
        BrandMark.Visibility = visibility;
        BrandText.Visibility = visibility;
        NavigateCaption.Visibility = visibility;
        ContextCaption.Visibility = visibility;
        DashboardLabel.Visibility = visibility;
        ProjectsLabel.Visibility = visibility;
        ProjectLabel.Visibility = visibility;
        UserText.Visibility = visibility;
        UserAvatar.Visibility = collapsed ? Visibility.Collapsed : Visibility.Visible;
        UserAvatarColumn.Width = collapsed ? new GridLength(0) : new GridLength(32);
        UserTextColumn.Width = collapsed ? new GridLength(0) : new GridLength(1, GridUnitType.Star);
        UserSettingsColumn.Width = collapsed ? new GridLength(28) : new GridLength(28);
        SettingsGlyph.Visibility = Visibility.Visible;
        Grid.SetColumn(CollapseSidebarButton, collapsed ? 0 : 1);
        CollapseSidebarButton.HorizontalAlignment = collapsed ? HorizontalAlignment.Center : HorizontalAlignment.Right;

        foreach (var button in new[] { DashboardNav, ProjectsNav, ProjectNav })
        {
            button.HorizontalContentAlignment = collapsed ? HorizontalAlignment.Center : HorizontalAlignment.Left;
            button.Padding = collapsed ? new Thickness(8) : new Thickness(12, 10, 12, 10);
            button.ToolTip = button.Tag switch
            {
                "Dashboard" => "Home",
                "Projects" => "Projetos",
                _ => "Projeto atual"
            };
        }

        UserSettingsButton.HorizontalContentAlignment = collapsed ? HorizontalAlignment.Center : HorizontalAlignment.Stretch;
        UserSettingsButton.Padding = collapsed ? new Thickness(2) : new Thickness(8);
    }

    private void OpenSettings_Click(object sender, RoutedEventArgs e)
    {
        _settingsInvoker = sender as Button ?? UserSettingsButton;
        _isSettingsOpen = true;
        SettingsOverlay.Visibility = Visibility.Visible;
        Dispatcher.BeginInvoke(DispatcherPriority.Input, new Action(() => ReducedMotionCheckBox.Focus()));
    }

    private void CloseSettings_Click(object sender, RoutedEventArgs e) => CloseSettingsPanel();

    private async void CheckGateway_Click(object sender, RoutedEventArgs e)
    {
        await _viewModel.CheckGatewayAsync();
    }

    private async void ConnectSync_Click(object sender, RoutedEventArgs e)
    {
        _viewModel.SetSyncPassword(SyncPasswordBox.Password);
        await _viewModel.ConnectConfiguredSyncAsync();
    }

    private async void PauseSync_Click(object sender, RoutedEventArgs e)
    {
        await _viewModel.PauseSyncAsync();
    }

    private async void MainWindow_Closing(object? sender, CancelEventArgs e)
    {
        await _viewModel.ShutdownAsync();
    }

    private void CloseSettingsPanel()
    {
        _isSettingsOpen = false;
        SettingsOverlay.Visibility = Visibility.Collapsed;
        _settingsInvoker?.Focus();
        _settingsInvoker = null;
    }

    private void ReducedMotion_Changed(object sender, RoutedEventArgs e)
    {
        _reduceMotion = ReducedMotionCheckBox.IsChecked == true;
        if (_dashboardView is not null)
        {
            _dashboardView.SetReducedMotion(_reduceMotion);
        }
    }

    private void MainWindow_PreviewKeyDown(object sender, KeyEventArgs e)
    {
        if (_isSettingsOpen && e.Key == Key.Escape)
        {
            e.Handled = true;
            CloseSettingsPanel();
            return;
        }

        if (_isSettingsOpen && e.Key == Key.Tab && Keyboard.FocusedElement is DependencyObject focused && !IsDescendantOf(SettingsPanel, focused))
        {
            e.Handled = true;
            if (Keyboard.Modifiers.HasFlag(ModifierKeys.Shift))
            {
                CloseSettingsButton.Focus();
            }
            else
            {
                ReducedMotionCheckBox.Focus();
            }
        }
    }

    private static bool IsDescendantOf(DependencyObject ancestor, DependencyObject? child)
    {
        while (child is not null)
        {
            if (ReferenceEquals(child, ancestor))
            {
                return true;
            }

            child = child is Visual or Visual3D
                ? VisualTreeHelper.GetParent(child)
                : LogicalTreeHelper.GetParent(child);
        }

        return false;
    }

    private void DragSurface_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ClickCount == 2)
        {
            ToggleWindowState();
            return;
        }

        try
        {
            DragMove();
        }
        catch (InvalidOperationException)
        {
            // The window can lose mouse capture during a fast double click.
        }
    }

    private void Minimize_Click(object sender, RoutedEventArgs e) => WindowState = WindowState.Minimized;

    private void Maximize_Click(object sender, RoutedEventArgs e) => ToggleWindowState();

    private void ToggleWindowState() => WindowState = WindowState == WindowState.Maximized ? WindowState.Normal : WindowState.Maximized;

    private void Close_Click(object sender, RoutedEventArgs e) => Close();

    private void DismissToast_Click(object sender, RoutedEventArgs e)
    {
        _viewModel.DismissToast();
        ToastBorder.Visibility = Visibility.Collapsed;
    }
}
