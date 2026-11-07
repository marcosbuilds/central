# Peace local state

This directory is reserved for the bot's operational state and local exports.
SQLite databases, Discord snapshots, logs, and member data are not committed to
version control. Source code lives in `bot/`, assets live in `assets/`, and
tests live in `tests/`. The provider deployment copies the contents of `bot/`
to its runtime root, where it starts `main.py`.
