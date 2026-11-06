# Public interaction inventory

This document records only the interaction families required to understand the
bot source. Raw Discord snapshots, channel identifiers, member identifiers,
message payloads, and local database contents are intentionally excluded from
the public repository.

## Interaction families

- member onboarding and request submission;
- approval and status notices;
- support ticket creation, claim, rename, close, and call creation;
- attendance and activity records;
- absence requests and operational notices;
- controlled support responses from the local Iris adapter.

## Contract rule

The implementation preserves stable component identifiers only when they are
part of the public bot contract. A real server snapshot must stay in an
operator-controlled, ignored location and must never be copied into Git,
issues, logs, or review comments.

## Public evidence boundary

Tests should use synthetic members, channels, messages, and identifiers. Any
production observation must be summarized at the behavior level, with personal
data, Discord identifiers, ticket content, and raw message text removed.
