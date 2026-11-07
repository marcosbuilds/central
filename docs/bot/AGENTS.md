# Peace bot source rules

This document describes the Peace bot's specific rules within the monorepo.
The general rules are in the root `AGENTS.md`.

## Bot structure

The bot files live in these focused locations in the tree:

- `bot/`: package code;
- `assets/bot/`: versioned images and other resources used by the bot;
- `docs/bot/`: bot architecture, operations, and decisions;
- `tests/peace/`: automated tests;
- `data/`: local state and exports, always ignored when they contain real data;
- `pyproject.toml`: bot packaging and commands.

Do not create root directories or files named `tmp`, `output`, `backup`, `new`,
`final`, `logs`, `exports`, `reports`, or equivalents. Temporary output must go
in `data/runtime/`, `data/snapshots/`, or a temporary directory outside the
project.

## Data and secret rules

- Never commit `.env` files, tokens, credentials, SQLite databases, Discord
  snapshots, dumps, logs containing message content, or personal data.
- `data/` is local state, not source code. The legacy database
  `data/peace.sqlite3` may be moved only through an explicit migration with a
  verified backup.
- New snapshots must be written to `data/snapshots/`.
- New operational state must be written to `data/runtime/` when a database
  migration is planned.
- Do not print tokens, national IDs, phone numbers, ticket content, or private
  data in logs, tests, or review messages.

## Code rules

- Preserve Peace's identity. Do not rename the server, brand, or identity
  categories as part of a refactor; naming changes require an explicit decision
  and compatibility plan.
- Keep the public entry points `peace-bot`, `peace-snapshot`, and `peace-nick`
  defined in `pyproject.toml`.
- Do not change existing panel `custom_id` values without a planned migration.
- The `spam-control` channel panel and asset are a strict contract: do not change
  its text, embed, or `assets/bot/automod.png` without explicit authorization.
  Welcome, set, support, and operations artwork are the safe points for visual
  evolution.
- Do not change the schema or move SQLite without preserving the data and
  recording the migration.
- `bot/main.py` must remain a compatibility entry point during the refactor.
  Supporting code belongs in responsibility-specific subdirectories such as
  `bot/config/`, `bot/core/`, `bot/commands/`, `bot/integrations/`,
  `bot/operations/`, or `bot/persistence/` instead of adding more root-level
  modules.
- Server settings come from `.env` and `bot/config/settings.py`; do not hardcode tokens,
  IDs, or permissions in new features.
- Classify every role as `access` or `visual`. A visual role must have all global
  permissions cleared, must not appear in authorization guards, and must never
  control channel visibility. An access role must have a documented technical
  purpose; do not use a visual role to grant permission.
- New operational names must follow the English pattern already used on the
  server. In organized categories, use `╭` for the first channel, `├` for
  middle channels, and `╰` for the last; dry areas such as `staff-only`,
  `scan-only`, and `logs` use no ornaments.
- Before renaming, removing, or reusing a role/channel, collect its ID, members,
  overwrites, and code usage. Preserve the ID when that reduces risk.
- Peace IDs must never be silently reused: leaving Peace reserves the ID;
  returning requires a card in `scan-only`, approval, and a record of the new ID.
- Every change to permissions, roles, tickets, moderation, or personal data
  must validate authorization, hierarchy, and partial failures.
- AI support remains disabled while `IRIS_ENABLED=false`; before re-enabling it,
  record which channels, data, and guards will be used.

## Dependency and external-bot rules

- Before adding a dependency or external bot, document the problem it solves,
  the data it accesses, and the removal plan.
- Prefer one well-configured integration over multiple bots with overlapping
  responsibilities.
- Iris may guide and prepare actions, but must never be treated as the authority
  to grant roles, punish members, or delete structure without system
  confirmations and guards.

## Required change process

1. Read this file and the relevant documentation before editing.
2. Make small, reversible changes, separating organization from behavior changes.
3. Add or update tests for changed pure logic, database, permissions, and flows.
4. Run tests and a startup check before completing the change.
5. Update the README or `docs/` when execution, configuration, or the tree changes.
6. Describe risks, required migrations, and generated files in the handoff.

## Conventions

- Python: modules and functions use `snake_case`; classes use `PascalCase`.
- Documentation: descriptive names in `UPPER_SNAKE_CASE.md` or `kebab-case.md`,
  with no competing copies of the same subject.
- Each file must have a clear responsibility; avoid generic modules such as
  `utils.py` when a domain-specific name is possible.
- Generated artifacts must be reproducible and must never be used as the source
  of truth.
