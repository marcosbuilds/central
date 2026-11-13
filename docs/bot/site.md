# Public Peace site

Status: tracked implementation; Netlify serves the public static front, while
ACLClouds remains the runtime for the Discord bot and the backend HTTP process.

The public Peace home is a static single-page experience. It keeps the first
view within the viewport, uses the official Peace bird as a transparent PNG,
and provides a short public history based on the three curated milestones
already represented in the tracked site. It does not read Discord at request
time for the editorial sections and does not expose member data or operational
logs. Avisos and parceiros are separate public interfaces rather than sections
embedded in the home.

The home also has a bounded community-media feed. The bot reads up to 200
messages from the configured public media and clips channels, keeps a short
in-memory cache, and exposes at most 12 selected items per category through
`/api/media`. A message can contribute a Discord CDN attachment, a direct
HTTPS link from its text, or an allowlisted link/video already exposed by a
Discord provider embed. The explicit provider allowlist includes Medal,
Streamable, YouTube, Twitch Clips, TikTok, Gyazo, Imgur, and Outplayed. Medal
links are resolved only through the public Medal page for that clip, and only
a matching signed `cdn.medal.tv` MP4 is promoted to a playable video; the resolver
reads the bounded HTML response in chunks so provider media emitted after the first
network chunk is still discovered. Expired
or unresolved clips remain source cards with their bounded preview context. A canonical
TikTok video URL uses TikTok's official player URL; TikTok short links remain
source-only cards until an ID can be identified, so the site never tries to
decode an HTML page as a video file. The player format follows [TikTok's Embed
Player contract](https://developers.tiktok.com/docs/en/embed-player).

Each item reports an explicit render kind (`embed`, `direct`, or `link`), the
source URL, a bounded message caption with links and mentions removed, provider
preview text already supplied by Discord, the message author's Discord display
name/avatar when present, the message date, and reaction count. The display
name is the server-visible nickname/name; the endpoint does not expose a Peace
ID or raw message content. Discord does not expose public click counts for
messages, so the site does not invent them. A browser-local random seed gives
visitors different deterministic selections without identifying or tracking
them. Duplicate links inside one message and repeated reposts across the
channel are collapsed by provider/media identity while the newest message
context remains attached to the surviving item.
Media failures preserve the last successful list and keep an external origin
link visible; a provider page is never presented as an iframe video when the
provider blocks embedding.

## Source and publication layout

The frontend source is kept under `bot/site/` because Netlify publishes that
directory directly. `script.js` and `styles.css` remain compatibility
entrypoints for every route; their implementation is split into
`bot/site/js/` and `bot/site/css/` by responsibility. This keeps cacheable
public URLs stable while allowing media, candidature, access, member-area,
study/process, layout, and responsive rules to be maintained independently.

ACL deployment packages are backend-only. A valid package contains the bot
entrypoint and its support modules, configuration, persistence, operations,
and runtime artwork; it does not contain `site/`, HTML, frontend JavaScript,
frontend CSS, or site assets. Packages that still contain both surfaces are
legacy archives and must not be reused for production.

The clips channel is intentionally handled as a link-first feed: a message may
contain only a Medal/TikTok URL and no caption at all. In that case an empty
caption is valid; the site uses the bounded provider title/author as secondary
context, then shows the Discord message author and date. A direct Discord video
attachment follows the same contract without requiring a text caption. A clip
reposted in a different message remains a separate publication so its author,
date, and message context are not lost.

The `/entrar/` and `/candidatura/` routes are the public entry and candidature
UI. The first candidature action asks ACLClouds for an individual Discord
invite created in `#verify`. The runtime keeps the invite effectively
single-use: it creates a short-lived two-use invite so Discord's usage counter
remains observable during the join event, binds the first observed member, and
deletes the invite immediately. The invite is valid for 30 minutes. The browser
keeps only an opaque short-lived flow token, so a reload reuses the same invite
while it is valid. If the invite expires or disappears before entry, the bot
reports that bounded state and the browser automatically requests a replacement
while remaining in a loading state. The bot binds the invite to the member join
event, reports the linked
Discord display name, and exposes the verification state from the member's
`Not Verified`, `Visitante`, or `Peace` role. The interface advances to the
interview only after `Visitante` or `Peace` is observed; it never treats the
public service-health check as proof of a member identity and it does not
create a Discord OAuth session. If the visitor already belongs to the server,
the candidature flow can identify the existing member by required username and
optional Discord ID/profile URL, then route `Visitante` to the interview or
route an existing `Peace` member to `/acessar/` without requesting a new
setagem. `/acessar/` validates the numeric Peace ID, including the valid
Founder ID `0`, against the runtime member record, requires the configured
Peace role, sends a short-lived single-use code to that member's Discord DM,
and creates a web session only after the code is consumed. The DM is an embed
with a time-of-day greeting, a user mention, a bounded code field, an expiry
field, and no Peace ID in the greeting. The web session is an `HttpOnly`,
`Secure`, `SameSite=Lax` cookie; a checked “Manter conectado neste dispositivo”
sets a server-enforced maximum lifetime of seven days, while the default
session expires after the configured short TTL. A legacy bearer token may be
accepted during migration, but new browser sessions do not expose the token to
JavaScript. No static page creates an application, approval, or member record.

The `/area/` route is the member-area UI shell. Without a valid authenticated
session it shows only an access gate; it never renders a member workspace,
investigative case, or synthetic record. With the public member session it
revalidates the cookie/bearer and the live Peace role, then loads a read-only
overview. The overview returns only authorized blocks: next action, recent
public notices, bounded media, partner posts, and a privacy-limited active
clock summary. Investigator data is omitted from the payload unless the live
member has `Investigator` or `Lead Investigator`. When present, the block reads
from the site-owned investigative surface and does not read an investigation
category or channel from Discord. Query strings such as
`?preview=member` and `?preview=investigativa` cannot bypass this gate.
Every public API route also has a bounded in-process rate limit; the member
overview keeps a separate per-member refresh throttle. Source blocks report
`ready`, `empty`, or `unavailable` with `stale` metadata rather than presenting
a failed Discord/SQLite read as current data.

The public learning library is separate from `/area/`. `/estudos/` links to
the Civil study material and the Peace convivencia manual, while
`/meu-processo/` is the candidate-facing shell for Discord-linked exam
tracking. These pages do not require a Peace role. The reader publishes
rendered page images from the supplied PDFs rather than the original files, and
the process page reads only records bound to the authenticated Discord ID.

The public shell makes the selection contract visible and active: the Civil
page explains that the question bank is shared while the per-attempt order may
differ, and the process page separates the authenticated Discord ID from the
display-only username. The reader keeps the current study context visible and
fragment targets are focusable so keyboard and screen-reader users can move
from the outline to the requested chapter.

The selection contract is intentionally narrower than the member area: only
Gerência may create, assign, revoke, or grade an exam, and that authorization
is enforced server-side by a stable Discord role ID. Candidate sessions read
only records bound to their authenticated Discord ID. A username is a display
snapshot rather than an authorization key. See
`docs/architecture/decisions/2026-11-13-peace-public-learning-and-selection.md`
for the public boundary and delivered flow.

Netlify is the public TLS edge for the static front. The `bot/site/_redirects`
file owns the short `/discord` and `/discord/` routes and sends them directly
to the public Discord invite with a temporary redirect. It also proxies the
bounded status, notices, entry, OAuth, and exam routes to the fixed HTTPS
ACLClouds endpoint, so the browser keeps a same-origin HTTPS request. The
member-session proxy forwards only the member cookie or legacy bearer on the
allowlisted member routes. Bot credentials and provider settings remain
outside the repository.

For local review, run `python ops/peace_site_server.py --port 4173`. The
localhost-only server mirrors the route contract needed by the static front:
`/discord` redirects to the public invite, the public flow aliases normalize to
their trailing-slash directories, and the bounded status/entry/member-auth
routes proxy to the fixed ACLClouds origin. It does not proxy arbitrary member
routes or administrative actions; the allowlisted member routes forward only
the session cookie or legacy bearer. The repair route can only
inspect and, when Discord permits it, restore `Not Verified` for the member
already bound to that opaque entry token; it cannot look up an arbitrary ID.
If ACLClouds cannot be resolved or reached, the local route returns a truthful
`503` response.

The repository-level `netlify.toml` publishes `bot/site` without a build step,
so a linked Netlify project can reproduce the same artifact from the source
tree. Production visibility is public; deploy previews remain private.

## Runtime contract

The provider receives the bot package as its runtime root. The startup command
is therefore `python -u main.py`. `bot/site` remains in the repository because
it is the Netlify publish directory, but it is not a runtime dependency of the
ACL process and must not be copied into the ACL deployment as a served site.

| Route | Behavior |
|---|---|
| Netlify `/` | serves `bot/site/index.html` with HTTPS |
| Netlify `/styles.css`, `/script.js`, `/assets/*` | serves versioned static site files |
| Netlify `/discord`, `/discord/` | redirects to the public Discord invite via `_redirects` |
| Netlify `/entrar/` | serves the public entry UI |
| Netlify `/candidatura/` | serves the documented candidature and setagem UI states |
| Netlify `/acessar/` | serves the member Peace ID + code login UI |
| Netlify `/avisos/` | serves the dedicated public notices interface |
| Netlify `/parceiros/` | serves the dedicated public partners interface |
| Netlify `/estudos/` | serves the public study library and material cards |
| Netlify `/estudos/civil/` | serves the Civil study reader and rendered pages |
| Netlify `/estudos/peace/` | serves the Peace convivencia reader and rendered pages |
| Netlify `/meu-processo/` | serves the candidate-owned Discord-linked process shell |
| Netlify `/estudos/a-peace` | redirects to `/estudos/peace/` as a readable alias |
| Netlify `/entrar`, `/candidatura`, `/acessar`, `/avisos`, `/parceiros`, `/estudos`, `/meu-processo` | normalize to their trailing-slash routes |
| Netlify `/area` | normalizes to the gated `/area/` shell |
| Netlify `/area/` | serves the gated member-area UI shell |
| Netlify `/api/status` | proxies only the public backend status contract |
| Netlify `/api/media` | proxies the bounded public Discord media feed |
| Netlify `/api/entry/start` | creates or resumes one short-lived, single-use Discord invite |
| Netlify `/api/entry/status` | accepts the opaque flow token only in the POST body; tokens in query strings are rejected |
| Netlify `/api/entry/repair` | repairs only the linked member's `Not Verified` entry role when safe |
| Netlify `/api/entry/identify` | identifies an existing server member and reports the confirmed role state |
| Netlify `/api/member/auth/request` | validates a Peace ID and sends a one-time code to the linked member's Discord DM |
| Netlify `/api/member/auth/verify` | consumes the one-time code bound to the HttpOnly challenge cookie and creates a member session |
| Netlify `/api/member/auth/session` | validates the bounded member session and the current Discord identity |
| Netlify `/api/member/auth/revoke` | revokes the current member session and clears the cookie |
| Netlify `/api/member/overview` | returns the read-only, capability-filtered member overview |
| Netlify `/api/notices` | proxies the bounded public notices feed |
| Netlify `/api/auth/discord/start` | starts Discord OAuth with PKCE and a persisted state |
| Netlify `/api/auth/discord/callback` | validates the state, exchanges the code, and creates the HttpOnly session |
| Netlify `/api/auth/discord/session` | returns the authenticated Discord identity and guild state |
| Netlify `/api/auth/discord/logout` | revokes the current Discord session |
| Netlify `/api/exams/process` | returns only the candidate's assignments and score |
| Netlify `/api/exams/access` | validates the individualized assignment link against the authenticated Discord ID |
| Netlify `/api/exams/start` | materializes the fixed Civil question set with per-attempt ordering |
| Netlify `/api/exams/submit` | grades once on the server and delivers the result to the assigning manager |
| Netlify `/api/exams/assignments` | allows only Gerência to create and list assignments |
| ACLClouds `/healthz` | returns a no-store JSON liveness response |
| ACLClouds `/api/status` | returns bot readiness without member data or secrets |
| ACLClouds `/api/entry/start` | creates/resumes the 30-minute invite in the verification channel |
| ACLClouds `/api/entry/status` | returns bounded flow state, not cookies or OAuth data |
| ACLClouds `/api/entry/repair` | validates the linked session before the narrow role repair |
| ACLClouds `/api/entry/identify` | matches required username plus optional identity hints against current guild membership |
| ACLClouds `/api/member/auth/request` | validates an active Peace member and sends the short-lived DM code |
| ACLClouds `/api/member/auth/verify` | consumes the code once from the browser-bound challenge and issues a bounded member session |
| ACLClouds `/api/member/auth/session` | rechecks the session, Discord user ID, and current Peace role |
| ACLClouds `/api/member/auth/revoke` | revokes the current member session |
| ACLClouds `/api/member/overview` | returns only source-backed blocks authorized for the current role |
| ACLClouds `/api/notices` | returns the bounded public notices feed |
| ACLClouds `/api/auth/discord/*` | serves the Discord OAuth session contract |
| ACLClouds `/api/exams/*` | serves candidate process and Gerência-only exam operations |
| ACLClouds `/`, `/discord`, `/styles.css`, `/script.js`, `/assets/*` | returns 404; the ACL does not serve the frontend |

The ACLClouds process binds to `PEACE_API_HOST` and `PEACE_API_PORT`; when the
provider sets `PORT`, the API uses it as the default. `PEACE_API_ENABLED=false`
disables this listener without changing the bot's other services. The public
domain remains on Netlify; the API origin is used only by the explicit proxy
rule.

## Configuration boundary

Production values belong in the provider environment, never in the public
repository. The committed `.env.example` contains placeholders for OAuth and
the protected answer key; the actual values are configured only in ACLClouds
and the ignored local `.env`. The canonical public URL is configured as
`PEACE_SITE_URL` so Discord buttons and external documentation can reference it
without coupling the code to a provider hostname.

`PEACE_SITE_MEDIA_CHANNEL_ID` and `PEACE_SITE_CLIPS_CHANNEL_ID` identify the two
Discord channels intentionally exposed to the public home. They are optional;
when absent, the feed remains empty rather than guessing a channel. The bot
refreshes each channel cache after `PEACE_SITE_MEDIA_CACHE_SECONDS` (minimum 30
seconds, default 300).

`PEACE_SITE_PARTNERS_CHANNEL_ID` optionally identifies the partner source for
the authenticated overview. Investigation data is site-owned and has no
Discord channel or category configuration.
`DISCORD_INVESTIGATOR_ROLE_ID` and
`DISCORD_LEAD_INVESTIGATOR_ROLE_ID` are the preferred stable production role
IDs. The bot creates the canonical zero-permission roles when needed and may
bind a unique canonical role to the running configuration when an ID is not
present; duplicate names fail closed. Role names are never accepted as an
authorization fallback when more than one candidate exists.
`PEACE_TIMEZONE` controls the access-code greeting and defaults to
`America/Sao_Paulo`. The persistent web session is capped at seven days by
`CENTRAL_AUTH_PERSISTENT_SESSION_TTL_SECONDS` even if an environment value is
set higher. The web code request creates an opaque, `Secure` and `HttpOnly`
challenge cookie that expires with the code; the verification form sends only
the six-digit code and keeps the Peace ID out of the second request. Releasing
or reassigning a Peace identity revokes its sessions, and validation also
requires the stored Discord user ID to match the live member.

The local preview proxy forwards only the member session/challenge cookies,
Discord OAuth cookies, and Bearer compatibility header. It does not follow
ACLClouds redirects, so a misconfigured redirect cannot carry credentials to a
different origin. Production uses the HTTPS ACLClouds hostname rather than the
legacy public IP route.

## Visual and accessibility contract

The pages use a dark editorial palette derived from the supplied Peace mark:
graphite canvas, restrained slate surfaces, feather-white text, and cold blue
accents. CSS-only radial, grid, and line textures echo flight geometry without
introducing a second background asset. The pages also keep visible focus states,
semantic headings, skip links, keyboard-accessible mobile navigation, the
authenticated-area gate, and a `prefers-reduced-motion` path. On compact home
layouts, the main header centers a lowercase `menu` disclosure with a real
two-stroke arrow; its navigation panel opens below the control as a rounded
translucent 2×2 grid with a centered pointer and keeps the same keyboard/inert
state contract. The reveal behavior uses
`IntersectionObserver` without an external motion dependency, continuous scroll
listener, ticker, or auto-scrolling content.

`bot/site/assets/peace-bird.png` is the transparent RGBA Peace logo supplied for
this redesign and stored at a stable runtime path. The original attachment is
not a runtime dependency. The background treatment is project-owned CSS derived
from the logo's blue-gray feathers and navy outline; it is not presented as an
original Discord background or a separately sourced brand asset.

`bot/site/assets/discord.svg` is the local Discord destination icon used only
inside links that visibly lead to the Peace Discord invite. Its provenance is
recorded here so the asset is not mistaken for a project-owned logo:

- source: [theSVG Discord default icon](https://thesvg.org/icons/discord/default.svg);
- upstream brand and usage rules: [Discord](https://discord.com/branding);
- license metadata declared by theSVG: `CC0-1.0` for the catalogued file;
- retrieved: 2026-11-11;
- SHA-256: `6634CC2F915DB66DF7A5237CAC0C1B98016289E86A2BB4B7BF6408EC2B95265C`;
- constraint: keep the mark unmodified and do not imply Discord endorsement.

`bot/site/assets/shield-check.svg` is the local verification-state icon used in
the candidature, login and notices surfaces. Its provenance is recorded here
so it is not confused with the Peace mark:

- source: [theSVG Shield Check UI icon](https://thesvg.org/ui/shield-check/outline.svg);
- catalog page: [Shield Check](https://thesvg.org/ui/shield-check);
- license/attribution: theSVG page declares its UI collection open-source and
  states that no attribution is required; the SVG contains no scripts or
  external references;
- retrieved: 2026-11-11;
- SHA-256: `80D0ECEBCBA1D1F28CAE603E8C9C1886FCA1CF22CC213EDDDFF526A059BEA86D`;
- constraint: use only for a verification/security state, never as the Peace
  logo or as evidence that a user is authenticated.

`bot/site/assets/id-card.svg` is the local identity cue shown beside the Peace
ID field on `/acessar/`. Its provenance is recorded here so it is not confused
with the Peace mark:

- source: [theSVG Id Card outline UI icon](https://thesvg.org/ui/id-card/outline.svg);
- catalog page: [Id Card](https://thesvg.org/ui/id-card);
- license/attribution: theSVG UI collection is open-source and requires no
  attribution; the SVG contains no scripts or external references;
- retrieved: 2026-11-11;
- SHA-256: `AB43B1100D12EA994E2C740AF830CB0BAEE6B7921697EEECE3897D0AB1AC22EE`;
- constraint: use only as an identity-field cue, never as a Peace logo or as
  proof that a visitor is authenticated.

`bot/site/assets/copy.svg` is the icon-only action for copying the public
Discord route. Its provenance is recorded here so the control remains
recognizable without turning into a large secondary button:

- source: [theSVG Copy outline UI icon](https://thesvg.org/ui/copy/outline.svg);
- license/attribution: theSVG UI collection is open-source and requires no attribution;
- retrieved: 2026-11-11;
- SHA-256: `1CB5A83DCF054C292A43071EE8FEDA3AF9886EF596854BEB5ED39DABCF2AA7AD`;
- accessible behavior: the button keeps an `aria-label`, a native tooltip and a live copy result;
- constraint: use only for the copy action, never as a substitute for the visible link.

The public page keeps the visible invite explicitly marked as copyable and
shows `peacegg.com.br/discord`; the browser may select and copy ordinary
editorial text normally. The copy control only writes the invite to the
clipboard after an explicit user action. Clipboard behavior is browser-level
convenience, not a security boundary: source inspection, DevTools, OCR,
screenshots, and assistive technology remain outside the control of a static
site.

The home media region uses skeleton cards during its first request, a truthful
empty state when either configured channel has no eligible items, and a quiet
refresh status. It refreshes while the tab is visible according to the backend
cache hint; it does not autoplay media or create a continuous ticker. Cards
show the sanitized message text when available, otherwise a provider preview
title, followed by the display name/avatar, complete local date, and provider
origin. A resolved Medal clip and a direct Discord attachment use native video
controls; an expired Medal link keeps its preview thumbnail/origin card instead
of showing a blank iframe. A source-only card keeps the provider action in its
visual and avoids repeating the same title/link below. The lightbox repeats that
metadata and restores focus to its launcher.

When the individual invite is being generated, the browser keeps the Peace page
in place and shows an accessible loading state. The Discord window is reserved
during the user's click and reused by a stable window name, then navigated only
after the API confirms a valid invite. If the browser blocks the popup, the
same invite is exposed as a real manual link; it keeps the same session token
and does not create a second invite. The Peace tab remains available.

The entry surfaces keep one next action in view. `/acessar/` contains only the
Peace ID/code interaction and a compact route to candidature, `/entrar/` keeps
the three public destinations visible, and `/candidatura/` reveals one stage at
a time. Future stage buttons are disabled until the backend-backed entry state
advances the flow. The Discord invite opens in a new tab and remains reusable
after a reload until its 30-minute expiry. Stage 02 explains the real `#verify`
CAPTCHA flow, polls the bounded entry status, and moves automatically only when
the bot observes `Visitante` or `Peace`. During the invite stage it shows one
Discord-opening action plus a non-clickable invite label, waits for the bot's
actual member binding, and never treats a browser click as proof of entry. Its
troubleshooting panel accepts
optional username, ID, and profile link fields, but the backend binds every
repair to the member already identified by that invite. Remote actions use a
60-second timeout, expose a button loading state with `aria-busy`, and return to
a retryable state without showing internal routes or technical integration
logs. Member authentication shows a loading state while the session is checked,
redirects an already authenticated browser directly to `/area/`, and returns
an invalidated session to `/acessar/?status=session-expired` rather than the
home page. A transient timeout keeps the local session and offers a retry.
The authenticated area uses one compact hierarchy, no unauthenticated preview,
and source-aware blocks with `updated_at`, `source`, and `stale` semantics. It
uses bounded polling while the tab is visible; it does not create a WebSocket
until the Discord sources expose an event contract. The required
terms remain on the final review step, while the draft is persisted silently on
input, step changes, and page hide. The candidature header is hidden on desktop
and mobile; the desktop return link remains beside the title.

## Verification

Run the bot tests and compile check from the repository root:

```powershell
python -m pytest tests/peace -q
python -m compileall bot
node --check bot/site/script.js
git diff --check
```

The public route tests exercise the Netlify artifact contract, the ACL API
allowlist, CORS behavior, health response, media filtering, and the fixed
status proxy rule without contacting Discord or a production provider. A
production smoke check should verify the Netlify homepage, `/discord`,
`/entrar/`, `/candidatura/`, `/acessar/`, `/avisos/`, `/parceiros/`, `/area/`,
`/api/status`, and `/api/media`, followed by the direct ACL `/healthz`,
`/api/status`, and `/api/media` routes. Custom-domain TLS
remains controlled by Netlify after DNS propagation. The current redesign is
not considered production-published until that smoke check is repeated after
an explicitly authorized deploy.
