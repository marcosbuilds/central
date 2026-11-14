# Integration contract — Peace and Central

Status: implemented locally; the bridge is loopback-only, scoped sessions are
enforced by protected Central operations, and the provider-side identity
exchange remains a separate deployment decision

## Objective

The Peace Discord bot will be Central's entry point. Only a member with the
technical access role `Dev` may initiate release. The user provides their Peace
ID, receives an authentication code by DM, and uses the code to open a short
Central session.

This flow must not reuse the bot token, Discord password, or SQLite database as
a desktop credential.

## Normative flow

1. The Central desktop sends the Peace ID, a generated installation client ID,
   and the optional configured project ID to the bot's loopback bridge.
2. The bot resolves the member's immutable Discord ID and checks the configured
   `Dev` role ID. A visual role name is not authorization.
3. The bot asks for the Peace ID and validates the database relationship under
   the Peace reservation/return rules already documented.
4. The bot creates a random challenge, stores only its hash, associates it with
   the Discord user ID, Peace ID, client, and `central-login` purpose, sets a
   ten-minute expiration, limits five code attempts, and throttles new requests
   per member and client.
5. The bot sends the code by DM. The value does not appear in logs, snapshots,
   tickets, public replies, or Iris prompts.
6. Central sends the code to the authenticated loopback bridge. The bot checks
   one-time use, expiration, attempts, client association, and role state. If
   valid, it issues a random, hashed, thirty-minute session with a subject,
   client binding, and optional project scope; invalid identity responses are
   uniform.
7. Central validates that session before protected project synchronization. The
   existing Supabase session and Syncthing device registration are started only
   after the Central session authorizes the same project. Session revocation,
   expiration, or removal of the `Dev` role blocks the next validation.

## Limits and open decisions

- The local bridge is intentionally not the PythonAnywhere gateway: it binds
  only to HTTP loopback and requires a generated shared key. A remote exchange
  service still needs its own architecture decision before deployment.
- `CENTRAL_BRIDGE_URL` is the single endpoint setting for bot and desktop; it
  must be `http://localhost`, `127.0.0.1`, or `::1`. The key must be a random
  value of at least 32 characters and is never committed.
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
- Protected synchronization revalidates the Central session for the configured
  client and project before starting Supabase or Syncthing operations. Local
  fixture actions are not a substitute for that protected path.

## Planned verification

- a member without `Dev` is denied;
- a Peace ID that does not belong to the member is denied;
- an expired or repeated code, or one attempted above the limit, is denied;
- a valid code creates one short session and cannot be reused;
- revoking the role prevents a new login;
- no secret appears in logs, the local database, a snapshot, or a desktop artifact.

The local implementation is available only when the protected environment
configuration is present. It must not be described as a remote production
identity provider until the provider-side exchange and Supabase identity
binding are separately approved and deployed.
