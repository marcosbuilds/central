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
operation succeeds. The member remains in the server. A second confirmation is
mandatory, and every successful action uses the configured logs channel.

Management announcements are collected as the next DM message so Discord
Markdown and attachments remain intact. `AllowedMentions.none()` prevents
untrusted message text from notifying users or roles. The published message is
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
return contract and a new ID is recorded.

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
