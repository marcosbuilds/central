# Public Peace site

Status: tracked implementation; the current redesign is local-only until an
explicit Netlify publication. Netlify serves the public static front, while
ACLClouds remains the runtime for the Discord bot and the backend HTTP process.

The public Peace home is a static single-page experience. It keeps the first
view within the viewport, uses the official Peace bird as a transparent PNG,
and provides a short public history based on the three curated milestones
already represented in the tracked site. It does not read Discord at request
time and does not expose member data or operational logs.

The `/area/` route is the member-area UI shell. Without a future authenticated
session it shows an access gate. The query string `?preview=member` is a
local-only visual preview populated with synthetic records; it is not a login,
does not contact the bot, and must never be described as member data.

Netlify is the public TLS edge for the static front. The `bot/site/_redirects`
file owns the short `/discord` and `/discord/` routes and sends them directly
to the public Discord invite with a temporary redirect. It also proxies the
single read-only `/api/status` route to the fixed ACLClouds API origin, so the
browser keeps a same-origin HTTPS request. The invite is public by design; bot
credentials and provider settings remain outside the repository.

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
| Netlify `/discord` and `/discord/` | redirects to the public Discord invite via `_redirects` |
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

The pages use a cool neutral palette derived from the official bird: an
ice-blue canvas, feather-white surfaces, slate-blue editorial accents, and
navy action/contrast surfaces. CSS-only radial and line textures echo the
logo's wing geometry without introducing a second background asset. The pages
also keep visible focus states, semantic headings, skip links,
keyboard-accessible mobile navigation and member tabs, and a
`prefers-reduced-motion` path. The reveal behavior uses `IntersectionObserver`
without an external motion dependency, continuous scroll listener, ticker, or
auto-scrolling content.

`bot/site/assets/peace-bird.png` is the official logo extracted from the
server's public `media` channel and processed into a transparent RGBA PNG. The
source image is intentionally not committed: only the runtime asset with a
stable purpose is part of the public tree. The background treatment is
project-owned CSS derived from the logo's blue-gray feathers and navy outline;
it is not presented as an original Discord background or a separately sourced
brand asset.

## Verification

Run the bot tests and compile check from the repository root:

```powershell
python -m pytest tests/peace -q
python -m compileall bot
git diff --check
```

The public route tests exercise the Netlify artifact contract, the ACL API
allowlist, CORS behavior, health response, and the fixed status proxy rule
without contacting Discord or a production provider. A production smoke check
should verify the Netlify homepage, `/discord`, `/area/`, and `/api/status`,
followed by the direct ACL `/healthz` and `/api/status` routes. Custom-domain
TLS remains controlled by Netlify after DNS propagation. The current redesign
is not considered production-published until that smoke check is repeated
after an explicitly authorized deploy.
