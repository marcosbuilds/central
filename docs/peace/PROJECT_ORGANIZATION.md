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
├── assets/                 # versioned visual assets
├── bot/                    # Python package
├── docs/                   # documentation and decisions
├── tests/                  # to be created with the first tests
└── data/                   # local data; not a source of code
    ├── README.md
    ├── runtime/            # new operational state
    └── snapshots/          # Discord exports
```

The current SQLite database remains at `data/peace.sqlite3` for compatibility.
It is a legacy location and must not be moved for aesthetics alone. A future
move to `data/runtime/peace.sqlite3` must update configuration, create a backup,
and validate the database before and after the move.

## Planned package split

Today `bot/main.py` contains initialization, views, panels, events, tickets,
set flow, operations, boosters, Iris, and scheduling. The split must be
incremental:

```text
bot/
├── main.py                 # compatibility and bootstrap
├── cfg.py                  # configuration loading and validation
├── db.py                   # temporary database facade
├── context.py              # redaction and context limits
├── ai.py                   # Iris client and prompts
├── api.py                  # REST client used by utilities
├── features/               # domain rules
│   ├── set_flow.py
│   ├── tickets.py
│   ├── operations.py
│   ├── boosters.py
│   └── developer_flow.py
├── ui/                     # views, embeds, and panel synchronization
├── integrations/           # Discord REST, Iris, and external services
└── persistence/            # schema, migrations, and repositories
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
