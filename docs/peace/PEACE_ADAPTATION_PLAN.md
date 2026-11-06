# Peace adaptation: community + work

## Product decision

Peace remains the same community: social conversation, games together, calls,
support, and tickets. Development work is added as a second function, using the
existing structure and a small number of channels. The server's name, brand, and
identity are not changing.

The governance principle is to separate two things:

- access role: controls a permission or area;
- visual role: organizes the member list and appearance without granting access.

A visual role must never appear in an authorization rule.

## State applied on the server

### Public root

- `rules`: remains at the top and stays public for welcome/rules;
- `spam-control`: public honeypot channel, also at the top;
- `AFK`: visible public call without connection permission, preserving its AFK function.

### Preserved and adapted categories

| Area | Main channels | Usage rule |
| --- | --- | --- |
| `[🎫] RECEPÇÃO` | `boas-vindas`, `regras`, `pedir-set` | entry and initial interview |
| `[💻] DEVELOPERS` | `╰💬・chat-dev`, `╭💻・programming` | technical-team collaboration |
| `[🔔] RESENHA & SOCIAL` | social chats and `música` | community and social life |
| `[☎️] ATENDIMENTO` | panel, waiting room, and support | game, Discord, or work support |
| `[🎙️] CALLS` | four existing calls | shared calls for Peace and development |
| `[🎙️] CALL・PRIVADA` | current private calls | booster benefit, separate from development |
| `[🎟️] TICKETS-FECHADOS` | empty | future archive, invisible to members |
| `[🛡️] STAFF` | `scan-only`, `staff-only`, `logs` | recruiting and internal operations |

Existing IDs were reused whenever that reduced risk. The former Florenza area
was reused internally for `DEVELOPERS`; Peace's public identity did not change.
The chat channel became `╰💬・chat-dev` and the call became
`╭💻・programming`.

## What was removed

- the `[🔫] AÇÃO` category and its model-specific calls;
- accumulated open/closed ticket channels;
- records for those tickets in SQLite, while keeping the database and the
  system's technical history intact;
- the legacy `Florenza Founds` role;
- the legacy `Advertência I`, `Advertência II`, `Advertência III`, and `Sublider` roles;
- public exposure of the old `programming-only` flow as a builder;
- use of `programming-only` as a structural execution channel.

No `Streamer`, booster, Peace, staff, visitor, elite, or bot-integration role was
removed as part of this cleanup. `Gerência` was kept as an organizational role,
but its global permissions were cleared.

## Role matrix

### Technical access

`Dev` is the technical role controlling access to the Developers category. It
was reused from the former `Developer` role, but its broad global permissions
were cleared. Area authorization lives in channel and category overwrites, not
in `Administrator`, `Manage Guild`, `Manage Roles`, or `Manage Channels`.

### Visual identity

The roles below have a visual/organizational purpose and zero global permissions:

- `Developer`;
- `Frontend`;
- `Backend`;
- `Documentation`;
- `AI & Bots` — reserved for AI bots; currently used by the Peace bot.

They may provide color, ordering, and identification. They cannot open channels,
grant roles, moderate, or change the structure.

### Preserved roles

`Peace`, `Novato Peace`, `Staff Peace`, `Gerência`, `Recrutador`, `Elite Peace`,
`Visitante`, `Streamer`, booster, and integration-managed roles were kept.
Future changes to these roles require an inventory of members, permissions, and
dependencies before application.

## Entry and interviews

The `pedir-set` panel now offers three entry points:

1. `Sou player`;
2. `Join Developers`;
3. `Staff — indisponível por hora`.

Members who already have `Peace` cannot request player entry again. The initial
player interview keeps the requested in-game data collection and requires manual
approval.

The developer flow is split into stages:

1. legal first and last name, nickname, and motivation;
2. area: Frontend, Backend, Documentation, or AI & Bots · Íris;
3. specialization time, previous experience, and optional portfolio;
4. send answers to `scan-only`;
5. manual approval or rejection by an authorized recruiter;
6. after approval, select a time on the next business day, between `06:00–13:00`
   or `14:00–00:00` Brasília time;
7. DM with the scheduled time; if the person cannot attend, they are instructed
   to open a ticket.

The flow does not grant a role automatically. Integration happens after the
meeting and the human decision.

### Returning Peace members

When a member leaves with `Peace`, the ID does not immediately return to the
pool: it remains reserved for the account. If the account returns, the bot posts
a card in `scan-only` and does not restore the link automatically. An authorized
recruiter may use `Liberar ID`; this releases the old ID and records a new ID for
the approved return.

In STAFF, `scan-only` is accessible only to `Recrutador`. `staff-only` and `logs`
allow only `Staff Peace` and the bot; `Gerência` has no access.

## Moderation honeypot

The `spam-control` channel publishes a single embed with a visual asset and
scope, action, limit, and status cards. Any message sent by a member is:

1. deleted immediately;
2. recorded in the log without republishing the content;
3. punished with a seven-day timeout, without a ban or kick.

The bot needs `Manage Messages` and `Moderate Members`, and its hierarchy must
allow it to apply the timeout. The channel is a specific layer for accounts that
trigger mass spam; native AutoMod remains a useful complementary layer for
links, mentions, and spam patterns.

The embed and `assets/automod.png` are strict and are not part of the Halloween
rotation. Halloween is limited to lightweight welcome, set, support, and
operations panels.

## Tickets and support

The panel remains in a single channel. Categories must cover both community and
work:

- Community and Discord;
- Work and development;
- Present a project;
- Idea or proposal;
- Privacy or moderation;
- Partnership or private contact.

`Present a project` accepts a game, product, tool, or idea. The ticket is
private; public presentations remain in the social space or in threads when
appropriate. Íris is currently disabled; open tickets are accessible to `Staff
Peace` and follow manual support.

## Bots and integrations

No additional ticket, music, welcome, or moderation bot was added. Peace already
has its own bot, Jockie Music, DutiesBot, Medal, and TimeCord; each must retain a
clear responsibility. The next integration gain should come from native Discord
features and GitHub for pull requests, CI, and releases, only when the team is
ready to operate them.

## Operations and rollback

- `bot/maintenance.py` applies the structural adaptation in dry-run, normal, or
  explicit-cleanup mode;
- `bot/snap.py` creates snapshots in `data/snapshots/`;
- `bot/main.py` keeps panel, ticket, booster, Iris (configuration-disabled),
  honeypot, and interview synchronization;
- any new cleanup must be preceded by a snapshot and validation of IDs, members,
  and overwrites.

In ACLClouds, the production root must not receive loose copies of the code. The
entry point and dependencies remain at the root as required by the provider;
the executable version stays inside a versioned directory and packages go in
`releases/`. Directories such as `__pycache__` and `.deps` are generated by the
environment and may be ignored during tree review.

When joining the server, the bot reconciles `Visitante` for human members
without `Peace`. The routine is idempotent: it does not remove existing roles,
assign `Visitante` to integration bots, or reuse Peace IDs.

The bot must be observed after permission changes. If synchronization fails
partially, correct the exact target and repeat the step; do not recreate the
entire tree.
