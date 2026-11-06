# 15 — Technical protocol: changes, conversations, contracts, and review

**State:** conceptual contracts for future implementation. The goal is not to
promise a working API; routes and examples are engineering proposals to validate.

## A. Resource model

- `projects`: id, slug, aliases, owner, state `OPEN|CLOSING|CLOSED`,
  `fencing_epoch`, repositories, workspace_revision.
- `memberships`: member, project, roles/scopes, validity.
- `agent_sessions`: agent, human owner, provider, connection_id, active_project_id,
  permissions, last_seen, adapter_version.
- `tasks`: owner, description, criteria, priority, dependencies, logical resources, state.
- `resource_claims`: project, logic/file, task, session, exclusivity, epoch,
  expiration, heartbeat.
- `change_sets`: revision, base_revision, hash, patch, claimed_resources, result, CI, writer, time.
- `snapshots`: workspace_revision, manifest, checksums, recoverable storage.
- `threads`: project, context, associated resource, visibility, state, participants.
- `messages`: thread, author, sponsoring member, agent, type, payload, timestamp, restricted attachments.
- `integration_requests`: consumer, provider, task_ids, status, contract_id, desired deadline, blocker.
- `api_contracts`: id, version, OpenAPI/JSON Schema source, owner, consumers,
  agreed_hash, status, checks.
- `delivery_candidates`: base_master, selected_change_sets, exact hash, diff, risk, status, owner.
- `evidence_runs`: CI job, runner, commands, environment, artifact hashes,
  filtered logs, status.
- `reviews`: reviewer member/agent, delegated scope, candidate hash, decision,
  reason, evidence_ids, signed event.
- `releases`, `deployments`, `audit_events`: approved versions, deployment, and non-rewritable trail.

Relational database with referential integrity (for example PostgreSQL),
immutable objects for snapshots/diffs, and an event queue to distribute changes.
Never store tokens in plaintext.

## B. Commands and authentication (pseudo-routes)

```text
GET    /v1/projects                         # authorized users only
POST   /v1/agents/sessions                  # link provider and member
POST   /v1/agents/sessions/{id}/select      # select project by ID after search
GET    /v1/projects/{id}/manifest           # requirements, contracts, revision
POST   /v1/projects/{id}/claims             # reserve logical resource
POST   /v1/projects/{id}/patches/propose    # submit diff, base + hashes
POST   /v1/projects/{id}/patches/{id}/apply # gateway validates and confirms
GET    /v1/projects/{id}/threads
POST   /v1/projects/{id}/threads
POST   /v1/projects/{id}/threads/{id}/messages
POST   /v1/projects/{id}/integrations/requests
POST   /v1/projects/{id}/contracts/{id}/versions
POST   /v1/projects/{id}/deliveries
POST   /v1/projects/{id}/deliveries/{id}/evidence
POST   /v1/projects/{id}/deliveries/{id}/reviews
POST   /v1/projects/{id}/deliveries/{id}/integrate
POST   /v1/projects/{id}/close                 # dedicated role
POST   /v1/projects/{id}/reopen                # dedicated role
GET    /v1/projects/{id}/events                # authorized WebSocket/SSE
```

**Transactional rules:** every write command checks project open state,
membership, scope, epoch, resource, hash, and base_revision; responses include
event_id/idempotency_key. Patch confirmation and revision increase must be
atomic. Events are *at-least-once* with sequences; clients deduplicate. Repeated
operations with the same key do not create duplicate changes.

## C. Event envelope

```json
{
  "event_id": "evt_000123",
  "project_id": "seloryn",
  "project_seq": 203,
  "type": "integration.requested",
  "actor": {"member_id": "member_A", "agent_session_id": "session_codex_A"},
  "refs": {"task_id": "T-17", "contract_id": "api.registration.v1", "thread_id": "thread_45"},
  "payload": {"summary": "Frontend requests registration contract"},
  "visibility": "project_members",
  "occurred_at": "2026-11-03T12:00:00Z"
}
```

Important transitions: `workspace.patch_applied`, `task.blocked`,
`agent.mentioned`, `integration.requested`, `contract.proposed`,
`contract.agreed`, `contract.verified`, `delivery.created`,
`delivery.evidence_added`, `delivery.reviewed`, `delivery.integrated`,
`project.closed`, `project.reopened`.

## D. Approval-evaluation policy

```text
can_approve(candidate, reviewer, evidence):
    require candidate.frozen_hash == evidence.reviewed_hash
    require project.state == OPEN
    require no_open_blocking_comments(candidate)
    require all_required_CI_checks_pass(candidate.frozen_hash)
    require independent(reviewer, candidate.author)
    require reviewer.is_authorized_for(project, risk)
    require evidence.reproducible_and_authenticated
    if candidate.risk == HIGH: require human_approval_from_distinct_member
    return APPROVABLE
```

Actual execution must use backend transactions and implemented security policies,
not only this pseudologic. For GitHub permissions, respect external branch rules,
which may require specific people and CI.

## E. Minimum guarantees

1. Never apply a change to a closed project, even with a previously valid token.
2. Reject changes when the project epoch has changed (revocation/closing).
3. Do not merge two patches with a known semantic conflict; record block and resolution.
4. Never mark a route ready/tested merely because an AI described it.
5. Bind approval to the exact reviewed content, evidence, and real/delegated identity.
6. Never automatically run production from a simple workspace edit.
7. Do not require an offline session to answer mentions; notification waits or escalates.
8. An AI reads only authorized projects, not all projects from all clients indiscriminately.
