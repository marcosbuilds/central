# Implementation decision — coordination core 2026-11-05

Status: implemented locally; Supabase integration pending a dedicated project
Owner: Central Colaborativa
Scope: resource reservations, leases, fencing, and the first coordination migration

## First vertical-slice contract

The first verifiable increment of the mission is to protect the resource before
writing:

- logical paths are project-relative and normalized for Windows case-insensitive behavior;
- a project reservation conflicts with any descendant; a directory reservation
  conflicts with descendant files and vice versa;
- a reservation identifies the user, device, agent, session, task, and project;
- leases have heartbeat, expiration, and a monotonic fencing token;
- a session may repeat acquisition of the same resource without creating two reservations;
- only the owner may renew or release;
- conflict, expiration, and release preserve the record for audit;
- the in-memory coordinator is only a deterministic adapter for tests/offline and
  is not authority across computers.

## Evidence

| ID | Claim | Source | Class | Result |
| --- | --- | --- | --- | --- |
| E-001 | The current base is WPF/.NET 8 and `CentralStore` is in memory | `README.md`, `docs/ARCHITECTURE.md`, `app/desktop/Central.Desktop/Services/CentralStore.cs` | documentation + code | verified |
| E-002 | The existing architecture already requires TTL claims, base revision, audit, and replacement by a gateway | `docs/ARCHITECTURE.md`, `docs/SERVER-PLAN.md`, `docs/plan/07-collaboration.md` | project contract | verified |
| E-003 | Reservations must prevent semantic overlap and cannot depend on a local variable | mission brief, section 6 | user requirement | adopted |
| E-004 | The first implementation must work without claiming nonexistent external integration | `README.md`, `docs/DESIGN-CONTRACT.md` | project contract | verified |
| E-005 | The current Release build passes without warnings/errors | `dotnet build Central.sln -c Release --no-restore` on 2026-11-05 | executable observation | pass |
| E-006 | The existing suite had 12 passing tests before the increment | `dotnet test Central.sln -c Release --no-restore` on 2026-11-05 | executable observation | pass |
| E-007 | PostgreSQL accepts the complete migration, including DDL, functions, RLS, grants, and Realtime | disposable PostgreSQL 16 Docker instance; `Get-Content db/migrations/202611050001_coordination.sql | docker exec -i ... psql -v ON_ERROR_STOP=1` on 2026-11-05 | local integration observation | pass |
| E-008 | Two members see the project, a parent reservation blocks its child, renewal/release work, and an external user receives `42501` | ephemeral fixtures + `create_organization`, `create_project`, `acquire_resource_lock`, `renew_resource_lock`, and `release_resource_lock` RPCs in PostgreSQL 16 | local security/concurrency observation | pass |

## Decision

Keep .NET 8 as the first integration stack because the WPF base, packaged SDK,
and installer already exist in this environment. Add a dependency-free
`Central.Core` to express domain invariants and a Supabase migration that will
become multi-user authoritative source.

The shared path uses PostgreSQL RPCs with `pg_advisory_xact_lock` per project.
Overlap checking and insertion happen in the same transaction. RLS restricts
reads to the project, and RPCs validate `auth.uid()`, membership, reservation
owner, session, and deadline.

## Adopted external authority

- [Supabase Database Functions](https://supabase.com/docs/guides/database/functions): RPCs are the boundary for transactional operations; `security definer` functions use an empty `search_path`, qualified references, and restricted execution.
- [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security): grants and policies are required together; the migration enables RLS on all exposed tables and revokes the `anon` role.
- [Supabase Realtime](https://supabase.com/docs/guides/realtime/subscribing-to-database-changes): persistent state does not depend on a notification; the next step will use Broadcast/Presence for fast signals while PostgreSQL remains authoritative.
- [Syncthing Config REST API](https://docs.syncthing.net/rest/config): future automation must read and update devices/folders through official APIs and track `restart-required`, without blindly editing another computer's configuration.

## Selected risks

- concurrency/idempotency: parallel test and repeated acquisition;
- data/schema: new migration with no change to the existing database;
- authorization: RLS and negative validations still need execution in a dedicated project;
- external integration: Supabase/Realtime have not yet been executed;
- compatibility: the current desktop continues to use local `CentralStore` until an authenticated client exists.

## Surfaces authorized in this round

- `app/core/**`;
- `tests/app/**` only for reference and tests of the new core;
- `Central.sln`;
- `db/migrations/202611050001_coordination.sql`;
- this record and architecture/README documentation.

Supabase projects, existing data, credentials, PythonAnywhere, and the published
installer were not changed.

## Planned verification

1. Release solution build.
2. Unit and concurrent core tests.
3. SQL validation in a dedicated Supabase project, including RLS between two
   users and RPCs under contention; equivalent syntax and flow have already
   been validated in disposable PostgreSQL 16.
4. Only afterward: authenticated desktop client, Syncthing synchronization, and
   MCP integration.

## Open limitations

- The migration has not yet been applied; Supabase open in the browser contains
  an existing organization with a project that will not be reused.
- There is no desktop authentication, REST/RPC client, configured Syncthing, Git
  worktree, or Codex/Claude adapters yet.
- The local test proves the algorithm invariant, not two-computer concurrency or
  PostgreSQL execution.
