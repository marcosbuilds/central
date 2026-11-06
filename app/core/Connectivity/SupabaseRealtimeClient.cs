using System.Net.WebSockets;
using System.Text;
using System.Text.Json;

namespace Central.Core.Connectivity;

public static class SupabaseRealtimeProtocol
{
    public static string CreateJoinMessage(Guid projectId, SupabaseSession session, string reference = "1")
    {
        var payload = new
        {
            config = new
            {
                broadcast = new { ack = false, self = false },
                presence = new
                {
                    enabled = true,
                    key = session.UserId?.ToString("D") ?? "central",
                },
                postgres_changes = new object[]
                {
                    new { @event = "*", schema = "public", table = "project_events", filter = $"project_id=eq.{projectId:D}" },
                    new { @event = "*", schema = "public", table = "sync_states", filter = $"project_id=eq.{projectId:D}" },
                },
                @private = true,
            },
            access_token = session.AccessToken,
        };

        return JsonSerializer.Serialize(new
        {
            topic = $"realtime:project:{projectId:D}",
            @event = "phx_join",
            payload,
            @ref = reference,
            join_ref = reference,
        }, ConnectivityJson.Options);
    }

    public static string CreateAccessTokenMessage(
        string topic,
        string joinReference,
        SupabaseSession session,
        string reference)
        => JsonSerializer.Serialize(new
        {
            topic,
            @event = "access_token",
            payload = new { access_token = session.AccessToken },
            @ref = reference,
            join_ref = joinReference,
        }, ConnectivityJson.Options);

    public static string CreateHeartbeatMessage(string reference)
        => JsonSerializer.Serialize(new
        {
            topic = "phoenix",
            @event = "heartbeat",
            payload = new { },
            @ref = reference,
        }, ConnectivityJson.Options);

    public static bool TryParseNotification(
        string json,
        out SupabaseRealtimeNotification? notification)
    {
        notification = null;
        try
        {
            using var document = JsonDocument.Parse(json);
            var root = document.RootElement;
            if (!root.TryGetProperty("event", out var eventElement)
                || !string.Equals(eventElement.GetString(), "postgres_changes", StringComparison.Ordinal))
            {
                return false;
            }

            if (!root.TryGetProperty("topic", out var topicElement)
                || !root.TryGetProperty("payload", out var payloadElement)
                || !payloadElement.TryGetProperty("data", out var dataElement)
                || !dataElement.TryGetProperty("table", out var tableElement)
                || !dataElement.TryGetProperty("record", out var recordElement))
            {
                return false;
            }

            notification = new SupabaseRealtimeNotification(
                topicElement.GetString() ?? string.Empty,
                tableElement.GetString() ?? string.Empty,
                dataElement.TryGetProperty("type", out var typeElement)
                    ? typeElement.GetString() ?? "*"
                    : "*",
                recordElement.Clone());
            return true;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    public static bool TryParseReply(
        string json,
        out string topic,
        out string status)
    {
        topic = string.Empty;
        status = string.Empty;
        try
        {
            using var document = JsonDocument.Parse(json);
            var root = document.RootElement;
            if (!root.TryGetProperty("event", out var eventElement)
                || !string.Equals(eventElement.GetString(), "phx_reply", StringComparison.Ordinal)
                || !root.TryGetProperty("payload", out var payloadElement)
                || !payloadElement.TryGetProperty("status", out var statusElement))
            {
                return false;
            }

            topic = root.TryGetProperty("topic", out var topicElement)
                ? topicElement.GetString() ?? string.Empty
                : string.Empty;
            status = statusElement.GetString() ?? string.Empty;
            return true;
        }
        catch (JsonException)
        {
            return false;
        }
    }
}

/// <summary>
/// Reconnectable Supabase Realtime consumer. It is intentionally a notification
/// transport; callers must replay the database cursor after every reconnect.
/// </summary>
public sealed class SupabaseRealtimeClient : IAsyncDisposable
{
    private readonly SupabaseOptions _options;
    private readonly SemaphoreSlim _sendLock = new(1, 1);
    private ClientWebSocket? _socket;
    private int _reference;

    public SupabaseRealtimeClient(SupabaseOptions options)
    {
        _options = options ?? throw new ArgumentNullException(nameof(options));
    }

    public event EventHandler<bool>? ConnectionChanged;

    public async Task RunAsync(
        Guid projectId,
        SupabaseSession session,
        Func<SupabaseRealtimeNotification, Task> onNotification,
        CancellationToken cancellationToken = default,
        Func<CancellationToken, Task<SupabaseSession>>? sessionProvider = null)
    {
        ArgumentNullException.ThrowIfNull(onNotification);
        var reconnectDelay = TimeSpan.FromSeconds(1);

        while (!cancellationToken.IsCancellationRequested)
        {
            try
            {
                var currentSession = sessionProvider is null
                    ? session
                    : await sessionProvider(cancellationToken).ConfigureAwait(false);
                await ConnectAndListenAsync(
                    projectId,
                    currentSession,
                    onNotification,
                    sessionProvider,
                    cancellationToken).ConfigureAwait(false);
                reconnectDelay = TimeSpan.FromSeconds(1);
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
            {
                break;
            }
            catch (WebSocketException)
            {
                await Task.Delay(reconnectDelay, cancellationToken).ConfigureAwait(false);
                reconnectDelay = TimeSpan.FromSeconds(Math.Min(30, reconnectDelay.TotalSeconds * 2));
            }
            catch (IOException)
            {
                await Task.Delay(reconnectDelay, cancellationToken).ConfigureAwait(false);
                reconnectDelay = TimeSpan.FromSeconds(Math.Min(30, reconnectDelay.TotalSeconds * 2));
            }
            catch (TimeoutException)
            {
                await Task.Delay(reconnectDelay, cancellationToken).ConfigureAwait(false);
                reconnectDelay = TimeSpan.FromSeconds(Math.Min(30, reconnectDelay.TotalSeconds * 2));
            }
            catch (InvalidOperationException)
            {
                await Task.Delay(reconnectDelay, cancellationToken).ConfigureAwait(false);
                reconnectDelay = TimeSpan.FromSeconds(Math.Min(30, reconnectDelay.TotalSeconds * 2));
            }
        }
    }

    private async Task ConnectAndListenAsync(
        Guid projectId,
        SupabaseSession session,
        Func<SupabaseRealtimeNotification, Task> onNotification,
        Func<CancellationToken, Task<SupabaseSession>>? sessionProvider,
        CancellationToken cancellationToken)
    {
        var socket = new ClientWebSocket();
        var topic = $"realtime:project:{projectId:D}";
        var joinReference = NextReference();
        var joined = false;
        var joinSignal = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);

        _socket = socket;
        socket.Options.SetRequestHeader("apikey", _options.PublishableKey);
        socket.Options.SetRequestHeader("Authorization", $"Bearer {session.AccessToken}");

        var builder = new UriBuilder(_options.Url)
        {
            Scheme = _options.Url.Scheme == "https" ? "wss" : "ws",
            Path = "/realtime/v1/websocket",
            Query = $"apikey={Uri.EscapeDataString(_options.PublishableKey)}&vsn=1.0.0",
        };

        try
        {
            await socket.ConnectAsync(builder.Uri, cancellationToken).ConfigureAwait(false);
            await SendTextAsync(
                SupabaseRealtimeProtocol.CreateJoinMessage(projectId, session, joinReference),
                cancellationToken).ConfigureAwait(false);

            using var linked = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            var receiveTask = ReceiveLoopAsync(onNotification, topic, joinSignal, linked.Token);
            var heartbeatTask = HeartbeatLoopAsync(topic, joinReference, session, sessionProvider, linked.Token);
            try
            {
                try
                {
                    await joinSignal.Task.WaitAsync(TimeSpan.FromSeconds(15), cancellationToken).ConfigureAwait(false);
                }
                catch (TimeoutException)
                {
                    throw new WebSocketException("O Supabase não confirmou a inscrição Realtime.");
                }

                joined = true;
                ConnectionChanged?.Invoke(this, true);
                await Task.WhenAny(receiveTask, heartbeatTask).ConfigureAwait(false);
            }
            finally
            {
                linked.Cancel();
                try
                {
                    await Task.WhenAll(receiveTask, heartbeatTask).ConfigureAwait(false);
                }
                catch (OperationCanceledException) when (linked.IsCancellationRequested)
                {
                }
            }

            await receiveTask.ConfigureAwait(false);
            await heartbeatTask.ConfigureAwait(false);
        }
        finally
        {
            if (joined)
            {
                ConnectionChanged?.Invoke(this, false);
            }

            if (ReferenceEquals(_socket, socket))
            {
                _socket = null;
            }

            try
            {
                if (socket.State is WebSocketState.Open or WebSocketState.CloseReceived)
                {
                    await socket.CloseAsync(
                        WebSocketCloseStatus.NormalClosure,
                        "Central reconectando",
                        CancellationToken.None).ConfigureAwait(false);
                }
            }
            catch (WebSocketException)
            {
            }
            catch (InvalidOperationException)
            {
            }
            finally
            {
                socket.Dispose();
            }
        }
    }

    private async Task ReceiveLoopAsync(
        Func<SupabaseRealtimeNotification, Task> onNotification,
        string topic,
        TaskCompletionSource<bool> joinSignal,
        CancellationToken cancellationToken)
    {
        var buffer = new byte[16 * 1024];
        try
        {
            while (!cancellationToken.IsCancellationRequested
                && _socket is { State: WebSocketState.Open } socket)
            {
                using var message = new MemoryStream();
                WebSocketReceiveResult result;
                do
                {
                    result = await socket.ReceiveAsync(buffer, cancellationToken).ConfigureAwait(false);
                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        throw new WebSocketException("Supabase Realtime encerrou a conexão.");
                    }

                    message.Write(buffer, 0, result.Count);
                }
                while (!result.EndOfMessage);

                var json = Encoding.UTF8.GetString(message.ToArray());
                if (SupabaseRealtimeProtocol.TryParseReply(json, out var replyTopic, out var replyStatus)
                    && string.Equals(replyTopic, topic, StringComparison.Ordinal)
                    && !joinSignal.Task.IsCompleted)
                {
                    if (!string.Equals(replyStatus, "ok", StringComparison.OrdinalIgnoreCase))
                    {
                        joinSignal.TrySetException(new WebSocketException("A inscrição Realtime foi recusada."));
                        throw new WebSocketException("A inscrição Realtime foi recusada.");
                    }

                    joinSignal.TrySetResult(true);
                }

                if (IsChannelFailure(json, topic))
                {
                    joinSignal.TrySetException(new WebSocketException("O canal Realtime foi encerrado."));
                    throw new WebSocketException("O canal Realtime foi encerrado.");
                }

                if (SupabaseRealtimeProtocol.TryParseNotification(json, out var notification)
                    && notification is not null)
                {
                    await onNotification(notification).ConfigureAwait(false);
                }
            }
        }
        catch (Exception exception) when (exception is WebSocketException or IOException or JsonException)
        {
            joinSignal.TrySetException(exception);
            throw;
        }
    }

    private async Task HeartbeatLoopAsync(
        string topic,
        string joinReference,
        SupabaseSession session,
        Func<CancellationToken, Task<SupabaseSession>>? sessionProvider,
        CancellationToken cancellationToken)
    {
        var currentSession = session;
        while (!cancellationToken.IsCancellationRequested)
        {
            await Task.Delay(TimeSpan.FromSeconds(20), cancellationToken).ConfigureAwait(false);
            if (sessionProvider is not null)
            {
                var refreshed = await sessionProvider(cancellationToken).ConfigureAwait(false);
                if (!string.Equals(refreshed.AccessToken, currentSession.AccessToken, StringComparison.Ordinal))
                {
                    await SendTextAsync(
                        SupabaseRealtimeProtocol.CreateAccessTokenMessage(
                            topic,
                            joinReference,
                            refreshed,
                            NextReference()),
                        cancellationToken).ConfigureAwait(false);
                    currentSession = refreshed;
                }
            }

            await SendTextAsync(
                SupabaseRealtimeProtocol.CreateHeartbeatMessage(NextReference()),
                cancellationToken).ConfigureAwait(false);
        }
    }

    private static bool IsChannelFailure(string json, string topic)
    {
        try
        {
            using var document = JsonDocument.Parse(json);
            var root = document.RootElement;
            if (!root.TryGetProperty("topic", out var topicElement)
                || !string.Equals(topicElement.GetString(), topic, StringComparison.Ordinal)
                || !root.TryGetProperty("event", out var eventElement))
            {
                return false;
            }

            var eventName = eventElement.GetString();
            return string.Equals(eventName, "phx_error", StringComparison.Ordinal)
                || string.Equals(eventName, "phx_close", StringComparison.Ordinal);
        }
        catch (JsonException)
        {
            return false;
        }
    }

    private async Task SendTextAsync(string text, CancellationToken cancellationToken)
    {
        if (_socket is not { State: WebSocketState.Open } socket)
        {
            throw new WebSocketException("Supabase Realtime não está conectado.");
        }

        await _sendLock.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var bytes = Encoding.UTF8.GetBytes(text);
            await socket.SendAsync(bytes, WebSocketMessageType.Text, true, cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _sendLock.Release();
        }
    }

    private string NextReference()
        => Interlocked.Increment(ref _reference).ToString(System.Globalization.CultureInfo.InvariantCulture);

    public async ValueTask DisposeAsync()
    {
        var socket = Interlocked.Exchange(ref _socket, null);
        if (socket is not null)
        {
            try
            {
                if (socket.State is WebSocketState.Open or WebSocketState.CloseReceived)
                {
                    await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Central encerrando", CancellationToken.None).ConfigureAwait(false);
                }
            }
            catch (WebSocketException)
            {
                // The peer may already have gone away; disposal remains safe.
            }
            catch (InvalidOperationException)
            {
                // The socket may have already transitioned during reconnect.
            }
            finally
            {
                socket.Dispose();
            }
        }

        _sendLock.Dispose();
    }
}

public sealed class ProjectEventCursor
{
    private readonly HashSet<Guid> _seenEventIds = new();

    public long LastSequence { get; private set; }
    public bool HasGap { get; private set; }

    public bool TryAccept(SupabaseProjectEvent projectEvent)
    {
        if (_seenEventIds.Contains(projectEvent.Id) || projectEvent.Sequence <= LastSequence)
        {
            return false;
        }

        if (LastSequence > 0 && projectEvent.Sequence != LastSequence + 1)
        {
            HasGap = true;
            return false;
        }

        _seenEventIds.Add(projectEvent.Id);
        LastSequence = projectEvent.Sequence;
        if (HasGap)
        {
            HasGap = false;
        }
        return true;
    }

    public int ApplyReplay(IEnumerable<SupabaseProjectEvent> events)
    {
        var accepted = 0;
        foreach (var projectEvent in events.OrderBy(item => item.Sequence))
        {
            if (_seenEventIds.Contains(projectEvent.Id) || projectEvent.Sequence <= LastSequence)
            {
                continue;
            }

            if (LastSequence > 0 && projectEvent.Sequence != LastSequence + 1)
            {
                HasGap = true;
                break;
            }

            _seenEventIds.Add(projectEvent.Id);
            LastSequence = projectEvent.Sequence;
            if (HasGap)
            {
                HasGap = false;
            }
            accepted++;
        }

        return accepted;
    }

    public void MarkSnapshot(long sequence)
    {
        if (sequence > LastSequence)
        {
            LastSequence = sequence;
        }

        HasGap = false;
    }
}
