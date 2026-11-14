# Peace public learning and selection surfaces

Status: accepted and implemented for the public learning and selection flow.
Production credentials and the answer key remain provider-managed secrets; the
role and selection rules below are delivered permission boundaries.

## Decision

The public Peace site will expose a small learning library and a candidate
tracking surface without requiring a visitor to be a Peace member or to open
the authenticated member area.

The first public routes are:

- `/estudos/` — library landing page;
- `/estudos/civil/` — Civil study material;
- `/estudos/peace/` — Peace convivencia manual;
- `/meu-processo/` — candidate-owned process shell.

Both study pages are web-native reading surfaces backed by page-rendered image
assets from the supplied PDFs. The original PDFs are not published or offered
as downloads; the reader exposes a cover, outline, page navigation, and bounded
page explanations.

## Authorization boundary

Study pages are public. Candidate process data is private to the authenticated
Discord identity and must not be rendered by a static page before a real
backend session exists. The candidate-facing shell therefore shows the
planned states without synthetic grades, attempts, deadlines, or approvals.

Only the Gerência role may create, assign, revoke, or grade an exam.
Authorization is enforced server-side using the configured stable Discord role
ID and fails closed. Staff, candidate-facing sessions, and frontend-only
controls are not treated as permission to generate an exam.

The candidate flow uses Discord OAuth identity, compares the authenticated
Discord ID with the assignment, and shows only records owned by that ID. A
username is a display snapshot, not an authorization key.

## Role policy

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

## Delivered integration

The public backend now delivers OAuth2 Authorization Code + PKCE with a
consumed state, protected cookies, persistent candidate/assignment/attempt/
event records, Gerência-only assignment creation, deadline enforcement,
server-side grading, per-attempt question and option order, and one definitive
submission per candidate assignment. The assignment URL is individualized and
stores only a hash server-side; reloading resumes the same in-progress attempt
and never creates a second attempt.

## Selection flow

1. A manager authenticates with Discord and the server verifies the current
   `Gerência` role by stable ID. A frontend-only button or an old role snapshot
   is never enough.
2. The manager selects the immutable Civil question-bank version, the target
   Discord user ID, the visible username snapshot, and an absolute deadline in
   UTC. The username is displayed for recognition and audit only.
3. The server creates one assignment per candidate Discord ID, generates a
   high-entropy opaque token, stores only its hash, and publishes an
   individualized link scoped to that assignment. The URL does not contain the
   raw Discord ID or answer data.
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

## Discord developer setup

The Discord developer application uses the exact production callback
`https://peacegg.com.br/api/auth/discord/callback`. The candidate flow requests
only the minimum `identify` scope. The bot/API verifies the manager's role
using its configured guild and role IDs; it does not ask candidates for
`guilds`, `guilds.join`, or `guilds.members.read` just to prove identity.

The callback is also registered in the Discord Developer Portal, and the
rotated client secret is stored only in the local ignored `.env` and the
ACLClouds provider environment. It must never be copied into the repository,
logs, screenshots, or issue/PR text.

The public edge and ACLClouds origin use HTTPS for the authenticated callback
and cookie flow. The local preview keeps a fixed HTTPS ACL origin and forwards
only the allowlisted OAuth and exam routes.

## Verification contract

The public shell has route coverage in the local server and route tests,
keyboard-visible focus, responsive reflow, truthful error states, and no
private PDF or answer key in `bot/site`. Browser review is required at compact
and desktop widths before each public release. Production smoke tests must
confirm the OAuth start/callback/session/logout contract and the 401/403
boundaries for candidate and manager routes.
