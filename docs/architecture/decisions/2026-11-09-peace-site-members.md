# Peace site and member area

Status: implemented UI shell; authenticated member integration is proposed and
not implemented

Decision owner: Peace product and bot maintainers

Date: 2026-11-09

## Outcome

The public Peace site remains a Discord-first editorial surface. It explains
the entry path, curates the public history already recorded in the site, and
points people to the server. A separate `/area/` route now defines the member
surface without pretending that a web session or member API exists.

The member route has two truthful states:

- no session: an access gate explains that Discord and Peace Tools still own
  identity, CAPTCHA, role changes, and private conversations;
- local preview: `?preview=member` opens synthetic records for visual and
  responsive review. The preview is explicitly labelled and is not a member
  account or a production data source.

## Evidence boundary

The repository documents and implements these real jobs:

- community conversation, games, calls, support, and tickets;
- `Not Verified` to CAPTCHA to `Visitor` onboarding in Discord;
- manual set requests reviewed by Staff or Management;
- operational records such as point, absence, and farm in the bot database;
- technical access guarded by the Discord `Dev` role and a separate local-only
  Central bridge.

The public HTTP process currently exposes only `/healthz` and `/api/status`.
There is no remote OAuth callback, browser session, member overview endpoint,
or web CAPTCHA contract. The site therefore does not show a real name, avatar,
Peace ID, role, request, ticket, operation, log, or Discord message.
The `/candidatura/` route may preserve an in-progress draft, including its
review step and local terms, in the current browser only; it does not create a
server-side application or imply that a submission was received.

The historical copy on the public home is editorially curated from the three
milestones already represented in the tracked site: the 29 April cycle
announcement, the 30 April season reset, and the 2 May Peace Tools dashboard
milestone. The repository does not contain stable links to the original Discord
messages, so these are explicitly presented as a concise editorial reading
rather than as a live feed or independently queryable archive. Product names
and unverifiable source-specific labels are not expanded beyond what the
repository can support.

## Information architecture

### Public home

The home uses a short top navigation: Entry, History, Notices, and Member area.
Its content order follows the visitor's decision:

1. understand what Peace is and start in Discord;
2. see the three entry steps;
3. understand the public history;
4. learn where current detail lives;
5. discover the future member area without bypassing Discord.

The implementation uses an editorial split hero, a line-based step list, a
timeline, and one dark notice frame. It deliberately avoids a metric dashboard,
member count, live Discord feed, or invented activity indicator.

### Member area

The member UI is task-oriented rather than metric-oriented:

- Overview: next allowed step, authorized status summary, and a small activity
  history owned by the member;
- Entry: verification state and the next step, with the bot remaining the
  authority;
- Requests: set/developer request status and next action, without private form
  fields or ticket content;
- Support: authorized ticket status and a link back to Discord.

Staff and Management approval controls are intentionally not part of this
surface. Central access is also a separate future route with its own role and
project checks.

## Proposed authenticated contract

The following is a proposal for a future backend change, not a delivered API:

| Route | Expected behavior | Required security |
|---|---|---|
| `GET /api/member/session` | return a small session summary or `401` | Discord OAuth2 Authorization Code, `state`, PKCE where applicable, HttpOnly Secure cookie |
| `GET /api/member/overview` | return only the current member's allowed overview | server-side Discord identity binding, access checks on every request, no raw tickets or sensitive onboarding fields |
| `GET /api/member/requests` | return that member's request states and dates | ownership check; redact RG, phone, reviewer notes, and private messages |
| `GET /api/member/support` | return allowed ticket status only | ownership, closed-ticket policy, no message transcript |
| `POST /api/member/verification/refresh` | refresh a status read from the bot | never grant/remove roles from the browser; bot remains the authority |

The first implementation should be read-only. A browser request must never be
able to grant `Visitor`, `Peace`, `Intern`, `Dev`, or any other role. A web
CAPTCHA can only be considered after an explicit threat model, replay
protection, rate limit, bot-side verification handshake, and audit contract are
approved. The current design correctly sends members to the Discord CAPTCHA.

## Visual and motion contract

- cool neutral canvas derived from the bird's blue-gray feathers, paper-white
  surfaces, navy action surfaces, semantic status colors, and visible focus
  states;
- CSS-only radial and line textures echo the logo's wing geometry; no separate
  background asset is claimed or introduced;
- Avenir/Segoe system sans with Georgia for editorial emphasis; no remote font
  dependency;
- line-based grouping for steps, history, and actions instead of repeated
  cards;
- the official transparent Peace bird from `bot/site/assets/peace-bird.png`;
- IntersectionObserver reveal using opacity, transform, and blur only;
- `prefers-reduced-motion` removes non-essential movement while preserving all
  content and task order;
- the mobile navigation and member tabs remain keyboard operable and use
  native links/buttons.

## Verification plan

The UI revision must be checked with:

```powershell
node --check bot/site/script.js
python -m pytest tests/peace -q
python -m compileall bot
git diff --check
```

Manual local review must cover `/`, `/area/`, and `/area/?preview=member` at
320, 768, 1024, and 1440 CSS pixels; keyboard navigation; 400% zoom; reduced
motion; menu close with Escape; member tab arrow navigation; candidature reload
at the review step; and a console-free load. These checks validate the static UI only. They do not prove OAuth,
production TLS, DNS, API authorization, or Discord availability.
