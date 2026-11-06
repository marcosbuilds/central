# Updated Peace inventory

This inventory records the code state and the adaptation applied in Discord
Development on November 2, 2026. Complete snapshots live in
`data/snapshots/` and are not source code.

## Code and entry points

| File | Responsibility | State |
| --- | --- | --- |
| `bot/main.py` | gateway, views, panels, tickets, interviews, boosters, and Iris | active |
| `bot/maintenance.py` | idempotent structural migration and explicit cleanup | new operational utility |
| `bot/db.py` | SQLite, tickets, events, set flow, and developer requests | active |
| `bot/cfg.py` | `.env` configuration | active |
| `bot/ai.py` | Iris client and prompts | available in code; AI support disabled by `IRIS_ENABLED=false` |
| `bot/context.py` | redaction, limits, and sanitization | active |
| `bot/api.py` | REST used by utilities | active |
| `bot/snap.py` | read-only snapshot | active |
| `bot/nick.py` | nickname utility | use only after review |

## Final applied state

- server preserved as `REAL PEACE IS BACK`;
- `programming-only` stopped being a structural execution area and became the
  public `spam-control` channel;
- `rules` remained at the top;
- AFK moved to the top as a visible public call without connection permission;
- category `[🤝] FLORENZA & PEACE` became `[💻] DEVELOPERS`;
- `chat-tie` became `chat-dev`;
- `Call` became `╭💻・programming`;
- `[🎙️] CALL・PEACE` became `[🎙️] CALLS`, accessible to Peace, development, and
  staff;
- `[🛡️] STAFF` received `scan-only`, `staff-only`, and `logs`, in that order;
- `scan-only` became exclusive to `Recrutador`; `staff-only` and `logs` became
  exclusive to `Staff Peace`;
- the ticket panel remained in `[☎️] ATENDIMENTO`;
- `[🎟️] TICKETS-FECHADOS` remains empty, reserved for the archive and invisible;
- open tickets are accessible to `Staff Peace`, without automatic triage by Íris;
- `[🔫] AÇÃO` and its calls were removed;
- old `sup-*` tickets were cleaned from Discord and SQLite;
- the `Florenza Founds` role was removed through the Discord owner interface
  after the access migration;
- the `Advertência I`, `Advertência II`, `Advertência III`, and `Sublider` roles
  were removed through authorized maintenance.

## Roles

| Role | Type | Rule |
| --- | --- | --- |
| `Dev` | technical access | access to the Developers category; global permissions cleared |
| `Developer` | visual | identification, no access |
| `Frontend` | visual | identification, no access |
| `Backend` | visual | identification, no access |
| `Documentation` | visual | identification, no access |
| `AI & Bots` | visual | AI bots only; no access by itself |
| `Peace` | existing membership/access | preserved |
| `Novato Peace` | progression | preserved |
| `Staff Peace` | operational access | preserved |
| `Gerência` | organization/hierarchy | preserved, global permissions cleared; access only through explicit channels |
| `Recrutador` | approval | preserved |
| `Elite Peace` | specific access | preserved |
| `Visitante` | entry access | preserved |
| `Streamer` | identity/benefit | preserved |
| booster and managed roles | integration | preserved |

The old `Developer` role was not kept with dangerous permissions: it was reused
by ID as `Dev`, and its global permissions were removed. Visual identity lives in
separate roles.

## Local database

SQLite remains at `data/peace.sqlite3` for compatibility. The
`developer_requests` table records the new staged flow; national ID and phone
belong to the in-game player flow and must not be reused for the developer process.

The old `builder_objects` tables remain only for schema compatibility. The
builder is not exposed in a channel or in `on_message`; schema cleanup may occur
only in its own migration with backup and rollback.

`peace_id_pool` now distinguishes available IDs from reserved IDs. When an
account leaves with `Peace`, the ID stays reserved; when the account returns,
the request appears in `scan-only` with the `Liberar ID` button. Approval
releases the old ID and creates a new one for the account, avoiding silent reuse.

## Audit and security

- `developer_requests` is published only in `scan-only`;
- developer approval is limited to `Recrutador` with access to `scan-only`;
- approval does not grant a role automatically;
- `spam-control` removes the message, applies a seven-day timeout, and records
  only what is necessary in the log;
- visual roles do not appear in authorization guards;
- `scan-only` is accessible only to recruiters; `staff-only` and `logs` only to
  `Staff Peace`;
- Developers channels accept `Dev` and `Staff Peace`; Gerência has no override;
- `assets/automod.png` and `spam-control` content do not participate in the
  Halloween visual rotation;
- closed tickets remain hidden from ordinary members;
- any future structural change must have a target, hierarchy, snapshot, and record.

## Production on ACLClouds

The service root keeps only the items required to start the application:

- `bot.py`: hosting-compatible launcher;
- `requirements.txt`: dependencies installed by the provider;
- `peace-deploy-20261102-0606/`: published version containing `bot/`, `assets/`,
  and `docs/`;
- `releases/`: distribution and rollback packages, outside the execution path.

`__pycache__/` and `.deps/` are directories generated by ACLClouds and are not
part of the source of truth. The token remains only in the provider's protected
field; it must never be placed inside the published tree.

During the November 2, 2026 audit, every human member already had at least one
custom role. The bot also keeps `Visitante` reconciliation in `on_member_join`
and `on_ready`: a human member without `Peace` receives `Visitante`, and a member
approved as `Peace` stops being a visitor.

## Next checks

1. verify a player interview and a developer simulation on the real server;
2. test the honeypot with a test account that can receive a timeout;
3. validate that the bot keeps only one panel in `boas-vindas` and one in
   `spam-control`;
4. review effective permissions for `Gerência`, `Staff Peace`, and `Recrutador`;
5. add automated tests for permissions, migrations, and persistence.
