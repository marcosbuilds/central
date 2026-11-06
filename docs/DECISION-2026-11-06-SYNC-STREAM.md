# Implementation decision — real synchronization and streaming 2026-11-06

Status: accepted for the first operational vertical slice
Owner: Central user / Central Colaborativa
Scope: dedicated test folder, Supabase coordination, Realtime events, local
Syncthing integration, and reconnection

## Desired observable result

Two computers can participate in the same authenticated project. Each
installation registers a device, keeps a dedicated local folder, and observes
the summarized synchronization state. File contents travel through Syncthing;
Supabase stores identity, authorization, state, locks, and events. Central
receives real-time notices but rereads persistent events after a disconnect.

## Invariants

- `project_id`, user, device, and session are explicit identities; there is no
  pairing by IP address or machine name.
- The shared folder is a dedicated root outside the source code and receives
  ignore rules for secrets and artifacts.
- PostgreSQL is the authoritative source for events and state; Realtime is a
  low-latency delivery mechanism and may lose messages.
- The event cursor is monotonic. Duplicates and old sequences do not change the
  UI; gaps trigger recovery through a persistent query.
- Central does not store a service-role key, database password, or provider credentials.
- A file conflict is not success: `sync-conflict` files and error states remain visible.
- Pausing integration does not delete files, unpair devices, or propagate a rollback deletion.

## Evidence and reviews

- E-001: `CentralStore` and the current UI are local;
  `app/desktop/Central.Desktop/Services/CentralStore.cs` and `docs/ARCHITECTURE.md`.
- E-002: the published gateway exposes only `/healthz` and capabilities;
  `ops/gateway/central_gateway.py`.
- E-003: the initial migration already contains `devices`, `sync_states`, and
  `project_events`; `db/migrations/202611050001_coordination.sql`.
- E-004: independent read-only adversarial passes were performed over the
  current worktree; those reports are separate review/role simulation and do
  not replace two-PC integration testing.
- E-005: official Syncthing documentation confirms the configuration REST API,
  status, events, and restart query; `https://docs.syncthing.net/rest/config` and
  `https://docs.syncthing.net/dev/rest.html`.
- E-006: Supabase Realtime documentation requires rereading the database after
  reconnection; the channel is not authoritative.
- E-007: migration `202611060002` was executed in the dedicated test project,
  and a follow-up query confirmed the RPCs, private policy, and `sync_states`
  publication. Tenant and project identifiers are intentionally omitted here.

## Decision

1. Syncthing is the data plane. Central initializes/observes a local instance
   only when the bundled executable is available and never shares the entire repository.
2. Supabase is the control plane. The additive migration already applied adds
   idempotent device registration, heartbeat, authenticated `sync_states`
   updates, idempotent events, a project folder, project-scoped device filtering,
   and private-channel authorization.
3. The desktop uses REST for snapshot/replay and Realtime WebSocket for
   notification. Reconnection always fetches `project_events` after `last_seq`.
4. The PythonAnywhere gateway remains health-only in this phase. There is no
   continuous SSE on the free plan.
5. Synchronization mode is explicit in configuration. The first test folder may
   be `send-only`/`receive-only`; `send-receive` should be used only after the
   test file's copy and hash have been proven.

## Rejected or deferred alternatives

- Supabase Storage as a local folder: it does not provide appropriate P2P,
  offline editing, or conflict-resolution semantics.
- Continuous SSE on free PythonAnywhere: a worker and web-request timeout are
  incompatible with a durable connection.
- Copying files through the gateway: this would increase loss risk, turn the
  gateway into storage, and not solve offline editing.
- Declaring the second PC present through `/healthz`: server health does not
  prove identity, pairing, or equal hashes.

## Minimum verification

- deterministic tests for cursor, deduplication, JSON contract, RPC, and status parser;
- complete .NET build and suite;
- migration applied in the dedicated project and validated with RLS, RPCs, and Realtime;
- local Syncthing in a disposable folder: file A→B, equal hash, change B→A,
  pause/reconnect, and controlled conflict;
- physical proof: two Device IDs, two heartbeats, identical file/nonce and
  SHA-256 on both PCs, and `insync` state on both sides.

## Residual risk

The free Supabase plan is not a backup; Syncthing does not replace a backup.
Propagated deletions and conflicts remain operations that require testing in a
disposable folder. The two-PC proof will be declared only after the evidence
above is observed on both devices.
