using System.Net;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace Central.Core.Connectivity;

public sealed record SupabaseOptions(Uri Url, string PublishableKey)
{
    public static SupabaseOptions? FromEnvironment()
    {
        var configuredUrl = Environment.GetEnvironmentVariable("CENTRAL_SUPABASE_URL")
            ?? "https://ydouynbssldpjhlnawtm.supabase.co/";
        var publishableKey = Environment.GetEnvironmentVariable("CENTRAL_SUPABASE_PUBLISHABLE_KEY");

        return Uri.TryCreate(configuredUrl, UriKind.Absolute, out var uri)
            && uri.Scheme is "http" or "https"
            && !string.IsNullOrWhiteSpace(publishableKey)
            ? new SupabaseOptions(uri.ToString().EndsWith('/') ? uri : new Uri(uri + "/"), publishableKey)
            : null;
    }
}

public sealed record SupabaseSession(
    string AccessToken,
    string RefreshToken,
    DateTimeOffset ExpiresAt,
    Guid? UserId,
    string? Email);

public sealed record SupabaseOrganization(
    [property: JsonPropertyName("id")] Guid Id,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("slug")] string Slug);

public sealed record SupabaseProject(
    [property: JsonPropertyName("id")] Guid Id,
    [property: JsonPropertyName("organization_id")] Guid OrganizationId,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("slug")] string Slug,
    [property: JsonPropertyName("description")] string Description);

public sealed record SupabaseDevice(
    [property: JsonPropertyName("id")] Guid Id,
    [property: JsonPropertyName("user_id")] Guid UserId,
    [property: JsonPropertyName("organization_id")] Guid OrganizationId,
    [property: JsonPropertyName("device_name")] string DeviceName,
    [property: JsonPropertyName("syncthing_device_id")] string? SyncthingDeviceId,
    [property: JsonPropertyName("client_key")] string? ClientKey,
    [property: JsonPropertyName("last_seen_at")] DateTimeOffset? LastSeenAt,
    [property: JsonPropertyName("revoked_at")] DateTimeOffset? RevokedAt);

public sealed record SupabaseSyncFolder(
    [property: JsonPropertyName("id")] Guid Id,
    [property: JsonPropertyName("project_id")] Guid ProjectId,
    [property: JsonPropertyName("folder_id")] string FolderId,
    [property: JsonPropertyName("label")] string Label,
    [property: JsonPropertyName("relative_path")] string RelativePath,
    [property: JsonPropertyName("mode")] string Mode,
    [property: JsonPropertyName("enabled")] bool Enabled,
    [property: JsonPropertyName("created_by")] Guid CreatedBy,
    [property: JsonPropertyName("created_at")] DateTimeOffset CreatedAt,
    [property: JsonPropertyName("updated_at")] DateTimeOffset UpdatedAt);

public sealed record SupabaseSyncState(
    [property: JsonPropertyName("id")] Guid Id,
    [property: JsonPropertyName("project_id")] Guid ProjectId,
    [property: JsonPropertyName("device_id")] Guid DeviceId,
    [property: JsonPropertyName("state")] string State,
    [property: JsonPropertyName("pending_items")] int PendingItems,
    [property: JsonPropertyName("last_observed_at")] DateTimeOffset? LastObservedAt,
    [property: JsonPropertyName("detail")] string Detail);

public sealed record SupabaseProjectEvent(
    [property: JsonPropertyName("id")] Guid Id,
    [property: JsonPropertyName("project_id")] Guid ProjectId,
    [property: JsonPropertyName("actor_user_id")] Guid? ActorUserId,
    [property: JsonPropertyName("event_type")] string EventType,
    [property: JsonPropertyName("sequence")] long Sequence,
    [property: JsonPropertyName("payload")] JsonElement Payload,
    [property: JsonPropertyName("created_at")] DateTimeOffset CreatedAt,
    [property: JsonPropertyName("idempotency_key")] string? IdempotencyKey);

public sealed record SupabaseRealtimeNotification(
    string Topic,
    string Table,
    string Event,
    JsonElement Record);

public sealed class SupabaseRequestException : Exception
{
    public SupabaseRequestException(HttpStatusCode statusCode, string errorCode, string message)
        : base(message)
    {
        StatusCode = statusCode;
        ErrorCode = errorCode;
    }

    public HttpStatusCode StatusCode { get; }
    public string ErrorCode { get; }
}

public enum SyncStateKind
{
    Unknown,
    Syncing,
    Synced,
    Offline,
    Error,
    Conflict,
}

public sealed record SyncthingStatus(
    string DeviceId,
    string Version,
    string? Error = null);

public sealed record SyncthingFolderStatus(
    string FolderId,
    string State,
    int NeedItems,
    long NeedBytes,
    string? Error,
    DateTimeOffset ObservedAt);

public sealed record SyncthingPeer(string DeviceId, string Name);

public sealed record SyncthingPeerConnection(
    string DeviceId,
    bool Connected,
    string? Address,
    string? ClientVersion);

public sealed record SyncthingEnsureResult(
    bool Changed,
    bool RestartRequired,
    string FolderId,
    string Path,
    string Mode);

public static class ConnectivityJson
{
    public static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web)
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
    };
}
