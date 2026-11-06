# Decision — Obsidian Workspace visual system

Date: 2026-11-06
Status: accepted for implementation review

## Context

The previous desktop shell used a lime accent and a rounded-card visual
language. That made navigation, focus, success, and brand identity compete for
the same signal. Fixed columns and compensating margins also made narrow
windows harder to read.

## Decision

Central adopts the Obsidian Workspace visual system: black canvas, near-black
sidebar, four quiet surface levels, blue-gray navigation/focus, green only for
semantic success, and thin dividers for information hierarchy. Shared WPF
resources define the palette, typography, control states, and spacing rhythm.

The redesign remains a WPF presentation change. It does not imply new Discord,
Codex, Claude, Git, CI/CD, or deployment integrations, and it does not change
the distinction between local fixtures and verified external synchronization.

## Consequences

- The shell and every existing View can share the same tokens without a second
  visual library.
- Keyboard focus and selected states remain visible on a black base.
- Reflow remains local to functional regions rather than using a global
  horizontal scroll or negative right margins.
- Existing screenshots and visual expectations based on the lime identity are
  historical references; the current contract is documented in
  `docs/design/VISUAL-SYSTEM.md`.
- Manual pixel validation at the acceptance sizes is still required before
  merge when a Windows capture of the local binary is available.
