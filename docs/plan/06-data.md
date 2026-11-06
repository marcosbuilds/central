# 08 — Data, APIs, and events: contracts to start implementation

## Main entities (conceptual model)

- `organizations`: company/client and isolation.
- `members`: internal identity; `discord_id` is an external association, not the system primary key.
- `invitations`, `memberships`, `project_memberships`, `roles`, `permissions`, `devices`, `api_tokens`.
- `projects`: objective, state, and configuration.
- `requirements`, `decisions`, `documents`, `document_versions`, `project_architecture_versions`, `project_modules`.
- `tasks`: owner, state, priority, acceptance, module, and dependencies.
- `resource_map`: logical/physical resources and their dependency relationships.
- `claims`: owner, session, project, resources, expiration, state, and reservation version.
- `agent_sessions`: provider, device, token, task, and heartbeat.
- `workspace_revisions`: sequential number per project, hash manifest, origin, and time.
- `change_sets`: intent, base, patch, state, tests, reviewer, impact, and reversal.
- `change_set_files`: path, previous/new hash, type, and affected symbol.
- `reviews`, `review_comments`, `test_runs`, `deployments`, `releases`, `artifacts`, `audit_events`.
- `project_events`: persistent event with `event_id`, `project_seq`, actor, and filtered payload.

## Rules enforced by database/gateway

- Email/Discord name are not authorization IDs; never trust only data sent by the client.
- An exclusive resource cannot be actively reserved by two writers. Enforce it
  with a database transaction and appropriate lock/index or a serializer; do not
  only check and then insert without protection.
- `workspace_revision` grows in project order; event `project_seq` is durable,
  generated in the same transaction or through an outbox.
- A change set can be applied only with an authorized session, valid reservation,
  allowed paths, and a compatible base.
- Idempotent application: the same operation key produces the same recorded result.
- A release points to a specific revision and lists approved change sets and valid tests.
- Review is done by a different person from the author when required; approval is invalidated if the diff changes.

## Main endpoints (design, subject to refinement)

| Method | Route | Action |
|---|---|---|
| POST | `/v1/auth/discord/start` | Start Discord login (secure flow) |
| GET | `/v1/auth/discord/callback` | Complete authentication |
| POST | `/v1/invitations` | Create invitation, admin |
| POST | `/v1/members/{id}/approve` | Approve member |
| GET | `/v1/projects` | List accessible projects |
| POST | `/v1/projects` | Create project |
| POST | `/v1/projects/{id}/imports` | Import validated ZIP |
| GET | `/v1/projects/{id}/plan` | Planning and architecture |
| GET | `/v1/projects/{id}/tasks` | Tasks and dependencies |
| GET | `/v1/projects/{id}/workspace/manifest` | Tree and hashes |
| GET | `/v1/projects/{id}/workspace/files` | File by validated path |
| POST | `/v1/projects/{id}/claims` | Request atomic reservation |
| POST | `/v1/claims/{id}/heartbeat` | Renew presence/reservation |
| DELETE | `/v1/claims/{id}` | Release reservation |
| POST | `/v1/projects/{id}/patches/validate` | Pre-check change set |
| POST | `/v1/projects/{id}/patches/apply` | Apply canonical batch |
| POST | `/v1/projects/{id}/reviews` | Request review |
| POST | `/v1/reviews/{id}/decision` | Approve, reject, or request correction |
| POST | `/v1/projects/{id}/test-runs` | Run allowed tests |
| POST | `/v1/projects/{id}/releases` | Create approved stable snapshot |
| POST | `/v1/projects/{id}/deployments` | Deploy with specific authorization |
| GET | `/v1/projects/{id}/events?after_seq=N` | Recover missed events |
| WS | `/v1/projects/{id}/stream` | Authenticated ordered WebSocket |
| POST | `/v1/me/tokens` | Create least-privilege token |
| DELETE | `/v1/me/tokens/{id}` | Revoke token |

Mutation endpoints require project authorization, input validation, idempotency
when duplication is risky, and auditable logs. **Large patches** may be sent by
an expiring signed temporary object instead of an unlimited API payload.

## Minimum reservation-request payload

```json
{
  "project_id": "P-001",
  "task_id": "T-104",
  "session_id": "S-AI-1",
  "semantic_resources": ["booking.create", "booking.availability"],
  "write_paths": ["services/api/src/booking/**"],
  "read_dependencies": ["packages/contracts/booking.schema.json"],
  "intent": "Create an appointment without duplicate times",
  "lease_seconds": 120,
  "idempotency_key": "claim-uuid"
}
```

## Patch-envelope example

```json
{
  "project_id": "P-001",
  "task_id": "T-104",
  "agent_session_id": "S-AI-1",
  "claim_id": "C-040",
  "base_revision": 127,
  "idempotency_key": "patch-uuid",
  "changes": [
    {
      "path": "services/api/src/booking/service.py",
      "base_sha256": "sha256-of-original-content",
      "operation": "modify",
      "patch_ref": "restricted-patch-object-42"
    }
  ]
}
```

The `patch_ref` content must have size limits, security checks, and retention.
The gateway calculates new hashes, scope checks, and dependency checks before applying.

## Event model

Every important event carries `event_id`, `project_id`, `project_seq`,
`occurred_at`, `actor_type`, `actor_id`, optional `session_id`, `task_id`,
`workspace_revision`, `type`, and a limited `payload`. Do not include unnecessary
sensitive content or credentials.

**Display semantics:** `agent.activity` is an execution observation;
`patch.applied` confirms that a change occurred in the central code. Never show
“file already updated” based only on an AI text token.

## Version compatibility

API version `/v1`, stable event type, and `schema_version` inside envelopes;
consumers ignore unknown fields and explicitly reject incompatible changes.
Important contract changes require migration and tests.
