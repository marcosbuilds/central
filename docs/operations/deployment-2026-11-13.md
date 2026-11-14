# Peace public learning deployment record

Date: 2026-11-13
Scope: ACLClouds backend package, Discord-linked learning flow, and public
frontend smoke verification

## Result

The ACLClouds backend package from commit `7f433e1` was imported, moved from
its temporary upload directory to the runtime root, and restarted. The
temporary empty directory was moved to the provider trash after the move was
verified. The previous runtime files remain in the provider directory
`legacy-backup-2026-11-13` until the public frontend deployment is verified.

The backend is online and reports Discord connectivity. The public Netlify
frontend was not redeployed during this operation; the public domain still
serves the previous frontend version.

## Verification evidence

| Surface | Check | Result |
| --- | --- | --- |
| Local Peace suite | `python -m pytest tests/peace -q` | 157 passed, 1 known `audioop` deprecation warning |
| Local route server | `python ops/peace_site_server.py --port 4173` with public route smoke requests | `/`, `/estudos/`, `/estudos/civil/`, `/estudos/peace/`, `/meu-processo/`, `/gerencia/`, and `/prova/` returned 200 |
| ACL liveness | `/healthz` | 200; backend service healthy |
| ACL status | `/api/status` | 200; `status=ok`, Discord connected |
| ACL OAuth boundary | `/api/auth/discord/session` without a session | 401 with the expected OAuth-session error |
| ACL candidate boundary | `/api/exams/process` without a session | 401 with the expected OAuth-session error |
| ACL management boundary | `/api/exams/assignments` without a session | 401 with the expected OAuth-session error |
| ACL OAuth start | `/api/auth/discord/start` | 302 to Discord authorization |
| Public homepage | Netlify `/` | 200, but the older frontend is still served |
| Public study route | Netlify `/estudos/` | 404 |
| Public process route | Netlify `/meu-processo/` | 404 |
| .NET release checks | `dotnet build/test Central.sln -c Release` | Not executed: `dotnet` is unavailable on this host |

The tracked `bot/site/_redirects` already contains the study, process, OAuth,
and exam routes. The production 404s therefore indicate a missing Netlify
publication of the tracked frontend, not a missing route in the checked-out
source.

## Cleanup and rollback

The temporary upload wrapper is gone from the active root and is recoverable
from the provider trash. The legacy backup is deliberately retained because
the public frontend smoke checks are not green. It must not be deleted until
the Netlify frontend is published, the public routes above return the expected
responses, and the owner confirms the rollback is no longer needed.

No credentials, OAuth secrets, tokens, cookies, Discord member data, provider
IP addresses, or local paths are recorded in this document.
