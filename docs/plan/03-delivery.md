# 03 — Client interview, initial architecture, and team delivery

The product/documentation owner **is not just someone who writes text**. They
translate the client's real problem into team execution. They **also create the
first architecture sketch**, always validated by the technical lead, QA, and
infrastructure whenever there is impact.

## Journey — from conversation to first line of code

### 1. Prepare and interview the client

- Identify who uses, pays, decides, and knows the daily work.
- First understand the **existing problem**, not only the screen the client requested.
- Ask how the task works today, what causes errors, what takes time, what happens
  without internet, who has access, which data is stored, and what must integrate.
- Demonstrate understanding with real examples: “If two employees perform the
  same operation together, what should happen?”
- Separate essential, desirable, out-of-scope, and not-yet-understood items.
- Get permission to record a meeting and take care with personal data/secrets;
  never put sensitive real data into prompts without an appropriate legal/contractual basis.

### 2. Write testable requirements

Each requirement should contain ID, problem, simple story, rule, permission,
priority, acceptance criteria, dependency, and open question. Example:

> `REQ-012` — A receptionist can book an appointment in a free slot; if another
> person chooses the same time, only one reservation should win. **Test:**
> simulate two simultaneous reservations; expected result: one success and one understandable conflict.

### 3. Design the solution before code

Prepare: screens/flows with the designer; modules with the technical lead;
entities and relationships; contracts/API; external integration and boundaries;
access risks; environments; tests; and a record of rejected architecture options
and why. When a technical decision is unclear, record `PENDING` rather than inventing it.

### 4. Plan tasks

Break deliveries into small, observable units with dependencies. Assign owners by
**outcome**, not only by file. Example: `TASK-17 Create appointment reservation`
depends on `TASK-08 practitioner registration` and `TASK-11 available hours`.

### 5. Produce the starter ZIP

The ZIP is a **versioned starting package** with an organized tree, approved
documentation, example files, and initial contracts. It includes README,
decisions, requirements, app/service structure, test planning, and example
configuration, but **not** credentials, real client data, caches, or installed
dependencies. It is not a promise of a complete working project.

### 6. Kickoff and acceptance meeting

The technical lead reviews feasibility, alternatives, and module interfaces; the
designer reviews flows; QA reviews criteria; infrastructure reviews deployment
and security. Only afterward does the package become an active Central project.
The client validates scope and commercial dates before a delivery is promised.

## Required package content

```text
client-project/
├── README.md                      # context, instructions, and package status
├── manifest.json                  # identifier, version, and planned modules
├── docs/
│   ├── briefing.md                # client, problem, people, and goals
│   ├── requirements.md            # numbered rules, criteria, and priorities
│   ├── scope.md                   # in/out, dependencies, and constraints
│   ├── flows.md                   # step-by-step use and interface states
│   ├── architecture.md            # decisions and boundaries for each part
│   ├── data-and-permissions.md    # entities and who can access them
│   ├── integrations.md            # external services, risks, and contracts
│   ├── test-plan.md               # real scenarios and non-functional requirements
│   ├── delivery.md                # stages, owners, questions, and approvals
│   └── decisions/ADR-0001.md      # why this architecture was chosen
├── apps/
│   ├── web/                       # include when there is a web application
│   └── mobile/                    # include only when there is a mobile app
├── services/api/                  # include when the system has an API
├── packages/contracts/            # shared formats and specifications
├── infra/                         # example configuration, without secrets
└── tests/                         # initial cases and tests
```

**The tree must follow the project.** Do not create a `mobile` folder or a
microservice just because the template has one; the generator removes areas that
do not apply. A single well-organized application is acceptable.

## `manifest.json`: identity and responsibility

- Project ID and name; client and environment (without confidential data in
  public files); application type; modules; external systems; product owner;
  architecture approval; package version; repository origin; risks and open items.
- Central reads the manifest, compares it with a valid schema, creates initial
  tasks, requests review, and records history. Do not execute unknown scripts
  automatically when importing a ZIP.

## Criteria for releasing to the team

- [ ] Problem and expected result are written in plain language.
- [ ] Scope and exclusions are clear; essential tasks are prioritized.
- [ ] Main requirements have an acceptance test.
- [ ] Flows and permissions were reviewed.
- [ ] Technical architecture is **approved**, not merely generated.
- [ ] Project tree matches the contracted modules.
- [ ] ZIP opens correctly, without passwords, tokens, or real data.
- [ ] Client approved scope; team accepted the estimate.
- [ ] Open decisions have an owner and resolution date.

## Rule for later changes

A new request enters as a scope change: record impact on cost, dependencies,
architecture, work already completed, and schedule; require the client's decision
before changing team priorities.
