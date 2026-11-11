# Public Peace site

Status: tracked implementation; the current redesign is local-only until an
explicit Netlify publication. Netlify serves the public static front, while
ACLClouds remains the runtime for the Discord bot and the backend HTTP process.

The public Peace home is a static single-page experience. It keeps the first
view within the viewport, uses the official Peace bird as a transparent PNG,
and provides a short public history based on the three curated milestones
already represented in the tracked site. It does not read Discord at request
time and does not expose member data or operational logs. Avisos and parceiros
are separate public interfaces rather than sections embedded in the home.

The `/entrar/` and `/candidatura/` routes are the public entry and candidature
UI. The first candidature action opens the public Discord invite; the explicit
confirmation then checks the read-only `/api/status` contract before revealing
the next stage. The interface does not claim to prove a member's identity or
create an OAuth session because that remote exchange remains a separate,
unimplemented contract. `/acessar/` is the member login UI for Peace ID plus a
six-digit DM code; it also remains honest when the code endpoints are
unavailable. No static page creates a session, invitation, application,
approval, or member record.

The `/area/` route is the member-area UI shell. Without a future authenticated
session it shows an access gate. The query strings `?preview=member` and
`?preview=investigativa` are local-only visual previews populated with synthetic
records; they are not login paths, do not contact the bot, and must never be
described as member or case data.

Netlify is the public TLS edge for the static front. The `bot/site/_redirects`
file owns the short `/discord` and `/discord/` routes and sends them directly
to the public Discord invite with a temporary redirect. It also proxies the
single read-only `/api/status` route to the fixed public ACLClouds endpoint at
`141.11.237.97:25072`, so the browser keeps a same-origin HTTPS request. The
invite is public by design; bot
credentials and provider settings remain outside the repository.

For local review, run `python ops/peace_site_server.py --port 4173`. The
localhost-only server mirrors the route contract needed by the static front:
`/discord` redirects to the public invite, the public flow aliases normalize to
their trailing-slash directories, and `GET /api/status` proxies only the fixed
read-only ACLClouds status endpoint. It does not proxy cookies, authorization
headers, member routes, or administrative actions. If ACLClouds cannot be
resolved or reached, the local route returns a truthful `503` response.

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
| ACLClouds `/healthz` | returns a no-store JSON liveness response |
| ACLClouds `/api/status` | returns bot readiness without member data or secrets |
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

## Visual and accessibility contract

The pages use a dark editorial palette derived from the supplied Peace mark:
graphite canvas, restrained slate surfaces, feather-white text, and cold blue
accents. CSS-only radial, grid, and line textures echo flight geometry without
introducing a second background asset. The pages also keep visible focus states,
semantic headings, skip links, keyboard-accessible mobile navigation, member
tabs, and a `prefers-reduced-motion` path. The reveal behavior uses
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

The entry surfaces keep one next action in view. `/acessar/` contains only the
Peace ID/code interaction and a compact route to candidature, `/entrar/` keeps
the three public destinations visible, and `/candidatura/` reveals one stage at
a time. Future stage buttons are disabled until the previous action advances
the flow. The Peace ID accepts only 1–19 digits and remains in the field after a
failed or timed-out request. Remote actions use a 60-second timeout, expose a
button loading state with `aria-busy`, and return to a retryable state without
showing internal routes or technical integration logs. The required terms
remain on the final review step, while the draft is persisted silently on input,
step changes, and page hide.

## Verification

Run the bot tests and compile check from the repository root:

```powershell
python -m pytest tests/peace -q
python -m compileall bot
node --check bot/site/script.js
git diff --check
```

The public route tests exercise the Netlify artifact contract, the ACL API
allowlist, CORS behavior, health response, and the fixed status proxy rule
without contacting Discord or a production provider. A production smoke check
should verify the Netlify homepage, `/discord`, `/entrar/`, `/candidatura/`,
`/acessar/`, `/avisos/`, `/parceiros/`, `/area/`, and `/api/status`, followed
by the direct ACL `/healthz` and `/api/status` routes. Custom-domain TLS
remains controlled by Netlify after DNS propagation. The current redesign is
not considered production-published until that smoke check is repeated after
an explicitly authorized deploy.
