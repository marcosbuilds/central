# Approved deliveries, commits, versioning, and agent dialogue

**Status:** proposed specification; not implemented. **Objective:** enable shared
live code without confusing editing, official version, and publication; allow AI
and people to discuss integrations in a traceable way.

## 1. Central language: four different things

| Simple screen name | Technical record | Human review required? | Enters main? | Deploys? |
|---|---|---|---|---|
| Work in progress | Unsynchronized local change | No | No | No |
| Live change | `change_set`, sequential revision, recoverable snapshot | Usually no; automated checks required | No | No |
| Delivery for approval | Set of revisions + diff + checks + opinion | According to risk and policy | Only after approval | Not automatically |
| Publication | Release, environment, artifact, and rollback | According to environment | Uses already-approved version | Yes, after authorization |

**Precision note:** Git defines a *commit* as a record of changes, not
necessarily a large change. Central calls the package requesting approval a
**delivery**; its implementation may use periodic technical commits, snapshot
hashes, and one consolidated integration commit, without requiring every
micro-edit to create a PR and deployment. Small high-risk changes still require approval.

## 2. Versioning model

- `workspace_revision`: increments for every confirmed patch set in the live
  workspace; everyone sees the same logical sequence.
- `change_set`: author, agent, task, files/symbols, base revision, patch, hash,
  date, checks, reason, and reversals; changes may be grouped.
- `snapshot`: recoverable state at a known point; automatic write by batch/interval and before important deliveries.
- `delivery_candidate`: immutable set of `change_set`s selected for integration;
  an ID, hash, main base version, dependencies, and risk summary.
- `main`: protected stable Git history; only the approved integration service
  publishes a validated delivery to the protected branch (through PR/merge or an
  equivalent provider-controlled mechanism).
- `release`: named version/tag after an approved delivery; does not imply deployment.
- `deployment`: link among release/commit, environment, requester, approval,
  tests, logs, and rollback.

Recommendation: use semantic versioning for products that need it (for example
`1.2.0`) and workspace revision numbers for daily coordination (`r145`). Do not
increase product version for every patch.

## 3. Risk policy (not only size)

| Risk | Example | Suggested approval |
|---|---|---|
| Low | Interface text, formatting with no behavior effect | **Independent** AI reviewer with evidence may be sufficient if the project authorizes it |
| Medium | New route, compatible database adjustment, validation behavior | Independent specialized AI + required checks; human review optional/according to policy |
| High | Authentication, authorization, payments, data deletion, destructive migrations, production configuration | At least one authorized person, with technical opinion and tests; AI assists but does not decide alone |

**Universal condition:** without explicit permission, an AI gives an **opinion**,
not executable approval. It never self-approves. If Git policy requires human
review, an AI opinion does not automatically satisfy it. Approval belongs to the
exact reviewed hash; if the diff changes, reevaluate.

## 4. Evidence required before approval

Each delivery generates an **evidence dossier**:

1. **Exact change:** revision reference, hash, human and agent authorship, task/requirement.
2. **Why change:** problem, expected result, impact on dependencies and user.
3. **Checks run:** commands, environment, versions, secret-free logs, relevant
   coverage, and comparison with the previous scenario.
4. **Contracts:** touched APIs/routes/events/schemas, notified consumers, and contract tests.
5. **Security and recovery:** risk, permissions/data analysis, reversal plan,
   backup/migration when applicable.
6. **Independent review:** distinct author/reviewer, answered comments, decision
   reason, timestamp, and test-job ID.

Tests are run by isolated CI infrastructure, not merely declared in AI text. An
AI may raise questions, reproduce defects, open correction requests, and mark a
delivery `inconclusive`. A reviewer cannot simply write “approved” without
linking evidence. Logs and artifacts must be verifiable.

### Delivery state machine

`DRAFT → PREPARED → TESTING → IN_REVIEW → [CHANGES_REQUESTED | REJECTED | APPROVED] → INTEGRATING → INTEGRATED`.

- Changes requested: author corrects, updates the hash, and restarts checks and review when necessary.
- Rejected: do not integrate into main, but keep auditable history and rollback
  in the live area. If other change sets depend on it, open a reconciliation incident.
- Integrating: service checks project state, permission, hash, and main base
  again; detects regressions/incompatibilities; only then publishes to the protected branch.
- `APPROVED` does not mean GitHub or production accepted the change. If an
  external rule denies merge, mark `BLOCKED` and record the reason.

## 5. Conversation between agents inside the project

**Locations:** project channel, task thread, file/line discussion, API
integration request, review comment, contract-change announcement. Each message
belongs to a project and may reference logical resource, revision, contract, and task.

**Minimum message:** `message_id, project_id, thread_id, sender_type, member_id,
agent_session_id, type, resource_refs, body, created_at, mentions, visibility,
reply_to`. The shown identity is `Codex from [member]`, `Claude from [member]`,
etc., never “an unknown AI”.

Types: `question`, `integration_request`, `contract_proposal`, `contract_ack`,
`contract_ready`, `blocker`, `decision`, `review_comment`, `evidence`,
`notification`. Threads can be resolved, reopened, searched, and audited.

**Coordination:** an active session receives a mention and responds through an
authorized adapter; an inactive session receives a notification/pending request,
without invented response or model spend without the owner's policy and
authorization. A budget and message limit per integration are recommended to
prevent infinite AI loops.

## 6. Complete example — frontend requests an API from backend

1. Frontend Codex reserves `ui.registration` and sees a dependency on
   `api.registration` in planning.
2. It posts: “Which route, authentication, payload, response, errors, and expected
   timing?” Central creates `integration_request IR-24` linked to tasks T-17 and T-18.
3. Backend Claude, owner of `api.registration`, replies with a **contract
   proposal** (not a promise of ready code):

```yaml
id: api.registration.v1
status: proposed
method: POST
path: /api/register
request:
  content_type: application/json
  body: { name: string, email: string, password: string }
responses:
  201: { user_id: string, status: pending_verification }
  400: { code: validation_error }
  409: { code: email_already_registered }
owner: task:T-18
consumer: task:T-17
```

4. Codex replies `contract_ack` (accepts or asks); Central changes the contract
   to `agreed`, records the version, and notifies both.
5. Frontend may prepare the interface using a mock **labeled as simulation**; it
   does not confuse a proposed API with an available one.
6. Backend implements and publishes contract-test evidence. State: `implemented`, then `tested`.
7. Central tells frontend that the route is tested in revision `r123`; Codex
   synchronizes and runs real integration in a test environment.
8. If backend changes a field, it creates `contract_change` before an incompatible
   change; dependents are alerted and integration is tested again.
9. Everyone can comment and consult the decision months later without losing
   context in private chat.

## 7. Dependency rules and conflicts

- A logical resource has a temporary owner and consumers (`api.registration`
  provides, `ui.registration` consumes). Two agents may develop their portions
  in parallel; an incompatible contract change requires coordination.
- A message *does not grant* a reservation or authorization. Central checks claims and permissions through the API.
- Rules apply by file **and by logic**; different file names do not guarantee
  independence. When in doubt, reserve the larger module and block dangerous changes.
- The gateway revalidates `project.state`, revision, and hashes when confirming a patch. No conversation can authorize a bypass.
- `CLOSED` projects allow discussion/reading when policy permits; writing, merge,
  release, and deployment are blocked until reopening.

## 8. Where it appears in the interface

Project screen: `Overview | Planning | Live workspace | Discussions | Integrations/API | Deliveries | History | Publications | Security`.

In Workspace, clicking a file shows each agent's changes, related contracts,
revisions, and thread. In Integrations, show pending requests, agreed contracts,
consumers, and checks. In Deliveries, show dossiers, diff against main, checks,
who approved, and why. In History, recover a revision without contaminating main.

## 9. Risks and safeguards

- **AI argument/loop:** limit turns, discourage ping-pong, allow cancellation/escalation to a human.
- **Route/result hallucination:** contracts move to `tested` only with a CI check; distinguish proposal from implementation.
- **Disguised self-approval:** correlate agent → member → author and require another owner for executable review.
- **Silent API change:** changelog, consumer acknowledgment, compatibility tests.
- **Patch followed by closing:** fencing token and atomic gateway check to reject writing after close.
- **Stale approval:** bind approval to exact hash and base commit; revalidate during integration.
- **Delivery merge into changed live work:** compute an immutable candidate; reconcile dependencies/revisions before approving/publishing.
- **Confidential data in conversations/streaming:** project authorization, configurable retention, secret redaction; never store model private reasoning as a requirement.

## 10. Specific acceptance tests

- Two AIs request and confirm a contract; another person follows the thread in real time.
- Offline backend session: request persists and is answered on reconnect; no invented response.
- Contract change invalidates affected integration and triggers a required check.
- 100 small edits create reversible revisions **without** 100 deployments/PRs.
- Low-risk delivery with independent AI reviewer, valid evidence, and delegated policy may proceed to main; without delegation, it may not.
- Authoring AI tries to approve with another token from the same person: block when policy requires independence.
- Authentication change with a favorable AI opinion remains blocked until human review.
- Approval referring to an old hash is invalid after a new patch.
- Project closed between review and merge prevents integration and deployment.
- External GitHub checks reject merge: Central does not show false success.

## Technical references

- Git: https://git-scm.com/docs/git-commit (commit records state; it does not require a large change).
- GitHub protected branches: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches (reviewers, checks, locking, merge queue).
- Codex App Server: https://learn.chatgpt.com/docs/app-server (events, approvals, application integration).
- Claude Agent SDK: https://platform.claude.com/docs/en/managed-agents/migration (agents, sessions, tools, permissions).

*All revision numbers, tasks, projects, and APIs in this chapter are proposed
examples, not existing implementations.*
