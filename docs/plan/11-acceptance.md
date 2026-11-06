# 11 — Acceptance criteria and tests

| ID | Scenario | Required result |
|---|---|---|
| CA-01 | Member without invitation tries to enter | Denied and recorded |
| CA-02 | Discord disconnects after creation | Safe local policy; no implicit grant |
| CA-03 | AI requests `work on Seloryn` | Resolves only an authorized project and shows valid state/task |
| CA-04 | AI requests an ambiguous name | Asks before changing any project |
| CA-05 | One AI occupies `auth.register` | Another AI cannot reserve incompatible logic |
| CA-06 | Backend implements a route used by frontend | Conversation, versioned contract, and integration tests available |
| CA-07 | Backend session is offline | Request remains pending; no false automatic response |
| CA-08 | Two patches arrive with the same base | One applied; the other revalidated or rejected with conflict |
| CA-09 | Project closes during patch | No write accepted after closing; session receives signal and can recover state |
| CA-10 | Project is closed | No patches, claims, merge, or deployment; permitted reading remains |
| CA-11 | Small edit does not need official version | Versioned and recoverable without PR or deployment |
| CA-12 | Master candidate changes after approval | Approval invalidated; new review required |
| CA-13 | AI reviews a change it created | Denied for lack of independence |
| CA-14 | Authorized AI reviews a low-risk change | Approves only with verified evidence and allowed policy |
| CA-15 | Authentication change has only AI opinion | Blocked until defined human approval |
| CA-16 | Tests failed but AI wrote “approved” | Do not integrate into master |
| CA-17 | GitHub rule blocks merge | Show the real block, not “approved and published” |
| CA-18 | Master version was approved | Do not deploy without its own authorization stage |
| CA-19 | API contract changed incompatibly | Alert consumers; block integration until reconciliation |
| CA-20 | Unauthorized client asks to see another project | No cross-data through API, search, logs, events, or cache |

Run concurrency tests with 9 sessions, varied latency, retries, dropped
connections, and concurrency in distinct and overlapping logical resources. Also
verify that a local connector without write control **cannot** fool Central into
publishing changes outside the gateway.
