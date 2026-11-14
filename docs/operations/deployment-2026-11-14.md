# Peace public learning deployment record

Date: 2026-11-14
Status: **Implemented and locally verified**

## Scope

This release covers the public Peace learning library, the Civil study reader,
the A Peace manual reader, the public process/proof entrypoints, and shared
Discord identity controls. Production publication for `peacegg.com.br` remains
deferred.

The frontend was verified locally from `bot/site`; production publication is
deferred. The original PDF files are not part of the public package. Readers
display generated page images,
the table of contents, the current-page indicator, and page-specific context.

## Production publication

| Surface | Check | Result |
| --- | --- | --- |
| Netlify site | Production publication for `peacegg.com.br` | **Not run — local-only scope** |
| Local public routes | Homepage, studies, Civil, A Peace, process, proof, management, notices, partners | 200 and visually inspected |
| Static assets | Covers and reader page images | Loaded after the normal image request completes |
| Netlify branding | Production pages | Not applicable until a deploy is requested |
| Original PDF files | Public package and rendered reader DOM | Not published or linked |

No Netlify dashboard, Drop workflow, or production provider was touched in
this verification. A future release should use the repository-connected build
once the production boundary is explicitly authorized and configured.

## Browser verification

The local site was inspected in the internal browser at the available desktop
viewport, including the header, study library, Civil landing page, index and
accordion states. Production was not inspected because deployment was deferred.

Verified public routes:

- `/`
- `/estudos/`
- `/estudos/civil/`
- `/estudos/civil/leitor/`
- `/estudos/peace/`
- `/estudos/peace/leitor/`
- `/meu-processo/`
- `/prova/`
- `/gerencia/provas/`
- `/avisos/`
- `/parceiros/`

Reader-specific checks:

- Civil: all 18 table-of-contents destinations were opened and visually
  checked; `Código Q` resolves to `#reader-page-7`, whose image and context
  both identify page 7.
- A Peace: all 8 table-of-contents destinations were opened and visually
  checked.
- Sticky headers, side summaries, current-page highlighting, page context,
  accordions, empty states, and footer navigation were inspected.
- No overlap, clipped control, broken line wrap, page-level horizontal scroll,
  or route-level layout break was observed in the checked surfaces.
- The local browser console produced no captured errors or warnings during the
  verification run.

## Checks

| Command | Result |
| --- | --- |
| `python -m pytest tests/peace -q` | 159 passed |
| `node --check` for changed site JavaScript | Passed |
| `python -m compileall -q bot` | Passed |
| Local public-route smoke requests | 13 routes/assets returned 200 |
| `git diff --check` | Passed |
| `dotnet build Central.sln -c Release` | Not executed: .NET SDK unavailable on the host |
| `dotnet test Central.sln -c Release` | Not executed: .NET SDK unavailable on the host |

## Discord and authentication boundary

The public frontend now uses one shared Discord identity control. An
unauthenticated visitor sees the connect action; an authenticated session is
intended to replace it with the avatar, username, and role-aware menu. The
backend remains the authority for Discord ID, membership, and management
permissions.

The local OAuth start boundary was observed, but a complete
OAuth callback was **not verified in this run** because the internal browser
session remained at the Discord login screen. No authenticated identity,
avatar, role, or manager proof is claimed by this record. The next integration
check must use an authorized test Discord session and verify both an allowed
manager path and a denied non-manager path without recording member data.

## Residual limits

The visual reader intentionally does not expose the original PDF or a download
control. Browser-visible material cannot be made impossible to screenshot, OCR,
inspect with developer tools, or manually submit to another service; the UI
states this limitation instead of promising an impossible protection.

The ACLClouds legacy backup remains retained until the owner completes the
separate rollback-retention decision. This document does not authorize deleting
that backup or changing provider permissions.
