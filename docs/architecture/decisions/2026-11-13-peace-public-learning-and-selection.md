# Peace public learning and selection surfaces

Status: accepted for the public shell; Discord OAuth, persistence, and exam
generation remain deferred. The role and selection rules below are a planned
contract, not a delivered permission boundary.

## Decision

The public Peace site will expose a small learning library and a candidate
tracking surface without requiring a visitor to be a Peace member or to open
the authenticated member area.

The first public routes are:

- `/estudos/` — library landing page;
- `/estudos/civil/` — Civil study material;
- `/estudos/peace/` — Peace convivencia manual;
- `/meu-processo/` — candidate-owned process shell.

Both study pages are web-native reading surfaces with an explicit placeholder
for the source PDF. Until the team publishes a file, the UI must say that the
PDF is in preparation and must not imply that incomplete copy is an official
rule or exam requirement.

## Authorization boundary

Study pages are public. Candidate process data is private to the authenticated
Discord identity and must not be rendered by a static page before a real
backend session exists. The candidate-facing shell therefore shows the
planned states without synthetic grades, attempts, deadlines, or approvals.

When the selection backend is implemented, only the Gerência role may create,
assign, revoke, or grade an exam. Authorization must be enforced server-side
using a stable Discord role ID and must fail closed. Staff, candidate-facing
sessions, and frontend-only controls must not be treated as permission to
generate an exam.

The future candidate flow will use Discord OAuth identity, compare the
authenticated Discord ID with the assignment, and show only records owned by
that ID. A username is a display snapshot, not an authorization key.

## Role policy (planned)

The first release should use the existing `Gerência` role as the single
authority for exam mutations. The backend must check the configured stable role
ID (`DISCORD_MANAGER_ROLE_ID`) on every manager mutation and fail closed when
the guild, member, role, or hierarchy check is unavailable.

| Role or identity | Planned capability | Authority boundary |
| --- | --- | --- |
| `Gerência` | Generate, assign, revoke, publish, and correct exams | The only identity allowed to mutate exam records |
| `Recrutador` (optional later role) | Read assigned candidates and coordinate the next step | Must not generate, publish, revoke, or correct an exam unless a later decision explicitly expands the policy |
| `Aluno` | Receive the role after an approved set request | Outcome/access role; never an exam-authority role |
| Candidate Discord identity | Authenticate, start an assigned attempt, submit it, and read its own result | Bound to the authenticated Discord user ID; no Peace membership required |
| Anonymous visitor | Read the public study materials | No process, exam, answer, or result data |

The current server observation showed `Gerência` and `Aluno` roles, but no
selection-specific `Recrutador` role. This is unverified external state and is
not a substitute for storing the role IDs in provider configuration. No Discord
role, application, or permission was changed for this decision.

## Deferred integration

The following are intentionally deferred until the backend contract and
production transport are ready:

- OAuth2 Authorization Code + PKCE, state validation, and secure cookies;
- persistent candidate, assignment, attempt, answer, and event records;
- opaque expiring one-use proof links stored as hashes;
- Gerência-only exam generation and result correction;
- question-bank versioning with materialized per-attempt order;
- set request and bot-mediated cargo changes.

## Future selection flow (planned)

1. A manager authenticates with Discord and the server verifies the current
   `Gerência` role by stable ID. A frontend-only button or an old role snapshot
   is never enough.
2. The manager selects the immutable Civil question-bank version, the target
   Discord user ID, the visible username snapshot, and an absolute deadline in
   UTC. The username is displayed for recognition and audit only.
3. The server creates a draft assignment, generates a high-entropy opaque
   token, stores only its hash, and publishes a revocable one-use link scoped to
   that assignment. The URL must not contain the raw Discord ID or answer data.
4. The candidate opens the link and authenticates with Discord OAuth2. The
   server compares the authenticated user ID with the assignment before
   consuming the link or starting an attempt. A non-member can authenticate;
   guild membership is not a candidate prerequisite.
5. The server materializes the same question set for every attempt from the
   selected bank version, but applies a server-generated per-attempt order (and
   option order where applicable). The seed/order is stored for audit and is
   never accepted from the browser. Two simultaneous candidates therefore see
   different orderings without changing the contents of the exam.
6. The server enforces the deadline for both start and submit. After submission,
   the result remains private to the candidate and authorized staff, with an
   append-only audit event for the assignment, attempt, actor, timestamp, and
   outcome. Raw tokens and answer keys do not enter public logs.
7. After approval, the candidate explicitly requests the set. The bot performs
   the role change only after the server verifies the approved state, role
   hierarchy, idempotency, and an auditable actor/event. The `Aluno` role is
   not granted merely because the candidate opened a link or saw a score.

## Discord developer setup (deferred)

The Discord developer application must have an exact production callback before
OAuth can be enabled, for example
`https://public.example/auth/discord/callback`, plus a local callback kept out
of production configuration. The candidate flow needs only the minimum
`identify` scope. The bot/API verifies the manager's role using its configured
guild and role IDs; it must not ask candidates for `guilds`, `guilds.join`, or
`guilds.members.read` just to prove identity.

The current developer portal has no redirect URI configured for this flow and
no OAuth scope selected. This is a read-only observation from 2026-11-13; the
settings remain unchanged until the HTTPS backend, callback, session contract,
and privacy copy are reviewed together.

The current deployment documentation identifies an HTTP ACL upstream. The
future authenticated selection flow must not be released through that
boundary without HTTPS or an equivalent private transport boundary.

## Verification contract

The public shell must have route coverage in the local server and route tests,
keyboard-visible focus, responsive reflow, honest empty/pending states, and no
private PDF or answer key in `bot/site`. Browser review is required at compact
and desktop widths before the OAuth or selection backend is enabled.
