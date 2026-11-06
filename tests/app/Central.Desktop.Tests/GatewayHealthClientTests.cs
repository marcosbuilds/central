using System.Net;
using System.Net.Http;
using Central.Core.Connectivity;
using Xunit;

namespace Central.Desktop.Tests;

public sealed class GatewayHealthClientTests
{
    [Fact]
    public async Task CheckAsync_reads_health_without_exposing_configuration_values()
    {
        using var client = new GatewayHealthClient(new HttpClient(new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent("{\"status\":\"ok\",\"deployment\":\"pythonanywhere\",\"version\":\"0.2.0\",\"checked_at\":\"2026-11-06T01:59:09Z\",\"configuration\":{\"supabase_publishable_key_configured\":true}}")
        })));

        var snapshot = await client.CheckAsync(new Uri("https://gateway.example/"));

        Assert.True(snapshot.IsReachable);
        Assert.Equal("ok", snapshot.Status);
        Assert.Equal("pythonanywhere", snapshot.Deployment);
        Assert.Equal("0.2.0", snapshot.Version);
        Assert.Null(snapshot.Error);
    }

    [Fact]
    public async Task CheckAsync_reports_http_failure_as_unreachable()
    {
        using var client = new GatewayHealthClient(new HttpClient(new StubHandler(_ => new HttpResponseMessage(HttpStatusCode.ServiceUnavailable))));

        var snapshot = await client.CheckAsync(new Uri("https://gateway.example/"));

        Assert.False(snapshot.IsReachable);
        Assert.Contains("503", snapshot.Error);
    }

    [Fact]
    public async Task CheckAsync_rejects_non_http_urls_without_a_request()
    {
        var called = false;
        using var client = new GatewayHealthClient(new HttpClient(new StubHandler(_ =>
        {
            called = true;
            return new HttpResponseMessage(HttpStatusCode.OK);
        })));

        var snapshot = await client.CheckAsync(new Uri("file:///tmp/gateway"));

        Assert.False(snapshot.IsReachable);
        Assert.False(called);
        Assert.Contains("HTTP", snapshot.Error, StringComparison.OrdinalIgnoreCase);
    }

    private sealed class StubHandler(Func<HttpRequestMessage, HttpResponseMessage> responder) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
            => Task.FromResult(responder(request));
    }
}
