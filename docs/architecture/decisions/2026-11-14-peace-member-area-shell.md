# Peace authenticated member-area shell

Status: implemented locally; production publication and authenticated browser
acceptance remain pending.

Decision owner: Peace public-site implementation

## Product job

The authenticated `/area/` surface gives a confirmed Peace member one place to
see their identity, process summary, study materials, notices, partners, and
public clips. A connected Discord account without the live Peace role sees only
the setagem path. An unknown or unavailable session never receives a panel
preview.

## Navigation contract

The panel uses a left navigation rail on wide screens. The rail is part of the
authenticated shell and pushes the main content to the right. At compact
widths it becomes a drawer: opening it moves the content instead of covering
the reading order, marks the closed rail `inert`, moves focus to the first
control, and returns focus to the toggle on close or `Escape`.

Each sidebar item is a real route, not a panel fragment:
`/area/`, `/estudos/`, `/parceiros/`, `/clipes/`, and `/meu-processo/`.
The current route is exposed with `aria-current`, and the public pages retain a
contextual return link based on browser history. Public notices remain a full
route, but the authenticated overview opens them from a notification bell so
they do not compete with the primary workspace navigation. The panel does not
send a connected member back to the public Home; Home resolves the same session
and redirects to `/area/` for Peace members or `/entrar/` for connected
accounts without the Peace role. Full-resource links may still open public
study, notice, partner, or media routes. The Discord destination is explicitly
external and opens in a separate tab.

## Authentication and state

The browser keeps only the provider-managed HttpOnly Discord session cookie.
Each page requests the same-origin session endpoint once and shares the
in-flight result within that page. The authenticated panel remains behind a
structural skeleton until all of the following are available:

1. a valid Discord ID, display identity, and official avatar URL;
2. a live guild membership result with the Peace role and manager flag;
3. the Discord-linked process response with profile and assignments.

The backend remains authoritative for all role and process decisions. A hidden
sidebar item is not an access control. The `401`, non-member, unavailable, and
ready states have separate copy and recovery actions; retry never starts a new
OAuth flow automatically.

## Visual contract

The shell uses the existing dark semantic tokens and a restrained surface
hierarchy. The connected profile appears in the rail with the avatar URL
provided by the backend's official Discord CDN construction. Material covers
reuse the shared cover component: the image is the base, a dark bottom-up
gradient provides contrast, and the title, description, page count, and
availability metadata sit over that gradient.

Skeleton geometry matches the rail and content columns. It is removed only
after the state contract above resolves, preventing a connected person from
seeing a second login action during the request or from entering a partially
identified panel. The ready view gives the profile the first visual priority,
shows only backend-confirmed role chips, and keeps the public notices feed out
of the initial process request; the bell loads it on demand with keyboard-safe
focus restoration.

## React decision

The public front is currently a no-build static site published directly from
`bot/site`; this checkout has no `package.json`, React dependency, or frontend
build step, and the local runtime does not provide npm. Introducing React by a
remote CDN would violate the site's CSP and deployment contract, while adding a
new build pipeline would expand this change beyond the requested member-area
flow. The implementation therefore uses small vanilla modules with the same
component boundaries expected in React: data fetching is isolated from
rendering, state transitions are explicit, and DOM updates use text content for
server data. A future React migration is a separate decision requiring a
bundled dependency, static build output, CSP review, and route parity tests.

## Verification

- `node --check` on every public JavaScript module;
- `python -m pytest tests/peace -q`, including candidature persistence and
  idempotent scan-only repair coverage;
- local route and responsive browser review at desktop and compact widths;
- `git diff --check` and a final public-boundary scan.

The external Discord OAuth callback still needs a registered localhost URI for
an end-to-end browser login test.
