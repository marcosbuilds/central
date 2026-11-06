# Central Colaborativa — Windows desktop application

Implementation of Central Colaborativa for Windows, built with C# and .NET 8
using WPF. The visual shell still uses local fixtures for areas that are not
connected yet, while the dedicated folder can already synchronize files between
computers through Syncthing and receive state/events through Supabase.

This repository is now a monorepo: the Peace Discord bot lives in
[`bot`](bot), with tests in [`tests/peace`](tests/peace). The Peace→Central
release contract is documented in
[`docs/INTEGRATION-PEACE-CENTRAL.md`](docs/INTEGRATION-PEACE-CENTRAL.md), but
code exchange is not yet an implemented capability.

## Delivered so far

- Native desktop shell with navigation for Home, Projects, and the selected project; visual settings are available from the profile gear.
- Catalog with search by name, identifier, or module.
- Project details with overview, planning, manual local Pulse, browsable workspace, discussions, deliveries, quality, releases, and history.
- Coherent simulations for semantic reservations, base-reviewed patches, ordered events, local references, local commits/tags/releases, delivery candidates, evidence, local approval, and closing/reopening.
- Closed state blocks writes, reservations, Pulse, local versioning, approval, integration, and deployment at the local domain layer.
- Project catalog with its own vector mark, functional Apple/Segoe title, editorial Seloryn subtitles, priority tier, and responsive reading.
- Technical usage dashboard prepared for duration, tokens, and requests over 1/7/31 days, retaining `N/D` when the gateway provides no measurements.
- Home starts with no project selected: Central does not guess the focus; the catalog resolves the identity before opening a workbench.
- xUnit suite with twelve domain and behavior tests covering the main invariants, semantic selection, and Pulse/workspace flows.
- `Central.Core` with Windows resource normalization, parent/child reservations, leases, heartbeat, expiration, fencing tokens, and a race test across 32 sessions.
- First versioned Supabase migration in `db/migrations/202611050001_coordination.sql`, with RLS, coordination tables, and transactional RPCs for acquiring, renewing, and releasing reservations; it was applied to the dedicated project `ydouynbssldpjhlnawtm`.
- Minimal WSGI gateway published at `https://marcosbuilds.pythonanywhere.com`, with `/healthz` and `/v1/capabilities` for smoke testing; the publication stores no keys and does not replace Supabase.
- The desktop runs an automatic `/healthz` smoke test on startup and accepts `CENTRAL_GATEWAY_URL` to point an installation at another gateway without recompiling.
- Self-contained x64 publishing and a Windows Inno Setup installer.
- Opt-in real synchronization: each installation authenticates with Supabase, registers its Device ID, configures a local Syncthing folder, and tracks peers, state, heartbeat, and conflicts.
- Private Supabase Realtime control streaming, with `phx_join` confirmation, session renewal, backoff, and persistent replay after reconnect. The local cursor is only a checkpoint; PostgreSQL remains the source of truth.
- Migration `db/migrations/202611060002_sync_stream.sql` was applied and verified in the dedicated project `ydouynbssldpjhlnawtm`; peers are filtered by project and sensitive writes go through authenticated RPCs.
- Empty state is also validated through the UI Automation tree: Home does not announce fictional scale or log headers without rows; Prove reflows actions before content is lost at compact widths.

## Repository tree

```text
app/       Central desktop and shared core
bot/       Peace Discord bot
db/        Supabase migrations
ops/       gateway, installer, and scripts
tests/     Central and Peace tests
assets/    versioned bot images
docs/      architecture, decisions, integration, and plan
data/      local markers; real data stays outside Git
```

## Honest phase boundary

There is still no connection to Discord, Codex, Claude, Git, CI/CD, or deploy.
Pulse, tags, releases, commits, and the visual catalog remain local fixtures;
they must not be confused with the shared-folder data plane. PythonAnywhere is
health-only in this phase: real streaming uses Supabase Realtime/WebSocket and
bytes use Syncthing. A physical proof between two PCs still needs to be
observed before it can be declared complete.

## Run from source

The SDK is in `tools/dotnet` to keep the environment organized on the D: drive.
In PowerShell:

```powershell
$dotnet = 'D:\projetos\Central\tools\dotnet\dotnet.exe'
& $dotnet restore 'D:\projetos\Central\Central.sln'
& $dotnet build 'D:\projetos\Central\Central.sln' -c Debug --no-restore
& $dotnet run --project 'D:\projetos\Central\app\desktop\Central.Desktop\Central.Desktop.csproj' -c Debug --no-restore
```

## Tests

```powershell
& 'D:\projetos\Central\tools\dotnet\dotnet.exe' test 'D:\projetos\Central\Central.sln' -c Debug --no-restore
```

## Packaging

The final installer is written to
`artifacts\installer\Central-Colaborativa-Setup-0.2.0.exe`. The reproducible
flow is in `ops\scripts\Build-Central.ps1`, and the self-contained publish is in
`artifacts\publish`. Infrastructure records are in
[docs/DEPLOYMENT-2026-11-05.md](docs/DEPLOYMENT-2026-11-05.md).

## Decisions and next step

- The current visual contract is in [docs/DESIGN-DECISIONS-2026-11-04.md](docs/DESIGN-DECISIONS-2026-11-04.md).
- Future planning for the Python gateway, Claude/Codex adapters, and per-user keys is in [docs/SERVER-PLAN.md](docs/SERVER-PLAN.md). The currently published component is in `ops/gateway/` and deliberately exposes only health/capabilities; it is not a file broker and does not replace Supabase.

## Planning source

The original planning material is preserved as evidence in `docs/plan`. The
visual contract and the decision addendum may supersede the navigation
interpretation when a documented counterexample shows that the original
hypothesis would make someone lose context; domain, security, and future
integration boundaries remain normative. Every such change is recorded in
`docs/DESIGN-DECISIONS-2026-11-04.md`.
