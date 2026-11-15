# Decision — local Peace-to-Central authentication exchange

Date: 2026-11-06  
Status: accepted for local integration; provider identity binding deferred  
Owner: Central Colaborativa

## Decision

The first Peace-to-Central exchange runs only between the Discord bot and the
Central desktop on the same machine. The desktop sends a Peace ID and a
persistent installation client ID to a loopback HTTP bridge. The bot checks the
member-to-Peace relationship and the configured technical access role, sends a
single-use six-digit code by Discord DM, and never returns the code in the
bridge response.

A successful code check creates a random, hashed, thirty-minute session bound to
the client and optional project. Central must revalidate that session before
starting Supabase authentication, device registration, or Syncthing project
operations. Closing the desktop revokes the session; expiration, revocation, or
removal of the access role denies the next validation.

## Security boundaries

- The bridge binds only to `CENTRAL_BRIDGE_URL` on HTTP loopback.
- The shared bridge key is explicit, randomly generated, at least 32
  characters, rejected when it is a placeholder, and never committed.
- Challenge and session values are stored as salted hashes; cleartext codes are
  not logged or returned by the API.
- New requests are throttled per member and per installation client. Invalid
  identity responses are uniform so the API does not disclose whether a Peace
  ID exists or merely lacks the access role.
- The desktop rejects remote or missing bridge URLs, refuses redirects, and
  accepts a session only when its client, project, Peace ID, and scope match the
  request.

## Deferred decision

This local exchange is not the PythonAnywhere gateway and does not establish a
remote provider identity. A future remote exchange must separately define the
authenticated service boundary, Supabase subject mapping, rotation, and
deployment controls before replacing the loopback bridge.

## Verification

The Python suite covers endpoint authorization, uniform identity denial,
request throttling, code expiration and attempt exhaustion, single-use
challenges, session issuance and revocation, role revalidation, and secret
redaction. The .NET suite covers loopback configuration, redirect-safe client
behavior, session binding, and protected project scope.
