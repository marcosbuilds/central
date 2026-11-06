# Registration, identity, permissions, and security

## Entry requirement

Central uses invitation/approval-controlled registration, Discord linking, and
server release. It is not a public registration that grants access merely by
submitting a form.

## Proposed flow (with consent)

1. An administrator creates an individual invitation limited by validity, use,
   and, when appropriate, invited email.
2. The person accesses Central and authenticates with **Discord OAuth2**
   (Authorization Code; use `state` against forgery, PKCE when applicable to the
   client, and secure session storage).
3. Central reads Discord identity with `identify` scope and verifies the
   invitation. If needed, it checks server association with `guilds.members.read`
   consent or an authorized bot.
4. The record is `pending_approval`, with no project access.
5. An administrator reviews, selects role and allowed projects, and approves.
6. The bot applies the server role. If the person is not in the server, offer an
   invitation; optionally use `guilds.join` **only with explicit authorization**
   and API prerequisites.
7. Confirm and audit. If Discord fails, state becomes `pending_discord_sync` for
   retry; never assume success.
8. On suspension or deactivation, Central revokes tokens/sessions; the bot tries
   to remove Discord roles/access and records failures for correction.

**Discord is not the primary permission database.** It may synchronize roles, but
real access is validated in Central on every request. Do not show another
client's documents merely because a user entered a channel.

## Roles and project control

| Role | Read project | Change code in reserved area | Approve code | Production | Manage users |
|---|---|---|---|---|---|
| Developer member | per project | yes, with validated reservation | peer review when authorized | no | no |
| Documenter/product | per project | documents/architecture by reservation | scope/requirements | no | no |
| QA | per project | tests by reservation | validates tests/criteria | no | no |
| Technical lead | per project | yes | yes, independently | with second control | not necessarily |
| Infrastructure/operator | per project | infrastructure by reservation | infrastructure approval | authorized execution | not necessarily |
| Administrator | authorized projects | not automatically | not automatically | not automatically | yes |
| AI agent | token-restricted | scoped operations only | **not as sole final approval** | **never through default token** | no |
| Future external client | released deliverables only | no | business acceptance | no | no |

Apply **RBAC + project permissions + task/resource conditions**. Platform
administrator status must not authorize modifying client code without a record and review.

## Tokens and sessions

- Short API tokens by scope/project, with stored hash, expiration, rotation, and use limit.
- Browser session in `HttpOnly`, `Secure`, appropriately `SameSite` cookie;
  CSRF protection when applicable; TLS required.
- Distinguish `member`, `device`, `agent_session`, `service_account`, and `deploy_identity`.
- Service keys, Discord bot token, and client data belong in a secret manager,
  not in the repository or ZIP.
- 2FA/passkeys for critical Central actions are strongly recommended; a Discord
  session alone is not sufficient production assurance.
- Sensitive audit records include author, time, security IP when necessary,
  summarized before/after, and reason; document retention period.

## Abuse protection

- Stolen invitation, Discord account swap, and server removal require verification/revocation.
- Bots and users see only released projects; limit access between clients.
- Rate limits and brute-force protection, webhook/signature validation, Markdown
  and comment sanitization, and ZIP upload isolation against `../`, zip bombs,
  and unexpected executables.
- Scan and block secrets accidentally added to code before publication.
- The AI client may execute commands only in a limited sandbox; destructive
  operations and network/secret access require appropriate consent.
- Tell the team and clients what data enters third-party tools; meet applicable
  contractual and legal requirements, including LGPD.

## Acceptance conditions

A person without approval cannot open a workspace; a member of project A cannot
access B; a revoked token fails immediately; a bot without access cannot create a
fictional approval; a change outside a reservation is denied; production deploy
requires human permission and an approved snapshot.

## Addendum — multiple projects, freezing, and delegated review

- An AI session receives only the list of projects the member **already may
  access**, even when the token enables discovery of multiple projects. Other
  clients' data remains invisible.
- Write operations require `project.state=OPEN`, authorization at execution
  time, a valid reservation, and current base revision. A close command invalidates
  write grants and blocks even previously issued tokens.
- Closing/reopening requires an authorized role, recorded reason, and atomic
  transition. Closing does not delete history or discussions.
- `review.propose` does not grant `review.approve`. AI approval occurs only with
  specific delegated authorization for project/risk. Central keeps evidence, AI
  identity, owner, exact reviewed hash, and applied policy.
- Independent approver: a person/AI cannot approve its own batch or use a second
  identity from the same author to simulate independence. A later change
  invalidates approval for that hash.
- Code-integration approval does not grant deployment permission; production
  publication requires its own role, environment rules, and tests.
- Do not expose secrets, personal data, or private content in agent messages or telemetry.
