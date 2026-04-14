"""Solana audit log: Merkle tree + memo anchoring."""
import hashlib
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def build_merkle_root(leaves: list[str]) -> str:
    """Build a Merkle root from a list of string leaves.

    SHA256 hashes each leaf, then pairs and hashes up the tree.
    If there's an odd number of nodes at any level, the last node is duplicated.
    Returns the hex-encoded root hash.
    """
    if not leaves:
        return hashlib.sha256(b"").hexdigest()

    nodes = [hashlib.sha256(leaf.encode("utf-8")).digest() for leaf in leaves]

    while len(nodes) > 1:
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])
        next_level = []
        for i in range(0, len(nodes), 2):
            combined = nodes[i] + nodes[i + 1]
            next_level.append(hashlib.sha256(combined).digest())
        nodes = next_level

    return nodes[0].hex()


def anchor_to_solana(session_id: str, merkle_root: str, transaction_id: str) -> Optional[str]:
    """Anchor a memo containing session/root/txid to Solana devnet.

    Returns the transaction signature string, or None on any failure.
    """
    try:
        from solders.keypair import Keypair
        from solders.pubkey import Pubkey
        from solders.transaction import Transaction
        from solders.message import Message
        from solders.instruction import Instruction, AccountMeta
        from solders.hash import Hash
        from solana.rpc.api import Client
        import base58

        memo = json.dumps({
            "sid": session_id[:36],
            "root": merkle_root,
            "txid": transaction_id[:36],
        })

        private_key_b58 = os.environ.get("SOLANA_PRIVATE_KEY")
        if not private_key_b58:
            logger.error("SOLANA_PRIVATE_KEY not set")
            return None

        rpc_url = os.environ.get("SOLANA_RPC_URL", "https://api.devnet.solana.com")

        key_bytes = base58.b58decode(private_key_b58)
        kp = Keypair.from_bytes(key_bytes)

        client = Client(rpc_url)
        recent_blockhash_resp = client.get_latest_blockhash()
        recent_blockhash = recent_blockhash_resp.value.blockhash

        MEMO_PROGRAM_ID = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")

        memo_ix = Instruction(
            program_id=MEMO_PROGRAM_ID,
            accounts=[AccountMeta(pubkey=kp.pubkey(), is_signer=True, is_writable=False)],
            data=memo.encode("utf-8"),
        )

        msg = Message.new_with_blockhash(
            [memo_ix],
            kp.pubkey(),
            recent_blockhash,
        )
        tx = Transaction.new_unsigned(msg)
        tx.sign([kp], recent_blockhash)

        result = client.send_transaction(tx)
        sig = str(result.value)
        logger.info("Solana memo anchored: %s", sig)
        return sig

    except Exception:
        logger.exception("Failed to anchor to Solana")
        return None


def anchor_purchase(
    session_id: str,
    transaction_id: str,
    steps: list[dict],
    evidence: dict,
) -> Optional[str]:
    """Anchor a full purchase audit trail to Solana.

    Serializes each agent step and the evidence bundle as sorted JSON,
    builds a Merkle root over all leaves, and writes a memo to Solana.
    Returns the transaction signature or None on failure.
    """
    leaves = [json.dumps(step, sort_keys=True) for step in steps]
    leaves.append(json.dumps(evidence, sort_keys=True))

    root = build_merkle_root(leaves)
    return anchor_to_solana(session_id, root, transaction_id)
