"""Solana RPC proxy — fetches on-chain transaction data from devnet."""
import os
import requests
from flask import Blueprint, jsonify

solana_bp = Blueprint("solana", __name__, url_prefix="/api")


@solana_bp.route("/solana/tx/<signature>", methods=["GET"])
def get_solana_tx(signature):
    rpc_url = os.environ.get("SOLANA_RPC_URL", "https://api.devnet.solana.com")
    resp = requests.post(rpc_url, json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
    })
    data = resp.json()
    if not data.get("result"):
        return jsonify({"error": "transaction not found"}), 404

    result = data["result"]
    block_time = result.get("blockTime")
    slot = result.get("slot")
    fee = result["meta"]["fee"]

    # Extract memo from instructions
    memo = None
    for ix in result["transaction"]["message"]["instructions"]:
        if isinstance(ix, dict):
            if ix.get("parsed"):
                memo = ix["parsed"]
            elif ix.get("program") == "spl-memo" or "Memo" in ix.get("programId", ""):
                import base64
                try:
                    memo = base64.b64decode(ix.get("data", "")).decode("utf-8")
                except Exception:
                    memo = ix.get("data")

    return jsonify({
        "signature": signature,
        "block_time": block_time,
        "slot": slot,
        "fee_lamports": fee,
        "fee_sol": fee / 1_000_000_000,
        "memo": memo,
        "confirmations": result["meta"].get("confirmationStatus", "confirmed"),
        "success": result["meta"]["err"] is None,
        "explorer_url": f"https://explorer.solana.com/tx/{signature}?cluster=devnet"
    })
