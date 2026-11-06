# Documentation map

This directory is the public source of truth for how Central is built,
verified, operated, and extended. It is organized by reader need rather than
by implementation history.

## Read in this order

1. [`../README.md`](../README.md) — public scope and quick start.
2. [`ARCHITECTURE.md`](ARCHITECTURE.md) — runtime boundaries and current limits.
3. [`BUILD.md`](BUILD.md) and [`TEST-PLAN.md`](TEST-PLAN.md) — reproducible
   development and verification.
4. [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`BRANCHES.md`](BRANCHES.md) — team
   workflow, commits, branches, and Pull Requests.
5. [`DESIGN-CONTRACT.md`](DESIGN-CONTRACT.md) and
   [`DESIGN-DECISIONS-2026-11-04.md`](DESIGN-DECISIONS-2026-11-04.md) — interface
   rules and recorded design decisions.
6. [`DOCS-PLAN.md`](DOCS-PLAN.md) — documentation ownership, status, and
   maintenance roadmap.
7. [`plan/`](plan/) — public product and development planning.

## Document groups

| Group | Location | Purpose |
|---|---|---|
| Overview | `README.md` | public scope and limits |
| Runtime | `ARCHITECTURE.md`, `SERVER-PLAN.md` | components and boundaries |
| Delivery | `BUILD.md`, `DEPLOYMENT-*.md` | build, packaging, and operational evidence |
| Quality | `TEST-PLAN.md`, `plan/11-acceptance.md` | automated and manual verification |
| Design | `DESIGN-CONTRACT.md`, `DESIGN-DECISIONS-*.md` | visual and interaction contract |
| Integration | `INTEGRATION-PEACE-CENTRAL.md` | public integration contract and limits |
| Team workflow | `AGENTS.md`, `CONTRIBUTING.md`, `BRANCHES.md` | agent and contributor rules |
| Planning | `plan/` | product, architecture, security, roadmap, and acceptance planning |
| Bot context | `peace/` | scoped bot documentation and inventory |

## Status language

Every document must make its status clear:

- **Implemented** — code exists and the cited verification can reproduce it.
- **Verified** — the implementation was exercised by the stated check or
  observation.
- **Planned** — the target is documented but not available yet.
- **Deferred** — intentionally postponed with a reason.
- **Unverified** — code or configuration exists, but the required proof is not
  complete.

Do not use a future-tense plan as evidence of a delivered feature.

## Public boundary

Planning is intentionally public so the team can work from the same source.
Public docs must contain only repository-level contracts, reproducible commands,
decisions, and evidence that can be shared openly. Keep secrets, private
identifiers, local machine paths, member data, and live credentials out of this
directory. Use placeholders and link to committed examples instead.

## Visual references

The documentation visuals are deliberately text-free so they can be reused in
public pages without exposing operational details:

![Central collaboration mark](../assets/central-mark.png)

![Synchronization stream](../assets/sync-stream.png)

![Review flow](../assets/review-flow.png)

Asset purpose and maintenance rules are recorded in
[`DOCS-PLAN.md`](DOCS-PLAN.md).
