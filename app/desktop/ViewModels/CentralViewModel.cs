using System.IO;
using System.Net.Http;
using System.Text.Json;
using Central.Core.Connectivity;
using Central.Desktop.Models;
using Central.Desktop.Services;

namespace Central.Desktop.ViewModels;

public sealed class CentralViewModel : ObservableObject
{
    private string _toastMessage = string.Empty;
    private bool _isToastVisible;
    private OperationState _toastState = OperationState.Success;
    private readonly GatewayHealthClient _gatewayHealthClient = new();
    private readonly Uri _gatewayBaseUri = ResolveGatewayBaseUri();
    private readonly CentralSyncRuntime _syncRuntime = new();
    private readonly SemaphoreSlim _syncOperationLock = new(1, 1);
    private GatewayHealthSnapshot _gatewayHealth = GatewayHealthSnapshot.Pending;
    private bool _gatewayCheckInProgress;
    private string _syncSupabaseUrl = "https://ydouynbssldpjhlnawtm.supabase.co";
    private string _syncPublishableKey = string.Empty;
    private string _syncEmail = string.Empty;
    private string _syncOrganizationId = string.Empty;
    private string _syncProjectId = string.Empty;
    private string _syncFolder = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        "Central",
        "shared-test");
    private string _syncMode = "receive-only";
    private string _syncPassword = string.Empty;

    public CentralViewModel()
    {
        Store = new CentralStore();
        RequestLogs = CreateRequestLogs();
        LoadSyncSettings();
        _syncRuntime.StatusChanged += SyncRuntime_StatusChanged;
        _syncRuntime.ProjectEventReceived += SyncRuntime_ProjectEventReceived;
        _ = _syncRuntime.StartLocalAsync();
    }

    public CentralStore Store { get; }
    public ProjectModel? SelectedProject => Store.SelectedProject;
    public ProjectModel? FeaturedProject => Store.SelectedProject;
    public ProjectTask? FeaturedTask => FeaturedProject?.NextActionableTask;
    public string HomeTitle => FeaturedProject is null ? "Contexto" : "Triagem";
    public string HomeSubtitle => FeaturedProject is null
        ? "Nenhum projeto em foco. Escolha uma bancada para continuar."
        : "Um projeto em foco. Exceções visíveis. Nenhuma fonte externa fingida.";
    public string HomeSummaryLabel => FeaturedProject is null
        ? "RESUMO DO CATÁLOGO · FIXTURE LOCAL"
        : "TRIAGEM · FIXTURE LOCAL";
    public string HomeBlockedLabel => FormatCount(
        FeaturedProject?.BlockedTaskCount ?? BlockedCount,
        "bloqueio",
        "bloqueios");
    public string HomeReviewLabel => FormatCount(
        FeaturedProject?.Deliveries.Count(delivery => delivery.Status == DeliveryStatus.InReview) ?? ReviewCount,
        "em revisão",
        "em revisão");
    public IEnumerable<ProjectModel> Projects => Store.Projects;
    public IEnumerable<ActivityEvent> RecentActivity => Store.RecentActivity;
    public IEnumerable<AgentSession> ActiveSessions => Store.ActiveSessions;
    public IEnumerable<TeamMember> TeamMembers => Store.Team;
    public IReadOnlyList<RequestLogEntry> RequestLogs { get; }

    public int ActiveProjectCount => Store.Projects.Count(project => project.Status == ProjectStatus.Open);
    public int ReviewCount => Store.Projects.Sum(project => project.Deliveries.Count(delivery => delivery.Status == DeliveryStatus.InReview));
    public int BlockedCount => Store.Projects.Sum(project => project.BlockedTaskCount);
    public int QualityAlertCount => Store.Projects.Sum(project => project.QualityChecks.Count(check => check.Status != "PASS"));
    public int ConnectedAgentCount => Store.ActiveSessions.Count(session => session.IsOnline);
    public int OfflineSessionCount => Store.ActiveSessions.Count(session => !session.IsOnline);
    public string LocalModeLabel => "MODO LOCAL · DADOS LOCAIS";
    public string LocalModeDescription => SyncStatus.State is CentralSyncConnectionState.Connected
        ? "Arquivos via Syncthing; identidade, estado e eventos via Supabase."
        : "Fixtures locais continuam disponíveis; a sincronização só é afirmada quando o agente e a sessão respondem.";
    public Uri GatewayBaseUri => _gatewayBaseUri;
    public string GatewayUrl => _gatewayBaseUri.ToString().TrimEnd('/');
    public bool IsGatewayCheckInProgress => _gatewayCheckInProgress;
    public string GatewayStatusLabel => _gatewayCheckInProgress
        ? "SERVIDOR · VERIFICANDO"
        : _gatewayHealth.IsReachable
            ? "SERVIDOR · ALCANÇÁVEL"
            : "SERVIDOR · PENDENTE";
    public string GatewayStatusDetail => _gatewayCheckInProgress
        ? $"Consultando /healthz em {GatewayUrl}"
        : _gatewayHealth.IsReachable
            ? $"{_gatewayHealth.Deployment} · gateway v{_gatewayHealth.Version} · resposta de saúde confirmada"
            : $"{_gatewayHealth.Error ?? "Ainda não verificado"} · {GatewayUrl}";
    public CentralSyncStatus SyncStatus => _syncRuntime.Status;
    public string SyncStatusLabel => SyncStatus.Label;
    public string SyncStatusDetail => SyncStatus.Detail;
    public bool IsSyncConnected => SyncStatus.State == CentralSyncConnectionState.Connected;
    public string SyncSupabaseUrl
    {
        get => _syncSupabaseUrl;
        set => SetProperty(ref _syncSupabaseUrl, value);
    }

    public string SyncPublishableKey
    {
        get => _syncPublishableKey;
        set => SetProperty(ref _syncPublishableKey, value);
    }

    public string SyncEmail
    {
        get => _syncEmail;
        set => SetProperty(ref _syncEmail, value);
    }

    public string SyncOrganizationId
    {
        get => _syncOrganizationId;
        set => SetProperty(ref _syncOrganizationId, value);
    }

    public string SyncProjectId
    {
        get => _syncProjectId;
        set => SetProperty(ref _syncProjectId, value);
    }

    public string SyncFolder
    {
        get => _syncFolder;
        set => SetProperty(ref _syncFolder, value);
    }

    public string SyncMode
    {
        get => _syncMode;
        set => SetProperty(ref _syncMode, value);
    }

    public IReadOnlyList<string> SyncModes { get; } = new[]
    {
        "receive-only",
        "send-only",
        "send-receive",
    };

    public void SetSyncPassword(string password) => _syncPassword = password;
    public string ToastMessage
    {
        get => _toastMessage;
        private set => SetProperty(ref _toastMessage, value);
    }

    public bool IsToastVisible
    {
        get => _isToastVisible;
        private set => SetProperty(ref _isToastVisible, value);
    }

    public OperationState ToastState
    {
        get => _toastState;
        private set => SetProperty(ref _toastState, value);
    }

    public async Task CheckGatewayAsync(CancellationToken cancellationToken = default)
    {
        if (_gatewayCheckInProgress)
        {
            return;
        }

        _gatewayCheckInProgress = true;
        RaiseGatewayState();

        try
        {
            _gatewayHealth = await _gatewayHealthClient.CheckAsync(_gatewayBaseUri, cancellationToken);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            return;
        }
        finally
        {
            _gatewayCheckInProgress = false;
            RaiseGatewayState();
        }
    }

    public async Task ConnectConfiguredSyncAsync(CancellationToken cancellationToken = default)
    {
        await _syncOperationLock.WaitAsync(cancellationToken);
        try
        {
            await ConnectConfiguredSyncCoreAsync(cancellationToken);
        }
        finally
        {
            _syncOperationLock.Release();
        }
    }

    private async Task ConnectConfiguredSyncCoreAsync(CancellationToken cancellationToken)
    {
        var options = ResolveSupabaseOptions();
        var email = string.IsNullOrWhiteSpace(SyncEmail)
            ? Environment.GetEnvironmentVariable("CENTRAL_SUPABASE_EMAIL")
            : SyncEmail.Trim();
        var password = string.IsNullOrWhiteSpace(_syncPassword)
            ? Environment.GetEnvironmentVariable("CENTRAL_SUPABASE_PASSWORD")
            : _syncPassword;
        var organizationId = string.IsNullOrWhiteSpace(SyncOrganizationId)
            ? Environment.GetEnvironmentVariable("CENTRAL_ORGANIZATION_ID")
            : SyncOrganizationId.Trim();
        var projectId = string.IsNullOrWhiteSpace(SyncProjectId)
            ? Environment.GetEnvironmentVariable("CENTRAL_PROJECT_ID")
            : SyncProjectId.Trim();
        var folder = string.IsNullOrWhiteSpace(SyncFolder)
            ? Environment.GetEnvironmentVariable("CENTRAL_SYNC_FOLDER")
                ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Central", "shared-test")
            : SyncFolder.Trim();
        var mode = string.IsNullOrWhiteSpace(SyncMode)
            ? Environment.GetEnvironmentVariable("CENTRAL_SYNC_MODE") ?? "receive-only"
            : SyncMode;

        if (options is null || string.IsNullOrWhiteSpace(email) || string.IsNullOrWhiteSpace(password)
            || !Guid.TryParse(organizationId, out var parsedOrganizationId)
            || !Guid.TryParse(projectId, out var parsedProjectId))
        {
            Notify("Sincronização não ativada: defina CENTRAL_SUPABASE_URL, a chave publishable, e-mail, senha, CENTRAL_ORGANIZATION_ID e CENTRAL_PROJECT_ID. Nenhum arquivo foi enviado.", OperationState.Pending);
            return;
        }

        try
        {
            await _syncRuntime.ConnectAsync(
                options,
                email,
                password,
                parsedOrganizationId,
                parsedProjectId,
                folder,
                mode,
                cancellationToken);
            SaveSyncSettings();
            _syncPassword = string.Empty;
            Notify("Sincronização autenticada. O estado da pasta e os eventos serão atualizados conforme os dois dispositivos responderem.");
        }
        catch (Exception exception) when (exception is InvalidOperationException or ArgumentException or HttpRequestException or SupabaseRequestException)
        {
            Notify($"Sincronização não ativada: {exception.Message}", OperationState.Error);
        }
    }

    public async Task PauseSyncAsync()
    {
        await _syncOperationLock.WaitAsync();
        try
        {
            await _syncRuntime.StopAsync();
            Notify("Sincronização pausada sem apagar arquivos nem conflitos.", OperationState.Pending);
        }
        finally
        {
            _syncOperationLock.Release();
        }
    }

    public async Task ShutdownAsync()
    {
        await _syncOperationLock.WaitAsync();
        try
        {
            await _syncRuntime.DisposeAsync();
        }
        finally
        {
            _syncOperationLock.Release();
        }
    }

    public void SelectProject(ProjectModel project)
    {
        Store.SelectedProject = project;
        Raise(nameof(SelectedProject));
        Raise(nameof(FeaturedProject));
        Raise(nameof(FeaturedTask));
        RaiseHomeState();
    }

    public OperationResult ClaimTask(ProjectTask task)
    {
        var project = SelectedProject;
        var result = project is null
            ? new OperationResult(false, "Selecione um projeto antes de reservar uma tarefa.", OperationState.Denied)
            : Store.ClaimTask(project, task, "Local developer · local session");
        Notify(result.Message, result.State);
        RefreshMetrics();
        return result;
    }

    public OperationResult ApplyWorkspaceChange(string summary)
    {
        var project = SelectedProject;
        var result = project is null
            ? new OperationResult(false, "Selecione um projeto antes de aplicar uma alteração.", OperationState.Denied)
            : Store.ApplyWorkspaceChange(project, "Local developer · local session", summary);
        Notify(result.Message, result.State);
        RefreshMetrics();
        return result;
    }

    public OperationResult AdvanceSimulation()
    {
        var project = SelectedProject;
        var result = project is null
            ? new OperationResult(false, "Selecione um projeto antes de avançar o Pulso local.", OperationState.Denied)
            : Store.AdvanceSimulation(project, "Local developer · local session");
        Notify(result.Message, result.State);
        RefreshMetrics();
        return result;
    }

    public OperationResult CreateWorkspaceTag()
    {
        var project = SelectedProject;
        var result = project is null
            ? new OperationResult(false, "Selecione um projeto antes de criar uma tag local.", OperationState.Denied)
            : Store.CreateWorkspaceTag(project, "Local developer · local session");
        Notify(result.Message, result.State);
        RefreshMetrics();
        return result;
    }

    public OperationResult CreateWorkspaceRelease()
    {
        var project = SelectedProject;
        var result = project is null
            ? new OperationResult(false, "Selecione um projeto antes de criar uma release local.", OperationState.Denied)
            : Store.CreateWorkspaceRelease(project, "Local developer · local session");
        Notify(result.Message, result.State);
        RefreshMetrics();
        return result;
    }

    public void SelectWorkspaceFile(WorkspaceFile file)
    {
        if (SelectedProject is null)
        {
            return;
        }

        SelectedProject.SelectedWorkspaceFile = file;
        SelectedProject.SelectedWorkspaceCommit = null;
        SelectedProject.SelectedWorkspaceTag = null;
        SelectedProject.SelectedWorkspaceRelease = null;
    }

    public void SelectStreamEvent(AgentStreamEvent streamEvent)
    {
        if (SelectedProject is null)
        {
            return;
        }

        SelectedProject.SelectedStreamEvent = streamEvent;
    }

    public void SelectCommit(WorkspaceCommit commit)
    {
        if (SelectedProject is null)
        {
            return;
        }

        SelectedProject.SelectedWorkspaceCommit = commit;
        SelectedProject.SelectedWorkspaceTag = null;
        SelectedProject.SelectedWorkspaceRelease = null;
    }

    public void SelectTag(WorkspaceTag tag)
    {
        if (SelectedProject is null)
        {
            return;
        }

        SelectedProject.SelectedWorkspaceTag = tag;
        SelectedProject.SelectedWorkspaceCommit = null;
        SelectedProject.SelectedWorkspaceRelease = null;
    }

    public void SelectRelease(WorkspaceRelease release)
    {
        if (SelectedProject is null)
        {
            return;
        }

        SelectedProject.SelectedWorkspaceRelease = release;
        SelectedProject.SelectedWorkspaceCommit = null;
        SelectedProject.SelectedWorkspaceTag = null;
    }

    public void SelectDelivery(DeliveryCandidate delivery)
    {
        if (SelectedProject is null)
        {
            return;
        }

        SelectedProject.SelectedDelivery = delivery;
    }

    public OperationResult OpenReference(WorkspaceReference reference)
    {
        if (!reference.IsResolvable || SelectedProject is null)
        {
            return new OperationResult(false, reference.Hint, OperationState.Pending);
        }

        var project = SelectedProject;
        switch (reference.Kind.ToLowerInvariant())
        {
            case "arquivo":
                var file = project.WorkspaceFiles.FirstOrDefault(item => string.Equals(item.Path, reference.TargetId, StringComparison.OrdinalIgnoreCase));
                if (file is null)
                {
                    return new OperationResult(false, "O arquivo não está no manifesto local.", OperationState.Pending);
                }

                SelectWorkspaceFile(file);
                return new OperationResult(true, $"Arquivo {file.Path} aberto no workspace local.");

            case "tarefa":
                var task = project.Tasks.FirstOrDefault(item => string.Equals(item.Id, reference.TargetId, StringComparison.OrdinalIgnoreCase));
                if (task is null)
                {
                    return new OperationResult(false, "A tarefa não está no contexto selecionado.", OperationState.Pending);
                }

                project.SelectedTask = task;
                return new OperationResult(true, $"Tarefa {task.Id} selecionada no planejamento local.");

            case "tag":
                var tag = project.WorkspaceTags.FirstOrDefault(item => string.Equals(item.Name, reference.TargetId, StringComparison.OrdinalIgnoreCase));
                if (tag is null)
                {
                    return new OperationResult(false, "A tag não está no manifesto local.", OperationState.Pending);
                }

                SelectTag(tag);
                return new OperationResult(true, $"Tag {tag.Name} selecionada no versionamento local.");

            case "revisão":
                var revisionEvent = project.StreamEvents.FirstOrDefault(item => item.References.Any(itemReference => string.Equals(itemReference.TargetId, reference.TargetId, StringComparison.OrdinalIgnoreCase)));
                if (revisionEvent is not null)
                {
                    SelectStreamEvent(revisionEvent);
                    return new OperationResult(true, $"Revisão {reference.TargetId} selecionada no Pulso local; não é branch Git.");
                }

                return new OperationResult(false, $"A revisão {reference.TargetId} não tem evento selecionável no manifesto local.", OperationState.Pending);

            case "entrega":
                var delivery = project.Deliveries.FirstOrDefault(item => string.Equals(item.Id, reference.TargetId, StringComparison.OrdinalIgnoreCase));
                if (delivery is null)
                {
                    return new OperationResult(false, "A entrega não está no dossiê local.", OperationState.Pending);
                }

                SelectDelivery(delivery);
                return new OperationResult(true, $"Entrega {delivery.Id} selecionada no dossiê local.");

            case "evento":
                var streamEvent = project.StreamEvents.FirstOrDefault(item => string.Equals(item.EventId, reference.TargetId, StringComparison.OrdinalIgnoreCase) || string.Equals(item.SequenceLabel, reference.TargetId, StringComparison.OrdinalIgnoreCase));
                if (streamEvent is null)
                {
                    return new OperationResult(false, "O evento não está na sequência observável local.", OperationState.Pending);
                }

                SelectStreamEvent(streamEvent);
                return new OperationResult(true, $"Evento {streamEvent.SequenceLabel} selecionado no Pulso local.");

            case "commit":
                var commit = project.WorkspaceCommits.FirstOrDefault(item => string.Equals(item.Id, reference.TargetId, StringComparison.OrdinalIgnoreCase) || string.Equals(item.RevisionLabel, reference.TargetId, StringComparison.OrdinalIgnoreCase));
                if (commit is null)
                {
                    return new OperationResult(false, "O commit não está no histórico local.", OperationState.Pending);
                }

                SelectCommit(commit);
                return new OperationResult(true, $"Commit {commit.RevisionLabel} selecionado no workspace local.");

            case "release":
                var release = project.WorkspaceReleases.FirstOrDefault(item => string.Equals(item.Name, reference.TargetId, StringComparison.OrdinalIgnoreCase) || string.Equals(item.Tag, reference.TargetId, StringComparison.OrdinalIgnoreCase));
                if (release is null)
                {
                    return new OperationResult(false, "A release não está no manifesto local.", OperationState.Pending);
                }

                SelectRelease(release);
                return new OperationResult(true, $"Release {release.Name} selecionada no workspace local.");

            case "pessoa":
            case "ia":
                return new OperationResult(true, $"{reference.Label} é uma identidade observável nesta simulação; nenhuma sessão externa foi acionada.");

            default:
                return new OperationResult(true, $"{reference.Label} é uma referência local de {reference.Kind}.");
        }
    }

    public OperationResult PostMessage(string body)
    {
        var project = SelectedProject;
        var result = project is null
            ? new OperationResult(false, "Selecione um projeto antes de publicar uma mensagem.", OperationState.Denied)
            : Store.PostMessage(project, "Local developer", body);
        Notify(result.Message, result.State);
        RefreshMetrics();
        return result;
    }

    public OperationResult CreateDelivery()
    {
        var project = SelectedProject;
        var result = project is null
            ? new OperationResult(false, "Selecione um projeto antes de criar uma entrega.", OperationState.Denied)
            : Store.CreateDelivery(project, "Local developer · local session");
        Notify(result.Message, result.State);
        RefreshMetrics();
        return result;
    }

    public OperationResult ApproveDelivery(DeliveryCandidate delivery)
    {
        var project = SelectedProject;
        var result = project is null
            ? new OperationResult(false, "Selecione um projeto antes de revisar uma entrega.", OperationState.Denied)
            : Store.ApproveDelivery(project, delivery, "Independent reviewer · local session");
        Notify(result.Message, result.State);
        RefreshMetrics();
        return result;
    }

    public OperationResult IntegrateDelivery(DeliveryCandidate delivery)
    {
        var project = SelectedProject;
        var result = project is null
            ? new OperationResult(false, "Selecione um projeto antes de integrar uma entrega.", OperationState.Denied)
            : Store.IntegrateDelivery(project, delivery, "Gateway local");
        Notify(result.Message, result.State);
        RefreshMetrics();
        return result;
    }

    public OperationResult RunQuality()
    {
        var project = SelectedProject;
        var result = project is null
            ? new OperationResult(false, "Selecione um projeto antes de executar qualidade.", OperationState.Denied)
            : Store.RunQuality(project, "QA · sessão local");
        Notify(result.Message, result.State);
        RefreshMetrics();
        return result;
    }

    public OperationResult ToggleProjectLifecycle()
    {
        var project = SelectedProject;
        var result = project is null
            ? new OperationResult(false, "Selecione um projeto antes de alterar o ciclo de vida.", OperationState.Denied)
            : Store.ToggleProjectLifecycle(project, "Local administrator");
        Notify(result.Message, result.State);
        RefreshMetrics();
        return result;
    }

    public void Notify(string message, OperationState state = OperationState.Success)
    {
        ToastMessage = message;
        ToastState = state;
        IsToastVisible = true;
    }

    public void DismissToast() => IsToastVisible = false;

    public void RefreshMetrics()
    {
        foreach (var project in Store.Projects)
        {
            project.RefreshDerivedState();
        }

        Raise(nameof(SelectedProject));
        Raise(nameof(FeaturedTask));
        Raise(nameof(RecentActivity));
        Raise(nameof(ActiveProjectCount));
        Raise(nameof(ReviewCount));
        Raise(nameof(BlockedCount));
        Raise(nameof(QualityAlertCount));
        Raise(nameof(ConnectedAgentCount));
        Raise(nameof(OfflineSessionCount));
        RaiseHomeState();
    }

    private void RaiseHomeState()
    {
        Raise(nameof(HomeTitle));
        Raise(nameof(HomeSubtitle));
        Raise(nameof(HomeSummaryLabel));
        Raise(nameof(HomeBlockedLabel));
        Raise(nameof(HomeReviewLabel));
    }

    private void RaiseGatewayState()
    {
        Raise(nameof(IsGatewayCheckInProgress));
        Raise(nameof(GatewayStatusLabel));
        Raise(nameof(GatewayStatusDetail));
    }

    private void SyncRuntime_StatusChanged(object? sender, CentralSyncStatus status)
    {
        var dispatcher = System.Windows.Application.Current?.Dispatcher;
        if (dispatcher is null || dispatcher.CheckAccess())
        {
            RaiseSyncState();
            return;
        }

        _ = dispatcher.BeginInvoke(new Action(RaiseSyncState));
    }

    private void SyncRuntime_ProjectEventReceived(object? sender, SupabaseProjectEvent projectEvent)
    {
        var dispatcher = System.Windows.Application.Current?.Dispatcher;
        if (dispatcher is null)
        {
            return;
        }

        _ = dispatcher.BeginInvoke(new Action(() =>
        {
            Raise(nameof(RecentActivity));
            if (SelectedProject is not null)
            {
                Notify($"Evento persistente recebido · sequência {projectEvent.Sequence}.", OperationState.Success);
            }
        }));
    }

    private void RaiseSyncState()
    {
        Raise(nameof(SyncStatus));
        Raise(nameof(SyncStatusLabel));
        Raise(nameof(SyncStatusDetail));
        Raise(nameof(IsSyncConnected));
        Raise(nameof(LocalModeDescription));
    }

    private SupabaseOptions? ResolveSupabaseOptions()
    {
        var url = string.IsNullOrWhiteSpace(SyncSupabaseUrl)
            ? Environment.GetEnvironmentVariable("CENTRAL_SUPABASE_URL")
            : SyncSupabaseUrl.Trim();
        var key = string.IsNullOrWhiteSpace(SyncPublishableKey)
            ? Environment.GetEnvironmentVariable("CENTRAL_SUPABASE_PUBLISHABLE_KEY")
            : SyncPublishableKey.Trim();

        return Uri.TryCreate(url, UriKind.Absolute, out var uri)
            && uri.Scheme is "http" or "https"
            && !string.IsNullOrWhiteSpace(key)
            ? new SupabaseOptions(
                uri.ToString().EndsWith('/') ? uri : new Uri(uri + "/"),
                key)
            : null;
    }

    private void LoadSyncSettings()
    {
        var path = SyncSettingsPath();
        try
        {
            if (!File.Exists(path))
            {
                SyncSupabaseUrl = Environment.GetEnvironmentVariable("CENTRAL_SUPABASE_URL") ?? SyncSupabaseUrl;
                SyncPublishableKey = Environment.GetEnvironmentVariable("CENTRAL_SUPABASE_PUBLISHABLE_KEY") ?? string.Empty;
                SyncEmail = Environment.GetEnvironmentVariable("CENTRAL_SUPABASE_EMAIL") ?? string.Empty;
                SyncOrganizationId = Environment.GetEnvironmentVariable("CENTRAL_ORGANIZATION_ID") ?? string.Empty;
                SyncProjectId = Environment.GetEnvironmentVariable("CENTRAL_PROJECT_ID") ?? string.Empty;
                SyncFolder = Environment.GetEnvironmentVariable("CENTRAL_SYNC_FOLDER") ?? SyncFolder;
                SyncMode = Environment.GetEnvironmentVariable("CENTRAL_SYNC_MODE") ?? SyncMode;
                return;
            }

            var saved = JsonSerializer.Deserialize<LocalSyncSettings>(File.ReadAllText(path));
            if (saved is null)
            {
                return;
            }

            SyncSupabaseUrl = saved.SupabaseUrl ?? SyncSupabaseUrl;
            SyncPublishableKey = saved.PublishableKey ?? string.Empty;
            SyncEmail = saved.Email ?? string.Empty;
            SyncOrganizationId = saved.OrganizationId ?? string.Empty;
            SyncProjectId = saved.ProjectId ?? string.Empty;
            SyncFolder = saved.Folder ?? SyncFolder;
            SyncMode = saved.Mode is "send-only" or "receive-only" or "send-receive"
                ? saved.Mode
                : SyncMode;
        }
        catch (Exception exception) when (exception is IOException or JsonException)
        {
            // A corrupt local preference must not prevent the offline shell from opening.
        }
    }

    private void SaveSyncSettings()
    {
        try
        {
            var path = SyncSettingsPath();
            var directory = Path.GetDirectoryName(path)!;
            Directory.CreateDirectory(directory);
            var temporary = path + ".tmp";
            var json = JsonSerializer.Serialize(
                new LocalSyncSettings(
                    SyncSupabaseUrl,
                    SyncPublishableKey,
                    SyncEmail,
                    SyncOrganizationId,
                    SyncProjectId,
                    SyncFolder,
                    SyncMode),
                new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(temporary, json);
            File.Move(temporary, path, overwrite: true);
        }
        catch (IOException)
        {
            // Preferences are optional; a connected runtime must not be rolled
            // back merely because the local profile directory is unavailable.
        }
    }

    private static string SyncSettingsPath()
        => Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Central",
            "sync-settings.json");

    private sealed record LocalSyncSettings(
        string? SupabaseUrl,
        string? PublishableKey,
        string? Email,
        string? OrganizationId,
        string? ProjectId,
        string? Folder,
        string? Mode);

    private static Uri ResolveGatewayBaseUri()
    {
        var configured = Environment.GetEnvironmentVariable("CENTRAL_GATEWAY_URL");
        if (Uri.TryCreate(configured, UriKind.Absolute, out var configuredUri)
            && configuredUri.Scheme is "http" or "https")
        {
            return configuredUri.ToString().EndsWith('/')
                ? configuredUri
                : new Uri(configuredUri + "/");
        }

        return new Uri("https://example.invalid/");
    }

    private static string FormatCount(int count, string singular, string plural)
        => $"{count} {(count == 1 ? singular : plural)}";

    private static IReadOnlyList<RequestLogEntry> CreateRequestLogs()
    {
        // The visual table is intentionally empty until a real gateway provides
        // request_id, source, freshness, measured duration and redacted principal.
        // Empty is safer than turning a screenshot reference into fake telemetry.
        return Array.Empty<RequestLogEntry>();
    }
}
