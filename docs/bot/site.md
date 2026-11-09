# Public Peace site

Status: Implemented in the repository; production availability is verified
only by the deployment smoke check recorded for the current release.

The public Peace home is a static single-page experience served by the same
`aiohttp` process as the companion bot. It keeps the first view within the
viewport, uses the official Peace bird as a transparent PNG, and provides a
short public history based on verified community announcements. It does not
read Discord at request time and does not expose member data or operational
logs.

## Runtime contract

The provider receives the contents of `bot/` as its runtime root. The startup
command is therefore `python -u main.py`, and the public site is loaded from
the sibling `site/` directory in that deployment payload.

| Route | Behavior |
|---|---|
| `/` | serves `site/index.html` |
| `/styles.css`, `/script.js`, `/assets/*` | serves versioned static site files |
| `/discord` | redirects to `PEACE_DISCORD_INVITE_URL` with `Cache-Control: no-store` |
| `/healthz` | returns a small JSON health response for provider checks |

The server binds to `PEACE_SITE_HOST` and `PEACE_SITE_PORT`; when the provider
sets `PORT`, the site uses it as the default. `PEACE_SITE_ENABLED=false`
disables the listener without changing the bot's other services.

## Configuration boundary

Production values belong in the provider environment, never in the public
repository. The committed `.env.example` contains placeholders only for the
invite URL and site port. The canonical public URL is configured as
`PEACE_SITE_URL` so Discord buttons and external documentation can reference it
without coupling the code to a provider hostname.

## Visual and accessibility contract

The page uses a restrained neutral palette, visible focus states, semantic
headings, a skip link, keyboard-accessible mobile navigation, and a
`prefers-reduced-motion` path. The reveal behavior uses `IntersectionObserver`
with a GSAP enhancement when the CDN is available; it has no continuous scroll
listener, ticker, or auto-scrolling content.

`bot/site/assets/peace-bird.png` is the official logo extracted from the
server's public `media` channel and processed into a transparent RGBA PNG. The
source image is intentionally not committed: only the runtime asset with a
stable purpose is part of the public tree.

## Verification

Run the bot tests and compile check from the repository root:

```powershell
python -m pytest tests/peace -q
python -m compileall bot
git diff --check
```

The public route tests exercise the home, redirect, health response, and
required static files without contacting Discord or a production provider.
