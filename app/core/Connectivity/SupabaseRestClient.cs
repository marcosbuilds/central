using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Central.Core.Connectivity;

/// <summary>
/// Small dependency-free Supabase Auth/PostgREST client. The publishable key
/// is configuration, never a service-role credential. It intentionally has no
/// automatic retry policy: a retry must be authorized by the operation's
/// idempotency contract.
/// </summary>
public sealed class SupabaseRestClient
{
    private readonly HttpClient _httpClient;
    private readonly SupabaseOptions _options;
    private readonly JsonSerializerOptions _json = ConnectivityJson.Options;
    private readonly SemaphoreSlim _sessionRefreshLock = new(1, 1);

    public SupabaseRestClient(HttpClient httpClient, SupabaseOptions options)
    {
        _httpClient = httpClient ?? throw new ArgumentNullException(nameof(httpClient));
        _options = options ?? throw new ArgumentNullException(nameof(options));
    }

    public SupabaseSession? Session { get; private set; }

    public void SetSession(SupabaseSession? session) => Session = session;

    public async Task<SupabaseSession> GetValidSessionAsync(
        CancellationToken cancellationToken = default)
    {
        var current = Session ?? throw new InvalidOperationException(
            "A Central precisa de uma sessão Supabase autenticada.");

        if (current.ExpiresAt > DateTimeOffset.UtcNow.AddMinutes(2))
        {
            return current;
        }

        await _sessionRefreshLock.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            current = Session ?? throw new InvalidOperationException(
                "A Central precisa de uma sessão Supabase autenticada.");
            if (current.ExpiresAt > DateTimeOffset.UtcNow.AddMinutes(2))
            {
                return current;
            }

            var response = await SendAsync<AuthResponse>(
                HttpMethod.Post,
                "auth/v1/token?grant_type=refresh_token",
                new { refresh_token = current.RefreshToken },
                requireSession: false,
                cancellationToken).ConfigureAwait(false);

            var refreshed = response.ToSession(current.RefreshToken);
            Session = refreshed;
            return refreshed;
        }
        finally
        {
            _sessionRefreshLock.Release();
        }
    }

    public async Task<SupabaseSession> SignInPasswordAsync(
        string email,
        string password,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(email) || string.IsNullOrWhiteSpace(password))
        {
            throw new ArgumentException("E-mail e senha são obrigatórios.");
        }

        var response = await SendAsync<AuthResponse>(
            HttpMethod.Post,
            $"auth/v1/token?grant_type=password",
            new { email = email.Trim(), password },
            requireSession: false,
            cancellationToken).ConfigureAwait(false);

        var session = response.ToSession();
        Session = session;
        return session;
    }

    public async Task<SupabaseSession> SignUpPasswordAsync(
        string email,
        string password,
        CancellationToken cancellationToken = default)
    {
        var response = await SendAsync<AuthResponse>(
            HttpMethod.Post,
            "auth/v1/signup",
            new { email = email.Trim(), password },
            requireSession: false,
            cancellationToken).ConfigureAwait(false);

        var session = response.ToSession();
        Session = session;
        return session;
    }

    public async Task<SupabaseDevice> RegisterDeviceAsync(
        Guid organizationId,
        string clientKey,
        string deviceName,
        string? syncthingDeviceId,
        CancellationToken cancellationToken = default)
        => await RpcAsync<SupabaseDevice>(
            "register_device",
            new
            {
                p_organization_id = organizationId,
                p_client_key = clientKey,
                p_device_name = deviceName,
                p_syncthing_device_id = syncthingDeviceId,
            },
            cancellationToken).ConfigureAwait(false);

    public async Task<SupabaseDevice> HeartbeatDeviceAsync(
        Guid deviceId,
        CancellationToken cancellationToken = default)
        => await RpcAsync<SupabaseDevice>(
            "heartbeat_device",
            new { p_device_id = deviceId },
            cancellationToken).ConfigureAwait(false);

    public async Task<SupabaseDevice> RevokeDeviceAsync(
        Guid deviceId,
        CancellationToken cancellationToken = default)
        => await RpcAsync<SupabaseDevice>(
            "revoke_device",
            new { p_device_id = deviceId },
            cancellationToken).ConfigureAwait(false);

    public async Task<SupabaseSyncState> UpsertSyncStateAsync(
        Guid projectId,
        Guid deviceId,
        string state,
        int pendingItems,
        string detail,
        CancellationToken cancellationToken = default)
        => await RpcAsync<SupabaseSyncState>(
            "upsert_sync_state",
            new
            {
                p_project_id = projectId,
                p_device_id = deviceId,
                p_state = state,
                p_pending_items = pendingItems,
                p_detail = detail,
            },
            cancellationToken).ConfigureAwait(false);

    public async Task<SupabaseProjectEvent> AppendProjectEventAsync(
        Guid projectId,
        string eventType,
        object payload,
        string? idempotencyKey,
        CancellationToken cancellationToken = default)
        => await RpcAsync<SupabaseProjectEvent>(
            "append_project_event",
            new
            {
                p_project_id = projectId,
                p_event_type = eventType,
                p_payload = payload,
                p_idempotency_key = idempotencyKey,
            },
            cancellationToken).ConfigureAwait(false);

    public Task<IReadOnlyList<SupabaseDevice>> GetOrganizationDevicesAsync(
        Guid organizationId,
        CancellationToken cancellationToken = default)
        => GetRowsAsync<SupabaseDevice>(
            $"rest/v1/devices?organization_id=eq.{organizationId:D}&revoked_at=is.null&order=created_at.asc",
            cancellationToken);

    public async Task<IReadOnlyList<SupabaseDevice>> GetProjectDevicesAsync(
        Guid projectId,
        CancellationToken cancellationToken = default)
        => await SendAsync<List<SupabaseDevice>>(
            HttpMethod.Post,
            "rest/v1/rpc/get_project_devices",
            new { p_project_id = projectId },
            requireSession: true,
            cancellationToken,
            preferRepresentation: true).ConfigureAwait(false);

    public Task<IReadOnlyList<SupabaseOrganization>> GetOrganizationsAsync(
        CancellationToken cancellationToken = default)
        => GetRowsAsync<SupabaseOrganization>(
            "rest/v1/organizations?order=name.asc",
            cancellationToken);

    public Task<IReadOnlyList<SupabaseProject>> GetProjectsAsync(
        Guid organizationId,
        CancellationToken cancellationToken = default)
        => GetRowsAsync<SupabaseProject>(
            $"rest/v1/projects?organization_id=eq.{organizationId:D}&order=name.asc",
            cancellationToken);

    public async Task<SupabaseOrganization> CreateOrganizationAsync(
        string name,
        string slug,
        CancellationToken cancellationToken = default)
        => await RpcAsync<SupabaseOrganization>(
            "create_organization",
            new { p_name = name, p_slug = slug },
            cancellationToken).ConfigureAwait(false);

    public async Task<SupabaseProject> CreateProjectAsync(
        Guid organizationId,
        string name,
        string slug,
        string description = "",
        CancellationToken cancellationToken = default)
        => await RpcAsync<SupabaseProject>(
            "create_project",
            new
            {
                p_organization_id = organizationId,
                p_name = name,
                p_slug = slug,
                p_description = description,
            },
            cancellationToken).ConfigureAwait(false);

    public Task<IReadOnlyList<SupabaseProjectEvent>> GetProjectEventsSinceAsync(
        Guid projectId,
        long afterSequence,
        int limit = 200,
        CancellationToken cancellationToken = default)
    {
        limit = Math.Clamp(limit, 1, 1000);
        return GetRowsAsync<SupabaseProjectEvent>(
            $"rest/v1/project_events?project_id=eq.{projectId:D}&sequence=gt.{afterSequence}&order=sequence.asc&limit={limit}",
            cancellationToken);
    }

    public Task<IReadOnlyList<SupabaseSyncState>> GetProjectSyncStatesAsync(
        Guid projectId,
        CancellationToken cancellationToken = default)
        => GetRowsAsync<SupabaseSyncState>(
            $"rest/v1/sync_states?project_id=eq.{projectId:D}&order=last_observed_at.desc",
            cancellationToken);

    public async Task<SupabaseSyncFolder> EnsureSyncFolderAsync(
        Guid projectId,
        string folderId,
        string label,
        string relativePath,
        string mode,
        CancellationToken cancellationToken = default)
    {
        var created = await RpcAsync<SupabaseSyncFolder>(
            "ensure_sync_folder",
            new
            {
                p_project_id = projectId,
                p_folder_id = folderId,
                p_label = label,
                p_relative_path = relativePath,
                p_mode = mode,
            },
            cancellationToken).ConfigureAwait(false);

        return created;
    }

    private async Task<IReadOnlyList<T>> GetRowsAsync<T>(string path, CancellationToken cancellationToken)
        => await SendAsync<List<T>>(
            HttpMethod.Get,
            path,
            body: null,
            requireSession: true,
            cancellationToken).ConfigureAwait(false);

    private async Task<T> RpcAsync<T>(string function, object payload, CancellationToken cancellationToken)
        => await SendAsync<T>(
            HttpMethod.Post,
            $"rest/v1/rpc/{function}",
            payload,
            requireSession: true,
            cancellationToken,
            preferRepresentation: true).ConfigureAwait(false);

    private async Task<T> SendAsync<T>(
        HttpMethod method,
        string path,
        object? body,
        bool requireSession,
        CancellationToken cancellationToken,
        bool preferRepresentation = false,
        string? prefer = null)
    {
        if (requireSession && Session is null)
        {
            throw new InvalidOperationException("A Central precisa de uma sessão Supabase autenticada.");
        }

        if (requireSession)
        {
            await GetValidSessionAsync(cancellationToken).ConfigureAwait(false);
        }

        using var request = new HttpRequestMessage(method, new Uri(_options.Url, path));
        request.Headers.TryAddWithoutValidation("apikey", _options.PublishableKey);
        if (Session is not null)
        {
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", Session.AccessToken);
        }

        if (prefer is not null)
        {
            request.Headers.TryAddWithoutValidation("Prefer", prefer);
        }
        else if (preferRepresentation)
        {
            request.Headers.TryAddWithoutValidation("Prefer", "return=representation");
        }

        if (body is not null)
        {
            request.Content = new StringContent(
                JsonSerializer.Serialize(body, _json),
                Encoding.UTF8,
                "application/json");
        }

        using var response = await _httpClient.SendAsync(
            request,
            HttpCompletionOption.ResponseHeadersRead,
            cancellationToken).ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
        {
            throw await CreateRequestExceptionAsync(response).ConfigureAwait(false);
        }

        var value = await response.Content.ReadFromJsonAsync<T>(_json, cancellationToken).ConfigureAwait(false);
        return value ?? throw new SupabaseRequestException(
            response.StatusCode,
            "empty_response",
            "O Supabase respondeu sem o corpo esperado.");
    }

    private static async Task<SupabaseRequestException> CreateRequestExceptionAsync(HttpResponseMessage response)
    {
        var body = await response.Content.ReadAsStringAsync().ConfigureAwait(false);
        var code = "supabase_request_failed";
        try
        {
            using var document = JsonDocument.Parse(body);
            if (document.RootElement.TryGetProperty("code", out var codeElement))
            {
                code = codeElement.GetString() ?? code;
            }
            else if (document.RootElement.TryGetProperty("error_code", out var errorCodeElement))
            {
                code = errorCodeElement.GetString() ?? code;
            }
        }
        catch (JsonException)
        {
            // The response is deliberately not copied into the exception: it
            // may contain provider details or an echoed credential.
        }

        return new SupabaseRequestException(
            response.StatusCode,
            code,
            $"O Supabase respondeu {(int)response.StatusCode} {response.ReasonPhrase}.");
    }

    private sealed class AuthResponse
    {
        [JsonPropertyName("access_token")]
        public string? AccessToken { get; init; }

        [JsonPropertyName("refresh_token")]
        public string? RefreshToken { get; init; }

        [JsonPropertyName("expires_in")]
        public int ExpiresIn { get; init; }

        [JsonPropertyName("user")]
        public AuthUser? User { get; init; }

        public SupabaseSession ToSession(string? fallbackRefreshToken = null)
        {
            var refreshToken = string.IsNullOrWhiteSpace(RefreshToken)
                ? fallbackRefreshToken
                : RefreshToken;
            if (string.IsNullOrWhiteSpace(AccessToken) || string.IsNullOrWhiteSpace(refreshToken))
            {
                throw new SupabaseRequestException(
                    System.Net.HttpStatusCode.BadGateway,
                    "auth_session_missing",
                    "A autenticação não retornou uma sessão completa.");
            }

            return new SupabaseSession(
                AccessToken,
                refreshToken,
                DateTimeOffset.UtcNow.AddSeconds(Math.Max(60, ExpiresIn)),
                Guid.TryParse(User?.Id, out var id) ? id : null,
                User?.Email);
        }
    }

    private sealed class AuthUser
    {
        [JsonPropertyName("id")]
        public string? Id { get; init; }

        [JsonPropertyName("email")]
        public string? Email { get; init; }
    }
}
