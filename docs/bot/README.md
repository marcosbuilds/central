# Peace Discord Bot

First slice of the Real Peace bot in Python:

- captures members with the `Peace` role, complete role data, and bot messages;
- persistently assigns Peace IDs in SQLite, reserving `0` for the founder;
- `Request set` flow with nickname, national ID, phone, source, and reviewer selection fields;
- private tickets with `Poke`, closing, renaming, and claiming;
- ticket category selection, private calls, DM notices, and action blocking after closing;
- time tracking, farming logs, and absence requests;
- continuous Iris support using the ticket's recent history;
- preserves the original `custom_id` values `peace_pedir_set_open`, `peace_support_open_ticket`, and `clock_in_btn`.

## Run

```powershell
python -m pip install -e .
python -m bot.commands.snapshot
python -m bot.main
python -m bot.commands.nick --apply
```

The repository keeps the bot source in `bot/`, with `bot/main.py` as its
compatibility entry point. The provider deployment copies the contents of
`bot/` into its runtime root, so its startup command is `python -u main.py` and
there is no `bot/` directory in production. Supporting code remains grouped by
responsibility under `config/`, `core/`, `integrations/`, `persistence/`,
`operations/`, and `commands/` inside that deployment payload.

`snapshot` is read-only against Discord and writes the JSON snapshot to
`data/snapshots/` and the database to `data/`. It does not rename members or
modify roles. The bot applies a role and nickname only after a candidate
completes the set flow and the panel is open.

Player applications are open by default. Set `SET_VAGAS_ABERTAS=false` to close
them. Developer and Staff applications remain closed unless their explicit
flags (`SET_DEVELOPER_VAGAS_ABERTAS` and `SET_STAFF_VAGAS_ABERTAS`) are enabled.
Restart the bot after changing these values.

The persistent welcome, set, verification, support, and operations panels use a
wide banner embed followed by a short explanation card. Their interactive
buttons keep the existing styles and stable component IDs. Availability is
enforced by the configured application paths and select options, while each
card explains what the panel does and why it exists. The set card also keeps
its existing Peace rule, and the verification card explains the CAPTCHA flow.
If `Not Verified` is manually reapplied to an existing `Visitor`, the bot
removes `Visitor`, restores the verification panel, and requires the CAPTCHA
again.

Operational action records are sent as embeds to the channel configured by
`DISCORD_LOG_CHANNEL_ID`. Point, farm, and automatic-moderation records use
vertical fields and include the actor's display avatar when Discord provides
one. Runtime diagnostics remain application logs and are not copied into the
server channel.

Human members enter with the visual `Not Verified` role. The bot exposes one
verification channel, `verify`, only to that role; its persistent panel starts
a short CAPTCHA image, and only a correct selection grants `Visitor` while
removing `Not Verified`. A wrong or expired selection does not grant access and
returns the member to the start button for another attempt. Bots and members
with `Peace` never receive `Visitor` from this flow. A manually approved set
grants `Peace` and the visual `Intern` role, with no global permissions on the
latter.

The bot does not create or edit channel permission overwrites. Channel and
category permissions are operator-managed; the verification panel only edits
its own messages in the already configured channel.

Members without an access role cannot see the server structure. After
verification, `Visitor` can read `rules`, use `visitor-chat`, access `SUPPORT`,
and see `AFK` without connecting. `spam-control` is private to the bot and is
not a human-access channel.

The visible Discord structure uses English names. The maintained categories
are `RECEPTION`, `DEVELOPERS`, `RECORDS`, `SOCIAL LOUNGE`, `SUPPORT`, `CALLS`,
`PRIVATE CALLS`, `STAFF`, `VERIFICATION`, and `CLOSED TICKETS`; visual role
labels are also English and do not grant authorization.

The structural migration can create the verification surface, normalize role
names, save an ignored local role-membership snapshot, clear visual-role
permissions, and remove the requested legacy roles. Use
`python -m bot.operations.maintenance --apply --remove-chat-elite` only after
reviewing the dry run. The `--remove-chat-elite` flag is intentionally explicit
because channel deletion is irreversible.

The Central bridge is optional at startup but, when enabled, requires an
explicit `DISCORD_CENTRAL_ACCESS_ROLE_ID`, a loopback-only
`CENTRAL_BRIDGE_URL`, and a randomly generated `CENTRAL_BRIDGE_KEY` of at least
32 characters. Never commit that key. The desktop receives a one-time DM code,
then a short session bound to its installation client and configured project.

Iris support uses a local model. Keep the service available at `IRIS_URL` before
starting the bot. Iris builds context from ticket data and recent messages;
this is local context retrieval, not a change to the model weights.

The model service is operator-configured and must remain outside the public
repository. Choose a local model profile appropriate for the machine and keep
its storage path, port, and runtime options in environment variables:

```powershell
$env:OLLAMA_MODELS = "<local-model-directory>"
$env:OLLAMA_HOST = "127.0.0.1:<local-port>"
$env:OLLAMA_LLM_LIBRARY = "<local-library>"
ollama serve
```

The sanitized interaction notes are in
[`interactions.md`](interactions.md).

The tree organization and rules for not committing clutter or local data are in
[`AGENTS.md`](AGENTS.md) and
[`organization.md`](organization.md). New snapshots are written
to `data/snapshots/`; the current SQLite database remains at
`data/peace.sqlite3` until an explicit migration.

The code and server inventory is in
[`inventory.md`](inventory.md), and the public adaptation boundary is in
[`adaptation.md`](adaptation.md).

Iris's operational policy and privacy boundary are in [`iris.md`](iris.md). It
uses management, chat, and previous-ticket information as controlled context,
but does not store raw conversations as memory or reveal internal content to the
requester.

`bot.commands.nick` changes only the final ID portion of existing nicknames and preserves
the in-game name. It automatically skips the server owner and members above the
bot's hierarchy; roles are not removed or added by this migration.
