using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Text.Json;
using System.Xml.Linq;
using Central.Core.Connectivity;

namespace Central.Desktop.Services;

public enum CentralSyncConnectionState
{
    NotConfigured,
    Starting,
    LocalOnly,
    Authenticating,
    Connected,
    Reconnecting,
    Error,
    Paused,
}

public sealed record CentralSyncStatus(
    CentralSyncConnectionState State,
    string Label,
    string Detail,
    string? DeviceId = null,
    string? FolderState = null,
    int PendingItems = 0,
    long LastSequence = 0,
    bool IsRealtimeConnected = false,
    int ConnectedPeers = 0,
    int ConfiguredPeers = 0);

/// <summary>
/// Coordinates the local Syncthing data plane with the Supabase control plane.
/// The runtime is deliberately opt-in: without a publishable key, project and
/// organization IDs it only exposes the local Syncthing health state.
/// </summary>
public sealed class CentralSyncRuntime : IAsyncDisposable
{
    private readonly HttpClient _httpClient;
    private readonly string _clientKey;
    private readonly SemaphoreSlim _connectionLock = new(1, 1);
    private readonly SemaphoreSlim _eventReplayLock = new(1, 1);
    private readonly object _statusLock = new();
    private CancellationTokenSource? _runCts;
    private Task? _monitorTask;
    private Task? _realtimeTask;
    private SupabaseRestClient? _supabase;
    private SupabaseRealtimeClient? _realtime;
    private SyncthingRuntimeHandle? _syncthing;
    private Guid _organizationId;
    private Guid _projectId;
    private CentralAccessSession? _centralAccessSession;
    private string _folderId = string.Empty;
    private string _folderPath = string.Empty;
    private string _syncMode = "send-receive";
    private SupabaseDevice? _device;
    private readonly HashSet<string> _configuredPeerIds = new(StringComparer.Ordinal);
    private bool _realtimeConnected;
    private CentralSyncStatus _status = new(
        CentralSyncConnectionState.NotConfigured,
        "SINCRONIZAÇÃO · NÃO CONFIGURADA",
        "Informe a organização, o projeto e uma pasta dedicada para ativar a sincronização.");
    private ProjectEventCursor _cursor = new();

    public CentralSyncRuntime()
    {
        _httpClient = new HttpClient
        {
            Timeout = TimeSpan.FromSeconds(10),
        };
        _clientKey = LoadOrCreateClientKey();
    }

    public event EventHandler<CentralSyncStatus>? StatusChanged;
    public event EventHandler<SupabaseProjectEvent>? ProjectEventReceived;

    public CentralSyncStatus Status
    {
        get
        {
            lock (_statusLock)
            {
                return _status;
            }
        }
    }

    public async Task StartLocalAsync(CancellationToken cancellationToken = default)
    {
        SetStatus(new CentralSyncStatus(
            CentralSyncConnectionState.Starting,
            "SINCRONIZAÇÃO · INICIANDO",
            "Verificando o agente local de arquivos."));

        try
        {
            _syncthing = await SyncthingRuntime.StartAsync(_httpClient, cancellationToken).ConfigureAwait(false);
            if (_syncthing is null)
            {
                SetStatus(new CentralSyncStatus(
                    CentralSyncConnectionState.LocalOnly,
                    "SINCRONIZAÇÃO · AGENTE AUSENTE",
                    "Syncthing não está empacotado ou instalado; nenhum arquivo será copiado pela Central."));
                return;
            }

            SetStatus(new CentralSyncStatus(
                CentralSyncConnectionState.LocalOnly,
                "SINCRONIZAÇÃO · AGENTE LOCAL",
                $"Syncthing {_syncthing.Version} respondeu localmente; o pareamento ainda não foi ativado.",
                _syncthing.DeviceId));
        }
        catch (Exception exception) when (exception is IOException or HttpRequestException or InvalidOperationException)
        {
            SetStatus(new CentralSyncStatus(
                CentralSyncConnectionState.Error,
                "SINCRONIZAÇÃO · ERRO LOCAL",
                RedactError(exception.Message)));
        }
    }

    public async Task ConnectAsync(
        SupabaseOptions options,
        string email,
        string password,
        Guid organizationId,
        Guid projectId,
        string folderPath,
        string syncMode,
        CentralAccessSession centralAccessSession,
        CancellationToken cancellationToken = default)
    {
        await _connectionLock.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            await ConnectCoreAsync(
                options,
                email,
                password,
                organizationId,
                projectId,
                folderPath,
                syncMode,
                centralAccessSession,
                cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _connectionLock.Release();
        }
    }

    private async Task ConnectCoreAsync(
        SupabaseOptions options,
        string email,
        string password,
        Guid organizationId,
        Guid projectId,
        string folderPath,
        string syncMode,
        CentralAccessSession centralAccessSession,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(options);
        if (string.IsNullOrWhiteSpace(folderPath))
        {
            throw new ArgumentException("A pasta de sincronização é obrigatória.", nameof(folderPath));
        }
        if (syncMode is not ("send-only" or "receive-only" or "send-receive"))
        {
            throw new ArgumentOutOfRangeException(nameof(syncMode));
        }
        if (centralAccessSession.ExpiresAt <= DateTimeOffset.UtcNow
            || !centralAccessSession.Scope.Contains("central:sync", StringComparer.Ordinal)
            || centralAccessSession.ProjectId != projectId)
        {
            throw new InvalidOperationException("A sessão da Central não autoriza este projeto ou expirou.");
        }

        await StopAsync().ConfigureAwait(false);
        _organizationId = organizationId;
        _projectId = projectId;
        _folderPath = Path.GetFullPath(folderPath);
        _folderId = $"central-{projectId:N}";
        _syncMode = syncMode;
        _centralAccessSession = centralAccessSession;

        SetStatus(new CentralSyncStatus(
            CentralSyncConnectionState.Authenticating,
            "SINCRONIZAÇÃO · AUTENTICANDO",
            "Validando a sessão individual no Supabase."));

        _supabase = new SupabaseRestClient(_httpClient, options);
        await _supabase.SignInPasswordAsync(email, password, cancellationToken).ConfigureAwait(false);

        ValidateSyncFolderPath(_folderPath);
        Directory.CreateDirectory(_folderPath);
        SyncFolderPolicy.EnsureIgnorePatterns(_folderPath);

        _syncthing ??= await SyncthingRuntime.StartAsync(_httpClient, cancellationToken).ConfigureAwait(false);
        if (_syncthing is null)
        {
            throw new InvalidOperationException("O agente Syncthing local não está disponível.");
        }

        _device = await _supabase.RegisterDeviceAsync(
            organizationId,
            _clientKey,
            Environment.GetEnvironmentVariable("CENTRAL_DEVICE_NAME") ?? Environment.MachineName,
            _syncthing.DeviceId,
            cancellationToken).ConfigureAwait(false);

        var peers = (await _supabase.GetProjectDevicesAsync(projectId, cancellationToken).ConfigureAwait(false))
            .Where(item => item.Id != _device.Id && !string.IsNullOrWhiteSpace(item.SyncthingDeviceId))
            .Select(item => new SyncthingPeer(item.SyncthingDeviceId!, item.DeviceName))
            .ToArray();

        var syncFolder = await _supabase.EnsureSyncFolderAsync(
            projectId,
            _folderId,
            "Central · pasta compartilhada",
            Path.GetFileName(_folderPath),
            syncMode,
            cancellationToken).ConfigureAwait(false);
        if (!string.Equals(syncFolder.Mode, syncMode, StringComparison.Ordinal))
        {
            throw new InvalidOperationException(
                $"O projeto já usa o modo de sincronização {syncFolder.Mode}; os dois computadores precisam usar o mesmo modo.");
        }

        var ensure = await _syncthing.Client.EnsurePeerAndFolderAsync(
            _folderId,
            "Central · pasta compartilhada",
            _folderPath,
            syncMode,
            peers,
            cancellationToken).ConfigureAwait(false);

        _configuredPeerIds.Clear();
        foreach (var peer in peers)
        {
            _configuredPeerIds.Add(peer.DeviceId);
        }

        await _syncthing.Client.SetFolderPausedAsync(
            _folderId,
            paused: false,
            cancellationToken).ConfigureAwait(false);

        if (ensure.RestartRequired)
        {
            await _syncthing.Client.RestartAsync(cancellationToken).ConfigureAwait(false);
        }

        _cursor = LoadEventCursor(projectId);
        _runCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        _realtimeConnected = false;
        SetStatus(new CentralSyncStatus(
            peers.Length > 0 ? CentralSyncConnectionState.Reconnecting : CentralSyncConnectionState.LocalOnly,
            peers.Length > 0 ? "SINCRONIZAÇÃO · AGUARDANDO CONEXÃO" : "SINCRONIZAÇÃO · AGUARDANDO REMOTO",
            $"{_device.DeviceName} autenticado; {peers.Length} dispositivo(s) remoto(s) configurado(s). O estado só será conectado após o Realtime ou um peer responder.",
            _syncthing.DeviceId,
            "starting",
            IsRealtimeConnected: false,
            ConfiguredPeers: _configuredPeerIds.Count));

        await ReplayEventsAsync(_runCts.Token).ConfigureAwait(false);
        _monitorTask = MonitorAsync(_runCts.Token);
        _realtime = new SupabaseRealtimeClient(options);
        _realtime.ConnectionChanged += Realtime_ConnectionChanged;
        _realtimeTask = RunRealtimeAsync(_runCts.Token);
    }

    public async Task StopAsync()
    {
        var cts = Interlocked.Exchange(ref _runCts, null);
        if (cts is null)
        {
            return;
        }

        cts.Cancel();
        try
        {
            await Task.WhenAll(
                _monitorTask ?? Task.CompletedTask,
                _realtimeTask ?? Task.CompletedTask).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
        }
        finally
        {
            cts.Dispose();
            _monitorTask = null;
            _realtimeTask = null;
            if (_realtime is not null)
            {
                _realtime.ConnectionChanged -= Realtime_ConnectionChanged;
                await _realtime.DisposeAsync().ConfigureAwait(false);
                _realtime = null;
            }

            if (_syncthing is not null && !string.IsNullOrWhiteSpace(_folderId))
            {
                try
                {
                    await _syncthing.Client.SetFolderPausedAsync(_folderId, paused: true).ConfigureAwait(false);
                }
                catch (Exception exception) when (exception is HttpRequestException or IOException)
                {
                    // The local agent may already be unavailable; the files and
                    // conflict copies remain on disk for manual recovery.
                }
            }
        }

        SetStatus(new CentralSyncStatus(
            CentralSyncConnectionState.Paused,
            "SINCRONIZAÇÃO · PAUSADA",
            "A integração foi pausada. Arquivos e conflitos foram preservados."));
        _centralAccessSession = null;
    }

    private async Task RunRealtimeAsync(CancellationToken cancellationToken)
    {
        if (_realtime is null || _supabase?.Session is null)
        {
            return;
        }

        await _realtime.RunAsync(
            _projectId,
            _supabase.Session,
            async notification =>
            {
                if (string.Equals(notification.Table, "project_events", StringComparison.OrdinalIgnoreCase))
                {
                    await ReplayEventsAsync(cancellationToken).ConfigureAwait(false);
                }
                else if (string.Equals(notification.Table, "sync_states", StringComparison.OrdinalIgnoreCase))
                {
                    await PublishCurrentFolderStateAsync(cancellationToken).ConfigureAwait(false);
                }
            },
            cancellationToken,
            async token => await _supabase.GetValidSessionAsync(token).ConfigureAwait(false)).ConfigureAwait(false);
    }

    private async Task MonitorAsync(CancellationToken cancellationToken)
    {
        var lastPublished = DateTimeOffset.MinValue;
        while (!cancellationToken.IsCancellationRequested)
        {
            try
            {
                if (_syncthing is not null)
                {
                    var folder = await _syncthing.Client.GetFolderStatusAsync(_folderId, cancellationToken).ConfigureAwait(false);
                    var connections = await _syncthing.Client.GetConnectionsAsync(cancellationToken).ConfigureAwait(false);
                    var connectedPeers = connections.Count(connection =>
                        connection.Connected && _configuredPeerIds.Contains(connection.DeviceId));
                    var state = ToSyncState(folder.State);
                    var hasLiveConnection = _realtimeConnected || connectedPeers > 0;
                    var label = state switch
                    {
                        SyncStateKind.Synced when _configuredPeerIds.Count > 0 && connectedPeers == 0
                            => "SINCRONIZAÇÃO · AGUARDANDO REMOTO",
                        _ when !hasLiveConnection => "SINCRONIZAÇÃO · AGUARDANDO CONEXÃO",
                        SyncStateKind.Synced => "SINCRONIZAÇÃO · EM DIA",
                        SyncStateKind.Error or SyncStateKind.Conflict => "SINCRONIZAÇÃO · REQUER ATENÇÃO",
                        _ => "SINCRONIZAÇÃO · ATUALIZANDO",
                    };
                    SetStatus(new CentralSyncStatus(
                        state == SyncStateKind.Error || state == SyncStateKind.Conflict
                            ? CentralSyncConnectionState.Error
                            : hasLiveConnection
                                ? CentralSyncConnectionState.Connected
                                : CentralSyncConnectionState.LocalOnly,
                        label,
                        string.IsNullOrWhiteSpace(folder.Error)
                            ? $"{folder.NeedItems} item(ns) pendente(s) · {connectedPeers}/{_configuredPeerIds.Count} remoto(s) conectado(s) · estado Syncthing {folder.State}."
                            : RedactError(folder.Error),
                        _syncthing.DeviceId,
                        folder.State,
                        folder.NeedItems,
                        _cursor.LastSequence,
                        IsRealtimeConnected: _realtimeConnected,
                        ConnectedPeers: connectedPeers,
                        ConfiguredPeers: _configuredPeerIds.Count));

                    if (_supabase is not null && _device is not null
                        && DateTimeOffset.UtcNow - lastPublished >= TimeSpan.FromSeconds(10))
                    {
                        await _supabase.GetValidSessionAsync(cancellationToken).ConfigureAwait(false);
                        await _supabase.UpsertSyncStateAsync(
                            _projectId,
                            _device.Id,
                            state.ToString().ToLowerInvariant(),
                            folder.NeedItems,
                            folder.Error ?? folder.State,
                            cancellationToken).ConfigureAwait(false);
                        lastPublished = DateTimeOffset.UtcNow;
                    }

                    if (_supabase is not null && _device is not null)
                    {
                        await _supabase.GetValidSessionAsync(cancellationToken).ConfigureAwait(false);
                        await _supabase.HeartbeatDeviceAsync(_device.Id, cancellationToken).ConfigureAwait(false);
                    }
                }

                await Task.Delay(TimeSpan.FromSeconds(3), cancellationToken).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
            {
                break;
            }
            catch (Exception exception) when (exception is HttpRequestException or SupabaseRequestException or IOException)
            {
                SetStatus(new CentralSyncStatus(
                    CentralSyncConnectionState.Reconnecting,
                    "SINCRONIZAÇÃO · RECONECTANDO",
                    RedactError(exception.Message),
                    _syncthing?.DeviceId,
                    IsRealtimeConnected: _realtimeConnected,
                    LastSequence: _cursor.LastSequence));
                await Task.Delay(TimeSpan.FromSeconds(5), cancellationToken).ConfigureAwait(false);
            }
        }
    }

    private async Task ReplayEventsAsync(CancellationToken cancellationToken)
    {
        if (_supabase is null)
        {
            return;
        }

        await _eventReplayLock.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                var events = await _supabase.GetProjectEventsSinceAsync(
                    _projectId,
                    _cursor.LastSequence,
                    200,
                    cancellationToken).ConfigureAwait(false);
                if (events.Count == 0)
                {
                    return;
                }

                foreach (var projectEvent in events.OrderBy(item => item.Sequence))
                {
                    if (_cursor.TryAccept(projectEvent))
                    {
                        ProjectEventReceived?.Invoke(this, projectEvent);
                    }
                }

                PersistEventCursor(_projectId, _cursor.LastSequence);

                if (events.Count < 200)
                {
                    return;
                }
            }
        }
        finally
        {
            _eventReplayLock.Release();
        }
    }

    private async Task PublishCurrentFolderStateAsync(CancellationToken cancellationToken)
    {
        if (_syncthing is null)
        {
            return;
        }

        var status = await _syncthing.Client.GetFolderStatusAsync(_folderId, cancellationToken).ConfigureAwait(false);
        SetStatus(Status with
        {
            FolderState = status.State,
            PendingItems = status.NeedItems,
            LastSequence = _cursor.LastSequence,
        });
    }

    private static SyncStateKind ToSyncState(string state)
        => state.ToLowerInvariant() switch
        {
            "idle" or "clean" => SyncStateKind.Synced,
            "syncing" or "sync-preparing" or "scan-waiting" or "scanning" => SyncStateKind.Syncing,
            "error" => SyncStateKind.Error,
            _ => SyncStateKind.Unknown,
        };

    private void SetStatus(CentralSyncStatus status)
    {
        lock (_statusLock)
        {
            _status = status;
        }

        StatusChanged?.Invoke(this, status);
    }

    private void Realtime_ConnectionChanged(object? sender, bool connected)
    {
        _realtimeConnected = connected;
        if (connected)
        {
            var replayToken = _runCts?.Token ?? CancellationToken.None;
            _ = ReplayAfterReconnectAsync(replayToken);
        }

        SetStatus(Status with
        {
            State = connected
                ? CentralSyncConnectionState.Connected
                : CentralSyncConnectionState.Reconnecting,
            Label = connected
                ? "SINCRONIZAÇÃO · STREAMING ATIVO"
                : "SINCRONIZAÇÃO · STREAMING RECONECTANDO",
            Detail = connected
                ? "Canal Realtime confirmado; o cursor durável está sendo reconciliado."
                : "O canal Realtime caiu; os eventos serão recuperados pelo cursor quando voltar.",
            IsRealtimeConnected = connected,
            LastSequence = _cursor.LastSequence,
        });
    }

    private async Task ReplayAfterReconnectAsync(CancellationToken cancellationToken)
    {
        try
        {
            await ReplayEventsAsync(cancellationToken).ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
        }
        catch (Exception exception) when (exception is HttpRequestException or SupabaseRequestException or IOException)
        {
            SetStatus(Status with
            {
                State = CentralSyncConnectionState.Reconnecting,
                Label = "SINCRONIZAÇÃO · RECONCILIANDO",
                Detail = RedactError(exception.Message),
                IsRealtimeConnected = _realtimeConnected,
            });
        }
    }

    private static string LoadOrCreateClientKey()
    {
        var root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Central");
        Directory.CreateDirectory(root);
        var path = Path.Combine(root, "client-key.txt");
        try
        {
            if (File.Exists(path))
            {
                var value = File.ReadAllText(path).Trim();
                if (Guid.TryParse(value, out _))
                {
                    return value;
                }
            }

            var created = Guid.NewGuid().ToString("D");
            File.WriteAllText(path, created);
            return created;
        }
        catch (IOException)
        {
            return Guid.NewGuid().ToString("D");
        }
    }

    private static void ValidateSyncFolderPath(string folderPath)
    {
        var fullPath = Path.GetFullPath(folderPath);
        var root = Path.GetPathRoot(fullPath);
        if (string.IsNullOrWhiteSpace(root)
            || string.Equals(
                fullPath.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar),
                root.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar),
                StringComparison.OrdinalIgnoreCase))
        {
            throw new ArgumentException("Escolha uma pasta dedicada; a raiz do disco não pode ser sincronizada.", nameof(folderPath));
        }

        if (string.Equals(
                fullPath.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar),
                AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar),
                StringComparison.OrdinalIgnoreCase))
        {
            throw new ArgumentException("A pasta de instalação da Central não pode ser usada como workspace sincronizado.", nameof(folderPath));
        }
    }

    private static ProjectEventCursor LoadEventCursor(Guid projectId)
    {
        var path = EventCursorPath(projectId);
        try
        {
            if (File.Exists(path))
            {
                var saved = JsonSerializer.Deserialize<CursorCheckpoint>(File.ReadAllText(path));
                if (saved is not null && saved.LastSequence >= 0)
                {
                    var cursor = new ProjectEventCursor();
                    cursor.MarkSnapshot(saved.LastSequence);
                    return cursor;
                }
            }
        }
        catch (Exception exception) when (exception is IOException or JsonException)
        {
            // A damaged local checkpoint only costs a replay from sequence one.
        }

        return new ProjectEventCursor();
    }

    private static void PersistEventCursor(Guid projectId, long sequence)
    {
        if (sequence < 0)
        {
            return;
        }

        try
        {
            var path = EventCursorPath(projectId);
            var directory = Path.GetDirectoryName(path)!;
            Directory.CreateDirectory(directory);
            var temporary = path + ".tmp";
            File.WriteAllText(temporary, JsonSerializer.Serialize(new CursorCheckpoint(sequence)));
            File.Move(temporary, path, overwrite: true);
        }
        catch (IOException)
        {
            // The checkpoint is an optimization; the durable stream remains the
            // source of truth and will be replayed on the next startup.
        }
    }

    private static string EventCursorPath(Guid projectId)
        => Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Central",
            "event-cursors",
            $"{projectId:D}.json");

    private sealed record CursorCheckpoint(long LastSequence);

    private static string RedactError(string message)
    {
        var redacted = message;
        foreach (var secretName in new[]
        {
            "CENTRAL_SUPABASE_PUBLISHABLE_KEY",
            "CENTRAL_SUPABASE_PASSWORD",
        })
        {
            var secret = Environment.GetEnvironmentVariable(secretName);
            if (!string.IsNullOrEmpty(secret))
            {
                redacted = redacted.Replace(secret, "[redacted]", StringComparison.Ordinal);
            }
        }

        return redacted;
    }

    public async ValueTask DisposeAsync()
    {
        await StopAsync().ConfigureAwait(false);
        await SyncthingRuntime.StopOwnedProcessAsync(_syncthing).ConfigureAwait(false);
        _syncthing = null;
        _eventReplayLock.Dispose();
        _connectionLock.Dispose();
        _httpClient.Dispose();
    }
}

internal sealed record SyncthingRuntimeHandle(
    SyncthingClient Client,
    string DeviceId,
    string Version,
    Uri BaseAddress,
    string ApiKey,
    Process? Process);

internal static class SyncthingRuntime
{
    public static async Task<SyncthingRuntimeHandle?> StartAsync(HttpClient httpClient, CancellationToken cancellationToken)
    {
        var executable = ResolveExecutable();
        if (executable is null)
        {
            return null;
        }

        var home = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Central",
            "syncthing");
        Directory.CreateDirectory(home);
        var configPath = Path.Combine(home, "config.xml");
        if (!File.Exists(configPath))
        {
            using var generated = StartProcess(executable, $"generate --home \"{home}\"");
            await generated.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
            if (generated.ExitCode != 0 || !File.Exists(configPath))
            {
                throw new InvalidOperationException("Não foi possível gerar a configuração local do Syncthing.");
            }
        }

        var (baseAddress, apiKey) = ReadGuiConfig(configPath);
        var client = new SyncthingClient(httpClient, baseAddress, apiKey);
        Process? process = null;
        try
        {
            var current = await client.GetStatusAsync(cancellationToken).ConfigureAwait(false);
            return new SyncthingRuntimeHandle(client, current.DeviceId, current.Version, baseAddress, apiKey, null);
        }
        catch (HttpRequestException)
        {
            process = StartProcess(executable, $"serve --home \"{home}\" --no-browser");
        }

        SyncthingStatus? status = null;
        for (var attempt = 0; attempt < 30; attempt++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            try
            {
                status = await client.GetStatusAsync(cancellationToken).ConfigureAwait(false);
                break;
            }
            catch (HttpRequestException)
            {
                await Task.Delay(500, cancellationToken).ConfigureAwait(false);
            }
        }

        if (status is null)
        {
            await StopOwnedProcessAsync(new SyncthingRuntimeHandle(
                client,
                string.Empty,
                string.Empty,
                baseAddress,
                apiKey,
                process)).ConfigureAwait(false);
            throw new HttpRequestException("O agente Syncthing não respondeu ao endpoint local.");
        }

        return new SyncthingRuntimeHandle(client, status.DeviceId, status.Version, baseAddress, apiKey, process);
    }

    public static async Task StopOwnedProcessAsync(SyncthingRuntimeHandle? handle)
    {
        var process = handle?.Process;
        if (process is null)
        {
            return;
        }

        try
        {
            if (!process.HasExited)
            {
                process.Kill(entireProcessTree: true);
                await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(5)).ConfigureAwait(false);
            }
        }
        catch (InvalidOperationException)
        {
            // The process exited between the state check and Kill.
        }
        catch (System.ComponentModel.Win32Exception)
        {
            // The process may have already been terminated by the user.
        }
        catch (TimeoutException)
        {
            // Do not keep the UI blocked on a misbehaving child process.
        }
        finally
        {
            process.Dispose();
        }
    }

    private static string? ResolveExecutable()
    {
        var configured = Environment.GetEnvironmentVariable("CENTRAL_SYNCTHING_EXE");
        var candidates = new[]
        {
            configured,
            Path.Combine(AppContext.BaseDirectory, "syncthing.exe"),
            Path.Combine(AppContext.BaseDirectory, "tools", "syncthing", "syncthing.exe"),
        };
        return candidates.FirstOrDefault(item => !string.IsNullOrWhiteSpace(item) && File.Exists(item));
    }

    private static Process StartProcess(string executable, string arguments)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = executable,
            Arguments = arguments,
            UseShellExecute = false,
            CreateNoWindow = true,
            WorkingDirectory = Path.GetDirectoryName(executable) ?? AppContext.BaseDirectory,
        };
        foreach (var secretName in new[]
        {
            "CENTRAL_SUPABASE_URL",
            "CENTRAL_SUPABASE_PUBLISHABLE_KEY",
            "CENTRAL_SUPABASE_PASSWORD",
            "CENTRAL_SUPABASE_EMAIL",
        })
        {
            startInfo.Environment.Remove(secretName);
        }

        var process = Process.Start(startInfo);
        return process ?? throw new InvalidOperationException("Não foi possível iniciar o agente Syncthing local.");
    }

    private static (Uri BaseAddress, string ApiKey) ReadGuiConfig(string configPath)
    {
        var document = XDocument.Load(configPath, LoadOptions.PreserveWhitespace);
        var gui = document.Root?.Element("gui")
            ?? throw new InvalidOperationException("A configuração do Syncthing não possui GUI local.");
        var address = gui.Element("address")?.Value.Trim();
        var apiKey = gui.Element("apikey")?.Value.Trim();
        if (string.IsNullOrWhiteSpace(address) || string.IsNullOrWhiteSpace(apiKey))
        {
            throw new InvalidOperationException("A configuração local do Syncthing não possui endereço ou chave de API.");
        }

        var tls = string.Equals(gui.Element("tls")?.Value.Trim(), "true", StringComparison.OrdinalIgnoreCase);
        var scheme = tls ? "https" : "http";
        if (!Uri.TryCreate($"{scheme}://{address.TrimEnd('/')}/", UriKind.Absolute, out var configuredUri))
        {
            throw new InvalidOperationException("O endereço da GUI local do Syncthing é inválido.");
        }

        if (configuredUri.Host is not ("localhost" or "127.0.0.1" or "::1" or "0.0.0.0"))
        {
            throw new InvalidOperationException("A Central só aceita a GUI do Syncthing em loopback.");
        }

        var localHost = configuredUri.Host == "0.0.0.0" ? "127.0.0.1" : configuredUri.Host;
        var localUri = new UriBuilder(configuredUri) { Host = localHost }.Uri;
        return (localUri, apiKey);
    }
}

internal static class SyncFolderPolicy
{
    private static readonly string[] IgnorePatterns =
    {
        ".env",
        ".env.*",
        "*.pem",
        "*.key",
        "*.pfx",
        "appsettings.Production.json",
        "**/bin",
        "**/obj",
        "**/.git",
        "**/.codex",
        "**/artifacts",
        "**/*.log",
    };

    public static void EnsureIgnorePatterns(string folderPath)
    {
        var path = Path.Combine(folderPath, ".stignore");
        var existing = File.Exists(path)
            ? File.ReadAllLines(path).ToHashSet(StringComparer.OrdinalIgnoreCase)
            : new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var missing = IgnorePatterns.Where(pattern => !existing.Contains(pattern)).ToArray();
        if (missing.Length > 0)
        {
            var prefix = File.Exists(path) && new FileInfo(path).Length > 0
                ? Environment.NewLine
                : string.Empty;
            File.AppendAllText(path, prefix + string.Join(Environment.NewLine, missing) + Environment.NewLine);
        }
    }
}
