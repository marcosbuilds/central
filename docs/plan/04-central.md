# 04 — Central functional specification

## The problem Central solves

Nine people on different computers use different tools, repositories, AIs, and
messages. Without shared visibility, two people may take the same work, AIs may
change overlapping files, reviews may be forgotten, changes may reach production
without control, and nobody may know why a decision was made.

**Proposed solution:** an internal application that centralizes identity,
projects, tasks, information, authorized agent activity, review, quality, and
publication — with a central live workspace, change review, and Git to preserve
the history of official versions.

## Navigation overview

```text
Central
├── Home / Dashboard
├── Projects (catalog, name search, open/closed status)
│   ├── Overview
│   ├── Planning (scope, stages, tasks, dependencies)
│   ├── Workspace (live shared version, tree, reserved areas, diff, activity)
│   ├── Discussions / Integrations (people, AIs, contracts, questions)
│   ├── Deliveries / Reviews (evidence, approvals, master)
│   ├── Quality (tests, failures, coverage when available)
│   ├── Publications (preview, staging, production, logs)
│   ├── Documentation / Decisions
│   ├── Close/Reopen (change control and frozen version)
│   └── History / Audit
├── AI activity and local connections
├── People / Teams / Invitations
└── Settings / Security / Integrations
```

## Module A — registration, invitation, Discord, and release

**Flow:** administrator generates a single-use invitation with a short validity
period → person creates an account or signs in with Discord OAuth2 → Central
compares identity and invitation → status `PENDING` → authorized administrator/
bot releases access → Central role and appropriate Discord server role are
granted → active session with access to permitted projects.

**Details:** the Discord bot integrates community, release, and notices, but it
is **not Central's sole security source**. Discord removal may trigger review/
suspension under an explicit policy. Use OAuth2 `identify`; use `guilds.join`
only with consent when automatically joining the server. Roles and bots require
specific permissions. Never request a Discord password.

**Account states:** invited → registered → pending → active → suspended/revoked.
Revalidate access in every API and stream, not only on screen.

## Module B — dashboard with useful information

- **Projects:** active, waiting for client, in review, completed, and blocked.
- **Deliveries:** accepted completed tasks, open tasks, waiting time, and deadlines.
- **Quality:** approved/rejected deliveries, failed tests, reopened defects, and post-publication failures.
- **Flow:** blocked tasks, time to review, time to delivery, and incident recovery time.
- **AI collaboration:** active sessions, running tasks, expiring reservations, and possible conflicts.
- **Personal work:** owned tasks and upcoming reviews; avoid ranking online hours,
  commit count, prompts, or tokens as productivity.

Every indicator must show source, period, and definition. Do not perform
automatic individual ranking or invasive monitoring. The team must know and
approve the telemetry policy.

## Module C — complete planning

A project has: problem → scope → milestones → tasks → dependencies → owners →
criteria → risks → decisions → deliveries. Support backlog, Kanban board, simple
schedule, priorities, attachments, estimates, comments, and blockers.

Task: clear title; description; acceptance; owner; participants; status;
dependencies; intended modules/paths; revision; risk; priority; and history. A
project can be selected by name/ID, and the AI can query associated tasks and documentation.

States: `draft`, `ready`, `reserved`, `in_progress`, `in_review`, `blocked`,
`completed`, `cancelled`. `Completed` requires evidence and acceptance; an agent
saying it is finished is not enough.

## Module D — shared live workspace

- One **live working version** per project, identified by revision number; everyone
  sees confirmed changes on the same evolution line.
- Each AI works on a task and reserved logical area (for example,
  `auth.register`, `ui.registration`, `api.contract.registration`); Central prevents
  simultaneous writes to the same responsibility. Directory/file reservations
  reinforce the block when needed.
- Small changes enter the live area after permission, base-revision, patch
  integrity, and minimum-test checks. They **do not require master approval or deployment**.
- Before applying a batch, the gateway checks base revision, hashes, reservations,
  open project status, dependencies, and permissions. It accepts atomically or
  rejects; it never trusts only the AI prompt.
- The tree shows who is working, AI, task, affected contract, latest revisions,
  and conflicts. Messages and discussions can link to any tree part.
- An approved stable copy remains separate: work-in-progress content does not change production.
- Streaming shows observable events; an agent without a reliable adapter may be limited to read/propose.

## Module E — project discussions and AI cooperation

- General project channel, discussions by task/module/file/route, threaded
  replies, people/AI mentions, read receipts, search, and history.
- Structured messages: question, contract request, change proposal, decision,
  blocking question, confirmation, evidence, and review comment.
- A frontend AI may request a contract from a backend AI. Central creates
  `integration_request`, relates consumer/provider, notifies the responsible AI
  session, preserves messages and the versioned contract, and creates a pending
  item when it is offline.
- API contracts include method/route, authentication, fields, examples,
  success/error responses, version, and status (`proposed`, `agreed`, `implemented`,
  `tested`, `obsolete`). A change to an agreed contract notifies dependents and
  requires confirmation/validation.
- No AI may commit on behalf of the client, change a commercial requirement, or
  authorize access to secrets through a message alone.

## Module F — deliveries, history, and reviews

- Live edits are auditable and recoverable `change_sets`. Technical history may
  persist internal snapshots/commits without bothering users with a review for every line.
- `Delivery for approval` gathers a coherent change (large or small but risky),
  with diff, modules, reason, authorship, tests, impact, contracts, and recovery plan.
- Flow: prepare → validate automatically → independent review → approve/reject/
  request correction → integrate into `master` → publish when authorized.
- A reviewer may be **human** or a **delegated specialized AI** with explicit
  scope, its own identity, and attached evidence; never the author/authoring AI,
  and never without evidence.
- High-risk changes (authentication, finance, access, critical data,
  infrastructure, incompatible changes) require at least one human approval even
  when an AI reviewed them. The project owner may choose stricter policies.
- Evidence: reproducible tests (commands, redacted logs, result, version, hash),
  contract validation, security verification, and diff explanation; when missing,
  result is `inconclusive` and delivery does not advance.
- The Git provider's real branch-protection mechanisms must remain; Central's
  decision does not automatically replace GitHub-required review.

## Module F.1 — agents, tokens, and project access

- Each member registers a Central token for use in Codex/Claude Code, with
  separate permission to read projects, work on tasks, propose patches, and review.
- The agent can discover authorized projects by name/alias: `Work on Seloryn`
  resolves the real record, retrieves documentation/revision/work in progress/
  priorities, and asks when ambiguous; it never chooses outside the authorized list.
- Closed projects remain readable for those with permission but accept no write,
  task, merge, or deployment. Closing cancels new authorizations and invalidates
  write reservations; in-flight operations must revalidate state.
- Each local connector reports observable events and sends patches through the
  gateway. A Central token is not an OpenAI/Anthropic API key and does not grant
  free access to those services.

## Module G — deployments and log stream

- Optional change_set/delivery preview → tests → staging → production request →
  authorized-owner approval → publication → health/rollback check.
- Follow pipeline logs in real time with secret cleanup; include failures,
  version, author, commit, and environment.
- Separate “agent execution stream” from “deployment stream”: they are different events with different controls.
- Production must never be a button enabled for any AI token; a closed project
  blocks **new deployments** (except formally authorized emergency recovery when policy allows).

## Module H — living documentation

- Requirements and decisions associated with code and tasks.
- Compare scope changes and approval history.
- Export approved packages as ZIP and import them with validation.
- Search by requirement, task, file, and decision.

## Experience rules

- Responsive from the start; installable app/PWA first, native app only when proven necessary.
- Indicators for `live`, `updated 2 min ago`, and `disconnected`; never simulate activity.
- Do not overload the screen with a surveillance dashboard; prefer project/task focus.
- Conflict messages explain who is working, where, why, and the available alternatives.
- Destructive or high-risk actions require confirmation and are recorded.

## Visual counterexample addendum — Phase 1 desktop

This section is an authorized change to the navigation hypothesis, not a
revocation of the domain rules above. Implementation showed that a shell with
many equivalent destinations and module cards would make a person memorize the
architecture before doing the work Central must coordinate.

The decisive counterexample is opening a task, finding a dependency in a file,
discussing the contract with an AI, and verifying evidence. If each step changes
module and loses the selected project/object, Central fails the coordination
cycle. The approved Phase 1 visual design reduces context switching:

```text
Home → Projects → Selected project
                         ├── Operate       (next decision and blockers)
                         ├── Workspace     (tasks, files, and local Pulse)
                         ├── Coordination  (thread and references)
                         └── Prove         (evidence, checks, and gates)
```

`Plan`, `Publish`, `People and sessions`, and `Settings` are not global shell
destinations in this phase. Their objects were not deleted: planning lives in
Workspace, publication is an explicit state in Prove, local settings open from
the gear, and collaborator facts appear in Workspace/Coordination context.

The empty state is also part of the contract: Home does not choose the first
project by fixture order; the catalog resolves the ID. Without a gateway,
metrics and logs receive no invented values. This slice makes Central a specific
AI-and-human coordination workbench rather than a generic telemetry dashboard.

## Module I — catalog, contextual selection, and lifecycle

- Project with immutable identifier, display name, aliases, owner, repository,
  version, teams, state, and permissions.
- A person may say “work on Seloryn”; the agent calls `list_projects`/
  `resolve_project`, confirms the match, reads state, and associates the session
  with the exact identifier.
- Ambiguous names require a choice, not an assumption. When switching projects,
  the AI closes/pauses the previous reservation, records the resume point, and
  opens a new session at the destination.
- Project status: `OPEN` → `CLOSING` → `CLOSED` → `REOPENING` → `OPEN`.
  `ARCHIVED` is an optional separate administrative state.
- Closing is a **server transaction**: suspends new tasks, invalidates temporary
  permissions and delayed synchronizations, records version and reason, blocks
  publications, and notifies connectors. Reopening requires authorization and new synchronization.
- Blocks must apply to APIs, interfaces, WebSocket, jobs, workers, Git
  integrations, and deployments — not only to the interface.
- Details and verifiable criteria are in `13-catalog.md`.
