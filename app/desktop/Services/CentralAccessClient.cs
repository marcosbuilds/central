using System.Net;
using System.Net.Http;
using System.IO;
using System.Text;
using System.Text.Json;

namespace Central.Desktop.Services;

public sealed record CentralAccessSession(
    string Token,
    DateTimeOffset ExpiresAt,
    string Subject,
    int PeaceId,
    string ClientId,
    IReadOnlyList<string> Scope,
    Guid? ProjectId);

public sealed record CentralAccessResult(
    bool Success,
    string Message,
    CentralAccessSession? Session = null);

/// <summary>
/// Local, authenticated bridge between the Central panel and the Discord bot.
/// The Discord token never leaves the bot process. The bridge URL is restricted
/// to HTTP loopback so the shared key cannot be sent to a remote endpoint.
/// </summary>
public sealed class CentralAccessClient
{
    private const string GenericDenial = "Não foi possível autenticar o acesso à Central.";
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        PropertyNameCaseInsensitive = true,
    };

    private readonly HttpClient _httpClient;
    private readonly Uri _baseUri;
    private readonly string _bridgeKey;
    private readonly string _clientId;
    private readonly Guid? _configuredProjectId;
    private string? _configurationError;

    public CentralAccessClient()
        : this(
            new HttpClientHandler(),
            Environment.GetEnvironmentVariable("CENTRAL_BRIDGE_URL"),
            Environment.GetEnvironmentVariable("CENTRAL_BRIDGE_KEY"),
            Environment.GetEnvironmentVariable("CENTRAL_CLIENT_ID"),
            Environment.GetEnvironmentVariable("CENTRAL_PROJECT_ID"))
    {
    }

    public CentralAccessClient(
        HttpMessageHandler handler,
        string? bridgeUrl,
        string? bridgeKey,
        string? clientId,
        string? projectId)
    {
        _httpClient = new HttpClient(handler ?? throw new ArgumentNullException(nameof(handler)))
        {
            Timeout = TimeSpan.FromSeconds(8),
        };

        if (!TryParseLoopbackUrl(bridgeUrl, out var parsedUrl))
        {
            _baseUri = new Uri("http://127.0.0.1:8765/");
            _configurationError = "A URL da ponte precisa apontar para HTTP local (loopback).";
        }
        else
        {
            _baseUri = parsedUrl;
        }

        _bridgeKey = bridgeKey?.Trim() ?? string.Empty;
        if (!IsValidBridgeKey(_bridgeKey))
        {
            _configurationError ??= "A chave local da ponte não está configurada corretamente.";
        }

        _clientId = IsValidClientId(clientId) ? clientId!.Trim() : LoadOrCreateClientId();
        _configuredProjectId = Guid.TryParse(projectId, out var parsedProjectId)
            ? (Guid?)parsedProjectId
            : null;
    }

    public CentralAccessSession? Session { get; private set; }

    public bool IsAuthenticated
        => Session is not null && Session.ExpiresAt > DateTimeOffset.UtcNow;

    public async Task<CentralAccessResult> RequestCodeAsync(
        string peaceId,
        CancellationToken cancellationToken = default)
    {
        if (!int.TryParse(peaceId.Trim(), out var parsedPeaceId) || parsedPeaceId <= 0)
        {
            return new CentralAccessResult(false, "Informe um ID Peace válido.");
        }

        return await PostAsync(
            "v1/central/auth/request",
            new
            {
                peace_id = parsedPeaceId,
                client_id = _clientId,
                project_id = _configuredProjectId?.ToString("D"),
            },
            cancellationToken).ConfigureAwait(false);
    }

    public async Task<CentralAccessResult> VerifyCodeAsync(
        string peaceId,
        string code,
        CancellationToken cancellationToken = default)
    {
        if (!int.TryParse(peaceId.Trim(), out var parsedPeaceId) || parsedPeaceId <= 0)
        {
            return new CentralAccessResult(false, "Informe um ID Peace válido.");
        }

        var result = await PostAsync(
            "v1/central/auth/verify",
            new
            {
                peace_id = parsedPeaceId,
                code = code.Trim(),
                client_id = _clientId,
                project_id = _configuredProjectId?.ToString("D"),
            },
            cancellationToken).ConfigureAwait(false);
        if (!result.Success || result.Session is null)
        {
            return result.Success
                ? new CentralAccessResult(false, "A ponte não devolveu uma sessão autenticada.")
                : result;
        }

        Session = result.Session;
        return result;
    }

    public async Task<CentralAccessResult> ValidateSessionAsync(
        Guid? projectId = null,
        CancellationToken cancellationToken = default)
    {
        if (Session is null || !IsAuthenticated)
        {
            Session = null;
            return new CentralAccessResult(false, GenericDenial);
        }

        var requestedProject = projectId ?? _configuredProjectId;
        var result = await PostAsync(
            "v1/central/auth/session",
            new
            {
                client_id = _clientId,
                project_id = requestedProject?.ToString("D"),
            },
            cancellationToken,
            Session.Token).ConfigureAwait(false);
        if (!result.Success || result.Session is null)
        {
            Session = null;
            return result;
        }

        Session = result.Session with { Token = Session.Token };
        return new CentralAccessResult(true, result.Message, Session);
    }

    public async Task RevokeSessionAsync(CancellationToken cancellationToken = default)
    {
        if (Session is null)
        {
            return;
        }

        try
        {
            await PostAsync(
                "v1/central/auth/revoke",
                new { client_id = _clientId },
                cancellationToken,
                Session.Token).ConfigureAwait(false);
        }
        finally
        {
            Session = null;
        }
    }

    private async Task<CentralAccessResult> PostAsync(
        string path,
        object payload,
        CancellationToken cancellationToken,
        string? sessionToken = null)
    {
        if (_configurationError is not null)
        {
            return new CentralAccessResult(false, _configurationError);
        }

        using var request = new HttpRequestMessage(HttpMethod.Post, new Uri(_baseUri, path));
        request.Headers.Add("X-Central-Bridge-Key", _bridgeKey);
        if (sessionToken is not null)
        {
            request.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", sessionToken);
        }
        request.Content = new StringContent(
            JsonSerializer.Serialize(payload, JsonOptions),
            Encoding.UTF8,
            "application/json");

        try
        {
            using var response = await _httpClient.SendAsync(request, cancellationToken).ConfigureAwait(false);
            var body = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
            var message = response.StatusCode is HttpStatusCode.Unauthorized or HttpStatusCode.Forbidden
                ? GenericDenial
                : ReadMessage(body) ?? $"A ponte respondeu {(int)response.StatusCode} {response.StatusCode}.";
            var session = response.IsSuccessStatusCode ? ReadSession(body, sessionToken) : null;
            return new CentralAccessResult(response.IsSuccessStatusCode, message, session);
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

    private static bool TryParseLoopbackUrl(string? value, out Uri uri)
    {
        uri = new Uri("http://127.0.0.1:8765/");
        if (!Uri.TryCreate(string.IsNullOrWhiteSpace(value) ? uri.ToString() : value.Trim(), UriKind.Absolute, out var parsed)
            || parsed.Scheme != Uri.UriSchemeHttp
            || parsed.Host is not ("localhost" or "127.0.0.1" or "::1")
            || parsed.UserInfo.Length > 0
            || !string.IsNullOrEmpty(parsed.Query)
            || !string.IsNullOrEmpty(parsed.Fragment)
            || parsed.AbsolutePath is not ("" or "/"))
        {
            return false;
        }

        uri = new UriBuilder(parsed) { Path = "/" }.Uri;
        return true;
    }

    private static bool IsValidBridgeKey(string value)
        => value.Length >= 32
            && !value.Equals("generate-a-local-secret", StringComparison.OrdinalIgnoreCase)
            && !value.StartsWith("replace-with-", StringComparison.OrdinalIgnoreCase);

    private static bool IsValidClientId(string? value)
        => value is not null
            && value.Trim().Length is >= 8 and <= 128
            && value.Trim().All(character => char.IsLetterOrDigit(character) || character is '.' or '_' or ':' or '-');

    private static CentralAccessSession? ReadSession(string body, string? fallbackToken = null)
    {
        try
        {
            using var document = JsonDocument.Parse(body);
            if (!document.RootElement.TryGetProperty("session", out var sessionElement))
            {
                return null;
            }

            var token = sessionElement.TryGetProperty("token", out var tokenElement)
                ? tokenElement.GetString()
                : fallbackToken;
            var expiresAt = sessionElement.TryGetProperty("expires_at", out var expiresElement)
                ? expiresElement.GetDateTimeOffset()
                : DateTimeOffset.MinValue;
            var subject = sessionElement.TryGetProperty("subject", out var subjectElement)
                ? subjectElement.GetString()
                : null;
            var clientId = sessionElement.TryGetProperty("client_id", out var clientElement)
                ? clientElement.GetString()
                : null;
            var peaceId = sessionElement.TryGetProperty("peace_id", out var peaceElement)
                ? peaceElement.GetInt32()
                : 0;
            var projectId = sessionElement.TryGetProperty("project_id", out var projectElement)
                && Guid.TryParse(projectElement.GetString(), out var parsedProjectId)
                ? (Guid?)parsedProjectId
                : null;
            var scope = sessionElement.TryGetProperty("scope", out var scopeElement)
                ? scopeElement.EnumerateArray().Select(item => item.GetString() ?? string.Empty).Where(item => item.Length > 0).ToArray()
                : Array.Empty<string>();

            return string.IsNullOrWhiteSpace(token)
                || string.IsNullOrWhiteSpace(subject)
                || string.IsNullOrWhiteSpace(clientId)
                || peaceId <= 0
                || expiresAt <= DateTimeOffset.UtcNow
                ? null
                : new CentralAccessSession(token, expiresAt, subject, peaceId, clientId, scope, projectId);
        }
        catch (JsonException)
        {
            return null;
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

    private static string LoadOrCreateClientId()
    {
        var root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Central");
        var path = Path.Combine(root, "central-access-client-id.txt");
        try
        {
            Directory.CreateDirectory(root);
            if (File.Exists(path) && Guid.TryParse(File.ReadAllText(path).Trim(), out var existing))
            {
                return existing.ToString("D");
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
}
