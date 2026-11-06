# Branches

Branches are short-lived workspaces for a single outcome. GitHub is the live
source for branch state; this document defines the meaning of a branch name and
the route back to `main`.

## Protected baseline

| Branch | Meaning | Rule |
|---|---|---|
| `main` | reviewed and releasable baseline | no direct commits; changes arrive through an approved Pull Request |

Start every task by syncing from `origin/main`. A local branch with the same
name is not proof that it is current.

## Work branches

| Prefix | Use for | Example |
|---|---|---|
| `feature/` | new product or integration behavior | `feature/sync-reconnect` |
| `fix/` | a focused defect correction | `fix/empty-state-layout` |
| `docs/` | documentation, public text, or documentation visuals | `docs/public-docs-visuals` |
| `chore/` | maintenance, tooling, dependencies, or repository hygiene | `chore/update-ci` |
| `import/` | one-time migration or source import evidence | `import/central-peace` |

`import/` is historical by design. Do not use it for ongoing feature work.
Keep branch names lowercase, short, and specific; avoid names that contain
people, credentials, client data, or machine paths.

## Current public branch history

The repository may retain branches such as the original import, documentation
translation, or bot-continuation work for traceability. Their commit history is
useful evidence, but their names do not change the rules above. New work must
branch from the current `origin/main`, even when an older branch looks close to
the requested change.

## Required flow

```text
origin/main
    │
    └── feature/ | fix/ | docs/ | chore/
                         │
                         ├── plan and edit
                         ├── verify and commit
                         ├── push branch
                         └── Pull Request → review + green CI → main
```

An agent must not merge its own work by default. If a branch is abandoned,
close the Pull Request with a note and preserve the commits for reference; do
not rewrite shared history to hide the attempt.
