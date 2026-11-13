# Peace bot public inventory

This inventory describes the committed code and its public boundaries. Server
names, Discord identifiers, member counts, provider paths, snapshots, and
credentials are intentionally omitted.

## Code and entry points

| File | Responsibility | State |
| --- | --- | --- |
| `bot/main.py` | repository entry point; provider receives it as `main.py` | active |
| `bot/operations/maintenance.py` | idempotent structural migration and explicit cleanup | operational utility |
| `bot/persistence/database.py` | SQLite access, tickets, events, onboarding, and requests | active |
| `bot/config/settings.py` | environment configuration | active |
| `bot/core/identity.py` | shared access/visual nickname prefix policy | active |
| `bot/integrations/iris.py` | local support adapter and prompts | available; configuration-controlled |
| `bot/core/context.py` | redaction, limits, and sanitization | active |
| `bot/integrations/discord_api.py` | REST used by utilities | active |
| `bot/commands/snapshot.py` | read-only snapshot utility | active |
| `bot/commands/nick.py` | reviewed nickname utility | restricted |

## Applied behavior

- community entry and rules remain separate from technical collaboration;
- the technical access role is checked by explicit permission overwrites;
- support and moderation panels use one responsibility per workflow;
- closed tickets remain hidden from ordinary members;
- structural changes are idempotent and require a recoverable snapshot;
- visual roles do not participate in authorization;
- Human members receive `Not Verified` on join; `Visitante` is granted only by
  the verification CAPTCHA and is never granted on member join;
- approved sets receive `Peace` and the visual `Estagiário` label, which has no
  permission authority;
- role migration snapshots affected members before deleting obsolete roles;
- the maintained technical roles are `Developer` and `Dev`; obsolete
  `Frontend`, `Backend`, and `Documentation` roles are removed, as is the
  obsolete `Superintendente` role;
- `request-set` is not a Discord surface; applications start at the official
  site candidature route;
- `logs` and `scan-only` reject human message sending and are written by the
  bot;
- provider credentials remain in protected environment configuration.
- `/start` is a DM-only operational menu with separate Founder deletion and
  Management announcement guards;
- Request set is site-owned; Discord does not recreate a public set panel;
- Peace-ID loss records preserve a reservation reason and optional actor, and
  returning members are routed directly to `scan-only`;
- the nickname prefix policy is centralized so access roles cannot acquire
  presentation prefixes accidentally.
- the Central bridge stores only challenge and session hashes; the Discord
  access role is rechecked before issuing or validating a session.

## Data boundary

SQLite and snapshot output are local runtime state and are ignored by Git.
Onboarding and ticket fields are processed only as required by the configured
workflow. Personal identifiers, ticket content, raw messages, tokens, and
provider secrets must not appear in logs, tests, assets, documentation, or Pull
Requests.

The database retains compatibility tables only when a migration requires them.
Schema cleanup requires its own migration, backup, rollback path, and review.

## Audit and security

- authorization checks use access roles, not visual labels;
- moderation records only the minimum data required for audit;
- support context is redacted before model use;
- a role or permission change requires a target, hierarchy check, snapshot, and
  negative test;
- partial synchronization is corrected at the exact target rather than by
  recreating the whole structure.

## Provider boundary

The production host is provider-managed. Its protected token field, launcher,
release layout, generated directories, and rollback packages are not part of
the public source-of-truth tree and are not described with live paths here.

## Next checks

1. run synthetic onboarding and developer-access simulations;
2. verify the anti-spam flow with a disposable test account;
3. assert that each configured panel has one active instance;
4. review effective permissions for technical, staff, and recruiting roles;
5. keep persistence, migration, and negative authorization tests green.
