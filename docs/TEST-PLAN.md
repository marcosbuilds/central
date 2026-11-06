# Test and verification plan

## Automated

Executed on 2026-11-04 with .NET SDK 8.0.427:

- Solution build: passed, 0 warnings, 0 errors.
- xUnit tests: 12 passed in the final run, including reference, explicit-focus,
  and reflow checks below.
- Cases: authorized selection; semantic conflict and independent work; stale
  base; closing/reopening; approval with evidence separate from integration;
  nine-person team and offline agent; ordered local Pulse; patch with technical
  commit/local tags/releases; versioning-action blocking in a closed project.

## Manual UI verification

Executed in the self-contained x64 publish after the Home visual review; the
inspection used a window capture and native UI Automation. The environment did
not automatically convert the displayed capture into an archived screenshot, so
historical files are not presented as evidence for this run:

1. Open Home and confirm that `Current installation`, `Overview`, `LOCAL MODE ·
   SIMULATION`, local-mode cards, Context Line, Observable Sequence, and Agents
   and states do not exist.
2. Confirm the single chart with `1 day`, `7 days`, and `31 days` filters, `N/D`
   state, disconnected source, and an explanatory tooltip without inventing points.
3. Confirm the left card with the project mark, Seloryn name, I–V tier, latest
   activity, and external action; confirm the coherent next gate on the right.
4. Confirm request logs below with a masked header and an honest empty state.
5. Navigate to Projects, filter `vendas`/`seloryn`, and confirm custom vector
   marks and the empty state when there are no results.
6. Open Seloryn and verify tabs, revision `r127`, modules, and future gateway context.
7. Reserve `TASK-29`; confirm area update and toast. Close the project and
   confirm visual write blocks.
8. In Workspace, select a file, event, commit, tag, and release; confirm that
   each selection updates the inspector without asserting Git, a branch, or a deploy.
9. Collapse/expand the rail with the door control; confirm animated width,
   arrow rotation, icons-only collapsed state, and accessible tooltips.
10. Open the profile gear, test `Esc`, focus return, and the reduced-motion option.
11. Repeat in a maximized window and at the minimum operable width; confirm
    cards stack and only the table uses local horizontal scrolling.
12. Confirm caret, selection, focus, and scrollbar with visible contrast.
13. In compact Workspace, confirm the order files → inspector → metadata → tasks
    → commits and the presence of observable collaborators without asserting
    external presence.
14. Click task, file, revision, delivery, commit, tag, and release references;
    confirm selection and destination without relying on visual tab order.
15. In Prove, confirm that `Register integration` is disabled for a delivery in
    review and for a closed project, and enabled only for a locally approved
    delivery in an open project.
16. In the empty chart, confirm that every series appears as `N/D`, with no
    inferred zero and with an accessible summary.
17. Open a new session and confirm that Home shows `no project in focus`; open
    Projects, explicitly select an item, and confirm that focus/rail use the same
    `project_id`.
18. In a project with tasks in mixed states, confirm that "next decision" uses
    the first `READY` task; never use `Tasks[0]` as a semantic shortcut.
19. On Home without a gateway, confirm through UI Automation that chart
    axes/legends and empty Request Logs headers/rows do not enter `Document text`.
20. In compact Prove, confirm that delivery actions remain visible below the
    summary and incompatible actions remain disabled.
21. Open settings from the gear, confirm `ControlType=Window`, name `Settings`,
    `Escape`, and focus return.

## Required future coverage

Before connecting real services, automate scenarios CA-01 through CA-20 from the
documentation, including nine sessions, latency, retries, connection loss,
local-connector bypass, project isolation, and external protected-branch rules.
