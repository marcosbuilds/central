# Documentation plan

This plan keeps the public documentation useful as the codebase grows. It is a
maintenance contract, not a claim that every planned capability exists.

## Goals

- Give a new contributor one reliable reading path.
- Keep implementation, verification, design decisions, and product planning
  distinct.
- Explain branches, commits, Pull Requests, and agent handoffs without relying
  on private conversation history.
- Make every public claim traceable to code, a test, or an explicit decision.
- Provide reusable visual assets without embedding operational details.

## Information architecture

```text
README.md
  └── docs/README.md
        ├── ARCHITECTURE.md       runtime boundaries
        ├── BUILD.md              build and package
        ├── TEST-PLAN.md          verification
        ├── CONTRIBUTING.md       human workflow
        ├── BRANCHES.md           branch lifecycle
        ├── DESIGN-*.md           interface decisions
        ├── DECISION-*.md         implementation decisions
        ├── DEPLOYMENT-*.md       operational evidence
        ├── INTEGRATION-*.md      public contracts
        ├── peace/                 scoped bot docs
        └── plan/                  product and development plan
```

## Status and ownership

| Area | Canonical document | Update when |
|---|---|---|
| public scope | `README.md` | supported surface or phase boundary changes |
| runtime | `ARCHITECTURE.md` | component boundary or authority changes |
| build | `BUILD.md` | toolchain, package, or installer changes |
| verification | `TEST-PLAN.md` | test command, acceptance proof, or limitation changes |
| design | `DESIGN-CONTRACT.md` | UI contract, accessibility, or motion changes |
| decisions | `DECISION-*.md` | a security, data, permission, or integration decision is made |
| workflow | `AGENTS.md`, `CONTRIBUTING.md`, `BRANCHES.md` | branch or review policy changes |
| product plan | `plan/` | scope, roadmap, or acceptance criteria change |
| bot | `peace/` | bot behavior, inventory, or scoped operational contract changes |

The author of a code change updates the canonical document in the same Pull
Request. Reviewers should reject a public claim that has no implementation or
verification reference.

## Public-only rule

The repository and its documentation are public. Do not add secrets, tokens,
private identifiers, live credentials, member data, local absolute paths,
copied private messages, or operational details that are not already an
intentional public contract. Use placeholders and explain boundaries at a
conceptual level. The public development plan is allowed; it must label
future work as planned or deferred.

## Maintenance cycle

### 1. Baseline — complete

The documentation was translated to English and now has a public index, branch
guide, contributor workflow, and agent contract.

### 2. Evidence alignment — next

For each runtime area, link the implementation, the test, and the current
limitation. Remove stale commands, local machine paths, and claims that cannot
be reproduced from a clean checkout.

### 3. Design references — in progress

Use the transparent, text-free PNGs in `assets/` only where they improve
orientation. Keep illustrations neutral, reusable, and separate from product
state or telemetry claims.

The current public assets have these stable roles:

| Asset | Role | Delivery contract |
|---|---|---|
| `assets/central-mark.png` | collaboration and coordination mark | 1024 × 1024 PNG, RGBA, text-free |
| `assets/sync-stream.png` | synchronized state between two endpoints | 1200 × 720 PNG, RGBA, text-free |
| `assets/review-flow.png` | change, review, and approval flow | 1200 × 720 PNG, RGBA, text-free |

They were generated from repository-safe prompts in the ChatGPT image workspace,
then downloaded, normalized to the documented canvas sizes, and checked locally
for PNG RGBA format and transparent corner pixels. The visualizer's checkerboard
or dark preview surface is not part of the asset. Future replacements must keep
the same public purpose, avoid private or operational text, and repeat the
same file-level validation before review.

### 4. Review gate — continuous

Every source, documentation, asset, migration, or public-text change receives a
commit and a Pull Request. CI and the relevant manual evidence are recorded
before merge.

## Acceptance checklist

- The document is in English and has a direct filename.
- It appears in `docs/README.md` or is intentionally scoped below `peace/` or
  `plan/`.
- Implemented, verified, planned, deferred, and unverified states are not mixed.
- Commands use repository-relative paths and contain no credentials.
- Links resolve from the repository root.
- Assets have purpose, transparent background where requested, neutral colors,
  and no private text.
- `git diff --check`, the relevant tests, and the final staged file list pass.
