using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Central.Core.Connectivity;

/// <summary>
/// Minimal adapter for the official Syncthing REST API. It never edits an
/// arbitrary remote machine; the base address is expected to be the local GUI
/// endpoint. The app may use it to add an explicitly approved peer/folder.
/// </summary>
public sealed class SyncthingClient
{
    private readonly HttpClient _httpClient;
    private readonly Uri _baseUri;
    private readonly string _apiKey;

    public SyncthingClient(HttpClient httpClient, Uri baseUri, string apiKey)
    {
        _httpClient = httpClient ?? throw new ArgumentNullException(nameof(httpClient));
        _baseUri = baseUri ?? throw new ArgumentNullException(nameof(baseUri));
        if (!IsLoopback(baseUri))
        {
            throw new ArgumentException("A GUI do Syncthing precisa estar em loopback.", nameof(baseUri));
        }
        _apiKey = string.IsNullOrWhiteSpace(apiKey) ? throw new ArgumentException("A chave local do Syncthing é obrigatória.", nameof(apiKey)) : apiKey;
    }

    public async Task<SyncthingStatus> GetStatusAsync(CancellationToken cancellationToken = default)
    {
        using var response = await SendAsync(HttpMethod.Get, "rest/system/status", null, cancellationToken).ConfigureAwait(false);
        var document = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false), cancellationToken: cancellationToken).ConfigureAwait(false);
        var root = document.RootElement;
        return new SyncthingStatus(
            root.TryGetProperty("myID", out var id) ? id.GetString() ?? string.Empty : string.Empty,
            root.TryGetProperty("version", out var version) ? version.GetString() ?? string.Empty : string.Empty);
    }

    public async Task<SyncthingFolderStatus> GetFolderStatusAsync(
        string folderId,
        CancellationToken cancellationToken = default)
    {
        var encoded = Uri.EscapeDataString(folderId);
        using var response = await SendAsync(
            HttpMethod.Get,
            $"rest/db/status?folder={encoded}",
            null,
            cancellationToken).ConfigureAwait(false);
        var document = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false), cancellationToken: cancellationToken).ConfigureAwait(false);
        var root = document.RootElement;
        return new SyncthingFolderStatus(
            folderId,
            root.TryGetProperty("state", out var state) ? state.GetString() ?? "unknown" : "unknown",
            root.TryGetProperty("needItems", out var needItems) && needItems.TryGetInt32(out var count) ? count : 0,
            root.TryGetProperty("needBytes", out var needBytes) && needBytes.TryGetInt64(out var bytes) ? bytes : 0,
            root.TryGetProperty("error", out var error) ? error.GetString() : null,
            DateTimeOffset.UtcNow);
    }

    public async Task<IReadOnlyList<SyncthingPeerConnection>> GetConnectionsAsync(
        CancellationToken cancellationToken = default)
    {
        using var response = await SendAsync(
            HttpMethod.Get,
            "rest/system/connections",
            null,
            cancellationToken).ConfigureAwait(false);
        using var document = await JsonDocument.ParseAsync(
            await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false),
            cancellationToken: cancellationToken).ConfigureAwait(false);

        if (!document.RootElement.TryGetProperty("connections", out var connections)
            || connections.ValueKind != JsonValueKind.Object)
        {
            return Array.Empty<SyncthingPeerConnection>();
        }

        return connections.EnumerateObject()
            .Select(item => new SyncthingPeerConnection(
                item.Name,
                item.Value.TryGetProperty("connected", out var connected) && connected.GetBoolean(),
                item.Value.TryGetProperty("address", out var address) ? address.GetString() : null,
                item.Value.TryGetProperty("clientVersion", out var version) ? version.GetString() : null))
            .ToArray();
    }

    public async Task<IReadOnlyList<JsonElement>> GetEventsSinceAsync(
        long sinceId,
        CancellationToken cancellationToken = default)
    {
        using var response = await SendAsync(
            HttpMethod.Get,
            $"rest/events?since={Math.Max(0, sinceId)}&limit=500",
            null,
            cancellationToken).ConfigureAwait(false);
        var document = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false), cancellationToken: cancellationToken).ConfigureAwait(false);
        return document.RootElement.ValueKind == JsonValueKind.Array
            ? document.RootElement.EnumerateArray().Select(item => item.Clone()).ToArray()
            : Array.Empty<JsonElement>();
    }

    public async Task<SyncthingEnsureResult> EnsurePeerAndFolderAsync(
        string folderId,
        string label,
        string path,
        string mode,
        IReadOnlyList<SyncthingPeer> peers,
        CancellationToken cancellationToken = default)
    {
        if (mode is not ("send-only" or "receive-only" or "send-receive"))
        {
            throw new ArgumentOutOfRangeException(nameof(mode));
        }

        var devices = await GetArrayAsync("rest/config/devices", cancellationToken).ConfigureAwait(false);
        var deviceChanged = false;
        foreach (var peer in peers)
        {
            var existingDevice = devices.OfType<JsonObject>().FirstOrDefault(item =>
                string.Equals(item["deviceID"]?.GetValue<string>(), peer.DeviceId, StringComparison.Ordinal));
            if (existingDevice is not null)
            {
                if (string.IsNullOrWhiteSpace(existingDevice["name"]?.GetValue<string>())
                    && !string.IsNullOrWhiteSpace(peer.Name))
                {
                    existingDevice["name"] = peer.Name;
                    deviceChanged = true;
                }

                continue;
            }

            var defaults = await GetObjectAsync("rest/config/defaults/device", cancellationToken).ConfigureAwait(false);
            defaults["deviceID"] = peer.DeviceId;
            defaults["name"] = peer.Name;
            devices.Add(defaults);
            deviceChanged = true;
        }

        if (deviceChanged)
        {
            await PutJsonAsync("rest/config/devices", devices, cancellationToken).ConfigureAwait(false);
        }

        var folders = await GetArrayAsync("rest/config/folders", cancellationToken).ConfigureAwait(false);
        var folder = folders.OfType<JsonObject>().FirstOrDefault(item =>
            string.Equals(item["id"]?.GetValue<string>(), folderId, StringComparison.Ordinal));
        var folderChanged = false;
        if (folder is null)
        {
            folder = await GetObjectAsync("rest/config/defaults/folder", cancellationToken).ConfigureAwait(false);
            folder["id"] = folderId;
            folder["label"] = label;
            folder["path"] = path;
            folder["type"] = ToSyncthingFolderType(mode);
            folder["devices"] = CreatePeerArray(peers);
            folders.Add(folder);
            folderChanged = true;
        }
        else
        {
            var existingPath = folder["path"]?.GetValue<string>();
            if (!string.IsNullOrWhiteSpace(existingPath)
                && !string.Equals(existingPath, path, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException(
                    $"A pasta Syncthing {folderId} já aponta para outra localização local: {existingPath}.");
            }

            if (!string.Equals(folder["label"]?.GetValue<string>(), label, StringComparison.Ordinal))
            {
                folder["label"] = label;
                folderChanged = true;
            }

            if (!string.Equals(folder["path"]?.GetValue<string>(), path, StringComparison.OrdinalIgnoreCase))
            {
                folder["path"] = path;
                folderChanged = true;
            }

            var requestedType = ToSyncthingFolderType(mode);
            if (!string.Equals(folder["type"]?.GetValue<string>(), requestedType, StringComparison.OrdinalIgnoreCase))
            {
                folder["type"] = requestedType;
                folderChanged = true;
            }

            var configuredDevices = folder["devices"] as JsonArray ?? new JsonArray();
            if (folder["devices"] is null)
            {
                folder["devices"] = configuredDevices;
                folderChanged = true;
            }

            foreach (var peer in peers)
            {
                if (configuredDevices.OfType<JsonObject>().Any(item =>
                    string.Equals(item["deviceID"]?.GetValue<string>(), peer.DeviceId, StringComparison.Ordinal)))
                {
                    continue;
                }

                configuredDevices.Add(new JsonObject
                {
                    ["deviceID"] = peer.DeviceId,
                    ["introducedBy"] = string.Empty,
                    ["encryptionPassword"] = string.Empty,
                });
                folderChanged = true;
            }
        }

        if (folderChanged)
        {
            await PutJsonAsync("rest/config/folders", folders, cancellationToken).ConfigureAwait(false);
        }

        var restartRequired = await GetRestartRequiredAsync(cancellationToken).ConfigureAwait(false);
        return new SyncthingEnsureResult(deviceChanged || folderChanged, restartRequired, folderId, path, mode);
    }

    private static string ToSyncthingFolderType(string mode)
        => mode switch
        {
            "send-only" => "sendonly",
            "receive-only" => "receiveonly",
            _ => "sendreceive",
        };

    private static JsonArray CreatePeerArray(IReadOnlyList<SyncthingPeer> peers)
        => new(
            peers.Select(peer => (JsonNode)new JsonObject
            {
                ["deviceID"] = peer.DeviceId,
                ["introducedBy"] = string.Empty,
                ["encryptionPassword"] = string.Empty,
            }).ToArray());

    public async Task<bool> GetRestartRequiredAsync(CancellationToken cancellationToken = default)
    {
        using var response = await SendAsync(HttpMethod.Get, "rest/config/restart-required", null, cancellationToken).ConfigureAwait(false);
        var document = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false), cancellationToken: cancellationToken).ConfigureAwait(false);
        return document.RootElement.TryGetProperty("requiresRestart", out var value) && value.GetBoolean();
    }

    public async Task RestartAsync(CancellationToken cancellationToken = default)
    {
        using var response = await SendAsync(HttpMethod.Post, "rest/system/restart", string.Empty, cancellationToken).ConfigureAwait(false);
    }

    public async Task SetFolderPausedAsync(
        string folderId,
        bool paused,
        CancellationToken cancellationToken = default)
    {
        var encoded = Uri.EscapeDataString(folderId);
        using var response = await SendAsync(
            HttpMethod.Patch,
            $"rest/config/folders/{encoded}",
            JsonSerializer.Serialize(new { paused }),
            cancellationToken).ConfigureAwait(false);
    }

    private async Task<JsonArray> GetArrayAsync(string path, CancellationToken cancellationToken)
    {
        using var response = await SendAsync(HttpMethod.Get, path, null, cancellationToken).ConfigureAwait(false);
        var document = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false), cancellationToken: cancellationToken).ConfigureAwait(false);
        return JsonNode.Parse(document.RootElement.GetRawText())?.AsArray()
            ?? throw new InvalidOperationException("O Syncthing não retornou uma lista JSON.");
    }

    private async Task<JsonObject> GetObjectAsync(string path, CancellationToken cancellationToken)
    {
        using var response = await SendAsync(HttpMethod.Get, path, null, cancellationToken).ConfigureAwait(false);
        var document = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false), cancellationToken: cancellationToken).ConfigureAwait(false);
        return JsonNode.Parse(document.RootElement.GetRawText())?.AsObject()
            ?? throw new InvalidOperationException("O Syncthing não retornou um objeto JSON.");
    }

    private async Task PutJsonAsync(string path, JsonNode body, CancellationToken cancellationToken)
    {
        using var response = await SendAsync(HttpMethod.Put, path, body.ToJsonString(), cancellationToken).ConfigureAwait(false);
    }

    private async Task<HttpResponseMessage> SendAsync(
        HttpMethod method,
        string path,
        string? json,
        CancellationToken cancellationToken)
    {
        var request = new HttpRequestMessage(method, new Uri(_baseUri, path));
        request.Headers.TryAddWithoutValidation("X-API-Key", _apiKey);
        if (json is not null)
        {
            request.Content = new StringContent(json, Encoding.UTF8, "application/json");
        }

        var response = await _httpClient.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken).ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
        {
            response.Dispose();
            throw new HttpRequestException($"Syncthing respondeu {(int)response.StatusCode} {response.ReasonPhrase}.");
        }

        return response;
    }

    private static bool IsLoopback(Uri uri)
        => uri.IsLoopback
            || string.Equals(uri.Host, "localhost", StringComparison.OrdinalIgnoreCase)
            || string.Equals(uri.Host, "0.0.0.0", StringComparison.Ordinal);
}
