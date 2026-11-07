# Project organization

## Objective

Keep the root predictable, separate code from local state, and allow the bot to
evolve from a functional monolith into domain modules without breaking the
server, database, or already-published panels.

## Current tree and target rule

```text
.
├── AGENTS.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── main.py                 # provider entry point
├── config/                 # environment configuration
├── core/                   # context and error handling
├── commands/               # operator utilities
├── integrations/           # Discord REST and Iris adapters
├── operations/             # structural maintenance
├── persistence/            # SQLite access
├── assets/bot/             # bot runtime artwork
├── docs/                   # documentation and decisions
├── tests/peace/            # bot tests
└── data/                   # local data; not a source of code
    ├── README.md
    ├── runtime/            # new operational state
    └── snapshots/          # Discord exports
```

The current SQLite database remains at `data/peace.sqlite3` for compatibility.
It is a legacy location and must not be moved for aesthetics alone. A future
move to `data/runtime/peace.sqlite3` must update configuration, create a backup,
and validate the database before and after the move.

## Current source split

`main.py` contains initialization, views, panels, events, tickets, set flow,
operations, boosters, Iris, and scheduling. Supporting modules are grouped at
the repository root:

```text
main.py
config/
core/
commands/
integrations/
operations/
persistence/
```

Create new directories only when there is real code to put in them. Do not
create empty directories just to complete an idealized tree.

## Refactoring order

1. Create tests for `context.py`, `nick.py`, configuration, Peace IDs, and basic
   SQLite operations.
2. Extract visual components and embeds without changing business rules.
3. Extract the set flow and tickets while keeping delegated calls in `PeaceBot`.
4. Extract operations, boosters, Iris, and the developer flow.
5. Separate the schema and migrations from database access.
6. Reduce `main.py` to bootstrap, event registration, and module composition.

At every stage, installed commands, panel `custom_id` values, and existing
SQLite data must remain stable.
