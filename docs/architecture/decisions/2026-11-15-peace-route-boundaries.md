# Peace route boundaries and public navigation

Status: accepted and implemented locally; production publication remains
pending.

Decision owner: Peace public-site implementation

## Decision

The site has three authorization surfaces. A static page being reachable does
not grant access to private data or an operation; every private API and
mutation repeats the server-side check.

| Surface | Routes | Required authority |
| --- | --- | --- |
| Public content and entry | `/`, `/estudos/`, `/estudos/civil/`, `/estudos/peace/`, both readers, `/avisos/`, `/parceiros/`, `/clipes/`, `/entrar/`, `/candidatura/`, `/acessar/` | None to read the page; Discord identity only where an action or private response needs it |
| Candidate-owned data | `/meu-processo/`, `/prova/` and their APIs | Authenticated Discord identity; records are filtered by Discord ID |
| Peace workspace | `/area/` and `/api/peace/process` | Authenticated Discord identity, live Peace role, complete profile and process response |
| Management | `/gerencia/provas/` and assignment mutations | Authenticated Discord identity with the configured Gerência role |

The frontend can show a gate or hide a menu entry for clarity, but that is not
an authorization boundary. The backend remains authoritative for role,
identity, ownership, and mutation checks.

## Navigation contract

The Peace workspace sidebar uses real route URLs instead of `#`-based session
fragments. Its destinations are:

- `/area/` — overview and the authenticated Peace shell;
- `/estudos/` — public study library;
- `/avisos/` — public announcements with a notification bell and toast;
- `/parceiros/` — public partner directory;
- `/clipes/` — public clip feed with search, source-safe playback, and Peace-only likes/comments;
- `/meu-processo/` — candidate-owned process and exam history.

On wide screens the rail is sticky within the workspace layout and reserves
enough width for labels and the connected profile. On compact screens it is a
drawer that pushes the content, marks the closed rail `inert`, moves focus into
the open menu, and restores focus to the toggle after close or `Escape`.

Public pages do not render the full public header. They use a contextual bar
with a history-aware return link on the left and the shared Discord identity
control on the right. A connected Peace account can open `/area/`; an
unauthenticated or non-Peace account receives the appropriate gate when the
panel performs its server-side validation.

## State and loading rules

The `/area/` shell starts with structural skeletons. It reveals the workspace
only after the same-origin Discord session, official identity/avatar, live
Peace membership, and Peace process payload are all ready. Missing, expired,
non-Peace, and unavailable states have distinct recovery copy; no state starts
a new OAuth flow automatically.

The Gerência workspace follows the same fail-closed loading contract: its
assignment form remains hidden behind a skeleton until the Discord session,
current Gerência role, and assignment-list response are all valid. A denied or
incomplete assignment response returns to the gate/unavailable state without
briefly exposing the form.

Public data pages keep their own loading, empty, stale/unavailable, and retry
states. Notices use a local seen-key ledger so a newly returned public item can
produce an accessible toast without claiming a real-time guarantee. Clips
search the bounded public source by title, provider, caption, or author; the
server rechecks Peace membership before persisting likes or comments.

## Verification

- Route/static contract: `python -m pytest tests/peace/test_public_site.py -q`.
- JavaScript syntax: `node --check` for each module under `bot/site/js/`.
- Local browser: inspect `/`, `/area/`, `/estudos/`, `/avisos/`, `/parceiros/`,
  `/clipes/`, and `/meu-processo/` at compact and desktop widths.
- Public-boundary review: no credentials, cookies, private URLs, local paths,
  or generated databases in the tracked diff.

The local proxy may report an unavailable or missing clip source when the
ACLClouds runtime has not yet published the matching `/api/clips` endpoint.
That is a deployment limitation, not permission to treat an empty response as
published content.
