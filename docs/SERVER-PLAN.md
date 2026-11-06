# Python server plan — Central streaming gateway

Status: planning; no real connection is activated by Phase 1 desktop
Date: 2026-11-04
Objective: replace the in-memory `CentralStore` with an auditable gateway,
ordered streaming, and future Claude/Codex integration

This plan turns the requirements from documentation 1.1 and the redesign into
implementable contracts. It does not authorize adding keys, external calls, or
invented telemetry to the current interface.

## Principles and limits

1. The server is the source of observable events; the UI never infers
   productivity, presence, or private reasoning.
2. Each event has an identity, sequence, origin, timestamp, availability state,
   and project/task reference.
3. The client can disconnect and resume from `last_seq`; reconnection does not
   duplicate events.
4. Token usage is shown only when the provider returns measured counts. If there
   is no usage data, the value is `N/D`.
5. API keys are per user and provider, but are never returned to the desktop or
   written to logs, events, or error messages.
6. MCP is a tools/resources boundary. Claude/Codex integration must go through
   official adapters and retain a fallback path to the provider's official API
   when MCP is not the appropriate transport.

## Proposed architecture

```text
Windows Central
   │ HTTPS + SSE (events) / WebSocket (optional control)
   ▼
FastAPI gateway
   ├── AuthN/AuthZ + tenant/project policy
   ├── Run service + idempotency + cancellation
   ├── Provider adapters
   │     ├── Claude adapter (official API or MCP server)
   │     └── Codex/OpenAI adapter (official API or MCP server)
   ├── Event normalizer + redaction + outbox
   ├── Stream broker (Redis Streams or NATS, when scale requires it)
   └── Audit/usage service
        ├── PostgreSQL: state, claims, events, and audit
        └── Secret store/KMS: encrypted per-user keys
```

### Initial stack

- Python 3.12+, FastAPI, Uvicorn, AnyIO, and Pydantic v2;
- PostgreSQL for transactional state, `workspace_revision`, claims, outbox, and audit;
- Redis Streams for the first distributed deployment; NATS JetStream is an
  alternative when volume and consumer isolation justify it;
- Alembic for migrations, `httpx` for HTTP adapters, an official SDK when one
  exists, and an MCP client isolated by process/session;
- OpenTelemetry for technical metrics, with redaction before export;
- pytest, pytest-asyncio, Hypothesis, and event contract tests.

Redis/NATS are not prerequisites for the first vertical slice. The gateway can
start with a PostgreSQL outbox and a single worker while keeping the same stream
interface.

## Identity, API keys, and authorization

### User and session

- The desktop authenticates the user through OIDC/device flow or an explicitly
  marked local development session.
- The gateway issues a short-lived access token with `user_id`, `tenant_id`, and
  scopes; the refresh token stays outside events.
- Every operation receives an explicit `project_id`. Never select a project by name alone.
- Policy checks member, role, project state, task, resource, and action before
  creating a claim, run, delivery, or publication.

### Provider keys

- `provider_credentials` stores `user_id`, `provider`, `key_version`, scopes,
  revocation state, and metadata; the encrypted secret lives in KMS/Secret
  Manager or envelope encryption with a master key outside the database.
- In development, use a documented local secret store; never use a versioned
  `.env`, `appsettings`, fixture JSON, or clipboard as permanent storage.
- The API accepts `POST /v1/me/provider-keys` only from the authenticated user;
  it stores the encrypted key and returns only a masked fingerprint, provider,
  date, and state.
- The worker decrypts the key only when the call is made, in memory, and passes
  it to an adapter. The key must never appear in an exception, trace, prompt, MCP
  payload, or `request_log`.
- Rotation/revocation is idempotent. The previous version is no longer accepted;
  in-progress jobs finish as `cancelled` or `provider_error` without retrying
  with a revoked secret.
- A user may use a project service credential in the future, but that is a
  separate decision and must not be inferred from a personal key.

## Streaming contract

Each normalized event has a shape equivalent to:

```json
{
  "event_id": "evt_01J...",
  "request_id": "req_01J...",
  "seq": 42,
  "tenant_id": "ten_...",
  "project_id": "prj_seloryn",
  "run_id": "run_...",
  "session_id": "ses_...",
  "type": "run.delta",
  "provider": "claude",
  "model": "provider-model-id",
  "created_at": "2026-11-04T20:15:00Z",
  "availability": "connected",
  "payload": {"text_delta": "..."},
  "redaction": {"secrets_removed": true}
}
```

Minimum types: `run.started`, `run.delta`, `run.tool_call`, `run.tool_result`,
`run.usage`, `run.completed`, `run.cancelled`, `run.failed`,
`connection.heartbeat`, and `audit.decision`. `run.usage` carries
`input_tokens`, `output_tokens`, `total_tokens`, and the measurement source; it
does not estimate tokens.

### Delivery and resumption

- `GET /v1/runs/{run_id}/events` uses SSE and accepts
  `Last-Event-ID`/`last_seq`.
- Each stream keeps a monotonic sequence per `run_id`; the database/outbox
  guarantees persistence before publication.
- The client confirms only local reading; the server does not delete the event
  until retention/audit policy allows it.
- Repetitions are deduplicated by `event_id`; the client applies each event once
  and updates `last_seq` monotonically.
- Heartbeat is not agent activity. Disconnection, delay, `stale`, and
  reconnection appear as availability state.
- Backpressure: per-session buffer limit, coalescing only consecutive `run.delta`
  events, and never state, usage, error, or decision changes.
- Cancellation propagates to the adapter and records who cancelled it and why.

## First vertical-slice endpoints

| Method | Route | Contract |
|---|---|---|
| `GET` | `/v1/projects` | catalog with ID, logo, status, revision, and permission |
| `GET` | `/v1/projects/{project_id}` | context, task, claims, and next gate |
| `POST` | `/v1/runs` | creates an idempotent run; receives project, task, provider/model, and allowed prompt |
| `GET` | `/v1/runs/{run_id}` | state snapshot, origin, and `last_seq` |
| `GET` | `/v1/runs/{run_id}/events` | resumable, redacted, ordered SSE |
| `POST` | `/v1/runs/{run_id}/cancel` | authorized and audited cancellation |
| `GET` | `/v1/usage?range=1d\|7d\|31d` | team/project aggregates using measured usage only |
| `GET` | `/v1/request-logs` | masked logs with source, freshness, model, transport, and status |
| `POST/DELETE` | `/v1/me/provider-keys/{provider}` | save/revoke the user's credential without exposing the secret |

## Minimum data model

- `users`, `tenants`, `project_members`, `projects`, `tasks`, and `claims` with
  TTL and fencing;
- `runs`, `run_events` with unique `(run_id, seq)` and unique `event_id`;
- `provider_credentials` with encrypted envelope, `key_version`, fingerprint,
  and revocation timestamp;
- `outbox_events` with attempts, `published_at`, and redacted error;
- `request_logs` with `request_id`, masked principal, provider/model, transport,
  status, measured TTFT, usage, and freshness;
- append-only `audit_log` for authorization, secret access, cancellation,
  approval, integration, and publication.

Indexes and retention must be defined against real volume. Do not declare an SLA,
stale threshold, or retention duration before measuring and deciding with the
operations owner.

## Observability and operational security

- end-to-end correlation ID (`request_id`) without the full prompt by default;
- structured allowlist logs with redaction of keys, tokens, and sensitive content;
- metrics: time to first token, duration, dropped events, reconnections,
  duplicates, provider errors, and returned usage;
- alerts for queue depth, delayed outbox, KMS failures, provider rate limits, and
  sequence divergence;
- authorization-by-project, cross-user isolation, event replay, key rotation,
  cancellation, reconnection, and nine-session load tests;
- size and time limits, per-user/provider rate limits, and a provider circuit breaker;
- CSP/HTTPS, secrets outside the desktop, pinned dependencies, and an SBOM in packaging.

## Delivery phases

1. **Contract and fake gateway**: schemas, redaction, sequence, SSE, and test
   client; no external calls.
2. **Persistence**: PostgreSQL, outbox, claims, audit, project authorization,
   and migrations.
3. **Credentials**: secret store, per-user keys, rotation/revocation, and
   non-leakage tests.
4. **Claude adapter**: official path chosen after validating API/MCP
   availability, usage, tool calls, and cancellation.
5. **Codex/OpenAI adapter**: same normalized contract, without exposing provider
   differences to the UI.
6. **Desktop streaming**: replace fixtures with an SSE/WebSocket client, keep
   `N/D` offline, and support resumption.
7. **Operations**: broker, workers, tracing, load test, gradual rollout, and rollback plan.

## Server acceptance criteria

- a run produces ordered, resumable events without duplication;
- two users cannot read, cancel, or use each other's credentials;
- a revoked key is not used in new calls and does not appear in logs/events;
- displayed tokens are returned by the provider, with source and freshness;
- provider failure results in explicit `provider_error`/`stale` state, never green success;
- nine concurrent sessions preserve claims, `workspace_revision`, sequence, and audit;
- contract tests prove that the desktop can render the same model with a fake
  gateway and a real provider without changing the UI.
