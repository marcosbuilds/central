# 02 — Frontend, backend, and systems: real examples

## What each area means

**Frontend** is what a person sees and uses: menus, buttons, forms, registration
screens, charts, and notifications. It may be a **website**, **mobile app**,
**desktop program**, or machine panel.

**Backend** receives requests from screens and applies rules: checks passwords,
checks inventory, calculates values, records data, talks to external services,
and authorizes operations.

**A system** is not only backend. It is the set of frontend, backend, data,
integrations, processes, security, tests, and operations that solves a need.
Some systems work without screens; others include web, mobile, and desktop at once.

## Example A — Clinic that wants appointment scheduling

**Client problem:** patients call too often and time slots conflict.

1. **Product/documenter** interviews reception and practitioners: hours,
   overbooking, cancellations, confirmations, access rules, and sensitive data.
   Produces requirements, flows, entity designs, and the initial package.
2. **Design** shows how to choose a date and doctor and receive confirmation.
3. **Frontend** builds the patient screen and reception dashboard.
4. **Backend** checks availability, prevents double booking, records appointments,
   and sends reminders.
5. **Infrastructure** provides test environment, authentication, backups, and monitoring.
6. **QA** tests two people booking the same time, internet failure, cancellation, and accessibility.
7. **Everyone** reviews the result with the clinic before launch.

**Delivery:** not just a website: an appointment system with rules, database,
dashboard, and integrations. Health data requires additional care with LGPD and
scope; do not start without appropriate review.

## Example B — Store with inventory and sales

- **Web frontend:** product and order dashboard.
- **Mobile/desktop frontend:** app for checking inventory, including offline mode
  if contracted.
- **Backend:** controls stock in/out, prevents selling above inventory, and
  integrates payments/invoices when planned.
- **Product/documenter:** discovers how the store works in practice and decides what comes first.
- **QA + infrastructure + design:** ensure the result is usable, verifiable, and stable.
- **Final system:** dashboard + app + API + data + integrations and routines.

## Example C — Company that receives email files and fills spreadsheets manually

- The product may be **an automation without a complex interface**: retrieve
  authorized files, validate, transform data, record the result, and report failures.
- Backend/integrations take more of the work; frontend delivers a small dashboard
  only if needed; QA validates bad files and errors; documentation defines rules;
  infrastructure monitors.

## Example D — Startup's own internal platform

- **Frontend:** dashboard, project list, file tree, comments, and live work.
- **Backend:** login, permissions, tasks, reservations, history, and agent APIs.
- **Local connector:** reads authorized Codex/Claude events and sends developer activity.
- **QA:** simulates two AIs attempting to change the same module.
- **Infrastructure:** operations, deployment, and security.
- **Product/documenter:** specifies Central's flows and rules before coding.

## What not to confuse

- Having 3 backend developers does not mean one builds a “site” and another a
  “system”. They may work on the same product with module responsibilities.
- An interface can use different technologies; do not assume that a web frontend
  developer automatically masters native mobile.
- The client should see **outcome**, not technical nomenclature: less manual work,
  fewer errors, better support, more control, or a new revenue source.
