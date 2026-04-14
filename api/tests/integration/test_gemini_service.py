"""Tests for Gemini post-execution review service."""
import json
import pytest
from unittest.mock import patch, MagicMock

from api.src.services.gemini_service import review_purchase, review_and_score


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def intent_snapshot():
    return {
        "product_description": "USB-C cable",
        "amount": 11.99,
        "category": "electronics",
        "merchant": "Amazon",
    }


@pytest.fixture
def agent_steps():
    return [
        {"step_type": "search", "data": {"query": "USB-C cable"}},
        {"step_type": "select", "data": {"product": "USB-C cable 6ft"}},
    ]


@pytest.fixture
def execution_result():
    return {
        "final_amount": 11.99,
        "final_merchant": "Amazon",
        "amount_match": True,
        "merchant_match": True,
    }


@pytest.fixture
def match_response():
    return {
        "verdict": "MATCH",
        "reasoning": "The agent bought the correct item at the expected price.",
        "confidence": 0.95,
        "flagged_issues": [],
    }


@pytest.fixture
def mismatch_response():
    return {
        "verdict": "MISMATCH",
        "reasoning": "The agent bought from a different merchant than requested.",
        "confidence": 0.80,
        "flagged_issues": ["merchant mismatch", "price 10% higher"],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_genai_mock(response_text):
    """Create a mock google.genai module with a Client that returns *response_text*.

    ``from google import genai`` inside review_purchase resolves ``genai`` as
    ``sys.modules["google"].genai``.  We therefore build a mock ``google``
    parent whose ``.genai`` attribute has a working ``Client``.
    """
    mock_response = MagicMock()
    mock_response.text = response_text

    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response

    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client_instance

    mock_google = MagicMock()
    mock_google.genai = mock_genai

    return mock_google, mock_genai, mock_client_instance


def _build_genai_mock_error(error):
    """Create a mock google.genai module whose generate_content raises *error*."""
    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.side_effect = error

    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client_instance

    mock_google = MagicMock()
    mock_google.genai = mock_genai

    return mock_google, mock_genai


def _make_tx(evidence=None, session_id="sess-1"):
    return {
        "id": "tx-1",
        "session_id": session_id,
        "evidence": evidence if evidence is not None else {},
    }


def _setup_supabase_mock(mock_supabase, tx, agent_steps_data=None):
    """Wire up chained Supabase calls for transactions and agent_steps tables."""
    tx_select = MagicMock()
    tx_select.data = [tx] if tx else []

    steps_select = MagicMock()
    steps_select.data = agent_steps_data or []

    tx_update = MagicMock()

    def table_router(table_name):
        mock_table = MagicMock()
        if table_name == "transactions":
            mock_table.select.return_value.eq.return_value.execute.return_value = tx_select
            mock_table.update.return_value.eq.return_value.execute.return_value = tx_update
        elif table_name == "agent_steps":
            mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value = steps_select
        return mock_table

    mock_supabase.table.side_effect = table_router
    return mock_supabase


def _setup_supabase_mock_with_update_tracker(mock_supabase, tx, agent_steps_data=None):
    """Like _setup_supabase_mock but returns an update_tracker for payload inspection."""
    tx_select = MagicMock()
    tx_select.data = [tx] if tx else []

    steps_select = MagicMock()
    steps_select.data = agent_steps_data or []

    update_tracker = MagicMock()
    update_tracker.return_value.eq.return_value.execute.return_value = MagicMock()

    def table_router(table_name):
        mock_table = MagicMock()
        if table_name == "transactions":
            mock_table.select.return_value.eq.return_value.execute.return_value = tx_select
            mock_table.update = update_tracker
        elif table_name == "agent_steps":
            mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value = steps_select
        return mock_table

    mock_supabase.table.side_effect = table_router
    return update_tracker


# ===========================================================================
# TestReviewPurchase
# ===========================================================================

class TestReviewPurchase:
    """Unit tests for review_purchase (mock genai.Client)."""

    @patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"})
    def test_match_verdict_parsed_correctly(
        self, intent_snapshot, agent_steps, execution_result, match_response
    ):
        mock_google, mock_genai, _ = _build_genai_mock(json.dumps(match_response))
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            result = review_purchase(intent_snapshot, agent_steps, execution_result)

        assert result["verdict"] == "MATCH"
        assert result["reasoning"] == match_response["reasoning"]
        assert result["confidence"] == 0.95
        assert result["flagged_issues"] == []

    @patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"})
    def test_mismatch_with_flagged_issues(
        self, intent_snapshot, agent_steps, execution_result, mismatch_response
    ):
        mock_google, mock_genai, _ = _build_genai_mock(json.dumps(mismatch_response))
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            result = review_purchase(intent_snapshot, agent_steps, execution_result)

        assert result["verdict"] == "MISMATCH"
        assert "merchant mismatch" in result["flagged_issues"]
        assert "price 10% higher" in result["flagged_issues"]
        assert result["confidence"] == 0.80

    @patch.dict("os.environ", {"GEMINI_API_KEY": ""})
    def test_missing_api_key_returns_error(
        self, intent_snapshot, agent_steps, execution_result
    ):
        mock_google, mock_genai, _ = _build_genai_mock("{}")
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            result = review_purchase(intent_snapshot, agent_steps, execution_result)

        assert result["verdict"] == "ERROR"
        assert "GEMINI_API_KEY" in result["reasoning"]

    @patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"})
    def test_api_exception_returns_error(
        self, intent_snapshot, agent_steps, execution_result
    ):
        mock_google, mock_genai = _build_genai_mock_error(RuntimeError("quota exceeded"))
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            result = review_purchase(intent_snapshot, agent_steps, execution_result)

        assert result["verdict"] == "ERROR"
        assert "quota exceeded" in result["reasoning"]

    @patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"})
    def test_invalid_json_response_returns_error(
        self, intent_snapshot, agent_steps, execution_result
    ):
        mock_google, mock_genai, _ = _build_genai_mock("This is not valid JSON at all")
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            result = review_purchase(intent_snapshot, agent_steps, execution_result)

        assert result["verdict"] == "ERROR"
        assert result["reasoning"]  # contains JSONDecodeError info

    @patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"})
    def test_missing_verdict_field_defaults(
        self, intent_snapshot, agent_steps, execution_result
    ):
        """When verdict is absent or not MATCH/MISMATCH, it defaults to MISMATCH."""
        body = {"reasoning": "not sure", "confidence": 0.3}
        mock_google, mock_genai, _ = _build_genai_mock(json.dumps(body))
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            result = review_purchase(intent_snapshot, agent_steps, execution_result)

        assert result["verdict"] == "MISMATCH"
        assert result["reasoning"] == "not sure"
        assert result["confidence"] == 0.3
        assert result["flagged_issues"] == []

    @patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"})
    def test_markdown_fences_stripped(
        self, intent_snapshot, agent_steps, execution_result, match_response
    ):
        """Gemini sometimes wraps JSON in ```json ... ``` fences."""
        wrapped = "```json\n" + json.dumps(match_response) + "\n```"
        mock_google, mock_genai, _ = _build_genai_mock(wrapped)
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            result = review_purchase(intent_snapshot, agent_steps, execution_result)

        assert result["verdict"] == "MATCH"
        assert result["confidence"] == 0.95

    @patch.dict("os.environ", {"GEMINI_API_KEY": "fake-key"})
    def test_confidence_is_float_flagged_is_list(
        self, intent_snapshot, agent_steps, execution_result
    ):
        body = {
            "verdict": "MATCH",
            "reasoning": "All good.",
            "confidence": 0.88,
            "flagged_issues": ["minor concern"],
        }
        mock_google, mock_genai, _ = _build_genai_mock(json.dumps(body))
        with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
            result = review_purchase(intent_snapshot, agent_steps, execution_result)

        assert isinstance(result["confidence"], float)
        assert isinstance(result["flagged_issues"], list)
        assert result["flagged_issues"] == ["minor concern"]


# ===========================================================================
# TestReviewAndScore
# ===========================================================================

class TestReviewAndScore:
    """Unit tests for review_and_score (mock Supabase + review_purchase)."""

    @patch("api.src.services.gemini_service.review_purchase")
    @patch("api.src.db.supabase")
    def test_success_updates_evidence_with_gemini_review(
        self, mock_supabase, mock_review, match_response
    ):
        evidence = {
            "intent_snapshot": {"amount": 11.99},
            "execution_result": {"final_amount": 11.99},
        }
        tx = _make_tx(evidence=evidence, session_id="sess-1")
        steps_data = [{"step_type": "search", "data": {"q": "cable"}}]

        _setup_supabase_mock(mock_supabase, tx, agent_steps_data=steps_data)
        mock_review.return_value = match_response

        result = review_and_score("tx-1")

        assert result["verdict"] == "MATCH"
        mock_review.assert_called_once_with(
            evidence["intent_snapshot"],
            steps_data,
            evidence["execution_result"],
        )

    @patch("api.src.services.gemini_service.review_purchase")
    @patch("api.src.db.supabase")
    def test_transaction_not_found_returns_error(self, mock_supabase, mock_review):
        _setup_supabase_mock(mock_supabase, tx=None)

        result = review_and_score("tx-nonexistent")

        assert result["verdict"] == "ERROR"
        assert "not found" in result["reasoning"]
        mock_review.assert_not_called()

    @patch("api.src.services.gemini_service.review_purchase")
    @patch("api.src.db.supabase")
    def test_no_session_id_works_with_empty_steps(
        self, mock_supabase, mock_review, match_response
    ):
        """When tx has no session_id, agent_steps should be an empty list."""
        evidence = {"intent_snapshot": {}, "execution_result": {}}
        tx = _make_tx(evidence=evidence, session_id="")

        _setup_supabase_mock(mock_supabase, tx)
        mock_review.return_value = match_response

        result = review_and_score("tx-1")

        assert result["verdict"] == "MATCH"
        mock_review.assert_called_once_with({}, [], {})

    @patch("api.src.services.gemini_service.review_purchase")
    @patch("api.src.db.supabase")
    def test_review_error_stored_in_evidence(self, mock_supabase, mock_review):
        """When review_purchase returns ERROR, the result is still stored in evidence."""
        evidence = {"intent_snapshot": {}, "execution_result": {}}
        tx = _make_tx(evidence=evidence, session_id="sess-1")

        update_tracker = _setup_supabase_mock_with_update_tracker(
            mock_supabase, tx, agent_steps_data=[]
        )
        error_verdict = {"verdict": "ERROR", "reasoning": "quota exceeded"}
        mock_review.return_value = error_verdict

        result = review_and_score("tx-1")

        assert result["verdict"] == "ERROR"
        assert "quota exceeded" in result["reasoning"]

        # The ERROR verdict should still be stored in evidence
        update_tracker.assert_called_once()
        update_arg = update_tracker.call_args[0][0]
        assert update_arg["evidence"]["gemini_review"] == error_verdict

    @patch("api.src.services.gemini_service.review_purchase")
    @patch("api.src.db.supabase")
    def test_supabase_update_called_with_gemini_review_key(
        self, mock_supabase, mock_review, match_response
    ):
        evidence = {"intent_snapshot": {"amount": 5.0}, "execution_result": {}}
        tx = _make_tx(evidence=evidence, session_id="sess-1")

        update_tracker = _setup_supabase_mock_with_update_tracker(
            mock_supabase, tx, agent_steps_data=[]
        )
        mock_review.return_value = match_response

        review_and_score("tx-1")

        update_tracker.assert_called_once()
        update_arg = update_tracker.call_args[0][0]

        assert "evidence" in update_arg
        assert "gemini_review" in update_arg["evidence"]
        assert update_arg["evidence"]["gemini_review"] == match_response
