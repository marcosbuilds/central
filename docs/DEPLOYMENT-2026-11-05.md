# Deployment and smoke-test record

Date: 2026-11-05
Scope: public deployment boundaries and reproducible smoke checks

## Database control plane

A dedicated Supabase project was provisioned for the coordination and
synchronization migrations. Public documentation intentionally omits tenant
names, project references, URLs, account names, and dashboard details.

The committed migrations are:

- `db/migrations/202611050001_coordination.sql`
- `db/migrations/202611060002_sync_stream.sql`

The recorded verification checked that coordination tables use row-level
security and that sensitive coordination functions require an authenticated
session. No credentials or production data belong in the schema or in this
record.

## Availability gateway

The PythonAnywhere component is a minimal availability gateway. Its public
contract is limited to health and capabilities endpoints; it is not a file
broker, Syncthing disk, authentication broker, or authoritative data source.

Deployment-specific account names, WSGI paths, environment values, and live
URLs are intentionally kept outside the public repository. The gateway must
receive no database password, service-role key, bot token, or provider key.

## Package for computers

The Windows package is self-contained x64 and remains offline-first. The
desktop contains the authenticated REST/Realtime client, replay checkpoint,
and bundled Syncthing integration described by the implementation documents.
Creating users, organizations, or projects requires an authenticated session;
no user or production data is created by a migration alone.

The second physical computer is outside the repository's control. A package may
be installed there, but a two-computer test is not complete until both devices
are observed and the evidence is recorded without private identifiers.

## Verification

- Release build and test commands are defined in `docs/BUILD.md` and the CI
  workflow.
- The gateway health and capability smoke checks are repeatable against the
  deployment chosen by the operator.
- Migration verification must cover row-level security, authenticated RPCs,
  Realtime publication, and project-scoped filtering.
- Physical synchronization requires two Device IDs, heartbeats, equal test
  file hashes, reconnect evidence, and visible conflict handling. Do not report
  this as complete from a server health check alone.
