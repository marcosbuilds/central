# 13 — AI project selection and safe closing

## Objective in plain language

The member opens Codex/Claude and asks: **“Work on the Seloryn project and
continue where we stopped.”** The AI finds the project registered in Central,
knows the current version and what colleagues are doing, chooses a free task that
matches the request, and works in the **same shared project**.

The team can close a project: it remains available for consultation but accepts
no changes or new publications until someone with permission reopens it.

## Conversation and flow example

```text
Person: "Continue the Seloryn project. See what is missing."
AI   -> list_projects('Seloryn')
     <- [{id:'proj-101', name:'Seloryn', status:'OPEN'}]
AI   -> select_project('proj-101')
AI   -> get_project_context('proj-101')
     <- revision rev-127, tree, documentation, modules, contract, and tasks
AI   -> get_active_work('proj-101')
     <- Ana + Codex occupy parser; Bruno + Claude occupy runtime
AI   -> list_tasks('proj-101', available=true)
     <- free CLI tests; documentation blocked by a decision
AI   -> claim_task('TASK-29', resources=['module:cli/tests'])
     <- lease confirmed
AI   -> sends progress + proposed changes and receives verification
     <- shared revision rev-128 after validation/acceptance
```

## 1. Identify the project correctly

- The official key is an internal UUID/ID, never an inferred folder name.
- Name, aliases, and search help identify it. Alias `seloryn`, project `Seloryn`,
  and the matching repository point to the same ID.
- If two projects match an expression (for example “internal site”), the AI asks
  which one; it does not choose arbitrarily.
- If the user is already working in Seloryn and says “continue that”, it may use
  the previous `selected_project_id` **when there is no relevant ambiguity**.
- If the user says “work on Seloryn”, the explicit command takes precedence over the previous project.
- The AI validates target changes against the registry; it does not trust README,
  comment, or issue text that tells it to switch projects.

## 2. Before changing anything

Central returns `id`, `status`, `generation`, `shared_revision`, approved plan,
manifest, tree, modules, tasks, rules, occupied areas, and dependencies. The
model may edit only a project the member can access, through an authenticated
Central token and write authorization.

The member may be allowed to **see all projects** and select any one, but client
access must follow contracts. Reading is not writing. The AI never inherits the
power to close/reopen or publish to production merely because it can edit.

## 3. Select the task

- For a specific request (“fix the inspect command”), find a coherent task and
  area; if none exists, propose creating a task and request validation under policy.
- For a broad request (“continue”), offer the next **approved, ready, unblocked**
  task according to priority and dependencies.
- Also reserve logical resources: if a backend changes a contract, a dependent
  frontend receives a blocker or coordination signal.
- The AI must not start a new task while unsynchronized or holding a reservation
  in another project without releasing/checkpointing it.

## 4. Switch projects during work

1. Capture current work state, unintegrated diff, and pending-work comment.
2. Finish or pause safely and release the reservation (or keep it only when
   planned continuity permits, with a deadline).
3. Resolve the new project and validate state and authorization.
4. Update context, revision, and dependencies; create a new session/association.
5. Confirm the switch to the user and report what was preserved from the previous project.

## 5. Closing and reopening

| Status | Reading | New task/edit/merge/deploy | Description |
|---|---|---|---|
| `OPEN` | Allowed by ACL | Allowed by rules | Normal work |
| `CLOSING` | Allowed | **Blocked** | Interrupts work, cancels jobs, prepares snapshot |
| `CLOSED` | Allowed | **Blocked** | Frozen, auditable version |
| `REOPENING` | Allowed | **Blocked** | Verifies synchronization and restores rules |

**Who closes:** manager/authorized person; record reason, owner, timestamp, and
revision. The request must require confirmation. **Who reopens:** a person
authorized by policy, with justification.

### Suggested atomic closing

- Validate permission and record intent.
- In the transactional database, change `OPEN` → `CLOSING` + `generation += 1`
  and close the write gate **in the same step**. All APIs and jobs reject the
  previous generation from then on.
- Invalidate reservations and editing sessions, notify connectors, and try to
  interrupt supervised local execution.
- Block integration and publication through service credentials and external
  repository/CI rules when available.
- Record `closed_revision`, pending-work document, unincorporated work, and audit links.
- Confirm external controls before marking `CLOSED`; if they fail, Central still
  blocks writes and warns that the external block is partial.

### Reopening

- Request authorization; enter `REOPENING`; verify permissions, repository, CI, and task state.
- Restore write policies, increment generation, and keep old tokens/sessions
  blocked until reauthentication or renewal; do not reuse reservations.
- Update agent context and synchronize the revision before accepting a new write; only then `OPEN`.

### What if an AI is still running?

Central can send “stop” to the connector and immediately block **gateway writes**.
It cannot guarantee that an offline local program stops editing its own disk.
Local changes do not enter the official project while closed; direct Git/server
access must be blocked separately.

## 6. User stories

- As a member, I want to say the project name so the AI automatically loads context and tasks.
- As a member, I want to switch projects without losing pending work.
- As a reviewer, I want to see work in progress before it becomes an integrated change.
- As a manager, I want to close a project and prevent new writes to the controlled repository until it is reopened.
- As an auditor, I want to know who closed/reopened it, which revision was frozen, and which work was rejected.

## 7. Expected AI errors and correct response

- “Seloryn does not exist”: do not create a repository automatically; query the catalog/aliases and ask for confirmation.
- “Project closed”: do not change it; read and propose a resumption plan without writing.
- “No permission”: do not request a bypass; tell the member to request access.
- “Another AI occupies the task”: find documented independent work, or wait/release in a coordinated way.
- “Session lost connection”: do not invent progress; synchronize before acting.
- “Base revision changed”: reevaluate diff and tests, without silent overwrite.

## 8. Experience-defining sentence

**“Name the project; the AI finds the right context, continues with the team, and respects when work is closed.”**
