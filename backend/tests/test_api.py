import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Set test environment variables before importing app
os.environ["LLM_API_KEYS"] = "dummy_key_1,dummy_key_2"
os.environ["ENABLE_FAILURE_SIMULATION"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"
os.environ["LLM_MODEL"] = "gemini/gemini-2.5-flash"

from app.main import app
from app.db import init_db, clear_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    init_db()
    clear_db()
    yield
    clear_db()

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["keys_configured"] == 2
    assert data["cache_enabled"] is True

def test_chat_validation_errors():
    # Empty message
    r1 = client.post("/chat", json={"session_id": "test_s1", "message": "   "})
    assert r1.status_code == 422
    assert "detail" in r1.json()

    # Empty session_id
    r2 = client.post("/chat", json={"session_id": "", "message": "hello"})
    assert r2.status_code == 422

    # Over 4000 characters
    r3 = client.post("/chat", json={"session_id": "test_s1", "message": "a" * 4001})
    assert r3.status_code == 422

def test_chat_with_mocked_litellm():
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="Paris is the capital of France."))]
    mock_resp.usage = MagicMock(prompt_tokens=25, completion_tokens=10)

    with patch("litellm.completion", return_value=mock_resp):
        response = client.post(
            "/chat",
            json={"session_id": "test_session_1", "message": "What is the capital of France?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test_session_1"
        assert data["reply"] == "Paris is the capital of France."
        assert data["metadata"]["resolution_source"] == "LIVE_INFERENCE"
        assert data["metadata"]["key_id"] == "key_1"
        assert data["metadata"]["fallback_attempts"] == 0
        assert data["metadata"]["input_tokens"] == 25
        assert data["metadata"]["output_tokens"] == 10

def test_caching_behavior():
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="Cached response text"))]
    mock_resp.usage = MagicMock(prompt_tokens=20, completion_tokens=8)

    with patch("litellm.completion", return_value=mock_resp) as mock_litellm:
        # First call in session A -> LIVE_INFERENCE
        r1 = client.post("/chat", json={"session_id": "session_cache_1", "message": "Tell me a joke"})
        assert r1.status_code == 200
        assert r1.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
        assert mock_litellm.call_count == 1

        # Second call with identical first message in a NEW session B -> LLM_CACHE
        r2 = client.post("/chat", json={"session_id": "session_cache_2", "message": "Tell me a joke"})
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["metadata"]["resolution_source"] == "LLM_CACHE"
        assert data2["reply"] == "Cached response text"
        assert data2["metadata"]["key_id"] is None
        assert data2["metadata"]["fallback_attempts"] == 0
        # Should not have called litellm.completion again
        assert mock_litellm.call_count == 1

def test_failure_simulation_failover():
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="Success on backup key."))]
    mock_resp.usage = MagicMock(prompt_tokens=30, completion_tokens=12)

    with patch("litellm.completion", return_value=mock_resp) as mock_litellm:
        # Simulate key_1 failing with 429
        r = client.post(
            "/chat",
            json={"session_id": "sim_fail_1", "message": "Simulate failover"},
            headers={"X-Simulate-Failure": "key_1=429"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["metadata"]["key_id"] == "key_2"
        assert data["metadata"]["fallback_attempts"] == 1
        assert data["reply"] == "Success on backup key."

def test_failure_simulation_all_fail():
    # Simulate all keys failing with 429
    r = client.post(
        "/chat",
        json={"session_id": "sim_fail_all", "message": "All keys down"},
        headers={"X-Simulate-Failure": "*=429"}
    )
    assert r.status_code == 503
    assert r.json() == {"detail": "all providers unavailable"}

    # Verify session was NOT saved
    r_hist = client.get("/sessions/sim_fail_all/messages")
    assert r_hist.status_code == 404

def test_session_messages_history():
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="Hello! How can I help you?"))]
    mock_resp.usage = MagicMock(prompt_tokens=15, completion_tokens=8)

    with patch("litellm.completion", return_value=mock_resp):
        client.post("/chat", json={"session_id": "history_session", "message": "Hi"})

    r = client.get("/sessions/history_session/messages")
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == "history_session"
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "Hi"
    assert data["messages"][1]["role"] == "assistant"
    assert data["messages"][1]["content"] == "Hello! How can I help you?"
    assert data["messages"][1]["metadata"]["resolution_source"] == "LIVE_INFERENCE"
