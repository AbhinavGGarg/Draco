# Stage 1: POC

**Goal:** Prove the core idea works. Flask + Supabase + trust score + constraints + mock payment flow. No frontend, no OpenClaw, no real Stripe/Rye. Curl demos only.

---

## Task Dependency Graph

```
STAGE 1: POC
  Task 0a: skill-discovery-foundation    owner: builder-foundation
  Task 1:  build-foundation              owner: builder-foundation        blocked_by: [0a]
  Task 2:  validate-foundation           owner: validator-foundation      blocked_by: [1]

  Task 0b: skill-discovery-core          owner: builder-core-purchase
  Task 3:  build-core-purchase           owner: builder-core-purchase     blocked_by: [0b, 2]
  Task 4:  validate-core-purchase        owner: validator-core-purchase   blocked_by: [3]

  Task 5:  poc-integration               owner: lead                      blocked_by: [4]
  Task 6:  poc-demo                      owner: lead                      blocked_by: [5]

  --- GATE: Lead presents demo, evaluates POC gate criteria, asks user "Proceed to MVP 2a?" ---
```

## Task Creation Sequence

```
TaskCreate({ subject: "skill-discovery-foundation", description: "Task 0: builder-foundation discovers and loads relevant skills" })
TaskCreate({ subject: "build-foundation", description: "Flask scaffold, Supabase client, DB schema, health endpoint, user CRUD, seed skeleton" })
TaskCreate({ subject: "validate-foundation", description: "Verify Flask starts, health OK, user CRUD works, schema correct" })
TaskCreate({ subject: "skill-discovery-core", description: "Task 0: builder-core-purchase discovers and loads relevant skills" })
TaskCreate({ subject: "build-core-purchase", description: "Trust score, constraints, agent routes, transaction routes, webhook endpoints with mock Stripe/Rye" })
TaskCreate({ subject: "validate-core-purchase", description: "Verify trust score, constraints, webhooks, mock purchase flow" })
TaskCreate({ subject: "poc-integration", description: "Wire blueprints, register routes, run full mock purchase flow" })
TaskCreate({ subject: "poc-demo", description: "Curl-based demo of happy path, evaluate POC gate criteria" })

// Set dependencies
TaskUpdate({ taskId: "<build-foundation-id>", addBlockedBy: ["<skill-discovery-foundation-id>"] })
TaskUpdate({ taskId: "<validate-foundation-id>", addBlockedBy: ["<build-foundation-id>"] })
TaskUpdate({ taskId: "<build-core-purchase-id>", addBlockedBy: ["<skill-discovery-core-id>", "<validate-foundation-id>"] })
TaskUpdate({ taskId: "<validate-core-purchase-id>", addBlockedBy: ["<build-core-purchase-id>"] })
TaskUpdate({ taskId: "<poc-integration-id>", addBlockedBy: ["<validate-core-purchase-id>"] })
TaskUpdate({ taskId: "<poc-demo-id>", addBlockedBy: ["<poc-integration-id>"] })
```

---

## builder-foundation — Spawn Prompt

> **NOTE:** Expand this prompt through the teammate-maker skill before spawning.
> It adds Task 0 steps, MCP philosophy, commit protocol, report format, and escalation rules.

```
## Role
You are the builder-foundation teammate. Your ONE job: set up the Flask app
scaffold, Supabase client, database schema, requirements, seed script skeleton,
and verify the foundation works end-to-end.

## Spec
Read `CLAUDE.md`. Focus on:
- "How to Run Locally" section
- "Database Schema" section (full SQL — note v3 columns: evidence, dispute_type, dispute_at)
- "Directory Structure" section
- "Environment Variables" section

## Scope
You own these files and ONLY these files:
- api/app.py
- api/src/db.py
- api/src/__init__.py
- api/requirements.txt
- scripts/seed_demo.py (skeleton only — user + agent + placeholder transactions)
- scripts/reset_trust_score.py

Do NOT create route files, service files, or frontend/.

## MCP Servers
- supabase: for applying the database schema (execute_sql)

## What to Build

1. **api/requirements.txt**: flask, flask-cors, python-dotenv, supabase, stripe, requests

2. **api/src/db.py** — Supabase client:
   Load .env from project root, init client with SUPABASE_URL and SUPABASE_KEY, export `supabase`.

3. **api/src/__init__.py** — empty or minimal

4. **api/app.py** — Flask entry point:
   - Load .env, create Flask app, enable CORS (localhost:3000)
   - User CRUD routes: POST /api/users, GET /api/users/<id>
   - GET /health → {"status": "ok"}
   - Blueprint imports commented out (ready for integration):
     ```python
     # from api.src.routes.agents import agents_bp
     # from api.src.routes.transactions import transactions_bp
     # from api.src.routes.webhooks import webhooks_bp
     ```
   - Run on port 5000

5. **Database schema** — Apply via Supabase MCP (execute_sql):
   EXACT SQL from CLAUDE.md "Database Schema" section. Three tables: users, agents, transactions.
   IMPORTANT: transactions includes v3 columns (evidence JSONB, dispute_type, dispute_at).

6. **scripts/seed_demo.py** — skeleton:
   Demo user (demo@openpay.com), agent (score: 50), 5 transactions (3 completed, 1 failed, 1 wrong_item).
   Trust score ends at 48.

7. **scripts/reset_trust_score.py** — reset agent score to 50

## Self-Validation
1. `pip install -r api/requirements.txt`
2. `python -c "from api.src.db import supabase; print(supabase)"` — no error
3. Flask starts, `curl localhost:5000/health` → {"status": "ok"}
4. POST /api/users creates user, GET /api/users/<id> returns it

## Constraints
- Do NOT import anthropic or call Claude API directly
- Do NOT create route files, service files, or frontend/
- Blueprint imports for other teammates' routes: commented out
```

---

## validator-foundation — Spawn Prompt

> **NOTE:** Expand through teammate-maker. Validator is READ-ONLY (no Write/Edit).

```
## Role
You are the validator-foundation teammate. READ-ONLY. Verify Flask foundation,
Supabase connection, and user CRUD work in the real project directory.

## Spec
Read `CLAUDE.md`: "Database Schema", "How to Run Locally", "Flask API Endpoints" → Users

## Scope
Inspect (do NOT modify): api/app.py, api/src/db.py, api/requirements.txt, scripts/

## MCP Servers
- supabase: read-only queries

## Checks
1. **Files**: api/app.py, api/src/db.py, api/requirements.txt, scripts/seed_demo.py exist
2. **Dependencies**: flask, flask-cors, python-dotenv, supabase, stripe in requirements.txt
3. **Schema** (query Supabase): users, agents, transactions tables with correct columns
   — transactions MUST have evidence, dispute_type, dispute_at columns
   — NO chat_messages table
4. **Flask starts**: `cd /Users/davidchen/OpenPay-v3 && python api/app.py &` → no error
   — `curl localhost:5000/health` → {"status": "ok"}
5. **User CRUD**: POST creates user, GET returns it
6. **Code quality**: .env loaded correctly, no hardcoded keys, CORS enabled
```

---

## builder-core-purchase — Spawn Prompt

> **NOTE:** Expand through teammate-maker before spawning.

```
## Role
You are the builder-core-purchase teammate. Your ONE job: build the trust score engine,
constraint enforcement, agent routes, transaction routes, and purchase webhook endpoints
with MOCK Stripe and Rye.

## Spec
Read `CLAUDE.md`. Focus on:
- "Trust Score System" (tiers, score deltas, risk rate escalation)
- "Flask API Endpoints" → Agent, Transactions, Purchase Webhooks
- "Database Schema" → agents, transactions (note v3 columns)
- "Dispute System" (trust deltas per type)
- "Risk Metrics" (rate calculation, escalation bands)

## Scope
- api/src/services/trust_score.py
- api/src/services/constraints.py
- api/src/routes/agents.py
- api/src/routes/transactions.py
- api/src/routes/webhooks.py
- api/src/services/stripe_service.py (MOCK)
- api/src/services/rye_service.py (MOCK)
- api/tests/test_trust_score.py
- api/tests/test_constraints.py

Do NOT modify api/app.py or api/src/db.py.

## MCP Servers
- supabase: for querying/updating agent and transaction data
- context7: for verifying SDK patterns

## What to Build

1. **trust_score.py**:
   - `score_to_tier(score) -> str` — thresholds per CLAUDE.md
   - `apply_score_delta(agent_id, delta) -> dict` — read, apply, clamp 0-100, write back

2. **constraints.py**:
   - `enforce_constraints(agent_id, amount, merchant, category) -> dict`
     Steps: frozen check → risk rate check (MOCK in POC) → amount → category/merchant → balance → weekly
     Returns `{"decision": "APPROVE"|"DENY"|"PAUSE_FOR_REVIEW", "reason": ...}`
   - Risk rate mock:
     ```python
     # MOCK: replace with real risk_metrics in MVP 2b
     def _check_risk_rates(agent_id):
         return {"status": "normal"}
     ```

3. **agents.py** (blueprint: agents_bp, prefix='/api'):
   - GET /users/<id>/agent — with derived tier
   - PUT /users/<id>/agent/constraints — merge partial
   - POST /users/<id>/agent/reset-score — reset to 50

4. **transactions.py** (blueprint: transactions_bp, prefix='/api'):
   - GET /users/<id>/transactions — optional ?status= filter
   - PUT /transactions/<id>/mark — "good" (+5) or "wrong_item" (-10)

5. **webhooks.py** (blueprint: webhooks_bp, prefix='/api'):
   - POST /webhook/purchase-request: enforce → create transaction → mock Stripe → mock Rye
   - POST /webhook/purchase-complete: update status, decrement balance, +3 trust

6. **stripe_service.py** (MOCK): create_customer, attach_payment_method, charge — all return mock IDs
7. **rye_service.py** (MOCK): checkout — returns mock order_id

8. **test_trust_score.py** (write FIRST): boundary tests (0,25,26,50,51,75,76,100), clamping
9. **test_constraints.py** (write FIRST): frozen→DENY, overspend→DENY, blocked category→DENY,
   insufficient balance→DENY, weekly limit→DENY, all pass→APPROVE, tier override test

## Self-Validation
1. py_compile all service and route files
2. `pytest api/tests/test_trust_score.py -v` — ALL pass
3. `pytest api/tests/test_constraints.py -v` — ALL pass

## Constraints
- Import db from api.src.db (assume it exists)
- Do NOT modify api/app.py
- Signatures MUST match Interface Contracts in ORCHESTRATOR_PROMPT.md
- Use v3 format: `{"decision": "APPROVE"|"DENY"|"PAUSE_FOR_REVIEW"}` NOT `{"approved": bool}`
```

---

## validator-core-purchase — Spawn Prompt

> **NOTE:** Expand through teammate-maker. Validator is READ-ONLY.

```
## Role
You are the validator-core-purchase teammate. READ-ONLY. Verify trust score,
constraints, and purchase webhooks work correctly.

## Spec
Read `CLAUDE.md`: "Trust Score System", "Flask API Endpoints" → Agent/Transactions/Webhooks, "Database Schema"

## Scope
Inspect: api/src/services/, api/src/routes/, api/tests/

## MCP Servers
- supabase: read-only queries

## Checks
1. **Interface contracts**: score_to_tier, apply_score_delta, enforce_constraints match signatures
   — enforce_constraints returns {decision, reason} NOT {approved: bool}
2. **Tests**: `pytest api/tests/test_trust_score.py -v` all pass, boundary values tested
3. **Tests**: `pytest api/tests/test_constraints.py -v` all pass, all 6 denial reasons + tier override
4. **Agent routes** (curl): GET agent has tier field, PUT constraints merges, POST reset sets 50
5. **Transaction routes**: GET returns list, PUT mark applies correct deltas
6. **Webhooks**: purchase-request APPROVE/DENY, purchase-complete updates status + balance + trust
7. **Mocks**: stripe_service.py and rye_service.py clearly marked with # MOCK
```

---

## poc-integration — Lead Task

After validator-core-purchase passes:

1. Pull builder-core-purchase code from sandbox into main project
2. Uncomment blueprint registration in `api/app.py`:
   ```python
   from api.src.routes.agents import agents_bp
   from api.src.routes.transactions import transactions_bp
   from api.src.routes.webhooks import webhooks_bp
   app.register_blueprint(agents_bp)
   app.register_blueprint(transactions_bp)
   app.register_blueprint(webhooks_bp)
   ```
3. Run `python -m pytest api/tests/ -v` — all tests pass
4. Start Flask, run seed script
5. Verify full mock purchase flow via curl:
   - Create user → create agent → purchase-request → purchase-complete
   - Check trust score changed, balance decremented, transaction created

## poc-demo — Lead Task

Present the demo to the user:
1. Show Flask health, user CRUD, agent CRUD
2. Walk through a mock purchase flow (curl commands and responses)
3. Show trust score changes and constraint enforcement
4. Evaluate each POC gate criterion
5. **Ask user: "POC gate criteria pass/fail. Proceed to MVP 2a?"**
6. Wait for approval. Do NOT create MVP 2a tasks until approved.
