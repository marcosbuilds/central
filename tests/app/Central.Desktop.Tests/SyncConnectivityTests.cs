using System.Net;
using System.Text.Json;
using Central.Core.Connectivity;
using Xunit;

namespace Central.Desktop.Tests;

public sealed class SyncConnectivityTests
{
    [Fact]
    public void SupabaseOptions_require_explicit_environment_configuration()
    {
        var previousUrl = Environment.GetEnvironmentVariable("CENTRAL_SUPABASE_URL");
        var previousKey = Environment.GetEnvironmentVariable("CENTRAL_SUPABASE_PUBLISHABLE_KEY");
        try
        {
            Environment.SetEnvironmentVariable("CENTRAL_SUPABASE_URL", null);
            Environment.SetEnvironmentVariable("CENTRAL_SUPABASE_PUBLISHABLE_KEY", "publishable-key");
            Assert.Null(SupabaseOptions.FromEnvironment());

            Environment.SetEnvironmentVariable("CENTRAL_SUPABASE_URL", "https://central.example");
            var options = SupabaseOptions.FromEnvironment();

            Assert.NotNull(options);
            Assert.Equal(new Uri("https://central.example/"), options!.Url);
        }
        finally
        {
            Environment.SetEnvironmentVariable("CENTRAL_SUPABASE_URL", previousUrl);
            Environment.SetEnvironmentVariable("CENTRAL_SUPABASE_PUBLISHABLE_KEY", previousKey);
        }
    }

    [Fact]
    public void ProjectEventCursor_rejects_duplicates_and_detects_a_gap()
    {
        var cursor = new ProjectEventCursor();
        var first = Event(1);
        var third = Event(3);

        Assert.True(cursor.TryAccept(first));
        Assert.False(cursor.TryAccept(first));
        Assert.False(cursor.TryAccept(third));
        Assert.Equal(1, cursor.LastSequence);
        Assert.True(cursor.HasGap);

        Assert.Equal(2, cursor.ApplyReplay(new[] { Event(2), third }));
        Assert.Equal(3, cursor.LastSequence);
        Assert.False(cursor.HasGap);
    }

    [Fact]
    public void RealtimeProtocol_builds_an_authenticated_project_join_and_parses_notifications()
    {
        var projectId = Guid.NewGuid();
        var session = new SupabaseSession("access", "refresh", DateTimeOffset.UtcNow.AddMinutes(10), Guid.NewGuid(), "developer@example.test");
        var join = SupabaseRealtimeProtocol.CreateJoinMessage(projectId, session);

        Assert.Contains("phx_join", join, StringComparison.Ordinal);
        Assert.Contains($"project_id=eq.{projectId:D}", join, StringComparison.Ordinal);
        Assert.Contains("access_token", join, StringComparison.Ordinal);

        var eventId = Guid.NewGuid();
        var payload = $"{{\"topic\":\"realtime:project:{projectId:D}\",\"event\":\"postgres_changes\",\"payload\":{{\"data\":{{\"table\":\"project_events\",\"type\":\"INSERT\",\"record\":{{\"id\":\"{eventId:D}\",\"project_id\":\"{projectId:D}\",\"sequence\":1}}}}}}}}";

        Assert.True(SupabaseRealtimeProtocol.TryParseNotification(payload, out var notification));
        Assert.NotNull(notification);
        Assert.Equal("project_events", notification!.Table);
        Assert.Equal(eventId, notification.Record.GetProperty("id").GetGuid());
    }

    [Fact]
    public void RealtimeProtocol_requires_a_private_channel_and_supports_token_refresh_replies()
    {
        var projectId = Guid.NewGuid();
        var session = new SupabaseSession("access", "refresh", DateTimeOffset.UtcNow.AddMinutes(10), Guid.NewGuid(), "developer@example.test");
        var join = SupabaseRealtimeProtocol.CreateJoinMessage(projectId, session);
        Assert.Contains("\"private\":true", join, StringComparison.Ordinal);
        Assert.Contains("\"enabled\":true", join, StringComparison.Ordinal);

        var topic = $"realtime:project:{projectId:D}";
        var refresh = SupabaseRealtimeProtocol.CreateAccessTokenMessage(topic, "7", session with { AccessToken = "new-access" }, "8");
        Assert.Contains("\"event\":\"access_token\"", refresh, StringComparison.Ordinal);
        Assert.Contains("new-access", refresh, StringComparison.Ordinal);

        Assert.True(SupabaseRealtimeProtocol.TryParseReply(
            "{\"topic\":\"" + topic + "\",\"event\":\"phx_reply\",\"payload\":{\"status\":\"ok\"}}",
            out var replyTopic,
            out var replyStatus));
        Assert.Equal(topic, replyTopic);
        Assert.Equal("ok", replyStatus);
    }

    [Fact]
    public async Task SupabaseRestClient_signs_in_and_uses_the_session_for_rpc()
    {
        var userId = Guid.NewGuid();
        var requests = new List<HttpRequestMessage>();
        using var client = new HttpClient(new StubHandler(request =>
        {
            requests.Add(request);
            if (request.RequestUri!.AbsolutePath.EndsWith("/auth/v1/token", StringComparison.Ordinal))
            {
                return Json("""
                    {"access_token":"access-token","refresh_token":"refresh-token","expires_in":3600,"user":{"id":"00000000-0000-0000-0000-000000000001","email":"developer@example.test"}}
                    """);
            }

            return Json($$"""
                {"id":"{{userId:D}}","user_id":"00000000-0000-0000-0000-000000000001","organization_id":"00000000-0000-0000-0000-000000000002","device_name":"PC principal","syncthing_device_id":"ABC","client_key":"client","last_seen_at":"2026-11-06T00:00:00Z","revoked_at":null}
                """);
        }));

        var options = new SupabaseOptions(new Uri("https://central.example/"), "publishable-key");
        var supabase = new SupabaseRestClient(client, options);
        await supabase.SignInPasswordAsync("developer@example.test", "password");
        var device = await supabase.RegisterDeviceAsync(Guid.NewGuid(), "client", "PC principal", "ABC");

        Assert.Equal(userId, device.Id);
        Assert.Equal(2, requests.Count);
        Assert.All(requests, request => Assert.Equal("publishable-key", request.Headers.GetValues("apikey").Single()));
        Assert.Equal("Bearer", requests[1].Headers.Authorization?.Scheme);
        Assert.Equal("access-token", requests[1].Headers.Authorization?.Parameter);
    }

    [Fact]
    public async Task SupabaseRestClient_does_not_call_protected_rpc_without_a_session()
    {
        var called = false;
        using var client = new HttpClient(new StubHandler(_ =>
        {
            called = true;
            return Json("{}");
        }));
        var supabase = new SupabaseRestClient(
            client,
            new SupabaseOptions(new Uri("https://central.example/"), "publishable-key"));

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            supabase.HeartbeatDeviceAsync(Guid.NewGuid()));
        Assert.False(called);
    }

    [Fact]
    public async Task SupabaseRestClient_refreshes_an_expired_session_before_a_protected_call()
    {
        var requests = new List<HttpRequestMessage>();
        var requestBodies = new List<string>();
        using var client = new HttpClient(new StubHandler(request =>
        {
            requests.Add(request);
            requestBodies.Add(request.Content?.ReadAsStringAsync().GetAwaiter().GetResult() ?? string.Empty);
            if (request.RequestUri!.AbsolutePath.EndsWith("/auth/v1/token", StringComparison.Ordinal))
            {
                return Json("{\"access_token\":\"new-access\",\"refresh_token\":\"new-refresh\",\"expires_in\":3600,\"user\":{\"id\":\"00000000-0000-0000-0000-000000000001\"}}");
            }

            return Json("{\"id\":\"00000000-0000-0000-0000-000000000010\",\"user_id\":\"00000000-0000-0000-0000-000000000001\",\"organization_id\":\"00000000-0000-0000-0000-000000000002\",\"device_name\":\"PC\",\"syncthing_device_id\":null,\"client_key\":\"client\",\"last_seen_at\":null,\"revoked_at\":null}");
        }));

        var supabase = new SupabaseRestClient(
            client,
            new SupabaseOptions(new Uri("https://central.example/"), "publishable-key"));
        supabase.SetSession(new SupabaseSession(
            "expired-access",
            "refresh-token",
            DateTimeOffset.UtcNow.AddMinutes(-1),
            Guid.Parse("00000000-0000-0000-0000-000000000001"),
            "developer@example.test"));

        await supabase.HeartbeatDeviceAsync(Guid.Parse("00000000-0000-0000-0000-000000000010"));

        Assert.Equal(2, requests.Count);
        Assert.Contains("refresh_token", requestBodies[0]);
        Assert.Equal("new-access", requests[1].Headers.Authorization?.Parameter);
        Assert.Equal("new-access", supabase.Session?.AccessToken);
    }

    [Fact]
    public async Task SupabaseRestClient_uses_the_authenticated_rpc_for_sync_folder_creation()
    {
        HttpRequestMessage? captured = null;
        string capturedBody = string.Empty;
        using var client = new HttpClient(new StubHandler(request =>
        {
            captured = request;
            capturedBody = request.Content?.ReadAsStringAsync().GetAwaiter().GetResult() ?? string.Empty;
            return Json("{\"id\":\"00000000-0000-0000-0000-000000000020\",\"project_id\":\"00000000-0000-0000-0000-000000000002\",\"folder_id\":\"central-folder\",\"label\":\"Central\",\"relative_path\":\"shared-test\",\"mode\":\"receive-only\",\"enabled\":true,\"created_by\":\"00000000-0000-0000-0000-000000000001\",\"created_at\":\"2026-11-06T00:00:00Z\",\"updated_at\":\"2026-11-06T00:00:00Z\"}");
        }));

        var supabase = new SupabaseRestClient(
            client,
            new SupabaseOptions(new Uri("https://central.example/"), "publishable-key"));
        supabase.SetSession(new SupabaseSession(
            "access",
            "refresh",
            DateTimeOffset.UtcNow.AddMinutes(10),
            Guid.NewGuid(),
            "developer@example.test"));

        await supabase.EnsureSyncFolderAsync(
            Guid.Parse("00000000-0000-0000-0000-000000000002"),
            "central-folder",
            "Central",
            "shared-test",
            "receive-only");

        Assert.NotNull(captured);
        Assert.EndsWith("/rest/v1/rpc/ensure_sync_folder", captured!.RequestUri!.AbsolutePath, StringComparison.Ordinal);
        Assert.Contains("p_mode", capturedBody);
    }

    [Fact]
    public async Task SyncthingClient_reads_remote_connections_and_can_pause_a_folder()
    {
        var requests = new List<HttpRequestMessage>();
        using var client = new HttpClient(new StubHandler(request =>
        {
            requests.Add(request);
            if (request.RequestUri!.AbsolutePath.EndsWith("/rest/system/connections", StringComparison.Ordinal))
            {
                return Json("{\"connections\":{\"PEER\":{\"connected\":true,\"address\":\"tcp://127.0.0.1:22000\",\"clientVersion\":\"v2\"}}}");
            }

            return new HttpResponseMessage(HttpStatusCode.OK);
        }));

        var syncthing = new SyncthingClient(client, new Uri("http://127.0.0.1:8384/"), "local-api-key");
        var connections = await syncthing.GetConnectionsAsync();
        await syncthing.SetFolderPausedAsync("central-folder", paused: true);

        var peer = Assert.Single(connections);
        Assert.True(peer.Connected);
        Assert.Equal("PEER", peer.DeviceId);
        Assert.Equal("PATCH", requests[1].Method.Method);
        Assert.Contains("\"paused\":true", await requests[1].Content!.ReadAsStringAsync());
        Assert.All(requests, request => Assert.Equal("local-api-key", request.Headers.GetValues("X-API-Key").Single()));
    }

    [Fact]
    public async Task SupabaseRestClient_uses_project_scoped_devices_for_peer_discovery()
    {
        HttpRequestMessage? captured = null;
        using var client = new HttpClient(new StubHandler(request =>
        {
            captured = request;
            return Json("[{\"id\":\"00000000-0000-0000-0000-000000000030\",\"user_id\":\"00000000-0000-0000-0000-000000000001\",\"organization_id\":\"00000000-0000-0000-0000-000000000002\",\"device_name\":\"PC remoto\",\"syncthing_device_id\":\"PEER\",\"client_key\":\"client-remote\",\"last_seen_at\":null,\"revoked_at\":null}]");
        }));

        var supabase = new SupabaseRestClient(
            client,
            new SupabaseOptions(new Uri("https://central.example/"), "publishable-key"));
        supabase.SetSession(new SupabaseSession(
            "access",
            "refresh",
            DateTimeOffset.UtcNow.AddMinutes(10),
            Guid.NewGuid(),
            "developer@example.test"));

        var devices = await supabase.GetProjectDevicesAsync(Guid.Parse("00000000-0000-0000-0000-000000000002"));

        Assert.Single(devices);
        Assert.NotNull(captured);
        Assert.EndsWith("/rest/v1/rpc/get_project_devices", captured!.RequestUri!.AbsolutePath, StringComparison.Ordinal);
    }

    [Fact]
    public void SyncthingClient_rejects_non_loopback_gui_endpoints()
    {
        using var client = new HttpClient(new StubHandler(_ => Json("{}")));

        Assert.Throws<ArgumentException>(() => new SyncthingClient(
            client,
            new Uri("https://remote.example/"),
            "local-api-key"));
    }

    private static SupabaseProjectEvent Event(long sequence)
        => new(
            Guid.NewGuid(),
            Guid.NewGuid(),
            null,
            "test.event",
            sequence,
            JsonDocument.Parse("{}").RootElement.Clone(),
            DateTimeOffset.UtcNow,
            null);

    private static HttpResponseMessage Json(string json)
        => new(HttpStatusCode.OK)
        {
            Content = new StringContent(json, System.Text.Encoding.UTF8, "application/json"),
        };

    private sealed class StubHandler(Func<HttpRequestMessage, HttpResponseMessage> responder) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
            => Task.FromResult(responder(request));
    }
}
