# Design contract — Central Colaborativa v1.1

Status: domain and accessibility foundation contract; the current visual review
is in `docs/DESIGN-DECISIONS-2026-11-04.md`
Decision owner: Phase 1 implementation, subject to later human validation
Date: 2026-11-04

> Precedence note: the decision addendum above governs the shell/Home redesigned
> on this date. The Pulse, workspace, and governance sections below remain valid
> for project detail and the future domain; they must not reintroduce Context
> Line, Observable Sequence, or Agents and states to Home.

## Additional evidence and redesign decision

The human review recorded in `artifacts/qa-screens/HUMAN-REVIEW-2026-11-04.md`
recognized the organization but asked for less text and more visual
representation: agents working in an observable sequence, specific tasks,
discussions with mentions and references, and a workspace with files, titled
commits, tags, and releases. The independent architecture review confirmed that
the previous model had no event identity/order, file tree, or destinations for
references.

Decision: the “Context Line” signature remains as guidance, but the project's
main surface becomes the **local Pulse**. It shows agents, task, logical area,
operation, and result in a manual deterministic sequence. The user advances each
event with the `Advance simulation` button; this is not real streaming, online
presence, synchronization, or external activity.

Allowed scope in this review: local in-memory fixtures for files, titled
technical commits, tags, releases, discussion references, and stream events.
Each item has an explicit source and state. The project has no connected Git,
server, CI, WebSocket, Discord, Codex, or Claude; releases/tags/commits are
local demonstration records and do not produce a deployment.

## Evidence boundary

This contract separates what the documentation authorizes from visual
interpretation. The catalog, manual Pulse, workspace, and governance surfaces
remain WPF/.NET 8 with in-memory `CentralStore` and local fixtures; they are not
turned into remote data by appearance. In parallel, the shared-folder vertical
slice uses `CentralSyncRuntime` with Syncthing, Supabase Auth/PostgreSQL/Realtime,
and explicit connection state. Discord, Codex, Claude, Git, CI, and deployment
remain out of scope.

Main sources used:

- `docs/plan/04-central.md`: navigation, coordination, planning, reservations,
  and observable telemetry.
- `docs/plan/07-collaboration.md`: claims, base revision, events, sessions, and reconciliation.
- `docs/plan/08-security.md`: permissions by member/project/task/resource and approval limits.
- `docs/plan/09-operations.md`: allowed metrics, audit, publishing, and rollback.
- `docs/plan/10-roadmap.md`: prioritize the coordination core before a decorative dashboard.
- `docs/plan/11-acceptance.md`: isolation, states, concurrency, and validation.
- `docs/plan/13-catalog.md`: selection by ID, context, lifecycle, and write blocking in a closed project.
- `docs/plan/14-approval.md`: local editing, live workspace, approved delivery, integration, and publishing as distinct concepts.
- `docs/plan/15-protocol.md`: observable events without private reasoning.

## Primary jobs

1. Identify the correct project and recover context without choosing by ambiguous name.
2. Find the next ready, compatible, unblocked task.
3. Check task, logical, physical-path, and dependency reservations before writing.
4. Understand the current revision, base, blockers, and next gate.
5. Discuss a contract/integration without confusing a request with a response or permission.
6. Inspect evidence and review without confusing approval with integration or publication.
7. Consult people, sessions, and global governance without turning presence into productivity.

Real frequency is not measurable in this phase: the data is local fixtures. The
frequencies above are structural protocol priorities, not usage telemetry.

## Authorized content and actions

Authorized in Phase 1:

- navigate Home, Projects, and the explicitly selected project; local settings
  live in the gear dialog;
- select a project and view lifecycle, tasks, simulated reservations, simulated
  workspace, discussions, deliveries, quality, publications, and history;
- execute only local simulations already supported by `CentralStore`, always
  labeled as simulations;
- show source, revision, timestamp/freshness when the data exists; otherwise say
  that the indicator is local/simulated;
- visually block actions incompatible with a closed project, delivery state, or missing evidence.

Not authorized:

- claim real integration, synchronization, operational security, CI, Git,
  deployment, human approval, or real online presence;
- show private reasoning, tokens, connected time, or activity as productivity;
- invent ACLs, aliases, event sources, stale thresholds, reconnection, or delivery guarantees;
- offer “approve”, “integrate master”, or “publish” as though they had external effects.

## Information and navigation hypothesis

Hypothesis: Central is a context-anchored decision queue, not a count dashboard.
The interface's first response should be: “which project am I in, which decision
can move forward, what is blocking it, and what is the next permitted action?”

Current global navigation:

- **Home**: context without a project or triage for the already selected project;
  technical usage and request logs remain honest when no gateway exists.
- **Projects**: catalog, unambiguous search, lifecycle, and explicit selection.
- **Selected project**: contextual access to the four canonical modes; people/
  sessions and settings do not compete as global destinations.

Inside the project:

- **Operate**: next step, blockers, and permitted action.
- **Workspace**: tasks, dependencies, reservations, files, local Pulse, commits,
  tags, and releases.
- **Coordination**: local discussions, contracts, and references.
- **Prove**: quality, evidence, deliveries, and publication states.

`Plan`, `Publish`, `People and sessions`, and `Context` are not equivalent
destinations in the current shell. Their objects remain accessible in the
canonical mode where they can be understood.

## Detail visual signature: local Pulse

Hook: **Right context. Clear next step.**

The former Context Line concept is not a Home strip or a navigation destination.
In detail, local Pulse shows observable events without claiming external
execution. It is not generic progress or a ticker.

### Local Pulse

Local Pulse is the primary visual representation of authorized activity. Each
event shows:

`event + sequence → agent/provider → task → file/resource → operation → result`

Future events remain in a manual queue; advancing the simulation reveals one
event at a time, selects its detail, and updates local activity without
auto-scrolling. The list preserves identity and sequence so repetition,
inspection, and origin are not confused with an external stream.

The workspace uses a master-detail composition: file tree on the left, stream in
the center, and selected detail on the right. Below the stream are local
technical commits with a title, tags, and local releases. Resolvable references
appear as actionable chips; references without a modeled object remain visible,
but disabled and labeled unavailable in this simulation.

Exceptions have visual precedence over the list: closed project, blocked
dependency, offline session, unavailable source, stale revision, missing
evidence, and error must appear above/with textual emphasis. The user must
understand the block before noticing the sequence.

## State and trust model

Each region must distinguish, whenever applicable:

- business state: open, closed, in review, approved, pending;
- availability: local, connected, offline, stale, unknown source;
- result: pass, fail, execution error, not run;
- source/freshness: local simulation, observation, and time; no “live” without a real stream;
- permission: allowed, read-only, denied, or lifecycle-blocked.

Minimum matrix:

| Region | Honest local state |
|---|---|
| Project | open / closing / closed / reopening; closed remains readable and blocks writing |
| Task | ready / reserved / in progress / in review / blocked / completed / cancelled |
| Workspace | simulated revision; local patch pending/applied; no real file changed |
| Discussion | persisted locally, pending, denied, or error; never an invented response |
| Delivery | draft/prepared/in review/approved locally; external integration unconfirmed |
| Quality | PASS/FAIL/PENDING/STALE/ERROR; execution is separate from result |
| Session | locally observable, disconnected, pending; no productivity inference |

## Visual tokens

Initial semantic values, subject to contrast testing:

- canvas `#0E1216`;
- surface `#151B20`;
- elevated surface `#1C252C`;
- border/divider `#2A353D`;
- primary text `#F3F6F7`;
- secondary text `#A9B3BD`;
- action/focus `#D8FF63`;
- information `#7EA9FF`;
- success/verified `#42D6AE`;
- attention/pending `#F2B660`;
- error/denied `#F17E86`;
- unavailable `#8D9AAD`.

The action color does not mean success. Each state has a label and/or icon/shape
in addition to color. Text uses the existing Segoe UI, with display roles
32/40, title 20/28, body 14/21, label 11/14, and number/revision 24/30. Base
spacing: 8 px; few surface levels; no ornamental shadow.

## Compact behavior

- At the minimum supported width, the project header uses explicit columns and
  may wrap to two lines; it never overlaps title, badge, and action.
- Project navigation visually reduces groups and allows localized horizontal tab
  scrolling without clipping text.
- Main content preserves reading order; lists do not force window-wide horizontal scrolling.
- Long text and 125–200% scale must preserve state and action identification.
- Future event lists should group updates (“N new updates”), preserve focus, and allow pause/inspection.
- In the workspace, the tree, stream, and detail may stack at compact width;
  horizontal scrolling is contained only in the code/manifest panel when two
  dimensions are required.
- The advance button is a manual action and stays near the Pulse state; it does
  not start a timer, loop, or auto-scroll.

## Accessibility

- The window frame and controls have explicit accessible names or preserve the native frame.
- Every field has a visible label or `AutomationProperties.Name`; a tooltip is not the only name.
- Current navigation exposes semantic state, not only color.
- Visible focus on buttons, tabs, fields, and disabled controls with an explanation.
- High-risk actions ask for confirmation and a reason when supported by the domain.
- Important messages do not disappear only on timeout and can be read by assistive technology.
- Full keyboard support: Tab/Shift+Tab, Enter/Space, tab arrows, Escape in overlays; focus returns to the trigger.
- Visible contrast, color-independent states, and reduced-motion mode.

## Motion

No loops, pulses, or tickers. Only short transitions (approximately 150–180 ms)
of opacity/transform are allowed for selection, orientation, and opening context.
Reduced motion removes the transition without removing the state. Activity
updates do not reorder or auto-scroll the list.

## Open decisions

- real data source, authentication, ACL, cadence/freshness, and reconnection;
- event, release, deployment, persistent-audit, and integration contracts;
- official alias and ambiguity resolution;
- final design of the global Work/Governance view;
- automated audit with Accessibility Insights/Inspect and load testing with nine sessions.

While open, these areas remain labeled future/disconnected and do not authorize
new behavior.

## Validation plan and falsifiable checks

1. `dotnet build` Release with no warnings/errors.
2. Existing xUnit tests and new checks for Pulse identity/order, file selection,
   local tag/release creation, and lifecycle blocking.
3. Visual inspection of the installation in dashboard, catalog, detail, planning,
   workspace, discussions, deliveries, quality, publications, history, team,
   and settings.
4. No-search-result scenario: correct count and empty state.
5. Closed scenario: reading continues; reserve, patch, approval, integration, and
   publication are blocked/explained.
6. Pending/offline/stale scenario: no false green points, invented response, or
   external guarantee.
7. Keyboard, focus, accessible names, compact width, and enlarged-scale testing.
8. Reaction test: advance Pulse, select agent/event/task/file, open a reference,
   view the commit title, and distinguish a local tag/release from publication.
   Within five seconds, identify the project, blocker, permitted action, and
   next gate. If someone repeats the visual sequence but misses the exception,
   local Pulse has failed.
9. Do not claim screen-reader or production-performance auditing without the
   corresponding tool and source.

## Completion criteria

The redesign is considered better only when it reduces misleading signals found
in inspection: `LOCAL · SEGURO`, all-green states, literal risk binding, enabled
incompatible actions, search without an empty state, low-contrast titles,
wrapping headers/tabs, and unnamed fields. The final installer must have the same
honesty as the source and remain buildable/navigable.

---

## Current navigation contract — AI coordination workbench

This section supersedes the seven-equivalent-tab hypothesis described above. The
change was authorized by the product owner after the 2026-11-04 human review and
is recorded in full in `docs/DESIGN-DECISIONS-2026-11-04.md`.

### Central job

A person must be able to choose the correct project, understand the next allowed
decision, inspect the artifact and human/AI work, discuss the decision, and prove
the result without losing context. Central is a coordination workbench, not a
count dashboard or a generic module manager.

### Canonical routes

- **Home:** compact global context. Shows an explicitly selected focus or a
  clear indication that no focus was selected, AI technical usage, and request
  logs without inventing a source or aggregate counts without an object.
- **Projects:** catalog and unambiguous identity resolution. Entering a project
  requires explicit selection.
- **Project / Operate:** next step, blockers, current revision, and permitted
  action. It is not the owner of the file tree.
- **Project / Workspace:** canonical owner of tasks, criteria, dependencies,
  reservations, file tree, README when present in the manifest, local Pulse,
  commits, tags, and releases.
- **Project / Coordination:** local chat with threads, mentions, and references
  to known objects. Request, contract, and integration types remain visible in the conversation.
- **Project / Prove:** deliveries, checks, history, and publication states.
  `local release`, `local integration`, `local approval`, and `unconnected
  deploy` are never collapsed into “published”.

`Plan`, `Publish`, and `Context` are not first-level destinations in this
review. Their objects were not deleted: tasks/reservations live in Workspace;
history lives in the stream/Prove; publication lives as an explicit state within Prove.

### Reference destination contract

The destination must be semantic and independent of visual control order:

| Reference | Canonical destination | Minimum result |
|---|---|---|
| task, dependency, criterion | Workspace | selected item and reservation context visible |
| file, line, commit, event, tag, release | Workspace | selected inspector and local origin visible |
| delivery, check, review, publication state | Prove | selected item and distinct gate |
| person, agent, session | Coordination/Workspace | identity and availability explicitly modeled, or “no detail in this phase” |

### Visual surface

The project uses one workbench per mode, with dividers and selectable rows; it
does not use one separate card for each datum. The tree, content, and inspector
remain functional panels. At compact width, reading order is preserved, the
inspector stacks, and delivery actions move into their own band instead of
leaving the viewport.

### States and honesty

The contract continues to prohibit inventing presence, productivity, tokens,
streaming, Git, CI, or publication. When the gateway does not exist, usage and
request logs show `N/D`/empty with the missing source. `0` may appear only when
zero was measured by a real source. A local state must say `local`, `pending`,
`not connected`, or equivalent.

### Compact navigation

The shell starts with the rail collapsed by default, but the reopen button and
page context remain accessible by name and focus. When expanded, the brand and
profile reappear. The minimum supported width remains 820×560; the workbench
stacks panels when the width cannot sustain readable columns. Home starts with no
project in focus: no fixture is selected silently; the user resolves identity in
the catalog.

## Precision addendum — Context Cursor

The former detail-context banner was deliberately replaced by an inline header
state (`local fixture · gateway unavailable`). The information was not removed;
its surface was reduced so the project and next decision receive visual precedence.

The rejected counterexample is a control room with repeated cards, green states,
and continuous motion. It would be eye-catching but would not be Central: it
would confuse a missing source with productivity and force the person to memorize
modules. The current grammar is an **open C facing the next step** — bounded
context, a clear passage, and no success/presence meaning embedded in the logo.

In Workspace, compact order is files → inspector → metadata/collaborators →
tasks → commits → Pulse. The catalog uses rows with normalized local logos and
explicit destinations. References must select the canonical object; a toast
without selection is a behavior failure.

`N/D` remains distinct from measured zero. In a no-gateway state, the chart does
not show a numeric scale that could be read as measurement, axes, or legend;
request logs remove the table header/viewport and keep only the compact empty state.
