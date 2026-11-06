# 10 — Workflows, reviews, tests, publications, and productivity

## Task states

`draft` → `approved-to-run` → `available` → `reserved` → `in-progress` →
`awaiting-review` → `corrections-requested` (returns to execution) / `validated`
→ `delivered`. Auxiliary states: `blocked`, `cancelled`. State changes have an
author and reason.

## Change-set states

**Small change sets:** `proposed` → `automatically-validated` →
`applied-to-live-workspace` → `reviewed/snapshotted` (without master approval or deployment).

**Master delivery:** `immutable-candidate` → `CI` → `in-review` →
`pending-corrections` / `rejected` / `approved` → `integrated-into-master` →
`release-eligible` (deployment requires separate authorization).

A rejection requires documented reversal/neutralization in the live workspace or
a replacement decision; it must not silently affect the stable version. Approvals
are tied to the exact hash: if the diff changes, reevaluate.

## Review rules

- The author is never the sole approver of their own change.
- A change in a sensitive area (authorization, payments, data, infrastructure,
  deployment, data deletion) gets two reviewers or a special policy.
- Review considers requirement and acceptance, diff, impacts, security, tests,
  readability, error handling, performance when needed, and documentation.
- A comment has open/resolved state and a line or logical resource. Rejection
  decisions need a reason.
- QA automates routine tests; human review focuses on risk and coherence.

## Minimum tests by type

- Backend: rules, input errors, authorization, concurrency, database, and integration.
- Frontend/mobile: flows, accessibility, empty states, network errors, and supported devices.
- Contracts: API, events, and client compatibility.
- Infrastructure: reproducible publication, rollback, backup, and secrets.
- Central engine: claims, revisions, patches, events, idempotency, misbehaving
  agents, and project isolation.

## Deployment policy

1. Choose the candidate revision, freeze the snapshot, and list change sets.
2. Require approvals and valid tests on the **same revision**; prevent old
   approval for a changed diff.
3. Generate an identifiable artifact, preferably with hash and build evidence.
4. Use preview/staging and test behavior according to risk.
5. An authorized owner approves production, with additional confirmation for sensitive systems.
6. Publish an immutable artifact, monitor failures, and keep rollback ready.
7. Record date, executor, version, changelog, links, and incidents.

“Deploy with streaming” in the interface must mean **following live** the stages,
filtered logs, tests, and result. Never confuse watching a build with authorization
to promote unreviewed code.

## Work and effort metrics

Measure teams and projects first. Examples:

- **Delivery:** tasks accepted against criteria, stage predictability, and value demonstrated to the client.
- **Quality:** production failures, error rework, risk-covered tests, and completed reviews.
- **Flow:** blocked time, review wait, and incident recovery time.
- **Collaboration:** resolved dependencies, useful documentation, and reviews that prevent problems.
- **Cost:** tool/infrastructure usage by project when measurable and consented.

**Do not use:** lines of code, raw commit count, tokens used, connected hours,
keystroke frequency, message count, or punitive opaque “productivity scores”. A
member may avoid major loss with a few lines or a good interview.

## Comments and planning

An important decision in a comment should be promoted to a project `decision`;
loose discussion does not replace requirements. Mentions notify only authorized
members of the same project. A client can approve a functional delivery without
understanding every line internally.

## Minimum meetings

- Scope definition with a clear document.
- Dependency alignment when a shared contract changes.
- Short delivery review and demonstration for client/users.
- Blameless failure retrospective; correct the process.
