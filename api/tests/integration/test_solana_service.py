"""Tests for Solana audit log service: Merkle tree + memo anchoring."""
import hashlib
import json
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# TestBuildMerkleRoot — pure function, no mocks needed
# ---------------------------------------------------------------------------

class TestBuildMerkleRoot:
    """Test Merkle root construction from string leaves."""

    def test_empty_list(self):
        from api.src.services.solana_service import build_merkle_root
        result = build_merkle_root([])
        expected = hashlib.sha256(b"").hexdigest()
        assert result == expected

    def test_single_leaf(self):
        from api.src.services.solana_service import build_merkle_root
        result = build_merkle_root(["hello"])
        expected = hashlib.sha256("hello".encode("utf-8")).digest().hex()
        assert result == expected

    def test_two_leaves(self):
        from api.src.services.solana_service import build_merkle_root
        result = build_merkle_root(["a", "b"])
        h_a = hashlib.sha256("a".encode("utf-8")).digest()
        h_b = hashlib.sha256("b".encode("utf-8")).digest()
        expected = hashlib.sha256(h_a + h_b).digest().hex()
        assert result == expected

    def test_three_leaves_odd_duplicates_last(self):
        from api.src.services.solana_service import build_merkle_root
        result = build_merkle_root(["x", "y", "z"])
        # Level 0: hash each leaf
        h_x = hashlib.sha256("x".encode("utf-8")).digest()
        h_y = hashlib.sha256("y".encode("utf-8")).digest()
        h_z = hashlib.sha256("z".encode("utf-8")).digest()
        # Odd count: duplicate last => [h_x, h_y, h_z, h_z]
        # Level 1: pair and hash
        h_xy = hashlib.sha256(h_x + h_y).digest()
        h_zz = hashlib.sha256(h_z + h_z).digest()
        # Level 2: final root
        expected = hashlib.sha256(h_xy + h_zz).digest().hex()
        assert result == expected

    def test_deterministic_same_input_same_output(self):
        from api.src.services.solana_service import build_merkle_root
        leaves = ["alpha", "beta", "gamma"]
        result_1 = build_merkle_root(leaves)
        result_2 = build_merkle_root(leaves)
        assert result_1 == result_2

    def test_large_list_100_leaves(self):
        from api.src.services.solana_service import build_merkle_root
        leaves = [f"leaf-{i}" for i in range(100)]
        result = build_merkle_root(leaves)
        # Must be a valid 64-char hex string (SHA256)
        assert isinstance(result, str)
        assert len(result) == 64
        int(result, 16)  # raises ValueError if not valid hex


# ---------------------------------------------------------------------------
# TestAnchorToSolana — mock env vars + Solana RPC
# ---------------------------------------------------------------------------

class TestAnchorToSolana:
    """Test Solana memo anchoring with mocked RPC and keypair."""

    @patch.dict("os.environ", {
        "SOLANA_PRIVATE_KEY": "5K" + "A" * 85,  # placeholder, won't be decoded
        "SOLANA_RPC_URL": "https://api.devnet.solana.com",
    })
    @patch("api.src.services.solana_service.os.environ.get")
    def test_success_returns_signature(self, mock_env_get):
        """Full happy path: keypair loads, RPC returns signature."""
        from api.src.services.solana_service import anchor_to_solana

        mock_env_get.side_effect = lambda key, default=None: {
            "SOLANA_PRIVATE_KEY": "FAKE_B58_KEY",
            "SOLANA_RPC_URL": "https://api.devnet.solana.com",
        }.get(key, default)

        mock_sig = "5abc123def456"
        mock_keypair = MagicMock()
        mock_keypair.pubkey.return_value = MagicMock()

        mock_client_instance = MagicMock()
        mock_blockhash = MagicMock()
        mock_blockhash.value.blockhash = MagicMock()
        mock_client_instance.get_latest_blockhash.return_value = mock_blockhash
        mock_send_result = MagicMock()
        mock_send_result.value = mock_sig
        mock_client_instance.send_transaction.return_value = mock_send_result

        with patch("base58.b58decode", return_value=b"\x00" * 64), \
             patch("solders.keypair.Keypair.from_bytes", return_value=mock_keypair), \
             patch("solana.rpc.api.Client", return_value=mock_client_instance), \
             patch("solders.pubkey.Pubkey.from_string", return_value=MagicMock()), \
             patch("solders.instruction.Instruction", return_value=MagicMock()), \
             patch("solders.instruction.AccountMeta", return_value=MagicMock()), \
             patch("solders.message.Message.new_with_blockhash", return_value=MagicMock()), \
             patch("solders.transaction.Transaction.new_unsigned") as mock_tx_cls:

            mock_tx = MagicMock()
            mock_tx_cls.return_value = mock_tx

            result = anchor_to_solana("session-abc", "rootabc123", "tx-456")

        assert result == mock_sig

    @patch("api.src.services.solana_service.os.environ.get", return_value=None)
    def test_missing_private_key_returns_none(self, mock_env_get):
        from api.src.services.solana_service import anchor_to_solana
        result = anchor_to_solana("session-1", "root-hash", "tx-1")
        assert result is None

    @patch("api.src.services.solana_service.os.environ.get")
    def test_rpc_exception_returns_none(self, mock_env_get):
        """When the Solana RPC client throws, anchor_to_solana returns None."""
        from api.src.services.solana_service import anchor_to_solana

        mock_env_get.side_effect = lambda key, default=None: {
            "SOLANA_PRIVATE_KEY": "FAKE_KEY",
            "SOLANA_RPC_URL": "https://api.devnet.solana.com",
        }.get(key, default)

        with patch("base58.b58decode", return_value=b"\x00" * 64), \
             patch("solders.keypair.Keypair.from_bytes") as mock_kp:
            mock_kp.side_effect = Exception("RPC connection failed")
            result = anchor_to_solana("s1", "root", "tx1")

        assert result is None

    @patch("api.src.services.solana_service.os.environ.get")
    def test_bad_base58_key_returns_none(self, mock_env_get):
        """Invalid base58 key causes an exception caught by the handler."""
        from api.src.services.solana_service import anchor_to_solana

        mock_env_get.side_effect = lambda key, default=None: {
            "SOLANA_PRIVATE_KEY": "NOT_VALID_BASE58!!!",
            "SOLANA_RPC_URL": "https://api.devnet.solana.com",
        }.get(key, default)

        with patch("base58.b58decode", side_effect=ValueError("Non-base58 digit")):
            result = anchor_to_solana("s1", "root", "tx1")

        assert result is None


# ---------------------------------------------------------------------------
# TestAnchorPurchase — mock build_merkle_root + anchor_to_solana
# ---------------------------------------------------------------------------

class TestAnchorPurchase:
    """Test full purchase audit trail anchoring."""

    @patch("api.src.services.solana_service.anchor_to_solana", return_value="sig-abc-123")
    @patch("api.src.services.solana_service.build_merkle_root", return_value="deadbeef" * 8)
    def test_success_returns_signature(self, mock_merkle, mock_anchor):
        from api.src.services.solana_service import anchor_purchase
        steps = [{"action": "search", "result": "found"}]
        evidence = {"intent": "buy cable", "amount": 9.99}

        result = anchor_purchase("sess-1", "tx-1", steps, evidence)

        assert result == "sig-abc-123"
        mock_merkle.assert_called_once()
        mock_anchor.assert_called_once_with("sess-1", "deadbeef" * 8, "tx-1")

    @patch("api.src.services.solana_service.anchor_to_solana", return_value=None)
    @patch("api.src.services.solana_service.build_merkle_root", return_value="aabbccdd" * 8)
    def test_anchor_fails_returns_none(self, mock_merkle, mock_anchor):
        from api.src.services.solana_service import anchor_purchase
        steps = [{"action": "search"}]
        evidence = {"intent": "buy"}

        result = anchor_purchase("sess-2", "tx-2", steps, evidence)

        assert result is None

    @patch("api.src.services.solana_service.anchor_to_solana", return_value="sig-xyz")
    def test_leaves_include_steps_and_evidence(self, mock_anchor):
        """Verify that leaves passed to build_merkle_root contain all steps + evidence."""
        from api.src.services.solana_service import anchor_purchase

        steps = [
            {"action": "search", "query": "usb cable"},
            {"action": "compare", "products": 3},
        ]
        evidence = {"amount": 12.99, "merchant": "Amazon"}

        result = anchor_purchase("sess-3", "tx-3", steps, evidence)

        assert result == "sig-xyz"
        # Reconstruct what build_merkle_root should have received
        expected_leaves = [json.dumps(s, sort_keys=True) for s in steps]
        expected_leaves.append(json.dumps(evidence, sort_keys=True))
        # Verify by calling build_merkle_root ourselves and checking the root
        # was forwarded to anchor_to_solana
        from api.src.services.solana_service import build_merkle_root
        expected_root = build_merkle_root(expected_leaves)
        mock_anchor.assert_called_once_with("sess-3", expected_root, "tx-3")

    @patch("api.src.services.solana_service.anchor_to_solana", return_value="sig-empty")
    def test_empty_steps_still_works(self, mock_anchor):
        """Even with no agent steps, evidence alone produces a valid root."""
        from api.src.services.solana_service import anchor_purchase

        steps = []
        evidence = {"note": "direct purchase"}

        result = anchor_purchase("sess-4", "tx-4", steps, evidence)

        assert result == "sig-empty"
        # With empty steps, leaves should be just the evidence JSON
        expected_leaves = [json.dumps(evidence, sort_keys=True)]
        from api.src.services.solana_service import build_merkle_root
        expected_root = build_merkle_root(expected_leaves)
        mock_anchor.assert_called_once_with("sess-4", expected_root, "tx-4")
