using System.Net.Http;
using System.Text;
using System.Text.Json;

namespace Central.Desktop.Services;

public sealed record CentralAccessResult(bool Success, string Message);

/// <summary>
/// Local, authenticated bridge between the Central panel and the Discord bot.
/// The Discord token never leaves the bot process.
/// </summary>
public sealed class CentralAccessClient
{
    private static readonly HttpClient HttpClient = new()
    {
        Timeout = TimeSpan.FromSeconds(8),
    };

    private readonly Uri _baseUri;
    private readonly string _bridgeKey;

    public CentralAccessClient()
    {
        var configuredUrl = Environment.GetEnvironmentVariable("CENTRAL_BRIDGE_URL")
            ?? "http://127.0.0.1:8765/";
        if (Uri.TryCreate(configuredUrl, UriKind.Absolute, out var parsed)
            && parsed.Scheme is "http" or "https")
        {
            var baseText = parsed.ToString();
            _baseUri = new Uri(baseText.EndsWith('/') ? baseText : baseText + "/");
        }
        else
        {
            _baseUri = new Uri("http://127.0.0.1:8765/");
        }
        _bridgeKey = Environment.GetEnvironmentVariable("CENTRAL_BRIDGE_KEY")?.Trim() ?? string.Empty;
    }

    public async Task<CentralAccessResult> RequestCodeAsync(string peaceId, CancellationToken cancellationToken = default)
    {
        if (!int.TryParse(peaceId.Trim(), out var parsedPeaceId) || parsedPeaceId <= 0)
        {
            return new CentralAccessResult(false, "Informe um ID Peace válido.");
        }

        return await PostAsync(
            "v1/central/auth/request",
            new { peace_id = parsedPeaceId },
            cancellationToken).ConfigureAwait(false);
    }

    public async Task<CentralAccessResult> VerifyCodeAsync(string peaceId, string code, CancellationToken cancellationToken = default)
    {
        if (!int.TryParse(peaceId.Trim(), out var parsedPeaceId) || parsedPeaceId <= 0)
        {
            return new CentralAccessResult(false, "Informe um ID Peace válido.");
        }

        return await PostAsync(
            "v1/central/auth/verify",
            new { peace_id = parsedPeaceId, code = code.Trim() },
            cancellationToken).ConfigureAwait(false);
    }

    private async Task<CentralAccessResult> PostAsync(
        string path,
        object payload,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(_bridgeKey))
        {
            return new CentralAccessResult(false, "A integração com o bot não está configurada nesta instalação.");
        }

        using var request = new HttpRequestMessage(HttpMethod.Post, new Uri(_baseUri, path));
        request.Headers.Add("X-Central-Bridge-Key", _bridgeKey);
        request.Content = new StringContent(
            JsonSerializer.Serialize(payload),
            Encoding.UTF8,
            "application/json");

        try
        {
            using var response = await HttpClient.SendAsync(request, cancellationToken).ConfigureAwait(false);
            var body = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
            var message = ReadMessage(body)
                ?? $"A ponte respondeu {(int)response.StatusCode} {response.StatusCode}.";
            return new CentralAccessResult(response.IsSuccessStatusCode, message);
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            return new CentralAccessResult(false, "A ponte do bot não respondeu dentro do prazo.");
        }
        catch (HttpRequestException)
        {
            return new CentralAccessResult(false, "Não foi possível alcançar o bot local. Verifique se ele está em execução.");
        }
    }

    private static string? ReadMessage(string body)
    {
        try
        {
            using var document = JsonDocument.Parse(body);
            return document.RootElement.TryGetProperty("message", out var message)
                ? message.GetString()
                : null;
        }
        catch (JsonException)
        {
            return null;
        }
    }
}
