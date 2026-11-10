# Peace management menu and reserved-ID return flow

Status: accepted and implemented

Decision owner: Peace product and bot maintainers

Date: 2026-11-10

## Outcome

The bot exposes one global `/start` command in direct messages. Its menu is
derived from the caller's current server roles:

- Founder can select `Excluir usuário`;
- Management can select `Avisar`;
- each action rechecks its own role before selection, confirmation, or
  publication.

Deletion is a membership-preserving operational action rather than a kick. It requires
a valid non-founder Peace record, applies or preserves `Not Verified`, removes
only roles below the bot's hierarchy, and releases the ID only after the role
operation succeeds. The member remains in the server and the Peace nickname is
reset. Selection, confirmation, progress, and result states edit the same DM
message; no extra confirmation message is created. Multi-member deletions expose
a bounded textual progress bar and the users already processed in that same
message. A second confirmation is mandatory, and every successful action uses
the configured logs channel.

The operation is serialized per member and the database release is guarded by an
immediate transaction, so repeated clicks converge to one release and one
success log. Startup repairs legacy manual deletions only when the pool reason
identifies that operation and no active member record exists. A later Player set
therefore consumes the released ID and is never removed by the repair pass.

Management announcements are collected as the next DM message so Discord
Markdown and attachments remain intact. `AllowedMentions.none()` prevents
untrusted message text from notifying users or roles. The published message is
a neutral embed card; the first image attachment is used as the card image and
all attachments remain available on the published message. The result is
reported back to the operator and recorded as a log card without copying the
announcement body into the audit channel.

The Founder guard reuses the existing structural migration's Founder role
identity; no second Founder-role environment variable is introduced. Configured
role IDs are validated for uniqueness at startup, and the onboarding roles use
their configured IDs before falling back to their established names.

Members without either internal role receive no denial message from `/start`;
the command is ignored. Approved Player sets send a private welcome embed with
the new Peace ID and the approving member's avatar.

## Reserved-ID lifecycle

The `peace_id_pool` table now keeps an expand-only reason and optional actor
for each reservation/release. A transition from `Peace` to no `Peace`, a
member removal, and startup reconciliation use distinct reasons. A best-effort
audit-log lookup records the actor only when the removed role is observable in a
fresh Discord audit entry; otherwise the card says that the actor was not
identified.

Returning members receive one pending `scan-only` request, created atomically
per member. The card includes the old ID, loss reason, actor when known, and
recorded time. No Player interview is opened. The old ID remains reserved while
the request is pending. If role or nickname application fails during approval,
the local approval is rolled back and the request remains pending. After a
successful approval, the previous ID is released according to the existing
return contract and a new ID is recorded. Approval applies Peace, removes the
entry roles, updates the nickname, and repairs interrupted approved states on
startup before the missing-ID audit. Staff and Management can also reject a
pending return from the same card; the request becomes terminally rejected and
the old ID remains reserved, with no automatic duplicate card.

## Nickname policy

`bot/core/identity.py` is the single prefix policy. Founder receives `F`.
Access roles do not generate prefixes. Only the explicit visual-role allowlist
can generate the existing presentation prefixes `D`, `S`, and `R`; runtime
sync, snapshot import, return approval, and `peace-nick` share the same helper.

## Compatibility and verification

The SQLite changes run through the existing `PeaceDatabase.initialize()`
expand-only migration path. No role or channel is created by `/start`, and the
existing Management role and logs-channel configuration are reused. Synthetic
tests cover role separation, real confirmation, hierarchy-safe deletion,
reason/actor persistence, direct return routing, prefix precedence, and
Player-only set selection.
