# Stage 2b: MVP Part 2 — Risk & Validation

**Goal:** Evidence bundles + post-purchase validation + dispute system + risk rate monitoring + Risk tab with real data.

Created ONLY after user approves MVP 2a gate.

---

## Task Dependency Graph

```
STAGE 2b: MVP Part 2
  Task 0f: skill-discovery-evidence      owner: builder-evidence
  Task 15: build-evidence                owner: builder-evidence          blocked_by: [0f]
  Task 16: validate-evidence             owner: validator-evidence        blocked_by: [15]

  Task 0g: skill-discovery-disputes      owner: builder-disputes
  Task 17: build-disputes                owner: builder-disputes          blocked_by: [0g, 16]
  Task 18: validate-disputes             owner: validator-disputes        blocked_by: [17]

  Task 0h: skill-discovery-risk          owner: builder-risk-metrics
  Task 19: build-risk-metrics            owner: builder-risk-metrics      blocked_by: [0h, 16]
  Task 20: validate-risk-metrics         owner: validator-risk-metrics    blocked_by: [19]

  Task 0i: skill-discovery-risk-tab      owner: builder-risk-tab
  Task 21: build-risk-tab                owner: builder-risk-tab          blocked_by: [0i, 18, 20]
  Task 22: validate-risk-tab             owner: validator-risk-tab        blocked_by: [21]

  Task 23: mvp2b-integration             owner: lead                      blocked_by: [18, 20, 22]
  Task 24: mvp2b-demo                    owner: lead                      blocked_by: [23]

  --- GATE: Lead presents risk management, evaluates MVP 2b gate, asks user "Proceed to Production?" ---
```

---

## builder-evidence — Spawn Prompt

> **NOTE:** Expand through teammate-maker before spawning.

```
## Role
You are the builder-evidence teammate. Your ONE job: build the evidence bundle
creation and update system for OpenPay v3 transactions.

## Task 0: Skill Discovery (MANDATORY)
Load relevant skills, especially spec-validator for self-checking.

## Spec
Read `CLAUDE.md`:
- "Evidence Bundle" section (full schema)
- "Purchase Webhooks" → purchase-request step 9, purchase-complete step 4

## Scope
- api/src/services/evidence.py
- api/tests/test_evidence.py

## What to Build

1. **evidence.py**:
   - `create_evidence_bundle(intent, account_state, policy_checks) -> dict`
     Creates the JSONB bundle per the Evidence Bundle schema in CLAUDE.md.
   - `update_evidence_execution(transaction_id, execution_result) -> dict`
     Updates existing bundle with execution_result from post-purchase validation.
     Compares intent_snapshot (amount, merchant) vs execution_result.
     Sets flagged=True if amount mismatch > 5% or merchant mismatch.

2. **test_evidence.py** (write FIRST):
   - Bundle creation with all fields
   - Bundle update with matching execution → flagged=False
   - Bundle update with amount mismatch > 5% → flagged=True
   - Bundle update with merchant mismatch → flagged=True

## MCP Servers
- supabase: for reading/updating transaction evidence JSONB

## Constraints
- Function signatures MUST match Interface Contracts in ORCHESTRATOR_PROMPT.md
- Evidence schema MUST match CLAUDE.md Evidence Bundle section exactly

## Commit After Task Completion
git add scoped files, commit with detailed message, push.
```

---

## builder-disputes — Spawn Prompt

> **NOTE:** Expand through teammate-maker before spawning.

```
## Role
You are the builder-disputes teammate. Your ONE job: build the dispute
filing endpoint and eligibility logic.

## Task 0: Skill Discovery (MANDATORY)
Load spec-validator and any relevant skills.

## Spec
Read `CLAUDE.md`:
- "Dispute System" section (types, flow, eligibility, trust deltas)
- "Trust Score System" → score delta table

## Scope
- api/src/routes/transactions.py (ADD dispute endpoint — coordinate with lead about existing file)
- api/tests/test_disputes.py

## What to Build

1. **PUT /api/transactions/:id/dispute** endpoint:
   - Accept { type: "unauthorized" | "wrong_item" | "fulfillment_issue" }
   - Record dispute_type and dispute_at on transaction
   - Update status to "disputed"
   - Check eligibility: within constraints, evidence complete, within 7 days, valid type
   - Apply trust delta: unauthorized=-12, wrong_item=-10, fulfillment_issue=-5
   - If eligible: credit balance (add amount back to user)
   - Return { transaction_id, dispute_type, eligible, trust_score, old_tier, new_tier, balance_credited? }

2. **test_disputes.py** (write FIRST):
   - File unauthorized dispute → -12 trust delta
   - File wrong_item dispute → -10 trust delta
   - File fulfillment_issue → -5 trust delta
   - Eligible dispute → balance credited
   - Ineligible (>7 days) → no credit
   - Ineligible (incomplete evidence) → no credit

## MCP Servers
- supabase: for transaction/agent/user queries

## Constraints
- Trust deltas MUST match CLAUDE.md exactly
- The existing mark endpoint ("good" → +5) stays. Dispute endpoint is NEW, not a replacement.

## Commit After Task Completion
git add scoped files, commit with detailed message, push.
```

---

## builder-risk-metrics — Spawn Prompt

> **NOTE:** Expand through teammate-maker before spawning.

```
## Role
You are the builder-risk-metrics teammate. Your ONE job: build the risk rate
calculation and the GET /api/users/:id/risk endpoint.

## Task 0: Skill Discovery (MANDATORY)
Load relevant skills.

## Spec
Read `CLAUDE.md`:
- "Risk Metrics" section (rates, endpoint, response schema)
- "Trust Score System" → Risk Rate Escalation (bands, actions)

## Scope
- api/src/services/risk_metrics.py
- api/tests/test_risk_metrics.py

## What to Build

1. **risk_metrics.py**:
   - `compute_risk_rates(agent_id) -> dict`
     Query transactions from last 30 days. Count by status and dispute_type.
     Calculate rates. Determine worst-case escalation band.
     Return schema per CLAUDE.md Risk Metrics section.

2. **Add route** (coordinate with lead for registration):
   - GET /api/users/:id/risk → calls compute_risk_rates, returns result

3. **test_risk_metrics.py** (write FIRST):
   - No disputes/flags → all rates 0, status "normal"
   - 1 dispute in 50 completions → 2% → "elevated"
   - 2 disputes in 50 completions → 4% → "restricted"
   - 3 disputes in 50 completions → 6% → "frozen"
   - Mixed rates → worst-case determines status

## MCP Servers
- supabase: for transaction queries

## Constraints
- Function signature MUST match Interface Contracts in ORCHESTRATOR_PROMPT.md
- ~15 lines core logic — keep it simple
- 30-day window is rolling from current date

## Commit After Task Completion
git add scoped files, commit with detailed message, push.
```

---

## builder-risk-tab — Spawn Prompt

> **NOTE:** Expand through teammate-maker before spawning.

```
## Role
You are the builder-risk-tab teammate. Your ONE job: build the Risk tab
component for the OpenPay dashboard with real data from the risk endpoint.

## Task 0: Skill Discovery (MANDATORY)
Load frontend-design skill and its cookbook.

## Spec
Read `CLAUDE.md`:
- "Frontend Pages" → Risk Tab section
- "Risk Metrics" → endpoint response schema
- "Evidence Bundle" → schema for evidence viewer

## Scope
- frontend/components/RiskTab.tsx (REPLACE placeholder with real implementation)

## MCP Servers
- context7: for React/Tailwind docs
- playwright: for visual testing

## What to Build

1. **RiskTab.tsx** with real data:
   - Fetch from GET /api/users/:id/risk
   - Metric cards: 4 rate percentages with trend indicators
   - Escalation status badge with explanation text
   - Recent disputes table (fetch from transactions with ?status=disputed)
   - Evidence bundle viewer: expandable accordion per transaction showing full bundle JSON
   - Stripe-inspired design: clean tables, color-coded badges, subtle borders

## Constraints
- Fetch from Flask API, not Supabase directly
- Must work with the existing tab structure in page.tsx

## Commit After Task Completion
git add scoped files, commit with detailed message, push.
```

---

## mvp2b-integration — Lead Task

1. Pull evidence, disputes, risk metrics code
2. Wire risk rate checks into constraints.py (replace mock _check_risk_rates)
3. Wire evidence bundle creation into webhooks.py purchase-request
4. Wire evidence update into webhooks.py purchase-complete
5. Register risk endpoint
6. Pull risk tab, verify it renders with real data
7. Run all tests

## mvp2b-demo — Lead Task

1. Demonstrate evidence bundle on a new purchase
2. Demonstrate post-purchase validation (flag a mismatched transaction)
3. Demonstrate dispute filing (all 3 types)
4. Show risk metrics updating in real time
5. Show Risk tab with real data
6. Evaluate MVP 2b gate criteria
7. **Ask user: "MVP 2b gate criteria pass/fail. Proceed to Production?"**
