namespace Central.Core.Coordination;

public enum ResourceKind
{
    Project,
    Task,
    Module,
    Directory,
    File,
    Dependency
}

public enum ResourceLockState
{
    Active,
    Released,
    Expired
}

public enum LockAcquisitionStatus
{
    Acquired,
    AlreadyHeld,
    Conflict,
    Invalid
}

public sealed record LockOwner(Guid UserId, Guid DeviceId, string AgentId, Guid SessionId)
{
    public void Validate()
    {
        if (UserId == Guid.Empty)
        {
            throw new ArgumentException("O identificador do usuário é obrigatório.", nameof(UserId));
        }

        if (DeviceId == Guid.Empty)
        {
            throw new ArgumentException("O identificador do dispositivo é obrigatório.", nameof(DeviceId));
        }

        if (string.IsNullOrWhiteSpace(AgentId))
        {
            throw new ArgumentException("O identificador do agente é obrigatório.", nameof(AgentId));
        }

        if (SessionId == Guid.Empty)
        {
            throw new ArgumentException("O identificador da sessão é obrigatório.", nameof(SessionId));
        }
    }
}

public sealed record AcquireResourceLockCommand(
    Guid ProjectId,
    Guid? TaskId,
    ResourceKind ResourceKind,
    string ResourcePath,
    LockOwner Owner,
    TimeSpan LeaseDuration)
{
    public void Validate()
    {
        if (ProjectId == Guid.Empty)
        {
            throw new ArgumentException("O identificador do projeto é obrigatório.", nameof(ProjectId));
        }

        Owner.Validate();
        _ = global::Central.Core.Coordination.ResourcePath.Normalize(ResourcePath);

        if (LeaseDuration < LeasePolicy.Minimum || LeaseDuration > LeasePolicy.Maximum)
        {
            throw new ArgumentOutOfRangeException(
                nameof(LeaseDuration),
                LeaseDuration,
                $"O lease deve durar entre {LeasePolicy.Minimum.TotalSeconds:0} e {LeasePolicy.Maximum.TotalSeconds:0} segundos.");
        }
    }
}

public sealed record ResourceLock(
    Guid Id,
    Guid ProjectId,
    Guid? TaskId,
    ResourceKind ResourceKind,
    string ResourcePath,
    LockOwner Owner,
    DateTimeOffset AcquiredAt,
    DateTimeOffset LastRenewedAt,
    DateTimeOffset ExpiresAt,
    ResourceLockState State,
    long FencingToken);

public sealed record LockAcquisitionResult(
    LockAcquisitionStatus Status,
    ResourceLock? Lock,
    IReadOnlyList<ResourceLock> Conflicts,
    string Message)
{
    public bool Succeeded => Status is LockAcquisitionStatus.Acquired or LockAcquisitionStatus.AlreadyHeld;
}

public interface IClock
{
    DateTimeOffset UtcNow { get; }
}

public sealed class SystemClock : IClock
{
    public DateTimeOffset UtcNow => DateTimeOffset.UtcNow;
}

public static class LeasePolicy
{
    public static readonly TimeSpan Minimum = TimeSpan.FromSeconds(15);
    public static readonly TimeSpan Maximum = TimeSpan.FromMinutes(15);
}
