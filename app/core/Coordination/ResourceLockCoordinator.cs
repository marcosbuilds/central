namespace Central.Core.Coordination;

/// <summary>
/// Deterministic coordination kernel used by offline tests and by the future gateway adapter.
/// It is deliberately process-local; shared authorization must use the Supabase RPC migration
/// in supabase/migrations, never this dictionary as an authority across computers.
/// </summary>
public sealed class ResourceLockCoordinator
{
    private readonly object _gate = new();
    private readonly Dictionary<Guid, ResourceLock> _locks = new();
    private readonly IClock _clock;
    private long _fencingToken;

    public ResourceLockCoordinator(IClock? clock = null)
    {
        _clock = clock ?? new SystemClock();
    }

    public LockAcquisitionResult TryAcquire(AcquireResourceLockCommand command)
    {
        try
        {
            command.Validate();
        }
        catch (ArgumentException exception)
        {
            return new LockAcquisitionResult(
                LockAcquisitionStatus.Invalid,
                null,
                Array.Empty<ResourceLock>(),
                exception.Message);
        }

        var normalizedPath = ResourcePath.Normalize(command.ResourcePath);
        lock (_gate)
        {
            var now = _clock.UtcNow;
            ExpireLeases(now);

            var conflicts = _locks.Values
                .Where(item => item.ProjectId == command.ProjectId
                    && item.State == ResourceLockState.Active
                    && item.ExpiresAt > now
                    && ResourcePath.Overlaps(item.ResourcePath, normalizedPath))
                .OrderBy(item => item.AcquiredAt)
                .ToArray();

            var existing = conflicts.FirstOrDefault(item =>
                item.ResourceKind == command.ResourceKind
                && string.Equals(item.ResourcePath, normalizedPath, StringComparison.Ordinal)
                && OwnersMatch(item.Owner, command.Owner));
            if (existing is not null)
            {
                var renewed = existing with
                {
                    LastRenewedAt = now,
                    ExpiresAt = now.Add(command.LeaseDuration)
                };
                _locks[renewed.Id] = renewed;
                return new LockAcquisitionResult(
                    LockAcquisitionStatus.AlreadyHeld,
                    renewed,
                    Array.Empty<ResourceLock>(),
                    "A sessão já possuía este recurso; o lease foi renovado.");
            }

            if (conflicts.Length > 0)
            {
                return new LockAcquisitionResult(
                    LockAcquisitionStatus.Conflict,
                    null,
                    conflicts,
                    "O recurso conflita com uma reserva ativa do mesmo projeto.");
            }

            var resourceLock = new ResourceLock(
                Guid.NewGuid(),
                command.ProjectId,
                command.TaskId,
                command.ResourceKind,
                normalizedPath,
                command.Owner,
                now,
                now,
                now.Add(command.LeaseDuration),
                ResourceLockState.Active,
                ++_fencingToken);
            _locks.Add(resourceLock.Id, resourceLock);
            return new LockAcquisitionResult(
                LockAcquisitionStatus.Acquired,
                resourceLock,
                Array.Empty<ResourceLock>(),
                "Reserva criada.");
        }
    }

    public bool TryRenew(Guid lockId, LockOwner owner, TimeSpan leaseDuration, out ResourceLock? renewed)
    {
        renewed = null;
        if (!IsLeaseDurationValid(leaseDuration))
        {
            return false;
        }

        lock (_gate)
        {
            var now = _clock.UtcNow;
            ExpireLeases(now);
            if (!_locks.TryGetValue(lockId, out var current)
                || current.State != ResourceLockState.Active
                || current.ExpiresAt <= now
                || !OwnersMatch(current.Owner, owner))
            {
                return false;
            }

            renewed = current with
            {
                LastRenewedAt = now,
                ExpiresAt = now.Add(leaseDuration)
            };
            _locks[lockId] = renewed;
            return true;
        }
    }

    public bool TryRelease(Guid lockId, LockOwner owner, out ResourceLock? released)
    {
        released = null;
        lock (_gate)
        {
            if (!_locks.TryGetValue(lockId, out var current)
                || current.State != ResourceLockState.Active
                || !OwnersMatch(current.Owner, owner))
            {
                return false;
            }

            released = current with { State = ResourceLockState.Released };
            _locks[lockId] = released;
            return true;
        }
    }

    public IReadOnlyList<ResourceLock> ListActive(Guid projectId)
    {
        lock (_gate)
        {
            ExpireLeases(_clock.UtcNow);
            return _locks.Values
                .Where(item => item.ProjectId == projectId && item.State == ResourceLockState.Active)
                .OrderBy(item => item.ResourcePath)
                .ToArray();
        }
    }

    public IReadOnlyList<ResourceLock> Snapshot()
    {
        lock (_gate)
        {
            ExpireLeases(_clock.UtcNow);
            return _locks.Values.OrderBy(item => item.AcquiredAt).ToArray();
        }
    }

    public int ExpireLeases()
    {
        lock (_gate)
        {
            return ExpireLeases(_clock.UtcNow);
        }
    }

    private int ExpireLeases(DateTimeOffset now)
    {
        var expired = 0;
        foreach (var current in _locks.Values.Where(item => item.State == ResourceLockState.Active && item.ExpiresAt <= now).ToArray())
        {
            _locks[current.Id] = current with { State = ResourceLockState.Expired };
            expired++;
        }

        return expired;
    }

    private static bool IsLeaseDurationValid(TimeSpan leaseDuration)
        => leaseDuration >= LeasePolicy.Minimum && leaseDuration <= LeasePolicy.Maximum;

    private static bool OwnersMatch(LockOwner left, LockOwner right)
        => left.UserId == right.UserId
            && left.DeviceId == right.DeviceId
            && string.Equals(left.AgentId, right.AgentId, StringComparison.Ordinal)
            && left.SessionId == right.SessionId;
}
