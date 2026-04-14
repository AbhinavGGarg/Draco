"""Reset an agent's trust score to 50 (Standard tier)."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.src.db import supabase


def reset(agent_id: str):
    result = supabase.table("agents").update({"trust_score": 50}).eq("id", agent_id).execute()
    if not result.data:
        print(f"Error: agent {agent_id} not found")
        sys.exit(1)
    print(f"Reset trust_score to 50 for agent {agent_id}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.reset_trust_score <agent_id>")
        sys.exit(1)
    reset(sys.argv[1])
