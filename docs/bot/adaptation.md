# Peace adaptation: community and development access

This document describes the public product boundary of the companion Discord
bot. It intentionally omits server names, channel identifiers, member data,
provider paths, and operational snapshots.

## Product decision

The community experience remains social: conversation, games, calls, support,
and tickets. Development work is an additional, separately authorized area.
Access roles control permissions; visual roles organize presentation only and
must never appear in an authorization rule.

## Public behavior

- Community entry, rules, and support remain available through the bot's
  configured Discord surfaces.
- Development collaboration is isolated behind the technical access role
  described in [`../integration/peace-central.md`](../integration/peace-central.md).
- Support and operational areas are restricted by explicit role and channel
  overwrites.
- Closed tickets remain unavailable to ordinary members.
- Structural changes are applied idempotently and require a snapshot, a dry
  run, and a reviewable record.

## Technical access

The `Dev` role is the authorization boundary for the development area. Its
global permissions remain narrow; access is granted by explicit Discord
overwrites and then revalidated by the Central integration. A visual label such
as a discipline or bot role does not grant access.

The entry flow is staged:

1. collect only the onboarding fields required by the public contract;
2. route the request to an authorized review surface;
3. approve or reject it manually;
4. issue the development access decision only after review;
5. record the result without exposing private content in public channels.

The flow does not grant privileged access automatically from a message alone.

## Moderation and support

The bot may provide a controlled anti-spam surface, ticket workflows, and a
local support adapter. Message content is not republished as a moderation
response, and support context is redacted before it is sent to a model.

Tickets cover community support and development requests. Private ticket
content remains private; public project presentations belong in public project
spaces or approved threads.

## Data and privacy

- Production snapshots and local SQLite files stay outside Git.
- Tests use synthetic members, channels, messages, and identifiers.
- Tokens, personal identifiers, ticket content, and raw conversations never
  appear in logs, assets, public docs, or Pull Requests.
- The bot's public integration contract is separate from its provider-managed
  runtime configuration.

## Operations and rollback

- `bot/maintenance.py` supports dry-run and explicit cleanup modes.
- `bot/snap.py` creates operator-controlled snapshots.
- `bot/main.py` synchronizes panels, tickets, support, moderation, and
  onboarding according to configuration.
- Any structural change must identify its target, validate hierarchy and
  permissions, and preserve a recoverable snapshot.

Provider-specific roots, release folders, generated directories, and protected
environment values are intentionally not documented here.

## Required evidence

Before a production change is considered complete, verify onboarding, technical
access, ticket restrictions, moderation behavior, persistence, and rollback in
a disposable environment. Summarize behavior and results without publishing
server identifiers or member data.
