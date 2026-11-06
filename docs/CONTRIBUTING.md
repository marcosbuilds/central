# Contributing

Central uses a review-led workflow. The goal is not only to produce a change,
but to leave a public, reproducible record of why it exists and how it was
checked.

## Before editing

1. Read the root [`AGENTS.md`](../AGENTS.md) and this guide.
2. Fetch the repository and inspect the current branch and status.
3. Create a focused branch from `origin/main`.
4. Write down the outcome, files in scope, risks, and verification plan.
5. Check whether the change affects public docs, security, data, migrations,
   permissions, or an external service.

## Local change loop

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c docs/short-purpose

# edit and verify only the requested scope
git diff --check
git status --short
git diff --stat

git add <reviewed-files>
git diff --cached --check
git diff --cached --name-status
git commit -m "docs: describe the public workflow"
git push -u origin docs/short-purpose
```

Use `feature/`, `fix/`, `docs/`, or `chore/` as appropriate. Do not use a
blanket add without reviewing the staged file list.

## Commit style

Use a short imperative subject and keep each commit coherent:

| Prefix | Meaning |
|---|---|
| `feat:` | new behavior |
| `fix:` | defect correction |
| `docs:` | documentation or public text |
| `test:` | test-only change |
| `refactor:` | behavior-preserving code structure |
| `chore:` | maintenance or tooling |

Every repository update must have a commit. Do not amend or rewrite a commit
that another contributor has already pulled without agreement.

## Pull Requests

Open or update a Pull Request after pushing the branch. The description must
include:

- the user-visible outcome;
- the files or components changed;
- the public-boundary and security impact;
- commands or checks run and their result;
- known limitations and follow-up work.

The Pull Request must pass CI and receive the required review before it is
merged into `main`. Documentation-only and asset-only changes still use this
flow when they change the shared repository.

## Documentation and assets

Keep the document map and the implementation aligned. Add a decision record
when a change affects security, data, permissions, authentication, migrations,
or an integration contract. New visual assets must be purposeful, text-free
unless exact text is required, transparent where practical, and free of private
or machine-specific information.

## Handoff

The final handoff names the branch, commit, Pull Request, checks, and remaining
limitations. “Done” means the result is committed and reviewable; it does not
mean that an unobserved production or multi-computer proof may be assumed.
