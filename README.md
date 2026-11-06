# Central

Central is a Windows desktop workspace for collaborative software development.
It brings project context, coordination, shared-state boundaries, verification,
and review-led delivery into one public codebase.

The repository is intentionally honest about its phase. Implemented behavior,
local simulations, synchronized state, and planned integrations are documented
separately; a proposal is never presented as a production capability.

## Public scope

- .NET 8 and WPF desktop application in `app/`.
- Companion automation bot in `bot/`.
- Database migrations and access rules in `db/`.
- Gateway, installer, and operational scripts in `ops/`.
- Automated tests in `tests/`.
- Public architecture, decisions, development plan, and review rules in `docs/`.
- Versioned visual and bot assets in `assets/`.

## Repository map

- `app/` — desktop application and shared core.
- `bot/` — companion automation bot.
- `db/` — database migrations.
- `ops/` — gateway, installer, and scripts.
- `tests/` — application and bot tests.
- `assets/` — visual and bot assets.
- `data/` — local markers only.
- `docs/` — public documentation and plan.
- `.github/` — CI and Pull Request templates.

## Documentation

Start with [`docs/README.md`](docs/README.md). It defines the reading order and
links to the architecture, build, test, design, integration, operations, and
planning documents.

- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — branch, commit, and Pull
  Request workflow.
- [`docs/BRANCHES.md`](docs/BRANCHES.md) — branch purposes and lifecycle.
- [`docs/DOCS-PLAN.md`](docs/DOCS-PLAN.md) — public documentation roadmap and
  maintenance rules.
- [`docs/plan/`](docs/plan/) — public product and development planning.

## Development workflow

Plan first, create a branch from the latest `origin/main`, make a focused
change, run the relevant checks, commit it, push the branch, and request a Pull
Request. `main` is reserved for reviewed and approved changes.

Do not add credentials, tokens, private identifiers, local paths, runtime data,
or copied private conversations. Examples must use placeholders. See
[`AGENTS.md`](AGENTS.md) for the complete agent contract.

## Build and test

From PowerShell at the repository root:

```powershell
& .\tools\dotnet\dotnet.exe restore .\Central.sln
& .\tools\dotnet\dotnet.exe build .\Central.sln -c Release --no-restore
& .\tools\dotnet\dotnet.exe test .\Central.sln -c Release --no-restore
python -m pytest tests/peace -q
```

The bot test command requires the project's Python environment and dependencies.
The exact packaging flow is in [`docs/BUILD.md`](docs/BUILD.md).

## Phase boundary

The current codebase documents which surfaces are local, synchronized, or
planned. The public repository does not claim an unobserved multi-computer
proof, a production authentication broker, or an automatic deployment flow.
Check the relevant decision and test documents before extending a boundary.
