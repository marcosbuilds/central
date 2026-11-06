# UI audit — Obsidian Workspace

Date: 2026-11-06

## Scope

The audit covered the WPF shell, shared resources, the Home and Projects views,
the project workbench tabs, Settings, Team, and the existing responsive handlers.
The goal was to preserve bindings and local/real integration boundaries while
making the interface read as a focused development workspace.

## Findings before the redesign

| Priority | Finding | Evidence | Resolution |
| --- | --- | --- |
| P0 | The old lime accent was used as the brand, action surface, active navigation state, and focus state. | `App.xaml` used `#CFFF4E` for `AccentBrush`. | Replaced with semantic blue-gray accent `#8BA7D0`; green is reserved for success/online states. |
| P0 | The shell and views had inconsistent outer margins and the Home chart used negative horizontal margins. | `MainWindow.xaml`, `DashboardView.xaml`, `ProjectsView.xaml`, and `ProjectView.xaml`. | Standardized page insets to the 4/8/12/16/20/24/32 rhythm and removed the chart/list negative compensation. |
| P1 | Surfaces were over-rounded and nested, making the app read like a generic card dashboard. | Shared `CardBorder`, `PanelBorder`, `DialogPanel`, and repeated inline borders used radii from 8 to 16. | Reduced shared radii to 5–8 and retained borders/dividers only where they carry hierarchy. |
| P1 | The title bar was taller than the requested workspace density and duplicated status emphasis. | `MainWindow.xaml` used a 58-unit title bar and bright status pills. | Reduced title bar to 52 units and moved status emphasis to quiet, bordered labels. |
| P1 | Settings used four fixed integration columns that could push content outside the viewport. | `SettingsView.xaml` used four `*` columns. | Replaced the fixed grid with a wrapping layout of bounded cards. |
| P1 | Workspace and Home reflow existed, but the visual system did not make the stacked regions feel intentional. | `DashboardView.xaml` and `ProjectView.xaml` used the old card language. | Kept the existing size handlers and redesigned the surfaces/dividers so stacked regions preserve reading order. |
| P2 | Functional text relied heavily on all-caps labels and Seloryn in dense catalog content. | Views used all-caps labels and Seloryn for project names. | Kept short technical category labels where useful, moved primary content to Segoe UI Variable, and reserved Seloryn for identity/empty-state moments. |

## Implementation notes

- No backend, security, data, synchronization, or fixture behavior was changed.
- Existing `AutomationProperties`, event handlers, bindings, tabs, and lifecycle
  gates were preserved.
- Focus remains visible on buttons, tabs, search, and text fields through the
  shared control templates.
- The existing reduced-motion preference remains authoritative for sidebar and
  chart behavior.

## Visual evidence

The local Release executable was launched after the redesign. The Windows
capture helper did not expose the locally built custom-`WindowChrome` window in
its inventory, so a pixel screenshot from the local binary could not be
captured in this environment. The application process remained responsive and
the XAML build completed successfully. The acceptance matrix below separates
code/build evidence from visual checks that still need a human desktop pass.
