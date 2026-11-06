# Infrastructure delivery — Central Colaborativa

Date: 2026-11-05
Scope: dedicated provisioning and remote smoke test

## Supabase

- Organization: `Seloryn Collective FREE`
- Project: `Central Colaborativa`
- Project ref: `ydouynbssldpjhlnawtm`
- Public project URL: `https://ydouynbssldpjhlnawtm.supabase.co`
- Observed state after provisioning: `Healthy`
- Compute: `Nano`
- Region shown in the dashboard: `Canada (Central)` / `ca-central-1`
- Applied migrations: `db/migrations/202611050001_coordination.sql` and
  `db/migrations/202611060002_sync_stream.sql`
- Second application result: `Success. No rows returned`

### Verification performed in the real project

The verification query returned 19 rows: all 14 coordination tables have RLS
enabled (`true`), and the five coordination functions are denied to `anon` and
granted to `authenticated` (`false/true`).

After the second application, a query in the real project confirmed the
`register_device`, `get_project_devices`, `heartbeat_device`,
`upsert_sync_state`, `append_project_event`, and `ensure_sync_folder` RPCs, the
private `realtime.messages` policy, and `project_events`/`sync_states` in the
`supabase_realtime` publication.

No organization, project, user, password, service-role key, or production data
was created inside the schema. Creating an organization or project requires a
session authenticated by the client itself.

## PythonAnywhere

- Account: `MarcosBuilds`
- Web app: `https://marcosbuilds.pythonanywhere.com`
- Python: `3.12`
- WSGI: `/var/www/marcosbuilds_pythonanywhere_com_wsgi.py`
- Uploaded code: `ops/gateway/central_gateway.py`
- Endpoint verified after the 0.2.0 publish: `/healthz` → `status: ok`,
  `deployment: pythonanywhere`, `version: 0.2.0`
- Endpoint verified: `/v1/capabilities` → only `health` available

The gateway received no password, service-role key, or publishable key. Optional
variables are read from the environment and exposed only as configuration
booleans. PythonAnywhere is an availability gateway, not a Syncthing disk or an
authoritative data source.

## Package for computers

The Windows installer is self-contained x64 and remains local/offline-first.
This version's desktop contains in-memory password login, an authenticated REST/
Realtime client, a replay checkpoint, and bundled Syncthing. Creating a user,
organization, or project still requires an authenticated session; no user or
production data was created automatically by the migration.

The second physical computer is not under this session's control. The package
can be installed there, but the test will not be declared complete until the
execution is observed on that device.

## Verification

- `dotnet test Central.sln -c Debug --no-restore`: 30 passed, 0 failed.
- `dotnet build Central.sln -c Debug --no-restore`: passed, 0 errors and 0 warnings.
- The desktop client now queries only `/healthz` on startup; client health unit
  tests cover success, HTTP errors, and an invalid URL.
- Release packaging completed through `ops/scripts/Build-Central.ps1`; the
  installer `artifacts/installer/Central-Colaborativa-Setup-0.2.0.exe` was
  installed and uninstalled in a temporary directory, with `Central.exe` and
  `syncthing.exe` present and exit codes of 0.
- Local Python test: not run; Python is not installed on this Windows machine.
- Remote PythonAnywhere smoke test: passed through an HTTPS browser.
