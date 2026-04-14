# OpenPay — Shared Development Guide

## Project Overview

OpenPay is a PayFac-style liability and risk management layer for AI agent commerce. One Flask API, one Next.js frontend, one shared Supabase database, one self-hosted OpenClaw Gateway. The platform umbrellas AI agents under a single accountable entity — agents buy things from real online stores on behalf of humans, and OpenPay enforces spending constraints, tracks trust scores, and manages the payment flow.

**Think of it as:** PayPal solved "untrusted eBay sellers can't get merchant accounts." OpenPay solves "AI agents have no legal identity and nobody is liable when they buy things."

**This conversation is the spec.** There is no separate PRD.

---

## Development Principles

**KISS — Keep It Simple.** Every line of code should serve the product. No abstractions "for later," no config systems, no plugin architectures. If a hardcoded string works, use a hardcoded string. If a 10-line function works, don't refactor it into 3 files. Simple code that works beats elegant code that's half-finished.

**YAGNI — You Aren't Gonna Need It.** Don't build anything not described in this file. No crypto/blockchain, no multi-currency, no admin panel, no multi-agent-per-user, no mobile app, no internationalization. If it's not in this doc, don't build it.

**Staged Development — POC → MVP → Production.** This project follows staged development. Read `~/.claude/skills/development-stages/SKILL.md` for gate criteria and stage definitions. Don't jump ahead — each stage must be validated before the next begins.

**TDD — Write Tests First for Critical Paths.** You don't need 100% coverage, but write tests *before* implementation for:
- Trust score computation (tier thresholds, score deltas)
- Constraint enforcement logic (spending limits, category checks, balance validation)
- Stripe tokenization and charge flow
- Purchase request webhook validation

Skip tests for: UI components, OpenClaw skill prompt text. Use `pytest` for Flask, `vitest` for Next.js.

**Prompting — Ask Until You're 100% Sure.** Before writing or modifying any OpenClaw skill, agent prompt, or Claude API call, ask clarifying questions until you have zero ambiguity about: (1) the exact input format, (2) the exact output JSON schema, (3) edge cases, and (4) which model it runs on. Don't guess — ask.

---

## Architecture

```
┌─────────────────────────┐     ┌─────────────────────────┐
│  frontend/              │     │  api/                   │
│  Next.js + Tailwind     │────→│  Flask (Python)         │
│  Port 3000              │HTTP │  Port 5000              │
│                         │     │                         │
│  - Dashboard (4 tabs)   │     │  - User CRUD            │
│  - Transaction history  │     │  - Agent management     │
│  - Risk dashboard       │     │  - Trust score engine   │
│  - Settings/constraints │     │  - Constraint enforcement│
│  - Stripe.js card input │     │  - Risk management      │
│                         │     │  - Post-purchase valid. │
│                         │     │  - Stripe charges       │
│                         │     │  - Rye API checkout     │
│                         │     │  - Purchase webhooks    │
└────────────┬────────────┘     └────────────┬────────────┘
             │                                │
             └──────────┬─────────────────────┘
                        ▼
              ┌──────────────────┐
              │    Supabase      │
              │   (shared DB)    │
              └──────────────────┘

              ┌──────────────────┐
              │  OpenClaw Gateway│
              │  Port 18789      │
              │  (self-hosted)   │
              │                  │
              │  - Shopping agent│
              │  - shopping-     │
              │    expert skill  │
              │  - Custom buy    │
              │    skill (calls  │
              │    Flask webhook)│
              │  - iMessage      │
              │    channel       │
              └──────────────────┘

              ┌──────────────────┐
              │  iMessage        │
              │  (via OpenClaw)  │
              │                  │
              │  User texts →    │
              │  Gateway reads → │
              │  Agent responds  │
              └──────────────────┘
```

**Key architectural decision:** OpenClaw is the conversational/reasoning layer. Flask is the enforcement and payment layer. The agent CANNOT buy anything without Flask approving it. The custom buy skill in OpenClaw calls `POST /api/webhook/purchase-request` on Flask before any purchase executes. Flask validates constraints, trust score, and balance, then calls Stripe + Rye to execute the purchase. This separation means the agent can never bypass the risk layer.

**Skeleton reference:** `/Users/davidchen/OpenPay/` is the v1 implementation, and the current `OpenPay-v2/` directory contains v2 patterns. Reference v2 for payment workflow patterns. Do NOT copy the old orchestrator or stale skill patterns — v3 uses cookbook-pattern skills, Task 0, and development stages.

---

## How to Run Locally

```bash
# 1. Set up Supabase project
# Create a project at https://supabase.com, then apply the schema from the
# "Database Schema" section below using the Supabase SQL Editor.

# 2. Copy env file and fill in API keys
cp .env.example .env

# 3. Start Flask API (terminal 1)
cd api
pip install -r requirements.txt
python app.py
# Runs on http://localhost:5000

# 4. Seed the database (terminal 1, after Flask is running)
python scripts/seed_demo.py

# 5. Start Next.js frontend (terminal 2)
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000

# 6. OpenClaw Gateway should already be running on port 18789
# Verify: curl http://localhost:18789/health
```

### Technical Setup Notes

- **Supabase clients:** Flask uses `supabase-py`. Next.js uses `@supabase/supabase-js` (for Stripe.js card input only — all data queries go through Flask). Reference `Davids_Prereq/api/src/db.py` for the Python client pattern.
- **Stripe.js:** The frontend loads Stripe.js to tokenize card input. Raw card numbers NEVER touch Flask or Supabase. Flask only stores `stripe_customer_id` and `stripe_payment_method_id`.
- **OpenClaw SDK:** Flask uses `openclaw-sdk` (Python) to send messages to and receive responses from the OpenClaw Gateway at `http://localhost:18789`.
- **`.env` loading:** The `.env` file lives at the project root. Flask loads it via `python-dotenv`.

---

## Environment Variables

```bash
# .env (root level, shared by both services)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
RYE_API_KEY=your-rye-key
OPENCLAW_GATEWAY_URL=http://localhost:18789
ANTHROPIC_API_KEY=sk-ant-...
FLASK_SECRET_KEY=your-flask-secret

# Next.js needs to know where Flask is
NEXT_PUBLIC_FLASK_API_URL=http://localhost:5000
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

**On Render (future):** `NEXT_PUBLIC_FLASK_API_URL` points to the deployed Flask URL. `SUPABASE_URL` and `SUPABASE_KEY` stay the same (Supabase is hosted).

---

## Database Schema

Flask owns the schema. Apply in Supabase SQL Editor during project setup.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supabase_auth_id UUID UNIQUE,  -- links to Supabase Auth user, set during onboarding
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    stripe_payment_method_id VARCHAR(255),
    balance FLOAT DEFAULT 0.0,  -- spending limit remaining, NOT held funds
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    openclaw_agent_id VARCHAR(255),
    trust_score INT DEFAULT 50,  -- 0-100
    constraints JSONB DEFAULT '{
        "max_per_transaction": 100,
        "max_per_week": 500,
        "allowed_categories": ["electronics", "groceries", "books", "clothing", "home", "office"],
        "blocked_merchants": []
    }'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tier is DERIVED from trust_score, never stored:
--   0-25:  "frozen"     — agent cannot buy anything
--   26-50: "restricted" — max $25/tx, only pre-approved merchants
--   51-75: "standard"   — max $100/tx, any merchant in allowed categories
--   76-100: "trusted"   — operates within user-set constraints, full autonomy

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    amount FLOAT NOT NULL,
    merchant VARCHAR(255),
    product_url TEXT,
    product_description TEXT,
    category VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending' | 'completed' | 'failed' | 'returned' | 'disputed' | 'flagged'
    evidence JSONB,  -- evidence bundle: intent snapshot, policy checks, account state, execution result
    dispute_type VARCHAR(50),  -- NULL | 'unauthorized' | 'wrong_item' | 'fulfillment_issue'
    dispute_at TIMESTAMP,  -- when dispute was filed
    rye_order_id VARCHAR(255),
    stripe_payment_intent_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

```

Note: There is no `chat_messages` table. Conversation history is managed by OpenClaw's iMessage channel, not stored in Supabase.

---

## Trust Score System

**Single source of truth:** `trust_score` integer (0-100) in `agents` table. Tier is DERIVED, never stored.

| Score | Tier | Behavior |
| --- | --- | --- |
| 0-25 | Frozen | Agent cannot buy anything. User notified. Manual reset required. |
| 26-50 | Restricted | Max $25/transaction. Only pre-approved merchants. |
| 51-75 | Standard | Max $100/transaction. Any merchant in allowed categories. |
| 76-100 | Trusted | Operates within user-configured constraints. Full autonomy. |

**New agents start at 50 (Standard).**

**Score change rules:**

| Event | Delta | Notes |
| --- | --- | --- |
| Successful purchase, no issue | +3 | |
| Human marks "good purchase" | +5 | Via dashboard |
| Human marks "wrong item" | -10 | |
| Agent attempted to overspend (hit limit) | -5 | |
| Agent attempted blocked category/merchant | -8 | |
| Runtime mismatch / security flag confirmed | -6 | Post-purchase validation |
| Confirmed unauthorized action | -12 | Via dispute system |
| Score is always clamped to 0-100 | | |

### Risk Rate Escalation

In addition to trust score tiers, OpenPay tracks rolling risk rates over a 30-day window of completed transactions:

| Rate | Calculation |
| --- | --- |
| `dispute_rate` | disputes / total completed |
| `flagged_rate` | flagged transactions / total completed |
| `unauthorized_rate` | unauthorized disputes / total completed |
| `wrong_item_rate` | wrong-item disputes / total completed |

**Escalation bands:**

| Rate Range | Status | Action |
| --- | --- | --- |
| 0-1% | Normal | No restrictions beyond trust tier |
| >1% | Elevated | PAUSE_FOR_REVIEW on purchases (human must approve) |
| >3% | Restricted | Max $10/tx regardless of tier, limited categories |
| >5% | Frozen | Agent cannot purchase. Manual review required. |

Risk rates are checked as part of pre-purchase validation (see purchase-request webhook). The worst status across all four rates determines the agent's risk status.

**Tier-based constraint override:** When the agent's tier imposes stricter limits than the user's custom constraints, the tier limits win. For example, if a user sets `max_per_transaction: 200` but the agent is in Restricted tier (max $25), the effective limit is $25.

**Tier derivation helper** (implement in both services):
```python
# Python (Flask)
def score_to_tier(score: int) -> str:
    if score <= 25:
        return "frozen"
    elif score <= 50:
        return "restricted"
    elif score <= 75:
        return "standard"
    else:
        return "trusted"
```
```typescript
// TypeScript (Next.js)
function scoreToTier(score: number): string {
  if (score <= 25) return "frozen";
  if (score <= 50) return "restricted";
  if (score <= 75) return "standard";
  return "trusted";
}
```

---

## Flask API Endpoints (Port 5000)

### Users

| Method | Path | Request Body | Response |
| --- | --- | --- | --- |
| `POST` | `/api/users` | `{ name, email }` | `{ id, name, email, balance }` |
| `GET` | `/api/users/:id` | — | `{ id, name, email, stripe_customer_id, balance, created_at }` |

### Card / Payment Setup

| Method | Path | Request Body | Response |
| --- | --- | --- | --- |
| `POST` | `/api/users/:id/card` | `{ stripe_token }` | `{ stripe_customer_id, stripe_payment_method_id }` |

Steps: (1) Create Stripe Customer if not exists. (2) Attach PaymentMethod from token. (3) Store `stripe_customer_id` and `stripe_payment_method_id` in Supabase. (4) Return IDs. The frontend uses Stripe.js Elements to collect card info and generate the token — raw card data never touches Flask.

### Balance

| Method | Path | Request Body | Response |
| --- | --- | --- | --- |
| `POST` | `/api/users/:id/balance` | `{ amount }` | `{ balance }` |

Sets the user's spending limit. This is NOT holding funds — it's a self-imposed cap. When the agent buys something, the card is charged directly via Stripe for that exact amount, and the balance number is decremented.

### Agent

| Method | Path | Request Body | Response |
| --- | --- | --- | --- |
| `GET` | `/api/users/:id/agent` | — | `{ id, trust_score, tier, constraints, openclaw_agent_id }` |
| `PUT` | `/api/users/:id/agent/constraints` | `{ max_per_transaction?, max_per_week?, allowed_categories?, blocked_merchants? }` | `{ constraints }` |
| `POST` | `/api/users/:id/agent/reset-score` | — | `{ trust_score: 50, tier: "standard" }` |

The GET endpoint returns `tier` as a derived field (computed from `trust_score` using `score_to_tier()`).

### Transactions

| Method | Path | Query Params | Response |
| --- | --- | --- | --- |
| `GET` | `/api/users/:id/transactions` | `?status=` (optional filter) | `[{ id, amount, merchant, product_description, category, status, created_at }]` |
| `PUT` | `/api/transactions/:id/mark` | `{ mark: "good" \| "wrong_item" }` | `{ transaction_id, trust_score, old_tier, new_tier }` |

The mark endpoint: (1) Reads current trust score. (2) Applies delta (+5 for good, -10 for wrong_item). (3) Clamps to 0-100. (4) Writes new score. (5) Derives old and new tiers. (6) Returns both so the frontend can show tier transitions.

### Purchase Webhooks (called BY OpenClaw, not by frontend)

| Method | Path | Request Body | Response |
| --- | --- | --- | --- |
| `POST` | `/api/webhook/purchase-request` | `{ agent_id, user_id, product_url, amount, merchant, category, product_description }` | `{ decision: "APPROVE" \| "DENY" \| "PAUSE_FOR_REVIEW", reason?, transaction_id? }` |
| `POST` | `/api/webhook/purchase-complete` | `{ transaction_id, rye_order_id, status }` | `{ success: bool }` |

**purchase-request** is the enforcement point. Steps:
1. Look up agent's trust score and derive tier.
2. Check: is tier "frozen"? → DENY.
3. **Check risk rates** (dispute_rate, flagged_rate, unauthorized_rate, wrong_item_rate). If any rate exceeds threshold, apply escalation action: >1% → PAUSE_FOR_REVIEW, >3% → restrict to $10/tx, >5% → DENY (frozen).
4. Compute effective constraints (merge user constraints with tier overrides AND risk rate overrides).
5. Check: is `amount` under effective `max_per_transaction`? → if not, DENY + apply -5 trust score.
6. Check: is `category` in `allowed_categories` and merchant not in `blocked_merchants`? → if not, DENY + apply -8 trust score.
7. Check: is `amount` under remaining `balance`? → if not, DENY.
8. Check: has weekly spending exceeded `max_per_week`? (sum transactions this week) → if not, DENY.
9. **Create evidence bundle** JSONB: `{ intent_snapshot: { product_url, amount, merchant, category }, account_state_at_purchase: { balance, trust_score, tier, risk_status }, policy_checks: [{ check, result, detail }] }`. Attach to transaction row.
10. If all checks pass: create transaction (status: pending, evidence: bundle), charge Stripe PaymentMethod, call Rye API with product URL.
11. If Rye fails (out of stock, merchant down): try alternative product if available, otherwise mark transaction as `failed` and return DENY with reason.
12. If Stripe card declines: mark transaction as `failed`, return DENY with reason "card_declined". No trust score change.
13. If success: return APPROVE with `transaction_id`.

**PAUSE_FOR_REVIEW:** When risk rates are elevated (>1%) but not frozen, the purchase does not execute. The transaction is created with status `pending` and the response includes `decision: "PAUSE_FOR_REVIEW"`. The agent informs the user that the purchase needs manual approval. The user can approve or deny via the dashboard (future: Risk tab action).

**purchase-complete** is called after Rye confirms the order:
1. Update transaction status to `completed`, store `rye_order_id`.
2. Decrement user's `balance` by `amount`.
3. Apply +3 to agent's trust score.
4. **Post-purchase validation:** Compare the approved intent snapshot (amount, merchant, category) against Rye's final checkout result. If mismatch beyond tolerance (e.g., final charge > approved amount + 5%, or different merchant), flag the transaction (status: `flagged`) and apply -6 trust score delta. Store the comparison result in the evidence bundle's `execution_result` field.
5. Agent sends notification to user via iMessage: "Purchased [product] for $[amount] from [merchant]."

### Dispute System

Three dispute types, filed by the user via the dashboard:

| Type | Description | Trust Delta |
| --- | --- | --- |
| `unauthorized` | Agent made a purchase the user didn't request | -12 |
| `wrong_item` | Agent bought the wrong product | -10 |
| `fulfillment_issue` | Correct item ordered but delivery/quality problem | -5 |

**Endpoint:** `PUT /api/transactions/:id/dispute` with `{ type: "unauthorized" | "wrong_item" | "fulfillment_issue" }`

**Dispute flow:**
1. Record dispute type and timestamp on the transaction row (`dispute_type`, `dispute_at`).
2. Update transaction status to `disputed`.
3. Check evidence bundle for eligibility: purchase was within constraints, evidence bundle is complete, reported within 7 days, type matches a supported category.
4. Apply trust delta based on dispute type.
5. If eligible: reverse balance deduction (goodwill credit — add the amount back to user's balance).
6. Return `{ transaction_id, dispute_type, eligible, trust_score, old_tier, new_tier, balance_credited? }`.

**Note:** The existing `PUT /api/transactions/:id/mark` endpoint is replaced by this dispute endpoint. "Mark as good" remains as `PUT /api/transactions/:id/mark` with `{ mark: "good" }` (trust delta +5).

### Risk Metrics

**Endpoint:** `GET /api/users/:id/risk`

**Response:**
```json
{
  "dispute_rate": 0.02,
  "flagged_rate": 0.01,
  "unauthorized_rate": 0.0,
  "wrong_item_rate": 0.02,
  "status": "elevated",
  "total_completed_30d": 50,
  "total_disputes_30d": 1,
  "total_flagged_30d": 0
}
```

Rates are computed over the last 30 days of completed transactions. The `status` field reflects the worst escalation band across all four rates (see Risk Rate Escalation in Trust Score System).

Implementation: one function in `api/src/services/risk_metrics.py`, ~15 lines Python. Query transactions from last 30 days, count by status/dispute_type, divide.

### Evidence Bundle

Every transaction gets an evidence bundle stored as `evidence` JSONB on the transactions table.

**Created during** pre-purchase validation (step 9 in purchase-request webhook).
**Updated during** post-purchase validation (step 4 in purchase-complete webhook).

**Schema:**
```json
{
  "intent_snapshot": {
    "product_url": "https://...",
    "amount": 29.99,
    "merchant": "Amazon",
    "category": "electronics",
    "product_description": "USB-C cable"
  },
  "account_state_at_purchase": {
    "balance": 470.01,
    "trust_score": 53,
    "tier": "standard",
    "risk_status": "normal"
  },
  "policy_checks": [
    { "check": "tier_not_frozen", "result": "pass" },
    { "check": "risk_rate_check", "result": "pass", "detail": "all rates < 1%" },
    { "check": "amount_under_limit", "result": "pass", "detail": "29.99 < 100" },
    { "check": "category_allowed", "result": "pass" },
    { "check": "balance_sufficient", "result": "pass" },
    { "check": "weekly_limit_ok", "result": "pass" }
  ],
  "execution_result": {
    "rye_order_id": "rye_abc123",
    "final_amount": 29.99,
    "final_merchant": "Amazon",
    "amount_match": true,
    "merchant_match": true,
    "flagged": false
  }
}
```

Full schema details in `~/Vaults/OpenPay/Technical Docs/Technical Docs Validation.md` section 14.

---

## OpenClaw Integration

**Gateway:** Self-hosted, running on `http://localhost:18789` on the same machine as Flask.

**Agent model:** Claude Sonnet (via OpenClaw's model config). Haiku used for lightweight judgment calls (e.g., "does this message need clarification before I can shop?").

**Installed skills:**
- `shopping-expert` — product search and comparison across retailers. Agent uses this to find products matching the user's request.
- **Custom buy skill** — a simple SKILL.md that instructs the agent: "When you've decided what to buy, call POST `http://localhost:5000/api/webhook/purchase-request` with the product details. Wait for approval. If denied, tell the user why. If approved, confirm the purchase to the user."

**The custom buy skill is the bridge between OpenClaw and Flask.** It replaces the `buy-anything` skill because our Flask backend handles Stripe + Rye directly. The agent never calls Rye or Stripe itself — it only asks Flask for permission and Flask does the rest.

**Agent behavior:**
- When the user's request is vague ("buy me a gift for my girlfriend"), the agent asks clarifying questions before searching.
- When the agent finds a product, it sends a purchase request to Flask. No human approval step — the constraint system is the guardrail.
- After a purchase succeeds or fails, the agent notifies the user via iMessage.
- If a purchase fails (Rye checkout fails), the agent tries an alternative product that fits the same constraints before reporting failure.
- Conversation history is managed by OpenClaw's iMessage channel with `historyLimit: 50`.

---

## Messaging Interface (iMessage via OpenClaw)

The user communicates with the shopping agent via iMessage. There is no chat interface in the web dashboard. OpenClaw's native iMessage channel handles receiving and sending messages.

**Prerequisites:**
- `imsg` CLI tool installed (`brew install imsg` or as documented by OpenClaw)
- Full Disk Access granted to the terminal running the OpenClaw gateway (System Settings → Privacy & Security → Full Disk Access)
- The gateway Mac is signed into iMessage with the agent's Apple ID or the user's own Apple ID for testing

**Gateway config addition:**
```json5
{
  channels: {
    imessage: {
      enabled: true,
      cliPath: "imsg",
      dbPath: "~/Library/Messages/chat.db",
      dmPolicy: "allowlist",
      allowFrom: ["USER_PHONE_OR_APPLE_ID"],
      historyLimit: 50,
      includeAttachments: false
    }
  }
}
```

**Message flow:**
1. User texts the agent's iMessage contact
2. OpenClaw gateway polls `~/Library/Messages/chat.db` for new messages
3. Gateway routes the message to the shopping agent
4. Agent reasons about the request (Claude Sonnet via OpenClaw)
5. If buying: agent triggers buy skill → Flask validates → Stripe + Rye execute
6. Agent replies via iMessage with the result ("Purchased USB-C cable for $11.99 from Amazon" or "Denied: exceeds your $25 transaction limit")

**For local testing:** Text yourself or sign into a secondary Apple ID on the same Mac. The gateway reads from chat.db regardless of sender identity — `allowFrom` controls which messages it responds to.

---

## Frontend Pages (Next.js + Tailwind)

Multi-page app with auth flow and 4-tab dashboard. Messaging happens via iMessage through OpenClaw (no chat interface). Dashboard design inspired by Stripe's dashboard — clean data tables, status badges, metric cards with trend indicators.

### Landing Page (`/`) — Stage 3a
- Hero section with value proposition
- Sign Up / Sign In buttons
- If session exists, redirect to /dashboard

### Auth Pages (`/login`, `/signup`) — Stage 3a
- Email + password forms
- Sign up / sign in toggle
- Error handling (invalid credentials, email taken, etc.)

### Onboarding Page (`/onboarding`) — Stage 3a
- Multi-step questionnaire (identity → preferences → payment → terms)
- Only accessible to authenticated users without an OpenPay profile
- Creates user + agent rows on submit

### Dashboard (`/dashboard`) — Existing (moved from `/`)

### Overview Tab (default)
- Current balance (spending limit remaining)
- Agent trust score (numeric + tier badge: Frozen/Restricted/Standard/Trusted)
- **Risk status badge** (normal/elevated/restricted/frozen) — color-coded
- Total spent this week and this month
- Last 5 transactions (preview list)

### Transactions Tab
- Full transaction history table
- Columns: Date, Merchant, Product, Amount, Category, Status
- Status badges: pending (yellow), completed (green), failed (red), returned (gray), **disputed (orange), flagged (purple)**
- Each row has dispute actions: **"Mark as good"**, **"Unauthorized"**, **"Wrong item"**, **"Fulfillment issue"** (triggers trust score update + dispute flow)

### Risk Tab (NEW)
- **Metric cards:** dispute rate, flagged rate, unauthorized rate, wrong-item rate — each with percentage and trend indicator (up/down arrow vs last 30 days)
- **Escalation status:** current risk status (normal/elevated/restricted/frozen) with explanation of what it means
- **Recent disputes list:** table of disputed transactions with type, date, and resolution status
- **Evidence bundle viewer:** expandable per-transaction view showing intent snapshot, policy checks, account state at purchase, and execution result

### Settings Tab
- Spending limits form (max per transaction, max per week)
- Allowed categories (checkboxes)
- Blocked merchants (text input, add/remove)
- Balance top-up input (set new spending limit)
- Card management (add card via Stripe Elements)

---

## Seed Data (Demo)

The seed script (`scripts/seed_demo.py`) creates:

**User:** Demo User (demo@openpay.com)
- Balance: $500.00
- Stripe customer with test card attached

**Agent:** Demo User's shopping agent
- Trust score: 50 (Standard tier)
- Default constraints: $100/tx, $500/week, all categories allowed, no blocked merchants

**Transactions:** 5-8 pre-seeded transactions showing variety:
- 3 completed purchases (electronics, groceries, books) — shows working history
- 1 failed purchase (out of stock) — shows error handling
- 1 marked as "wrong item" — shows trust score was decremented

**Result:** Dashboard looks populated on first load. Trust score shows 48 (Standard, near Restricted boundary) because of the "wrong item" deduction, making tier transitions visible during the demo.

---

## Directory Structure

```
OpenPay/
├── api/
│   ├── app.py              # Flask entry point
│   ├── requirements.txt
│   └── src/
│       ├── db.py            # Supabase client
│       ├── middleware/
│       │   └── auth.py      # @require_auth decorator, JWT validation
│       ├── routes/
│       │   ├── users.py
│       │   ├── agents.py
│       │   ├── transactions.py  # Includes dispute endpoint
│       │   └── webhooks.py
│       └── services/
│           ├── trust_score.py    # Score computation, tier derivation
│           ├── constraints.py    # Constraint enforcement logic
│           ├── risk_metrics.py   # Risk rate calculation, escalation bands
│           ├── evidence.py       # Evidence bundle creation and update
│           ├── stripe_service.py # Stripe customer, charge, tokenization
│           └── rye_service.py    # Rye API checkout
├── frontend/
│   ├── middleware.ts         # Auth redirect logic (session checks on every route)
│   ├── app/
│   │   ├── page.tsx          # Landing page (hero + sign up/sign in)
│   │   ├── login/page.tsx    # Sign in form
│   │   ├── signup/page.tsx   # Sign up form
│   │   ├── onboarding/page.tsx # Multi-step questionnaire
│   │   └── dashboard/page.tsx  # 4-tab dashboard (moved from /)
│   ├── lib/
│   │   ├── api.ts            # Flask API client helpers
│   │   └── supabase.ts       # Supabase client with @supabase/ssr
│   ├── components/
│   │   ├── OverviewTab.tsx
│   │   ├── TransactionsTab.tsx  # Includes dispute actions (unauthorized, wrong_item, fulfillment_issue)
│   │   ├── RiskTab.tsx          # Risk dashboard: rates, escalation, disputes, evidence viewer
│   │   ├── SettingsTab.tsx
│   │   ├── TrustScoreBadge.tsx
│   │   └── StripeCardInput.tsx
│   ├── package.json
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── scripts/
│   ├── seed_demo.py
│   └── reset_trust_score.py
├── .env.example
├── CLAUDE.md
└── README.md
```

---

## Git Workflow

- **Branch:** `main` only (solo dev)
- **Commits:** Present tense ("Add trust score engine", "Wire Stripe card input")
- **Repo:** `https://github.com/DavidChen-006/OpenPay.git` (private)

---

## Auth & Onboarding (Stage 3a)

Identity is required because money is tied to identity. Auth is not optional.

### User Flow

```
/ (Landing)  →  /signup  →  /onboarding  →  /dashboard
                /login   →                   /dashboard
```

1. **Landing page (`/`)** — Hero: "OpenPay — Your AI shops, you stay in control." Sign Up / Sign In buttons. If session exists, redirect to /dashboard.
2. **Sign Up (`/signup`)** — Email + password + confirm password. Creates Supabase Auth user. Redirects to /onboarding.
3. **Sign In (`/login`)** — Email + password. If valid session, redirect to /dashboard. Link to /signup.
4. **Onboarding (`/onboarding`)** — Only accessible if user has no OpenPay profile yet (check `GET /api/auth/me` → 404 means onboarding needed). Multi-step questionnaire:
   - **Step 1 — Identity:** Full name, phone number (for iMessage gateway allowFrom)
   - **Step 2 — Preferences:** Max per transaction (default $100), max per week (default $500), allowed categories (checkboxes), blocked merchants (optional)
   - **Step 3 — Payment:** Spending balance amount, card setup (dev: "Use test card" button attaches tok_visa; production: Stripe Elements)
   - **Step 4 — Terms:** Accept TOS checkbox, submit
   - On submit: creates user row (with `supabase_auth_id`), agent row, attaches card, stores preferences. Redirects to /dashboard.
5. **Dashboard (`/dashboard`)** — Auth-protected. The existing 4-tab app. User ID derived from JWT session, not hardcoded. Sign out button → clears session → redirect to /.

### Edge Cases
- Refresh on /dashboard → check session → expired → redirect to /login
- Refresh on /login → check session → valid → redirect to /dashboard
- New sign-up, closed tab before finishing onboarding → next sign-in → check profile → no profile → redirect to /onboarding
- Sign out → clear session → redirect to /

### Supabase Auth
- **Provider:** Email + password (enable in Supabase dashboard → Authentication → Providers)
- **Client:** `@supabase/ssr` for Next.js (cookie-based sessions, SSR-compatible)
- **Session management:** Supabase handles refresh tokens, session expiry automatically
- **JWT validation (Flask):** Decode JWT using Supabase JWT secret (from dashboard → Settings → API). One middleware function: `@require_auth` decorator on all protected endpoints.
- **User identity link:** `supabase_auth_id UUID UNIQUE` column on `users` table links Supabase Auth user to OpenPay user row.

### API Changes for Auth
- All existing endpoints change from `/api/users/:id/...` to `/api/me/...` — user ID derived from JWT, not URL parameter. Prevents users from accessing each other's data.
- New endpoints:
  - `GET /api/auth/me` — returns current user's OpenPay profile (or 404 if onboarding not complete)
  - `POST /api/auth/onboarding` — creates user + agent rows from onboarding questionnaire data
- `@require_auth` decorator on all endpoints except `/health`

### Frontend Auth Architecture
- `middleware.ts` — Next.js middleware checks session on every request. Handles all redirect logic centrally (no per-page auth checks).
- `lib/supabase.ts` — Supabase client init with `@supabase/ssr`
- No AuthWrapper.tsx needed — middleware handles it

---

## Deployment (Stage 3b)

### Render Services
- **Frontend:** Render (Next.js) — use `render-deploy` skill
- **Flask API:** Render (Python, gunicorn) — use `render-deploy` skill
- **Database:** Supabase (hosted, same URL in all environments)
- **OpenClaw Gateway:** Separate Mac host (NOT Render — iMessage requires macOS)

### Configuration
- `render.yaml` — Blueprint defining both services, env vars, health checks, build/start commands
- Flask: `gunicorn api.app:app --bind 0.0.0.0:$PORT` (NOT `python app.py`)
- Flask: `debug=False` in production (env var controlled)
- CORS: `ALLOWED_ORIGINS` env var (not hardcoded localhost)
- All API keys as Render environment variables with `sync: false` (not in render.yaml)
- `NEXT_PUBLIC_FLASK_API_URL` → Render Flask URL
- `OPENCLAW_GATEWAY_URL` → production gateway Mac IP/hostname

### Error Handling
- All Flask endpoints return consistent error responses: `{ error: string, code: string }`
- Stripe failures: retry once, then return error with reason
- Rye failures: try alternative product, then return error
- Supabase connection errors: return 503 with retry hint
- OpenClaw gateway down: purchases fail gracefully, user notified via dashboard

### Health Checks
- Flask: `GET /health` (already exists)
- Next.js: `GET /api/health` (needs adding)

---

## Development Stages

This project follows staged development. Read `~/.claude/skills/development-stages/SKILL.md`.

### Stage 1: POC
Foundation + basic CRUD + health check + one happy path with mocks. Prove the architecture works end-to-end with mock Stripe and mock Rye.

### Stage 2a: MVP Part 1 — Payment Workflow
Full purchase flow end-to-end with real services + 4-tab dashboard + iMessage. Replace mocks with Stripe test mode and Rye staging.

### Stage 2b: MVP Part 2 — Risk & Validation
Evidence bundles + post-purchase validation + dispute system + risk rate monitoring + Risk tab. The full risk management layer.

### Stage 3a: Auth & Onboarding
Supabase Auth + landing page + sign up/sign in + onboarding questionnaire + JWT middleware + /api/me endpoints. Identity before deployment.

### Stage 3b: Deployment
Deploy to Render + render.yaml + gunicorn + env var configuration + error handling + health checks. Ready for real users.

Gate criteria are proposed by the orchestrator and approved by the user at each stage boundary.
