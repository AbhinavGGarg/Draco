"""Seed demo data for OpenPay POC."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.src.db import supabase


def seed():
    print("Seeding demo data...")

    # Clean existing demo data
    existing = supabase.table("users").select("id").eq("email", "demo@openpay.com").execute()
    if existing.data:
        old_id = existing.data[0]["id"]
        supabase.table("agent_steps").delete().eq("session_id", "demo-session-001").execute()
        supabase.table("transactions").delete().eq("user_id", old_id).execute()
        supabase.table("agents").delete().eq("user_id", old_id).execute()
        supabase.table("users").delete().eq("id", old_id).execute()
        print("Cleaned existing demo data.")

    # Create demo user
    user_result = supabase.table("users").insert({
        "name": "Demo User",
        "email": "demo@openpay.com",
        "balance": 500.0,
    }).execute()
    user = user_result.data[0]
    user_id = user["id"]
    print(f"Created user: {user['name']} ({user_id})")

    # Create agent
    agent_result = supabase.table("agents").insert({
        "user_id": user_id,
        "trust_score": 50,
        "constraints": {
            "max_per_transaction": 100,
            "max_per_week": 500,
            "allowed_categories": ["electronics", "groceries", "books", "clothing", "home", "office"],
            "blocked_merchants": [],
        },
    }).execute()
    agent = agent_result.data[0]
    agent_id = agent["id"]
    print(f"Created agent: {agent_id} (trust_score: 50)")

    # Create transactions
    transactions = [
        {"agent_id": agent_id, "user_id": user_id, "amount": 29.99, "merchant": "Amazon", "product_description": "USB-C Cable", "category": "electronics", "status": "completed"},
        {"agent_id": agent_id, "user_id": user_id, "amount": 45.50, "merchant": "Whole Foods", "product_description": "Weekly groceries", "category": "groceries", "status": "completed"},
        {"agent_id": agent_id, "user_id": user_id, "amount": 12.99, "merchant": "Barnes & Noble", "product_description": "Python Cookbook", "category": "books", "status": "completed"},
        {"agent_id": agent_id, "user_id": user_id, "amount": 89.99, "merchant": "Best Buy", "product_description": "Bluetooth Speaker", "category": "electronics", "status": "failed"},
        {"agent_id": agent_id, "user_id": user_id, "amount": 34.99, "merchant": "Amazon", "product_description": "Wrong phone case", "category": "electronics", "status": "completed"},
    ]

    for tx in transactions:
        result = supabase.table("transactions").insert(tx).execute()
        print(f"  Transaction: {tx['product_description']} - ${tx['amount']} ({tx['status']})")

    # Update first completed transaction with Solana audit proof and session_id
    first_completed = supabase.table("transactions").select("id").eq("user_id", user_id).eq("status", "completed").order("created_at").limit(1).execute()
    if first_completed.data:
        demo_tx_id = first_completed.data[0]["id"]
        supabase.table("transactions").update({
            "session_id": "demo-session-001",
            "solana_tx_signature": "5demoExampleSolanaSignature",
        }).eq("id", demo_tx_id).execute()
        print(f"  Updated transaction {demo_tx_id} with session_id and solana_tx_signature")

    # Seed agent_steps for demo session
    agent_steps = [
        {
            "session_id": "demo-session-001",
            "step_type": "search",
            "data": {"query": "USB-C cable", "source": "Amazon"},
        },
        {
            "session_id": "demo-session-001",
            "step_type": "results",
            "data": {"products_found": 3},
        },
        {
            "session_id": "demo-session-001",
            "step_type": "selection",
            "data": {"selected": "Anker USB-C 6ft", "price": 11.99, "reason": "Best rated under budget"},
        },
    ]
    for step in agent_steps:
        supabase.table("agent_steps").insert(step).execute()
        print(f"  Agent step: {step['step_type']}")

    # Apply wrong_item penalty (-10) to simulate marking last transaction
    # Trust score: 50 - 10 = 40... but we want 48 per spec
    # Spec says: 3 completed (+3 each = +9), 1 wrong_item (-10) = 50 + 9 - 10 = 49
    # Actually seed says "trust score shows 48" so let's just set it directly
    # The seed is a skeleton — we set the final state
    new_score = 48
    supabase.table("agents").update({"trust_score": new_score}).eq("id", agent_id).execute()
    print(f"Updated trust_score to {new_score} (simulating wrong_item deduction)")

    print("\nSeed complete!")
    print(f"  User ID: {user_id}")
    print(f"  Agent ID: {agent_id}")
    print(f"  Trust Score: {new_score} (Standard tier, near Restricted boundary)")


if __name__ == "__main__":
    seed()
