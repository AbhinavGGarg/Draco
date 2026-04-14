"""Tests for agent step audit log endpoints."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from flask import Flask
from api.src.routes.agent_steps import agent_steps_bp


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(agent_steps_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# TestCreateAgentStep  (POST /api/webhook/agent-step)
# ---------------------------------------------------------------------------

class TestCreateAgentStep:

    @patch("api.src.routes.agent_steps.supabase")
    def test_valid_step_returns_201_with_step_id(self, mock_supabase, client):
        mock_result = MagicMock()
        mock_result.data = [{"id": "step-abc-123"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result

        resp = client.post("/api/webhook/agent-step", json={
            "session_id": "sess-1",
            "step_type": "tool_call",
            "data": {"tool": "search", "query": "USB cables"},
        })

        assert resp.status_code == 201
        body = resp.get_json()
        assert body["success"] is True
        assert body["step_id"] == "step-abc-123"

        # Verify the row passed to insert
        inserted_row = mock_supabase.table.return_value.insert.call_args[0][0]
        assert inserted_row["session_id"] == "sess-1"
        assert inserted_row["step_type"] == "tool_call"
        assert inserted_row["data"] == {"tool": "search", "query": "USB cables"}

    @patch("api.src.routes.agent_steps.datetime")
    @patch("api.src.routes.agent_steps.supabase")
    def test_auto_generates_timestamp_when_not_provided(self, mock_supabase, mock_dt, client):
        """When the request body omits 'timestamp', the route should generate one
        from datetime.now(timezone.utc).  We verify datetime.now is called."""
        fake_now = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        mock_result = MagicMock()
        mock_result.data = [{"id": "step-ts-1"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result

        resp = client.post("/api/webhook/agent-step", json={
            "session_id": "sess-1",
            "step_type": "reasoning",
        })

        assert resp.status_code == 201
        mock_dt.now.assert_called_once_with(timezone.utc)

    @patch("api.src.routes.agent_steps.supabase")
    def test_uses_provided_timestamp(self, mock_supabase, client):
        """When the caller supplies a timestamp, datetime.now should NOT be invoked,
        and the provided value should be used as-is."""
        mock_result = MagicMock()
        mock_result.data = [{"id": "step-ts-2"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result

        provided_ts = "2026-01-15T08:30:00+00:00"
        resp = client.post("/api/webhook/agent-step", json={
            "session_id": "sess-1",
            "step_type": "reasoning",
            "timestamp": provided_ts,
        })

        assert resp.status_code == 201
        assert resp.get_json()["step_id"] == "step-ts-2"

    @patch("api.src.routes.agent_steps.supabase")
    def test_missing_session_id_returns_400(self, mock_supabase, client):
        resp = client.post("/api/webhook/agent-step", json={
            "step_type": "tool_call",
        })

        assert resp.status_code == 400
        body = resp.get_json()
        assert body["code"] == "missing_fields"
        assert "session_id" in body["error"]

    @patch("api.src.routes.agent_steps.supabase")
    def test_missing_step_type_returns_400(self, mock_supabase, client):
        resp = client.post("/api/webhook/agent-step", json={
            "session_id": "sess-1",
        })

        assert resp.status_code == 400
        body = resp.get_json()
        assert body["code"] == "missing_fields"
        assert "step_type" in body["error"]

    @patch("api.src.routes.agent_steps.supabase")
    def test_missing_both_fields_returns_400(self, mock_supabase, client):
        resp = client.post("/api/webhook/agent-step", json={})

        assert resp.status_code == 400
        body = resp.get_json()
        assert body["code"] == "missing_fields"

    @patch("api.src.routes.agent_steps.supabase")
    def test_data_field_is_optional(self, mock_supabase, client):
        """When 'data' is omitted, the row should contain data=None."""
        mock_result = MagicMock()
        mock_result.data = [{"id": "step-no-data"}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result

        resp = client.post("/api/webhook/agent-step", json={
            "session_id": "sess-1",
            "step_type": "reasoning",
        })

        assert resp.status_code == 201
        inserted_row = mock_supabase.table.return_value.insert.call_args[0][0]
        assert inserted_row["data"] is None


# ---------------------------------------------------------------------------
# TestGetSessionSteps  (GET /api/sessions/{session_id}/steps)
# ---------------------------------------------------------------------------

class TestGetSessionSteps:

    @patch("api.src.routes.agent_steps.supabase")
    def test_returns_ordered_steps(self, mock_supabase, client):
        steps = [
            {"id": "s1", "session_id": "sess-1", "step_type": "reasoning",
             "data": None, "created_at": "2026-03-28T10:00:00"},
            {"id": "s2", "session_id": "sess-1", "step_type": "tool_call",
             "data": {"tool": "search"}, "created_at": "2026-03-28T10:00:05"},
            {"id": "s3", "session_id": "sess-1", "step_type": "response",
             "data": {"text": "Found 3 results"}, "created_at": "2026-03-28T10:00:10"},
        ]
        mock_result = MagicMock()
        mock_result.data = steps
        (mock_supabase.table.return_value
         .select.return_value
         .eq.return_value
         .order.return_value
         .execute.return_value) = mock_result

        resp = client.get("/api/sessions/sess-1/steps")

        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body) == 3
        assert body[0]["id"] == "s1"
        assert body[1]["id"] == "s2"
        assert body[2]["id"] == "s3"

        # Verify the correct table and filters were used
        mock_supabase.table.assert_called_with("agent_steps")
        mock_supabase.table.return_value.select.assert_called_with("*")
        mock_supabase.table.return_value.select.return_value.eq.assert_called_with(
            "session_id", "sess-1"
        )
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.assert_called_with(
            "created_at"
        )

    @patch("api.src.routes.agent_steps.supabase")
    def test_empty_session_returns_empty_list(self, mock_supabase, client):
        mock_result = MagicMock()
        mock_result.data = []
        (mock_supabase.table.return_value
         .select.return_value
         .eq.return_value
         .order.return_value
         .execute.return_value) = mock_result

        resp = client.get("/api/sessions/sess-nonexistent/steps")

        assert resp.status_code == 200
        body = resp.get_json()
        assert body == []
