# Documentation maintenance

This is the maintenance contract for the public documentation. It keeps the
reading path, implementation claims, visual assets, and review process aligned.
It does not claim that every planned capability exists.

## Information architecture

```text
README.md
  └── docs/README.md
        ├── guide/         build, tests, branches, contribution, maintenance
        ├── architecture/  runtime, design, server, decisions
        ├── integration/   public component contracts
        ├── operations/    deployment boundaries and smoke checks
        ├── bot/            companion bot documentation
        ├── plan/           product and development planning
        └── template/       reusable project-delivery structure
```

Each folder has one responsibility. New documents should use a short filename
that describes the stored content; do not add catch-all folders or duplicate
copies of an existing contract.

## Status and ownership

| Area | Canonical location | Update when |
|---|---|---|
| public scope | `README.md` | supported surface or phase boundary changes |
| runtime | `docs/architecture/system.md` | component or authority changes |
| build and tests | `docs/guide/` | toolchain, test, or verification changes |
| design | `docs/architecture/design.md` | UI, accessibility, or motion changes |
| decisions | `docs/architecture/decisions/` | security, data, permission, or integration decisions |
| public contracts | `docs/integration/` | component boundary changes |
| operations | `docs/operations/` | deployment or smoke-test boundary changes |
| workflow | `AGENTS.md`, `docs/guide/` | branch or review policy changes |
| product plan | `docs/plan/` | scope, roadmap, or acceptance changes |
| bot | `docs/bot/` | bot behavior, inventory, or source rules change |

The author of a code or asset change updates the relevant canonical document in
the same Pull Request. Reviewers should reject a public claim with no
implementation, test, or explicit decision reference.

## Public-only rule

The repository and its documentation are public. Do not add secrets, tokens,
private identifiers, live credentials, member data, local absolute paths,
copied private messages, or unverified operational details. Use placeholders
and label future work as **Planned**, **Deferred**, or **Unverified**.

## Visual asset contract

Documentation visuals live in `assets/docs/`; bot artwork lives in
`assets/bot/`. The current public documentation set is:

| Asset | Role | Contract |
|---|---|---|
| `assets/docs/central-mark.png` | collaboration mark | 1024 × 1024 PNG, RGBA, text-free |
| `assets/docs/sync-stream.png` | state movement between endpoints | 1200 × 720 PNG, RGBA, text-free |
| `assets/docs/review-flow.png` | branch, review, and approval flow | 1200 × 720 PNG, RGBA, text-free |

The files must be checked at the file level and rendered on a light and dark
surface before review. A viewer's checkerboard or overlay is not part of a
transparent asset. Replacements must preserve the documented purpose and must
not contain private or operational text.

## Review gate

Every source, documentation, asset, migration, or public-text change receives a
focused commit and a Pull Request. CI and the relevant manual evidence are
recorded before merge; `main` is changed only by an approved Pull Request.

## Acceptance checklist

- The document is in English and has a direct filename.
- It appears in `docs/README.md` or is intentionally scoped below `bot/`,
  `plan/`, or `template/`.
- Implemented, verified, planned, deferred, and unverified states are not mixed.
- Commands use repository-relative paths and contain no credentials.
- Markdown links resolve from the file that contains them.
- Assets have a purpose, the required alpha behavior, neutral public content,
  and a consuming-document reference.
- `git diff --check`, relevant tests, and the final staged file list pass.
