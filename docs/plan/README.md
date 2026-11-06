# Software startup + Central Colaborativa for development

**Planning version:** 1.1 · **Date:** 2026-11-03 · **Initial team:** 9 people
**Source state:** original planning preserved; the Phase 1 desktop implementation
is in `D:\projetos\Central` and does not rewrite this package's domain contracts.

## What we will build

The company delivers **systems, web, mobile, and desktop applications,
automations, platforms, and services**, not just websites. Central is its
internal application for planning, documenting, and tracking projects;
integrating members' own AIs; coordinating the **same live version** of the
code; enabling cooperation between AIs; reviewing deliveries; and controlling
official versions and publication.

## Agreed rules

1. **Nine specialties**, but a multidisciplinary team; the documenter interviews
   the client, details scope/architecture with the technical lead, and delivers
   an organized ZIP.
2. **Multiple projects** in Central. The AI selects by natural name/alias
   (`work on Seloryn`), querying only authorized projects.
3. **One live workspace for everyone**, with sequential revisions, atomic
   patches, reservations by task/module/logic/file. AI-isolated branches are not
   the primary experience.
4. **Projects can be closed** to make their code/state immutable until reopened,
   including against agents and old tokens; reading follows permission.
5. **Everyday changes ≠ official delivery ≠ deployment.** Live code has
   recoverable history; `master` is protected and receives only approved
   deliveries; publication is an independent decision.
6. **Human or specialized-AI review with explicit delegation and reproducible
   evidence.** An AI cannot approve its own change. Critical changes require
   human approval.
7. **AIs talk in the project**, discuss tasks, request API routes, record
   contracts, and resolve blockers; the team follows everything in searchable threads.
8. Security by project, client, member, and token; Discord supports invitations/
   community and does not replace authentication/authorization.
9. Telemetry shows observable facts, does not capture private AI reasoning or
   invent streaming. The dashboard measures outcome and quality, not online hours.

## Documents (recommended reading)

| Path | Content |
|---|---|
| `01-team.md` | current team and future openings |
| `02-cases.md` | frontend, backend, and systems with examples |
| `03-delivery.md` | client, documenter, architecture, and initial ZIP |
| `04-central.md` | platform screens, modules, and rules |
| `05-architecture.md` | components, servers, integration, and boundaries |
| `06-data.md` | entities, contracts, and events |
| `07-collaboration.md` | live workspace, logic reservations, connectors, and streaming |
| `08-security.md` | Discord, identity, tokens, projects, and delegations |
| `09-operations.md` | metrics, reviews, deployments, and operations |
| `10-roadmap.md` | recommended build order |
| `11-acceptance.md` | verifiable scenarios for testing Central |
| `12-references.md` | official documentation consulted and limits |
| `13-catalog.md` | AI project selection, pausing, and closing |
| `14-approval.md` | **commit/delivery policy, approval, and AI conversations** |
| `15-protocol.md` | suggested API, entities, events, and integration rules |
| `template/` | short template for a project delivered to the team |

## Simple glossary

- **Frontend:** screens and interactions a person sees.
- **Backend:** rules, processing, and data behind the screens.
- **System:** the complete working set (interface, logic, database,
  integrations, and operations) that solves a need.
- **API:** an agreed way for programs to exchange information.
- **Live workspace:** a shared version where the team follows authorized changes
  almost in real time.
- **Revision `r123`:** recoverable record of one stage of live work.
- **Git commit:** record of changes; it may be small or large.
- **Delivery for approval:** coherent group of changes seeking entry into `master`.
- **`master`:** protected, stable history separated from work in progress.
- **Deployment:** putting an approved version into a test or production environment.
- **API contract:** documented agreement about routes, data, and errors between frontend and backend.

## Next real action

Before creating dashboards, test the **coordination core** with two simulated AIs
and then nine sessions: select a project; lock logic; submit a patch; show
activity; open an API discussion; freeze the project; prepare a delivery; review
with evidence; integrate into master without automatic deployment. Require test
and failure-recovery evidence before expanding.

**Attention:** flows and endpoints are **proposals**, not currently available
features. Codex/Claude integrations need tests with real SDKs and versions; do
not assume that a token alone prevents local edits outside the gateway.

## Counterexample addendum — Phase 1 interface

This addendum changes the original visual-navigation hypothesis only where
implementation and adversarial review demonstrated a better-grounded
counterexample. The domain remains normative: live workspace, reservations,
review, evidence, security, and publication remain separate.

The rejected counterexample is a shell exposing `Overview`, `People`, `Settings`,
`Plan`, `Publish`, and other modules as equivalent destinations, plus a card for
each metric. It looks complete but forces a person to memorize the taxonomy before
solving Central's core work: identify the project, understand the next decision,
inspect the artifact, discuss it with the team, and prove the result.

The exclusive hypothesis replacing it in Phase 1 is:

```text
Home → Projects → Selected project
                         ├── Operate
                         ├── Workspace
                         ├── Coordination
                         └── Prove
```

The project is the context boundary. Tasks, files, commits, tags, releases, and
Pulse belong to Workspace; people/AI references belong to Coordination; evidence,
checks, and publication states belong to Prove. Home starts with no project in
focus and does not silently choose the first fixture.

The interface also must not invent streaming, productivity, tokens, presence,
Git, CI, or a gateway. Without a source, usage and Request Logs are `N/D`/empty;
local states are declared as local. The desktop implementation and its auditable
decisions are in `docs\DESIGN-CONTRACT.md` and `docs\DESIGN-DECISIONS-2026-11-04.md`.
