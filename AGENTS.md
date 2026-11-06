# Central — agent guide

This repository is public. Treat every committed line, filename, image, issue,
and Pull Request as public material. This guide is the operating contract for
human contributors and development agents working in the monorepo.

## Scope and source of truth

The repository contains the Central desktop application, the companion
automation bot, database migrations, operational scripts, tests, and public
planning. The source tree and the current `main` branch are authoritative;
chat messages, local files, generated output, and uncommitted experiments are
not release evidence.

The public boundary is strict:

- Never commit credentials, tokens, cookies, private keys, local database
  files, user data, private URLs, internal host paths, or copied chat history.
- Do not document a capability as delivered unless the repository contains the
  implementation and a reproducible verification path.
- Use placeholders in examples and keep live identifiers out of public docs.
- Planning may remain public, but proposals must be labelled as planned,
  deferred, or unverified.

## Canonical tree

```text
.
├── app/       # Central desktop and shared core
├── bot/       # companion automation bot
├── db/        # database migrations
├── ops/       # gateway, installer, and operational scripts
├── tests/     # application and bot tests
├── assets/    # versioned visual and bot assets
├── data/      # local markers only; runtime data stays out of Git
├── docs/      # public guides, decisions, integration, and plan
└── .github/   # CI and review templates
```

Local-only folders such as `artifacts/`, `tools/`, `shared-test/`, caches,
snapshots, `.env` files, credentials, and generated databases must stay ignored
and must never be added with a broad `git add .` without reviewing the file
list.

## Plan before editing

Every agent must begin with a short plan before changing files:

1. Read this file and the nearest scoped instructions.
2. Inspect `git status`, the current branch, and the relevant public docs.
3. State the intended outcome, files in scope, risks, and verification.
4. Confirm whether the work is implemented, documentation-only, or a proposal.
5. Stop and ask when the change would expose data, alter permissions, or expand
   the product boundary beyond the request.

Do not start by editing `main`, by rewriting another contributor's work, or by
guessing a contract that is not documented.

## Branch workflow

- `main` is the reviewed, releasable baseline. Never commit directly to it.
- Create work from the latest `origin/main` using one of `feature/`, `fix/`,
  `docs/`, or `chore/`.
- Use one purpose per branch and keep the branch name short and explicit.
- Historical `import/` branches are evidence of migration, not a place for new
  feature work.
- See [`docs/BRANCHES.md`](docs/BRANCHES.md) for the branch contract and the
  review flow.

## Commit and Pull Request rules

Every repository update must finish in a coherent commit. A commit is not a
substitute for review:

- Write a focused commit message with an imperative subject, for example
  `docs: organize the public documentation map`.
- Review `git diff --check`, the staged file list, and the diff before committing.
- Push the work branch and open or update a Pull Request for every shared
  change, including source, migrations, configuration, documentation, assets,
  and public repository text.
- A Pull Request must explain the outcome, public boundary, tests/checks, and
  any remaining limitation.
- `main` may change only through an approved Pull Request with green CI and the
  required reviewer approval. Do not merge your own change unless the project
  owner explicitly assigns that responsibility.

## Documentation and asset rules

- Keep documentation in English and use direct filenames that describe their
  contents.
- Update the relevant guide in the same Pull Request as the implementation.
- Keep `docs/README.md`, `docs/BRANCHES.md`, and `docs/DOCS-PLAN.md` aligned
  with the actual tree and workflow.
- Visual assets must have a clear purpose, a stable filename, no secret or
  private text, and a documented source or generation note.
- Prefer transparent PNGs with a restrained neutral palette for documentation
  visuals. Do not replace an existing asset without explicit approval.

## Minimum verification

Run the smallest complete set that proves the change, and record the result in
the Pull Request:

- Central: `tools/dotnet/dotnet.exe build Central.sln -c Release` and
  `tools/dotnet/dotnet.exe test Central.sln -c Release`.
- Bot: `python -m pytest tests/peace -q` in the project virtual environment.
- Documentation/assets: link and filename review, `git diff --check`, and a
  final scan for secrets, local paths, and generated state.

Before handoff, report the branch, commit, Pull Request, checks, and any
remaining limitation. If the work is not ready for review, do not present it
as complete.
