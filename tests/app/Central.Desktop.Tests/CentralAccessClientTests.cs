using System.Net;
using System.Net.Http;
using Central.Desktop.Services;
using Xunit;

namespace Central.Desktop.Tests;

public sealed class CentralAccessClientTests
{
    [Fact]
    public async Task Rejects_remote_bridge_before_sending_the_shared_key()
    {
        var handler = new RecordingHandler();
        var client = new CentralAccessClient(
            handler,
            "https://example.com/bridge",
            new string('a', 32),
            "client-test-1",
            null);

        var result = await client.RequestCodeAsync("42");

        Assert.False(result.Success);
        Assert.Empty(handler.Requests);
    }

    [Fact]
    public async Task Rejects_missing_or_placeholder_bridge_configuration()
    {
        var handler = new RecordingHandler();
        var missingUrl = new CentralAccessClient(
            handler,
            null,
            new string('a', 32),
            "client-test-1",
            null);
        var placeholderKey = new CentralAccessClient(
            handler,
            "http://127.0.0.1:8765/",
            "generate-a-local-secret",
            "client-test-1",
            null);

        Assert.False((await missingUrl.RequestCodeAsync("42")).Success);
        Assert.False((await placeholderKey.RequestCodeAsync("42")).Success);
        Assert.Empty(handler.Requests);
    }

    [Fact]
    public async Task Keeps_and_reuses_the_short_session_token()
    {
        var handler = new RecordingHandler();
        var client = new CentralAccessClient(
            handler,
            "http://127.0.0.1:8765/",
            new string('a', 32),
            "client-test-1",
            "00000000-0000-4000-8000-000000000001");

        var verified = await client.VerifyCodeAsync("42", "123456");
        var validated = await client.ValidateSessionAsync(
            Guid.Parse("00000000-0000-4000-8000-000000000001"));

        Assert.True(verified.Success);
        Assert.True(validated.Success);
        Assert.NotNull(client.Session);
        Assert.Equal("session-token", client.Session!.Token);
        Assert.Equal(2, handler.Requests.Count);
        Assert.Contains("Bearer session-token", handler.Requests[1].Headers.Authorization?.ToString());
    }

    [Fact]
    public async Task Rejects_a_session_for_another_client_or_project()
    {
        var handler = new RecordingHandler
        {
            SessionClientId = "another-client",
            SessionProjectId = "00000000-0000-4000-8000-000000000002",
        };
        var client = new CentralAccessClient(
            handler,
            "http://127.0.0.1:8765/",
            new string('a', 32),
            "client-test-1",
            "00000000-0000-4000-8000-000000000001");

        var verified = await client.VerifyCodeAsync("42", "123456");

        Assert.False(verified.Success);
        Assert.Null(client.Session);
    }

    private sealed class RecordingHandler : HttpMessageHandler
    {
        public List<HttpRequestMessage> Requests { get; } = new();
        public string SessionClientId { get; init; } = "client-test-1";
        public string SessionProjectId { get; init; } = "00000000-0000-4000-8000-000000000001";

        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            Requests.Add(request);
            var body = request.RequestUri!.AbsolutePath.EndsWith("/session", StringComparison.Ordinal)
                ? $"{{\"ok\":true,\"message\":\"Sessão válida.\",\"session\":{{\"peace_id\":42,\"subject\":\"discord:10\",\"client_id\":\"{SessionClientId}\",\"scope\":[\"central:access\",\"central:sync\"],\"project_id\":\"{SessionProjectId}\",\"expires_at\":\"2099-01-01T00:00:00+00:00\"}}}}"
                : $"{{\"ok\":true,\"message\":\"Acesso liberado.\",\"session\":{{\"token\":\"session-token\",\"peace_id\":42,\"subject\":\"discord:10\",\"client_id\":\"{SessionClientId}\",\"scope\":[\"central:access\",\"central:sync\"],\"project_id\":\"{SessionProjectId}\",\"expires_at\":\"2099-01-01T00:00:00+00:00\"}}}}";
            return Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(body),
            });
        }
    }
}
