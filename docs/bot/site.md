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
them. Duplicate links inside one message are collapsed by provider/media
identity while the message context remains attached to the surviving item.
Media failures preserve the last successful list and keep an external origin
link visible; a provider page is never presented as an iframe video when the
provider blocks embedding.

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
`Not Verified`, `Visitor`, or `Peace` role. The interface advances to the
interview only after `Visitor` or `Peace` is observed; it never treats the
public service-health check as proof of a member identity and it does not
create a Discord OAuth session. If the visitor already belongs to the server,
the candidature flow can identify the existing member by required username and
optional Discord ID/profile URL, then route `Visitor` to the interview or
route an existing `Peace` member to `/acessar/` without requesting a new
setagem. `/acessar/` validates the numeric Peace ID against the runtime member
record or Peace nickname, requires the Peace role, sends a short-lived
single-use code to that member's Discord DM, and creates a short-lived web
session only after the code is consumed. No static page creates an
application, approval, or member record.

The `/area/` route is the member-area UI shell. Without a valid authenticated
session it shows an access gate; with the public member session it validates the
bearer token and shows the confirmed member identity. The query strings `?preview=member` and
`?preview=investigativa` are local-only visual previews populated with synthetic
records; they are not login paths, do not contact the bot, and must never be
described as member or case data.

Netlify is the public TLS edge for the static front. The `bot/site/_redirects`
file owns the short `/discord` and `/discord/` routes and sends them directly
to the public Discord invite with a temporary redirect. It also proxies the
bounded status and entry routes to the fixed public ACLClouds endpoint at
`141.11.237.97:25072`, so the browser keeps a same-origin HTTPS request. The
member-session proxy forwards only the short-lived bearer header on its
dedicated session route. Bot credentials and provider settings remain outside
the repository.

For local review, run `python ops/peace_site_server.py --port 4173`. The
localhost-only server mirrors the route contract needed by the static front:
`/discord` redirects to the public invite, the public flow aliases normalize to
their trailing-slash directories, and the bounded status/entry/member-auth
routes proxy to the fixed ACLClouds origin. It does not proxy cookies, arbitrary
member routes, or administrative actions; only the member-session route
forwards its bearer header. The repair route can only
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
| Netlify `/entrar`, `/candidatura`, `/acessar`, `/avisos`, `/parceiros` | normalize to their trailing-slash routes |
| Netlify `/area` | normalizes to the gated `/area/` shell |
| Netlify `/area/` | serves the gated member-area UI shell |
| Netlify `/api/status` | proxies only the public backend status contract |
| Netlify `/api/media` | proxies the bounded public Discord media feed |
| Netlify `/api/entry/start` | creates or resumes one short-lived, single-use Discord invite |
| Netlify `/api/entry/status` | returns the invite/member/verification state for the opaque flow token |
| Netlify `/api/entry/repair` | repairs only the linked member's `Not Verified` entry role when safe |
| Netlify `/api/entry/identify` | identifies an existing server member and reports the confirmed role state |
| Netlify `/api/member/auth/request` | validates a Peace ID and sends a one-time code to the linked member's Discord DM |
| Netlify `/api/member/auth/verify` | consumes the one-time code and creates a short-lived member session |
| Netlify `/api/member/auth/session` | validates the short-lived member session |
| ACLClouds `/healthz` | returns a no-store JSON liveness response |
| ACLClouds `/api/status` | returns bot readiness without member data or secrets |
| ACLClouds `/api/entry/start` | creates/resumes the 30-minute invite in the verification channel |
| ACLClouds `/api/entry/status` | returns bounded flow state, not cookies or OAuth data |
| ACLClouds `/api/entry/repair` | validates the linked session before the narrow role repair |
| ACLClouds `/api/entry/identify` | matches required username plus optional identity hints against current guild membership |
| ACLClouds `/api/member/auth/request` | validates an active Peace member and sends the short-lived DM code |
| ACLClouds `/api/member/auth/verify` | consumes the code once and issues a bounded member session |
| ACLClouds `/api/member/auth/session` | rechecks the session and current Peace role |
| ACLClouds `/`, `/discord`, `/styles.css`, `/script.js`, `/assets/*` | returns 404; the ACL does not serve the frontend |

The ACLClouds process binds to `PEACE_API_HOST` and `PEACE_API_PORT`; when the
provider sets `PORT`, the API uses it as the default. `PEACE_API_ENABLED=false`
disables this listener without changing the bot's other services. The public
domain remains on Netlify; the API origin is used only by the explicit proxy
rule.

## Configuration boundary

Production values belong in the provider environment, never in the public
repository. The committed `.env.example` contains placeholders only for the
 invite URL and API listener port. The canonical public URL is configured as
`PEACE_SITE_URL` so Discord buttons and external documentation can reference it
without coupling the code to a provider hostname.

`PEACE_SITE_MEDIA_CHANNEL_ID` and `PEACE_SITE_CLIPS_CHANNEL_ID` identify the two
Discord channels intentionally exposed to the public home. They are optional;
when absent, the feed remains empty rather than guessing a channel. The bot
refreshes each channel cache after `PEACE_SITE_MEDIA_CACHE_SECONDS` (minimum 30
seconds, default 300).

## Visual and accessibility contract

The pages use a dark editorial palette derived from the supplied Peace mark:
graphite canvas, restrained slate surfaces, feather-white text, and cold blue
accents. CSS-only radial, grid, and line textures echo flight geometry without
introducing a second background asset. The pages also keep visible focus states,
semantic headings, skip links, keyboard-accessible mobile navigation, member
tabs, and a `prefers-reduced-motion` path. On compact home layouts, the main
header centers a labeled three-line menu control; its navigation panel opens
below the control with a centered pointer and keeps the same keyboard/inert
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

The public page uses a small allowlist for copying: the visible invite is
explicitly marked as copyable and shows `peacegg.com.br/discord`; ordinary
editorial text is not placed on the clipboard by the page. This is
browser-level friction, not a security boundary: source inspection, DevTools,
OCR, screenshots, and assistive technology remain outside the control of a
static site.

The home media region uses skeleton cards during its first request, a truthful
empty state when either configured channel has no eligible items, and a quiet
refresh status. It refreshes while the tab is visible according to the backend
cache hint; it does not autoplay media or create a continuous ticker. Cards
show the sanitized message text when available, otherwise a provider preview
title, followed by the display name/avatar, complete local date, and provider
origin. A resolved Medal clip and a direct Discord attachment use native video
controls; an expired Medal link keeps its preview thumbnail/origin card instead
of showing a blank iframe. The lightbox repeats that metadata and restores
focus to its launcher.

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
the bot observes `Visitor` or `Peace`. During the invite stage it shows one
Discord-opening action plus a non-clickable invite label, waits for the bot's
actual member binding, and never treats a browser click as proof of entry. Its
troubleshooting panel accepts
optional username, ID, and profile link fields, but the backend binds every
repair to the member already identified by that invite. Remote actions use a
60-second timeout, expose a button loading state with `aria-busy`, and return to
a retryable state without showing internal routes or technical integration
logs. Member authentication shows a loading state while the session is checked
and uses a skeleton before authenticated content is revealed. The required
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
