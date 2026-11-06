# 10 — Stages to build Central (suggested order)

## Stage 0 — Definitions and risk prototype

- Documenter and technical lead define roles, client constraints, project types,
  review policies, and backlog.
- Technically prove a patch gateway with revisions/hashes and two simulated
  agents, including same-logic blocking.
- Test closing during a patch, network loss, and recovery. **Do not invest first
  in a decorative dashboard.**

## Stage 1 — Reliable foundation

- Login/invitation, approval/Discord OAuth, member linking, project permissions,
  and audit trail.
- Project/alias registration, open/closed state, linked documentation, ZIP
  import, and Git repository.
- Tasks with owners, priorities, blockers, criteria, and dependencies.

## Stage 2 — Live workspace

- Central change gateway, revisioning, snapshots, semantic/file reservations,
  TTL locks, and synchronized local workspaces.
- Project tree, diff, and real activity; test with simulated agents and Git.
- Recovery/reconciliation after disconnect, synchronization quality, and backups.

## Stage 3 — First AIs and conversations

- Documented Codex adapter; then Claude and other connectors with declared capabilities.
- Project selection by name, planning read, task selection/reservation.
- Project/task threads, AI mentions, API requests, versioned contracts, and notifications.

## Stage 4 — Official deliveries

- Create immutable candidate, run CI, attach evidence, and use human/authorized-AI
  review according to risk.
- Integrate with real `main` protection, reversal, releases, and separate
  deployment with approval trail.
- Prove that small changes do not publish automatically and an AI cannot self-approve.

## Stage 5 — Operations and growth

- Dashboard for delivery, quality, queues, and bottlenecks; define data retention and privacy.
- Observability, alerts, limits, backup/restore, replication, and cost analysis.
- Multi-team and client support, repository policies, specific administrators, and hiring expansion.

## Gate for each stage

To move forward: a recorded real demo, reproducible automated tests, known
issues published, owners defined, performance data measured, and a verified
recovery plan. Do not declare readiness based only on a visual prototype.
