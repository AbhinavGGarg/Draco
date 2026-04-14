# Squid: The Responsibility Layer for AI Agent Commerce

When an AI agent spends money, someone needs to be accountable. Squid sits between the AI and your wallet — so every purchase has an owner, a set of rules, and a receipt that proves what happened.

## The Problem

There is no legal framework for AI spending money. When an AI agent makes the wrong purchase, consumers have no way to prove what they authorized and merchants have no way to verify the order was legitimate. Agentic payments are skyrocketing and they've already cost consumers millions.

## The Solution

Every AI agent transaction runs through Squid before money moves. We validate the purchase against the human's intent, run it through constraint checks, score the agent's trust using an AI-powered model based on behavioral history, and generate an evidence bundle anchored to Solana. If the agent deviates from what was authorized, the transaction is blocked, the trust score drops, and permissions tighten automatically.

## Demo

<!-- Replace with actual demo video link -->
[![Demo Video](https://img.youtube.com/vi/REPLACE/maxresdefault.jpg)](https://youtube.com/watch?v=REPLACE)

> Click to watch the full demo

## How It Works

```
User sends request via iMessage
        │
        ▼
   OpenClaw Agent
   (research + select product)
        │
        ▼
   Squid Enforcement Layer
   ┌─────────────────────────┐
   │ 1. Constraint checks    │  spending limits, categories,
   │ 2. Trust tier gate      │  merchants, weekly caps
   │ 3. Evidence bundle      │  intent + state + checks
   │ 4. Stripe charge        │  tokenized payment
   │ 5. Rye checkout         │  universal merchant checkout
   │ 6. Post-purchase audit   │  amount/merchant match
   │ 7. Solana anchor        │  SHA-256 Merkle root on-chain
   │ 8. Trust recomputation  │  AI model rescores agent
   └─────────────────────────┘
        │
        ▼
   User sees result in dashboard
```

## Core Features

### Constraint Enforcement
Six validation checks before every purchase: spending limits, category permissions, blocked merchants, weekly caps, balance sufficiency, and trust tier gates. Any failure blocks the transaction immediately.

### AI Trust Scoring
Weighted factor model inspired by the Altman Z-Score framework:

```
T = 30·R + 20·S + 25·D + 10·C + 15·M

R = Purchase Reliability    S = Spending Behavior
D = Dispute History         C = Category Diversity
M = Account Maturity
```

The mathematical base score is refined by Gemini 3.0 Flash for qualitative pattern recognition. Updates automatically on every transaction.

### Evidence Bundles
Every transaction records: what was requested (intent snapshot), the account state at time of purchase, every policy check with pass/fail, and the execution result. Full audit trail for every dollar spent.

### On-Chain Proof (Solana)
Evidence bundles are SHA-256 hashed into a Merkle root and anchored to Solana devnet. Block number, timestamp, signature, and memo are publicly verifiable on Solana Explorer. No one can alter a receipt after the fact.

### Dispute System
Three dispute types — unauthorized, wrong item, fulfillment issue — with eligibility checks, trust score impact, and goodwill balance credits. Filed through the dashboard, resolved against the evidence bundle.

## Tech Stack

| Layer | Technology | Role |
|-------|-----------|------|
| Enforcement | Flask | Constraint checks, trust scoring, evidence, payment orchestration |
| Frontend | Next.js + Tailwind | Consumer dashboard with 5 tabs, animated charts, spider graphs |
| Database | Supabase | User profiles, transactions, evidence bundles, trust history, JWT auth |
| Payments | Stripe | Card tokenization via Elements, direct charges. Raw card data never touches our servers |
| Checkout | Rye.AI | Universal merchant checkout from product URL |
| Audit Trail | Solana | SHA-256 Merkle root anchoring on devnet |
| Trust Model | Gemini 3.0 Flash | AI-powered trust scoring with weighted factor analysis |
| Agent Runtime | OpenClaw | Conversational AI via iMessage, product search, shopping logic |
| Auth | PyJWT + Supabase Auth | JWT validation on every request, identity-linked transactions |

## Project Structure

```
├── api/                        # Flask enforcement engine
│   ├── app.py                  # Entry point, CORS, blueprints
│   └── src/
│       ├── routes/             # REST endpoints
│       │   ├── webhooks.py     # Purchase request/complete (called by OpenClaw)
│       │   ├── transactions.py # History, mark, dispute
│       │   ├── agents.py       # Trust analysis, constraints, effective limits
│       │   ├── risk.py         # 30-day rolling risk rates
│       │   ├── disputes.py     # Dispute filing with trust recomputation
│       │   ├── auth.py         # JWT-protected /api/auth/me, onboarding
│       │   └── solana.py       # On-chain proof proxy
│       ├── services/
│       │   ├── constraints.py  # 6-check enforcement pipeline
│       │   ├── trust_model.py  # Altman Z-Score + Gemini scoring
│       │   ├── trust_score.py  # Tier derivation, delta application
│       │   ├── evidence.py     # Bundle creation, timestamps, execution comparison
│       │   ├── risk_metrics.py # Rolling rate computation
│       │   ├── stripe_service.py
│       │   ├── rye_service.py
│       │   └── solana_service.py
│       └── middleware/
│           └── auth.py         # @require_auth JWT decorator
│
├── frontend/                   # Next.js consumer dashboard
│   ├── app/
│   │   ├── page.tsx            # Landing page with animated hero
│   │   ├── dashboard/page.tsx  # 5-tab dashboard (Overview, Transactions, Trust, Risk, Settings)
│   │   ├── product/page.tsx    # Philosophy/manifesto
│   │   ├── policy/page.tsx     # TOS, Privacy, AUP
│   │   ├── docs/page.tsx       # User-facing documentation
│   │   ├── login/page.tsx
│   │   ├── signup/page.tsx
│   │   └── onboarding/page.tsx # 4-step questionnaire
│   ├── components/
│   │   ├── OverviewTab.tsx     # Spending chart, metric cards, recent activity
│   │   ├── TransactionsTab.tsx # Full history with dispute actions
│   │   ├── TrustTab.tsx        # AI score, spider chart, history graph, tier system
│   │   ├── RiskTab.tsx         # Rate bars, evidence viewer with Solana proof
│   │   ├── SettingsTab.tsx     # Constraints, weekly progress, override warnings
│   │   ├── SpendingChart.tsx   # Animated SVG area chart
│   │   ├── FirewallSidebar.tsx # Navigation with trust score badge
│   │   └── TrustScoreBadge.tsx # Score + tier display
│   └── lib/
│       └── api.ts              # Typed API client with all endpoints
│
└── scripts/
    └── seed_demo.py            # Demo data seeding
```

## Quick Start

**Prerequisites:** Python 3.10+, Node.js 18+, Supabase project, Stripe test keys

**1. Clone and set up environment**

```bash
git clone https://github.com/DavidChen-006/OpenPay_.git
cd OpenPay_
cp .env.example .env
# Fill in: SUPABASE_URL, SUPABASE_KEY, STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY,
#          RYE_API_KEY, GEMINI_API_KEY, FLASK_SECRET_KEY
```

**2. Start Flask API**

```bash
cd api
pip install -r requirements.txt
cd ..
python -m api.app
# Runs on http://localhost:5001
```

**3. Start Next.js frontend**

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

**4. Seed demo data (optional)**

```bash
python scripts/seed_demo.py
```

## Architecture

The key architectural decision: **the agent proposes, the platform decides.**

OpenClaw handles conversation and product research. It can decide what it wants to buy. But it cannot spend a single dollar without Squid approving the transaction. The enforcement layer validates constraints, records evidence, charges the card, executes checkout, and anchors proof — all atomically in one webhook call.

This separation means the AI agent can never bypass the risk layer. Every purchase has a complete, tamper-proof audit trail from intent to execution.

## Team

- David Chen
- Rohan Muppa
- Aditya Munot

Built at Indy Hacks 2026
