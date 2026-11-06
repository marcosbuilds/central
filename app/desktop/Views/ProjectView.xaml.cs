using System.Windows;
using System.Windows.Controls;
using Central.Desktop.Models;
using Central.Desktop.ViewModels;

namespace Central.Desktop.Views;

public partial class ProjectView : UserControl
{
    public ProjectView()
    {
        InitializeComponent();
        Loaded += (_, _) => RefreshView();
    }

    public void RefreshView()
    {
        if (DataContext is not CentralViewModel viewModel || viewModel.SelectedProject is null)
        {
            return;
        }

        LifecycleButton.Content = viewModel.SelectedProject.Status == ProjectStatus.Closed ? "Reabrir projeto" : "Fechar projeto";
    }

    private CentralViewModel? ViewModel => DataContext as CentralViewModel;

    private void ProjectTabs_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (e.Source == ProjectTabs)
        {
            RefreshView();
        }
    }

    private void NavigateTo(TabItem tab)
    {
        ProjectTabs.SelectedItem = tab;
        tab.Focus();
    }

    private void OpenWorkspace_Click(object sender, RoutedEventArgs e) => NavigateTo(WorkspaceTab);

    private void OperateGrid_SizeChanged(object sender, SizeChangedEventArgs e)
    {
        if (OperateGrid is null || OperateDecisionPanel is null || OperateBlockerPanel is null || OperateActivityPanel is null)
        {
            return;
        }

        var compact = OperateGrid.ActualWidth > 0 && OperateGrid.ActualWidth < 760;

        OperateGrid.RowDefinitions[1].Height = compact ? GridLength.Auto : GridLength.Auto;
        OperateGrid.RowDefinitions[2].Height = compact ? GridLength.Auto : new GridLength(0);
        OperateGrid.ColumnDefinitions[0].Width = new GridLength(1, GridUnitType.Star);
        OperateGrid.ColumnDefinitions[1].Width = compact ? new GridLength(0) : new GridLength(0.85, GridUnitType.Star);

        Grid.SetColumnSpan(OperateDecisionPanel, compact ? 2 : 1);
        Grid.SetRow(OperateBlockerPanel, compact ? 1 : 0);
        Grid.SetColumn(OperateBlockerPanel, compact ? 0 : 1);
        Grid.SetColumnSpan(OperateBlockerPanel, compact ? 2 : 1);
        Grid.SetRow(OperateActivityPanel, compact ? 2 : 1);

        OperateDecisionPanel.Margin = compact ? new Thickness(0, 0, 0, 16) : new Thickness(0, 0, 20, 0);
        OperateBlockerPanel.BorderThickness = compact ? new Thickness(0, 1, 0, 0) : new Thickness(1, 0, 0, 0);
        OperateBlockerPanel.Padding = compact ? new Thickness(0, 16, 0, 0) : new Thickness(20, 0, 0, 0);
        OperateBlockerPanel.Margin = compact ? new Thickness(0) : new Thickness(0);
        OperateActivityPanel.Margin = compact ? new Thickness(0, 22, 0, 0) : new Thickness(0, 22, 0, 0);
    }

    private void Task_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.Tag is ProjectTask task && ViewModel?.SelectedProject is not null)
        {
            ViewModel.SelectedProject.SelectedTask = task;
            NavigateTo(WorkspaceTab);
        }
    }

    private void AdvanceSimulation_Click(object sender, RoutedEventArgs e) => ViewModel?.AdvanceSimulation();

    private void ClaimTask_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.DataContext is ProjectTask task)
        {
            ViewModel?.ClaimTask(task);
        }
    }

    private void ApplyPatch_Click(object sender, RoutedEventArgs e)
        => ViewModel?.ApplyWorkspaceChange("lote de demonstração: validação de reservas e revisão-base");

    private void WorkspaceFile_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.Tag is WorkspaceFile file)
        {
            ViewModel?.SelectWorkspaceFile(file);
            NavigateTo(WorkspaceTab);
        }
    }

    private void StreamEvent_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.Tag is AgentStreamEvent streamEvent)
        {
            ViewModel?.SelectStreamEvent(streamEvent);
            NavigateTo(WorkspaceTab);
        }
    }

    private void Commit_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.Tag is WorkspaceCommit commit)
        {
            ViewModel?.SelectCommit(commit);
            NavigateTo(WorkspaceTab);
        }
    }

    private void Tag_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.Tag is WorkspaceTag tag)
        {
            ViewModel?.SelectTag(tag);
            NavigateTo(WorkspaceTab);
        }
    }

    private void Release_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.Tag is WorkspaceRelease release)
        {
            ViewModel?.SelectRelease(release);
            NavigateTo(WorkspaceTab);
        }
    }

    private void CreateTag_Click(object sender, RoutedEventArgs e) => ViewModel?.CreateWorkspaceTag();

    private void CreateRelease_Click(object sender, RoutedEventArgs e) => ViewModel?.CreateWorkspaceRelease();

    private void Reference_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button button || button.Tag is not WorkspaceReference reference || ViewModel is null)
        {
            return;
        }

        var result = ViewModel.OpenReference(reference);
        ViewModel.Notify(result.Message, result.State);
        if (!result.Success)
        {
            return;
        }

        var destination = reference.Kind.ToLowerInvariant() switch
        {
            "entrega" or "check" or "revisão de entrega" or "publicação" => ProveTab,
            "pessoa" or "ia" or "sessão" => CoordinationTab,
            _ => WorkspaceTab
        };
        NavigateTo(destination);
    }

    private void WorkspaceGrid_SizeChanged(object sender, SizeChangedEventArgs e)
    {
        if (WorkspaceTopGrid is null || WorkspaceLowerGrid is null)
        {
            return;
        }

        var compact = ActualWidth > 0 && ActualWidth < 980;

        WorkspaceTopGrid.RowDefinitions[0].Height = GridLength.Auto;
        WorkspaceTopGrid.RowDefinitions[1].Height = compact ? GridLength.Auto : new GridLength(0);
        WorkspaceTopGrid.RowDefinitions[2].Height = compact ? GridLength.Auto : new GridLength(0);
        WorkspaceTopGrid.ColumnDefinitions[0].Width = new GridLength(1, GridUnitType.Star);
        WorkspaceTopGrid.ColumnDefinitions[1].Width = compact ? new GridLength(1, GridUnitType.Star) : new GridLength(1.35, GridUnitType.Star);
        WorkspaceTopGrid.ColumnDefinitions[2].Width = compact ? new GridLength(1, GridUnitType.Star) : new GridLength(0.72, GridUnitType.Star);

        Grid.SetRow(WorkspaceFilesPanel, 0);
        Grid.SetColumn(WorkspaceFilesPanel, 0);
        Grid.SetRow(WorkspaceInspectorPanel, compact ? 1 : 0);
        Grid.SetColumn(WorkspaceInspectorPanel, compact ? 0 : 1);
        Grid.SetRow(WorkspaceMetaPanel, compact ? 2 : 0);
        Grid.SetColumn(WorkspaceMetaPanel, compact ? 0 : 2);

        WorkspaceFilesPanel.Margin = compact ? new Thickness(0, 0, 0, 10) : new Thickness(0, 0, 5, 0);
        WorkspaceInspectorPanel.Margin = compact ? new Thickness(0, 0, 0, 10) : new Thickness(5, 0, 5, 0);
        WorkspaceMetaPanel.Margin = compact ? new Thickness(0) : new Thickness(5, 0, 0, 0);

        WorkspaceLowerGrid.RowDefinitions[0].Height = GridLength.Auto;
        WorkspaceLowerGrid.RowDefinitions[1].Height = compact ? GridLength.Auto : new GridLength(0);
        WorkspaceLowerGrid.ColumnDefinitions[0].Width = new GridLength(1, GridUnitType.Star);
        WorkspaceLowerGrid.ColumnDefinitions[1].Width = compact ? new GridLength(1, GridUnitType.Star) : new GridLength(0.8, GridUnitType.Star);
        Grid.SetRow(WorkspaceTasksPanel, 0);
        Grid.SetColumn(WorkspaceTasksPanel, 0);
        Grid.SetRow(WorkspaceCommitsPanel, compact ? 1 : 0);
        Grid.SetColumn(WorkspaceCommitsPanel, compact ? 0 : 1);
        WorkspaceTasksPanel.Margin = compact ? new Thickness(0, 0, 0, 10) : new Thickness(0, 0, 5, 0);
        WorkspaceCommitsPanel.Margin = compact ? new Thickness(0) : new Thickness(5, 0, 0, 0);
    }

    private void PostDiscussion_Click(object sender, RoutedEventArgs e)
    {
        var body = DiscussionBox.Text.Trim();
        if (string.IsNullOrWhiteSpace(body))
        {
            ViewModel?.Notify("Escreva uma mensagem antes de publicar na thread.");
            return;
        }

        var result = ViewModel?.PostMessage(body);
        if (result?.Success == true)
        {
            DiscussionBox.Clear();
        }
    }

    private void CreateDelivery_Click(object sender, RoutedEventArgs e) => ViewModel?.CreateDelivery();

    private void ApproveDelivery_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.DataContext is DeliveryCandidate delivery)
        {
            ViewModel?.ApproveDelivery(delivery);
        }
    }

    private void IntegrateDelivery_Click(object sender, RoutedEventArgs e)
    {
        if (sender is Button button && button.DataContext is DeliveryCandidate delivery)
        {
            ViewModel?.IntegrateDelivery(delivery);
        }
    }

    private void RunQuality_Click(object sender, RoutedEventArgs e) => ViewModel?.RunQuality();

    private void Preview_Click(object sender, RoutedEventArgs e)
        => ViewModel?.Notify("Prévia local preparada apenas como simulação. A Central não conectou pipeline, servidor ou credencial externa.");

    private void LifecycleButton_Click(object sender, RoutedEventArgs e)
    {
        var project = ViewModel?.SelectedProject;
        if (project is null)
        {
            return;
        }

        var action = project.IsOpen ? "fechar" : "reabrir";
        var message = project.IsOpen
            ? "Fechar o projeto preserva a leitura, mas bloqueia escrita, reservas, integração e publicação. Confirmar?"
            : "Reabrir o projeto permite novas escritas locais; reservas antigas não serão reaproveitadas. Confirmar?";
        var confirmation = MessageBox.Show(message, $"Confirmar {action} projeto", MessageBoxButton.YesNo, MessageBoxImage.Warning);
        if (confirmation != MessageBoxResult.Yes)
        {
            return;
        }

        ViewModel?.ToggleProjectLifecycle();
        RefreshView();
    }
}
