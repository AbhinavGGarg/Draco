import os
import json
import pytest
import sys
from unittest.mock import patch, MagicMock

# Mock google.genai module since it might not be installed in the test environment
sys.modules['google'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['google'].genai = sys.modules['google.genai']

# Import the module under test
from api.src.services import gemini_service

@pytest.fixture
def mock_genai_client():
    with patch("google.genai.Client", create=True) as mock_client:
        yield mock_client

@pytest.fixture
def mock_supabase():
    with patch("api.src.db.supabase") as mock_sb:
        yield mock_sb

@pytest.fixture
def sample_intent_snapshot():
    return {
        "product_description": "USB-C cable",
        "amount": 10.99,
        "category": "electronics",
        "merchant": "Amazon"
    }

@pytest.fixture
def sample_execution_result():
    return {
        "final_amount": 10.99,
        "final_merchant": "Amazon",
        "amount_match": True,
        "merchant_match": True
    }

@pytest.fixture
def sample_agent_steps():
    return [
        {"step_type": "search", "data": {"query": "USB-C cable"}},
        {"step_type": "click", "data": {"item": "Amazon Basics USB-C"}}
    ]

class TestReviewPurchase:
    def test_missing_api_key(self, sample_intent_snapshot, sample_execution_result, sample_agent_steps):
        with patch.dict(os.environ, {}, clear=True):
            result = gemini_service.review_purchase(sample_intent_snapshot, sample_agent_steps, sample_execution_result)
            assert result["verdict"] == "ERROR"
            assert "GEMINI_API_KEY not set" in result["reasoning"]

    def test_success_match(self, mock_genai_client, sample_intent_snapshot, sample_execution_result, sample_agent_steps):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
            # Setup mock response
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "verdict": "MATCH",
                "reasoning": "The agent bought exactly what the user wanted.",
                "confidence": 0.95,
                "flagged_issues": []
            })
            mock_instance = MagicMock()
            mock_instance.models.generate_content.return_value = mock_response
            mock_genai_client.return_value = mock_instance

            result = gemini_service.review_purchase(sample_intent_snapshot, sample_agent_steps, sample_execution_result)
            
            assert result["verdict"] == "MATCH"
            assert result["confidence"] == 0.95

    def test_success_mismatch(self, mock_genai_client, sample_intent_snapshot, sample_execution_result, sample_agent_steps):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "verdict": "MISMATCH",
                "reasoning": "Wrong merchant.",
                "confidence": 0.8,
                "flagged_issues": ["merchant mismatch"]
            })
            mock_instance = MagicMock()
            mock_instance.models.generate_content.return_value = mock_response
            mock_genai_client.return_value = mock_instance

            result = gemini_service.review_purchase(sample_intent_snapshot, sample_agent_steps, sample_execution_result)
            
            assert result["verdict"] == "MISMATCH"
            assert "merchant mismatch" in result["flagged_issues"]

    def test_empty_agent_steps(self, mock_genai_client, sample_intent_snapshot, sample_execution_result):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
            mock_response = MagicMock()
            mock_response.text = json.dumps({"verdict": "MATCH"})
            mock_instance = MagicMock()
            mock_instance.models.generate_content.return_value = mock_response
            mock_genai_client.return_value = mock_instance

            # Call with empty list
            result = gemini_service.review_purchase(sample_intent_snapshot, [], sample_execution_result)
            
            assert result["verdict"] == "MATCH"

    def test_malformed_json_response(self, mock_genai_client, sample_intent_snapshot, sample_execution_result, sample_agent_steps):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
            mock_response = MagicMock()
            mock_response.text = "This is not JSON 123"
            mock_instance = MagicMock()
            mock_instance.models.generate_content.return_value = mock_response
            mock_genai_client.return_value = mock_instance

            result = gemini_service.review_purchase(sample_intent_snapshot, sample_agent_steps, sample_execution_result)
            
            assert result["verdict"] == "ERROR"
            assert "Expecting value" in result["reasoning"]

    def test_invalid_verdict_fallback(self, mock_genai_client, sample_intent_snapshot, sample_execution_result, sample_agent_steps):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
            mock_response = MagicMock()
            mock_response.text = json.dumps({"verdict": "MAYBE"}) # Invalid verdict
            mock_instance = MagicMock()
            mock_instance.models.generate_content.return_value = mock_response
            mock_genai_client.return_value = mock_instance

            result = gemini_service.review_purchase(sample_intent_snapshot, sample_agent_steps, sample_execution_result)
            
            # Should fallback to MISMATCH
            assert result["verdict"] == "MISMATCH"

    def test_markdown_code_fences_stripped(self, mock_genai_client, sample_intent_snapshot, sample_execution_result, sample_agent_steps):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
            mock_response = MagicMock()
            # Wrap JSON in markdown fences
            mock_response.text = "```json\n" + json.dumps({"verdict": "MATCH"}) + "\n```"
            mock_instance = MagicMock()
            mock_instance.models.generate_content.return_value = mock_response
            mock_genai_client.return_value = mock_instance

            result = gemini_service.review_purchase(sample_intent_snapshot, sample_agent_steps, sample_execution_result)
            
            assert result["verdict"] == "MATCH"

    def test_gemini_api_exception(self, mock_genai_client, sample_intent_snapshot, sample_execution_result, sample_agent_steps):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
            mock_instance = MagicMock()
            mock_instance.models.generate_content.side_effect = Exception("API Server Down")
            mock_genai_client.return_value = mock_instance

            result = gemini_service.review_purchase(sample_intent_snapshot, sample_agent_steps, sample_execution_result)
            
            assert result["verdict"] == "ERROR"
            assert "API Server Down" in result["reasoning"]


class TestReviewAndScore:
    @patch('api.src.db.supabase')
    def test_transaction_not_found(self, mock_supabase):
        # Mock transaction lookup returning empty list
        mock_tx_query = MagicMock()
        mock_tx_query.execute.return_value.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value = mock_tx_query

        result = gemini_service.review_and_score("tx_missing")
        
        assert result["verdict"] == "ERROR"
        assert "not found" in result["reasoning"]

    @patch('api.src.db.supabase')
    @patch('api.src.services.gemini_service.review_purchase')
    def test_successful_flow(self, mock_review_purchase, mock_supabase):
        # Mock transaction data
        tx_data = {
            "id": "tx_123",
            "session_id": "sess_123",
            "evidence": {
                "intent_snapshot": {"amount": 5.00},
                "execution_result": {"final_amount": 5.00}
            }
        }
        mock_tx_query = MagicMock()
        mock_tx_query.execute.return_value.data = [tx_data]
        
        # Mock agent steps data
        steps_data = [{"step_type": "search"}]
        mock_steps_query = MagicMock()
        mock_steps_query.execute.return_value.data = steps_data
        
        mock_tx_table = MagicMock()
        mock_tx_table.select.return_value.eq.return_value = mock_tx_query
        
        mock_steps_table = MagicMock()
        mock_steps_table.select.return_value.eq.return_value.order.return_value = mock_steps_query

        # Configure supabase table selector
        def table_side_effect(table_name):
            if table_name == "transactions":
                return mock_tx_table
            elif table_name == "agent_steps":
                return mock_steps_table
        
        mock_supabase.table.side_effect = table_side_effect
        
        # Mock review_purchase successful return
        mock_review_purchase.return_value = {
            "verdict": "MATCH",
            "reasoning": "Perfect match",
            "confidence": 1.0,
            "flagged_issues": []
        }
        
        result = gemini_service.review_and_score("tx_123")
        
        # Verify result structure
        assert result["verdict"] == "MATCH"
        
        # Verify db logic was called correctly
        mock_review_purchase.assert_called_once_with(
            tx_data["evidence"]["intent_snapshot"],
            steps_data,
            tx_data["evidence"]["execution_result"]
        )

        # Ensure update was called on the `transactions` table
        assert mock_tx_table.update.called

    @patch('api.src.db.supabase')
    @patch('api.src.services.gemini_service.review_purchase')
    def test_missing_session_id(self, mock_review_purchase, mock_supabase):
        # Transaction missing session_id
        tx_data = {
            "id": "tx_123",
            "session_id": "", # Missing
            "evidence": {}
        }
        mock_tx_query = MagicMock()
        mock_tx_query.execute.return_value.data = [tx_data]
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "transactions":
                mock_table.select.return_value.eq.return_value = mock_tx_query
            return mock_table
            
        mock_supabase.table.side_effect = table_side_effect
        mock_review_purchase.return_value = {"verdict": "MISMATCH"}

        result = gemini_service.review_and_score("tx_123")
        
        assert result["verdict"] == "MISMATCH"
        mock_review_purchase.assert_called_once_with({}, [], {})

    @patch('api.src.db.supabase')
    def test_supabase_update_exception(self, mock_supabase):
        # Mock transaction found
        mock_tx_query = MagicMock()
        mock_tx_query.execute.return_value.data = [{"id": "tx_no_update"}]
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "transactions":
                # First call is select, second call is update
                mock_table.select.return_value.eq.return_value = mock_tx_query
                mock_table.update.return_value.eq.return_value.execute.side_effect = Exception("DB Timeout")
            return mock_table
            
        mock_supabase.table.side_effect = table_side_effect
        
        with patch('api.src.services.gemini_service.review_purchase') as mock_review:
            mock_review.return_value = {"verdict": "MATCH"}
            result = gemini_service.review_and_score("tx_no_update")
            
            assert result["verdict"] == "ERROR"
            assert "DB Timeout" in result["reasoning"]

    @patch('api.src.db.supabase')
    @patch('api.src.services.gemini_service.review_purchase')
    def test_review_purchase_exception(self, mock_review_purchase, mock_supabase):
        # Mock transaction found
        mock_tx_query = MagicMock()
        mock_tx_query.execute.return_value.data = [{"id": "tx_fails"}]
        mock_supabase.table.return_value.select.return_value.eq.return_value = mock_tx_query

        # Mock review_purchase crash
        mock_review_purchase.side_effect = ValueError("Something bad happened internally")

        result = gemini_service.review_and_score("tx_fails")
        
        assert result["verdict"] == "ERROR"
        assert "Something bad happened internally" in result["reasoning"]
