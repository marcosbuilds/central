using Central.Desktop.Models;
using Central.Desktop.Services;
using Xunit;
using ProjectTaskStatus = Central.Desktop.Models.TaskStatus;

namespace Central.Desktop.Tests;

public sealed class CentralStoreTests
{
    [Fact]
    public void ResolveProjects_returns_only_matching_catalog_entries()
    {
        var store = new CentralStore();

        var matches = store.ResolveProjects("seloryn");

        var project = Assert.Single(matches);
        Assert.Equal("Seloryn", project.Name);
        Assert.Equal(ProjectStatus.Open, project.Status);
    }

    [Fact]
    public void Semantic_claim_prevents_overlapping_work_and_allows_independent_work()
    {
        var store = new CentralStore();
        var project = store.Projects.Single(item => item.Name == "Sistema de Vendas");
        var first = project.Tasks.Single(task => task.Id == "TASK-44");
        var independent = project.Tasks.Single(task => task.Id == "TASK-45");
        var overlapping = new ProjectTask("TASK-46", "Outra alteração de estoque", "Mesmo recurso lógico.", "api.inventory", "Alta", ProjectTaskStatus.Ready, "Conflito detectado", "—", "TASK-44");
        project.Tasks.Add(overlapping);

        var firstResult = store.ClaimTask(project, first, "sessão-A");
        var overlapResult = store.ClaimTask(project, overlapping, "sessão-B");
        var independentResult = store.ClaimTask(project, independent, "sessão-C");

        Assert.True(firstResult.Success);
        Assert.False(overlapResult.Success);
        Assert.Contains("api.inventory", overlapResult.Message);
        Assert.True(independentResult.Success);
    }

    [Fact]
    public void Stale_base_is_rejected_and_current_base_is_applied_once()
    {
        var store = new CentralStore();
        var project = store.Projects.Single(item => item.Name == "Seloryn");
        var baseRevision = project.WorkspaceRevision;

        var first = store.ApplyWorkspaceChange(project, "sessão-A", "primeiro lote", baseRevision);
        var stale = store.ApplyWorkspaceChange(project, "sessão-B", "lote atrasado", baseRevision);
        var current = store.ApplyWorkspaceChange(project, "sessão-B", "lote refeito", project.WorkspaceRevision);

        Assert.True(first.Success);
        Assert.False(stale.Success);
        Assert.Contains("Base obsoleta", stale.Message);
        Assert.True(current.Success);
        Assert.Equal(baseRevision + 2, project.WorkspaceRevision);
    }

    [Fact]
    public void Closed_project_blocks_writes_and_reopening_increments_generation()
    {
        var store = new CentralStore();
        var project = store.Projects.Single(item => item.Name == "Projeto Interno");
        var originalGeneration = project.Generation;
        var task = project.Tasks.Single();

        var patch = store.ApplyWorkspaceChange(project, "sessão", "tentativa fora do portão");
        var claim = store.ClaimTask(project, task, "sessão");
        var reopened = store.ToggleProjectLifecycle(project, "administrador");

        Assert.False(patch.Success);
        Assert.False(claim.Success);
        Assert.True(reopened.Success);
        Assert.Equal(ProjectStatus.Open, project.Status);
        Assert.Equal(originalGeneration + 1, project.Generation);
    }

    [Fact]
    public void Delivery_requires_evidence_and_keeps_deploy_separate()
    {
        var store = new CentralStore();
        var project = store.Projects.Single(item => item.Name == "Seloryn");
        var delivery = project.Deliveries.Single(item => item.Id == "DEL-007");

        var approved = store.ApproveDelivery(project, delivery, "revisor-independente");
        var integrated = store.IntegrateDelivery(project, delivery, "gateway");

        Assert.True(approved.Success);
        Assert.True(integrated.Success);
        Assert.Equal(DeliveryStatus.Integrated, delivery.Status);
        Assert.Contains(project.Activity, eventItem => eventItem.Type == "delivery.integrated");
    }

    [Fact]
    public void Seed_preserves_nine_people_and_marks_offline_agent_as_pending()
    {
        var store = new CentralStore();

        Assert.Equal(9, store.Team.Count);
        Assert.Equal(4, store.ActiveSessions.Count(session => session.IsOnline));
        Assert.Contains(store.ActiveSessions, session => !session.IsOnline && session.ConnectionLabel.Contains("Pendente"));
    }

    [Fact]
    public void Local_pulse_reveals_ordered_event_without_claiming_external_stream()
    {
        var store = new CentralStore();
        var project = store.Projects.Single(item => item.Name == "Seloryn");
        var initialCount = project.StreamEvents.Count;
        var initialStep = project.SimulationStep;

        var result = store.AdvanceSimulation(project, "sessão de teste");

        Assert.True(result.Success);
        Assert.Equal(initialCount + 1, project.StreamEvents.Count);
        Assert.Equal(initialStep + 1, project.SimulationStep);
        Assert.Equal(201, project.StreamEvents[0].Sequence);
        Assert.Equal(project.StreamEvents[0], project.SelectedStreamEvent);
        Assert.Contains(project.Activity, item => item.Type == "task.claimed");
        Assert.Contains("nenhuma fonte externa", result.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Workspace_patch_creates_titled_local_commit_and_tags_require_open_project()
    {
        var store = new CentralStore();
        var project = store.Projects.Single(item => item.Name == "Seloryn");
        var originalCommitCount = project.WorkspaceCommits.Count;

        var patch = store.ApplyWorkspaceChange(project, "sessão", "validar referências");
        var tag = store.CreateWorkspaceTag(project, "sessão");
        var release = store.CreateWorkspaceRelease(project, "sessão");

        Assert.True(patch.Success);
        Assert.Equal(originalCommitCount + 1, project.WorkspaceCommits.Count);
        Assert.Contains("validar referências", project.WorkspaceCommits[0].Title);
        Assert.True(tag.Success);
        Assert.True(release.Success);
        Assert.Contains(project.WorkspaceTags, item => item.TargetRevision == project.WorkspaceRevisionLabel);
        Assert.Contains(project.WorkspaceReleases, item => item.Status.Contains("SEM DEPLOY"));
    }

    [Fact]
    public void Closed_project_blocks_pulse_and_local_versioning_actions()
    {
        var store = new CentralStore();
        var project = store.Projects.Single(item => item.Name == "Projeto Interno");

        var pulse = store.AdvanceSimulation(project, "sessão");
        var tag = store.CreateWorkspaceTag(project, "sessão");
        var release = store.CreateWorkspaceRelease(project, "sessão");

        Assert.False(pulse.Success);
        Assert.False(tag.Success);
        Assert.False(release.Success);
        Assert.Equal(ProjectStatus.Closed, project.Status);
    }

    [Fact]
    public void Reference_resolution_selects_the_canonical_local_object()
    {
        var viewModel = new Central.Desktop.ViewModels.CentralViewModel();
        viewModel.SelectProject(viewModel.Projects.Single(item => item.Name == "Seloryn"));
        var project = viewModel.SelectedProject;
        Assert.NotNull(project);

        var fileResult = viewModel.OpenReference(new WorkspaceReference("arquivo", "README.md", "README.md"));
        var deliveryResult = viewModel.OpenReference(new WorkspaceReference("entrega", "DEL-007", "DEL-007"));

        Assert.True(fileResult.Success);
        Assert.Equal("README.md", project!.SelectedWorkspaceFile?.Path);
        Assert.True(deliveryResult.Success);
        Assert.Equal("DEL-007", project.SelectedDelivery?.Id);
    }

    [Fact]
    public void New_session_does_not_guess_a_project_or_a_next_task()
    {
        var viewModel = new Central.Desktop.ViewModels.CentralViewModel();

        Assert.Null(viewModel.SelectedProject);
        Assert.Null(viewModel.FeaturedProject);
        Assert.Null(viewModel.FeaturedTask);

        var project = viewModel.Projects.Single(item => item.Name == "Seloryn");
        viewModel.SelectProject(project);

        Assert.Same(project, viewModel.FeaturedProject);
        Assert.Equal("TASK-29", viewModel.FeaturedTask?.Id);
    }

    [Fact]
    public void Delivery_integration_is_only_available_after_local_approval()
    {
        var viewModel = new Central.Desktop.ViewModels.CentralViewModel();
        viewModel.SelectProject(viewModel.Projects.Single(item => item.Name == "Seloryn"));
        var project = viewModel.SelectedProject;
        Assert.NotNull(project);
        var delivery = project!.Deliveries.Single(item => item.Id == "DEL-007");

        Assert.False(delivery.CanIntegrate);
        viewModel.ApproveDelivery(delivery);

        Assert.True(delivery.CanIntegrate);
    }
}
