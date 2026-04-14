---
name: buy
description: >-
  Execute purchases through the OpenPay Flask API. Trigger when the agent has
  identified a product to buy — has a product URL, price, merchant, category,
  and description. Calls the Flask purchase-request webhook for validation,
  then handles APPROVE, DENY, or PAUSE_FOR_REVIEW responses.
---

# Buy Skill

Execute purchases by requesting approval from the OpenPay Flask API.
Never call Stripe or Rye directly — all purchases go through Flask.

## When to Use

Use this skill when you have ALL of the following:
- Product URL
- Price (amount in USD)
- Merchant name
- Category (one of: electronics, groceries, books, clothing, home, office, health, beauty, sports, toys, automotive, garden, pet supplies, food & dining, travel, entertainment)
- Product description

If any field is missing, ask the user before proceeding.

## Agent Step Reporting

The agent should:
1. Generate a unique session_id (UUID format) at the START of each purchase flow
2. POST intermediate steps to http://localhost:5001/api/webhook/agent-step as it works
3. Three step types: "search" (when searching), "results" (when receiving results), "selection" (when choosing a product)
4. Include the session_id in the final purchase-request body
5. Steps are fire-and-forget -- if a step POST fails, continue anyway

### Step Payloads

**Search step** (when the agent begins searching for a product):
```json
{
  "session_id": "b7e2c4a1-3f8d-4e5b-9a1c-6d7e8f9a0b1c",
  "step_type": "search",
  "data": {
    "query": "USB-C cable under $15",
    "source": "shopping-expert"
  }
}
```

**Results step** (when the agent receives search results):
```json
{
  "session_id": "b7e2c4a1-3f8d-4e5b-9a1c-6d7e8f9a0b1c",
  "step_type": "results",
  "data": {
    "count": 5,
    "top_result": "Anker USB-C Cable 6ft",
    "price_range": "$8.99 - $14.99"
  }
}
```

**Selection step** (when the agent chooses a product to buy):
```json
{
  "session_id": "b7e2c4a1-3f8d-4e5b-9a1c-6d7e8f9a0b1c",
  "step_type": "selection",
  "data": {
    "product_url": "https://amazon.com/dp/B08XYZ",
    "product_name": "Anker USB-C Cable 6ft",
    "amount": 11.99,
    "merchant": "Amazon",
    "reason": "Best rated option under budget"
  }
}
```

### Updated Purchase Request Body (with session_id)

```json
{
  "agent_id": "adf65815-dd03-496e-919b-75933d087f5f",
  "user_id": "517dea61-5726-4129-90cb-198b063bef52",
  "session_id": "b7e2c4a1-3f8d-4e5b-9a1c-6d7e8f9a0b1c",
  "product_url": "https://amazon.com/dp/B08XYZ",
  "amount": 11.99,
  "merchant": "Amazon",
  "category": "electronics",
  "product_description": "Anker USB-C Cable 6ft"
}
```

### Safety Rule

Always generate a fresh session_id for each new purchase flow. Reuse the same session_id for all steps within one flow.

## Purchase Flow

### 1. Confirm Details

Before submitting, verify you have:
- `product_url` — full URL to the product page
- `amount` — price as a number (e.g., 29.99)
- `merchant` — store name (e.g., "Amazon", "Target")
- `category` — must be one of the allowed categories
- `product_description` — brief description of the item

### 2. Submit Purchase Request

POST to the Flask webhook:

```
POST http://localhost:5001/api/webhook/purchase-request
Content-Type: application/json

{
  "agent_id": "adf65815-dd03-496e-919b-75933d087f5f",
  "user_id": "517dea61-5726-4129-90cb-198b063bef52",
  "product_url": "<url>",
  "amount": <number>,
  "merchant": "<merchant>",
  "category": "<category>",
  "product_description": "<description>"
}
```

### 3. Handle Response

The webhook returns one of three decisions:

**APPROVE** — Purchase completed. Payment charged, order placed, balance decremented.
- Response includes `transaction_id`
- The purchase is fully finalized — no further action needed from the agent
- Notify the user: "Purchased [product] for $[amount] from [merchant]."

**DENY** — Purchase rejected.
- Response includes `reason` explaining why
- Tell the user the reason (e.g., "Exceeds your $25 transaction limit", "Category not allowed", "Insufficient balance")
- Do NOT retry the same purchase

**PAUSE_FOR_REVIEW** — Needs human approval.
- Response includes `transaction_id` with status `pending`
- Tell the user: "This purchase needs your approval. Please review it in the OpenPay dashboard."
- Do NOT retry or re-submit — wait for the user to approve via the dashboard

### 4. Handle Failures

If the purchase is denied due to product availability (out of stock, merchant down):
1. Search for an alternative product that matches the original request
2. Verify the alternative fits within the same constraints (price, category)
3. Submit a new purchase request for the alternative
4. If the alternative also fails, inform the user and stop

If denied for constraint violations (amount too high, blocked category, insufficient balance):
- Do NOT try alternatives — inform the user of the specific constraint that blocked the purchase

## Safety Rules

- NEVER call Stripe APIs directly
- NEVER call Rye APIs directly
- NEVER bypass the Flask webhook — it is the only path to purchase
- NEVER fabricate transaction IDs or purchase confirmations
- NEVER retry a denied purchase with the same parameters
- Always use the agent_id and user_id from your current session context
