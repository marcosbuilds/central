using System.Net;
using System.Net.Http;
using System.Text.Json;

namespace Central.Core.Connectivity;

public sealed record GatewayHealthSnapshot(
    bool IsReachable,
    string Status,
    string Deployment,
    string Version,
    DateTimeOffset? CheckedAt,
    string? Error)
{
    public static GatewayHealthSnapshot Pending => new(
        false,
        "pending",
        "unknown",
        "unknown",
        null,
        "Ainda não foi feita uma consulta ao gateway.");

    public static GatewayHealthSnapshot NotConfigured => new(
        false,
        "not-configured",
        "unknown",
        "unknown",
        null,
        "O gateway não está configurado.");
}

public sealed class GatewayHealthClient : IDisposable
{
    private readonly HttpClient _httpClient;
    private readonly bool _ownsHttpClient;

    public GatewayHealthClient(HttpClient? httpClient = null)
    {
        _httpClient = httpClient ?? new HttpClient();
        _ownsHttpClient = httpClient is null;
        _httpClient.Timeout = TimeSpan.FromSeconds(5);
    }

    public async Task<GatewayHealthSnapshot> CheckAsync(Uri? gatewayBaseUri, CancellationToken cancellationToken = default)
    {
        if (gatewayBaseUri is null)
        {
            return GatewayHealthSnapshot.NotConfigured;
        }

        if (!gatewayBaseUri.IsAbsoluteUri || gatewayBaseUri.Scheme is not ("http" or "https"))
        {
            return GatewayHealthSnapshot.Pending with
            {
                Error = "A URL do gateway precisa ser absoluta e usar HTTP ou HTTPS."
            };
        }

        var healthUri = new Uri(gatewayBaseUri, "healthz");

        try
        {
            using var response = await _httpClient.GetAsync(healthUri, cancellationToken).ConfigureAwait(false);
            var body = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);

            if (!response.IsSuccessStatusCode)
            {
                return GatewayHealthSnapshot.Pending with
                {
                    Error = $"O gateway respondeu {(int)response.StatusCode} {response.StatusCode}."
                };
            }

            using var document = JsonDocument.Parse(body);
            var root = document.RootElement;
            return new GatewayHealthSnapshot(
                true,
                ReadString(root, "status") ?? "unknown",
                ReadString(root, "deployment") ?? "unknown",
                ReadString(root, "version") ?? "unknown",
                ReadDateTime(root, "checked_at"),
                null);
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return GatewayHealthSnapshot.Pending with { Error = "A consulta ao gateway expirou após 5 segundos." };
        }
        catch (HttpRequestException exception)
        {
            return GatewayHealthSnapshot.Pending with { Error = $"Não foi possível alcançar o gateway: {exception.Message}" };
        }
        catch (JsonException)
        {
            return GatewayHealthSnapshot.Pending with { Error = "O gateway respondeu com um formato inválido." };
        }
    }

    private static string? ReadString(JsonElement root, string propertyName)
        => root.TryGetProperty(propertyName, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;

    private static DateTimeOffset? ReadDateTime(JsonElement root, string propertyName)
        => DateTimeOffset.TryParse(ReadString(root, propertyName), out var value) ? value : null;

    public void Dispose()
    {
        if (_ownsHttpClient)
        {
            _httpClient.Dispose();
        }
    }
}
