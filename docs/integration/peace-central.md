# Integration contract — Peace and Central

Status: contract documented; code-exchange implementation is still pending

## Objective

The Peace Discord bot will be Central's entry point. Only a member with the
technical access role `Dev` may initiate release. The user provides their Peace
ID, receives an authentication code by DM, and uses the code to open a short
Central session.

This flow must not reuse the bot token, Discord password, or SQLite database as
a desktop credential.

## Normative flow

1. The member requests access through the bot's official command/panel. The exact
   command name remains a UX decision and must not be invented in code yet.
2. The bot resolves the member's immutable Discord ID and checks the configured
   `Dev` role ID. A visual role name is not authorization.
3. The bot asks for the Peace ID and validates the database relationship under
   the Peace reservation/return rules already documented.
4. An authentication service creates a random challenge, stores only its hash,
   associates it with the Discord user ID, Peace ID, client, and
   `central-login` purpose, sets a short expiration, and limits attempts.
5. The bot sends the code by DM. The value does not appear in logs, snapshots,
   tickets, public replies, or Iris prompts.
6. Central sends the code over HTTPS to the authentication service. The service
   checks one-time use, expiration, attempts, purpose, and association. If
   valid, it issues a short session with project scope; if invalid, it denies
   without revealing whether the ID or code was the problem.
7. Central uses the short session to authenticate with Supabase and register the
   Syncthing Device ID. Role or session revocation invalidates new connections.

## Limits and open decisions

- The implementation must choose between a Supabase Edge Function and a
  dedicated service for the exchange endpoint; the current PythonAnywhere
  gateway is health-only and is not authorized to assume this role.
- The final command/panel form, expiration time, and attempt limit must be
  approved before coding.
- Supabase must receive a verifiable identity and must not trust a client-entered
  `peace_id` without proof issued by the bot.
- The flow must support revocation, minimal audit, and recovery from blocked DMs
  without showing the code in a public channel.

## Security invariants

- The `Dev` role is checked on the Discord server using the stable role and member IDs.
- The desktop never receives the bot token, service-role key, or SQLite database.
- The code is a transient, one-time credential with an at-rest hash, expiration,
  rate limit, and invalidation after success.
- IP address, machine name, and Discord display name are not sufficient identity.
- Partial failure never grants access: a DM sent without a persisted challenge,
  expired challenge, revoked session, or Supabase error results in denial.

## Planned verification

- a member without `Dev` is denied;
- a Peace ID that does not belong to the member is denied;
- an expired or repeated code, or one attempted above the limit, is denied;
- a valid code creates one short session and cannot be reused;
- revoking the role prevents a new login;
- no secret appears in logs, the local database, a snapshot, or a desktop artifact.

Until these tests exist, the integration must be treated as planning, not as an
available Central capability.
