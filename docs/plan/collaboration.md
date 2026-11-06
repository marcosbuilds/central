# Live workspace: same code, different agents, no collisions

> **Core requirement defined by the team:** agents work on the same shared
> project and quickly see one another's changes. Reservations prohibit
> concurrency in the same part/logic. An AI-isolated branch **is not** the main
> experience. An approved stable version is separated from the live editing area
> for operational safety.

## Why “locking a file” alone is not enough

The “create order” logic may be distributed across `api/orders.py`, an SQL table,
a type contract, and a web interface. Two AIs changing different files can break
the same rule. A large file may also contain unrelated functions. Coordination
is therefore needed in **layers of intent**, in addition to files.

## Three coordination layers

1. **Task reservation:** a person/agent owns the delivery defined in planning.
2. **Logical/semantic reservation:** module, service, resource, endpoint, data
   model, external contract, schema, function, or set of responsibilities.
3. **Physical reservation:** files and directories that may be changed, exclusive
   when code analysis is not reliable.

Example: `auth.login` is a logical reservation covering password validation,
session, and authorization contracts. Nobody changes the same points without
requesting a transfer or negotiating a split.

## Source of truth

- A **canonical live workspace** is the source of the files everyone reads.
- The server maintains monotonic `workspace_revision` and a path/hash manifest per revision.
- The synchronization layer transmits **confirmed** changes to others within
  seconds; it does not promise absolute simultaneity on unstable networks.
- Every change has `change_set_id`, human author, agent/session, task,
  reservations, base revision, and hashes.
- The gateway applies the change set **atomically** or rejects the entire batch;
  it records an event and recoverable snapshot.
- Changes under review are **visible and labeled**, but do not appear in the published stable version.

## Required AI protocol

1. `discover`: query project, open tasks, reservations, dependencies, and contracts.
2. `claim`: request task and logic/file reservations, stating intent and estimate.
3. `refresh`: obtain current revision, documentation, and required files.
4. `plan`: declare planned files and logic; Central may expand protected areas through dependencies.
5. `heartbeat`: keep the reservation active while working.
6. `propose_patch`: submit differences and base hashes; the server inspects paths,
   operations, dependencies, and unexpected changes.
7. `apply_patch`: the gateway validates again **at the exact moment** of
   application; in a transaction/exclusion control, it updates the workspace and emits an ordered event.
8. `verify`: run appropriate tests and code analysis; record results.
9. `request_review`: send the change for independent review.
10. `release_claim`: release the reservation and update the map for others; close the session when finished.

**Important:** `claim` alone cannot guarantee that an AI never accesses another
path if it has free disk access. The system must control the adapter's and the
executed environment's write capability.

## Reservation policy

- Exclusive writing in the same logical or physical area; shared reading.
- Reservations cover **affected dependencies**, not only the selected file.
- Dependencies are declared in the project and gradually inferred through
  imports, call graph, API contracts, and ownership map; inference is a
  **heuristic**, never a formal guarantee.
- If a language cannot be analyzed reliably, reserve the entire file (or module for structural changes).
- Central documents and contracts have reinforced reservations and notify owners of dependent modules.
- Task reservation has a human owner, associated agent(s), scope, expiration,
  and heartbeats.
- Deadlock: request multiple resources in a stable order with an atomic request;
  if unavailable, do not hold partial resources indefinitely.
- Expiration: a session without signals enters `suspect`; after a configured
  period, safely cancel writing and supervise lock recovery; do not release in the middle of a patch.
- Manual displacement: leader with reason, notice, audit, and confirmation that no active operation exists.
- A sensitive resource may require one agent at a time even when two agents edit different symbols.

## Conflicts and simultaneous updates

**Scenario 1 — Same logic:** AI A reserved `payments.capture`. AI B tries to
touch that logic: **deny** with owner, current task, and options to request help,
wait, or choose an independent part.

**Scenario 2 — Different files, same API:** AI A changes `/bookings` response.
AI B changes the app consuming `/bookings`. Central detects dependency, blocks a
contract change without agreement, informs AI B, and requires a contract test.

**Scenario 3 — Same file, independent functions:** allow symbol-level concurrency
only when parser/AST and language ownership map can distinguish sections and
validate per-section hashes. Otherwise the entire file is exclusive.

**Scenario 4 — Both read revision 15:** AI A applies a patch and creates revision
16. AI B sends a patch based on revision 15. The gateway compares hashes of
touched sections and dependencies: if still applicable, reconcile and create
revision 17; otherwise return `409 STALE_BASE` and require reload/rewrite. Never
apply blindly from an old base.

**Scenario 5 — Network loss:** the client queues only safe local changes marked
`awaiting synchronization`, without claiming they are in the live workspace.
On reconnect, revalidate reservations, hashes, and revision. If invalid, do not force synchronization.

**Scenario 6 — Rejected change:** the set was visible in the live area but cannot
enter the stable version. Revert selectively by change set and test, evaluating
dependent changes; if other agents built on it, open a recovery task and block
publication until resolved.

**Scenario 7 — Agent changes names/structure without announcing:** the gateway
requires reservation of the old and new directory/module, analyzes references,
invalidates dependent tasks, and requires strengthened review.

## Fundamental risk: shared changes can break the live project

A global editing workspace is inherently more vulnerable to transient failures
than isolated development environments. Reduce risk with:

- small reversible batches; *checkpoint* before each batch;
- fast pre-application tests for critical operations; full tests after application;
- preview and build/execution in an isolated container, never directly on the
  server with real data;
- **always recoverable stable snapshot**; never run production directly from the live tree;
- if an essential test fails, signal and block promotion; under strict rules,
  revert the batch before releasing dependencies;
- **do not promise prevention of 100% of semantic conflicts.** Reservations,
  base validation, and tests reduce known risks; contracts and human review cover gaps.

## Special case: each member's AI is on their own computer

The local desktop app/daemon observes allowed operations, connects to the gateway,
and keeps a synchronized copy. The central source is authoritative. A local copy
may lag; a patch is accepted only after the server revalidates it. SDK/hook
integration is **instrumented**: writing/terminal tools must pass through the
controller or run in a restricted-access workspace. Loose agents in user
directories without a controller cannot receive an exclusivity guarantee.

## Required acceptance test

Run 9 simulated sessions mixing providers, with 4 non-conflicting tasks and 5
overlap attempts. Central must allow independent work, deny all configured
overlaps, reject stale-base patches, show ordered events, recover from connection
loss, and preserve the stable version. Also test that a bypass attempt cannot
publish to the canonical workspace.

---

# 05 — Each member's own AI: connection and streaming

## Idea

Each developer may continue using Codex, Claude Code, or another compatible tool.
Central **does not replace** the model; it adds shared context, reservations,
authorization, observability, and controlled publication.

## Components

- **Member app:** interface, sessions, tasks, and alerts.
- **Local synchronization agent:** authenticates the machine, retrieves plans/
  contracts, watches changes, transmits events, and submits patches.
- **Provider adapter:** translates tool calls/events to Central contracts.
- **Central gateway:** authenticates, checks scope, reserves, controls writing,
  versions, and audit.
- **Event channel:** server sends presence, progress, diff, blocker, and review
  over WebSocket (or SSE for read-only clients).

## Compatibility based on documented APIs

- **Codex:** the SDK helps automate sessions; **Codex App Server** is a richer
  integration option with events, approvals, and control. Do not assume every
  Codex mode can block all external writes without a controlling adapter.
- **Claude Code:** the Python/TypeScript Agent SDK has streaming, permissions,
  and hooks capable of intercepting tool calls; use them to apply rules and
  record events, subject to real installation behavior and versions.
- **Other agents:** versioned adapters require the ability to report activity and
  submit changes through a gateway. If a tool lacks reliable integration, offer
  read-only or manual work, not a false “conflict-free” seal.

## Personal Central token

Create a token per member, project, device, and validity period. The public token
identifier plus secret is shown only once. Store a token hash, not plaintext.
Minimum permissions: `project.read`, `tasks.read`, `claims.create`,
`workspace.read`, `patch.propose`, `patch.apply.claimed`, `tests.run`,
`review.read`. `deploy.production` and administration are never included in a
default AI token.

Rotation, immediate revocation, expiration, rate limiting, and audit are required.
The token is bound to project and user. A removed member loses access even with an
old copy of the token.

## Sessions and events

Session: `session_id`, `member_id`, `provider`, `project_id`, `task_id`,
`agent_version`, `client_version`, `status`, `started_at`, `last_heartbeat_at`,
`resource_claims`, `last_workspace_revision`.

Minimum events:

- `agent.connected`, `agent.disconnected`, `agent.heartbeat`;
- `task.claimed`, `claim.blocked`, `claim.released`;
- `agent.started_work`, `agent.activity`, `agent.waiting`, `agent.completed`, `agent.failed`;
- `patch.proposed`, `patch.denied`, `patch.applied`, `workspace.revision_updated`;
- `test.started`, `test.finished`, `review.requested`, `review.decided`.

**Useful streaming**, rather than capturing private reasoning or keystrokes:
show the current authorized step, task, affected file/contract, operation, and
result. Do not collect *chain of thought*, passwords, confidential prompts, or
complete terminal output by default.

## AI connection process

1. The member signs in to Central and receives project approval.
2. They create a restricted token for their machine and agent, with an expiration date.
3. They install/configure the local adapter/agent; the secret stays in secure device storage.
4. The adapter registers the session and obtains the task/contract manifest.
5. Before acting, the AI queries reservations and proposes a work plan.
6. Central releases the scope; the adapter limits write operations to the scope.
7. Activities and patches stream; confirmed changes enter the shared workspace.
8. A reviewer approves or requests correction; after tests, a stable snapshot is created.

## Real limits and security

- It is not enough to tell an AI in a prompt “do not touch other files”: this is
  an **operational** rule enforced by the gateway and, whenever possible, execution layer.
- An observer-only plugin does not stop the local process from editing files; it
  must control publication and preferably mediate writing.
- Subprocesses and terminals can modify files outside the editor. Run them with
  bounded permissions and validate every difference before synchronization.
- Never copy a provider credential to Central without need; prefer user-managed
  local credentials or authorized enterprise access.
- Limit transmitted content; client files and logs may be confidential. Define
  authorization and contractual transparency for AI use.

## Example Central message to an agent

```json
{
  "status": "denied",
  "reason": "SEMANTIC_RESOURCE_BUSY",
  "resource": "booking.create",
  "current_owner": "session_A",
  "blocked_task": "T-104",
  "available_tasks": ["T-109", "T-112"],
  "suggestion": "Choose an independent task or request an interface agreement from the owner."
}
```

## Performance goals — proposals to test, not evidence

Target experience on a normal network: reservation/activity status reaches other
clients within a few seconds; patch propagation after confirmation is similarly
fast; reconnection restores state without lost/duplicated changes. Exact latency
and scale will be defined and measured through prototypes and tests, not promised now.
