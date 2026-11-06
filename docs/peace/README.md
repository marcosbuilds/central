# Peace Discord Bot

First slice of the Real Peace bot in Python:

- captures members with the `Peace` role, complete role data, and bot messages;
- persistently assigns Peace IDs in SQLite, reserving `0` for the founder;
- `Request set` flow with nickname, national ID, phone, source, and recruiter modal fields;
- private tickets with `Poke`, closing, renaming, and claiming;
- ticket category selection, private calls, DM notices, and action blocking after closing;
- time tracking, farming logs, and absence requests;
- continuous Iris support using the ticket's recent history;
- preserves the original `custom_id` values `peace_pedir_set_open`, `peace_support_open_ticket`, and `clock_in_btn`.

## Run

```powershell
python -m pip install -e .
python -m bot.snap
python -m bot.main
python -m bot.nick --apply
```

`snapshot` is read-only against Discord and writes the JSON snapshot to
`data/snapshots/` and the database to `data/`. It does not rename members or
modify roles. The bot applies a role and nickname only after a candidate
completes the set flow and the panel is open.

To open applications, set `SET_VAGAS_ABERTAS=true` in `.env` and restart the
bot. The existing server panel remains closed while the value is `false`.

Iris support uses a local model. Keep the service available at `IRIS_URL` before
starting the bot. Iris builds context from ticket data and recent messages;
this is local context retrieval, not a change to the model weights.

In the current environment, the service uses storage at `D:\Ollama\Models`, port
`11435`, and the `iris-peace` profile, which was validated on the available
hardware. On a smaller machine, `iris-peace-micro` remains available as a lower-
resource alternative:

```powershell
$env:OLLAMA_MODELS = "D:\Ollama\Models"
$env:OLLAMA_HOST = "127.0.0.1:11435"
$env:OLLAMA_LLM_LIBRARY = "cpu_avx2"
ollama serve
```

The catalog of observed messages is in
[`RECOVERED_MESSAGES.md`](RECOVERED_MESSAGES.md).

The tree organization and rules for not committing clutter or local data are in
[`AGENTS.md`](AGENTS.md) and
[`PROJECT_ORGANIZATION.md`](PROJECT_ORGANIZATION.md). New snapshots are written
to `data/snapshots/`; the current SQLite database remains at
`data/peace.sqlite3` until an explicit migration.

The code and server inventory is in
[`PEACE_SYSTEM_INVENTORY.md`](PEACE_SYSTEM_INVENTORY.md), and the proposal to
adapt Peace without changing its identity is in
[`PEACE_ADAPTATION_PLAN.md`](PEACE_ADAPTATION_PLAN.md).

Iris's operational policy and privacy boundary are in [`IRIS.md`](IRIS.md). It
uses management, chat, and previous-ticket information as controlled context,
but does not store raw conversations as memory or reveal internal content to the
requester.

`bot.nick` changes only the final ID portion of existing nicknames and preserves
the in-game name. It automatically skips the server owner and members above the
bot's hierarchy; roles are not removed or added by this migration.
