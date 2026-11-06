using Central.Core.Coordination;
using Xunit;

namespace Central.Desktop.Tests;

public sealed class CoordinationTests
{
    private static readonly Guid ProjectId = Guid.Parse("f7c0c1d2-7f3e-4f92-9f8d-0c0d93d3f901");

    [Fact]
    public void Resource_paths_are_case_insensitive_and_parent_locks_cover_children()
    {
        Assert.Equal("frontend\\auth", ResourcePath.Normalize(" ./Frontend/auth/ "));
        Assert.True(ResourcePath.Overlaps("frontend/auth", "FRONTEND\\AUTH\\login.cs"));
        Assert.True(ResourcePath.Overlaps(string.Empty, "backend/api.cs"));
        Assert.False(ResourcePath.Overlaps("frontend/auth", "frontend/home"));
        Assert.Throws<ArgumentException>(() => ResourcePath.Normalize("frontend/../secrets"));
    }

    [Fact]
    public async Task Concurrent_acquisition_allows_one_authoritative_holder()
    {
        var coordinator = new ResourceLockCoordinator();
        var requests = Enumerable.Range(0, 32)
            .Select(index => Task.Run(() => coordinator.TryAcquire(CreateCommand(
                Guid.NewGuid(),
                $"agent-{index}",
                "frontend/auth/login.cs"))))
            .ToArray();

        var results = await Task.WhenAll(requests);

        Assert.Equal(1, results.Count(item => item.Status == LockAcquisitionStatus.Acquired));
        Assert.Equal(31, results.Count(item => item.Status == LockAcquisitionStatus.Conflict));
        Assert.Single(coordinator.ListActive(ProjectId));
    }

    [Fact]
    public void Repeated_acquisition_by_same_session_is_idempotent_and_renews_lease()
    {
        var clock = new ManualClock(DateTimeOffset.Parse("2026-11-05T22:00:00Z"));
        var coordinator = new ResourceLockCoordinator(clock);
        var request = CreateCommand(Guid.Parse("75e1ad4e-e24f-4389-9824-90dcfd3e47a5"), "codex", "frontend/auth");

        var first = coordinator.TryAcquire(request);
        clock.Advance(TimeSpan.FromSeconds(5));
        var second = coordinator.TryAcquire(request);

        Assert.Equal(LockAcquisitionStatus.Acquired, first.Status);
        Assert.Equal(LockAcquisitionStatus.AlreadyHeld, second.Status);
        Assert.Equal(first.Lock!.Id, second.Lock!.Id);
        Assert.True(second.Lock.ExpiresAt > first.Lock.ExpiresAt);
        Assert.Single(coordinator.Snapshot());
    }

    [Fact]
    public void Expired_lease_is_not_a_conflict_and_cannot_be_renewed_by_old_owner()
    {
        var clock = new ManualClock(DateTimeOffset.Parse("2026-11-05T22:00:00Z"));
        var coordinator = new ResourceLockCoordinator(clock);
        var firstOwner = CreateOwner(Guid.Parse("75e1ad4e-e24f-4389-9824-90dcfd3e47a5"), "codex");
        var secondOwner = CreateOwner(Guid.Parse("fd8b3f6c-d36c-4012-b146-0b8ed1f5caaf"), "claude");
        var first = coordinator.TryAcquire(CreateCommand(firstOwner, "backend/api"));

        clock.Advance(LeasePolicy.Maximum + TimeSpan.FromSeconds(1));
        Assert.False(coordinator.TryRenew(first.Lock!.Id, firstOwner, LeasePolicy.Minimum, out _));
        var second = coordinator.TryAcquire(CreateCommand(secondOwner, "backend/api/controller.cs"));

        Assert.Equal(LockAcquisitionStatus.Acquired, second.Status);
        Assert.Equal(ResourceLockState.Expired, coordinator.Snapshot().Single(item => item.Id == first.Lock.Id).State);
    }

    [Fact]
    public void Only_the_owner_can_renew_or_release_a_lock()
    {
        var coordinator = new ResourceLockCoordinator();
        var owner = CreateOwner(Guid.Parse("75e1ad4e-e24f-4389-9824-90dcfd3e47a5"), "codex");
        var other = CreateOwner(Guid.Parse("fd8b3f6c-d36c-4012-b146-0b8ed1f5caaf"), "claude");
        var acquired = coordinator.TryAcquire(CreateCommand(owner, "docs/architecture.md"));

        Assert.False(coordinator.TryRenew(acquired.Lock!.Id, other, LeasePolicy.Minimum, out _));
        Assert.False(coordinator.TryRelease(acquired.Lock.Id, other, out _));
        Assert.True(coordinator.TryRelease(acquired.Lock.Id, owner, out var released));
        Assert.Equal(ResourceLockState.Released, released!.State);
        Assert.Empty(coordinator.ListActive(ProjectId));
    }

    private static AcquireResourceLockCommand CreateCommand(Guid ownerId, string agentId, string path)
        => CreateCommand(CreateOwner(ownerId, agentId), path);

    private static AcquireResourceLockCommand CreateCommand(LockOwner owner, string path)
        => new(ProjectId, null, ResourceKind.File, path, owner, LeasePolicy.Maximum);

    private static LockOwner CreateOwner(Guid userId, string agentId)
        => new(
            userId,
            Guid.Parse("2b0fbb66-9ee4-48f6-a3a4-e8a347c5e6d0"),
            agentId,
            Guid.Parse("d0c4b9a0-bfac-4a1c-8e25-0bfe6e430a3e"));

    private sealed class ManualClock : IClock
    {
        public ManualClock(DateTimeOffset start) => UtcNow = start;

        public DateTimeOffset UtcNow { get; private set; }

        public void Advance(TimeSpan amount) => UtcNow = UtcNow.Add(amount);
    }
}
