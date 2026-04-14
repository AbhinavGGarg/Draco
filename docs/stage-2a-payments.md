# Stage 2a: MVP Part 1 — Payment Workflow

**Goal:** Full purchase flow end-to-end with real services + 4-tab dashboard + iMessage.

Created ONLY after user approves POC gate.

---

## Task Dependency Graph

```
STAGE 2a: MVP Part 1
  Task 0c: skill-discovery-payments     owner: builder-real-payments
  Task 7:  build-real-payments          owner: builder-real-payments     blocked_by: [0c]
  Task 8:  validate-real-payments       owner: validator-real-payments   blocked_by: [7]

  Task 0d: skill-discovery-openclaw     owner: builder-openclaw
  Task 9:  build-openclaw               owner: builder-openclaw          blocked_by: [0d]
  Task 10: validate-openclaw            owner: validator-openclaw        blocked_by: [9]

  Task 0e: skill-discovery-frontend     owner: builder-frontend
  Task 11: build-frontend               owner: builder-frontend          blocked_by: [0e]
  Task 12: validate-frontend            owner: validator-frontend        blocked_by: [11]

  Task 13: mvp2a-integration            owner: lead                      blocked_by: [8, 10, 12]
  Task 14: mvp2a-demo                   owner: lead                      blocked_by: [13]

  --- GATE: Lead presents full flow, evaluates MVP 2a gate criteria, asks user "Proceed to MVP 2b?" ---
```

---

## builder-real-payments — Spawn Prompt

> **NOTE:** Expand this prompt through the teammate-maker skill before spawning.

```
## Role
You are the builder-real-payments teammate. Your ONE job: replace the mock
Stripe and Rye services with real test-mode integrations.

## Task 0: Skill Discovery (MANDATORY)
1. Scan skills directories
2. If no Stripe SDK skill exists, create one via skill-creator (scrape Stripe Python SDK docs)
3. If no Rye API skill exists, create one via skill-creator (scrape Rye docs)
4. Report loaded/created skills

## Spec
Read `CLAUDE.md`:
- "Flask API Endpoints" → Card/Payment Setup, Balance
- "Test Mode" section (test keys, test cards)
- "Environment Variables" (STRIPE_SECRET_KEY, RYE_API_KEY)

## Scope
- api/src/services/stripe_service.py (REPLACE mock with real)
- api/src/services/rye_service.py (REPLACE mock with real)
- api/tests/test_payments.py

## MCP Servers
- supabase: for storing customer/payment IDs
- context7: for SDK docs lookup

## What to Build

1. **stripe_service.py** — Real Stripe test-mode:
   - create_customer(email) → creates Stripe Customer, returns customer_id
   - attach_payment_method(customer_id, token) → attaches PaymentMethod
   - charge(customer_id, payment_method_id, amount, description) → creates PaymentIntent
   - Use sk_test_ keys only

2. **rye_service.py** — Real Rye staging:
   - checkout(product_url, shipping_address) → submits to Rye API, returns order_id
   - Use staging API key
   - If Rye staging doesn't support a test merchant, keep mock with # MOCKED comment

3. **test_payments.py**:
   - Stripe: create customer, attach tok_visa, charge $10 → succeeds
   - Stripe: charge with 4000000000000002 → declines
   - Rye: checkout with test product URL → returns order (or verify mock)

## Commit After Task Completion
git add scoped files, commit with detailed message, push.

## Constraints
- ONLY use sk_test_ and pk_test_ Stripe keys
- NEVER charge real money
- Function signatures must match existing mock signatures
```

---

## builder-openclaw — Spawn Prompt

> **NOTE:** Expand through teammate-maker before spawning.

```
## Role
You are the builder-openclaw teammate. Your ONE job: configure the OpenClaw
Gateway's buy skill and iMessage channel for OpenPay v3.

## Task 0: Skill Discovery (MANDATORY)
1. Read `.agents/skills/openclaw/SKILL.md` — this is your PRIMARY skill
2. Read the cookbook files it references for buy-skill configuration
3. Scan global skills for any relevant patterns
4. Report loaded skills

## Spec
Read `CLAUDE.md`:
- "OpenClaw Integration" section
- "Messaging Interface (iMessage via OpenClaw)" section
- "Purchase Webhooks" section (what the buy skill calls)

## Scope
- skills/buy/SKILL.md (the custom buy skill)
- OpenClaw gateway configuration
- Any OpenClaw-related config files

## MCP Servers
- supabase: for verifying agent setup
- context7: for OpenClaw docs
- firecrawl: for crawling OpenClaw documentation if needed

## What to Build

1. **skills/buy/SKILL.md** — Custom buy skill:
   Instructions for the agent: "When you've decided what to buy, call
   POST http://localhost:5000/api/webhook/purchase-request with product details.
   Handle three possible decisions: APPROVE (confirm to user), DENY (explain why),
   PAUSE_FOR_REVIEW (tell user purchase needs manual approval)."

2. **Gateway config** — iMessage channel:
   - dmPolicy: allowlist
   - historyLimit: 50
   - Agent model: Claude Sonnet
   - Shopping-expert skill installed
   - Custom buy skill installed

## Constraints
- Agents MUST use the OpenClaw Gateway API, NOT the Anthropic API directly
- The buy skill calls Flask webhooks — it does NOT call Stripe or Rye
- Follow the openclaw skill's cookbook patterns exactly
```

---

## builder-frontend — Spawn Prompt

> **NOTE:** Expand through teammate-maker before spawning.

```
## Role
You are the builder-frontend teammate. Your ONE job: build the 4-tab Next.js
dashboard for OpenPay v3 with Stripe-inspired design.

## Task 0: Skill Discovery (MANDATORY)
1. Read `~/.claude/skills/frontend-design/SKILL.md` and its cookbook
2. Scan for other relevant skills
3. Report loaded skills

## Spec
Read `CLAUDE.md`:
- "Frontend Pages (Next.js + Tailwind)" section (all 4 tabs)
- "Flask API Endpoints" (what the frontend calls)
- "Directory Structure" → frontend/

## Scope
- frontend/** (entire frontend directory)

## MCP Servers
- context7: for Next.js/React/Tailwind docs
- playwright: for browser testing

## What to Build

1. **app/page.tsx** — Single page, 4 tabs (Overview, Transactions, Risk, Settings)

2. **components/OverviewTab.tsx**:
   - Balance, trust score + tier badge, risk status badge (normal/elevated/restricted/frozen)
   - Total spent this week/month, last 5 transactions

3. **components/TransactionsTab.tsx**:
   - Full history table: Date, Merchant, Product, Amount, Category, Status
   - Status badges: pending (yellow), completed (green), failed (red), returned (gray),
     disputed (orange), flagged (purple)
   - Dispute actions per row: Mark as good, Unauthorized, Wrong item, Fulfillment issue

4. **components/RiskTab.tsx**:
   - Metric cards: dispute rate, flagged rate, unauthorized rate, wrong-item rate
   - Escalation status with explanation
   - Recent disputes table
   - Evidence bundle viewer (expandable per transaction)
   NOTE: In MVP 2a, Risk tab can show placeholder/demo data. Real data wired in MVP 2b.

5. **components/SettingsTab.tsx**:
   - Spending limits, allowed categories, blocked merchants, balance, card input

6. **components/TrustScoreBadge.tsx** — score + tier visual
7. **components/StripeCardInput.tsx** — Stripe Elements
8. **lib/api.ts** — Flask API client helpers for all endpoints

Design: Stripe-inspired. Clean data tables, status badges, metric cards with trend indicators.

## Constraints
- All data fetched from Flask API (NEXT_PUBLIC_FLASK_API_URL)
- No direct Supabase queries from frontend
- Use Tailwind for styling
- No chat interface — messaging is via iMessage
```

---

## mvp2a-integration — Lead Task

1. Pull all builder code, wire together
2. Register all blueprints
3. Run seed script with real Stripe test customer
4. Verify: frontend loads, all 4 tabs render, Stripe card input works
5. Test full flow: OpenClaw agent → buy skill → Flask webhook → Stripe charge → Rye order → dashboard updates
6. If OpenClaw not working yet, test with curl-based flow first

## mvp2a-demo — Lead Task

1. Present full purchase flow to user
2. Show 4-tab dashboard with real data
3. Evaluate MVP 2a gate criteria
4. **Ask user: "MVP 2a gate criteria pass/fail. Proceed to MVP 2b?"**
5. Wait for approval.
