namespace Central.Desktop.Models;

/// <summary>
/// A local, deterministic request record used to exercise the dashboard table.
/// It is intentionally not a transport or provider audit record yet.
/// </summary>
public sealed record RequestLogEntry(
    string Time,
    string Date,
    string Account,
    string Plan,
    string ApiKeyLabel,
    string Model,
    string Transport,
    string TransportDetail,
    string Status,
    string Ttft,
    string Tone)
{
    public string AccessibleLabel => $"{Time}, {Account}, plano {Plan}, chave {ApiKeyLabel}, modelo {Model}, transporte {Transport}, status {Status}, primeiro token {Ttft}";
}
