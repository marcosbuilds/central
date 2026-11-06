# Visual system — Obsidian Workspace

Central is a native Windows coordination workspace for programmers and AI
agents. Its visual language is intentionally quiet: the interface should help
someone identify context, available work, reservations, review gates, observed
activity, and the next action without pretending that fixtures are external
connections.

## Tokens

Tokens live in `app/desktop/App.xaml` and are consumed by the shell and views.

| Token | Value | Use |
| --- | --- | --- |
| `WindowBackgroundBrush` | `#000000` | Application canvas and deepest reading surface. |
| `SidebarBrush` | `#08090B` | Navigation rail. |
| `SurfaceBrush` | `#0D0F12` | Bounded work surfaces. |
| `SurfaceRaisedBrush` | `#15181C` | Inputs, secondary controls, and elevated regions. |
| `HoverBrush` | `#1C2026` | Pointer hover and active control feedback. |
| `LineBrush` | `#272C33` | Dividers and quiet borders. |
| `TextBrush` | `#EDF0F3` | Primary content. |
| `MutedTextBrush` | `#ACB5C0` | Supporting copy and metadata. |
| `SubtleTextBrush` | `#818B98` | Low-priority labels and unavailable states. |
| `AccentBrush` | `#8BA7D0` | Selection, focus, navigation, and technical links. |
| `AccentSoftBrush` | `#1B2838` | Selected/linked surface. |
| `SuccessBrush` | `#45B890` | Success and confirmed online state only. |
| `AmberBrush` | `#D5AB6B` | Pending, review, and attention. |
| `RedBrush` | `#E47B83` | Blocked and error states. |

## Type

- Segoe UI Variable Display is used for page and section headings.
- Segoe UI Variable Text is used for functional copy, controls, and metadata.
- Cascadia Mono is used for paths, IDs, revisions, and other code-like values.
- Seloryn remains an identity accent for selected brand/empty-state moments; it
  is not used as the default for dense technical content.
- The normal content floor is 11px. Page headings stay around 26–28px and
  section headings around 17px.

## Layout rhythm

Use 4, 8, 12, 16, 20, 24, and 32 units as the default spacing scale. Optical
adjustments are allowed when measured content needs them, but negative margins
are not a layout strategy.

- Sidebar: 72 units collapsed, 216 units expanded.
- Title bar: 52 units.
- Page inset: 24 units on the main work area.
- Control radius: 5–6 units.
- Panel radius: 7–8 units.
- Dividers: 1 unit.

## Interaction states

All shared buttons expose normal, hover, pressed, disabled, and keyboard-focus
states. Tabs use the accent as a bottom rule rather than a filled pill.
Compound fields use a stronger border when focused. Toasts retain their state
color and provide a dismiss action. No visual state is introduced without a
corresponding model or control state.

## Responsive behavior

The shell keeps the sidebar and title bar stable while page content uses local
reflow:

- Home stacks focus and technical usage before content becomes cramped.
- Operate stacks the decision, blockers, and activity regions.
- Workspace stacks files, inspector, metadata, then tasks and commits.
- Settings wraps integrations and installation information rather than forcing
  four columns into a narrow viewport.
- Project lists remain list-like and use truncation for long identifiers;
  horizontal scrolling is kept local to data tables where it is necessary.
