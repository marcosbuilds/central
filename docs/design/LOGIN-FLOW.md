# Central login flow — interface-only slice

Status: visual interface only; Discord, DM delivery, challenge exchange, and
session creation are not connected by this slice.

## Screen sequence

1. **Discord** — explains that the member starts from the Peace/Discord link.
2. **Peace ID** — collects the identifier that the bot would associate with the
   immutable Discord member ID and the configured `Dev` role.
3. **DM code** — represents the one-time code the bot would send privately. The
   screen explicitly states that it must not appear in public channels, logs, or
   snapshots.
4. **Session ready** — shows the hand-off point where a future authentication
   service would exchange the challenge for a short, project-scoped session.

The current controls only move between local visual states. They do not call
Discord, send a DM, persist a challenge, or create a Supabase session. The
implementation intentionally keeps this boundary visible until the
`docs/INTEGRATION-PEACE-CENTRAL.md` contract has an approved service, expiration,
attempt limit, revocation path, and negative tests.

## Accessibility and responsive behavior

- The flow is exposed as one dialog in UI Automation.
- Each stage has a named primary action and predictable keyboard focus.
- Escape cannot dismiss the login gate accidentally.
- The layout remains scrollable at the compact desktop minimum of 820×560.
