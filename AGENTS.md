# Central — monorepo rules

This directory contains the source for Central Colaborativa and the Peace
Discord bot. The organization separates products by responsibility while
maintaining a single version-control system and review flow.

## Canonical tree

```text
.
├── app/                      # Central desktop: core/ and desktop/
├── bot/                      # Peace bot Python code
├── db/                       # Supabase migrations
├── ops/                      # gateway, installer, and scripts
├── tests/                    # app/ and peace/ tests
├── assets/                   # versioned bot assets
├── data/                     # ignored local state
├── docs/                     # architecture, decisions, integration, and plan/
└── .github/                  # CI and review templates
```

`artifacts/`, `tools/`, `shared-test/`, caches, local databases, snapshots,
`.env` files, and credentials are local and must not enter the repository.
`.env.example` is allowed only when it contains no secret values.

## Peace → Central integration

The planned contract is in `docs/INTEGRATION-PEACE-CENTRAL.md`. The Discord bot
is authoritative for confirming the member and the technical `Dev` role;
Central does not receive or store the bot token. DM codes must be single-use,
expire, have an attempt limit, and be logged without their cleartext value.

The contract is documented, but code exchange is not considered implemented.
The current PythonAnywhere gateway remains health- and capabilities-only; it
must not receive the Discord token or become an authentication broker without an
architecture decision and security tests.

## Git process

- `main` contains only reviewed and approved code.
- All work enters through a branch (`feature/`, `fix/`, `docs/`, or `chore/`).
- Direct commits to `main` are not allowed.
- Every change must go through a pull request, passing CI, and approval from an
  authorized contributor.
- Migrations, Discord permissions, authentication, and data changes require a
  recorded decision and a corresponding negative test.

## Minimum verification

- Central: `tools/dotnet/dotnet.exe build Central.sln -c Release` and
  `dotnet test`.
- Peace: `python -m pytest tests/peace -q` after installing the package in a
  virtual environment.
- Before publishing, review `git diff --check`, `git status`, and the file list
  to confirm that no secret or local state was included.
